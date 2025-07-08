"""
Utility functions for rides app.
"""

import math
from decimal import Decimal
from datetime import datetime, timedelta
from typing import Tuple, List, Dict, Optional
from django.utils import timezone
from django.conf import settings

from apps.rides.models import Ride


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth in kilometers.
    Uses the Haversine formula.
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the bearing between two points.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    dlon = lon2 - lon1
    
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    
    bearing = math.atan2(y, x)
    bearing = math.degrees(bearing)
    bearing = (bearing + 360) % 360
    
    return bearing


def estimate_arrival_time(distance_km: float, traffic_factor: float = 1.2) -> int:
    """
    Estimate arrival time in minutes based on distance and traffic.
    """
    # Average speed in km/h (considering city traffic)
    avg_speed = 25 / traffic_factor
    
    # Calculate time in hours, then convert to minutes
    time_hours = distance_km / avg_speed
    time_minutes = time_hours * 60
    
    # Add buffer time
    buffer_minutes = max(5, distance_km * 2)  # 2 minutes per km minimum
    
    return int(time_minutes + buffer_minutes)


def calculate_base_fare(distance_km: float, duration_minutes: int) -> Decimal:
    """
    Calculate base fare for a ride.
    """
    # Base fare structure (in Naira)
    base_fare = Decimal('200.00')  # Base fare
    per_km_rate = Decimal('80.00')  # Per kilometer
    per_minute_rate = Decimal('15.00')  # Per minute
    
    # Calculate fare components
    distance_fare = Decimal(str(distance_km)) * per_km_rate
    time_fare = Decimal(str(duration_minutes)) * per_minute_rate
    
    total_fare = base_fare + distance_fare + time_fare
    
    # Minimum fare
    minimum_fare = Decimal('300.00')
    
    return max(total_fare, minimum_fare)


def apply_surge_pricing(base_fare: Decimal, surge_multiplier: float = 1.0) -> Decimal:
    """
    Apply surge pricing to base fare.
    """
    if surge_multiplier <= 1.0:
        return base_fare
    
    return base_fare * Decimal(str(surge_multiplier))


def get_surge_multiplier(pickup_lat: float, pickup_lon: float, 
                        current_time: datetime = None) -> float:
    """
    Calculate surge multiplier based on location and time.
    """
    if current_time is None:
        current_time = timezone.now()
    
    # Base multiplier
    multiplier = 1.0
    
    # Time-based surge
    hour = current_time.hour
    
    # Rush hours (7-9 AM, 5-7 PM)
    if (7 <= hour <= 9) or (17 <= hour <= 19):
        multiplier += 0.5
    
    # Late night (11 PM - 5 AM)
    elif hour >= 23 or hour <= 5:
        multiplier += 0.3
    
    # Weekend nights (Friday/Saturday 8 PM - 2 AM)
    if current_time.weekday() in [4, 5] and (20 <= hour or hour <= 2):
        multiplier += 0.4
    
    # Weather-based surge (simplified - in production, integrate with weather API)
    # For now, random chance of weather surge
    import random
    if random.random() < 0.1:  # 10% chance of weather surge
        multiplier += 0.2
    
    # Cap the multiplier
    return min(multiplier, 3.0)


def format_ride_duration(start_time: datetime, end_time: datetime = None) -> str:
    """
    Format ride duration in human-readable format.
    """
    if end_time is None:
        end_time = timezone.now()
    
    duration = end_time - start_time
    
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def get_ride_eta(ride: Ride) -> Optional[int]:
    """
    Get estimated time of arrival for a ride in minutes.
    """
    if not ride.driver or not hasattr(ride, 'trip_status'):
        return None
    
    trip_status = ride.trip_status
    
    if ride.status == Ride.RideStatus.DRIVER_ASSIGNED:
        # ETA to pickup location
        if trip_status.distance_to_pickup:
            return estimate_arrival_time(float(trip_status.distance_to_pickup))
    
    elif ride.status == Ride.RideStatus.IN_PROGRESS:
        # ETA to destination
        if trip_status.distance_to_dropoff:
            return estimate_arrival_time(float(trip_status.distance_to_dropoff))
    
    return None


