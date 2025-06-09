"""
Service for handling notifications.
"""

from django.utils import timezone
from django.db import transaction

from apps.notifications.models import (
    Notification, NotificationTemplate, NotificationPreference,
    DeviceToken, NotificationLog
)


class NotificationService:
    """
    Service for handling notification operations.
    """
    
    @staticmethod
    def send_notification(
        recipient, 
        notification_type, 
        context=None, 
        channels=None,
        priority=Notification.Priority.NORMAL,
        scheduled_at=None,
        expires_at=None,
        related_ride=None,
        related_message=None
    ):
        """
        Send a notification to a user.
        """
        context = context or {}
        channels = channels or [NotificationTemplate.Channel.PUSH, NotificationTemplate.Channel.IN_APP]
        
        # Get user preferences
        preferences = NotificationService._get_user_preferences(recipient)
        
        notifications_created = []
        
        for channel in channels:
            # Check if user wants this type of notification
            if not preferences.should_send_notification(notification_type, channel):
                continue
            
            # Check quiet hours for non-critical notifications
            if priority < Notification.Priority.CRITICAL and preferences.is_quiet_time():
                continue
            
            # Get template for this notification type and channel
            template = NotificationService._get_template(notification_type, channel)
            if not template:
                continue
            
            # Create notification
            notification = NotificationService._create_notification(
                recipient=recipient,
                template=template,
                context=context,
                priority=priority,
                scheduled_at=scheduled_at,
                expires_at=expires_at,
                related_ride=related_ride,
                related_message=related_message
            )
            
            if notification:
                notifications_created.append(notification)
                
                # Send immediately if not scheduled
                if not scheduled_at:
                    NotificationService._send_notification(notification)
        
        return notifications_created
    
    @staticmethod
    def send_ride_notification(ride, notification_type, context=None):
        """
        Send ride-related notification to both rider and driver.
        """
        context = context or {}
        context.update({
            'ride_id': str(ride.id),
            'pickup_location': ride.pickup_location,
            'destination': ride.destination,
            'fare': str(ride.fare_amount) if ride.fare_amount else 'TBD',
        })
        
        notifications = []
        
        # Send to rider
        if ride.rider:
            context['user_name'] = ride.rider.get_full_name() or ride.rider.phone_number
            context['driver_name'] = ride.driver.get_full_name() if ride.driver else 'Driver'
            
            rider_notifications = NotificationService.send_notification(
                recipient=ride.rider,
                notification_type=notification_type,
                context=context,
                related_ride=ride,
                priority=Notification.Priority.HIGH
            )
            notifications.extend(rider_notifications)
        
        # Send to driver
        if ride.driver:
            context['user_name'] = ride.driver.get_full_name() or ride.driver.phone_number
            context['rider_name'] = ride.rider.get_full_name() if ride.rider else 'Rider'
            
            driver_notifications = NotificationService.send_notification(
                recipient=ride.driver,
                notification_type=notification_type,
                context=context,
                related_ride=ride,
                priority=Notification.Priority.HIGH
            )
            notifications.extend(driver_notifications)
        
        return notifications
    
    @staticmethod
    def send_message_notification(message):
        """
        Send notification for new chat message.
        """
        recipient = message.recipient
        sender = message.sender
        
        # Don't send notification if recipient is online (would be handled by WebSocket)
        # This is a simplified check - in production, you'd check actual online status
        
        context = {
            'sender_name': sender.get_full_name() or sender.phone_number,
            'message_preview': message.content[:50] + '...' if len(message.content) > 50 else message.content,
            'chat_room_id': message.chat_room.room_id,
        }
        
        # Determine notification type based on message type
        if message.message_type == message.MessageType.VOICE:
            notification_type = NotificationTemplate.NotificationType.VOICE_MESSAGE
            context['message_preview'] = 'Voice message'
        else:
            notification_type = NotificationTemplate.NotificationType.NEW_MESSAGE
        
        return NotificationService.send_notification(
            recipient=recipient,
            notification_type=notification_type,
            context=context,
            related_message=message,
            priority=Notification.Priority.NORMAL
        )
    
    @staticmethod
    def send_payment_notification(payment, notification_type):
        """
        Send payment-related notification.
        """
        context = {
            'amount': str(payment.amount),
            'currency': payment.currency,
            'payment_method': payment.payment_method,
            'transaction_id': payment.transaction_id,
        }
        
        return NotificationService.send_notification(
            recipient=payment.user,
            notification_type=notification_type,
            context=context,
            priority=Notification.Priority.HIGH
        )
    
    @staticmethod
    def send_emergency_notification(emergency_alert):
        """
        Send emergency notification to emergency contacts.
        """
        context = {
            'user_name': emergency_alert.user.get_full_name() or emergency_alert.user.phone_number,
            'location': emergency_alert.location_name or f"{emergency_alert.latitude}, {emergency_alert.longitude}",
            'emergency_type': emergency_alert.emergency_type,
            'timestamp': emergency_alert.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        notifications = []
        
        # Send to emergency contacts
        for contact in emergency_alert.user.emergency_contacts.filter(is_active=True):
            contact_notifications = NotificationService.send_notification(
                recipient=contact.contact_user if contact.contact_user else None,
                notification_type=NotificationTemplate.NotificationType.EMERGENCY_ALERT,
                context=context,
                channels=[NotificationTemplate.Channel.SMS, NotificationTemplate.Channel.PUSH],
                priority=Notification.Priority.CRITICAL
            )
            notifications.extend(contact_notifications)
        
        return notifications
    
    @staticmethod
    def send_bulk_notification(
        recipients, 
        notification_type, 
        context=None, 
        channels=None,
        scheduled_at=None
    ):
        """
        Send bulk notifications to multiple recipients.
        """
        from apps.notifications.tasks import send_bulk_notifications_task
        
        # Create batch record
        template = NotificationService._get_template(
            notification_type, 
            channels[0] if channels else NotificationTemplate.Channel.PUSH
        )
        
        if not template:
            return None
        
        from apps.notifications.models import NotificationBatch
        batch = NotificationBatch.objects.create(
            name=f"Bulk {notification_type} - {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            template=template,
            recipient_count=len(recipients),
            scheduled_at=scheduled_at or timezone.now(),
            context=context or {},
        )
        
        # Send via Celery task
        recipient_ids = [r.id for r in recipients]
        send_bulk_notifications_task.delay(
            batch.id,
            recipient_ids,
            notification_type,
            context,
            channels
        )
        
        return batch
    
    @staticmethod
    def mark_notification_as_read(notification_id, user):
        """
        Mark notification as read.
        """
        try:
            notification = Notification.objects.get(
                id=notification_id,
                recipient=user
            )
            notification.mark_as_read()
            return True, "Notification marked as read"
        except Notification.DoesNotExist:
            return False, "Notification not found"
    
    @staticmethod
    def get_user_notifications(user, limit=50, offset=0, unread_only=False):
        """
        Get notifications for a user.
        """
        queryset = Notification.objects.filter(
            recipient=user,
            is_deleted=False
        )
        
        if unread_only:
            queryset = queryset.exclude(status=Notification.Status.READ)
        
        return queryset.order_by('-created_at')[offset:offset + limit]
    
    @staticmethod
    def get_unread_count(user):
        """
        Get unread notification count for a user.
        """
        return Notification.objects.filter(
            recipient=user,
            is_deleted=False
        ).exclude(status=Notification.Status.READ).count()
    
    @staticmethod
    def register_device_token(user, token, platform, device_id=None, device_name=None, app_version=None):
        """
        Register device token for push notifications.
        """
        device_token, created = DeviceToken.objects.update_or_create(
            user=user,
            token=token,
            defaults={
                'platform': platform,
                'device_id': device_id,
                'device_name': device_name,
                'app_version': app_version,
                'is_active': True,
                'last_used': timezone.now()
            }
        )
        
        return device_token, created
    
    @staticmethod
    def unregister_device_token(user, token):
        """
        Unregister device token.
        """
        try:
            device_token = DeviceToken.objects.get(user=user, token=token)
            device_token.is_active = False
            device_token.save()
            return True, "Device token unregistered"
        except DeviceToken.DoesNotExist:
            return False, "Device token not found"
    
    # Private helper methods
    @staticmethod
    def _get_user_preferences(user):
        """
        Get user notification preferences.
        """
        preferences, created = NotificationPreference.objects.get_or_create(
            user=user
        )
        return preferences
    
    @staticmethod
    def _get_template(notification_type, channel):
        """
        Get notification template.
        """
        try:
            return NotificationTemplate.objects.get(
                notification_type=notification_type,
                channel=channel,
                is_active=True
            )
        except NotificationTemplate.DoesNotExist:
            return None
    
    @staticmethod
    def _create_notification(
        recipient, template, context, priority, 
        scheduled_at, expires_at, related_ride, related_message
    ):
        """
        Create notification record.
        """
        try:
            # Render content
            title = template.render_title(context)
            body = template.render_body(context)
            
            notification = Notification.objects.create(
                recipient=recipient,
                template=template,
                title=title,
                body=body,
                context=context,
                priority=priority,
                scheduled_at=scheduled_at,
                expires_at=expires_at,
                ride=related_ride,
                message=related_message
            )
            
            return notification
        except Exception as e:
            print(f"Error creating notification: {e}")
            return None
    
    @staticmethod
    def _send_notification(notification):
        """
        Send notification via appropriate channel.
        """
        from apps.notifications.tasks import send_notification_task
        
        # Send via Celery task for better performance
        send_notification_task.delay(str(notification.id))
        
        return True
