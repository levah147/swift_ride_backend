from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin 
from django.utils.html import format_html
from django.urls import reverse
from apps.location.models import (
    Country, State, City, ServiceZone, Place, UserSavedPlace,
    Route, GeofenceZone, LocationHistory, LocationAnalytics,
    PopularDestination, LocationSearchLog, TrafficCondition
)
 

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'currency', 'phone_code', 'is_active', 'created_at']
    list_filter = ['is_active', 'currency', 'created_at']
    search_fields = ['name', 'code']
    ordering = ['name']


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'country', 'is_active', 'created_at']
    list_filter = ['country', 'is_active', 'created_at']
    search_fields = ['name', 'code', 'country__name']
    ordering = ['country', 'name']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'state', 'country_name', 'population',
        'service_available', 'launch_date', 'is_active'
    ]
    list_filter = ['service_available', 'is_active', 'state__country', 'created_at']
    search_fields = ['name', 'state__name', 'state__country__name']
    ordering = ['state', 'name']

    def country_name(self, obj):
        return obj.state.country.name
    country_name.short_description = 'Country'


@admin.register(ServiceZone)
class ServiceZoneAdmin(OSMGeoAdmin):
    list_display = [
        'name', 'city', 'zone_type', 'base_fare_multiplier',
        'surge_multiplier', 'is_active', 'created_at'
    ]
    list_filter = ['zone_type', 'is_active', 'city', 'created_at']
    search_fields = ['name', 'city__name']
    ordering = ['city', 'name']


@admin.register(Place)
class PlaceAdmin(OSMGeoAdmin):
    list_display = [
        'name', 'place_type', 'city', 'pickup_count',
        'dropoff_count', 'search_count', 'is_popular',
        'is_verified', 'is_active'
    ]
    list_filter = [
        'place_type', 'is_popular', 'is_verified', 'is_active',
        'city', 'created_at'
    ]
    search_fields = ['name', 'address', 'city__name']
    ordering = ['-pickup_count', '-dropoff_count', 'name']
    readonly_fields = ['pickup_count', 'dropoff_count', 'search_count']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'place_type', 'address', 'city')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'service_zone')
        }),
        ('External Data', {
            'fields': ('google_place_id', 'phone_number', 'website', 'rating')
        }),
        ('Statistics', {
            'fields': ('pickup_count', 'dropoff_count', 'search_count')
        }),
        ('Status', {
            'fields': ('is_verified', 'is_popular', 'is_active')
        })
    )


@admin.register(UserSavedPlace)
class UserSavedPlaceAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'place_name', 'custom_name', 'is_favorite',
        'usage_count', 'last_used', 'created_at'
    ]
    list_filter = ['is_favorite', 'place__place_type', 'created_at']
    search_fields = [
        'user__first_name', 'user__last_name',
        'place__name', 'custom_name'
    ]
    ordering = ['-is_favorite', '-usage_count']

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_link.short_description = 'User'

    def place_name(self, obj):
        return obj.place.name
    place_name.short_description = 'Place'


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'distance_km', 'duration_minutes', 'traffic_condition',
        'usage_count', 'expires_at', 'created_at'
    ]
    list_filter = ['traffic_condition', 'expires_at', 'created_at']
    search_fields = ['origin_address', 'destination_address']
    ordering = ['-created_at']
    readonly_fields = ['usage_count']

    def distance_km(self, obj):
        return f"{obj.distance_km} km"
    distance_km.short_description = 'Distance'

    def duration_minutes(self, obj):
        return f"{obj.duration_minutes} min"
    duration_minutes.short_description = 'Duration'


@admin.register(GeofenceZone)
class GeofenceZoneAdmin(OSMGeoAdmin):
    list_display = [
        'name', 'zone_type', 'city', 'trigger_on_enter',
        'trigger_on_exit', 'is_active', 'created_at'
    ]
    list_filter = ['zone_type', 'is_active', 'city', 'created_at']
    search_fields = ['name', 'description', 'city__name']
    ordering = ['city', 'name']


@admin.register(LocationHistory)
class LocationHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'latitude', 'longitude', 'activity_type',
        'accuracy', 'ride_link', 'created_at'
    ]
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__first_name', 'user__last_name']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_link.short_description = 'User'

    def ride_link(self, obj):
        if obj.ride:
            url = reverse('admin:rides_ride_change', args=[obj.ride.id])
            return format_html('<a href="{}">{}</a>', url, f"Ride #{obj.ride.id}")
        return "-"
    ride_link.short_description = 'Ride'


@admin.register(PopularDestination)
class PopularDestinationAdmin(admin.ModelAdmin):
    list_display = [
        'place_link', 'destination_type', 'score', 'weekly_visits',
        'monthly_visits', 'season', 'is_active', 'last_updated'
    ]
    list_filter = ['destination_type', 'season', 'is_active', 'last_updated']
    search_fields = ['place__name', 'place__city__name']
    ordering = ['-score', '-weekly_visits']

    def place_link(self, obj):
        url = reverse('admin:location_place_change', args=[obj.place.id])
        return format_html('<a href="{}">{}</a>', url, obj.place.name)
    place_link.short_description = 'Place'


@admin.register(LocationSearchLog)
class LocationSearchLogAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'query', 'search_type', 'results_count',
        'selected_place_link', 'response_time_ms', 'created_at'
    ]
    list_filter = ['search_type', 'created_at']
    search_fields = ['query', 'user__first_name', 'user__last_name']
    ordering = ['-created_at']

    def user_link(self, obj):
        if obj.user:
            url = reverse('admin:users_user_change', args=[obj.user.id])
            return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
        return "Anonymous"
    user_link.short_description = 'User'

    def selected_place_link(self, obj):
        if obj.selected_place:
            url = reverse('admin:location_place_change', args=[obj.selected_place.id])
            return format_html('<a href="{}">{}</a>', url, obj.selected_place.name)
        return "-"
    selected_place_link.short_description = 'Selected Place'


@admin.register(TrafficCondition)
class TrafficConditionAdmin(admin.ModelAdmin):
    list_display = [
        'route_link', 'severity', 'speed_kmh', 'delay_minutes',
        'incident_type', 'is_active', 'expires_at', 'created_at'
    ]
    list_filter = ['severity', 'incident_type', 'is_active', 'created_at']
    search_fields = ['description']
    ordering = ['-created_at']

    def route_link(self, obj):
        url = reverse('admin:location_route_change', args=[obj.route.id])
        return format_html('<a href="{}">{}</a>', url, f"Route #{obj.route.id}")
    route_link.short_description = 'Route'


@admin.register(LocationAnalytics)
class LocationAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'location_name', 'date', 'total_pickups', 'total_dropoffs',
        'unique_users', 'total_revenue', 'average_fare'
    ]
    list_filter = ['date', 'city']
    search_fields = ['place__name', 'service_zone__name', 'city__name']
    ordering = ['-date']

    def location_name(self, obj):
        if obj.place:
            return obj.place.name
        elif obj.service_zone:
            return obj.service_zone.name
        else:
            return obj.city.name
    location_name.short_description = 'Location'
 