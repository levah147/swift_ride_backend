"""
Celery tasks for the users app.
"""

from celery import shared_task
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
import logging

from .services.user_service import UserService
from .services.verification_service import VerificationService
from apps.notifications.services.notification_service import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_welcome_notification(self, user_id):
    """
    Send welcome notification to new user.
    """
    try:
        user = User.objects.get(id=user_id)
        notification_service = NotificationService()
        
        # Send welcome notification
        notification_service.send_notification(
            user=user,
            title="Welcome to SwiftRide!",
            message="Thank you for joining SwiftRide. Complete your profile to get started.",
            notification_type="welcome"
        )
        
        logger.info(f"Welcome notification sent to user {user_id}")
        return f"Welcome notification sent to user {user_id}"
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return f"User {user_id} not found"
    except Exception as exc:
        logger.error(f"Error sending welcome notification to user {user_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def verify_user_documents(self, user_id):
    """
    Verify user documents asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        verification_service = VerificationService()
        
        # Verify user documents
        verification_result = verification_service.verify_user_documents(user)
        
        if verification_result['success']:
            # Send verification success notification
            notification_service = NotificationService()
            notification_service.send_notification(
                user=user,
                title="Documents Verified",
                message="Your documents have been successfully verified!",
                notification_type="verification_success"
            )
        else:
            # Send verification failure notification
            notification_service = NotificationService()
            notification_service.send_notification(
                user=user,
                title="Document Verification Failed",
                message=f"Document verification failed: {verification_result.get('message', 'Unknown error')}",
                notification_type="verification_failed"
            )
        
        logger.info(f"Document verification completed for user {user_id}")
        return verification_result
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {"success": False, "message": f"User {user_id} not found"}
    except Exception as exc:
        logger.error(f"Error verifying documents for user {user_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes


@shared_task
def cleanup_inactive_users():
    """
    Clean up inactive users who haven't verified their accounts.
    """
    try:
        # Delete unverified users older than 7 days
        cutoff_date = timezone.now() - timedelta(days=7)
        inactive_users = User.objects.filter(
            is_verified=False,
            is_active=True,
            date_joined__lt=cutoff_date
        )
        
        count = inactive_users.count()
        inactive_users.delete()
        
        logger.info(f"Cleaned up {count} inactive users")
        return f"Cleaned up {count} inactive users"
        
    except Exception as exc:
        logger.error(f"Error cleaning up inactive users: {str(exc)}")
        raise exc


@shared_task
def update_user_ratings():
    """
    Update user ratings based on recent reviews.
    """
    try:
        user_service = UserService()
        updated_count = user_service.update_all_user_ratings()
        
        logger.info(f"Updated ratings for {updated_count} users")
        return f"Updated ratings for {updated_count} users"
        
    except Exception as exc:
        logger.error(f"Error updating user ratings: {str(exc)}")
        raise exc


@shared_task(bind=True, max_retries=3)
def send_profile_completion_reminder(self, user_id):
    """
    Send profile completion reminder to user.
    """
    try:
        user = User.objects.get(id=user_id)
        user_service = UserService()
        
        # Check profile completion percentage
        completion_percentage = user_service.get_profile_completion_percentage(user)
        
        if completion_percentage < 80:  # If profile is less than 80% complete
            notification_service = NotificationService()
            notification_service.send_notification(
                user=user,
                title="Complete Your Profile",
                message=f"Your profile is {completion_percentage}% complete. Complete it to get better ride matches!",
                notification_type="profile_reminder"
            )
            
            logger.info(f"Profile completion reminder sent to user {user_id}")
            return f"Profile completion reminder sent to user {user_id}"
        else:
            logger.info(f"User {user_id} profile is {completion_percentage}% complete, no reminder needed")
            return f"User {user_id} profile is complete"
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return f"User {user_id} not found"
    except Exception as exc:
        logger.error(f"Error sending profile completion reminder to user {user_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=300)


@shared_task
def generate_user_analytics():
    """
    Generate user analytics data.
    """
    try:
        user_service = UserService()
        analytics_data = user_service.generate_user_analytics()
        
        logger.info("User analytics generated successfully")
        return analytics_data
        
    except Exception as exc:
        logger.error(f"Error generating user analytics: {str(exc)}")
        raise exc


@shared_task(bind=True, max_retries=3)
def sync_user_location(self, user_id, latitude, longitude):
    """
    Sync user location to external services.
    """
    try:
        user = User.objects.get(id=user_id)
        user_service = UserService()
        
        # Update user location
        success = user_service.update_user_location(user, latitude, longitude)
        
        if success:
            logger.info(f"Location synced for user {user_id}")
            return f"Location synced for user {user_id}"
        else:
            logger.error(f"Failed to sync location for user {user_id}")
            return f"Failed to sync location for user {user_id}"
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return f"User {user_id} not found"
    except Exception as exc:
        logger.error(f"Error syncing location for user {user_id}: {str(exc)}")
        raise self.retry(exc=exc, countdown=60)


@shared_task
def send_birthday_notifications():
    """
    Send birthday notifications to users.
    """
    try:
        today = timezone.now().date()
        
        # Find users with birthday today
        birthday_users = User.objects.filter(
            date_of_birth__month=today.month,
            date_of_birth__day=today.day,
            is_active=True
        )
        
        notification_service = NotificationService()
        count = 0
        
        for user in birthday_users:
            notification_service.send_notification(
                user=user,
                title="Happy Birthday! 🎉",
                message="Happy Birthday from the SwiftRide team! Enjoy a special discount on your next ride.",
                notification_type="birthday"
            )
            count += 1
        
        logger.info(f"Birthday notifications sent to {count} users")
        return f"Birthday notifications sent to {count} users"
        
    except Exception as exc:
        logger.error(f"Error sending birthday notifications: {str(exc)}")
        raise exc


@shared_task
def backup_user_data():
    """
    Backup critical user data.
    """
    try:
        user_service = UserService()
        backup_result = user_service.backup_user_data()
        
        logger.info("User data backup completed")
        return backup_result
        
    except Exception as exc:
        logger.error(f"Error backing up user data: {str(exc)}")
        raise exc
