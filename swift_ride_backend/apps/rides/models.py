"""
Ride models for Swift Ride project.
"""

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.common.models import BaseModel, SoftDeleteModel


class Ride(BaseModel, SoftDeleteModel):
    """
    The main Ride model that stores ride information.
    """
    class RideStatus(models.TextChoices):
        REQUESTED = 'requested', _('Requested')
        SEARCHING = 'searching', _('Searching for Driver')
        BARGAINING = 'bargaining', _('Bargaining')
        ACCEPTED = 'accepted', _('Accepted')
        DRIVER_ASSIGNED = 'driver_assigned', _('Driver Assigned')
        DRIVER_ARRIVED = 'driver_arrived', _('Driver Arrived')
        IN_PROGRESS = 'in_progress', _('In Progress')
        COMPLETED = 'completed', _('Completed')
        CANCELLED = 'cancelled', _('Cancelled')
        EXPIRED = 'expired', _('Expired')
    
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rides_as_rider'
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='rides_as_driver',
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=RideStatus.choices,
        default=RideStatus.REQUESTED
    )
    pickup_location = models.CharField(max_length=255)
    pickup_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_location = models.CharField(max_length=255)
    dropoff_latitude = models.DecimalField(max_digits=9, decimal_places=6)
    dropoff_longitude = models.DecimalField(max_digits=9, decimal_places=6)
    pickup_time = models.DateTimeField(null=True, blank=True)
    dropoff_time = models.DateTimeField(null=True, blank=True)
    estimated_fare = models.DecimalField(max_digits=10, decimal_places=2)
    final_fare = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    rider_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    driver_rating = models.PositiveSmallIntegerField(null=True, blank=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2)
    duration_minutes = models.PositiveIntegerField()
    payment_method = models.CharField(max_length=50, default='cash')
    payment_status = models.CharField(max_length=20, default='pending')
    notes = models.TextField(blank=True, null=True)
    schedule_time = models.DateTimeField(null=True, blank=True)
    is_scheduled = models.BooleanField(default=False)
    vehicle = models.ForeignKey(
        'vehicles.Vehicle',
        on_delete=models.SET_NULL,
        related_name='rides',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"Ride {self.id} - {self.rider} to {self.dropoff_location}"
    
    @property
    def is_active(self):
        return self.status not in [self.RideStatus.COMPLETED, self.RideStatus.CANCELLED, self.RideStatus.EXPIRED]
    
    @property
    def is_bargaining(self):
        return self.status == self.RideStatus.BARGAINING
    
    @property
    def is_in_progress(self):
        return self.status == self.RideStatus.IN_PROGRESS
    
    @property
    def can_cancel(self):
        return self.status in [
            self.RideStatus.REQUESTED,
            self.RideStatus.SEARCHING,
            self.RideStatus.BARGAINING,
            self.RideStatus.ACCEPTED,
            self.RideStatus.DRIVER_ASSIGNED
        ]


class RideRequest(BaseModel):
    """
    Model to store ride requests for matching with drivers.
    """
    class RequestStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        MATCHED = 'matched', _('Matched')
        EXPIRED = 'expired', _('Expired')
        CANCELLED = 'cancelled', _('Cancelled')
    
    ride = models.OneToOneField(
        Ride,
        on_delete=models.CASCADE,
        related_name='request'
    )
    status = models.CharField(
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING
    )
    preferred_driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='preferred_ride_requests',
        null=True,
        blank=True
    )
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)
    expiry_time = models.DateTimeField()
    
    def __str__(self):
        return f"Request for {self.ride}"


class BargainOffer(BaseModel):
    """
    Model to store bargain offers between riders and drivers.
    """
    class OfferStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        ACCEPTED = 'accepted', _('Accepted')
        REJECTED = 'rejected', _('Rejected')
        COUNTERED = 'countered', _('Countered')
        EXPIRED = 'expired', _('Expired')
    
    class OfferType(models.TextChoices):
        RIDER = 'rider', _('Rider')
        DRIVER = 'driver', _('Driver')
    
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='bargain_offers'
    )
    offered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bargain_offers'
    )
    offer_type = models.CharField(
        max_length=10,
        choices=OfferType.choices
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=OfferStatus.choices,
        default=OfferStatus.PENDING
    )
    counter_offer = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        related_name='original_offer',
        null=True,
        blank=True
    )
    message = models.TextField(blank=True, null=True)
    expiry_time = models.DateTimeField()
    
    def __str__(self):
        return f"{self.offer_type} offer of {self.amount} for {self.ride}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expiry_time


class RideHistory(BaseModel):
    """
    Model to store ride history and tracking information.
    """
    class EventType(models.TextChoices):
        STATUS_CHANGE = 'status_change', _('Status Change')
        LOCATION_UPDATE = 'location_update', _('Location Update')
        FARE_UPDATE = 'fare_update', _('Fare Update')
        BARGAIN = 'bargain', _('Bargain')
        PAYMENT = 'payment', _('Payment')
        CANCELLATION = 'cancellation', _('Cancellation')
        COMPLETION = 'completion', _('Completion')
        SYSTEM = 'system', _('System Event')
    
    ride = models.ForeignKey(
        Ride,
        on_delete=models.CASCADE,
        related_name='history'
    )
    event_type = models.CharField(
        max_length=20,
        choices=EventType.choices
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Ride.RideStatus.choices,
        null=True,
        blank=True
    )
    new_status = models.CharField(
        max_length=20,
        choices=Ride.RideStatus.choices,
        null=True,
        blank=True
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    data = models.JSONField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.event_type} for {self.ride}"


class TripStatus(BaseModel):
    """
    Model to store real-time trip status and location.
    """
    ride = models.OneToOneField(
        Ride,
        on_delete=models.CASCADE,
        related_name='trip_status'
    )
    current_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    estimated_arrival_time = models.DateTimeField(null=True, blank=True)
    distance_to_pickup = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    distance_to_dropoff = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_driver_moving = models.BooleanField(default=False)
    driver_bearing = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    def __str__(self):
        return f"Trip status for {self.ride}"
