from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator
from apps.common.models import BaseModel
from apps.rides.models import Ride
import uuid

User = get_user_model()


class EmergencyContact(BaseModel):
    """Model for storing user emergency contacts"""
    
    RELATIONSHIP_CHOICES = [
        ('family', 'Family Member'),
        ('friend', 'Friend'),
        ('colleague', 'Colleague'),
        ('spouse', 'Spouse'),
        ('parent', 'Parent'),
        ('sibling', 'Sibling'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='emergency_contacts'
    )
    name = models.CharField(max_length=100)
    phone_number = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
        )]
    )
    email = models.EmailField(blank=True, null=True)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    is_primary = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'emergency_contacts'
        ordering = ['-is_primary', 'name']
        unique_together = ['user', 'phone_number']
    
    def __str__(self):
        return f"{self.name} - {self.user.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Ensure only one primary contact per user
        if self.is_primary:
            EmergencyContact.objects.filter(
                user=self.user, 
                is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
        super().save(*args, **kwargs)


class EmergencyAlert(BaseModel):
    """Model for emergency alerts and panic button activations"""
    
    ALERT_TYPES = [
        ('panic', 'Panic Button'),
        ('accident', 'Accident'),
        ('harassment', 'Harassment'),
        ('vehicle_breakdown', 'Vehicle Breakdown'),
        ('medical', 'Medical Emergency'),
        ('security', 'Security Threat'),
        ('other', 'Other Emergency'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('acknowledged', 'Acknowledged'),
        ('responding', 'Responding'),
        ('resolved', 'Resolved'),
        ('false_alarm', 'False Alarm'),
        ('cancelled', 'Cancelled'),
    ]
    
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='emergency_alerts'
    )
    ride = models.ForeignKey(
        Ride, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='emergency_alerts'
    )
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='high')
    
    # Location information
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    address = models.TextField(blank=True, null=True)
    
    # Alert details
    description = models.TextField(blank=True, null=True)
    audio_recording = models.FileField(
        upload_to='emergency/audio/', 
        blank=True, 
        null=True
    )
    photos = models.JSONField(default=list, blank=True)
    
    # Response information
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='acknowledged_alerts'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_alerts'
    )
    resolution_notes = models.TextField(blank=True, null=True)
    
    # Escalation
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_level = models.IntegerField(default=1)
    
    # External services
    police_notified = models.BooleanField(default=False)
    police_case_number = models.CharField(max_length=50, blank=True, null=True)
    medical_services_notified = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'emergency_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'severity']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ride']),
        ]
    
    def __str__(self):
        return f"Emergency Alert - {self.alert_type} - {self.user.get_full_name()}"
    
    @property
    def is_active(self):
        return self.status in ['active', 'acknowledged', 'responding']
    
    @property
    def response_time(self):
        if self.acknowledged_at:
            return self.acknowledged_at - self.created_at
        return None


class SafetyCheck(BaseModel):
    """Model for safety check-ins during rides"""
    
    CHECK_TYPES = [
        ('automatic', 'Automatic Check'),
        ('manual', 'Manual Check'),
        ('scheduled', 'Scheduled Check'),
        ('emergency', 'Emergency Check'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('escalated', 'Escalated'),
    ]
    
    ride = models.ForeignKey(
        Ride, 
        on_delete=models.CASCADE, 
        related_name='safety_checks'
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='safety_checks'
    )
    check_type = models.CharField(max_length=20, choices=CHECK_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Check details
    scheduled_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    
    # Response
    is_safe = models.BooleanField(null=True, blank=True)
    response_message = models.TextField(blank=True, null=True)
    
    # Escalation
    escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'safety_checks'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['ride', 'status']),
            models.Index(fields=['scheduled_at']),
        ]
    
    def __str__(self):
        return f"Safety Check - {self.ride} - {self.check_type}"
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        # Handle case where scheduled_at might be None (data inconsistency)
        if not self.scheduled_at:
            return False
        return (
            self.status == 'pending' and 
            timezone.now() > self.scheduled_at
        )


class EmergencyResponse(BaseModel):
    """Model for tracking emergency response actions"""
    
    ACTION_TYPES = [
        ('contact_emergency_contacts', 'Contact Emergency Contacts'),
        ('notify_authorities', 'Notify Authorities'),
        ('dispatch_security', 'Dispatch Security'),
        ('track_location', 'Track Location'),
        ('call_user', 'Call User'),
        ('send_help', 'Send Help'),
        ('escalate', 'Escalate'),
        ('close_case', 'Close Case'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    alert = models.ForeignKey(
        EmergencyAlert, 
        on_delete=models.CASCADE, 
        related_name='responses'
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Action details
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_responses'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    success = models.BooleanField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    contact_attempts = models.IntegerField(default=0)
    
    class Meta:
        db_table = 'emergency_responses'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert', 'status']),
            models.Index(fields=['assigned_to']),
        ]
    
    def __str__(self):
        return f"Response - {self.action_type} - {self.alert}"


class EmergencySettings(BaseModel):
    """Model for emergency system configuration"""
    
    # Check-in intervals (in minutes)
    safety_check_interval = models.IntegerField(default=15)
    emergency_check_interval = models.IntegerField(default=5)
    
    # Escalation timeouts (in minutes)
    first_escalation_timeout = models.IntegerField(default=2)
    second_escalation_timeout = models.IntegerField(default=5)
    authority_notification_timeout = models.IntegerField(default=10)
    
    # Contact settings
    max_contact_attempts = models.IntegerField(default=3)
    contact_retry_interval = models.IntegerField(default=1)
    
    # Emergency services
    police_number = models.CharField(max_length=20, default='911')
    medical_number = models.CharField(max_length=20, default='911')
    fire_number = models.CharField(max_length=20, default='911')
    
    # Geofencing
    safe_zone_radius = models.IntegerField(default=1000)  # meters
    danger_zone_enabled = models.BooleanField(default=True)
    
    # Notifications
    notify_emergency_contacts = models.BooleanField(default=True)
    notify_platform_admin = models.BooleanField(default=True)
    auto_call_authorities = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'emergency_settings'
        verbose_name = 'Emergency Settings'
        verbose_name_plural = 'Emergency Settings'
    
    def __str__(self):
        return "Emergency System Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create emergency settings"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings


class LocationShare(BaseModel):
    """Model for real-time location sharing during emergencies"""
    
    SHARE_TYPES = [
        ('emergency', 'Emergency Share'),
        ('ride', 'Ride Share'),
        ('manual', 'Manual Share'),
    ]
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='location_shares'
    )
    alert = models.ForeignKey(
        EmergencyAlert, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='location_shares'
    )
    ride = models.ForeignKey(
        Ride, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='location_shares'
    )
    
    share_type = models.CharField(max_length=20, choices=SHARE_TYPES)
    is_active = models.BooleanField(default=True)
    
    # Sharing details
    shared_with = models.ManyToManyField(
        User, 
        related_name='received_location_shares',
        blank=True
    )
    share_token = models.UUIDField(default=uuid.uuid4, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Location data
    current_latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8,
        null=True, 
        blank=True
    )
    current_longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8,
        null=True, 
        blank=True
    )
    last_update = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'location_shares'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['share_token']),
        ]
    
    def __str__(self):
        return f"Location Share - {self.user.get_full_name()} - {self.share_type}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return (
            self.expires_at and 
            timezone.now() > self.expires_at
        )
