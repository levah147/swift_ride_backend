from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from apps.location.models import Place, UserSavedPlace, LocationHistory


@receiver(post_save, sender=Place)
def handle_place_created(sender, instance, created, **kwargs):
    """Handle place creation"""
    if created:
        # Determine service zone for the place
        from apps.location.services.geospatial_service import GeospatialService
        
        zone = GeospatialService.get_service_zone_for_point(
            float(instance.latitude), float(instance.longitude)
        )
        
        if zone and not instance.service_zone:
            instance.service_zone = zone
            instance.save(update_fields=['service_zone'])


@receiver(post_save, sender=UserSavedPlace)
def handle_saved_place_used(sender, instance, **kwargs):
    """Update usage statistics when saved place is used"""
    if instance.last_used:
        instance.usage_count += 1
        instance.save(update_fields=['usage_count'])


@receiver(post_save, sender=LocationHistory)
def handle_location_tracked(sender, instance, created, **kwargs):
    """Handle location tracking"""
    if created and instance.ride:
        # Update ride location if this is during a ride
        from apps.rides.models import Ride
        
        try:
            ride = instance.ride
            if ride.status in ['accepted', 'driver_arrived', 'in_progress']:
                # Update ride's current location
                if instance.user == ride.driver:
                    ride.current_driver_latitude = instance.latitude
                    ride.current_driver_longitude = instance.longitude
                    ride.save(update_fields=[
                        'current_driver_latitude', 
                        'current_driver_longitude'
                    ])
        except Exception:
            pass  # Don't break location tracking if ride update fails
