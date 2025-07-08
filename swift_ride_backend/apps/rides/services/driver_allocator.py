"""
Driver allocation service for matching drivers to rides.
"""

from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q, Avg, Count
from django.core.cache import cache

from apps.rides.models import Ride
from apps.users.models import User
from apps.rides.utils import calculate_distance
from apps.rides.services.route_optimizer import RouteOptimizer


class DriverAllocator:
    """
    Service for intelligently allocating drivers to ride requests.
    """
    
    # Allocation parameters
    MAX_SEARCH_RADIUS_KM = 15
    MAX_ALLOCATION_TIME_MINUTES = 10
    DRIVER_SCORE_CACHE_TIMEOUT = 300  # 5 minutes
    
    # Scoring weights
    WEIGHT_DISTANCE = 0.25
    WEIGHT_RATING = 0.20
    WEIGHT_ACCEPTANCE_RATE = 0.15
    WEIGHT_COMPLETION_RATE = 0.15
    WEIGHT_AVAILABILITY = 0.10
    WEIGHT_VEHICLE_MATCH = 0.10
    WEIGHT_EARNINGS_POTENTIAL = 0.05
    
    @classmethod
    def find_best_drivers(cls, ride: Ride, limit: int = 10) -> List[Dict]:
        """
        Find the best available drivers for a ride request.
        """
        # Get available drivers in the area
        available_drivers = cls._get_available_drivers(
            float(ride.pickup_latitude),
            float(ride.pickup_longitude),
            cls.MAX_SEARCH_RADIUS_KM
        )
        
        if not available_drivers:
            return []
        
        # Score each driver
        driver_scores = []
        for driver in available_drivers:
            score = cls._calculate_driver_score(driver, ride)
            if score > 0:  # Only include drivers with positive scores
                driver_scores.append({
                    'driver': driver,
                    'score': score,
                    'distance_km': cls._calculate_distance_to_pickup(driver, ride),
                    'estimated_arrival_minutes': cls._estimate_arrival_time(driver, ride),
                    'score_breakdown': cls._get_score_breakdown(driver, ride)
                })
        
        # Sort by score (highest first) and return top drivers
        driver_scores.sort(key=lambda x: x['score'], reverse=True)
        return driver_scores[:limit]
    
    @classmethod
    def allocate_driver_automatically(cls, ride: Ride) -> Tuple[bool, str, Optional[User]]:
        """
        Automatically allocate the best available driver to a ride.
        """
        best_drivers = cls.find_best_drivers(ride, limit=1)
        
        if not best_drivers:
            return False, "No available drivers found", None
        
        best_driver_data = best_drivers[0]
        driver = best_driver_data['driver']
        
        # Check if driver is still available
        if not cls._is_driver_available(driver):
            return False, "Selected driver is no longer available", None
        
        # Assign driver to ride
        ride.driver = driver
        ride.status = Ride.RideStatus.DRIVER_ASSIGNED
        ride.save()
        
        # Update driver availability
        cls._mark_driver_busy(driver)
        
        # Create history entry
        from apps.rides.models import RideHistory
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.SYSTEM,
            description=f"Driver {driver.get_full_name()} automatically allocated",
            metadata={
                'driver_id': str(driver.id),
                'allocation_score': best_driver_data['score'],
                'distance_km': best_driver_data['distance_km']
            }
        )
        
        return True, "Driver allocated successfully", driver
    
    @classmethod
    def broadcast_ride_to_drivers(cls, ride: Ride, max_drivers: int = 5) -> List[User]:
        """
        Broadcast ride request to multiple drivers simultaneously.
        """
        best_drivers = cls.find_best_drivers(ride, limit=max_drivers)
        
        if not best_drivers:
            return []
        
        broadcasted_drivers = []
        
        for driver_data in best_drivers:
            driver = driver_data['driver']
            
            # Send ride request notification
            from apps.notifications.services.notification_service import NotificationService
            NotificationService.send_ride_request_notification(
                ride, driver, driver_data['estimated_arrival_minutes']
            )
            
            broadcasted_drivers.append(driver)
        
        # Cache the broadcast for tracking responses
        cache.set(
            f"ride_broadcast_{ride.id}",
            {
                'drivers': [str(d.id) for d in broadcasted_drivers],
                'broadcast_time': timezone.now().isoformat()
            },
            timeout=600  # 10 minutes
        )
        
        return broadcasted_drivers
    
    @classmethod
    def handle_driver_response(cls, ride: Ride, driver: User, response: str) -> Tuple[bool, str]:
        """
        Handle driver response to ride request (accept/reject).
        """
        if response == 'accept':
            return cls._handle_driver_acceptance(ride, driver)
        elif response == 'reject':
            return cls._handle_driver_rejection(ride, driver)
        else:
            return False, "Invalid response"
    
    @classmethod
    def reallocate_ride(cls, ride: Ride, reason: str = "") -> Tuple[bool, str]:
        """
        Reallocate a ride to a different driver.
        """
        # Clear current driver
        previous_driver = ride.driver
        ride.driver = None
        ride.status = Ride.RideStatus.SEARCHING
        ride.save()
        
        # Mark previous driver as available again
        if previous_driver:
            cls._mark_driver_available(previous_driver)
        
        # Create history entry
        from apps.rides.models import RideHistory
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.SYSTEM,
            description=f"Ride reallocated. Reason: {reason}",
            metadata={
                'previous_driver_id': str(previous_driver.id) if previous_driver else None,
                'reallocation_reason': reason
            }
        )
        
        # Try to allocate new driver
        success, message, new_driver = cls.allocate_driver_automatically(ride)
        
        if success:
            return True, f"Ride reallocated to {new_driver.get_full_name()}"
        else:
            # Broadcast to multiple drivers
            broadcasted_drivers = cls.broadcast_ride_to_drivers(ride)
            if broadcasted_drivers:
                return True, f"Ride broadcasted to {len(broadcasted_drivers)} drivers"
            else:
                return False, "No available drivers for reallocation"
    
    @classmethod
    def get_driver_allocation_stats(cls, driver: User, days: int = 30) -> Dict:
        """
        Get allocation statistics for a driver.
        """
        since = timezone.now() - timedelta(days=days)
        
        # Get rides assigned to this driver
        assigned_rides = Ride.objects.filter(
            driver=driver,
            created_at__gte=since
        )
        
        total_assigned = assigned_rides.count()
        completed_rides = assigned_rides.filter(status=Ride.RideStatus.COMPLETED)
        cancelled_rides = assigned_rides.filter(status=Ride.RideStatus.CANCELLED)
        
        # Calculate rates
        completion_rate = (completed_rides.count() / total_assigned * 100) if total_assigned > 0 else 0
        cancellation_rate = (cancelled_rides.count() / total_assigned * 100) if total_assigned > 0 else 0
        
        # Calculate average ratings
        avg_rating = completed_rides.aggregate(
            avg_rating=Avg('driver_rating')
        )['avg_rating'] or 0
        
        # Calculate earnings
        total_earnings = completed_rides.aggregate(
            total=models.Sum('final_fare')
        )['total'] or Decimal('0.00')
        
        return {
            'total_rides_assigned': total_assigned,
            'completed_rides': completed_rides.count(),
            'cancelled_rides': cancelled_rides.count(),
            'completion_rate': round(completion_rate, 2),
            'cancellation_rate': round(cancellation_rate, 2),
            'average_rating': round(float(avg_rating), 2),
            'total_earnings': float(total_earnings),
            'average_earnings_per_ride': float(total_earnings / completed_rides.count()) if completed_rides.count() > 0 else 0
        }
    
    @classmethod
    def _get_available_drivers(cls, pickup_lat: float, pickup_lon: float, 
                             radius_km: float) -> List[User]:
        """
        Get available drivers within a specified radius.
        """
        # Get drivers who are online and available
        available_drivers = User.objects.filter(
            is_driver=True,
            is_active=True,
            driver_profile__is_active=True,
            driver_profile__is_verified=True,
            driver_profile__is_online=True
        ).select_related('driver_profile')
        
        # Filter by location (simplified - in production, use PostGIS)
        nearby_drivers = []
        for driver in available_drivers:
            # Get driver's current location from cache
            from apps.rides.services.ride_tracker import RideTracker
            location = RideTracker.get_driver_location(str(driver.id))
            
            if location:
                distance = calculate_distance(
                    pickup_lat, pickup_lon,
                    location['latitude'], location['longitude']
                )
                
                if distance <= radius_km:
                    nearby_drivers.append(driver)
        
        return nearby_drivers
    
    @classmethod
    def _calculate_driver_score(cls, driver: User, ride: Ride) -> float:
        """
        Calculate overall score for a driver for a specific ride.
        """
        cache_key = f"driver_score_{driver.id}_{ride.id}"
        cached_score = cache.get(cache_key)
        
        if cached_score is not None:
            return cached_score
        
        score = 0.0
        
        # Distance score (closer is better)
        distance_score = cls._calculate_distance_score(driver, ride)
        score += distance_score * cls.WEIGHT_DISTANCE
        
        # Rating score
        rating_score = cls._calculate_rating_score(driver)
        score += rating_score * cls.WEIGHT_RATING
        
        # Acceptance rate score
        acceptance_score = cls._calculate_acceptance_rate_score(driver)
        score += acceptance_score * cls.WEIGHT_ACCEPTANCE_RATE
        
        # Completion rate score
        completion_score = cls._calculate_completion_rate_score(driver)
        score += completion_score * cls.WEIGHT_COMPLETION_RATE
        
        # Availability score
        availability_score = cls._calculate_availability_score(driver)
        score += availability_score * cls.WEIGHT_AVAILABILITY
        
        # Vehicle match score
        vehicle_score = cls._calculate_vehicle_match_score(driver, ride)
        score += vehicle_score * cls.WEIGHT_VEHICLE_MATCH
        
        # Earnings potential score
        earnings_score = cls._calculate_earnings_potential_score(driver, ride)
        score += earnings_score * cls.WEIGHT_EARNINGS_POTENTIAL
        
        # Cache the score
        cache.set(cache_key, score, timeout=cls.DRIVER_SCORE_CACHE_TIMEOUT)
        
        return score
    
    @classmethod
    def _calculate_distance_score(cls, driver: User, ride: Ride) -> float:
        """
        Calculate distance-based score (0-1, closer is better).
        """
        distance = cls._calculate_distance_to_pickup(driver, ride)
        
        if distance is None:
            return 0.0
        
        # Normalize distance score (closer = higher score)
        max_distance = cls.MAX_SEARCH_RADIUS_KM
        score = max(0, 1 - (distance / max_distance))
        
        return score
    
    @classmethod
    def _calculate_rating_score(cls, driver: User) -> float:
        """
        Calculate rating-based score (0-1).
        """
        # Get average rating from completed rides
        avg_rating = Ride.objects.filter(
            driver=driver,
            status=Ride.RideStatus.COMPLETED,
            driver_rating__isnull=False
        ).aggregate(avg_rating=Avg('driver_rating'))['avg_rating']
        
        if avg_rating is None:
            return 0.5  # Neutral score for new drivers
        
        # Normalize to 0-1 scale (5-star rating system)
        return (avg_rating - 1) / 4
    
    @classmethod
    def _calculate_acceptance_rate_score(cls, driver: User) -> float:
        """
        Calculate acceptance rate score (0-1).
        """
        # This would track ride request acceptances vs rejections
        # For now, return a default score
        return 0.8
    
    @classmethod
    def _calculate_completion_rate_score(cls, driver: User) -> float:
        """
        Calculate completion rate score (0-1).
        """
        total_rides = Ride.objects.filter(driver=driver).count()
        completed_rides = Ride.objects.filter(
            driver=driver,
            status=Ride.RideStatus.COMPLETED
        ).count()
        
        if total_rides == 0:
            return 0.5  # Neutral score for new drivers
        
        return completed_rides / total_rides
    
    @classmethod
    def _calculate_availability_score(cls, driver: User) -> float:
        """
        Calculate availability score based on current status.
        """
        if not hasattr(driver, 'driver_profile'):
            return 0.0
        
        profile = driver.driver_profile
        
        if not profile.is_online:
            return 0.0
        
        # Check if driver has active rides
        active_rides = Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.RideStatus.DRIVER_ASSIGNED,
                Ride.RideStatus.DRIVER_ARRIVED,
                Ride.RideStatus.IN_PROGRESS
            ]
        ).count()
        
        if active_rides > 0:
            return 0.3  # Lower score if busy
        
        return 1.0  # Full score if completely available
    
    @classmethod
    def _calculate_vehicle_match_score(cls, driver: User, ride: Ride) -> float:
        """
        Calculate vehicle match score.
        """
        # This would check if driver's vehicle matches ride requirements
        # For now, return a default score
        return 0.8
    
    @classmethod
    def _calculate_earnings_potential_score(cls, driver: User, ride: Ride) -> float:
        """
        Calculate earnings potential score.
        """
        # Higher fare rides get higher scores
        if ride.estimated_fare:
            # Normalize based on average fare (assume 800 Naira average)
            score = min(float(ride.estimated_fare) / 1600, 1.0)
            return score
        
        return 0.5
    
    @classmethod
    def _calculate_distance_to_pickup(cls, driver: User, ride: Ride) -> Optional[float]:
        """
        Calculate distance from driver to pickup location.
        """
        from apps.rides.services.ride_tracker import RideTracker
        
        driver_location = RideTracker.get_driver_location(str(driver.id))
        if not driver_location:
            return None
        
        return calculate_distance(
            driver_location['latitude'], driver_location['longitude'],
            float(ride.pickup_latitude), float(ride.pickup_longitude)
        )
    
    @classmethod
    def _estimate_arrival_time(cls, driver: User, ride: Ride) -> int:
        """
        Estimate driver arrival time in minutes.
        """
        distance = cls._calculate_distance_to_pickup(driver, ride)
        if distance is None:
            return 15  # Default estimate
        
        # Estimate based on average city speed (25 km/h)
        time_minutes = (distance / 25) * 60
        return max(int(time_minutes), 5)  # Minimum 5 minutes
    
    @classmethod
    def _get_score_breakdown(cls, driver: User, ride: Ride) -> Dict:
        """
        Get detailed score breakdown for transparency.
        """
        return {
            'distance_score': cls._calculate_distance_score(driver, ride),
            'rating_score': cls._calculate_rating_score(driver),
            'acceptance_rate_score': cls._calculate_acceptance_rate_score(driver),
            'completion_rate_score': cls._calculate_completion_rate_score(driver),
            'availability_score': cls._calculate_availability_score(driver),
            'vehicle_match_score': cls._calculate_vehicle_match_score(driver, ride),
            'earnings_potential_score': cls._calculate_earnings_potential_score(driver, ride)
        }
    
    @classmethod
    def _is_driver_available(cls, driver: User) -> bool:
        """
        Check if driver is currently available.
        """
        if not hasattr(driver, 'driver_profile'):
            return False
        
        profile = driver.driver_profile
        
        if not (profile.is_active and profile.is_verified and profile.is_online):
            return False
        
        # Check for active rides
        active_rides = Ride.objects.filter(
            driver=driver,
            status__in=[
                Ride.RideStatus.DRIVER_ASSIGNED,
                Ride.RideStatus.DRIVER_ARRIVED,
                Ride.RideStatus.IN_PROGRESS
            ]
        ).exists()
        
        return not active_rides
    
    @classmethod
    def _mark_driver_busy(cls, driver: User):
        """
        Mark driver as busy (has active ride).
        """
        # This could update a cache or database field
        # For now, we rely on active ride status
        pass
    
    @classmethod
    def _mark_driver_available(cls, driver: User):
        """
        Mark driver as available again.
        """
        # This could update a cache or database field
        # For now, we rely on active ride status
        pass
    
    @classmethod
    def _handle_driver_acceptance(cls, ride: Ride, driver: User) -> Tuple[bool, str]:
        """
        Handle driver accepting a ride request.
        """
        # Check if ride is still available
        if ride.status != Ride.RideStatus.SEARCHING:
            return False, "Ride is no longer available"
        
        # Check if driver is still available
        if not cls._is_driver_available(driver):
            return False, "Driver is no longer available"
        
        # Assign driver to ride
        ride.driver = driver
        ride.status = Ride.RideStatus.DRIVER_ASSIGNED
        ride.save()
        
        # Mark driver as busy
        cls._mark_driver_busy(driver)
        
        # Clear broadcast cache
        cache.delete(f"ride_broadcast_{ride.id}")
        
        # Create history entry
        from apps.rides.models import RideHistory
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.STATUS_CHANGE,
            previous_status=Ride.RideStatus.SEARCHING,
            new_status=Ride.RideStatus.DRIVER_ASSIGNED,
            description=f"Driver {driver.get_full_name()} accepted ride request",
            metadata={'driver_id': str(driver.id)}
        )
        
        # Send notifications
        from apps.notifications.services.notification_service import NotificationService
        NotificationService.send_ride_status_notification(ride, 'driver_assigned')
        
        return True, "Ride accepted successfully"
    
    @classmethod
    def _handle_driver_rejection(cls, ride: Ride, driver: User) -> Tuple[bool, str]:
        """
        Handle driver rejecting a ride request.
        """
        # Create history entry
        from apps.rides.models import RideHistory
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.SYSTEM,
            description=f"Driver {driver.get_full_name()} rejected ride request",
            metadata={'driver_id': str(driver.id)}
        )
        
        # Check if we should reallocate or continue broadcasting
        broadcast_data = cache.get(f"ride_broadcast_{ride.id}")
        if broadcast_data:
            remaining_drivers = [
                d for d in broadcast_data['drivers'] 
                if d != str(driver.id)
            ]
            
            if remaining_drivers:
                # Update broadcast cache
                broadcast_data['drivers'] = remaining_drivers
                cache.set(f"ride_broadcast_{ride.id}", broadcast_data, timeout=600)
                return True, "Rejection recorded, waiting for other drivers"
            else:
                # No more drivers in broadcast, try to find new ones
                new_drivers = cls.broadcast_ride_to_drivers(ride)
                if new_drivers:
                    return True, "Broadcasted to new drivers"
                else:
                    return False, "No more available drivers"
        
        return True, "Rejection recorded"
