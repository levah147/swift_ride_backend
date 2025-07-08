"""
Custom managers for rides app models.
"""

from django.db import models
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum
from datetime import timedelta


class RideManager(models.Manager):
    """
    Custom manager for Ride model.
    """
    
    def active(self):
        """
        Get all active rides (not completed, cancelled, or expired).
        """
        return self.filter(
            status__in=[
                'requested', 'searching', 'bargaining', 'accepted',
                'driver_assigned', 'driver_arrived', 'in_progress'
            ]
        )
    
    def completed(self):
        """
        Get all completed rides.
        """
        return self.filter(status='completed')
    
    def cancelled(self):
        """
        Get all cancelled rides.
        """
        return self.filter(status='cancelled')
    
    def for_rider(self, user):
        """
        Get rides for a specific rider.
        """
        return self.filter(rider=user)
    
    def for_driver(self, user):
        """
        Get rides for a specific driver.
        """
        return self.filter(driver=user)
    
    def in_progress(self):
        """
        Get rides currently in progress.
        """
        return self.filter(status='in_progress')
    
    def searching_for_driver(self):
        """
        Get rides that are searching for a driver.
        """
        return self.filter(status='searching')
    
    def scheduled(self):
        """
        Get scheduled rides.
        """
        return self.filter(is_scheduled=True)
    
    def due_for_scheduling(self):
        """
        Get scheduled rides that are due to start soon (within 30 minutes).
        """
        now = timezone.now()
        due_time = now + timedelta(minutes=30)
        
        return self.filter(
            is_scheduled=True,
            schedule_time__lte=due_time,
            status='requested'
        )
    
    def expired_requests(self):
        """
        Get ride requests that have expired (searching for more than 10 minutes).
        """
        expiry_time = timezone.now() - timedelta(minutes=10)
        
        return self.filter(
            status='searching',
            created_at__lt=expiry_time
        )
    
    def recent(self, days=7):
        """
        Get rides from the last N days.
        """
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)
    
    def by_payment_method(self, method):
        """
        Get rides by payment method.
        """
        return self.filter(payment_method=method)
    
    def with_ratings(self):
        """
        Get rides that have been rated.
        """
        return self.filter(
            Q(rider_rating__isnull=False) | Q(driver_rating__isnull=False)
        )
    
    def without_ratings(self):
        """
        Get completed rides without ratings.
        """
        return self.filter(
            status='completed',
            rider_rating__isnull=True,
            driver_rating__isnull=True
        )
    
    def high_value(self, min_fare=1000):
        """
        Get high-value rides above a certain fare amount.
        """
        return self.filter(
            Q(estimated_fare__gte=min_fare) | Q(final_fare__gte=min_fare)
        )
    
    def long_distance(self, min_distance=20):
        """
        Get long-distance rides.
        """
        return self.filter(distance_km__gte=min_distance)
    
    def with_bargaining(self):
        """
        Get rides that involved bargaining.
        """
        return self.filter(bargain_offers__isnull=False).distinct()


class RideRequestManager(models.Manager):
    """
    Custom manager for RideRequest model.
    """
    
    def pending(self):
        """
        Get pending ride requests.
        """
        return self.filter(status='pending')
    
    def matched(self):
        """
        Get matched ride requests.
        """
        return self.filter(status='matched')
    
    def expired(self):
        """
        Get expired ride requests.
        """
        return self.filter(status='expired')
    
    def for_vehicle_type(self, vehicle_type):
        """
        Get requests for a specific vehicle type.
        """
        return self.filter(vehicle_type=vehicle_type)
    
    def with_preferred_driver(self):
        """
        Get requests with a preferred driver.
        """
        return self.filter(preferred_driver__isnull=False)
    
    def expiring_soon(self, minutes=5):
        """
        Get requests expiring within the next N minutes.
        """
        expiry_threshold = timezone.now() + timedelta(minutes=minutes)
        return self.filter(
            status='pending',
            expiry_time__lte=expiry_threshold
        )


