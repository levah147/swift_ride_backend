"""
Service for matching rides with drivers.
"""

from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import math

from apps.users.models import CustomUser, DriverProfile
from apps.rides.models import Ride, RideHistory


class RideMatchingService:
    """
    Service for matching rides with drivers.
    """
    
    @staticmethod
    def find_nearby_drivers(ride, max_distance_km=5):
        """
        Find nearby drivers for a ride.
        """
        # Get coordinates
        pickup_lat = float(ride.pickup_latitude)
        pickup_lng = float(ride.pickup_longitude)
        
        # Find online drivers
        online_drivers = DriverProfile.objects.filter(
            is_online=True,
            is_available=True,
            verification_status=DriverProfile.VerificationStatus.APPROVED,
            current_latitude__isnull=False,
            current_longitude__isnull=False,
            user__is_active=True
        )
        
        nearby_drivers = []
        
        # Calculate distance for each driver and filter by max distance
        for driver_profile in online_drivers:
            driver_lat = float(driver_profile.current_latitude)
            driver_lng = float(driver_profile.current_longitude)
            
            distance = RideMatchingService._calculate_distance(
                pickup_lat, pickup_lng, driver_lat, driver_lng
            )
            
            if distance <= max_distance_km:
                nearby_drivers.append({
                    'driver': driver_profile.user,
                    'distance': distance,
                    'latitude': driver_lat,
                    'longitude': driver_lng
                })
        
        # Sort by distance
        nearby_drivers.sort(key=lambda x: x['distance'])
        
        return nearby_drivers
    
    @staticmethod
    def match_ride_to_driver(ride, driver):
        """
        Match a ride to a specific driver.
        """
        # Check if ride can be matched
        if ride.status not in [Ride.RideStatus.SEARCHING, Ride.RideStatus.REQUESTED]:
            return False, "Ride cannot be matched at this stage"
        
        # Check if driver is available
        try:
            driver_profile = driver.driver_profile
            if not driver_profile.is_online or not driver_profile.is_available:
                return False, "Driver is not available"
        except DriverProfile.DoesNotExist:
            return False, "Not a valid driver"
        
        # Start bargaining process
        from apps.rides.services.ride_service import RideService
        RideService.start_bargaining(ride, driver)
        
        return True, "Ride matched with driver for bargaining"
    
    @staticmethod
    def _calculate_distance(lat1, lng1, lat2, lng2):
        """
        Calculate distance between two points using Haversine formula.
        Returns distance in kilometers.
        """
        # Convert latitude and longitude to radians
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        r = 6371  # Radius of Earth in kilometers
        
        # Calculate distance
        distance = c * r
        
        return distance
