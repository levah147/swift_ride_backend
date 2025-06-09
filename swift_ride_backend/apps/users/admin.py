"""
Admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, RiderProfile, DriverProfile, UserPreferences


class CustomUserAdmin(UserAdmin):
    """
    Custom admin for CustomUser model.
    """
    list_display = ('phone_number', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_verified')
    list_filter = ('user_type', 'is_active', 'is_verified', 'is_staff')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name')
    ordering = ('phone_number',)
    
    # Add readonly_fields to make date_joined non-editable
    readonly_fields = ('date_joined', 'last_login')
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('User type'), {'fields': ('user_type',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        # Make Important dates read-only by removing date_joined from editable fields
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'user_type'),
        }),
    )
    
    # Override the username field since you're using phone_number
    USERNAME_FIELD = 'phone_number'
    
    # Add filter_horizontal for better UI on many-to-many fields
    filter_horizontal = ('groups', 'user_permissions')


class RiderProfileAdmin(admin.ModelAdmin):
    """
    Admin for RiderProfile model.
    """
    list_display = ('user', 'emergency_contact_name', 'emergency_contact_number')
    search_fields = ('user__phone_number', 'user__email', 'emergency_contact_name')
    raw_id_fields = ('user',)  # Better performance for foreign key lookups


class DriverProfileAdmin(admin.ModelAdmin):
    """
    Admin for DriverProfile model.
    """
    list_display = ('user', 'license_number', 'verification_status', 'is_online', 'is_available', 'average_rating')
    list_filter = ('verification_status', 'is_online', 'is_available')
    search_fields = ('user__phone_number', 'user__email', 'license_number')
    raw_id_fields = ('user',)  # Better performance for foreign key lookups
    
    # Add readonly fields if these are calculated fields
    readonly_fields = ('average_rating',) if hasattr(DriverProfile, 'average_rating') else ()


class UserPreferencesAdmin(admin.ModelAdmin):
    """
    Admin for UserPreferences model.
    """
    list_display = ('user', 'language', 'dark_mode', 'push_notifications', 'email_notifications', 'sms_notifications')
    list_filter = ('language', 'dark_mode', 'push_notifications', 'email_notifications', 'sms_notifications')
    search_fields = ('user__phone_number', 'user__email')
    raw_id_fields = ('user',)  # Better performance for foreign key lookups


# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(RiderProfile, RiderProfileAdmin)
admin.site.register(DriverProfile, DriverProfileAdmin)
admin.site.register(UserPreferences, UserPreferencesAdmin)