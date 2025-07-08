"""
Admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, RiderProfile, DriverProfile, UserPreferences, UserProfile, UserDocument


class CustomUserAdmin(UserAdmin):
    """
    Custom admin for CustomUser model.
    """
    list_display = ('phone_number', 'email', 'first_name', 'last_name', 'user_type', 'is_active', 'is_verified')
    list_filter = ('user_type', 'is_active', 'is_verified', 'is_staff')
    search_fields = ('phone_number', 'email', 'first_name', 'last_name')
    ordering = ('phone_number',)
    
    fieldsets = (
        (None, {'fields': ('phone_number', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('User type'), {'fields': ('user_type',)}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone_number', 'password1', 'password2', 'user_type'),
        }),
    )


class RiderProfileAdmin(admin.ModelAdmin):
    """
    Admin for RiderProfile model.
    """
    list_display = ('user', 'emergency_contact_name', 'emergency_contact_number')
    search_fields = ('user__phone_number', 'user__email', 'emergency_contact_name')


class DriverProfileAdmin(admin.ModelAdmin):
    """
    Admin for DriverProfile model.
    """
    list_display = ('user', 'license_number', 'verification_status', 'is_online', 'is_available', 'average_rating')
    list_filter = ('verification_status', 'is_online', 'is_available')
    search_fields = ('user__phone_number', 'user__email', 'license_number')


class UserPreferencesAdmin(admin.ModelAdmin):
    """
    Admin for UserPreferences model.
    """
    list_display = ('user', 'language', 'dark_mode', 'push_notifications', 'email_notifications', 'sms_notifications')
    list_filter = ('language', 'dark_mode', 'push_notifications', 'email_notifications', 'sms_notifications')
    search_fields = ('user__phone_number', 'user__email')


class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for UserProfile model.
    """
    list_display = ('user', 'city', 'state', 'country', 'date_of_birth')
    search_fields = ('user__phone_number', 'user__email', 'city', 'state')
    list_filter = ('gender', 'country', 'state')


class UserDocumentAdmin(admin.ModelAdmin):
    """
    Admin for UserDocument model.
    """
    list_display = ('user', 'document_type', 'document_number', 'verification_status', 'verified_at')
    list_filter = ('document_type', 'verification_status')
    search_fields = ('user__phone_number', 'user__email', 'document_number')
    readonly_fields = ('verified_at',)


# Register models
admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(RiderProfile, RiderProfileAdmin)
admin.site.register(DriverProfile, DriverProfileAdmin)
admin.site.register(UserPreferences, UserPreferencesAdmin)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(UserDocument, UserDocumentAdmin)
