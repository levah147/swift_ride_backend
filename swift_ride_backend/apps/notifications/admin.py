"""
Admin configuration for notification models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.notifications.models import (
    NotificationTemplate, Notification, NotificationPreference,
    DeviceToken, NotificationBatch, NotificationLog, NotificationAnalytics
)
 

@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    Admin for NotificationTemplate model.
    """
    list_display = (
        'name', 'notification_type', 'channel', 'priority', 
        'is_active', 'created_at'
    )
    list_filter = ('notification_type', 'channel', 'priority', 'is_active')
    search_fields = ('name', 'title_template', 'body_template')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'notification_type', 'channel', 'priority', 'is_active')
        }),
        ('Content Templates', {
            'fields': ('title_template', 'body_template', 'variables')
        }),
        ('SMS Settings', {
            'fields': ('sms_template',),
            'classes': ('collapse',)
        }),
        ('Email Settings', {
            'fields': ('email_subject_template', 'email_html_template'),
            'classes': ('collapse',)
        }),
        ('Push Notification Settings', {
            'fields': ('push_sound', 'push_badge_count', 'push_category'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin for Notification model.
    """
    list_display = (
        'title', 'recipient', 'template', 'status', 'priority',
        'status_badge', 'created_at'
    )
    list_filter = ('status', 'priority', 'template__notification_type', 'created_at')
    search_fields = ('title', 'body', 'recipient__phone_number')
    readonly_fields = (
        'created_at', 'updated_at', 'sent_at', 'delivered_at', 
        'read_at', 'failed_at'
    )
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': 'orange',
            'sent': 'blue',
            'delivered': 'green',
            'read': 'darkgreen',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('recipient', 'template', 'title', 'body')
        }),
        ('Status & Priority', {
            'fields': ('status', 'priority', 'failure_reason')
        }),
        ('Scheduling', {
            'fields': ('scheduled_at', 'expires_at')
        }),
        ('Delivery Tracking', {
            'fields': ('sent_at', 'delivered_at', 'read_at', 'failed_at'),
            'classes': ('collapse',)
        }),
        ('Related Objects', {
            'fields': ('ride', 'message'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('data', 'context'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Admin for NotificationPreference model.
    """
    list_display = (
        'user', 'push_enabled', 'sms_enabled', 'email_enabled',
        'quiet_hours_enabled', 'language'
    )
    list_filter = (
        'push_enabled', 'sms_enabled', 'email_enabled', 
        'quiet_hours_enabled', 'language'
    )
    search_fields = ('user__phone_number',)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Push Notifications', {
            'fields': (
                'push_enabled', 'push_ride_updates', 'push_messages',
                'push_payments', 'push_promotions', 'push_system_updates'
            )
        }),
        ('SMS Notifications', {
            'fields': (
                'sms_enabled', 'sms_ride_updates', 'sms_emergency_only',
                'sms_verification'
            )
        }),
        ('Email Notifications', {
            'fields': (
                'email_enabled', 'email_ride_receipts', 'email_weekly_summary',
                'email_promotions', 'email_system_updates'
            )
        }),
        ('Quiet Hours', {
            'fields': (
                'quiet_hours_enabled', 'quiet_hours_start', 'quiet_hours_end'
            )
        }),
        ('Other Settings', {
            'fields': ('language',)
        }),
    )


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    """
    Admin for DeviceToken model.
    """
    list_display = (
        'user', 'platform', 'device_name', 'is_active', 
        'last_used', 'created_at'
    )
    list_filter = ('platform', 'is_active', 'created_at')
    search_fields = ('user__phone_number', 'device_name', 'device_id')
    readonly_fields = ('created_at', 'updated_at', 'last_used')
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')


@admin.register(NotificationBatch)
class NotificationBatchAdmin(admin.ModelAdmin):
    """
    Admin for NotificationBatch model.
    """
    list_display = (
        'name', 'template', 'status', 'recipient_count',
        'sent_count', 'failed_count', 'success_rate_display',
        'scheduled_at'
    )
    list_filter = ('status', 'template__notification_type', 'scheduled_at')
    search_fields = ('name',)
    readonly_fields = (
        'created_at', 'updated_at', 'started_at', 'completed_at',
        'success_rate'
    )
    
    def success_rate_display(self, obj):
        """Display success rate with color coding."""
        rate = obj.success_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
            color,
            rate
        )
    
    success_rate_display.short_description = 'Success Rate'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    """
    Admin for NotificationLog model.
    """
    list_display = (
        'notification', 'channel', 'provider', 'success',
        'response_code', 'sent_at'
    )
    list_filter = ('channel', 'provider', 'success', 'sent_at')
    search_fields = ('notification__title', 'provider_message_id')
    readonly_fields = ('sent_at',)
    date_hierarchy = 'sent_at'


@admin.register(NotificationAnalytics)
class NotificationAnalyticsAdmin(admin.ModelAdmin):
    """
    Admin for NotificationAnalytics model.
    """
    list_display = (
        'date', 'template', 'channel', 'sent_count',
        'delivered_count', 'read_count', 'delivery_rate',
        'read_rate'
    )
    list_filter = ('date', 'template__notification_type', 'channel')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
