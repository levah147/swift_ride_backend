"""
Tests for vehicle services.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.vehicles.models import VehicleType, Vehicle, VehicleDocument, Insurance
from apps.vehicles.services.vehicle_service import VehicleService
from apps.vehicles.services.document_service import DocumentService
from apps.vehicles.services.verification_service import VerificationService

User = get_user_model()


class VehicleServiceTest(TestCase):
    """
    Test cases for VehicleService.
    """
    
    def setUp(self):
        self.driver = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123",
            user_type="driver"
        )
        self.admin = User.objects.create_user(
            phone_number="+2348123456788",
            password="testpass123",
            is_staff=True
        )
        self.vehicle_type = VehicleType.objects.create(
            name="Sedan",
            base_fare=500.00,
            per_km_rate=50.00,
            per_minute_rate=10.00,
            capacity=4
        )
    
    def test_register_vehicle(self):
        """Test vehicle registration."""
        vehicle_data = {
            'vehicle_type': self.vehicle_type,
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'color': 'Black',
            'license_plate': 'ABC-123-XY',
            'vin_number': '1HGBH41JXMN109186',
            'fuel_type': Vehicle.FuelType.PETROL
        }
        
        vehicle = VehicleService.register_vehicle(self.driver, vehicle_data)
        
        self.assertEqual(vehicle.owner, self.driver)
        self.assertEqual(vehicle.make, 'Toyota')
        self.assertEqual(vehicle.verification_status, Vehicle.VerificationStatus.PENDING)
    
    def test_verify_vehicle(self):
        """Test vehicle verification."""
        vehicle = Vehicle.objects.create(
            owner=self.driver,
            vehicle_type=self.vehicle_type,
            make="Toyota",
            model="Camry",
            year=2020,
            color="Black",
            license_plate="ABC-123-XY",
            vin_number="1HGBH41JXMN109186"
        )
        
        verified_vehicle = VehicleService.verify_vehicle(
            vehicle,
            self.admin,
            Vehicle.VerificationStatus.APPROVED
        )
        
        self.assertEqual(verified_vehicle.verification_status, Vehicle.VerificationStatus.APPROVED)
        self.assertEqual(verified_vehicle.verified_by, self.admin)
        self.assertIsNotNone(verified_vehicle.verified_at)
    
    def test_check_vehicle_eligibility(self):
        """Test vehicle eligibility check."""
        vehicle = Vehicle.objects.create(
            owner=self.driver,
            vehicle_type=self.vehicle_type,
            make="Toyota",
            model="Camry",
            year=2020,
            color="Black",
            license_plate="ABC-123-XY",
            vin_number="1HGBH41JXMN109186",
            verification_status=Vehicle.VerificationStatus.APPROVED
        )
        
        is_eligible, message = VehicleService.check_vehicle_eligibility(vehicle)
        
        # Should not be eligible without documents and insurance
        self.assertFalse(is_eligible)
        self.assertIn("documents", message.lower())


class DocumentServiceTest(TestCase):
    """
    Test cases for DocumentService.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123"
        )
        self.admin = User.objects.create_user(
            phone_number="+2348123456788",
            password="testpass123",
            is_staff=True
        )
        self.vehicle_type = VehicleType.objects.create(
            name="Sedan",
            base_fare=500.00,
            per_km_rate=50.00,
            per_minute_rate=10.00,
            capacity=4
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.user,
            vehicle_type=self.vehicle_type,
            make="Toyota",
            model="Camry",
            year=2020,
            color="Black",
            license_plate="ABC-123-XY",
            vin_number="1HGBH41JXMN109186"
        )
    
    def test_upload_document(self):
        """Test document upload."""
        document_data = {
            'document_type': VehicleDocument.DocumentType.REGISTRATION,
            'document_number': 'REG123456',
            'issue_date': timezone.now().date(),
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'issuing_authority': 'FRSC'
        }
        
        document = DocumentService.upload_document(
            self.vehicle,
            document_data,
            None  # Mock file
        )
        
        self.assertEqual(document.vehicle, self.vehicle)
        self.assertEqual(document.document_type, VehicleDocument.DocumentType.REGISTRATION)
        self.assertFalse(document.is_verified)
    
    def test_verify_document(self):
        """Test document verification."""
        document = VehicleDocument.objects.create(
            vehicle=self.vehicle,
            document_type=VehicleDocument.DocumentType.REGISTRATION,
            document_number='REG123456',
            issue_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timedelta(days=365),
            issuing_authority='FRSC'
        )
        
        verified_document = DocumentService.verify_document(
            document,
            self.admin,
            True,
            "Document verified successfully"
        )
        
        self.assertTrue(verified_document.is_verified)
        self.assertEqual(verified_document.verified_by, self.admin)
        self.assertIsNotNone(verified_document.verified_at)


class VerificationServiceTest(TestCase):
    """
    Test cases for VerificationService.
    """
    
    def setUp(self):
        self.driver = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123",
            user_type="driver"
        )
        self.admin = User.objects.create_user(
            phone_number="+2348123456788",
            password="testpass123",
            is_staff=True
        )
        self.vehicle_type = VehicleType.objects.create(
            name="Sedan",
            base_fare=500.00,
            per_km_rate=50.00,
            per_minute_rate=10.00,
            capacity=4
        )
        self.vehicle = Vehicle.objects.create(
            owner=self.driver,
            vehicle_type=self.vehicle_type,
            make="Toyota",
            model="Camry",
            year=2020,
            color="Black",
            license_plate="ABC-123-XY",
            vin_number="1HGBH41JXMN109186"
        )
    
    def test_get_verification_checklist(self):
        """Test verification checklist generation."""
        checklist = VerificationService.get_verification_checklist(self.vehicle)
        
        self.assertIn('vehicle_info', checklist)
        self.assertIn('photos', checklist)
        self.assertIn('documents', checklist)
        self.assertIn('insurance', checklist)
        self.assertIn('inspection', checklist)
        self.assertIn('overall_status', checklist)
    
    def test_verify_vehicle_documents(self):
        """Test vehicle documents verification."""
        # Create required documents
        VehicleDocument.objects.create(
            vehicle=self.vehicle,
            document_type=VehicleDocument.DocumentType.REGISTRATION,
            document_number='REG123456',
            issue_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timedelta(days=365),
            issuing_authority='FRSC',
            is_verified=True
        )
        
        all_verified, results = VerificationService.verify_vehicle_documents(self.vehicle)
        
        self.assertFalse(all_verified)  # Insurance document missing
        self.assertIn('registration', results)
        self.assertIn('insurance', results)
