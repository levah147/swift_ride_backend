"""
Notification models for Swift Ride project.
"""

import json
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from apps.common.models import BaseModel, SoftDeleteModel


class NotificationTemplate(BaseModel):
    """
    Model for notification templates.
    """
    class NotificationType(models.TextChoices):
        RIDE_REQUEST = 'ride_request', _('Ride Request')
        RIDE_ACCEPTED = 'ride_accepted', _('Ride Accepted')
        RIDE_STARTED = 'ride_started', _('Ride Started')
        RIDE_COMPLETED = 'ride_completed', _('Ride Completed')
        RIDE_CANCELLED = 'ride_cancelled', _('Ride Cancelled')
        DRIVER_ARRIVED = 'driver_arrived', _('Driver Arrived')
        PAYMENT_RECEIVED = 'payment_received', _('Payment Received')
        PAYMENT_FAILED = 'payment_failed', _('Payment Failed')
        NEW_MESSAGE = 'new_message', _('New Message')
        VOICE_MESSAGE = 'voice_message', _('Voice Message')
        DOCUMENT_VERIFIED = 'document_verified', _('Document Verified')
        DOCUMENT_REJECTED = 'document_rejected', _('Document Rejected')
        VEHICLE_APPROVED = 'vehicle_approved', _('Vehicle Approved')
        VEHICLE_SUSPENDED = 'vehicle_suspended', _('Vehicle Suspended')
        EMERGENCY_ALERT = 'emergency_alert', _('Emergency Alert')
        MAINTENANCE_REMINDER = 'maintenance_reminder', _('Maintenance Reminder')
        INSURANCE_EXPIRY = 'insurance_expiry', _('Insurance Expiry')
        PROMOTION = 'promotion', _('Promotion')
        SYSTEM_UPDATE = 'system_update', _('System Update')
    
    class Channel(models.TextChoices):
        PUSH = 'push', _('Push Notification')
        SMS = 'sms', _('SMS')
        EMAIL = 'email', _('Email')
        IN_APP = 'in_app', _('In-App Notification')
    
    name = models.CharField(max_length=100)
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        unique=True
    )
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices
    )
    
    # Template content
    title_template = models.CharField(max_length=200)
    body_template = models.TextField()
    
    # SMS specific
    sms_template = models.TextField(blank=True, null=True)
    
    # Email specific
    email_subject_template = models.CharField(max_length=200, blank=True, null=True)
    email_html_template = models.TextField(blank=True, null=True)
    
    # Push notification specific
    push_sound = models.CharField(max_length=50, default='default')
    push_badge_count = models.BooleanField(default=True)
    push_category = models.CharField(max_length=50, blank=True, null=True)
    
    # Metadata
    variables = models.JSONField(default=list, help_text="List of template variables")
    is_active = models.BooleanField(default=True)
    priority = models.IntegerField(default=1, help_text="1=Low, 2=Normal, 3=High, 4=Critical")
    
    def __str__(self):
        return f"{self.name} ({self.channel})"
    
    def render_title(self, context):
        """Render title template with context."""
        return self._render_template(self.title_template, context)
    
    def render_body(self, context):
        """Render body template with context."""
        return self._render_template(self.body_template, context)
    
    def render_sms(self, context):
        """Render SMS template with context."""
        if self.sms_template:
            return self._render_template(self.sms_template, context)
        return self.render_body(context)
    
    def render_email_subject(self, context):
        """Render email subject template with context."""
        if self.email_subject_template:
            return self._render_template(self.email_subject_template, context)
        return self.render_title(context)
    
    def render_email_body(self, context):
        """Render email body template with context."""
        if self.email_html_template:
            return self._render_template(self.email_html_template, context)
        return self.render_body(context)
    
    def _render_template(self, template, context):
        """Render template with context variables."""
        try:
            # Simple template rendering (in production, use Django templates or Jinja2)
            rendered = template
            for key, value in context.items():
                rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
            return rendered
        except Exception:
            return template
    
    class Meta:
        ordering = ['name']


