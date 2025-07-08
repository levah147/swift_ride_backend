"""
Profile service for managing user profiles.
"""

from typing import List, Dict, Any, Optional
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from geopy.distance import geodesic
import logging

from ..models import DriverProfile, RiderProfile
from ..utils import calculate_distance

User = get_user_model()
logger = logging.getLogger(__name__)


class ProfileService:
    """
    Service class for profile-related operations.
    """
    
    def get_nearby_drivers(self, latitude: float, longitude: float, radius: float = 5) -> List[Dict[str, Any]]:
        """
        Get nearby available drivers within specified radius.
        """
        try:
            # Get online drivers with location data
            online_drivers = DriverProfile.objects.filter(
                is_online=True,
                user__is_active=True,
                user__is_verified=True,
                user__current_latitude__isnull=False,
                user__current_longitude__isnull=False
            ).select_related('user')
            
            nearby_drivers = []
            
            for driver_profile in online_drivers:
                driver_lat = float(driver_profile.user.current_latitude)
                driver_lon = float(driver_profile.user.current_longitude)
                
                # Calculate distance
                distance = calculate_distance(latitude, longitude, driver_lat, driver_lon)
                
                if distance <= radius:
                    nearby_drivers.append({
                        'driver_id': driver_profile.user.id,
                        'name': f"{driver_profile.user.first_name} {driver_profile.user.last_name}",
                        'rating': driver_profile.rating or 0,
                        'total_reviews': driver_profile.total_reviews or 0,
                        'distance': round(distance, 2),
                        'vehicle_info': {
                            'make': driver_profile.vehicle.make if driver_profile.vehicle else None,
                            'model': driver_profile.vehicle.model if driver_profile.vehicle else None,
                            'color': driver_profile.vehicle.color if driver_profile.vehicle else None,
                            'plate_number': driver_profile.vehicle.plate_number if driver_profile.vehicle else None,
                        } if driver_profile.vehicle else None,
                        'location': {
                            'latitude': driver_lat,
                            'longitude': driver_lon
                        },
                        'estimated_arrival': self._calculate_eta(distance)
                    })
            
            # Sort by distance
            nearby_drivers.sort(key=lambda x: x['distance'])
            
            return nearby_drivers
            
        except Exception as e:
            logger.error(f"Error getting nearby drivers: {str(e)}")
            return []
    
    def update_driver_status(self, driver_user, is_online: bool) -> bool:
        """
        Update driver online/offline status.
        """
        try:
            driver_profile, created = DriverProfile.objects.get_or_create(user=driver_user)
            driver_profile.is_online = is_online
            driver_profile.last_location_update = timezone.now()
            driver_profile.save()
            
            logger.info(f"Driver {driver_user.id} status updated to {'online' if is_online else 'offline'}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating driver status for user {driver_user.id}: {str(e)}")
            return False
    
    def get_driver_profile_completion(self, driver_user) -> Dict[str, Any]:
        """
        Get driver profile completion status.
        """
        try:
            driver_profile = DriverProfile.objects.get(user=driver_user)
            
            required_fields = [
                'license_number', 'license_expiry', 'vehicle',
                'emergency_contact', 'bank_account_number'
            ]
            
            completed_fields = 0
            missing_fields = []
            
            for field in required_fields:
                if getattr(driver_profile, field, None):
                    completed_fields += 1
                else:
                    missing_fields.append(field)
            
            # Check user basic info
            user_fields = ['first_name', 'last_name', 'email', 'phone_number']
            for field in user_fields:
                if getattr(driver_user, field, None):
                    completed_fields += 1
                else:
                    missing_fields.append(field)
            
            total_fields = len(required_fields) + len(user_fields)
            completion_percentage = (completed_fields / total_fields) * 100
            
            return {
                'completion_percentage': round(completion_percentage, 1),
                'completed_fields': completed_fields,
                'total_fields': total_fields,
                'missing_fields': missing_fields,
                'can_go_online': completion_percentage >= 80
            }
            
        except DriverProfile.DoesNotExist:
            return {
                'completion_percentage': 0,
                'completed_fields': 0,
                'total_fields': 9,
                'missing_fields': ['All fields'],
                'can_go_online': False
            }
        except Exception as e:
            logger.error(f"Error getting driver profile completion for user {driver_user.id}: {str(e)}")
            return {}
    
    def get_rider_profile_completion(self, rider_user) -> Dict[str, Any]:
        """
        Get rider profile completion status.
        """
        try:
            rider_profile, created = RiderProfile.objects.get_or_create(user=rider_user)
            
            required_fields = ['emergency_contact', 'preferred_payment_method']
            completed_fields = 0
            missing_fields = []
            
            for field in required_fields:
                if getattr(rider_profile, field, None):
                    completed_fields += 1
                else:
                    missing_fields.append(field)
            
            # Check user basic info
            user_fields = ['first_name', 'last_name', 'email', 'phone_number']
            for field in user_fields:
                if getattr(rider_user, field, None):
                    completed_fields += 1
                else:
                    missing_fields.append(field)
            
            total_fields = len(required_fields) + len(user_fields)
            completion_percentage = (completed_fields / total_fields) * 100
            
            return {
                'completion_percentage': round(completion_percentage, 1),
                'completed_fields': completed_fields,
                'total_fields': total_fields,
                'missing_fields': missing_fields,
                'is_complete': completion_percentage >= 80
            }
            
        except Exception as e:
            logger.error(f"Error getting rider profile completion for user {rider_user.id}: {str(e)}")
            return {}
    
    def update_profile_picture(self, user, image_file) -> bool:
        """
        Update user profile picture.
        """
        try:
            user.profile_picture = image_file
            user.save(update_fields=['profile_picture'])
            
            logger.info(f"Profile picture updated for user {user.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating profile picture for user {user.id}: {str(e)}")
            return False
    
    def get_driver_earnings_summary(self, driver_user, period: str = 'month') -> Dict[str, Any]:
        """
        Get driver earnings summary for specified period.
        """
        try:
            from apps.rides.models import Ride
            from datetime import timedelta
            
            # Calculate date range based on period
            now = timezone.now()
            if period == 'week':
                start_date = now - timedelta(days=7)
            elif period == 'month':
                start_date = now - timedelta(days=30)
            elif period == 'year':
                start_date = now - timedelta(days=365)
            else:
                start_date = now - timedelta(days=30)  # Default to month
            
            # Get completed rides in the period
            rides = Ride.objects.filter(
                driver=driver_user,
                status='completed',
                completed_at__gte=start_date
            )
            
            total_earnings = sum(ride.fare_amount or 0 for ride in rides)
            total_rides = rides.count()
            
            return {
                'period': period,
                'total_earnings': total_earnings,
                'total_rides': total_rides,
                'average_per_ride': total_earnings / total_rides if total_rides > 0 else 0,
                'start_date': start_date.date(),
                'end_date': now.date()
            }
            
        except Exception as e:
            logger.error(f"Error getting driver earnings for user {driver_user.id}: {str(e)}")
            return {}
    
    def _calculate_eta(self, distance_km: float) -> int:
        """
        Calculate estimated time of arrival in minutes.
        """
        # Assume average speed of 30 km/h in city traffic
        average_speed = 30
        eta_hours = distance_km / average_speed
        eta_minutes = eta_hours * 60
        
        # Add buffer time
        eta_minutes += 2
        
        return max(1, int(eta_minutes))  # Minimum 1 minute
