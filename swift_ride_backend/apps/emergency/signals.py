from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from apps.emergency.models import EmergencyAlert, SafetyCheck, EmergencyResponse
from apps.notifications.services.notification_service import NotificationService
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=EmergencyAlert)
def emergency_alert_created(sender, instance, created, **kwargs):
    """Handle emergency alert creation"""
    if created:
        logger.info(f"Emergency alert created: {instance.id} for user {instance.user.id}")
        
        # Send real-time notification to admin users
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        admin_users = User.objects.filter(is_staff=True, is_active=True)
        for admin in admin_users:
            NotificationService.send_real_time_notification(
                user=admin,
                title="Emergency Alert",
                message=f"New emergency alert from {instance.user.get_full_name()}",
                notification_type='emergency',
                data={
                    'alert_id': str(instance.id),
                    'alert_type': instance.alert_type,
                    'severity': instance.severity,
                    'user_id': instance.user.id
                }
            )


@receiver(pre_save, sender=EmergencyAlert)
def emergency_alert_status_changed(sender, instance, **kwargs):
    """Handle emergency alert status changes"""
    if instance.pk:
        try:
            old_instance = EmergencyAlert.objects.get(pk=instance.pk)
            
            # Check if status changed
            if old_instance.status != instance.status:
                logger.info(f"Emergency alert {instance.id} status changed from {old_instance.status} to {instance.status}")
                
                # Send notification to user
                status_messages = {
                    'acknowledged': 'Your emergency alert has been acknowledged',
                    'responding': 'Emergency response is in progress',
                    'resolved': 'Your emergency alert has been resolved',
                    'false_alarm': 'Emergency alert marked as false alarm',
                    'cancelled': 'Emergency alert has been cancelled'
                }
                
                if instance.status in status_messages:
                    NotificationService.send_notification(
                        user=instance.user,
                        title="Emergency Alert Update",
                        message=status_messages[instance.status],
                        notification_type='emergency'
                    )
                
                # If resolved, notify emergency contacts
                if instance.status == 'resolved':
                    from apps.emergency.services.contact_service import ContactService
                    try:
                        ContactService.notify_emergency_contacts(instance, 'resolved')
                    except Exception as e:
                        logger.error(f"Error notifying contacts of resolution: {str(e)}")
        
        except EmergencyAlert.DoesNotExist:
            pass


@receiver(post_save, sender=SafetyCheck)
def safety_check_created(sender, instance, created, **kwargs):
    """Handle safety check creation"""
    if created:
        logger.info(f"Safety check scheduled: {instance.id} for ride {instance.ride.id}")
        
        # Send notification to user
        NotificationService.send_notification(
            user=instance.user,
            title="Safety Check Scheduled",
            message=f"Safety check scheduled for {instance.scheduled_at.strftime('%H:%M')}",
            notification_type='safety'
        )


@receiver(pre_save, sender=SafetyCheck)
def safety_check_status_changed(sender, instance, **kwargs):
    """Handle safety check status changes"""
    if instance.pk:
        try:
            old_instance = SafetyCheck.objects.get(pk=instance.pk)
            
            # Check if status changed to missed
            if old_instance.status != 'missed' and instance.status == 'missed':
                logger.warning(f"Safety check {instance.id} missed for user {instance.user.id}")
                
                # Create emergency alert for missed safety check
                from apps.emergency.models import EmergencyAlert
                EmergencyAlert.objects.create(
                    user=instance.user,
                    ride=instance.ride,
                    alert_type='other',
                    severity='medium',
                    description=f"Missed safety check at {instance.scheduled_at}",
                    latitude=instance.latitude,
                    longitude=instance.longitude
                )
            
            # Check if escalated
            if not old_instance.escalated and instance.escalated:
                logger.warning(f"Safety check {instance.id} escalated for user {instance.user.id}")
                
                # Send escalation notification
                NotificationService.send_notification(
                    user=instance.user,
                    title="Safety Check Escalated",
                    message="Your missed safety check has been escalated to emergency response",
                    notification_type='emergency'
                )
        
        except SafetyCheck.DoesNotExist:
            pass


@receiver(post_save, sender=EmergencyResponse)
def emergency_response_created(sender, instance, created, **kwargs):
    """Handle emergency response creation"""
    if created:
        logger.info(f"Emergency response created: {instance.action_type} for alert {instance.alert.id}")
        
        # Auto-assign response based on action type
        if instance.action_type == 'contact_emergency_contacts':
            # Trigger contact service
            from apps.emergency.tasks import contact_emergency_contacts
            contact_emergency_contacts.delay(instance.alert.id)
        
        elif instance.action_type == 'track_location':
            # Start location tracking
            from apps.emergency.tasks import start_location_tracking
            start_location_tracking.delay(instance.alert.id)
        
        elif instance.action_type == 'notify_authorities':
            # Notify authorities
            from apps.emergency.tasks import notify_authorities
            notify_authorities.delay(instance.alert.id)


@receiver(pre_save, sender=EmergencyResponse)
def emergency_response_status_changed(sender, instance, **kwargs):
    """Handle emergency response status changes"""
    if instance.pk:
        try:
            old_instance = EmergencyResponse.objects.get(pk=instance.pk)
            
            # Check if status changed to completed
            if old_instance.status != 'completed' and instance.status == 'completed':
                logger.info(f"Emergency response {instance.id} completed: {instance.action_type}")
                
                # Check if all responses for alert are completed
                alert = instance.alert
                pending_responses = EmergencyResponse.objects.filter(
                    alert=alert,
                    status__in=['pending', 'in_progress']
                ).count()
                
                if pending_responses == 0 and alert.status == 'acknowledged':
                    # All responses completed, update alert status
                    alert.status = 'responding'
                    alert.save()
        
        except EmergencyResponse.DoesNotExist:
            pass
