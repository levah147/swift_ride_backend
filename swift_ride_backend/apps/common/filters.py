"""
Common filters for Swift Ride project.
"""

import django_filters
from django.db import models
from django_filters import rest_framework as filters
from django.contrib.auth import get_user_model

User = get_user_model()


class BaseFilter(filters.FilterSet):
    """
    Base filter class with common filters.
    """
    created_at = django_filters.DateFromToRangeFilter()
    updated_at = django_filters.DateFromToRangeFilter()
    
    class Meta:
        abstract = True


class UserFilter(BaseFilter):
    """
    Filter for User model.
    """
    phone_number = django_filters.CharFilter(lookup_expr='icontains')
    email = django_filters.CharFilter(lookup_expr='icontains')
    first_name = django_filters.CharFilter(lookup_expr='icontains')
    last_name = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()
    phone_verified = django_filters.BooleanFilter()
    email_verified = django_filters.BooleanFilter()
    user_type = django_filters.ChoiceFilter(choices=[
        ('rider', 'Rider'),
        ('driver', 'Driver'),
        ('both', 'Both')
    ])
    
    class Meta:
        model = User
        fields = [
            'phone_number', 'email', 'first_name', 'last_name',
            'is_active', 'phone_verified', 'email_verified', 'user_type'
        ]


class LocationFilter(filters.FilterSet):
    """
    Filter for location-based queries.
    """
    latitude = django_filters.NumberFilter()
    longitude = django_filters.NumberFilter()
    radius = django_filters.NumberFilter(method='filter_by_radius')
    
    def filter_by_radius(self, queryset, name, value):
        """
        Filter by radius around a point.
        Requires latitude and longitude to be provided.
        """
        latitude = self.request.query_params.get('latitude')
        longitude = self.request.query_params.get('longitude')
        
        if latitude and longitude and value:
            # This would require PostGIS for proper implementation
            # For now, we'll use a simple bounding box approximation
            lat_delta = value / 111.0  # Rough conversion: 1 degree ≈ 111 km
            lng_delta = value / (111.0 * abs(float(latitude)))
            
            lat_min = float(latitude) - lat_delta
            lat_max = float(latitude) + lat_delta
            lng_min = float(longitude) - lng_delta
            lng_max = float(longitude) + lng_delta
            
            return queryset.filter(
                latitude__gte=lat_min,
                latitude__lte=lat_max,
                longitude__gte=lng_min,
                longitude__lte=lng_max
            )
        
        return queryset


class DateRangeFilter(filters.FilterSet):
    """
    Common date range filter.
    """
    start_date = django_filters.DateFilter(field_name='created_at', lookup_expr='gte')
    end_date = django_filters.DateFilter(field_name='created_at', lookup_expr='lte')
    date_range = django_filters.DateFromToRangeFilter(field_name='created_at')
    
    class Meta:
        abstract = True


class StatusFilter(filters.FilterSet):
    """
    Common status filter.
    """
    status = django_filters.ChoiceFilter(choices=[])  # To be overridden in subclasses
    is_active = django_filters.BooleanFilter()
    
    class Meta:
        abstract = True


class SearchFilter(filters.FilterSet):
    """
    Common search filter.
    """
    search = django_filters.CharFilter(method='filter_search')
    
    def filter_search(self, queryset, name, value):
        """
        Override this method in subclasses to define search behavior.
        """
        return queryset
    
    class Meta:
        abstract = True


class PriceRangeFilter(filters.FilterSet):
    """
    Filter for price ranges.
    """
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    price_range = django_filters.RangeFilter(field_name='price')
    
    class Meta:
        abstract = True


class RatingFilter(filters.FilterSet):
    """
    Filter for ratings.
    """
    min_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='gte')
    max_rating = django_filters.NumberFilter(field_name='rating', lookup_expr='lte')
    rating = django_filters.NumberFilter()
    
    class Meta:
        abstract = True


class OrderingFilter(filters.FilterSet):
    """
    Common ordering filter.
    """
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
            ('updated_at', 'updated_at'),
            ('id', 'id'),
        ),
        field_labels={
            'created_at': 'Created Date',
            'updated_at': 'Updated Date',
            'id': 'ID',
        }
    )
    
    class Meta:
        abstract = True


class SoftDeleteFilter(filters.FilterSet):
    """
    Filter for soft-deleted items.
    """
    include_deleted = django_filters.BooleanFilter(method='filter_include_deleted')
    
    def filter_include_deleted(self, queryset, name, value):
        """
        Include or exclude soft-deleted items.
        """
        if value:
            return queryset.filter(is_deleted=False)
        return queryset
    
    class Meta:
        abstract = True
