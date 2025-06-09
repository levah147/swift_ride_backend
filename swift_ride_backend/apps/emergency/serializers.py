from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.emergency.models import (
    EmergencyContact, EmergencyAlert, SafetyCheck, 
    EmergencyResponse, LocationShare, EmergencySettings
)
from apps.users.serializers import UserBasicSerializer

User = get_user_model()


class EmergencyContactSerializer(serializers.ModelSerializer):
    """Serializer for emergency contacts"""
    
    class Meta:
        model = EmergencyContact
        fields = [
            'id', 'name', 'phone_number', 'email', 'relationship',
            'is_primary', 'is_active', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_phone_number(self, value):
        """Validate phone number format"""
        import re
        pattern = r'^\+?1?\d{9,15}$'
        if not re.match(pattern, value):
            raise serializers.ValidationError(
                "Phone number must be in format: '+999999999'. Up to 15 digits allowed."
            )
        return value
    
    def create(self, validated_data):
        """Create emergency contact"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class EmergencyAlertSerializer(serializers.ModelSerializer):
    """Serializer for emergency alerts"""
    
    user = UserBasicSerializer(read_only=True)
    acknowledged_by = UserBasicSerializer(read_only=True)
    resolved_by = UserBasicSerializer(read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    response_time = serializers.DurationField(read_only=True)
    
    class Meta:
        model = EmergencyAlert
        fields = [
            'id', 'user', 'ride', 'alert_type', 'alert_type_display',
            'status', 'status_display', 'severity', 'severity_display',
            'latitude', 'longitude', 'address', 'description',
            'audio_recording', 'photos', 'acknowledged_at', 'acknowledged_by',
            'resolved_at', 'resolved_by', 'resolution_notes', 'escalated',
            'escalated_at', 'escalation_level', 'police_notified',
            'police_case_number', 'medical_services_notified',
            'is_active', 'response_time', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'acknowledged_at', 'acknowledged_by',
            'resolved_at', 'resolved_by', 'escalated', 'escalated_at',
            'created_at', 'updated_at'
        ]


class EmergencyAlertCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating emergency alerts"""
    
    class Meta:
        model = EmergencyAlert
        fields = [
            'ride', 'alert_type', 'severity', 'latitude', 'longitude',
            'address', 'description', 'audio_recording', 'photos'
        ]
    
    def create(self, validated_data):
        """Create emergency alert"""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class SafetyCheckSerializer(serializers.ModelSerializer):
    """Serializer for safety checks"""
    
    user = UserBasicSerializer(read_only=True)
    check_type_display = serializers.CharField(source='get_check_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = SafetyCheck
        fields = [
            'id', 'ride', 'user', 'check_type', 'check_type_display',
            'status', 'status_display', 'scheduled_at', 'completed_at',
            'latitude', 'longitude', 'is_safe', 'response_message',
            'escalated', 'escalated_at', 'is_overdue', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'ride', 'user', 'check_type', 'scheduled_at',
            'escalated', 'escalated_at', 'created_at', 'updated_at'
        ]


class SafetyCheckResponseSerializer(serializers.Serializer):
    """Serializer for safety check responses"""
    
    is_safe = serializers.BooleanField()
    response_message = serializers.CharField(required=False, allow_blank=True)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)


class EmergencyResponseSerializer(serializers.ModelSerializer):
    """Serializer for emergency responses"""
    
    alert = EmergencyAlertSerializer(read_only=True)
    assigned_to = UserBasicSerializer(read_only=True)
    action_type_display = serializers.CharField(source='get_action_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = EmergencyResponse
        fields = [
            'id', 'alert', 'action_type', 'action_type_display',
            'status', 'status_display', 'assigned_to', 'started_at',
            'completed_at', 'success', 'notes', 'contact_attempts',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'alert', 'action_type', 'created_at', 'updated_at'
        ]


class LocationShareSerializer(serializers.ModelSerializer):
    """Serializer for location sharing"""
    
    user = UserBasicSerializer(read_only=True)
    shared_with = UserBasicSerializer(many=True, read_only=True)
    share_type_display = serializers.CharField(source='get_share_type_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = LocationShare
        fields = [
            'id', 'user', 'alert', 'ride', 'share_type', 'share_type_display',
            'is_active', 'shared_with', 'share_token', 'expires_at',
            'current_latitude', 'current_longitude', 'last_update',
            'is_expired', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'share_token', 'created_at', 'updated_at'
        ]


class LocationUpdateSerializer(serializers.Serializer):
    """Serializer for location updates"""
    
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)


class EmergencySettingsSerializer(serializers.ModelSerializer):
    """Serializer for emergency settings"""
    
    class Meta:
        model = EmergencySettings
        fields = [
            'id', 'safety_check_interval', 'emergency_check_interval',
            'first_escalation_timeout', 'second_escalation_timeout',
            'authority_notification_timeout', 'max_contact_attempts',
            'contact_retry_interval', 'police_number', 'medical_number',
            'fire_number', 'safe_zone_radius', 'danger_zone_enabled',
            'notify_emergency_contacts', 'notify_platform_admin',
            'auto_call_authorities', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PanicButtonSerializer(serializers.Serializer):
    """Serializer for panic button activation"""
    
    ride_id = serializers.UUIDField(required=False)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
    address = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    audio_recording = serializers.FileField(required=False)


class EmergencyStatsSerializer(serializers.Serializer):
    """Serializer for emergency statistics"""
    
    total_alerts = serializers.IntegerField()
    active_alerts = serializers.IntegerField()
    resolved_alerts = serializers.IntegerField()
    false_alarms = serializers.IntegerField()
    average_response_time = serializers.DurationField()
    alerts_by_type = serializers.DictField()
    alerts_by_severity = serializers.DictField()
    monthly_trend = serializers.ListField()
