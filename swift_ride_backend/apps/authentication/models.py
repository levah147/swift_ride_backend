"""
Authentication models for Swift Ride project.
"""

from django.db import models
from django.utils import timezone
from django.conf import settings

from apps.common.models import BaseModel


class OTP(BaseModel):
    """
    One-Time Password model for phone verification.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otps'
    )
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"OTP for {self.user}"
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    @classmethod
    def create_for_user(cls, user, code=None, expiry_minutes=10):
        """
        Create a new OTP for the given user.
        """
        from apps.common.utils import generate_otp
        
        # Generate OTP if not provided
        if not code:
            code = generate_otp()
        
        # Set expiry time
        expires_at = timezone.now() + timezone.timedelta(minutes=expiry_minutes)
        
        # Create OTP
        otp = cls.objects.create(
            user=user,
            code=code,
            expires_at=expires_at
        )
        
        return otp


class LoginAttempt(BaseModel):
    """
    Model to track login attempts.
    """
    phone_number = models.CharField(max_length=20)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_successful = models.BooleanField(default=False)
    
    def __str__(self):
        status = "successful" if self.is_successful else "failed"
        return f"{status} login attempt for {self.phone_number}"
