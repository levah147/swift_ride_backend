"""
Common managers for Swift Ride project.
"""

from django.db import models
from django.utils import timezone
from django.db.models import Q


class ActiveManager(models.Manager):
    """
    Manager to return only active objects.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class SoftDeleteManager(models.Manager):
    """
    Manager for soft delete functionality.
    """
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)
    
    def deleted(self):
        """Return only deleted objects."""
        return super().get_queryset().filter(is_deleted=True)
    
    def with_deleted(self):
        """Return all objects including deleted ones."""
        return super().get_queryset()


class TimestampManager(models.Manager):
    """
    Manager with timestamp-based queries.
    """
    def created_today(self):
        """Return objects created today."""
        today = timezone.now().date()
        return self.filter(created_at__date=today)
    
    def created_this_week(self):
        """Return objects created this week."""
        week_ago = timezone.now() - timezone.timedelta(days=7)
        return self.filter(created_at__gte=week_ago)
    
    def created_this_month(self):
        """Return objects created this month."""
        month_ago = timezone.now() - timezone.timedelta(days=30)
        return self.filter(created_at__gte=month_ago)
    
    def updated_recently(self, hours=24):
        """Return objects updated in the last N hours."""
        cutoff = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(updated_at__gte=cutoff)


class LocationManager(models.Manager):
    """
    Manager for location-based queries.
    """
    def near_location(self, latitude, longitude, radius_km=10):
        """
        Find objects near a specific location.
        This is a simplified version - in production, use PostGIS.
        """
        # Simple bounding box calculation
        lat_delta = radius_km / 111.0  # Rough conversion: 1 degree ≈ 111 km
        lng_delta = radius_km / (111.0 * abs(latitude))
        
        lat_min = latitude - lat_delta
        lat_max = latitude + lat_delta
        lng_min = longitude - lng_delta
        lng_max = longitude + lng_delta
        
        return self.filter(
            latitude__gte=lat_min,
            latitude__lte=lat_max,
            longitude__gte=lng_min,
            longitude__lte=lng_max
        )
    
    def with_location(self):
        """Return only objects that have location data."""
        return self.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )


class StatusManager(models.Manager):
    """
    Manager for status-based queries.
    """
    def active(self):
        """Return active objects."""
        return self.filter(status='active', is_active=True)
    
    def inactive(self):
        """Return inactive objects."""
        return self.filter(Q(status='inactive') | Q(is_active=False))
    
    def by_status(self, status):
        """Return objects with specific status."""
        return self.filter(status=status)


class UserOwnedManager(models.Manager):
    """
    Manager for user-owned objects.
    """
    def for_user(self, user):
        """Return objects owned by a specific user."""
        return self.filter(user=user)
    
    def active_for_user(self, user):
        """Return active objects owned by a specific user."""
        return self.filter(user=user, is_active=True)


class VerificationManager(models.Manager):
    """
    Manager for verification-related queries.
    """
    def verified(self):
        """Return verified objects."""
        return self.filter(is_verified=True, verification_status='approved')
    
    def pending_verification(self):
        """Return objects pending verification."""
        return self.filter(verification_status='pending')
    
    def rejected(self):
        """Return rejected objects."""
        return self.filter(verification_status='rejected')
    
    def expired(self):
        """Return expired verifications."""
        return self.filter(verification_status='expired')


class RideManager(models.Manager):
    """
    Manager for ride-specific queries.
    """
    def active_rides(self):
        """Return active rides (requested, accepted, in_progress)."""
        return self.filter(
            status__in=['requested', 'accepted', 'driver_arrived', 'in_progress']
        )
    
    def completed_rides(self):
        """Return completed rides."""
        return self.filter(status='completed')
    
    def cancelled_rides(self):
        """Return cancelled rides."""
        return self.filter(status='cancelled')
    
    def for_rider(self, user):
        """Return rides for a specific rider."""
        return self.filter(rider=user)
    
    def for_driver(self, user):
        """Return rides for a specific driver."""
        return self.filter(driver=user)
    
    def today(self):
        """Return today's rides."""
        today = timezone.now().date()
        return self.filter(created_at__date=today)


class DriverManager(models.Manager):
    """
    Manager for driver-specific queries.
    """
    def online(self):
        """Return online drivers."""
        return self.filter(is_online=True, is_active=True)
    
    def offline(self):
        """Return offline drivers."""
        return self.filter(is_online=False)
    
    def verified(self):
        """Return verified drivers."""
        return self.filter(is_verified=True, verification_status='approved')
    
    def available(self):
        """Return available drivers (online, verified, not on a ride)."""
        return self.filter(
            is_online=True,
            is_active=True,
            is_verified=True,
            verification_status='approved',
            current_ride__isnull=True
        )
    
    def near_location(self, latitude, longitude, radius_km=10):
        """Find available drivers near a location."""
        return self.available().filter(
            latitude__isnull=False,
            longitude__isnull=False
        )  # Would implement proper distance calculation in production


class PaymentManager(models.Manager):
    """
    Manager for payment-specific queries.
    """
    def successful(self):
        """Return successful payments."""
        return self.filter(status='completed')
    
    def failed(self):
        """Return failed payments."""
        return self.filter(status='failed')
    
    def pending(self):
        """Return pending payments."""
        return self.filter(status='pending')
    
    def for_user(self, user):
        """Return payments for a specific user."""
        return self.filter(user=user)
    
    def today(self):
        """Return today's payments."""
        today = timezone.now().date()
        return self.filter(created_at__date=today)
    
    def this_month(self):
        """Return this month's payments."""
        now = timezone.now()
        return self.filter(
            created_at__year=now.year,
            created_at__month=now.month
        )


class NotificationManager(models.Manager):
    """
    Manager for notification-specific queries.
    """
    def unread(self):
        """Return unread notifications."""
        return self.filter(is_read=False)
    
    def read(self):
        """Return read notifications."""
        return self.filter(is_read=True)
    
    def for_user(self, user):
        """Return notifications for a specific user."""
        return self.filter(user=user)
    
    def by_type(self, notification_type):
        """Return notifications of a specific type."""
        return self.filter(notification_type=notification_type)
    
    def recent(self, days=7):
        """Return recent notifications."""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff)


class ReviewManager(models.Manager):
    """
    Manager for review-specific queries.
    """
    def for_driver(self, driver):
        """Return reviews for a specific driver."""
        return self.filter(driver=driver)
    
    def for_rider(self, rider):
        """Return reviews for a specific rider."""
        return self.filter(rider=rider)
    
    def high_rated(self, min_rating=4):
        """Return high-rated reviews."""
        return self.filter(rating__gte=min_rating)
    
    def low_rated(self, max_rating=2):
        """Return low-rated reviews."""
        return self.filter(rating__lte=max_rating)
    
    def recent(self, days=30):
        """Return recent reviews."""
        cutoff = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__gte=cutoff)
