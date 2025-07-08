"""
Tests for vehicle models.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta

from apps.vehicles.models import (
    VehicleType, Vehicle, VehicleDocument, Insurance, 
    Inspection, VehicleMaintenanceRecord
)

User = get_user_model()


class VehicleTypeModelTest(TestCase):
    """
    Test cases for VehicleType model.
    """
    
    def setUp(self):
        self.vehicle_type = VehicleType.objects.create(
            name="Sedan",
            description="4-door sedan vehicle",
            base_fare=500.00,
            per_km_rate=50.00,
            per_minute_rate=10.00,
            capacity=4
        )
    
    def test_vehicle_type_creation(self):
        """Test vehicle type creation."""
        self.assertEqual(self.vehicle_type.name, "Sedan")
        self.assertEqual(self.vehicle_type.capacity, 4)
        self.assertTrue(self.vehicle_type.is_active)
    
    def test_vehicle_type_str(self):
        """Test vehicle type string representation."""
        self.assertEqual(str(self.vehicle_type), "Sedan")


class VehicleModelTest(TestCase):
    """
    Test cases for Vehicle model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123"
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
            vin_number="1HGBH41JXMN109186",
            fuel_type=Vehicle.FuelType.PETROL
        )
    
    def test_vehicle_creation(self):
        """Test vehicle creation."""
        self.assertEqual(self.vehicle.make, "Toyota")
        self.assertEqual(self.vehicle.model, "Camry")
        self.assertEqual(self.vehicle.year, 2020)
        self.assertEqual(self.vehicle.verification_status, Vehicle.VerificationStatus.PENDING)
        self.assertTrue(self.vehicle.is_active)
    
    def test_vehicle_str(self):
        """Test vehicle string representation."""
        expected = "Toyota Camry (ABC-123-XY)"
        self.assertEqual(str(self.vehicle), expected)
    
    def test_is_verified_property(self):
        """Test is_verified property."""
        self.assertFalse(self.vehicle.is_verified)
        
        self.vehicle.verification_status = Vehicle.VerificationStatus.APPROVED
        self.vehicle.save()
        self.assertTrue(self.vehicle.is_verified)
    
    def test_display_name_property(self):
        """Test display_name property."""
        expected = "2020 Toyota Camry"
        self.assertEqual(self.vehicle.display_name, expected)


class VehicleDocumentModelTest(TestCase):
    """
    Test cases for VehicleDocument model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123"
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
        self.document = VehicleDocument.objects.create(
            vehicle=self.vehicle,
            document_type=VehicleDocument.DocumentType.REGISTRATION,
            document_number="REG123456",
            issue_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timedelta(days=365),
            issuing_authority="FRSC"
        )
    
    def test_document_creation(self):
        """Test document creation."""
        self.assertEqual(self.document.document_type, VehicleDocument.DocumentType.REGISTRATION)
        self.assertEqual(self.document.document_number, "REG123456")
        self.assertFalse(self.document.is_verified)
    
    def test_is_expired_property(self):
        """Test is_expired property."""
        self.assertFalse(self.document.is_expired)
        
        # Create expired document
        expired_doc = VehicleDocument.objects.create(
            vehicle=self.vehicle,
            document_type=VehicleDocument.DocumentType.INSURANCE,
            document_number="INS123456",
            issue_date=timezone.now().date() - timedelta(days=400),
            expiry_date=timezone.now().date() - timedelta(days=1),
            issuing_authority="Insurance Company"
        )
        self.assertTrue(expired_doc.is_expired)
    
    def test_days_until_expiry_property(self):
        """Test days_until_expiry property."""
        days = self.document.days_until_expiry
        self.assertGreater(days, 360)  # Should be around 365 days


class InsuranceModelTest(TestCase):
    """
    Test cases for Insurance model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123"
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
        self.insurance = Insurance.objects.create(
            vehicle=self.vehicle,
            insurance_type=Insurance.InsuranceType.COMPREHENSIVE,
            policy_number="POL123456",
            insurance_company="Test Insurance Co.",
            premium_amount=50000.00,
            coverage_amount=2000000.00,
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=365)
        )
    
    def test_insurance_creation(self):
        """Test insurance creation."""
        self.assertEqual(self.insurance.policy_number, "POL123456")
        self.assertEqual(self.insurance.insurance_type, Insurance.InsuranceType.COMPREHENSIVE)
        self.assertTrue(self.insurance.is_active)
    
    def test_is_expired_property(self):
        """Test is_expired property."""
        self.assertFalse(self.insurance.is_expired)


class InspectionModelTest(TestCase):
    """
    Test cases for Inspection model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number="+2348123456789",
            password="testpass123"
        )
        self.inspector = User.objects.create_user(
            phone_number="+2348123456788",
            password="testpass123"
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
        self.inspection = Inspection.objects.create(
            vehicle=self.vehicle,
            inspection_type=Inspection.InspectionType.INITIAL,
            scheduled_date=timezone.now() + timedelta(days=1),
            inspector=self.inspector,
            overall_score=85
        )
    
    def test_inspection_creation(self):
        """Test inspection creation."""
        self.assertEqual(self.inspection.inspection_type, Inspection.InspectionType.INITIAL)
        self.assertEqual(self.inspection.status, Inspection.InspectionStatus.SCHEDULED)
        self.assertEqual(self.inspection.overall_score, 85)
    
    def test_is_passed_property(self):
        """Test is_passed property."""
        self.assertFalse(self.inspection.is_passed)
        
        self.inspection.status = Inspection.InspectionStatus.PASSED
        self.inspection.save()
        self.assertTrue(self.inspection.is_passed)
