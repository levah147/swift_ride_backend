"""
Filters for rides app.
"""

import django_filters
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from apps.rides.models import Ride, BargainOffer, RideHistory


class RideFilter(django_filters.FilterSet):
    """
    Filter for Ride model.
    """
    
    # Status filters
    status = django_filters.ChoiceFilter(choices=Ride.RideStatus.choices)
    status_in = django_filters.MultipleChoiceFilter(
        field_name='status',
        choices=Ride.RideStatus.choices,
        lookup_expr='in'
    )
    
    # Date filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    created_date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='date'
    )
    
    # Fare filters
    min_fare = django_filters.NumberFilter(
        field_name='estimated_fare',
        lookup_expr='gte'
    )
    max_fare = django_filters.NumberFilter(
        field_name='estimated_fare',
        lookup_expr='lte'
    )
    
    # Distance filters
    min_distance = django_filters.NumberFilter(
        field_name='distance_km',
        lookup_expr='gte'
    )
    max_distance = django_filters.NumberFilter(
        field_name='distance_km',
        lookup_expr='lte'
    )
    
    # Duration filters
    min_duration = django_filters.NumberFilter(
        field_name='duration_minutes',
        lookup_expr='gte'
    )
    max_duration = django_filters.NumberFilter(
        field_name='duration_minutes',
        lookup_expr='lte'
    )
    
    # Payment filters
    payment_method = django_filters.CharFilter()
    payment_status = django_filters.CharFilter()
    
    # Location filters
    pickup_location = django_filters.CharFilter(
        field_name='pickup_location',
        lookup_expr='icontains'
    )
    dropoff_location = django_filters.CharFilter(
        field_name='dropoff_location',
        lookup_expr='icontains'
    )
    
    # User filters
    rider = django_filters.UUIDFilter(field_name='rider__id')
    driver = django_filters.UUIDFilter(field_name='driver__id')
    
    # Boolean filters
    is_scheduled = django_filters.BooleanFilter()
    has_rating = django_filters.BooleanFilter(method='filter_has_rating')
    is_active = django_filters.BooleanFilter(method='filter_is_active')
    
    # Search filter
    search = django_filters.CharFilter(method='filter_search')
    
    # Time-based filters
    today = django_filters.BooleanFilter(method='filter_today')
    this_week = django_filters.BooleanFilter(method='filter_this_week')
    this_month = django_filters.BooleanFilter(method='filter_this_month')
    
    class Meta:
        model = Ride
        fields = [
            'status', 'payment_method', 'payment_status',
            'is_scheduled', 'rider', 'driver'
        ]
    
    def filter_has_rating(self, queryset, name, value):
        """
        Filter rides that have ratings.
        """
        if value:
            return queryset.filter(
                Q(rider_rating__isnull=False) | Q(driver_rating__isnull=False)
            )
        else:
            return queryset.filter(
                rider_rating__isnull=True,
                driver_rating__isnull=True
            )
    
    def filter_is_active(self, queryset, name, value):
        """
        Filter active rides.
        """
        active_statuses = [
            Ride.RideStatus.REQUESTED,
            Ride.RideStatus.SEARCHING,
            Ride.RideStatus.BARGAINING,
            Ride.RideStatus.ACCEPTED,
            Ride.RideStatus.DRIVER_ASSIGNED,
            Ride.RideStatus.DRIVER_ARRIVED,
            Ride.RideStatus.IN_PROGRESS
        ]
        
        if value:
            return queryset.filter(status__in=active_statuses)
        else:
            return queryset.exclude(status__in=active_statuses)
    
    def filter_search(self, queryset, name, value):
        """
        Search across multiple fields.
        """
        return queryset.filter(
            Q(pickup_location__icontains=value) |
            Q(dropoff_location__icontains=value) |
            Q(rider__first_name__icontains=value) |
            Q(rider__last_name__icontains=value) |
            Q(rider__phone_number__icontains=value) |
            Q(driver__first_name__icontains=value) |
            Q(driver__last_name__icontains=value) |
            Q(driver__phone_number__icontains=value)
        )
    
    def filter_today(self, queryset, name, value):
        """
        Filter rides from today.
        """
        if value:
            today = timezone.now().date()
            return queryset.filter(created_at__date=today)
        return queryset
    
    def filter_this_week(self, queryset, name, value):
        """
        Filter rides from this week.
        """
        if value:
            week_start = timezone.now() - timedelta(days=7)
            return queryset.filter(created_at__gte=week_start)
        return queryset
    
    def filter_this_month(self, queryset, name, value):
        """
        Filter rides from this month.
        """
        if value:
            month_start = timezone.now() - timedelta(days=30)
            return queryset.filter(created_at__gte=month_start)
        return queryset


