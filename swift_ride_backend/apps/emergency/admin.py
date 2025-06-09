from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from apps.emergency.models import (
    EmergencyContact, EmergencyAlert, SafetyCheck, 
    EmergencyResponse, LocationShare, EmergencySettings
)


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'user', 'phone_number', 'relationship', 
        'is_primary', 'is_active', 'created_at'
    ]
    list_filter = ['relationship', 'is_primary', 'is_active', 'created_at']
    search_fields = ['name', 'phone_number', 'user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('user', 'name', 'phone_number', 'email')
        }),
        ('Relationship', {
            'fields': ('relationship', 'is_primary', 'notes')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(EmergencyAlert)
class EmergencyAlertAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'alert_type', 'severity', 'status', 
        'status_badge', 'created_at', 'response_time_display'
    ]
    list_filter = [
        'alert_type', 'severity', 'status', 'escalated', 
        'police_notified', 'medical_services_notified', 'created_at'
    ]
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name',
        'description', 'address'
    ]
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'response_time_display',
        'location_link'
    ]
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('id', 'user', 'ride', 'alert_type', 'severity', 'status')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'address', 'location_link')
        }),
        ('Details', {
            'fields': ('description', 'audio_recording', 'photos')
        }),
        ('Response', {
            'fields': (
                'acknowledged_at', 'acknowledged_by', 'resolved_at', 
                'resolved_by', 'resolution_notes', 'response_time_display'
            )
        }),
        ('Escalation', {
            'fields': ('escalated', 'escalated_at', 'escalation_level')
        }),
        ('External Services', {
            'fields': (
                'police_notified', 'police_case_number', 
                'medical_services_notified'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        colors = {
            'active': 'red',
            'acknowledged': 'orange',
            'responding': 'blue',
            'resolved': 'green',
            'false_alarm': 'gray',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def response_time_display(self, obj):
        if obj.response_time:
            total_seconds = int(obj.response_time.total_seconds())
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        return "N/A"
    response_time_display.short_description = 'Response Time'
    
    def location_link(self, obj):
        if obj.latitude and obj.longitude:
            url = f"https://maps.google.com/?q={obj.latitude},{obj.longitude}"
            return format_html('<a href="{}" target="_blank">View on Map</a>', url)
        return "No location"
    location_link.short_description = 'Location'


@admin.register(SafetyCheck)
class SafetyCheckAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'ride', 'check_type', 'status', 
        'scheduled_at', 'completed_at', 'is_safe', 'escalated', 'is_overdue_display',  # This should match the method name below
    ]
    list_filter = [
        'check_type', 'status', 'is_safe', 'escalated', 
        'scheduled_at', 'completed_at'
    ]
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name',
        'ride__id', 'response_message'
    ]
    readonly_fields = ['created_at', 'updated_at', 'is_overdue_display']
    
    fieldsets = (
        ('Check Information', {
            'fields': ('ride', 'user', 'check_type', 'status')
        }),
        ('Schedule', {
            'fields': ('scheduled_at', 'completed_at', 'is_overdue_display')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Response', {
            'fields': ('is_safe', 'response_message')
        }),
        ('Escalation', {
            'fields': ('escalated', 'escalated_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_overdue_display(self, obj):
        """Display method for overdue status with error handling"""
        try:
            if obj.is_overdue:
                return format_html('<span style="color: red; font-weight: bold;">OVERDUE</span>')
            return "No"
        except (TypeError, AttributeError) as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error checking overdue status for SafetyCheck {obj.id}: {e}")
            return format_html('<span style="color: orange;">Error</span>')
    
    is_overdue_display.short_description = 'Overdue' 
    # def is_overdue_display(self, obj):
    #     if obj.is_overdue:
    #         return format_html('<span style="color: red; font-weight: bold;">OVERDUE</span>')
    #     return "No"
    # is_overdue_display.short_description = 'Overdue'


@admin.register(EmergencyResponse)
class EmergencyResponseAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'alert', 'action_type', 'status', 'assigned_to',
        'started_at', 'completed_at', 'success'
    ]
    list_filter = [
        'action_type', 'status', 'success', 'started_at', 'completed_at'
    ]
    search_fields = [
        'alert__user__phone_number', 'alert__user__first_name',
        'alert__user__last_name', 'assigned_to__first_name',
        'assigned_to__last_name', 'notes'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Response Information', {
            'fields': ('alert', 'action_type', 'status', 'assigned_to')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Results', {
            'fields': ('success', 'notes', 'contact_attempts')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(LocationShare)
class LocationShareAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'share_type', 'is_active', 'expires_at',
        'last_update', 'shared_with_count'
    ]
    list_filter = [
        'share_type', 'is_active', 'expires_at', 'last_update'
    ]
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name',
        'share_token'
    ]
    readonly_fields = [
        'share_token', 'created_at', 'updated_at', 'is_expired_display'
    ]
    
    fieldsets = (
        ('Share Information', {
            'fields': ('user', 'alert', 'ride', 'share_type', 'is_active')
        }),
        ('Sharing Details', {
            'fields': ('shared_with', 'share_token', 'expires_at', 'is_expired_display')
        }),
        ('Location', {
            'fields': ('current_latitude', 'current_longitude', 'last_update')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def shared_with_count(self, obj):
        return obj.shared_with.count()
    shared_with_count.short_description = 'Shared With'
    
    def is_expired_display(self, obj):
        if obj.is_expired:
            return format_html('<span style="color: red;">EXPIRED</span>')
        return "Active"
    is_expired_display.short_description = 'Expired'


@admin.register(EmergencySettings)
class EmergencySettingsAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'safety_check_interval', 'emergency_check_interval',
        'notify_emergency_contacts', 'auto_call_authorities'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Check Intervals (minutes)', {
            'fields': ('safety_check_interval', 'emergency_check_interval')
        }),
        ('Escalation Timeouts (minutes)', {
            'fields': (
                'first_escalation_timeout', 'second_escalation_timeout',
                'authority_notification_timeout'
            )
        }),
        ('Contact Settings', {
            'fields': ('max_contact_attempts', 'contact_retry_interval')
        }),
        ('Emergency Numbers', {
            'fields': ('police_number', 'medical_number', 'fire_number')
        }),
        ('Geofencing', {
            'fields': ('safe_zone_radius', 'danger_zone_enabled')
        }),
        ('Notifications', {
            'fields': (
                'notify_emergency_contacts', 'notify_platform_admin',
                'auto_call_authorities'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not EmergencySettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
