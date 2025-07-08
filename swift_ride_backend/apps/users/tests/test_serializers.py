"""
Tests for user serializers.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from datetime import date, timedelta

from ..serializers import (
    UserSerializer, UserBasicSerializer, RiderProfileSerializer,
    DriverProfileSerializer, UserPreferencesSerializer
)
from ..models import RiderProfile, DriverProfile, UserPreferences

User = get_user_model()


class UserSerializerTest(TestCase):
    """
    Test cases for UserSerializer.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            user_type='rider'
        )
    
    def test_user_serialization(self):
        """Test user serialization."""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['phone_number'], '+2348012345678')
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'john.doe@example.com')
        self.assertEqual(data['user_type'], 'rider')
    
    def test_user_basic_serialization(self):
        """Test basic user serialization."""
        serializer = UserBasicSerializer(self.user)
        data = serializer.data
        
        self.assertIn('id', data)
        self.assertIn('first_name', data)
        self.assertIn('last_name', data)
        self.assertNotIn('phone_number', data)  # Should not include sensitive data


class RiderProfileSerializerTest(TestCase):
    """
    Test cases for RiderProfileSerializer.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            user_type='rider'
        )
        self.profile = RiderProfile.objects.create(
            user=self.user,
            emergency_contact='+2348087654321',
            preferred_payment_method='card'
        )
    
    def test_rider_profile_serialization(self):
        """Test rider profile serialization."""
        serializer = RiderProfileSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data['emergency_contact'], '+2348087654321')
        self.assertEqual(data['preferred_payment_method'], 'card')
        self.assertEqual(data['rating'], 0.0)
        self.assertEqual(data['total_rides'], 0)


class DriverProfileSerializerTest(TestCase):
    """
    Test cases for DriverProfileSerializer.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            user_type='driver'
        )
        self.profile = DriverProfile.objects.create(
            user=self.user,
            license_number='LAG-12345678-AA',
            license_expiry=date.today() + timedelta(days=365),
            emergency_contact='+2348087654321'
        )
    
    def test_driver_profile_serialization(self):
        """Test driver profile serialization."""
        serializer = DriverProfileSerializer(self.profile)
        data = serializer.data
        
        self.assertEqual(data['license_number'], 'LAG-12345678-AA')
        self.assertEqual(data['emergency_contact'], '+2348087654321')
        self.assertFalse(data['is_online'])
        self.assertEqual(data['rating'], 0.0)
