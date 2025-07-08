"""
Service for handling vehicle verification operations.
"""

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.vehicles.models import Vehicle, VehicleDocument, Insurance, Inspection
from apps.notifications.services.notification_service import NotificationService

User = get_user_model()


class VerificationService:
    """
    Service for handling vehicle verification operations.
    """
    
    @staticmethod
    def verify_vehicle_documents(vehicle):
        """
        Verify all required documents for a vehicle.
        """
        required_documents = [
            VehicleDocument.DocumentType.REGISTRATION,
            VehicleDocument.DocumentType.INSURANCE,
        ]
        
        verification_results = {}
        all_verified = True
        
        for doc_type in required_documents:
            try:
                document = vehicle.documents.get(document_type=doc_type)
                if document.is_verified and not document.is_expired:
                    verification_results[doc_type] = {
                        'status': 'verified',
                        'document': document,
                        'message': 'Document is verified and valid'
                    }
                elif document.is_expired:
                    verification_results[doc_type] = {
                        'status': 'expired',
                        'document': document,
                        'message': 'Document has expired'
                    }
                    all_verified = False
                else:
                    verification_results[doc_type] = {
                        'status': 'pending',
                        'document': document,
                        'message': 'Document is pending verification'
                    }
                    all_verified = False
            except VehicleDocument.DoesNotExist:
                verification_results[doc_type] = {
                    'status': 'missing',
                    'document': None,
                    'message': 'Document is missing'
                }
                all_verified = False
        
        return all_verified, verification_results
    
    @staticmethod
    def verify_vehicle_insurance(vehicle):
        """
        Verify vehicle insurance.
        """
        try:
            insurance = vehicle.insurance
            if insurance.is_expired:
                return False, 'Insurance has expired'
            elif not insurance.is_active:
                return False, 'Insurance is not active'
            else:
                return True, 'Insurance is valid'
        except Insurance.DoesNotExist:
            return False, 'No insurance found'
    
    @staticmethod
    def verify_vehicle_inspection(vehicle):
        """
        Verify vehicle inspection status.
        """
        # Get the latest passed inspection
        latest_inspection = vehicle.inspections.filter(
            status=Inspection.InspectionStatus.PASSED
        ).first()
        
        if not latest_inspection:
            return False, 'No valid inspection found'
        
        # Check if inspection is not too old (6 months)
        if latest_inspection.completed_date:
            days_since_inspection = (
                timezone.now().date() - latest_inspection.completed_date.date()
            ).days
            if days_since_inspection > 180:  # 6 months
                return False, 'Inspection is outdated'
        
        return True, 'Inspection is valid'
    
    @staticmethod
    @transaction.atomic
    def complete_vehicle_verification(vehicle, verifier, status, notes=None):
        """
        Complete the full vehicle verification process.
        """
        # Check documents
        docs_verified, doc_results = VerificationService.verify_vehicle_documents(vehicle)
        
        # Check insurance
        insurance_valid, insurance_message = VerificationService.verify_vehicle_insurance(vehicle)
        
        # Check inspection
        inspection_valid, inspection_message = VerificationService.verify_vehicle_inspection(vehicle)
        
        # Determine overall verification status
        if status == Vehicle.VerificationStatus.APPROVED:
            if not (docs_verified and insurance_valid and inspection_valid):
                # Cannot approve if requirements not met
                status = Vehicle.VerificationStatus.REJECTED
                if not notes:
                    notes = "Vehicle does not meet all verification requirements"
        
        # Update vehicle status
        vehicle.verification_status = status
        vehicle.verified_by = verifier
        
        if status == Vehicle.VerificationStatus.APPROVED:
            vehicle.verified_at = timezone.now()
            vehicle.rejection_reason = None
        elif status == Vehicle.VerificationStatus.REJECTED:
            vehicle.rejection_reason = notes
            vehicle.verified_at = None
        
        vehicle.save()
        
        # Send notification to vehicle owner
        VerificationService._send_verification_notification(vehicle, status, notes)
        
        # Update driver availability
        VerificationService._update_driver_availability(vehicle.owner)
        
        return {
            'vehicle': vehicle,
            'documents': doc_results,
            'insurance': {'valid': insurance_valid, 'message': insurance_message},
            'inspection': {'valid': inspection_valid, 'message': inspection_message}
        }
    
    @staticmethod
    def get_verification_checklist(vehicle):
        """
        Get a comprehensive verification checklist for a vehicle.
        """
        checklist = {
            'vehicle_info': {
                'status': 'complete' if all([
                    vehicle.make, vehicle.model, vehicle.year, vehicle.color,
                    vehicle.license_plate, vehicle.vin_number
                ]) else 'incomplete',
                'items': [
                    {'name': 'Make', 'status': 'complete' if vehicle.make else 'missing'},
                    {'name': 'Model', 'status': 'complete' if vehicle.model else 'missing'},
                    {'name': 'Year', 'status': 'complete' if vehicle.year else 'missing'},
                    {'name': 'Color', 'status': 'complete' if vehicle.color else 'missing'},
                    {'name': 'License Plate', 'status': 'complete' if vehicle.license_plate else 'missing'},
                    {'name': 'VIN Number', 'status': 'complete' if vehicle.vin_number else 'missing'},
                ]
            },
            'photos': {
                'status': 'complete' if all([
                    vehicle.front_photo, vehicle.back_photo, 
                    vehicle.side_photo, vehicle.interior_photo
                ]) else 'incomplete',
                'items': [
                    {'name': 'Front Photo', 'status': 'complete' if vehicle.front_photo else 'missing'},
                    {'name': 'Back Photo', 'status': 'complete' if vehicle.back_photo else 'missing'},
                    {'name': 'Side Photo', 'status': 'complete' if vehicle.side_photo else 'missing'},
                    {'name': 'Interior Photo', 'status': 'complete' if vehicle.interior_photo else 'missing'},
                ]
            }
        }
        
        # Check documents
        docs_verified, doc_results = VerificationService.verify_vehicle_documents(vehicle)
        checklist['documents'] = {
            'status': 'complete' if docs_verified else 'incomplete',
            'items': []
        }
        
        for doc_type, result in doc_results.items():
            checklist['documents']['items'].append({
                'name': doc_type.replace('_', ' ').title(),
                'status': result['status'],
                'message': result['message']
            })
        
        # Check insurance
        insurance_valid, insurance_message = VerificationService.verify_vehicle_insurance(vehicle)
        checklist['insurance'] = {
            'status': 'complete' if insurance_valid else 'incomplete',
            'message': insurance_message
        }
        
        # Check inspection
        inspection_valid, inspection_message = VerificationService.verify_vehicle_inspection(vehicle)
        checklist['inspection'] = {
            'status': 'complete' if inspection_valid else 'incomplete',
            'message': inspection_message
        }
        
        # Overall status
        all_complete = all([
            checklist['vehicle_info']['status'] == 'complete',
            checklist['photos']['status'] == 'complete',
            checklist['documents']['status'] == 'complete',
            checklist['insurance']['status'] == 'complete',
            checklist['inspection']['status'] == 'complete'
        ])
        
        checklist['overall_status'] = 'ready_for_verification' if all_complete else 'incomplete'
        
        return checklist
    
    @staticmethod
    def get_vehicles_pending_verification():
        """
        Get all vehicles pending verification.
        """
        return Vehicle.objects.filter(
            verification_status=Vehicle.VerificationStatus.PENDING
        ).order_by('created_at')
    
    @staticmethod
    def get_verification_statistics():
        """
        Get verification statistics.
        """
        from django.db.models import Count
        
        stats = Vehicle.objects.aggregate(
            total=Count('id'),
            pending=Count('id', filter=models.Q(verification_status='pending')),
            approved=Count('id', filter=models.Q(verification_status='approved')),
            rejected=Count('id', filter=models.Q(verification_status='rejected')),
            suspended=Count('id', filter=models.Q(verification_status='suspended'))
        )
        
        return stats
    
    @staticmethod
    def _send_verification_notification(vehicle, status, notes=None):
        """
        Send verification notification to vehicle owner.
        """
        try:
            if status == Vehicle.VerificationStatus.APPROVED:
                message = f"Your vehicle {vehicle.license_plate} has been approved for rides!"
                NotificationService.send_notification(
                    user=vehicle.owner,
                    title="Vehicle Approved",
                    message=message,
                    notification_type="vehicle_approved"
                )
            elif status == Vehicle.VerificationStatus.REJECTED:
                message = f"Your vehicle {vehicle.license_plate} verification was rejected."
                if notes:
                    message += f" Reason: {notes}"
                NotificationService.send_notification(
                    user=vehicle.owner,
                    title="Vehicle Rejected",
                    message=message,
                    notification_type="vehicle_rejected"
                )
        except Exception as e:
            print(f"Error sending verification notification: {e}")
    
    @staticmethod
    def _update_driver_availability(driver):
        """
        Update driver availability based on vehicle verification status.
        """
        try:
            driver_profile = driver.driver_profile
            
            # Check if driver has any approved vehicles
            has_approved_vehicle = driver.vehicles.filter(
                verification_status=Vehicle.VerificationStatus.APPROVED,
                is_active=True
            ).exists()
            
            if has_approved_vehicle:
                driver_profile.is_available = True
            else:
                driver_profile.is_available = False
                driver_profile.is_online = False
            
            driver_profile.save()
            
        except Exception as e:
            print(f"Error updating driver availability: {e}")
