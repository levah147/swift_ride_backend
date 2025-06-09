from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.emergency.models import (
    EmergencyAlert, SafetyCheck, EmergencyResponse, 
    EmergencySettings, LocationShare
)
from apps.emergency.services.contact_service import ContactService
from apps.emergency.services.location_service import LocationService
from apps.notifications.services.notification_service import NotificationService
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def process_safety_check(check_id):
    """Process a scheduled safety check"""
    try:
        check = SafetyCheck.objects.get(id=check_id)
        
        if check.status != 'pending':
            logger.info(f"Safety check {check_id} already processed")
            return
        
        # Check if overdue
        if timezone.now() > check.scheduled_at:
            # Send safety check notification
            NotificationService.send_notification(
                user=check.user,
                title="Safety Check",
                message="Please confirm you are safe",
                notification_type='safety',
                data={'check_id': check.id}
            )
            
            # Schedule escalation if not responded
            escalate_safety_check.apply_async(
                args=[check_id],
                countdown=300  # 5 minutes
            )
        
        logger.info(f"Safety check {check_id} processed")
        
    except SafetyCheck.DoesNotExist:
        logger.error(f"Safety check {check_id} not found")
    except Exception as e:
        logger.error(f"Error processing safety check {check_id}: {str(e)}")


@shared_task
def escalate_safety_check(check_id):
    """Escalate a missed safety check"""
    try:
        check = SafetyCheck.objects.get(id=check_id)
        
        if check.status == 'completed':
            logger.info(f"Safety check {check_id} completed, no escalation needed")
            return
        
        # Mark as missed
        check.status = 'missed'
        check.save()
        
        # Create emergency alert
        alert = EmergencyAlert.objects.create(
            user=check.user,
            ride=check.ride,
            alert_type='other',
            severity='medium',
            description=f"Missed safety check at {check.scheduled_at}",
            latitude=check.latitude,
            longitude=check.longitude
        )
        
        logger.warning(f"Safety check {check_id} escalated to emergency alert {alert.id}")
        
    except SafetyCheck.DoesNotExist:
        logger.error(f"Safety check {check_id} not found")
    except Exception as e:
        logger.error(f"Error escalating safety check {check_id}: {str(e)}")


@shared_task
def escalate_emergency_alert(alert_id):
    """Escalate an emergency alert if not acknowledged"""
    try:
        alert = EmergencyAlert.objects.get(id=alert_id)
        
        if alert.status != 'active':
            logger.info(f"Emergency alert {alert_id} already processed")
            return
        
        settings = EmergencySettings.get_settings()
        
        # Mark as escalated
        alert.escalated = True
        alert.escalated_at = timezone.now()
        alert.escalation_level += 1
        alert.save()
        
        # Create additional response actions
        if alert.escalation_level == 1:
            # First escalation - notify more contacts
            EmergencyResponse.objects.create(
                alert=alert,
                action_type='call_user'
            )
        
        elif alert.escalation_level == 2:
            # Second escalation - notify authorities
            EmergencyResponse.objects.create(
                alert=alert,
                action_type='notify_authorities'
            )
            
            alert.police_notified = True
            alert.save()
        
        # Schedule next escalation
        if alert.escalation_level < 3:
            escalate_emergency_alert.apply_async(
                args=[alert_id],
                countdown=settings.second_escalation_timeout * 60
            )
        
        logger.warning(f"Emergency alert {alert_id} escalated to level {alert.escalation_level}")
        
    except EmergencyAlert.DoesNotExist:
        logger.error(f"Emergency alert {alert_id} not found")
    except Exception as e:
        logger.error(f"Error escalating emergency alert {alert_id}: {str(e)}")


@shared_task
def contact_emergency_contacts(alert_id):
    """Contact emergency contacts for an alert"""
    try:
        alert = EmergencyAlert.objects.get(id=alert_id)
        
        # Get the response record
        response = EmergencyResponse.objects.filter(
            alert=alert,
            action_type='contact_emergency_contacts',
            status='pending'
        ).first()
        
        if response:
            response.status = 'in_progress'
            response.started_at = timezone.now()
            response.save()
        
        # Contact emergency contacts
        results = ContactService.notify_emergency_contacts(alert, 'emergency')
        
        # Update response
        if response:
            success_count = sum(1 for r in results if r.get('sms_sent') or r.get('email_sent'))
            response.status = 'completed'
            response.completed_at = timezone.now()
            response.success = success_count > 0
            response.notes = f"Contacted {success_count}/{len(results)} contacts"
            response.save()
        
        logger.info(f"Emergency contacts notified for alert {alert_id}")
        
    except EmergencyAlert.DoesNotExist:
        logger.error(f"Emergency alert {alert_id} not found")
    except Exception as e:
        logger.error(f"Error contacting emergency contacts for alert {alert_id}: {str(e)}")


