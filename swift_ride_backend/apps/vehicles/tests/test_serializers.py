"""
Tests for vehicle serializers.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.vehicles.models import VehicleType, Vehicle
from apps.vehicles.serializers import (
    VehicleTypeSerializer, VehicleSerializer, VehicleCreateSerializer,
    DocumentUploadSerializer, InsuranceCreateSerializer
)

User = get_user_model()


class VehicleTypeSerializerTest(TestCase):
    """
    Test cases for VehicleTypeSerializer.
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
    
    def test_vehicle_type_serialization(self):
        """Test vehicle type serialization."""
        serializer = VehicleTypeSerializer(self.vehicle_type)
        data = serializer.data
        
        self.assertEqual(data['name'], "Sedan")
        self.assertEqual(data['capacity'], 4)
        self.assertEqual(float(data['base_fare']), 500.00)


class VehicleCreateSerializerTest(TestCase):
    """
    Test cases for VehicleCreateSerializer.
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
    
    def test_valid_vehicle_creation(self):
        """Test valid vehicle creation."""
        data = {
            'vehicle_type_id': str(self.vehicle_type.id),
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'color': 'Black',
            'license_plate': 'ABC-123-XY',
            'vin_number': '1HGBH41JXMN109186',
            'fuel_type': 'petrol'
        }
        serializer = VehicleCreateSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
        vehicle = serializer.save(owner=self.user)
        self.assertEqual(vehicle.make, 'Toyota')
        self.assertEqual(vehicle.owner, self.user)
    
    def test_invalid_year(self):
        """Test invalid year validation."""
        data = {
            'vehicle_type_id': str(self.vehicle_type.id),
            'make': 'Toyota',
            'model': 'Camry',
            'year': 1980,  # Too old
            'color': 'Black',
            'license_plate': 'ABC-123-XY',
            'vin_number': '1HGBH41JXMN109186',
            'fuel_type': 'petrol'
        }
        serializer = VehicleCreateSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('year', serializer.errors)
    
    def test_invalid_license_plate(self):
        """Test invalid license plate validation."""
        data = {
            'vehicle_type_id': str(self.vehicle_type.id),
            'make': 'Toyota',
            'model': 'Camry',
            'year': 2020,
            'color': 'Black',
            'license_plate': 'AB',  # Too short
            'vin_number': '1HGBH41JXMN109186',
            'fuel_type': 'petrol'
        }
        serializer = VehicleCreateSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('license_plate', serializer.errors)


class DocumentUploadSerializerTest(TestCase):
    """
    Test cases for DocumentUploadSerializer.
    """
    
    def test_valid_document_data(self):
        """Test valid document data."""
        data = {
            'document_type': 'registration',
            'document_number': 'REG123456',
            'issue_date': timezone.now().date(),
            'expiry_date': timezone.now().date() + timedelta(days=365),
            'issuing_authority': 'FRSC'
        }
        serializer = DocumentUploadSerializer(data=data)
        
        self.assertTrue(serializer.is_valid())
    
    def test_expired_document(self):
        """Test expired document validation."""
        data = {
            'document_type': 'registration',
            'document_number': 'REG123456',
            'issue_date': timezone.now().date() - timedelta(days=400),
            'expiry_date': timezone.now().date() - timedelta(days=1),  # Expired
            'issuing_authority': 'FRSC'
        }
        serializer = DocumentUploadSerializer(data=data)
        
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)
