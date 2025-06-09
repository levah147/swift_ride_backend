"""
Celery tasks for rides app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.rides.models import Ride, RideRequest, BargainOffer
from apps.rides.services.ride_matching import RideMatchingService


@shared_task
def match_drivers_to_ride(ride_id):
    """
    Match drivers to a ride request.
    """
    try:
        ride = Ride.objects.get(id=ride_id)
        
        # Check if ride is still searching
        if ride.status != Ride.RideStatus.SEARCHING:
            return f"Ride {ride_id} is no longer searching"
        
        # Find nearby drivers
        nearby_drivers = RideMatchingService.find_nearby_drivers(ride)
        
        if not nearby_drivers:
            # No drivers found, mark ride as expired after timeout
            expire_ride_request.apply_async(
                args=[ride_id],
                countdown=300  # 5 minutes
            )
            return f"No drivers found for ride {ride_id}"
        
        # For now, just log the nearby drivers
        # In production, you might want to send notifications to drivers
        return f"Found {len(nearby_drivers)} drivers for ride {ride_id}"
        
    except Ride.DoesNotExist:
        return f"Ride {ride_id} not found"


@shared_task
def expire_ride_request(ride_id):
    """
    Expire a ride request if no driver is found.
    """
    try:
        ride = Ride.objects.get(id=ride_id)
        
        # Check if ride is still searching
        if ride.status == Ride.RideStatus.SEARCHING:
            # Update ride status
            ride.status = Ride.RideStatus.EXPIRED
            ride.save()
            
            # Update ride request
            if hasattr(ride, 'request'):
                ride.request.status = RideRequest.RequestStatus.EXPIRED
                ride.request.save()
            
            # Create history entry
            from apps.rides.models import RideHistory
            RideHistory.objects.create(
                ride=ride,
                event_type=RideHistory.EventType.STATUS_CHANGE,
                previous_status=Ride.RideStatus.SEARCHING,
                new_status=Ride.RideStatus.EXPIRED,
                notes="Ride expired due to no available drivers"
            )
            
            return f"Ride {ride_id} expired"
        
        return f"Ride {ride_id} is no longer searching"
        
    except Ride.DoesNotExist:
        return f"Ride {ride_id} not found"


@shared_task
def expire_bargain_offers():
    """
    Expire bargain offers that have passed their expiry time.
    """
    expired_offers = BargainOffer.objects.filter(
        status=BargainOffer.OfferStatus.PENDING,
        expiry_time__lt=timezone.now()
    )
    
    count = expired_offers.count()
    expired_offers.update(status=BargainOffer.OfferStatus.EXPIRED)
    
    return f"Expired {count} bargain offers"


@shared_task
def cleanup_old_ride_history():
    """
    Clean up old ride history entries (older than 6 months).
    """
    cutoff_date = timezone.now() - timedelta(days=180)
    
    from apps.rides.models import RideHistory
    deleted_count, _ = RideHistory.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return f"Deleted {deleted_count} old ride history entries"
