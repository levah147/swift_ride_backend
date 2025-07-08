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
    
    nin = models.CharField(max_length=11, blank=True, null=True, unique=True)
    bvn = models.CharField(max_length=11, blank=True, null=True, unique=True)
    referral_code = models.CharField(max_length=10, blank=True, null=True, unique=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='referrals'
    )
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
    location_updated_at = models.DateTimeField(null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    deactivated_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
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


class UserProfile(BaseModel):
    """
    Extended user profile model.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    bio = models.TextField(max_length=500, blank=True, null=True)
    profile_picture = models.ImageField(
        upload_to='profiles/',
        null=True,
        blank=True
    )
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=[
            ('male', _('Male')),
            ('female', _('Female')),
            ('other', _('Other')),
        ],
        blank=True,
        null=True
    )
    address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, default='Nigeria')
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True)
    emergency_contact_relationship = models.CharField(max_length=50, blank=True, null=True)
    emergency_contact_phone = PhoneNumberField(blank=True, null=True)
    
    def __str__(self):
        return f"Profile: {self.user}"


class UserDocument(BaseModel):
    """
    User document model for verification.
    """
    class DocumentType(models.TextChoices):
        NIN = 'nin', _('National ID (NIN)')
        BVN = 'bvn', _('Bank Verification Number')
        DRIVERS_LICENSE = 'drivers_license', _("Driver's License")
        PASSPORT = 'passport', _('International Passport')
        VOTERS_CARD = 'voters_card', _("Voter's Card")
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        VERIFIED = 'verified', _('Verified')
        REJECTED = 'rejected', _('Rejected')
    
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices
    )
    document_number = models.CharField(max_length=50)
    document_file = models.FileField(
        upload_to='documents/',
        null=True,
        blank=True
    )
    expiry_date = models.DateField(blank=True, null=True)
    verification_status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_notes = models.TextField(blank=True, null=True)
    
    class Meta:
        unique_together = ['user', 'document_type', 'document_number']
    
    def __str__(self):
        return f"{self.user} - {self.get_document_type_display()}"


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
    
    home_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    home_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    work_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    work_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0
    )
    total_rides = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
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
    
    vehicle_type = models.CharField(
        max_length=20,
        choices=[
            ('sedan', _('Sedan')),
            ('suv', _('SUV')),
            ('hatchback', _('Hatchback')),
            ('bus', _('Bus')),
            ('motorcycle', _('Motorcycle')),
        ],
        blank=True,
        null=True
    )
    experience_years = models.PositiveIntegerField(default=0)
    availability_status = models.CharField(
        max_length=20,
        choices=[
            ('available', _('Available')),
            ('busy', _('Busy')),
            ('offline', _('Offline')),
        ],
        default='offline'
    )
    status = models.CharField(
        max_length=10,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='drivers'
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
    
    currency = models.CharField(max_length=10, default='NGN')
    accessibility_features = models.JSONField(default=dict, blank=True)
    ride_notifications = models.BooleanField(default=True)
    chat_notifications = models.BooleanField(default=True)
    marketing_notifications = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Preferences: {self.user}"
 