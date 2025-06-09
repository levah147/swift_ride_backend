"""
User models for Swift Ride project.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from apps.common.models import BaseModel, SoftDeleteModel
from .managers import CustomUserManager


class CustomUser(AbstractBaseUser, PermissionsMixin, BaseModel, SoftDeleteModel):
    """
    Custom user model for Swift Ride.
    """
    class UserType(models.TextChoices):
        RIDER = 'rider', _('Rider')
        DRIVER = 'driver', _('Driver')
        ADMIN = 'admin', _('Admin')
    
    phone_number = PhoneNumberField(unique=True)
    email = models.EmailField(_('email address'), blank=True, null=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    user_type = models.CharField(
        max_length=10,
        choices=UserType.choices,
        default=UserType.RIDER
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_('Designates whether this user has verified their phone number.'),
    )
    date_joined = models.DateTimeField(_('date joined'), auto_now_add=True)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
    
    def __str__(self):
        return str(self.phone_number)
    
    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
    
    @property
    def is_rider(self):
        return self.user_type == self.UserType.RIDER
    
    @property
    def is_driver(self):
        return self.user_type == self.UserType.DRIVER
    
    @property
    def is_admin(self):
        return self.user_type == self.UserType.ADMIN


class RiderProfile(BaseModel):
    """
    Profile model for riders.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='rider_profile'
    )
    profile_picture = models.ImageField(
        upload_to='profiles/riders/',
        null=True,
        blank=True
    )
    home_address = models.CharField(max_length=255, blank=True, null=True)
    work_address = models.CharField(max_length=255, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_number = PhoneNumberField(blank=True, null=True)
    
    def __str__(self):
        return f"Rider Profile: {self.user}"


class DriverProfile(BaseModel):
    """
    Profile model for drivers.
    """
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
    
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='driver_profile'
    )
    profile_picture = models.ImageField(
        upload_to='profiles/drivers/',
        null=True,
        blank=True
    )
    license_number = models.CharField(max_length=50, blank=True, null=True)
    license_expiry = models.DateField(blank=True, null=True)
    license_image = models.ImageField(
        upload_to='documents/licenses/',
        null=True,
        blank=True
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    is_online = models.BooleanField(default=False)
    is_available = models.BooleanField(default=False)
    current_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    current_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    last_location_update = models.DateTimeField(null=True, blank=True)
    total_rides = models.PositiveIntegerField(default=0)
    total_earnings = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    
    def __str__(self):
        return f"Driver Profile: {self.user}"


class UserPreferences(BaseModel):
    """
    User preferences model.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='preferences'
    )
    language = models.CharField(max_length=10, default='en')
    dark_mode = models.BooleanField(default=False)
    push_notifications = models.BooleanField(default=True)
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Preferences: {self.user}"
 