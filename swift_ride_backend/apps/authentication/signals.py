"""
Signals for authentication app.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from .models import OTP, LoginAttempt


@receiver(post_save, sender=OTP)
def otp_created(sender, instance, created, **kwargs):
    """
    Signal handler for when OTP is created.
    """
    if created:
        # Log OTP creation (in production, use proper logging)
        print(f"OTP created for user {instance.user.phone_number}")
        
        # You could add analytics tracking here
        # analytics.track('otp_requested', {
        #     'user_id': instance.user.id,
        #     'phone_number': str(instance.user.phone_number)
        # })


@receiver(post_save, sender=LoginAttempt)
def login_attempt_logged(sender, instance, created, **kwargs):
    """
    Signal handler for login attempts.
    """
    if created:
        # Check for suspicious activity
        recent_failed = LoginAttempt.objects.get_recent_failed_attempts(
            instance.phone_number
        )
        
        if recent_failed >= 5:
            # Log security alert
            print(f"Security Alert: Multiple failed login attempts for {instance.phone_number}")
            
            # You could send notification to security team here
            # send_security_alert(instance.phone_number, recent_failed)


@receiver(pre_delete, sender=OTP)
def otp_cleanup(sender, instance, **kwargs):
    """
    Signal handler before OTP deletion.
    """
    # Log OTP cleanup for audit purposes
    print(f"Cleaning up OTP for user {instance.user.phone_number}")
