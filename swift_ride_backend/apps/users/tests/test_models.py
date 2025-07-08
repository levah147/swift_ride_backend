"""
Tests for user models.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta

from ..models import RiderProfile, DriverProfile, UserPreferences

User = get_user_model()


class CustomUserModelTest(TestCase):
    """
    Test cases for CustomUser model.
    """
    
    def setUp(self):
        self.user_data = {
            'phone_number': '+2348012345678',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'user_type': 'rider'
        }
    
    def test_create_user(self):
        """Test creating a regular user."""
        user = User.objects.create_user(**self.user_data)
        
        self.assertEqual(user.phone_number, '+2348012345678')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertEqual(user.user_type, 'rider')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_verified)
    
    def test_create_superuser(self):
        """Test creating a superuser."""
        user = User.objects.create_superuser(
            phone_number='+2348012345678',
            password='testpass123'
        )
        
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)
        self.assertEqual(user.user_type, 'admin')
    
    def test_user_string_representation(self):
        """Test user string representation."""
        user = User.objects.create_user(**self.user_data)
        expected_str = f"{user.first_name} {user.last_name} ({user.phone_number})"
        self.assertEqual(str(user), expected_str)
    
    def test_phone_number_required(self):
        """Test that phone number is required."""
        with self.assertRaises(ValueError):
            User.objects.create_user(phone_number='')


class RiderProfileModelTest(TestCase):
    """
    Test cases for RiderProfile model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            user_type='rider'
        )
    
    def test_create_rider_profile(self):
        """Test creating a rider profile."""
        profile = RiderProfile.objects.create(
            user=self.user,
            emergency_contact='+2348087654321',
            preferred_payment_method='card'
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.emergency_contact, '+2348087654321')
        self.assertEqual(profile.preferred_payment_method, 'card')
        self.assertEqual(profile.rating, 0.0)
        self.assertEqual(profile.total_rides, 0)
    
    def test_rider_profile_string_representation(self):
        """Test rider profile string representation."""
        profile = RiderProfile.objects.create(user=self.user)
        expected_str = f"Rider Profile - {self.user.first_name} {self.user.last_name}"
        self.assertEqual(str(profile), expected_str)


class DriverProfileModelTest(TestCase):
    """
    Test cases for DriverProfile model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            user_type='driver'
        )
    
    def test_create_driver_profile(self):
        """Test creating a driver profile."""
        profile = DriverProfile.objects.create(
            user=self.user,
            license_number='LAG-12345678-AA',
            license_expiry=date.today() + timedelta(days=365),
            emergency_contact='+2348087654321'
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.license_number, 'LAG-12345678-AA')
        self.assertEqual(profile.emergency_contact, '+2348087654321')
        self.assertFalse(profile.is_online)
        self.assertEqual(profile.rating, 0.0)
        self.assertEqual(profile.total_rides, 0)
    
    def test_driver_profile_string_representation(self):
        """Test driver profile string representation."""
        profile = DriverProfile.objects.create(user=self.user)
        expected_str = f"Driver Profile - {self.user.first_name} {self.user.last_name}"
        self.assertEqual(str(profile), expected_str)


class UserPreferencesModelTest(TestCase):
    """
    Test cases for UserPreferences model.
    """
    
    def setUp(self):
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe'
        )
    
    def test_create_user_preferences(self):
        """Test creating user preferences."""
        preferences = UserPreferences.objects.create(
            user=self.user,
            language='en',
            currency='NGN',
            notifications_enabled=True
        )
        
        self.assertEqual(preferences.user, self.user)
        self.assertEqual(preferences.language, 'en')
        self.assertEqual(preferences.currency, 'NGN')
        self.assertTrue(preferences.notifications_enabled)
    
    def test_user_preferences_string_representation(self):
        """Test user preferences string representation."""
        preferences = UserPreferences.objects.create(user=self.user)
        expected_str = f"Preferences - {self.user.first_name} {self.user.last_name}"
        self.assertEqual(str(preferences), expected_str)
