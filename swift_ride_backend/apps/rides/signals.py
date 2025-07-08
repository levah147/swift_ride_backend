"""
Signals for ride models.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.rides.models import Ride, RideHistory, BargainOffer
from apps.notifications.services.notification_service import NotificationService


@receiver(post_save, sender=Ride)
def ride_status_changed(sender, instance, created, **kwargs):
    """
    Handle ride status changes.
    """
    if created:
        # New ride created - notify relevant users
        NotificationService.send_ride_requested_notification(instance)
    else:
        # If status changed, notify relevant users
        if kwargs.get('update_fields') and 'status' in kwargs.get('update_fields'):
            if instance.status == Ride.RideStatus.ACCEPTED:
                NotificationService.send_ride_accepted_notification(instance)
            elif instance.status == Ride.RideStatus.DRIVER_ARRIVED:
                NotificationService.send_driver_arrived_notification(instance)
            elif instance.status == Ride.RideStatus.COMPLETED:
                NotificationService.send_ride_completed_notification(instance)
            elif instance.status == Ride.RideStatus.CANCELLED:
                NotificationService.send_ride_cancelled_notification(instance)


@receiver(post_save, sender=BargainOffer)
def bargain_offer_created(sender, instance, created, **kwargs):
    """
    Handle bargain offer creation.
    """
    if created:
        # New offer created - notify relevant users
        if instance.offer_type == BargainOffer.OfferType.RIDER:
            # Notify driver
            if instance.ride.driver:
                NotificationService.send_bargain_offer_notification(
                    instance.ride.driver,
                    instance
                )
        else:
            # Notify rider
            NotificationService.send_bargain_offer_notification(
                instance.ride.rider,
                instance
            )
