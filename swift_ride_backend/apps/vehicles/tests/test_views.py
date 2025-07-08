"""
Tests for vehicle views.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.vehicles.models import VehicleType, Vehicle

User = get_user_model()


class VehicleViewSetTest(TestCase):
    """
    Test cases for VehicleViewSet.
    """
    
    def setUp(self):
        self.client = APIClient()
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
    
    def test_list_vehicles_as_driver(self):
        """Test listing vehicles as driver."""
        self.client.force_authenticate(user=self.driver)
        url = reverse('vehicle-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_create_vehicle_as_driver(self):
        """Test creating vehicle as driver."""
        self.client.force_authenticate(user=self.driver)
        url = reverse('vehicle-list')
        data = {
            'vehicle_type_id': str(self.vehicle_type.id),
            'make': 'Honda',
            'model': 'Civic',
            'year': 2021,
            'color': 'White',
            'license_plate': 'XYZ-456-AB',
            'vin_number': '2HGBH41JXMN109187',
            'fuel_type': 'petrol'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vehicle.objects.count(), 2)
    
    def test_verify_vehicle_as_admin(self):
        """Test verifying vehicle as admin."""
        self.client.force_authenticate(user=self.admin)
        url = reverse('vehicle-verify', kwargs={'pk': self.vehicle.id})
        data = {
            'status': 'approved'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.vehicle.refresh_from_db()
        self.assertEqual(self.vehicle.verification_status, 'approved')
    
    def test_verify_vehicle_as_non_admin(self):
        """Test verifying vehicle as non-admin (should fail)."""
        self.client.force_authenticate(user=self.driver)
        url = reverse('vehicle-verify', kwargs={'pk': self.vehicle.id})
        data = {
            'status': 'approved'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class VehicleTypeViewSetTest(TestCase):
    """
    Test cases for VehicleTypeViewSet.
    """
    
    def setUp(self):
        self.client = APIClient()
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
    
    def test_list_vehicle_types(self):
        """Test listing vehicle types."""
        self.client.force_authenticate(user=self.user)
        url = reverse('vehicle-type-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_list_vehicle_types_unauthenticated(self):
        """Test listing vehicle types without authentication."""
        url = reverse('vehicle-type-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
