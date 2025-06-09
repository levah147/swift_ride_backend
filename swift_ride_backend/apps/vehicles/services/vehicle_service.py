"""
Service for handling vehicle operations.
"""

from django.utils import timezone
from django.db import transaction

from apps.vehicles.models import Vehicle, VehicleDocument, Insurance, Inspection


class VehicleService:
    """
    Service for handling vehicle operations.
    """
    
    @staticmethod
    def register_vehicle(owner, vehicle_data):
        """
        Register a new vehicle for a driver.
        """
        with transaction.atomic():
            # Create vehicle
            vehicle = Vehicle.objects.create(
                owner=owner,
                **vehicle_data
            )
            
            # Set eco-friendly flag based on fuel type
            if vehicle.fuel_type in [Vehicle.FuelType.ELECTRIC, Vehicle.FuelType.HYBRID]:
                vehicle.is_eco_friendly = True
                vehicle.save()
            
            return vehicle
    
    @staticmethod
    def verify_vehicle(vehicle, verified_by, status, rejection_reason=None):
        """
        Verify or reject a vehicle.
        """
        vehicle.verification_status = status
        vehicle.verified_by = verified_by
        
        if status == Vehicle.VerificationStatus.APPROVED:
            vehicle.verified_at = timezone.now()
            vehicle.rejection_reason = None
        elif status == Vehicle.VerificationStatus.REJECTED:
            vehicle.rejection_reason = rejection_reason
            vehicle.verified_at = None
        
        vehicle.save()
        
        # Update driver availability based on vehicle verification
        if status == Vehicle.VerificationStatus.APPROVED:
            VehicleService._update_driver_availability(vehicle.owner)
        
        return vehicle
    
    @staticmethod
    def suspend_vehicle(vehicle, reason):
        """
        Suspend a vehicle.
        """
        vehicle.verification_status = Vehicle.VerificationStatus.SUSPENDED
        vehicle.rejection_reason = reason
        vehicle.is_active = False
        vehicle.save()
        
        # Update driver availability
        VehicleService._update_driver_availability(vehicle.owner)
        
        return vehicle
    
    @staticmethod
    def activate_vehicle(vehicle):
        """
        Activate a suspended vehicle.
        """
        if vehicle.verification_status == Vehicle.VerificationStatus.SUSPENDED:
            vehicle.verification_status = Vehicle.VerificationStatus.APPROVED
            vehicle.is_active = True
            vehicle.rejection_reason = None
            vehicle.save()
            
            # Update driver availability
            VehicleService._update_driver_availability(vehicle.owner)
        
        return vehicle
    
    @staticmethod
    def get_driver_vehicles(driver, active_only=True):
        """
        Get all vehicles for a driver.
        """
        queryset = Vehicle.objects.filter(owner=driver)
        
        if active_only:
            queryset = queryset.filter(
                is_active=True,
                verification_status=Vehicle.VerificationStatus.APPROVED
            )
        
        return queryset.order_by('-created_at')
    
    @staticmethod
    def check_vehicle_eligibility(vehicle):
        """
        Check if a vehicle is eligible for rides.
        """
        # Check if vehicle is verified and active
        if not vehicle.is_verified or not vehicle.is_active:
            return False, "Vehicle is not verified or active"
        
        # Check if vehicle has valid documents
        if not vehicle.has_valid_documents:
            return False, "Vehicle does not have valid documents"
        
        # Check if insurance is valid
        try:
            insurance = vehicle.insurance
            if insurance.is_expired:
                return False, "Vehicle insurance has expired"
        except Insurance.DoesNotExist:
            return False, "Vehicle does not have insurance"
        
        # Check if recent inspection passed
        recent_inspection = vehicle.inspections.filter(
            status=Inspection.InspectionStatus.PASSED
        ).first()
        
        if not recent_inspection:
            return False, "Vehicle does not have a valid inspection"
        
        # Check if inspection is not too old (6 months)
        if recent_inspection.completed_date:
            days_since_inspection = (timezone.now().date() - recent_inspection.completed_date.date()).days
            if days_since_inspection > 180:  # 6 months
                return False, "Vehicle inspection is outdated"
        
        return True, "Vehicle is eligible for rides"
    
    @staticmethod
    def get_vehicles_needing_attention():
        """
        Get vehicles that need attention (expired documents, due for inspection, etc.).
        """
        from django.db.models import Q
        from datetime import timedelta
        
        today = timezone.now().date()
        warning_period = today + timedelta(days=30)  # 30 days warning
        
        # Vehicles with expired or soon-to-expire documents
        vehicles_with_issues = Vehicle.objects.filter(
            Q(documents__expiry_date__lte=warning_period) |
            Q(insurance__end_date__lte=warning_period) |
            Q(inspections__next_inspection_date__lte=warning_period)
        ).distinct()
        
        return vehicles_with_issues
    
    @staticmethod
    def _update_driver_availability(driver):
        """
        Update driver availability based on vehicle status.
        """
        try:
            driver_profile = driver.driver_profile
            
            # Check if driver has any eligible vehicles
            eligible_vehicles = VehicleService.get_driver_vehicles(driver, active_only=True)
            has_eligible_vehicle = False
            
            for vehicle in eligible_vehicles:
                is_eligible, _ = VehicleService.check_vehicle_eligibility(vehicle)
                if is_eligible:
                    has_eligible_vehicle = True
                    break
            
            # Update driver availability
            if has_eligible_vehicle:
                driver_profile.is_available = True
            else:
                driver_profile.is_available = False
                driver_profile.is_online = False
            
            driver_profile.save()
            
        except Exception as e:
            print(f"Error updating driver availability: {e}")
