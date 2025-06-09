"""
Signals for vehicle models.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.vehicles.models import Vehicle, VehicleDocument, Insurance, Inspection


@receiver(post_save, sender=Vehicle)
def vehicle_status_changed(sender, instance, created, **kwargs):
    """
    Handle vehicle status changes.
    """
    if created:
        # New vehicle registered
        print(f"New vehicle registered: {instance}")
        # Send notification to admin for verification
    else:
        # Check if verification status changed
        if kwargs.get('update_fields') and 'verification_status' in kwargs.get('update_fields'):
            if instance.verification_status == Vehicle.VerificationStatus.APPROVED:
                print(f"Vehicle approved: {instance}")
                # Send notification to driver
            elif instance.verification_status == Vehicle.VerificationStatus.REJECTED:
                print(f"Vehicle rejected: {instance}")
                # Send notification to driver with reason


@receiver(post_save, sender=VehicleDocument)
def document_uploaded(sender, instance, created, **kwargs):
    """
    Handle document upload.
    """
    if created:
        print(f"New document uploaded: {instance}")
        # Send notification to admin for verification


@receiver(post_save, sender=Insurance)
def insurance_updated(sender, instance, created, **kwargs):
    """
    Handle insurance updates.
    """
    if created:
        print(f"New insurance added: {instance}")
    
    # Check if insurance is expiring soon
    if instance.days_until_expiry <= 30:
        print(f"Insurance expiring soon: {instance}")
        # Send notification to vehicle owner


@receiver(post_save, sender=Inspection)
def inspection_completed(sender, instance, created, **kwargs):
    """
    Handle inspection completion.
    """
    if not created and instance.status == Inspection.InspectionStatus.PASSED:
        print(f"Inspection passed: {instance}")
        # Send notification to vehicle owner
    elif not created and instance.status == Inspection.InspectionStatus.FAILED:
        print(f"Inspection failed: {instance}")
        # Send notification to vehicle owner with recommendations