@shared_task
def start_location_tracking(alert_id):
    """Start location tracking for an emergency alert"""
    try:
        alert = EmergencyAlert.objects.get(id=alert_id)
        
        # Get the response record
        response = EmergencyResponse.objects.filter(
            alert=alert,
            action_type='track_location',
            status='pending'
        ).first()
        
        if response:
            response.status = 'in_progress'
            response.started_at = timezone.now()
            response.save()
        
        # Create or update location share
        location_share, created = LocationShare.objects.get_or_create(
            alert=alert,
            user=alert.user,
            defaults={
                'share_type': 'emergency',
                'is_active': True,
                'expires_at': timezone.now() + timezone.timedelta(hours=24)
            }
        )
        
        if not created:
            location_share.is_active = True
            location_share.expires_at = timezone.now() + timezone.timedelta(hours=24)
            location_share.save()
        
        # Update response
        if response:
            response.status = 'completed'
            response.completed_at = timezone.now()
            response.success = True
            response.notes = f"Location tracking started: {location_share.share_token}"
            response.save()
        
        logger.info(f"Location tracking started for alert {alert_id}")
        
    except EmergencyAlert.DoesNotExist:
        logger.error(f"Emergency alert {alert_id} not found")
    except Exception as e:
        logger.error(f"Error starting location tracking for alert {alert_id}: {str(e)}")


@shared_task
def notify_authorities(alert_id):
    """Notify authorities about an emergency alert"""
    try:
        alert = EmergencyAlert.objects.get(id=alert_id)
        
        # Get the response record
        response = EmergencyResponse.objects.filter(
            alert=alert,
            action_type='notify_authorities',
            status='pending'
        ).first()
        
        if response:
            response.status = 'in_progress'
            response.started_at = timezone.now()
            response.save()
        
        settings = EmergencySettings.get_settings()
        
        # In production, this would integrate with emergency services APIs
        # For now, we'll simulate the notification
        
        authority_message = (
            f"Emergency Alert Report\n"
            f"Alert ID: {alert.id}\n"
            f"User: {alert.user.get_full_name()}\n"
            f"Phone: {alert.user.phone_number}\n"
            f"Type: {alert.get_alert_type_display()}\n"
            f"Severity: {alert.get_severity_display()}\n"
            f"Time: {alert.created_at}\n"
            f"Location: {alert.latitude}, {alert.longitude}\n"
            f"Address: {alert.address or 'Unknown'}\n"
            f"Description: {alert.description or 'None'}"
        )
        
        # Simulate authority notification
        # In production, integrate with:
        # - Emergency services dispatch systems
        # - Police department APIs
        # - Medical services
        # - Fire department
        
        success = True  # Simulate successful notification
        
        # Update alert
        alert.police_notified = True
        alert.police_case_number = f"CASE-{alert.id}-{timezone.now().strftime('%Y%m%d')}"
        alert.save()
        
        # Update response
        if response:
            response.status = 'completed'
            response.completed_at = timezone.now()
            response.success = success
            response.notes = f"Authorities notified. Case: {alert.police_case_number}"
            response.save()
        
        logger.info(f"Authorities notified for alert {alert_id}")
        
    except EmergencyAlert.DoesNotExist:
        logger.error(f"Emergency alert {alert_id} not found")
    except Exception as e:
        logger.error(f"Error notifying authorities for alert {alert_id}: {str(e)}")


@shared_task
def cleanup_expired_location_shares():
    """Clean up expired location shares"""
    try:
        expired_shares = LocationShare.objects.filter(
            is_active=True,
            expires_at__lt=timezone.now()
        )
        
        count = expired_shares.count()
        expired_shares.update(is_active=False)
        
        logger.info(f"Cleaned up {count} expired location shares")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired location shares: {str(e)}")


@shared_task
def generate_emergency_analytics():
    """Generate emergency analytics and reports"""
    try:
        from datetime import timedelta
        
        # Calculate metrics for the last 24 hours
        since = timezone.now() - timedelta(hours=24)
        
        alerts = EmergencyAlert.objects.filter(created_at__gte=since)
        total_alerts = alerts.count()
        
        if total_alerts > 0:
            # Response time metrics
            acknowledged_alerts = alerts.filter(acknowledged_at__isnull=False)
            if acknowledged_alerts.exists():
                response_times = []
                for alert in acknowledged_alerts:
                    if alert.response_time:
                        response_times.append(alert.response_time.total_seconds())
                
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    
                    # Send analytics to admin users
                    admin_users = User.objects.filter(is_staff=True, is_active=True)
                    for admin in admin_users:
                        NotificationService.send_notification(
                            user=admin,
                            title="Emergency Analytics (24h)",
                            message=f"Total alerts: {total_alerts}, Avg response: {avg_response_time:.1f}s",
                            notification_type='system'
                        )
        
        logger.info(f"Emergency analytics generated: {total_alerts} alerts in last 24h")
        
    except Exception as e:
        logger.error(f"Error generating emergency analytics: {str(e)}")


@shared_task
def monitor_active_alerts():
    """Monitor active emergency alerts for status updates"""
    try:
        active_alerts = EmergencyAlert.objects.filter(
            status__in=['active', 'acknowledged', 'responding']
        )
        
        settings = EmergencySettings.get_settings()
        
        for alert in active_alerts:
            # Check if alert is too old without resolution
            hours_since_created = (timezone.now() - alert.created_at).total_seconds() / 3600
            
            if hours_since_created > 24:  # 24 hours without resolution
                # Send escalation notification to admins
                admin_users = User.objects.filter(is_staff=True, is_active=True)
                for admin in admin_users:
                    NotificationService.send_notification(
                        user=admin,
                        title="Long-Running Emergency Alert",
                        message=f"Alert {alert.id} has been active for {hours_since_created:.1f} hours",
                        notification_type='emergency',
                        data={'alert_id': str(alert.id)}
                    )
        
        logger.info(f"Monitored {active_alerts.count()} active emergency alerts")
        
    except Exception as e:
        logger.error(f"Error monitoring active alerts: {str(e)}")
