"""
Service for handling vehicle inspection operations.
"""

from django.utils import timezone
from datetime import timedelta

from apps.vehicles.models import Inspection


class InspectionService:
    """
    Service for handling vehicle inspection operations.
    """
    
    @staticmethod
    def schedule_inspection(vehicle, inspection_data):
        """
        Schedule a vehicle inspection.
        """
        inspection = Inspection.objects.create(
            vehicle=vehicle,
            **inspection_data
        )
        
        return inspection
    
    @staticmethod
    def start_inspection(inspection, inspector):
        """
        Start an inspection.
        """
        inspection.status = Inspection.InspectionStatus.IN_PROGRESS
        inspection.inspector = inspector
        inspection.save()
        
        return inspection
    
    @staticmethod
    def complete_inspection(inspection, inspection_results):
        """
        Complete an inspection with results.
        """
        # Update inspection with results
        for key, value in inspection_results.items():
            if hasattr(inspection, key):
                setattr(inspection, key, value)
        
        inspection.completed_date = timezone.now()
        
        # Determine pass/fail based on overall score
        if inspection.overall_score and inspection.overall_score >= 70:
            inspection.status = Inspection.InspectionStatus.PASSED
            # Schedule next inspection (6 months later)
            inspection.next_inspection_date = (
                timezone.now().date() + timedelta(days=180)
            )
        else:
            inspection.status = Inspection.InspectionStatus.FAILED
        
        inspection.save()
        
        # Update vehicle status based on inspection result
        InspectionService._update_vehicle_status_after_inspection(inspection)
        
        return inspection
    
    @staticmethod
    def cancel_inspection(inspection, reason):
        """
        Cancel a scheduled inspection.
        """
        inspection.status = Inspection.InspectionStatus.CANCELLED
        inspection.notes = f"Cancelled: {reason}"
        inspection.save()
        
        return inspection
    
    @staticmethod
    def get_due_inspections():
        """
        Get vehicles that are due for inspection.
        """
        today = timezone.now().date()
        
        # Get vehicles that need inspection
        due_inspections = Inspection.objects.filter(
            next_inspection_date__lte=today,
            status=Inspection.InspectionStatus.PASSED
        ).order_by('next_inspection_date')
        
        return due_inspections
    
    @staticmethod
    def get_overdue_inspections():
        """
        Get vehicles with overdue inspections.
        """
        today = timezone.now().date()
        overdue_date = today - timedelta(days=30)  # 30 days overdue
        
        # Get vehicles without recent passed inspections
        from apps.vehicles.models import Vehicle
        
        vehicles_needing_inspection = Vehicle.objects.filter(
            verification_status=Vehicle.VerificationStatus.APPROVED
        ).exclude(
            inspections__status=Inspection.InspectionStatus.PASSED,
            inspections__completed_date__gte=overdue_date
        )
        
        return vehicles_needing_inspection
    
    @staticmethod
    def _update_vehicle_status_after_inspection(inspection):
        """
        Update vehicle status based on inspection results.
        """
        vehicle = inspection.vehicle
        
        if inspection.status == Inspection.InspectionStatus.FAILED:
            # Suspend vehicle if inspection failed
            from apps.vehicles.services.vehicle_service import VehicleService
            VehicleService.suspend_vehicle(
                vehicle,
                f"Vehicle failed inspection on {inspection.completed_date.date()}"
            )
        elif inspection.status == Inspection.InspectionStatus.PASSED:
            # Reactivate vehicle if it was suspended due to failed inspection
            if vehicle.verification_status == Vehicle.VerificationStatus.SUSPENDED:
                from apps.vehicles.services.vehicle_service import VehicleService
                VehicleService.activate_vehicle(vehicle)
