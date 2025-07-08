"""
Custom managers for authentication models.
"""

from django.db import models
from django.utils import timezone


class OTPManager(models.Manager):
    """
    Custom manager for OTP model.
    """
    
    def get_valid_otp(self, user, code):
        """
        Get valid OTP for user.
        """
        try:
            return self.get(
                user=user,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except self.model.DoesNotExist:
            return None
    
    def cleanup_expired(self):
        """
        Clean up expired OTPs.
        """
        expired_count = self.filter(
            expires_at__lt=timezone.now()
        ).delete()[0]
        return expired_count
    
    def get_recent_attempts(self, phone_number, minutes=5):
        """
        Get recent OTP attempts for a phone number.
        """
        since = timezone.now() - timezone.timedelta(minutes=minutes)
        return self.filter(
            user__phone_number=phone_number,
            created_at__gte=since
        ).count()


class LoginAttemptManager(models.Manager):
    """
    Custom manager for LoginAttempt model.
    """
    
    def get_recent_failed_attempts(self, phone_number, minutes=30):
        """
        Get recent failed login attempts.
        """
        since = timezone.now() - timezone.timedelta(minutes=minutes)
        return self.filter(
            phone_number=phone_number,
            is_successful=False,
            created_at__gte=since
        ).count()
    
    def cleanup_old_attempts(self, days=30):
        """
        Clean up old login attempts.
        """
        cutoff = timezone.now() - timezone.timedelta(days=days)
        deleted_count = self.filter(created_at__lt=cutoff).delete()[0]
        return deleted_count