class DeviceToken(BaseModel):
    """
    Model for storing device tokens for push notifications.
    """
    class Platform(models.TextChoices):
        IOS = 'ios', _('iOS')
        ANDROID = 'android', _('Android')
        WEB = 'web', _('Web')
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens'
    )
    token = models.TextField(unique=True)
    platform = models.CharField(
        max_length=10,
        choices=Platform.choices
    )
    device_id = models.CharField(max_length=255, blank=True, null=True)
    device_name = models.CharField(max_length=100, blank=True, null=True)
    app_version = models.CharField(max_length=20, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user} - {self.platform} - {self.device_name or 'Unknown'}"
    
    class Meta:
        unique_together = ['user', 'token']
        ordering = ['-last_used']


class Notification(BaseModel, SoftDeleteModel):
    """
    Model for storing notifications.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        SENT = 'sent', _('Sent')
        DELIVERED = 'delivered', _('Delivered')
        READ = 'read', _('Read')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    class Priority(models.IntegerChoices):
        LOW = 1, _('Low')
        NORMAL = 2, _('Normal')
        HIGH = 3, _('High')
        CRITICAL = 4, _('Critical')
    
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    # Content
    title = models.CharField(max_length=200)
    body = models.TextField()
    
    # Metadata
    data = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)
    
    # Status tracking
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    priority = models.IntegerField(
        choices=Priority.choices,
        default=Priority.NORMAL
    )
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    # Scheduling
    scheduled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    message = models.ForeignKey(
        'chat.Message',
        on_delete=models.CASCADE,
        related_name='notifications',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"{self.title} - {self.recipient}"
    
    def mark_as_sent(self):
        """Mark notification as sent."""
        self.status = self.Status.SENT
        self.sent_at = models.functions.Now()
        self.save(update_fields=['status', 'sent_at'])
    
    def mark_as_delivered(self):
        """Mark notification as delivered."""
        self.status = self.Status.DELIVERED
        self.delivered_at = models.functions.Now()
        self.save(update_fields=['status', 'delivered_at'])
    
    def mark_as_read(self):
        """Mark notification as read."""
        self.status = self.Status.READ
        self.read_at = models.functions.Now()
        self.save(update_fields=['status', 'read_at'])
    
    def mark_as_failed(self, reason):
        """Mark notification as failed."""
        self.status = self.Status.FAILED
        self.failed_at = models.functions.Now()
        self.failure_reason = reason
        self.save(update_fields=['status', 'failed_at', 'failure_reason'])
    
    @property
    def is_expired(self):
        """Check if notification is expired."""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'status']),
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['template', 'created_at']),
        ]


class NotificationPreference(BaseModel):
    """
    Model for user notification preferences.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preferences'
    )
    
    # Push notification preferences
    push_enabled = models.BooleanField(default=True)
    push_ride_updates = models.BooleanField(default=True)
    push_messages = models.BooleanField(default=True)
    push_payments = models.BooleanField(default=True)
    push_promotions = models.BooleanField(default=False)
    push_system_updates = models.BooleanField(default=True)
    
    # SMS preferences
    sms_enabled = models.BooleanField(default=True)
    sms_ride_updates = models.BooleanField(default=True)
    sms_emergency_only = models.BooleanField(default=False)
    sms_verification = models.BooleanField(default=True)
    
    # Email preferences
    email_enabled = models.BooleanField(default=True)
    email_ride_receipts = models.BooleanField(default=True)
    email_weekly_summary = models.BooleanField(default=True)
    email_promotions = models.BooleanField(default=False)
    email_system_updates = models.BooleanField(default=True)
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(default='22:00')
    quiet_hours_end = models.TimeField(default='07:00')
    
    # Language preference
    language = models.CharField(max_length=10, default='en')
    
    def __str__(self):
        return f"Notification preferences for {self.user}"
    
    def is_quiet_time(self):
        """Check if current time is within quiet hours."""
        if not self.quiet_hours_enabled:
            return False
        
        from django.utils import timezone
        now = timezone.now().time()
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            # Same day quiet hours (e.g., 22:00 to 23:59)
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:
            # Overnight quiet hours (e.g., 22:00 to 07:00)
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end
    
    def should_send_notification(self, notification_type, channel):
        """Check if notification should be sent based on preferences."""
        # Check if channel is enabled
        if channel == NotificationTemplate.Channel.PUSH and not self.push_enabled:
            return False
        elif channel == NotificationTemplate.Channel.SMS and not self.sms_enabled:
            return False
        elif channel == NotificationTemplate.Channel.EMAIL and not self.email_enabled:
            return False
        
        # Check specific notification type preferences
        if channel == NotificationTemplate.Channel.PUSH:
            if notification_type in ['ride_request', 'ride_accepted', 'ride_started', 'ride_completed', 'ride_cancelled', 'driver_arrived']:
                return self.push_ride_updates
            elif notification_type in ['new_message', 'voice_message']:
                return self.push_messages
            elif notification_type in ['payment_received', 'payment_failed']:
                return self.push_payments
            elif notification_type == 'promotion':
                return self.push_promotions
            elif notification_type == 'system_update':
                return self.push_system_updates
        
        elif channel == NotificationTemplate.Channel.SMS:
            if notification_type in ['ride_request', 'ride_accepted', 'ride_started', 'ride_completed', 'ride_cancelled']:
                return self.sms_ride_updates
            elif notification_type == 'emergency_alert':
                return True  # Always send emergency alerts
            elif self.sms_emergency_only:
                return notification_type == 'emergency_alert'
        
        elif channel == NotificationTemplate.Channel.EMAIL:
            if notification_type in ['payment_received', 'ride_completed']:
                return self.email_ride_receipts
            elif notification_type == 'promotion':
                return self.email_promotions
            elif notification_type == 'system_update':
                return self.email_system_updates
        
        return True