def is_ride_expired(ride: Ride) -> bool:
    """
    Check if a ride request has expired.
    """
    if ride.status != Ride.RideStatus.SEARCHING:
        return False
    
    # Ride expires after 10 minutes of searching
    expiry_time = ride.created_at + timedelta(minutes=10)
    return timezone.now() > expiry_time


def get_nearby_rides(lat: float, lon: float, radius_km: float = 5) -> List[Ride]:
    """
    Get nearby rides within a specified radius.
    """
    # This is a simplified version. In production, use PostGIS for efficient spatial queries
    rides = Ride.objects.filter(
        status__in=[Ride.RideStatus.SEARCHING, Ride.RideStatus.BARGAINING]
    )
    
    nearby_rides = []
    for ride in rides:
        distance = calculate_distance(
            lat, lon,
            float(ride.pickup_latitude), float(ride.pickup_longitude)
        )
        if distance <= radius_km:
            nearby_rides.append(ride)
    
    return nearby_rides


def validate_ride_coordinates(pickup_lat: float, pickup_lon: float,
                            dropoff_lat: float, dropoff_lon: float) -> Tuple[bool, str]:
    """
    Validate ride coordinates.
    """
    # Check if coordinates are within Nigeria bounds (approximate)
    nigeria_bounds = {
        'min_lat': 4.0,
        'max_lat': 14.0,
        'min_lon': 2.5,
        'max_lon': 15.0
    }
    
    # Validate pickup coordinates
    if not (nigeria_bounds['min_lat'] <= pickup_lat <= nigeria_bounds['max_lat'] and
            nigeria_bounds['min_lon'] <= pickup_lon <= nigeria_bounds['max_lon']):
        return False, "Pickup location is outside service area"
    
    # Validate dropoff coordinates
    if not (nigeria_bounds['min_lat'] <= dropoff_lat <= nigeria_bounds['max_lat'] and
            nigeria_bounds['min_lon'] <= dropoff_lon <= nigeria_bounds['max_lon']):
        return False, "Dropoff location is outside service area"
    
    # Check minimum distance (prevent very short rides)
    distance = calculate_distance(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon)
    if distance < 0.5:  # 500 meters minimum
        return False, "Ride distance is too short (minimum 500m)"
    
    # Check maximum distance
    if distance > 200:  # 200 km maximum
        return False, "Ride distance is too long (maximum 200km)"
    
    return True, "Valid coordinates"


def generate_ride_otp() -> str:
    """
    Generate a 4-digit OTP for ride verification.
    """
    import random
    return str(random.randint(1000, 9999))


def calculate_cancellation_fee(ride: Ride) -> Decimal:
    """
    Calculate cancellation fee based on ride status and timing.
    """
    if ride.status in [Ride.RideStatus.REQUESTED, Ride.RideStatus.SEARCHING]:
        return Decimal('0.00')  # No fee for early cancellation
    
    elif ride.status == Ride.RideStatus.ACCEPTED:
        # Small fee if cancelled after acceptance
        return Decimal('50.00')
    
    elif ride.status in [Ride.RideStatus.DRIVER_ASSIGNED, Ride.RideStatus.DRIVER_ARRIVED]:
        # Higher fee if driver is already assigned/arrived
        return Decimal('100.00')
    
    else:
        # No cancellation allowed for rides in progress or completed
        return Decimal('0.00')


def get_ride_summary(ride: Ride) -> Dict:
    """
    Get a summary of ride details for notifications/receipts.
    """
    return {
        'ride_id': str(ride.id),
        'rider_name': ride.rider.get_full_name(),
        'driver_name': ride.driver.get_full_name() if ride.driver else None,
        'pickup_location': ride.pickup_location,
        'dropoff_location': ride.dropoff_location,
        'status': ride.get_status_display(),
        'estimated_fare': str(ride.estimated_fare),
        'final_fare': str(ride.final_fare) if ride.final_fare else None,
        'distance': f"{ride.distance_km} km",
        'duration': format_ride_duration(ride.created_at, ride.dropoff_time),
        'created_at': ride.created_at.isoformat(),
        'completed_at': ride.dropoff_time.isoformat() if ride.dropoff_time else None,
    }