class BargainOfferFilter(django_filters.FilterSet):
    """
    Filter for BargainOffer model.
    """
    
    # Status filters
    status = django_filters.ChoiceFilter(choices=BargainOffer.OfferStatus.choices)
    offer_type = django_filters.ChoiceFilter(choices=BargainOffer.OfferType.choices)
    
    # Amount filters
    min_amount = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='gte'
    )
    max_amount = django_filters.NumberFilter(
        field_name='amount',
        lookup_expr='lte'
    )
    
    # Date filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    
    # Expiry filters
    expires_after = django_filters.DateTimeFilter(
        field_name='expiry_time',
        lookup_expr='gte'
    )
    expires_before = django_filters.DateTimeFilter(
        field_name='expiry_time',
        lookup_expr='lte'
    )
    
    # Relationship filters
    ride = django_filters.UUIDFilter(field_name='ride__id')
    offered_by = django_filters.UUIDFilter(field_name='offered_by__id')
    
    # Boolean filters
    is_expired = django_filters.BooleanFilter(method='filter_is_expired')
    is_counter_offer = django_filters.BooleanFilter(method='filter_is_counter_offer')
    
    class Meta:
        model = BargainOffer
        fields = ['status', 'offer_type', 'ride', 'offered_by']
    
    def filter_is_expired(self, queryset, name, value):
        """
        Filter expired offers.
        """
        now = timezone.now()
        if value:
            return queryset.filter(expiry_time__lt=now)
        else:
            return queryset.filter(expiry_time__gte=now)
    
    def filter_is_counter_offer(self, queryset, name, value):
        """
        Filter counter offers.
        """
        if value:
            return queryset.filter(counter_offer__isnull=False)
        else:
            return queryset.filter(counter_offer__isnull=True)


class RideHistoryFilter(django_filters.FilterSet):
    """
    Filter for RideHistory model.
    """
    
    # Event type filter
    event_type = django_filters.ChoiceFilter(choices=RideHistory.EventType.choices)
    
    # Status filters
    previous_status = django_filters.ChoiceFilter(choices=Ride.RideStatus.choices)
    new_status = django_filters.ChoiceFilter(choices=Ride.RideStatus.choices)
    
    # Date filters
    created_after = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='gte'
    )
    created_before = django_filters.DateTimeFilter(
        field_name='created_at',
        lookup_expr='lte'
    )
    created_date = django_filters.DateFilter(
        field_name='created_at',
        lookup_expr='date'
    )
    
    # Relationship filters
    ride = django_filters.UUIDFilter(field_name='ride__id')
    
    # Location filters
    has_location = django_filters.BooleanFilter(method='filter_has_location')
    
    class Meta:
        model = RideHistory
        fields = ['event_type', 'previous_status', 'new_status', 'ride']
    
    def filter_has_location(self, queryset, name, value):
        """
        Filter history entries with location data.
        """
        if value:
            return queryset.filter(
                latitude__isnull=False,
                longitude__isnull=False
            )
        else:
            return queryset.filter(
                Q(latitude__isnull=True) | Q(longitude__isnull=True)
            )


class DriverRideFilter(django_filters.FilterSet):
    """
    Special filter for drivers to find available rides.
    """
    
    # Location-based filters (would need PostGIS in production)
    near_lat = django_filters.NumberFilter(method='filter_near_location')
    near_lon = django_filters.NumberFilter(method='filter_near_location')
    max_distance = django_filters.NumberFilter(method='filter_near_location')
    
    # Fare filters
    min_fare = django_filters.NumberFilter(
        field_name='estimated_fare',
        lookup_expr='gte'
    )
    
    # Vehicle type filter
    vehicle_type = django_filters.CharFilter(
        field_name='request__vehicle_type'
    )
    
    # Only available rides
    available_only = django_filters.BooleanFilter(method='filter_available_only')
    
    class Meta:
        model = Ride
        fields = ['min_fare', 'vehicle_type']
    
    def filter_near_location(self, queryset, name, value):
        """
        Filter rides near a specific location.
        This is a simplified version - in production, use PostGIS.
        """
        # This would be implemented with proper geospatial queries
        return queryset
    
    def filter_available_only(self, queryset, name, value):
        """
        Filter only available rides for drivers.
        """
        if value:
            return queryset.filter(
                status__in=[
                    Ride.RideStatus.SEARCHING,
                    Ride.RideStatus.BARGAINING
                ]
            )
        return queryset
