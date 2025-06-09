"""
Service for handling vehicle document operations.
"""

from django.utils import timezone
from datetime import timedelta

from apps.vehicles.models import VehicleDocument, Insurance


class DocumentService:
    """
    Service for handling vehicle document operations.
    """
    
    @staticmethod
    def upload_document(vehicle, document_data, document_file):
        """
        Upload a vehicle document.
        """
        # Check if document already exists
        existing_doc = VehicleDocument.objects.filter(
            vehicle=vehicle,
            document_type=document_data['document_type']
        ).first()
        
        if existing_doc:
            # Update existing document
            for key, value in document_data.items():
                setattr(existing_doc, key, value)
            existing_doc.document_file = document_file
            existing_doc.is_verified = False  # Reset verification
            existing_doc.verified_at = None
            existing_doc.verified_by = None
            existing_doc.save()
            return existing_doc
        else:
            # Create new document
            document = VehicleDocument.objects.create(
                vehicle=vehicle,
                document_file=document_file,
                **document_data
            )
            return document
    
    @staticmethod
    def verify_document(document, verified_by, is_verified, notes=None):
        """
        Verify or reject a document.
        """
        document.is_verified = is_verified
        document.verified_by = verified_by
        document.verified_at = timezone.now() if is_verified else None
        document.notes = notes
        document.save()
        
        # Check if all required documents are verified
        DocumentService._check_vehicle_document_status(document.vehicle)
        
        return document
    
    @staticmethod
    def get_expiring_documents(days_ahead=30):
        """
        Get documents that are expiring within the specified days.
        """
        expiry_date = timezone.now().date() + timedelta(days=days_ahead)
        
        return VehicleDocument.objects.filter(
            expiry_date__lte=expiry_date,
            is_verified=True
        ).order_by('expiry_date')
    
    @staticmethod
    def get_expired_documents():
        """
        Get all expired documents.
        """
        today = timezone.now().date()
        
        return VehicleDocument.objects.filter(
            expiry_date__lt=today,
            is_verified=True
        ).order_by('expiry_date')
    
    @staticmethod
    def create_insurance(vehicle, insurance_data, certificate_file):
        """
        Create or update vehicle insurance.
        """
        # Check if insurance already exists
        try:
            insurance = vehicle.insurance
            # Update existing insurance
            for key, value in insurance_data.items():
                setattr(insurance, key, value)
            insurance.certificate_file = certificate_file
            insurance.save()
        except Insurance.DoesNotExist:
            # Create new insurance
            insurance = Insurance.objects.create(
                vehicle=vehicle,
                certificate_file=certificate_file,
                **insurance_data
            )
        
        return insurance
    
    @staticmethod
    def get_expiring_insurance(days_ahead=30):
        """
        Get insurance policies that are expiring within the specified days.
        """
        expiry_date = timezone.now().date() + timedelta(days=days_ahead)
        
        return Insurance.objects.filter(
            end_date__lte=expiry_date,
            is_active=True
        ).order_by('end_date')
    
    @staticmethod
    def _check_vehicle_document_status(vehicle):
        """
        Check if vehicle has all required verified documents.
        """
        required_docs = ['registration', 'insurance']
        all_verified = True
        
        for doc_type in required_docs:
            if not vehicle.documents.filter(
                document_type=doc_type,
                is_verified=True
            ).exists():
                all_verified = False
                break
        
        # Update vehicle verification status if needed
        if all_verified and vehicle.verification_status == vehicle.VerificationStatus.PENDING:
            # Auto-approve vehicle if all documents are verified
            from apps.vehicles.services.vehicle_service import VehicleService
            VehicleService.verify_vehicle(
                vehicle,
                None,  # System verification
                vehicle.VerificationStatus.APPROVED
            )
