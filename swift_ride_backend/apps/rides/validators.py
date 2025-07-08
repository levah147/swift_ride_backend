"""
Validators for rides app.
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.rides.utils import validate_ride_coordinates, calculate_distance


def validate_pickup_location(value):
    """
    Validate pickup location string.
    """
    if not value or len(value.strip()) < 5:
        raise ValidationError("Pickup location must be at least 5 characters long")
    
    if len(value) > 255:
        raise ValidationError("Pickup location is too long")


def validate_dropoff_location(value):
    """
    Validate dropoff location string.
    """
    if not value or len(value.strip()) < 5:
        raise ValidationError("Dropoff location must be at least 5 characters long")
    
    if len(value) > 255:
        raise ValidationError("Dropoff location is too long")


def validate_coordinates(latitude, longitude):
    """
    Validate latitude and longitude values.
    """
    if not (-90 <= latitude <= 90):
        raise ValidationError("Latitude must be between -90 and 90")
    
    if not (-180 <= longitude <= 180):
        raise ValidationError("Longitude must be between -180 and 180")


def validate_nigeria_coordinates(latitude, longitude):
    """
    Validate that coordinates are within Nigeria bounds.
    """
    # Nigeria approximate bounds
    nigeria_bounds = {
        'min_lat': 4.0,
        'max_lat': 14.0,
        'min_lon': 2.5,
        'max_lon': 15.0
    }
    
    if not (nigeria_bounds['min_lat'] <= latitude <= nigeria_bounds['max_lat']):
        raise ValidationError("Latitude is outside Nigeria service area")
    
    if not (nigeria_bounds['min_lon'] <= longitude <= nigeria_bounds['max_lon']):
        raise ValidationError("Longitude is outside Nigeria service area")


def validate_ride_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon):
    """
    Validate ride distance is within acceptable limits.
    """
    distance = calculate_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    
    if distance < 0.5:  # 500 meters minimum
        raise ValidationError("Ride distance is too short (minimum 500 meters)")
    
    if distance > 200:  # 200 km maximum
        raise ValidationError("Ride distance is too long (maximum 200 km)")
    
    return distance


def validate_fare_amount(value):
    """
    Validate fare amount.
    """
    if value < Decimal('0.00'):
        raise ValidationError("Fare amount cannot be negative")
    
    if value > Decimal('50000.00'):  # 50,000 Naira maximum
        raise ValidationError("Fare amount is too high")
    
    # Check decimal places
    if value.as_tuple().exponent < -2:
        raise ValidationError("Fare amount cannot have more than 2 decimal places")


def validate_rating(value):
    """
    Validate rating value (1-5 stars).
    """
    if not (1 <= value <= 5):
        raise ValidationError("Rating must be between 1 and 5")


def validate_schedule_time(value):
    """
    Validate scheduled ride time.
    """
    if value <= timezone.now():
        raise ValidationError("Schedule time must be in the future")
    
    # Maximum 7 days in advance
    max_schedule_time = timezone.now() + timedelta(days=7)
    if value > max_schedule_time:
        raise ValidationError("Cannot schedule rides more than 7 days in advance")
    
    # Minimum 30 minutes in advance
    min_schedule_time = timezone.now() + timedelta(minutes=30)
    if value < min_schedule_time:
        raise ValidationError("Scheduled rides must be at least 30 minutes in advance")


def validate_duration_minutes(value):
    """
    Validate ride duration in minutes.
    """
    if value < 1:
        raise ValidationError("Duration must be at least 1 minute")
    
    if value > 720:  # 12 hours maximum
        raise ValidationError("Duration cannot exceed 12 hours")


def validate_payment_method(value):
    """
    Validate payment method.
    """
    valid_methods = ['cash', 'card', 'wallet', 'bank_transfer', 'mobile_money']
    
    if value not in valid_methods:
        raise ValidationError(f"Invalid payment method. Must be one of: {', '.join(valid_methods)}")


def validate_vehicle_type(value):
    """
    Validate vehicle type.
    """
    valid_types = ['sedan', 'suv', 'hatchback', 'bus', 'motorcycle', 'tricycle']
    
    if value and value not in valid_types:
        raise ValidationError(f"Invalid vehicle type. Must be one of: {', '.join(valid_types)}")


def validate_bargain_amount(value, estimated_fare):
    """
    Validate bargain offer amount.
    """
    if value <= Decimal('0.00'):
        raise ValidationError("Bargain amount must be greater than zero")
    
    # Cannot be more than 200% of estimated fare
    max_amount = estimated_fare * Decimal('2.0')
    if value > max_amount:
        raise ValidationError("Bargain amount cannot exceed 200% of estimated fare")
    
    # Cannot be less than 50% of estimated fare
    min_amount = estimated_fare * Decimal('0.5')
    if value < min_amount:
        raise ValidationError("Bargain amount cannot be less than 50% of estimated fare")


def validate_ride_notes(value):
    """
    Validate ride notes.
    """
    if value and len(value) > 500:
        raise ValidationError("Notes cannot exceed 500 characters")
    
    # Check for inappropriate content (basic check)
    inappropriate_words = ['spam', 'scam', 'fraud']  # Add more as needed
    if value:
        for word in inappropriate_words:
            if word.lower() in value.lower():
                raise ValidationError("Notes contain inappropriate content")


def validate_otp(value):
    """
    Validate OTP format.
    """
    if not value.isdigit():
        raise ValidationError("OTP must contain only digits")
    
    if len(value) != 4:
        raise ValidationError("OTP must be exactly 4 digits")


def validate_phone_number_for_ride(value):
    """
    Validate phone number format for ride-related operations.
    """
    import re
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', value)
    
    # Check Nigerian phone number patterns
    if digits_only.startswith('234'):
        # International format
        if len(digits_only) != 13:
            raise ValidationError("Invalid Nigerian phone number format")
    elif digits_only.startswith('0'):
        # Local format
        if len(digits_only) != 11:
            raise ValidationError("Invalid Nigerian phone number format")
    else:
        raise ValidationError("Phone number must be a valid Nigerian number")


def validate_emergency_contact(value):
    """
    Validate emergency contact information.
    """
    if not value.get('name') or len(value['name'].strip()) < 2:
        raise ValidationError("Emergency contact name is required")
    
    if not value.get('phone'):
        raise ValidationError("Emergency contact phone is required")
    
    try:
        validate_phone_number_for_ride(value['phone'])
    except ValidationError:
        raise ValidationError("Invalid emergency contact phone number")


def validate_ride_capacity(value):
    """
    Validate ride passenger capacity.
    """
    if not (1 <= value <= 8):
        raise ValidationError("Ride capacity must be between 1 and 8 passengers")


def validate_special_requirements(value):
    """
    Validate special requirements for ride.
    """
    valid_requirements = [
        'wheelchair_accessible',
        'child_seat',
        'pet_friendly',
        'air_conditioning',
        'quiet_ride',
        'music_allowed'
    ]
    
    if value:
        for requirement in value:
            if requirement not in valid_requirements:
                raise ValidationError(f"Invalid special requirement: {requirement}")
