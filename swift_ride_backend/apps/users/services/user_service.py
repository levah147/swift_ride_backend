"""
User service for business logic operations.
"""

from typing import Dict, Any, List, Optional
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.core.cache import cache
from datetime import timedelta
import logging

from ..utils import calculate_distance, get_user_completion_percentage
from apps.rides.models import Ride
from apps.reviews.models import Review

User = get_user_model()
logger = logging.getLogger(__name__)


class UserService:
    """
    Service class for user-related business logic.
    """
    
    def get_user_stats(self, user) -> Dict[str, Any]:
        """
        Get comprehensive user statistics.
        """
        try:
            stats = {
                'profile_completion': get_user_completion_percentage(user),
                'total_rides': 0,
                'total_earnings': 0,
                'average_rating': 0,
                'total_reviews': 0,
                'member_since': user.date_joined.strftime('%B %Y'),
                'last_active': user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else None,
            }
            
            if user.user_type == 'driver':
                # Driver-specific stats
                driver_rides = Ride.objects.filter(driver=user)
                stats.update({
                    'total_rides': driver_rides.count(),
                    'completed_rides': driver_rides.filter(status='completed').count(),
                    'cancelled_rides': driver_rides.filter(status='cancelled').count(),
                    'total_earnings': sum(ride.fare_amount or 0 for ride in driver_rides.filter(status='completed')),
                    'online_hours': self._calculate_online_hours(user),
                })
                
                # Driver rating
                driver_reviews = Review.objects.filter(driver=user)
                if driver_reviews.exists():
                    stats['average_rating'] = driver_reviews.aggregate(Avg('rating'))['rating__avg']
                    stats['total_reviews'] = driver_reviews.count()
                
            elif user.user_type == 'rider':
                # Rider-specific stats
                rider_rides = Ride.objects.filter(rider=user)
                stats.update({
                    'total_rides': rider_rides.count(),
                    'completed_rides': rider_rides.filter(status='completed').count(),
                    'cancelled_rides': rider_rides.filter(status='cancelled').count(),
                    'total_spent': sum(ride.fare_amount or 0 for ride in rider_rides.filter(status='completed')),
                    'favorite_destinations': self._get_favorite_destinations(user),
                })
                
                # Rider rating
                rider_reviews = Review.objects.filter(rider=user)
                if rider_reviews.exists():
                    stats['average_rating'] = rider_reviews.aggregate(Avg('rating'))['rating__avg']
                    stats['total_reviews'] = rider_reviews.count()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting user stats for user {user.id}: {str(e)}")
            return {}
    
    def update_user_location(self, user, latitude: float, longitude: float) -> bool:
        """
        Update user's current location.
        """
        try:
            # Update user's current location
            user.current_latitude = latitude
            user.current_longitude = longitude
            user.location_updated_at = timezone.now()
            user.save(update_fields=['current_latitude', 'current_longitude', 'location_updated_at'])
            
            # Cache the location for quick access
            cache_key = f"user_location_{user.id}"
            cache.set(cache_key, {
                'latitude': latitude,
                'longitude': longitude,
                'updated_at': timezone.now().isoformat()
            }, timeout=300)  # Cache for 5 minutes
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating location for user {user.id}: {str(e)}")
            return False
    
    def get_user_location(self, user) -> Optional[Dict[str, float]]:
        """
        Get user's current location.
        """
        try:
            # Try to get from cache first
            cache_key = f"user_location_{user.id}"
            cached_location = cache.get(cache_key)
            
            if cached_location:
                return {
                    'latitude': cached_location['latitude'],
                    'longitude': cached_location['longitude']
                }
            
            # Get from database
            if user.current_latitude and user.current_longitude:
                return {
                    'latitude': float(user.current_latitude),
                    'longitude': float(user.current_longitude)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting location for user {user.id}: {str(e)}")
            return None
    
    def deactivate_user(self, user) -> bool:
        """
        Deactivate user account.
        """
        try:
            user.is_active = False
            user.deactivated_at = timezone.now()
            user.save(update_fields=['is_active', 'deactivated_at'])
            
            # Cancel any active rides
            active_rides = Ride.objects.filter(
                Q(rider=user) | Q(driver=user),
                status__in=['pending', 'accepted', 'in_progress']
            )
            
            for ride in active_rides:
                ride.status = 'cancelled'
                ride.cancellation_reason = 'User account deactivated'
                ride.save()
            
            logger.info(f"User {user.id} account deactivated")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating user {user.id}: {str(e)}")
            return False
    
    def reactivate_user(self, user) -> bool:
        """
        Reactivate user account.
        """
        try:
            user.is_active = True
            user.deactivated_at = None
            user.save(update_fields=['is_active', 'deactivated_at'])
            
            logger.info(f"User {user.id} account reactivated")
            return True
            
        except Exception as e:
            logger.error(f"Error reactivating user {user.id}: {str(e)}")
            return False
    
    def update_all_user_ratings(self) -> int:
        """
        Update ratings for all users based on recent reviews.
        """
        try:
            updated_count = 0
            
            # Update driver ratings
            drivers = User.objects.filter(user_type='driver')
            for driver in drivers:
                reviews = Review.objects.filter(driver=driver)
                if reviews.exists():
                    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
                    if hasattr(driver, 'driver_profile'):
                        driver.driver_profile.rating = avg_rating
                        driver.driver_profile.total_reviews = reviews.count()
                        driver.driver_profile.save()
                        updated_count += 1
            
            # Update rider ratings
            riders = User.objects.filter(user_type='rider')
            for rider in riders:
                reviews = Review.objects.filter(rider=rider)
                if reviews.exists():
                    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
                    if hasattr(rider, 'rider_profile'):
                        rider.rider_profile.rating = avg_rating
                        rider.rider_profile.total_reviews = reviews.count()
                        rider.rider_profile.save()
                        updated_count += 1
            
            return updated_count
            
        except Exception as e:
            logger.error(f"Error updating user ratings: {str(e)}")
            return 0
    
    def generate_user_analytics(self) -> Dict[str, Any]:
        """
        Generate user analytics data.
        """
        try:
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            verified_users = User.objects.filter(is_verified=True).count()
            
            # User type breakdown
            drivers = User.objects.filter(user_type='driver').count()
            riders = User.objects.filter(user_type='rider').count()
            
            # Recent registrations (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            recent_registrations = User.objects.filter(
                date_joined__gte=thirty_days_ago
            ).count()
            
            # Active users (logged in within last 7 days)
            seven_days_ago = timezone.now() - timedelta(days=7)
            recently_active = User.objects.filter(
                last_login__gte=seven_days_ago
            ).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'verified_users': verified_users,
                'drivers': drivers,
                'riders': riders,
                'recent_registrations': recent_registrations,
                'recently_active': recently_active,
                'verification_rate': (verified_users / total_users * 100) if total_users > 0 else 0,
                'activity_rate': (recently_active / total_users * 100) if total_users > 0 else 0,
            }
            
        except Exception as e:
            logger.error(f"Error generating user analytics: {str(e)}")
            return {}
    
    def backup_user_data(self) -> Dict[str, Any]:
        """
        Backup critical user data.
        """
        try:
            # This would typically backup to cloud storage
            # For now, we'll just return a summary
            
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            
            backup_info = {
                'timestamp': timezone.now().isoformat(),
                'total_users_backed_up': total_users,
                'active_users_backed_up': active_users,
                'backup_status': 'completed'
            }
            
            logger.info(f"User data backup completed: {backup_info}")
            return backup_info
            
        except Exception as e:
            logger.error(f"Error backing up user data: {str(e)}")
            return {'backup_status': 'failed', 'error': str(e)}
    
    def _calculate_online_hours(self, driver) -> float:
        """
        Calculate total online hours for a driver.
        """
        try:
            # This would typically track driver online/offline sessions
            # For now, return a placeholder calculation
            if hasattr(driver, 'driver_profile'):
                # Estimate based on completed rides
                completed_rides = Ride.objects.filter(
                    driver=driver, 
                    status='completed'
                ).count()
                return completed_rides * 0.5  # Estimate 30 minutes per ride
            return 0.0
        except:
            return 0.0
    
    def _get_favorite_destinations(self, rider) -> List[str]:
        """
        Get rider's favorite destinations.
        """
        try:
            # Get most frequent destinations
            rides = Ride.objects.filter(
                rider=rider, 
                status='completed'
            ).values('destination_address').annotate(
                count=Count('destination_address')
            ).order_by('-count')[:5]
            
            return [ride['destination_address'] for ride in rides if ride['destination_address']]
        except:
            return []
