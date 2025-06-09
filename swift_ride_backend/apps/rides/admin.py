"""
Admin configuration for ride models.
"""

from django.contrib import admin

from apps.rides.models import Ride, RideRequest, BargainOffer, RideHistory, TripStatus


class RideHistoryInline(admin.TabularInline):
    """
    Inline admin for RideHistory.
    """
    model = RideHistory
    extra = 0
    readonly_fields = ['event_type', 'previous_status', 'new_status', 'latitude', 'longitude', 'data', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class BargainOfferInline(admin.TabularInline):
    """
    Inline admin for BargainOffer.
    """
    model = BargainOffer
    extra = 0
    readonly_fields = ['offered_by', 'offer_type', 'amount', 'status', 'message', 'expiry_time', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class TripStatusInline(admin.StackedInline):
    """
    Inline admin for TripStatus.
    """
    model = TripStatus
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


class RideAdmin(admin.ModelAdmin):
    """
    Admin for Ride model.
    """
    list_display = ('id', 'rider', 'driver', 'status', 'pickup_location', 'dropoff_location', 'estimated_fare', 'final_fare', 'created_at')
    list_filter = ('status', 'is_scheduled', 'payment_method', 'payment_status')
    search_fields = ('rider__phone_number', 'driver__phone_number', 'pickup_location', 'dropoff_location')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    inlines = [TripStatusInline, BargainOfferInline, RideHistoryInline]


class RideRequestAdmin(admin.ModelAdmin):
    """
    Admin for RideRequest model.
    """
    list_display = ('id', 'ride', 'status', 'vehicle_type', 'expiry_time', 'created_at')
    list_filter = ('status',)
    search_fields = ('ride__id', 'ride__rider__phone_number')
    readonly_fields = ('created_at', 'updated_at')


class BargainOfferAdmin(admin.ModelAdmin):
    """
    Admin for BargainOffer model.
    """
    list_display = ('id', 'ride', 'offered_by', 'offer_type', 'amount', 'status', 'created_at')
    list_filter = ('offer_type', 'status')
    search_fields = ('ride__id', 'offered_by__phone_number')
    readonly_fields = ('created_at', 'updated_at')


class RideHistoryAdmin(admin.ModelAdmin):
    """
    Admin for RideHistory model.
    """
    list_display = ('id', 'ride', 'event_type', 'previous_status', 'new_status', 'created_at')
    list_filter = ('event_type',)
    search_fields = ('ride__id',)
    readonly_fields = ('created_at',)


class TripStatusAdmin(admin.ModelAdmin):
    """
    Admin for TripStatus model.
    """
    list_display = ('id', 'ride', 'current_latitude', 'current_longitude', 'last_updated')
    search_fields = ('ride__id',)
    readonly_fields = ('last_updated',)


# Register models
admin.site.register(Ride, RideAdmin)
admin.site.register(RideRequest, RideRequestAdmin)
admin.site.register(BargainOffer, BargainOfferAdmin)
admin.site.register(RideHistory, RideHistoryAdmin)
admin.site.register(TripStatus, TripStatusAdmin)
