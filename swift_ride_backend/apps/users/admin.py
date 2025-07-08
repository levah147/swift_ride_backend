"""
Admin configuration for user models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import CustomUser, RiderProfile, DriverProfile, UserPreferences, UserProfile


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


class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin for UserProfile model.
    """
    list_display = (
        'user', 
        'get_full_name', 
        'city', 
        'country', 
        'is_profile_complete', 
        'get_age',
        'emergency_contact_name'
    )
    list_filter = (
        'is_profile_complete', 
        'gender', 
        'country', 
        'city',
        'created_at'
    )
    search_fields = (
        'user__phone_number', 
        'user__email', 
        'user__first_name', 
        'user__last_name',
        'address',
        'city',
        'emergency_contact_name'
    )
    raw_id_fields = ('user',)  # Better performance for foreign key lookups
    
    readonly_fields = ('is_profile_complete', 'get_age', 'get_full_address')
    
    fieldsets = (
        (_('User Information'), {
            'fields': ('user',)
        }),
        (_('Profile Picture'), {
            'fields': ('profile_picture',)
        }),
        (_('Personal Information'), {
            'fields': ('bio', 'date_of_birth', 'gender', 'get_age'),
            'classes': ('collapse',)
        }),
        (_('Address Information'), {
            'fields': ('address', 'city', 'state', 'country', 'postal_code', 'get_full_address'),
            'classes': ('collapse',)
        }),
        (_('Emergency Contact'), {
            'fields': ('emergency_contact_name', 'emergency_contact_number'),
            'classes': ('collapse',)
        }),
        (_('Profile Status'), {
            'fields': ('is_profile_complete',),
        }),
    )
    
    # Add custom methods for display
    def get_full_name(self, obj):
        """Display user's full name in admin list."""
        return obj.user.get_full_name() or "No name"
    get_full_name.short_description = 'Full Name'
    get_full_name.admin_order_field = 'user__first_name'
    
    def get_age(self, obj):
        """Display user's age in admin."""
        age = obj.calculate_age()
        return f"{age} years" if age else "Not set"
    get_age.short_description = 'Age'
    
    def get_full_address(self, obj):
        """Display full address in admin."""
        return obj.get_full_address() or "No address"
    get_full_address.short_description = 'Full Address'
    
    # Add actions
    actions = ['mark_profile_complete', 'mark_profile_incomplete']
    
    def mark_profile_complete(self, request, queryset):
        """Admin action to mark profiles as complete."""
        updated = queryset.update(is_profile_complete=True)
        self.message_user(
            request,
            f'{updated} profile(s) marked as complete.'
        )
    mark_profile_complete.short_description = "Mark selected profiles as complete"
    
    def mark_profile_incomplete(self, request, queryset):
        """Admin action to mark profiles as incomplete."""
        updated = queryset.update(is_profile_complete=False)
        self.message_user(
            request,
            f'{updated} profile(s) marked as incomplete.'
        )
    mark_profile_incomplete.short_description = "Mark selected profiles as incomplete"


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
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(RiderProfile, RiderProfileAdmin)
admin.site.register(DriverProfile, DriverProfileAdmin)
admin.site.register(UserPreferences, UserPreferencesAdmin)