"""
Celery tasks for notifications app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.notifications.models import Notification, NotificationBatch


@shared_task
def send_notification_task(notification_id):
    """
    Send a single notification.
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Check if notification is expired
        if notification.is_expired:
            notification.status = Notification.Status.CANCELLED
            notification.save()
            return f"Notification {notification_id} expired"
        
        # Send based on channel
        channel = notification.template.channel
        
        if channel == notification.template.Channel.PUSH:
            from apps.notifications.services.push_service import PushNotificationService
            success, message = PushNotificationService.send_push_notification(notification)
        
        elif channel == notification.template.Channel.SMS:
            from apps.notifications.services.sms_service import SMSService
            success, message = SMSService.send_sms_notification(notification)
        
        elif channel == notification.template.Channel.EMAIL:
            from apps.notifications.services.email_service import EmailService
            success, message = EmailService.send_email_notification(notification)
        
        else:
            # In-app notification - just mark as sent
            notification.mark_as_sent()
            success, message = True, "In-app notification sent"
        
        return f"Notification {notification_id}: {message}"
    
    except Notification.DoesNotExist:
        return f"Notification {notification_id} not found"
    except Exception as e:
        return f"Error sending notification {notification_id}: {str(e)}"


@shared_task
def send_bulk_notifications_task(batch_id, recipient_ids, notification_type, context, channels):
    """
    Send bulk notifications.
    """
    try:
        batch = NotificationBatch.objects.get(id=batch_id)
        batch.status = NotificationBatch.Status.PROCESSING
        batch.started_at = timezone.now()
        batch.save()
        
        from apps.users.models import CustomUser
        from apps.notifications.services.notification_service import NotificationService
        
        sent_count = 0
        failed_count = 0
        
        for recipient_id in recipient_ids:
            try:
                recipient = CustomUser.objects.get(id=recipient_id)
                
                notifications = NotificationService.send_notification(
                    recipient=recipient,
                    notification_type=notification_type,
                    context=context,
                    channels=channels
                )
                
                if notifications:
                    sent_count += len(notifications)
                else:
                    failed_count += 1
            
            except CustomUser.DoesNotExist:
                failed_count += 1
            except Exception:
                failed_count += 1
        
        # Update batch status
        batch.sent_count = sent_count
        batch.failed_count = failed_count
        batch.status = NotificationBatch.Status.COMPLETED
        batch.completed_at = timezone.now()
        batch.save()
        
        return f"Bulk notification batch {batch_id} completed: {sent_count} sent, {failed_count} failed"
    
    except NotificationBatch.DoesNotExist:
        return f"Notification batch {batch_id} not found"
    except Exception as e:
        return f"Error processing bulk notifications {batch_id}: {str(e)}"


@shared_task
def process_scheduled_notifications():
    """
    Process scheduled notifications that are due.
    """
    # Get notifications that are scheduled and due
    due_notifications = Notification.objects.filter(
        status=Notification.Status.PENDING,
        scheduled_at__lte=timezone.now(),
        is_deleted=False
    )
    
    count = 0
    for notification in due_notifications:
        # Check if not expired
        if not notification.is_expired:
            send_notification_task.delay(str(notification.id))
            count += 1
        else:
            notification.status = Notification.Status.CANCELLED
            notification.save()
    
    return f"Processed {count} scheduled notifications"


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notifications.
    """
    # Delete notifications older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_notifications = Notification.objects.filter(
        created_at__lt=cutoff_date
    )
    
    count = old_notifications.count()
    old_notifications.delete()
    
    return f"Deleted {count} old notifications"


@shared_task
def cleanup_inactive_device_tokens():
    """
    Clean up inactive device tokens.
    """
    from apps.notifications.models import DeviceToken
    
    # Delete device tokens that haven't been used in 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    
    inactive_tokens = DeviceToken.objects.filter(
        last_used__lt=cutoff_date,
        is_active=False
    )
    
    count = inactive_tokens.count()
    inactive_tokens.delete()
    
    return f"Deleted {count} inactive device tokens"


@shared_task
def generate_notification_analytics():
    """
    Generate daily notification analytics.
    """
    from apps.notifications.models import NotificationAnalytics, NotificationTemplate
    from django.db.models import Count, Avg
    
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Get all templates and channels
    templates = NotificationTemplate.objects.filter(is_active=True)
    
    for template in templates:
        for channel in NotificationTemplate.Channel.choices:
            channel_value = channel[0]
            
            # Get notifications for this template and channel from yesterday
            notifications = Notification.objects.filter(
                template=template,
                template__channel=channel_value,
                created_at__date=yesterday
            )
            
            if notifications.exists():
                # Calculate metrics
                sent_count = notifications.filter(status__in=[
                    Notification.Status.SENT,
                    Notification.Status.DELIVERED,
                    Notification.Status.READ
                ]).count()
                
                delivered_count = notifications.filter(status__in=[
                    Notification.Status.DELIVERED,
                    Notification.Status.READ
                ]).count()
                
                read_count = notifications.filter(
                    status=Notification.Status.READ
                ).count()
                
                failed_count = notifications.filter(
                    status=Notification.Status.FAILED
                ).count()
                
                # Create or update analytics record
                analytics, created = NotificationAnalytics.objects.get_or_create(
                    date=yesterday,
                    template=template,
                    channel=channel_value,
                    defaults={
                        'sent_count': sent_count,
                        'delivered_count': delivered_count,
                        'read_count': read_count,
                        'failed_count': failed_count,
                    }
                )
                
                if not created:
                    analytics.sent_count = sent_count
                    analytics.delivered_count = delivered_count
                    analytics.read_count = read_count
                    analytics.failed_count = failed_count
                
                # Calculate rates
                analytics.calculate_rates()
                analytics.save()
    
    return f"Generated notification analytics for {yesterday}"


@shared_task
def send_weekly_summary_emails():
    """
    Send weekly summary emails to users.
    """
    from apps.users.models import CustomUser
    from apps.notifications.services.email_service import EmailService
    
    # Get users who want weekly summaries
    users = CustomUser.objects.filter(
        notification_preferences__email_weekly_summary=True,
        email__isnull=False
    ).exclude(email='')
    
    sent_count = 0
    
    for user in users:
        try:
            # Generate summary data (simplified)
            summary_data = {
                'total_rides': user.rider_rides.filter(
                    created_at__gte=timezone.now() - timedelta(days=7)
                ).count(),
                'total_spent': 0,  # Calculate from payments
                'favorite_destinations': [],  # Calculate from rides
            }
            
            # Send email
            success = EmailService.send_weekly_summary_email(user, summary_data)
            if success:
                sent_count += 1
        
        except Exception as e:
            print(f"Error sending weekly summary to {user.id}: {e}")
    
    return f"Sent weekly summary emails to {sent_count} users"
