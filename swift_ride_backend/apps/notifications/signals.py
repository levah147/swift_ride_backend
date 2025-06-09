"""
Signals for notification models.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.notifications.models import Notification


@receiver(post_save, sender=Notification)
def notification_created(sender, instance, created, **kwargs):
    """
    Handle notification creation.
    """
    if created:
        # Send real-time notification via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        
        channel_layer = get_channel_layer()
        user_group_name = f'notifications_{instance.recipient.id}'
        
        # Send to WebSocket
        async_to_sync(channel_layer.group_send)(
            user_group_name,
            {
                'type': 'new_notification',
                'notification': {
                    'id': str(instance.id),
                    'title': instance.title,
                    'body': instance.body,
                    'type': instance.template.notification_type,
                    'priority': instance.priority,
                    'created_at': instance.created_at.isoformat(),
                }
            }
        )
        
        # Update unread count
        from apps.notifications.services.notification_service import NotificationService
        unread_count = NotificationService.get_unread_count(instance.recipient)
        
        async_to_sync(channel_layer.group_send)(
            user_group_name,
            {
                'type': 'notification_update',
                'unread_count': unread_count
            }
        )
