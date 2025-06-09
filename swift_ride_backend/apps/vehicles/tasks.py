"""
Celery tasks for vehicles app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.vehicles.models import VehicleDocument, Insurance, Inspection
from apps.vehicles.services.document_service import DocumentService
from apps.vehicles.services.inspection_service import InspectionService


@shared_task
def check_expiring_documents():
    """
    Check for expiring documents and send notifications.
    """
    # Check documents expiring in 30 days
    expiring_docs = DocumentService.get_expiring_documents(30)
    
    count = 0
    for doc in expiring_docs:
        # Send notification to vehicle owner
        print(f"Document expiring: {doc}")
        # Here you would send actual notifications
        count += 1
    
    return f"Found {count} expiring documents"


@shared_task
def check_expiring_insurance():
    """
    Check for expiring insurance policies and send notifications.
    """
    # Check insurance expiring in 30 days
    expiring_insurance = DocumentService.get_expiring_insurance(30)
    
    count = 0
    for insurance in expiring_insurance:
        # Send notification to vehicle owner
        print(f"Insurance expiring: {insurance}")
        # Here you would send actual notifications
        count += 1
    
    return f"Found {count} expiring insurance policies"


@shared_task
def check_due_inspections():
    """
    Check for vehicles due for inspection.
    """
    due_inspections = InspectionService.get_due_inspections()
    
    count = 0
    for inspection in due_inspections:
        # Send notification to vehicle owner
        print(f"Inspection due: {inspection}")
        # Here you would send actual notifications
        count += 1
    
    return f"Found {count} vehicles due for inspection"


@shared_task
def auto_suspend_expired_vehicles():
    """
    Automatically suspend vehicles with expired documents or insurance.
    """
    from apps.vehicles.models import Vehicle
    from apps.vehicles.services.vehicle_service import VehicleService
    
    # Get vehicles with expired documents
    expired_docs = DocumentService.get_expired_documents()
    expired_insurance = Insurance.objects.filter(
        end_date__lt=timezone.now().date(),
        is_active=True
    )
    
    suspended_count = 0
    
    # Suspend vehicles with expired documents
    for doc in expired_docs:
        vehicle = doc.vehicle
        if vehicle.verification_status == Vehicle.VerificationStatus.APPROVED:
            VehicleService.suspend_vehicle(
                vehicle,
                f"Vehicle suspended due to expired {doc.get_document_type_display()}"
            )
            suspended_count += 1
    
    # Suspend vehicles with expired insurance
    for insurance in expired_insurance:
        vehicle = insurance.vehicle
        if vehicle.verification_status == Vehicle.VerificationStatus.APPROVED:
            VehicleService.suspend_vehicle(
                vehicle,
                f"Vehicle suspended due to expired insurance"
            )
            suspended_count += 1
    
    return f"Suspended {suspended_count} vehicles due to expired documents/insurance"


@shared_task
def cleanup_old_vehicle_data():
    """
    Clean up old vehicle data (maintenance records older than 2 years).
    """
    cutoff_date = timezone.now() - timedelta(days=730)  # 2 years
    
    from apps.vehicles.models import VehicleMaintenanceRecord
    deleted_count, _ = VehicleMaintenanceRecord.objects.filter(
        created_at__lt=cutoff_date
    ).delete()
    
    return f"Deleted {deleted_count} old maintenance records"
