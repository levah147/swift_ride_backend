"""
Serializers for notification models.
"""

from rest_framework import serializers

from apps.notifications.models import (
    Notification, NotificationTemplate, NotificationPreference,
    DeviceToken, NotificationBatch
)
from apps.users.serializers import UserSerializer

 
class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationTemplate model.
    """
    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'notification_type', 'channel', 'title_template',
            'body_template', 'sms_template', 'email_subject_template',
            'email_html_template', 'push_sound', 'push_badge_count',
            'push_category', 'variables', 'is_active', 'priority'
        ]


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model.
    """
    recipient = UserSerializer(read_only=True)
    template = NotificationTemplateSerializer(read_only=True)
    time_ago = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'template', 'title', 'body', 'data',
            'status', 'priority', 'sent_at', 'delivered_at', 'read_at',
            'scheduled_at', 'expires_at', 'ride', 'message', 'time_ago',
            'created_at'
        ]
        read_only_fields = [
            'id', 'recipient', 'template', 'status', 'sent_at', 'delivered_at',
            'read_at', 'created_at'
        ]
    
    def get_time_ago(self, obj):
        """Get human-readable time ago."""
        from django.utils import timezone
        from datetime import timedelta
        
        now = timezone.now()
        diff = now - obj.created_at
        
        if diff < timedelta(minutes=1):
            return "Just now"
        elif diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff < timedelta(days=7):
            days = diff.days
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            return obj.created_at.strftime('%Y-%m-%d')


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationPreference model.
    """
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'push_enabled', 'push_ride_updates', 'push_messages',
            'push_payments', 'push_promotions', 'push_system_updates',
            'sms_enabled', 'sms_ride_updates', 'sms_emergency_only',
            'sms_verification', 'email_enabled', 'email_ride_receipts',
            'email_weekly_summary', 'email_promotions', 'email_system_updates',
            'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end',
            'language'
        ]
        read_only_fields = ['id']


class DeviceTokenSerializer(serializers.ModelSerializer):
    """
    Serializer for DeviceToken model.
    """
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'token', 'platform', 'device_id', 'device_name',
            'app_version', 'is_active', 'last_used', 'created_at'
        ]
        read_only_fields = ['id', 'last_used', 'created_at']


class DeviceTokenCreateSerializer(serializers.Serializer):
    """
    Serializer for creating device tokens.
    """
    token = serializers.CharField(max_length=500)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices)
    device_id = serializers.CharField(max_length=255, required=False)
    device_name = serializers.CharField(max_length=100, required=False)
    app_version = serializers.CharField(max_length=20, required=False)


class NotificationBatchSerializer(serializers.ModelSerializer):
    """
    Serializer for NotificationBatch model.
    """
    template = NotificationTemplateSerializer(read_only=True)
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    
    class Meta:
        model = NotificationBatch
        fields = [
            'id', 'name', 'template', 'recipient_count', 'sent_count',
            'failed_count', 'status', 'success_rate', 'scheduled_at',
            'started_at', 'completed_at', 'context', 'filters', 'created_at'
        ]
        read_only_fields = [
            'id', 'sent_count', 'failed_count', 'status', 'started_at',
            'completed_at', 'created_at'
        ]


class BulkNotificationSerializer(serializers.Serializer):
    """
    Serializer for sending bulk notifications.
    """
    notification_type = serializers.ChoiceField(
        choices=NotificationTemplate.NotificationType.choices
    )
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    channels = serializers.MultipleChoiceField(
        choices=NotificationTemplate.Channel.choices,
        default=[NotificationTemplate.Channel.PUSH]
    )
    recipient_filters = serializers.JSONField(default=dict)
    scheduled_at = serializers.DateTimeField(required=False)
    context = serializers.JSONField(default=dict)