class BargainOfferManager(models.Manager):
    """
    Custom manager for BargainOffer model.
    """
    
    def pending(self):
        """
        Get pending bargain offers.
        """
        return self.filter(status='pending')
    
    def accepted(self):
        """
        Get accepted bargain offers.
        """
        return self.filter(status='accepted')
    
    def rejected(self):
        """
        Get rejected bargain offers.
        """
        return self.filter(status='rejected')
    
    def expired(self):
        """
        Get expired bargain offers.
        """
        return self.filter(status='expired')
    
    def by_rider(self):
        """
        Get offers made by riders.
        """
        return self.filter(offer_type='rider')
    
    def by_driver(self):
        """
        Get offers made by drivers.
        """
        return self.filter(offer_type='driver')
    
    def for_ride(self, ride):
        """
        Get offers for a specific ride.
        """
        return self.filter(ride=ride)
    
    def for_user(self, user):
        """
        Get offers made by a specific user.
        """
        return self.filter(offered_by=user)
    
    def active(self):
        """
        Get active (non-expired, non-rejected) offers.
        """
        return self.filter(
            status__in=['pending', 'accepted', 'countered'],
            expiry_time__gt=timezone.now()
        )
    
    def counter_offers(self):
        """
        Get counter offers.
        """
        return self.filter(counter_offer__isnull=False)
    
    def original_offers(self):
        """
        Get original offers (not counter offers).
        """
        return self.filter(counter_offer__isnull=True)
    
    def high_value(self, min_amount=1000):
        """
        Get high-value offers.
        """
        return self.filter(amount__gte=min_amount)
    
    def recent(self, hours=24):
        """
        Get recent offers from the last N hours.
        """
        since = timezone.now() - timedelta(hours=hours)
        return self.filter(created_at__gte=since)


class RideHistoryManager(models.Manager):
    """
    Custom manager for RideHistory model.
    """
    
    def for_ride(self, ride):
        """
        Get history for a specific ride.
        """
        return self.filter(ride=ride).order_by('created_at')
    
    def status_changes(self):
        """
        Get status change events.
        """
        return self.filter(event_type='status_change')
    
    def location_updates(self):
        """
        Get location update events.
        """
        return self.filter(event_type='location_update')
    
    def payment_events(self):
        """
        Get payment-related events.
        """
        return self.filter(event_type='payment')
    
    def bargain_events(self):
        """
        Get bargaining events.
        """
        return self.filter(event_type='bargain')
    
    def system_events(self):
        """
        Get system-generated events.
        """
        return self.filter(event_type='system')
    
    def recent(self, days=7):
        """
        Get recent history from the last N days.
        """
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since)
    
    def with_location(self):
        """
        Get history entries with location data.
        """
        return self.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )


class TripStatusManager(models.Manager):
    """
    Custom manager for TripStatus model.
    """
    
    def active_trips(self):
        """
        Get status for active trips.
        """
        return self.filter(
            ride__status__in=[
                'driver_assigned', 'driver_arrived', 'in_progress'
            ]
        )
    
    def with_moving_drivers(self):
        """
        Get trips where drivers are currently moving.
        """
        return self.filter(is_driver_moving=True)
    
    def recently_updated(self, minutes=5):
        """
        Get trip statuses updated in the last N minutes.
        """
        since = timezone.now() - timedelta(minutes=minutes)
        return self.filter(last_updated__gte=since)
    
    def stale_updates(self, minutes=10):
        """
        Get trip statuses that haven't been updated recently.
        """
        stale_time = timezone.now() - timedelta(minutes=minutes)
        return self.filter(
            ride__status__in=['driver_assigned', 'driver_arrived', 'in_progress'],
            last_updated__lt=stale_time
        )
    
    def near_pickup(self, max_distance=0.5):
        """
        Get trips where driver is near pickup location.
        """
        return self.filter(
            distance_to_pickup__lte=max_distance,
            ride__status='driver_assigned'
        )
    
    def near_destination(self, max_distance=0.5):
        """
        Get trips where driver is near destination.
        """
        return self.filter(
            distance_to_dropoff__lte=max_distance,
            ride__status='in_progress'
        )
