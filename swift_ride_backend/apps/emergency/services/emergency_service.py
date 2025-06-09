from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from apps.emergency.models import (
    EmergencyAlert, EmergencyContact, SafetyCheck, 
    EmergencyResponse, EmergencySettings, LocationShare
)
from apps.notifications.services.notification_service import NotificationService
from apps.rides.models import Ride
from core.utils.exceptions import ValidationError
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class EmergencyService:
    """Service for handling emergency operations"""
    
    @staticmethod
    def trigger_panic_button(user, ride=None, location=None, description=None, audio_file=None):
        """Trigger panic button and initiate emergency response"""
        try:
            with transaction.atomic():
                # Create emergency alert
                alert = EmergencyAlert.objects.create(
                    user=user,
                    ride=ride,
                    alert_type='panic',
                    severity='critical',
                    latitude=location.get('latitude') if location else None,
                    longitude=location.get('longitude') if location else None,
                    address=location.get('address') if location else None,
                    description=description,
                    audio_recording=audio_file
                )
                
                # Start emergency response workflow
                EmergencyService._initiate_emergency_response(alert)
                
                # Send immediate notifications
                EmergencyService._send_emergency_notifications(alert)
                
                # Start location sharing
                if ride:
                    EmergencyService._start_emergency_location_sharing(user, alert, ride)
                
                logger.info(f"Panic button triggered for user {user.id}, alert {alert.id}")
                return alert
                
        except Exception as e:
            logger.error(f"Error triggering panic button: {str(e)}")
            raise ValidationError("Failed to trigger emergency alert")
    
    @staticmethod
    def create_emergency_alert(user, alert_type, severity='medium', **kwargs):
        """Create a general emergency alert"""
        try:
            alert = EmergencyAlert.objects.create(
                user=user,
                alert_type=alert_type,
                severity=severity,
                **kwargs
            )
            
            # Initiate response based on severity
            if severity in ['high', 'critical']:
                EmergencyService._initiate_emergency_response(alert)
            
            EmergencyService._send_emergency_notifications(alert)
            
            return alert
            
        except Exception as e:
            logger.error(f"Error creating emergency alert: {str(e)}")
            raise ValidationError("Failed to create emergency alert")
    
    @staticmethod
    def acknowledge_alert(alert_id, acknowledged_by):
        """Acknowledge an emergency alert"""
        try:
            alert = EmergencyAlert.objects.get(id=alert_id)
            
            if alert.status != 'active':
                raise ValidationError("Alert is not in active status")
            
            alert.status = 'acknowledged'
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = acknowledged_by
            alert.save()
            
            # Notify relevant parties
            NotificationService.send_notification(
                user=alert.user,
                title="Emergency Alert Acknowledged",
                message=f"Your emergency alert has been acknowledged by {acknowledged_by.get_full_name()}",
                notification_type='emergency'
            )
            
            return alert
            
        except EmergencyAlert.DoesNotExist:
            raise ValidationError("Emergency alert not found")
        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            raise ValidationError("Failed to acknowledge alert")
    
    @staticmethod
    def resolve_alert(alert_id, resolved_by, resolution_notes=None):
        """Resolve an emergency alert"""
        try:
            alert = EmergencyAlert.objects.get(id=alert_id)
            
            alert.status = 'resolved'
            alert.resolved_at = timezone.now()
            alert.resolved_by = resolved_by
            alert.resolution_notes = resolution_notes
            alert.save()
            
            # Stop location sharing
            LocationShare.objects.filter(
                alert=alert,
                is_active=True
            ).update(is_active=False)
            
            # Notify user
            NotificationService.send_notification(
                user=alert.user,
                title="Emergency Alert Resolved",
                message="Your emergency alert has been resolved",
                notification_type='emergency'
            )
            
            return alert
            
        except EmergencyAlert.DoesNotExist:
            raise ValidationError("Emergency alert not found")
        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            raise ValidationError("Failed to resolve alert")
    
    @staticmethod
    def schedule_safety_check(ride, check_type='automatic', delay_minutes=15):
        """Schedule a safety check for a ride"""
        try:
            scheduled_time = timezone.now() + timezone.timedelta(minutes=delay_minutes)
            
            safety_check = SafetyCheck.objects.create(
                ride=ride,
                user=ride.rider,
                check_type=check_type,
                scheduled_at=scheduled_time
            )
            
            # Schedule background task for check
            from apps.emergency.tasks import process_safety_check
            process_safety_check.apply_async(
                args=[safety_check.id],
                eta=scheduled_time
            )
            
            return safety_check
            
        except Exception as e:
            logger.error(f"Error scheduling safety check: {str(e)}")
            raise ValidationError("Failed to schedule safety check")
    
    @staticmethod
    def complete_safety_check(check_id, is_safe=True, response_message=None, location=None):
        """Complete a safety check"""
        try:
            check = SafetyCheck.objects.get(id=check_id)
            
            check.status = 'completed'
            check.completed_at = timezone.now()
            check.is_safe = is_safe
            check.response_message = response_message
            
            if location:
                check.latitude = location.get('latitude')
                check.longitude = location.get('longitude')
            
            check.save()
            
            # If not safe, escalate
            if not is_safe:
                EmergencyService._escalate_safety_check(check)
            
            return check
            
        except SafetyCheck.DoesNotExist:
            raise ValidationError("Safety check not found")
        except Exception as e:
            logger.error(f"Error completing safety check: {str(e)}")
            raise ValidationError("Failed to complete safety check")
    
    @staticmethod
    def _initiate_emergency_response(alert):
        """Initiate emergency response workflow"""
        settings = EmergencySettings.get_settings()
        
        # Create response actions
        response_actions = [
            'contact_emergency_contacts',
            'track_location',
        ]
        
        if alert.severity == 'critical':
            response_actions.extend([
                'notify_authorities',
                'call_user'
            ])
        
        for action in response_actions:
            EmergencyResponse.objects.create(
                alert=alert,
                action_type=action
            )
        
        # Schedule escalation if needed
        from apps.emergency.tasks import escalate_emergency_alert
        escalate_emergency_alert.apply_async(
            args=[alert.id],
            countdown=settings.first_escalation_timeout * 60
        )
    
    @staticmethod
    def _send_emergency_notifications(alert):
        """Send emergency notifications to relevant parties"""
        # Notify emergency contacts
        emergency_contacts = EmergencyContact.objects.filter(
            user=alert.user,
            is_active=True
        )
        
        for contact in emergency_contacts:
            NotificationService.send_sms(
                phone_number=contact.phone_number,
                message=f"EMERGENCY: {alert.user.get_full_name()} has triggered an emergency alert. "
                       f"Alert type: {alert.get_alert_type_display()}. "
                       f"Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S')}. "
                       f"Please contact them immediately."
            )
        
        # Notify platform administrators
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            NotificationService.send_notification(
                user=admin,
                title="Emergency Alert Triggered",
                message=f"Emergency alert triggered by {alert.user.get_full_name()}",
                notification_type='emergency',
                data={'alert_id': str(alert.id)}
            )
    
    @staticmethod
    def _start_emergency_location_sharing(user, alert, ride):
        """Start emergency location sharing"""
        # Get emergency contacts
        emergency_contacts = EmergencyContact.objects.filter(
            user=user,
            is_active=True
        ).values_list('user_id', flat=True)
        
        # Create location share
        location_share = LocationShare.objects.create(
            user=user,
            alert=alert,
            ride=ride,
            share_type='emergency',
            expires_at=timezone.now() + timezone.timedelta(hours=24)
        )
        
        # Add emergency contacts to sharing
        if emergency_contacts:
            location_share.shared_with.set(emergency_contacts)
        
        return location_share
    
    @staticmethod
    def _escalate_safety_check(check):
        """Escalate a failed safety check"""
        # Create emergency alert
        alert = EmergencyAlert.objects.create(
            user=check.user,
            ride=check.ride,
            alert_type='other',
            severity='high',
            description=f"Safety check failed: {check.response_message}",
            latitude=check.latitude,
            longitude=check.longitude
        )
        
        # Mark check as escalated
        check.escalated = True
        check.escalated_at = timezone.now()
        check.save()
        
        # Initiate emergency response
        EmergencyService._initiate_emergency_response(alert)
        EmergencyService._send_emergency_notifications(alert)
    
    @staticmethod
    def get_active_alerts(user=None):
        """Get active emergency alerts"""
        queryset = EmergencyAlert.objects.filter(
            status__in=['active', 'acknowledged', 'responding']
        )
        
        if user:
            queryset = queryset.filter(user=user)
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def get_user_emergency_contacts(user):
        """Get user's emergency contacts"""
        return EmergencyContact.objects.filter(
            user=user,
            is_active=True
        ).order_by('-is_primary', 'name')
    
    @staticmethod
    def add_emergency_contact(user, name, phone_number, relationship, email=None, is_primary=False):
        """Add emergency contact for user"""
        try:
            contact = EmergencyContact.objects.create(
                user=user,
                name=name,
                phone_number=phone_number,
                relationship=relationship,
                email=email,
                is_primary=is_primary
            )
            
            return contact
            
        except Exception as e:
            logger.error(f"Error adding emergency contact: {str(e)}")
            raise ValidationError("Failed to add emergency contact")
    
    @staticmethod
    def update_location_share(share_id, latitude, longitude):
        """Update location for active location share"""
        try:
            share = LocationShare.objects.get(
                id=share_id,
                is_active=True
            )
            
            share.current_latitude = latitude
            share.current_longitude = longitude
            share.last_update = timezone.now()
            share.save()
            
            return share
            
        except LocationShare.DoesNotExist:
            raise ValidationError("Location share not found or inactive")
        except Exception as e:
            logger.error(f"Error updating location share: {str(e)}")
            raise ValidationError("Failed to update location")
