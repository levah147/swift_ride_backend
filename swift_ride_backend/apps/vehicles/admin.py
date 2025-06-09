"""
Admin configuration for vehicle models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.vehicles.models import (
    VehicleType, Vehicle, VehicleDocument, Insurance, 
    Inspection, VehicleMaintenanceRecord
)


class VehicleDocumentInline(admin.TabularInline):
    """
    Inline admin for VehicleDocument.
    """
    model = VehicleDocument
    extra = 0
    readonly_fields = ['verified_at', 'verified_by']


class InsuranceInline(admin.StackedInline):
    """
    Inline admin for Insurance.
    """
    model = Insurance
    can_delete = False


class InspectionInline(admin.TabularInline):
    """
    Inline admin for Inspection.
    """
    model = Inspection
    extra = 0
    readonly_fields = ['completed_date', 'inspector']


class VehicleMaintenanceRecordInline(admin.TabularInline):
    """
    Inline admin for VehicleMaintenanceRecord.
    """
    model = VehicleMaintenanceRecord
    extra = 0


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
    """
    Admin for VehicleType model.
    """
    list_display = ('name', 'base_fare', 'per_km_rate', 'capacity', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    """
    Admin for Vehicle model.
    """
    list_display = (
        'license_plate', 'owner', 'make', 'model', 'year', 
        'verification_status', 'is_active', 'created_at'
    )
    list_filter = ('verification_status', 'is_active', 'fuel_type', 'vehicle_type')
    search_fields = ('license_plate', 'vin_number', 'owner__phone_number', 'make', 'model')
    readonly_fields = ('verified_at', 'verified_by', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [VehicleDocumentInline, InsuranceInline, InspectionInline, VehicleMaintenanceRecordInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'vehicle_type', 'make', 'model', 'year', 'color')
        }),
        ('Identification', {
            'fields': ('license_plate', 'vin_number')
        }),
        ('Technical Details', {
            'fields': ('fuel_type', 'engine_capacity', 'mileage', 'is_eco_friendly')
        }),
        ('Photos', {
            'fields': ('front_photo', 'back_photo', 'side_photo', 'interior_photo')
        }),
        ('Verification', {
            'fields': ('verification_status', 'verified_at', 'verified_by', 'rejection_reason')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly based on user permissions."""
        readonly = list(self.readonly_fields)
        if not request.user.is_superuser:
            readonly.extend(['owner', 'vin_number'])
        return readonly


@admin.register(VehicleDocument)
class VehicleDocumentAdmin(admin.ModelAdmin):
    """
    Admin for VehicleDocument model.
    """
    list_display = (
        'vehicle', 'document_type', 'document_number', 
        'expiry_date', 'is_verified', 'is_expired_display'
    )
    list_filter = ('document_type', 'is_verified', 'expiry_date')
    search_fields = ('vehicle__license_plate', 'document_number', 'issuing_authority')
    readonly_fields = ('verified_at', 'verified_by', 'created_at', 'updated_at')
    date_hierarchy = 'expiry_date'
    
    def is_expired_display(self, obj):
        """Display expiry status with color coding."""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.days_until_expiry <= 30:
            return format_html('<span style="color: orange;">Expiring Soon</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    
    is_expired_display.short_description = 'Status'


@admin.register(Insurance)
class InsuranceAdmin(admin.ModelAdmin):
    """
    Admin for Insurance model.
    """
    list_display = (
        'vehicle', 'policy_number', 'insurance_company', 
        'end_date', 'is_active', 'is_expired_display'
    )
    list_filter = ('insurance_type', 'is_active', 'end_date')
    search_fields = ('vehicle__license_plate', 'policy_number', 'insurance_company')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'end_date'
    
    def is_expired_display(self, obj):
        """Display expiry status with color coding."""
        if obj.is_expired:
            return format_html('<span style="color: red;">Expired</span>')
        elif obj.days_until_expiry <= 30:
            return format_html('<span style="color: orange;">Expiring Soon</span>')
        else:
            return format_html('<span style="color: green;">Valid</span>')
    
    is_expired_display.short_description = 'Status'


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    """
    Admin for Inspection model.
    """
    list_display = (
        'vehicle', 'inspection_type', 'status', 'scheduled_date', 
        'completed_date', 'overall_score', 'inspector'
    )
    list_filter = ('inspection_type', 'status', 'scheduled_date')
    search_fields = ('vehicle__license_plate', 'inspector__phone_number')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'scheduled_date'


@admin.register(VehicleMaintenanceRecord)
class VehicleMaintenanceRecordAdmin(admin.ModelAdmin):
    """
    Admin for VehicleMaintenanceRecord model.
    """
    list_display = (
        'vehicle', 'maintenance_type', 'service_date', 
        'cost', 'service_provider', 'next_service_date'
    )
    list_filter = ('maintenance_type', 'service_date')
    search_fields = ('vehicle__license_plate', 'service_provider', 'description')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'service_date'
