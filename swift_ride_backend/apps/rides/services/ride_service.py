"""
Service for handling ride operations.
"""

import uuid
from datetime import timedelta
from django.utils import timezone

from apps.rides.models import Ride, RideRequest, RideHistory
from apps.users.models import CustomUser


class RideService:
    """
    Service for handling ride operations.
    """
    
    @staticmethod
    def create_ride_request(rider, data):
        """
        Create a new ride request.
        """
        # Calculate estimated fare
        estimated_fare = RideService._calculate_fare(
            data['pickup_latitude'],
            data['pickup_longitude'],
            data['dropoff_latitude'],
            data['dropoff_longitude'],
            data.get('distance_km', 0)
        )
        
        # Create ride
        ride = Ride.objects.create(
            rider=rider,
            pickup_location=data['pickup_location'],
            pickup_latitude=data['pickup_latitude'],
            pickup_longitude=data['pickup_longitude'],
            dropoff_location=data['dropoff_location'],
            dropoff_latitude=data['dropoff_latitude'],
            dropoff_longitude=data['dropoff_longitude'],
            estimated_fare=estimated_fare,
            distance_km=data.get('distance_km', 0),
            duration_minutes=data.get('duration_minutes', 0),
            is_scheduled=data.get('is_scheduled', False),
            schedule_time=data.get('schedule_time'),
            payment_method=data.get('payment_method', 'cash'),
            notes=data.get('notes', '')
        )
        
        # Create ride request
        expiry_time = timezone.now() + timedelta(minutes=5)
        request = RideRequest.objects.create(
            ride=ride,
            vehicle_type=data.get('vehicle_type'),
            preferred_driver=data.get('preferred_driver'),
            expiry_time=expiry_time
        )
        
        # Create ride history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.STATUS_CHANGE,
            new_status=Ride.RideStatus.REQUESTED,
            data={'estimated_fare': str(estimated_fare)}
        )
        
        # If not scheduled, start searching for drivers
        if not ride.is_scheduled:
            RideService.start_searching_drivers(ride)
        
        return ride, request
    
    @staticmethod
    def start_searching_drivers(ride):
        """
        Start searching for drivers.
        """
        # Update ride status
        ride.status = Ride.RideStatus.SEARCHING
        ride.save()
        
        # Create ride history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.STATUS_CHANGE,
            previous_status=Ride.RideStatus.REQUESTED,
            new_status=Ride.RideStatus.SEARCHING
        )
        
        # Start driver matching (this would be done in a Celery task)
        # For now, just a placeholder
        from apps.rides.tasks import match_drivers_to_ride
        match_drivers_to_ride.delay(str(ride.id))
    
    @staticmethod
    def start_bargaining(ride, driver):
        """
        Start bargaining process.
        """
        # Update ride status
        previous_status = ride.status
        ride.status = Ride.RideStatus.BARGAINING
        ride.save()
        
        # Create ride history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.STATUS_CHANGE,
            previous_status=previous_status,
            new_status=Ride.RideStatus.BARGAINING,
            data={'driver_id': str(driver.id)}
        )
        
        # Notify via WebSocket that bargaining has started
        # This would be handled by the WebSocket consumer
    
    @staticmethod
    def cancel_ride(ride, cancelled_by, reason=None):
        """
        Cancel a ride.
        """
        if not ride.can_cancel:
            return False, "Ride cannot be cancelled at this stage"
        
        # Update ride status
        previous_status = ride.status
        ride.status = Ride.RideStatus.CANCELLED
        ride.save()
        
        # Update ride request if exists
        if hasattr(ride, 'request'):
            ride.request.status = RideRequest.RequestStatus.CANCELLED
            ride.request.save()
        
        # Create ride history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.CANCELLATION,
            previous_status=previous_status,
            new_status=Ride.RideStatus.CANCELLED,
            data={
                'cancelled_by_id': str(cancelled_by.id),
                'cancelled_by_type': cancelled_by.user_type,
                'reason': reason
            }
        )
        
        # Notify via WebSocket that ride has been cancelled
        # This would be handled by the WebSocket consumer
        
        return True, "Ride cancelled successfully"
    
    @staticmethod
    def complete_ride(ride, final_fare=None):
        """
        Complete a ride.
        """
        if not ride.is_in_progress:
            return False, "Ride must be in progress to complete"
        
        # Update ride status
        previous_status = ride.status
        ride.status = Ride.RideStatus.COMPLETED
        ride.dropoff_time = timezone.now()
        
        # Set final fare if provided, otherwise use estimated fare
        if final_fare:
            ride.final_fare = final_fare
        else:
            ride.final_fare = ride.estimated_fare
            
        ride.save()
        
        # Create ride history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.COMPLETION,
            previous_status=previous_status,
            new_status=Ride.RideStatus.COMPLETED,
            data={'final_fare': str(ride.final_fare)}
        )
        
        # Update driver statistics
        if ride.driver:
            driver_profile = ride.driver.driver_profile
            driver_profile.total_rides += 1
            driver_profile.total_earnings += ride.final_fare
            driver_profile.save()
        
        # Notify via WebSocket that ride has been completed
        # This would be handled by the WebSocket consumer
        
        return True, "Ride completed successfully"
    
    @staticmethod
    def update_ride_location(ride, latitude, longitude):
        """
        Update ride location for tracking.
        """
        # Update trip status
        from apps.rides.models import TripStatus
        
        trip_status, created = TripStatus.objects.get_or_create(ride=ride)
        trip_status.current_latitude = latitude
        trip_status.current_longitude = longitude
        trip_status.save()
        
        # Create ride history entry
        RideHistory.objects.create(
            ride=ride,
            event_type=RideHistory.EventType.LOCATION_UPDATE,
            latitude=latitude,
            longitude=longitude
        )
        
        return trip_status
    
    @staticmethod
    def _calculate_fare(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng, distance_km):
        """
        Calculate estimated fare based on distance and other factors.
        This is a simple implementation, would be more complex in production.
        """
        # Sample fare calculation algorithm
        base_fare = 500  # Base fare in local currency (e.g., Naira)
        distance_fare = distance_km * 150  # 150 per kilometer
        
        # Add dynamic pricing factors (time of day, demand, etc.)
        # This would be more complex in production
        time_factor = 1.0  # Normal pricing
        
        # Calculate total fare
        fare = (base_fare + distance_fare) * time_factor
        
        return round(fare, 2)
