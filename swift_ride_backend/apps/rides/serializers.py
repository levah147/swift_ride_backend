"""
Serializers for ride models.
"""

from rest_framework import serializers
from django.utils import timezone

from apps.rides.models import Ride, RideRequest, BargainOffer, RideHistory, TripStatus
from apps.users.serializers import UserSerializer


class TripStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for TripStatus model.
    """
    class Meta:
        model = TripStatus
        fields = [
            'current_latitude', 'current_longitude', 'last_updated', 
            'estimated_arrival_time', 'distance_to_pickup', 
            'distance_to_dropoff', 'is_driver_moving', 'driver_bearing'
        ]


class RideHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for RideHistory model.
    """
    class Meta:
        model = RideHistory
        fields = [
            'id', 'event_type', 'previous_status', 'new_status',
            'latitude', 'longitude', 'data', 'notes', 'created_at'
        ]


class BargainOfferSerializer(serializers.ModelSerializer):
    """
    Serializer for BargainOffer model.
    """
    offered_by = UserSerializer(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = BargainOffer
        fields = [
            'id', 'ride', 'offered_by', 'offer_type', 'amount',
            'status', 'message', 'expiry_time', 'counter_offer',
            'created_at', 'updated_at', 'is_expired'
        ]
        read_only_fields = ['id', 'ride', 'offered_by', 'created_at', 'updated_at']


class RideRequestSerializer(serializers.ModelSerializer):
    """
    Serializer for RideRequest model.
    """
    preferred_driver = UserSerializer(read_only=True)
    
    class Meta:
        model = RideRequest
        fields = [
            'id', 'ride', 'status', 'preferred_driver',
            'vehicle_type', 'expiry_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'ride', 'created_at', 'updated_at']


class RideSerializer(serializers.ModelSerializer):
    """
    Serializer for Ride model.
    """
    rider = UserSerializer(read_only=True)
    driver = UserSerializer(read_only=True)
    trip_status = TripStatusSerializer(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    can_cancel = serializers.BooleanField(read_only=True)
    is_bargaining = serializers.BooleanField(read_only=True)
    is_in_progress = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Ride
        fields = [
            'id', 'rider', 'driver', 'status', 'pickup_location',
            'pickup_latitude', 'pickup_longitude', 'dropoff_location',
            'dropoff_latitude', 'dropoff_longitude', 'pickup_time',
            'dropoff_time', 'estimated_fare', 'final_fare', 'rider_rating',
            'driver_rating', 'distance_km', 'duration_minutes',
            'payment_method', 'payment_status', 'notes', 'schedule_time',
            'is_scheduled', 'vehicle', 'trip_status', 'is_active',
            'can_cancel', 'is_bargaining', 'is_in_progress',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'rider', 'driver', 'status', 'pickup_time', 'dropoff_time',
            'final_fare', 'rider_rating', 'driver_rating', 'created_at', 'updated_at'
        ]


class RideCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a ride.
    """
    pickup_location = serializers.CharField(max_length=255)
    pickup_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    dropoff_location = serializers.CharField(max_length=255)
    dropoff_latitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    dropoff_longitude = serializers.DecimalField(max_digits=9, decimal_places=6)
    distance_km = serializers.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = serializers.IntegerField(min_value=1)
    is_scheduled = serializers.BooleanField(default=False)
    schedule_time = serializers.DateTimeField(required=False)
    payment_method = serializers.CharField(max_length=50, default='cash')
    notes = serializers.CharField(required=False, allow_blank=True)
    vehicle_type = serializers.CharField(required=False, allow_blank=True)
    preferred_driver_id = serializers.UUIDField(required=False)
    
    def validate(self, data):
        """
        Validate ride data.
        """
        # Check if schedule_time is provided for scheduled rides
        if data.get('is_scheduled', False) and not data.get('schedule_time'):
            raise serializers.ValidationError("Schedule time is required for scheduled rides")
            
        # Check if schedule_time is in the future for scheduled rides
        if data.get('is_scheduled', False) and data.get('schedule_time'):
            if data['schedule_time'] <= timezone.now():
                raise serializers.ValidationError("Schedule time must be in the future")
        
        return data


class BargainOfferCreateSerializer(serializers.Serializer):
    """
    Serializer for creating a bargain offer.
    """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    message = serializers.CharField(required=False, allow_blank=True)
    
    def validate_amount(self, value):
        """
        Validate offer amount.
        """
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        return value