class NotificationBatch(BaseModel):
    """
    Model for batch notifications.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    name = models.CharField(max_length=100)
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='batches'
    )
    
    # Recipients
    recipient_count = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Scheduling
    scheduled_at = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Content
    context = models.JSONField(default=dict)
    filters = models.JSONField(default=dict, help_text="User filters for targeting")
    
    def __str__(self):
        return f"Batch: {self.name}"
    
    @property
    def success_rate(self):
        """Calculate success rate."""
        if self.recipient_count == 0:
            return 0
        return (self.sent_count / self.recipient_count) * 100
    
    class Meta:
        ordering = ['-created_at']


class NotificationLog(BaseModel):
    """
    Model for logging notification delivery attempts.
    """
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    channel = models.CharField(
        max_length=10,
        choices=NotificationTemplate.Channel.choices
    )
    
    # Delivery details
    provider = models.CharField(max_length=50, blank=True, null=True)  # FCM, Twilio, etc.
    provider_message_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Status
    success = models.BooleanField()
    response_code = models.CharField(max_length=10, blank=True, null=True)
    response_message = models.TextField(blank=True, null=True)
    
    # Timing
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_time_ms = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        status = "Success" if self.success else "Failed"
        return f"{self.notification.title} - {self.channel} - {status}"
    
    class Meta:
        ordering = ['-sent_at']


class NotificationAnalytics(BaseModel):
    """
    Model for notification analytics and metrics.
    """
    date = models.DateField()
    template = models.ForeignKey(
        NotificationTemplate,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    channel = models.CharField(
        max_length=10,
        choices=NotificationTemplate.Channel.choices
    )
    
    # Metrics
    sent_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    
    # Rates
    delivery_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    read_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Timing
    avg_delivery_time_ms = models.PositiveIntegerField(null=True, blank=True)
    avg_read_time_minutes = models.PositiveIntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Analytics: {self.template.name} - {self.date}"
    
    def calculate_rates(self):
        """Calculate delivery and read rates."""
        if self.sent_count > 0:
            self.delivery_rate = (self.delivered_count / self.sent_count) * 100
            self.read_rate = (self.read_count / self.sent_count) * 100
        else:
            self.delivery_rate = 0
            self.read_rate = 0
    
    class Meta:
        unique_together = ['date', 'template', 'channel']
        ordering = ['-date']
