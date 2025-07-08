"""
Real-time ride tracking service.
"""

from decimal import Decimal
from datetime import timedelta
from typing import Dict, Optional, Tuple
from django.utils import timezone
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.rides.models import Ride, TripStatus, RideHistory
from apps.rides.utils import calculate_distance, calculate_bearing, estimate_arrival_time


class RideTracker:
    """
    Service for tracking rides in real-time.
    """
    
    # Cache keys
    DRIVER_LOCATION_KEY = "driver_location:{driver_id}"
    RIDE_TRACKING_KEY = "ride_tracking:{ride_id}"
    
    # Tracking configuration
    LOCATION_UPDATE_INTERVAL = 30  # seconds
    STALE_LOCATION_THRESHOLD = 300  # 5 minutes
    ARRIVAL_THRESHOLD_METERS = 100  # Consider arrived within 100m
    
    @classmethod
    def start_tracking(cls, ride: Ride) -> Tuple[bool, str]:
        """
        Start tracking a ride.
        """
        if ride.status not in [
            Ride.RideStatus.DRIVER_ASSIGNED,
            Ride.RideStatus.DRIVER_ARRIVED,
            Ride.RideStatus.IN_PROGRESS
        ]:
            return False, "Ride is not in a trackable status"
        
        # Create or update trip status
        trip_status, created = TripStatus.objects.get_or_create(
            ride=ride,
            defaults={
                'is_tracking_active': True,
                'last_updated': timezone.now()
            }
        )
        
        if not created:
            trip_status.is_tracking_active = True
            trip_status.last_updated = timezone.now()
            trip_status.save()
        
        # Initialize tracking cache
        tracking_data = {
            'ride_id': str(ride.id),
            'status': ride.status,
            'started_at': timezone.now().isoformat(),
            'driver_id': str(ride.driver.id) if ride.driver else None,
            'rider_id': str(ride.rider.id),
        }
        
        cache.set(
            cls.RIDE_TRACKING_KEY.format(ride_id=ride.id),
            tracking_data,
            timeout=3600  # 1 hour
        )
        
        # Create history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.SYSTEM,
            description="Ride tracking started",
            metadata={'tracking_started': True}
        )
        
        return True, "Tracking started successfully"
    
    @classmethod
    def stop_tracking(cls, ride: Ride) -> Tuple[bool, str]:
        """
        Stop tracking a ride.
        """
        try:
            trip_status = TripStatus.objects.get(ride=ride)
            trip_status.is_tracking_active = False
            trip_status.save()
        except TripStatus.DoesNotExist:
            pass
        
        # Clear tracking cache
        cache.delete(cls.RIDE_TRACKING_KEY.format(ride_id=ride.id))
        
        # Create history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.SYSTEM,
            description="Ride tracking stopped",
            metadata={'tracking_stopped': True}
        )
        
        return True, "Tracking stopped successfully"
    
    @classmethod
    def update_driver_location(cls, driver_id: str, latitude: float, longitude: float,
                             heading: Optional[float] = None, speed: Optional[float] = None) -> bool:
        """
        Update driver's current location.
        """
        location_data = {
            'latitude': latitude,
            'longitude': longitude,
            'heading': heading,
            'speed': speed,
            'timestamp': timezone.now().isoformat(),
            'driver_id': driver_id
        }
        
        # Cache the location
        cache.set(
            cls.DRIVER_LOCATION_KEY.format(driver_id=driver_id),
            location_data,
            timeout=600  # 10 minutes
        )
        
        # Update active rides for this driver
        active_rides = Ride.objects.filter(
            driver_id=driver_id,
            status__in=[
                Ride.RideStatus.DRIVER_ASSIGNED,
                Ride.RideStatus.DRIVER_ARRIVED,
                Ride.RideStatus.IN_PROGRESS
            ]
        )
        
        for ride in active_rides:
            cls._update_ride_tracking(ride, latitude, longitude, heading, speed)
        
        return True
    
    @classmethod
    def get_driver_location(cls, driver_id: str) -> Optional[Dict]:
        """
        Get driver's current location from cache.
        """
        return cache.get(cls.DRIVER_LOCATION_KEY.format(driver_id=driver_id))
    
    @classmethod
    def get_ride_tracking_data(cls, ride: Ride) -> Optional[Dict]:
        """
        Get comprehensive tracking data for a ride.
        """
        try:
            trip_status = TripStatus.objects.get(ride=ride)
        except TripStatus.DoesNotExist:
            return None
        
        # Get driver location
        driver_location = None
        if ride.driver:
            driver_location = cls.get_driver_location(str(ride.driver.id))
        
        # Calculate ETA
        eta_minutes = None
        if driver_location:
            if ride.status == Ride.RideStatus.DRIVER_ASSIGNED:
                # ETA to pickup
                distance = calculate_distance(
                    driver_location['latitude'], driver_location['longitude'],
                    float(ride.pickup_latitude), float(ride.pickup_longitude)
                )
                eta_minutes = estimate_arrival_time(distance)
            
            elif ride.status == Ride.RideStatus.IN_PROGRESS:
                # ETA to destination
                distance = calculate_distance(
                    driver_location['latitude'], driver_location['longitude'],
                    float(ride.dropoff_latitude), float(ride.dropoff_longitude)
                )
                eta_minutes = estimate_arrival_time(distance)
        
        return {
            'ride_id': str(ride.id),
            'status': ride.status,
            'is_tracking_active': trip_status.is_tracking_active,
            'driver_location': driver_location,
            'pickup_location': {
                'latitude': float(ride.pickup_latitude),
                'longitude': float(ride.pickup_longitude),
                'address': ride.pickup_location
            },
            'dropoff_location': {
                'latitude': float(ride.dropoff_latitude),
                'longitude': float(ride.dropoff_longitude),
                'address': ride.dropoff_location
            },
            'distance_to_pickup': float(trip_status.distance_to_pickup or 0),
            'distance_to_dropoff': float(trip_status.distance_to_dropoff or 0),
            'eta_minutes': eta_minutes,
            'is_driver_moving': trip_status.is_driver_moving,
            'last_updated': trip_status.last_updated.isoformat() if trip_status.last_updated else None
        }
    
    @classmethod
    def check_arrival_status(cls, ride: Ride) -> Optional[str]:
        """
        Check if driver has arrived at pickup or destination.
        """
        if not ride.driver:
            return None
        
        driver_location = cls.get_driver_location(str(ride.driver.id))
        if not driver_location:
            return None
        
        driver_lat = driver_location['latitude']
        driver_lon = driver_location['longitude']
        
        if ride.status == Ride.RideStatus.DRIVER_ASSIGNED:
            # Check arrival at pickup
            pickup_distance = calculate_distance(
                driver_lat, driver_lon,
                float(ride.pickup_latitude), float(ride.pickup_longitude)
            )
            
            if pickup_distance * 1000 <= cls.ARRIVAL_THRESHOLD_METERS:  # Convert km to meters
                return 'arrived_at_pickup'
        
        elif ride.status == Ride.RideStatus.IN_PROGRESS:
            # Check arrival at destination
            dropoff_distance = calculate_distance(
                driver_lat, driver_lon,
                float(ride.dropoff_latitude), float(ride.dropoff_longitude)
            )
            
            if dropoff_distance * 1000 <= cls.ARRIVAL_THRESHOLD_METERS:  # Convert km to meters
                return 'arrived_at_destination'
        
        return None
    
    @classmethod
    def get_ride_route_progress(cls, ride: Ride) -> Optional[Dict]:
        """
        Calculate ride progress along the route.
        """
        if ride.status != Ride.RideStatus.IN_PROGRESS:
            return None
        
        if not ride.driver:
            return None
        
        driver_location = cls.get_driver_location(str(ride.driver.id))
        if not driver_location:
            return None
        
        # Calculate total route distance
        total_distance = calculate_distance(
            float(ride.pickup_latitude), float(ride.pickup_longitude),
            float(ride.dropoff_latitude), float(ride.dropoff_longitude)
        )
        
        # Calculate distance from pickup to current location
        traveled_distance = calculate_distance(
            float(ride.pickup_latitude), float(ride.pickup_longitude),
            driver_location['latitude'], driver_location['longitude']
        )
        
        # Calculate remaining distance
        remaining_distance = calculate_distance(
            driver_location['latitude'], driver_location['longitude'],
            float(ride.dropoff_latitude), float(ride.dropoff_longitude)
        )
        
        # Calculate progress percentage
        progress_percentage = min((traveled_distance / total_distance) * 100, 100) if total_distance > 0 else 0
        
        return {
            'total_distance_km': total_distance,
            'traveled_distance_km': traveled_distance,
            'remaining_distance_km': remaining_distance,
            'progress_percentage': progress_percentage,
            'estimated_time_remaining': estimate_arrival_time(remaining_distance)
        }
    
    @classmethod
    def detect_route_deviation(cls, ride: Ride, threshold_km: float = 2.0) -> bool:
        """
        Detect if driver has deviated significantly from the expected route.
        """
        if not ride.driver:
            return False
        
        driver_location = cls.get_driver_location(str(ride.driver.id))
        if not driver_location:
            return False
        
        # Simple deviation detection - check if driver is too far from direct route
        # In production, this would use proper routing APIs
        
        if ride.status == Ride.RideStatus.DRIVER_ASSIGNED:
            # Check deviation from path to pickup
            expected_distance = calculate_distance(
                float(ride.pickup_latitude), float(ride.pickup_longitude),
                driver_location['latitude'], driver_location['longitude']
            )
            
            # If driver is more than threshold away from pickup, might be deviation
            return expected_distance > threshold_km
        
        elif ride.status == Ride.RideStatus.IN_PROGRESS:
            # Check deviation from path to destination
            # This is simplified - in production, use proper route calculation
            direct_distance = calculate_distance(
                float(ride.pickup_latitude), float(ride.pickup_longitude),
                float(ride.dropoff_latitude), float(ride.dropoff_longitude)
            )
            
            current_total_distance = (
                calculate_distance(
                    float(ride.pickup_latitude), float(ride.pickup_longitude),
                    driver_location['latitude'], driver_location['longitude']
                ) +
                calculate_distance(
                    driver_location['latitude'], driver_location['longitude'],
                    float(ride.dropoff_latitude), float(ride.dropoff_longitude)
                )
            )
            
            # If current path is significantly longer than direct path
            return current_total_distance > (direct_distance * 1.5)
        
        return False
    
    @classmethod
    def _update_ride_tracking(cls, ride: Ride, latitude: float, longitude: float,
                            heading: Optional[float], speed: Optional[float]):
        """
        Update ride tracking data with new driver location.
        """
        try:
            trip_status = TripStatus.objects.get(ride=ride)
        except TripStatus.DoesNotExist:
            return
        
        # Update distances
        if ride.status == Ride.RideStatus.DRIVER_ASSIGNED:
            trip_status.distance_to_pickup = Decimal(str(calculate_distance(
                latitude, longitude,
                float(ride.pickup_latitude), float(ride.pickup_longitude)
            )))
        
        elif ride.status == Ride.RideStatus.IN_PROGRESS:
            trip_status.distance_to_dropoff = Decimal(str(calculate_distance(
                latitude, longitude,
                float(ride.dropoff_latitude), float(ride.dropoff_longitude)
            )))
        
        # Update movement status
        trip_status.is_driver_moving = speed is not None and speed > 1.0  # Moving if speed > 1 km/h
        trip_status.last_updated = timezone.now()
        trip_status.save()
        
        # Send real-time updates via WebSocket
        cls._send_tracking_update(ride, {
            'driver_location': {
                'latitude': latitude,
                'longitude': longitude,
                'heading': heading,
                'speed': speed
            },
            'distance_to_pickup': float(trip_status.distance_to_pickup or 0),
            'distance_to_dropoff': float(trip_status.distance_to_dropoff or 0),
            'is_driver_moving': trip_status.is_driver_moving,
            'timestamp': timezone.now().isoformat()
        })
        
        # Check for automatic status updates
        arrival_status = cls.check_arrival_status(ride)
        if arrival_status:
            cls._handle_automatic_arrival(ride, arrival_status)
    
    @classmethod
    def _send_tracking_update(cls, ride: Ride, update_data: Dict):
        """
        Send tracking update via WebSocket.
        """
        channel_layer = get_channel_layer()
        
        # Send to rider
        async_to_sync(channel_layer.group_send)(
            f"ride_{ride.id}_rider",
            {
                'type': 'tracking_update',
                'data': update_data
            }
        )
        
        # Send to driver
        if ride.driver:
            async_to_sync(channel_layer.group_send)(
                f"ride_{ride.id}_driver",
                {
                    'type': 'tracking_update',
                    'data': update_data
                }
            )
    
    @classmethod
    def _handle_automatic_arrival(cls, ride: Ride, arrival_status: str):
        """
        Handle automatic arrival detection.
        """
        if arrival_status == 'arrived_at_pickup' and ride.status == Ride.RideStatus.DRIVER_ASSIGNED:
            # Auto-update to driver arrived
            ride.status = Ride.RideStatus.DRIVER_ARRIVED
            ride.pickup_time = timezone.now()
            ride.save()
            
            # Create history entry
            RideHistory.objects.create(
                ride=ride,
                event_type=RideHistory.EventType.STATUS_CHANGE,
                previous_status=Ride.RideStatus.DRIVER_ASSIGNED,
                new_status=Ride.RideStatus.DRIVER_ARRIVED,
                description="Driver automatically marked as arrived at pickup",
                metadata={'auto_detected': True}
            )
            
            # Send notification
            from apps.notifications.services.notification_service import NotificationService
            NotificationService.send_ride_status_notification(ride, 'driver_arrived')
        
        elif arrival_status == 'arrived_at_destination' and ride.status == Ride.RideStatus.IN_PROGRESS:
            # Don't auto-complete ride, but send notification
            from apps.notifications.services.notification_service import NotificationService
            NotificationService.send_ride_status_notification(ride, 'near_destination')
