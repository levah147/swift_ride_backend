"""
Tests for user views.
"""

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from ..models import RiderProfile, DriverProfile

User = get_user_model()


class UserViewsTest(TestCase):
    """
    Test cases for user views.
    """
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            user_type='rider'
        )
        
        # Create JWT token for authentication
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_user_profile_view_get(self):
        """Test getting user profile."""
        self.authenticate()
        url = reverse('users:user-profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['phone_number'], '+2348012345678')
        self.assertEqual(response.data['first_name'], 'John')
    
    def test_user_profile_view_update(self):
        """Test updating user profile."""
        self.authenticate()
        url = reverse('users:user-profile')
        data = {
            'first_name': 'Jane',
            'last_name': 'Smith'
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Jane')
        self.assertEqual(self.user.last_name, 'Smith')
    
    def test_rider_profile_view(self):
        """Test rider profile view."""
        self.authenticate()
        url = reverse('users:rider-profile')
        
        # Test GET (should create profile if doesn't exist)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Test UPDATE
        data = {
            'emergency_contact': '+2348087654321',
            'preferred_payment_method': 'card'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify profile was updated
        profile = RiderProfile.objects.get(user=self.user)
        self.assertEqual(profile.emergency_contact, '+2348087654321')
        self.assertEqual(profile.preferred_payment_method, 'card')
    
    def test_driver_profile_view_unauthorized(self):
        """Test driver profile view with rider user (should fail)."""
        self.authenticate()
        url = reverse('users:driver-profile')
        response = self.client.get(url)
        
        # Should fail because user is a rider, not a driver
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_update_location(self):
        """Test updating user location."""
        self.authenticate()
        url = reverse('users:update-location')
        data = {
            'latitude': 6.5244,
            'longitude': 3.3792
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
    
    def test_update_location_missing_data(self):
        """Test updating location with missing data."""
        self.authenticate()
        url = reverse('users:update-location')
        data = {'latitude': 6.5244}  # Missing longitude
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['status'], 'error')
    
    def test_user_stats_view(self):
        """Test user stats view."""
        self.authenticate()
        url = reverse('users:user-stats')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('profile_completion', response.data)
        self.assertIn('total_rides', response.data)
    
    def test_unauthenticated_access(self):
        """Test accessing views without authentication."""
        url = reverse('users:user-profile')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class DriverViewsTest(TestCase):
    """
    Test cases for driver-specific views.
    """
    
    def setUp(self):
        self.client = APIClient()
        self.driver = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            user_type='driver'
        )
        
        # Create driver profile
        self.driver_profile = DriverProfile.objects.create(user=self.driver)
        
        # Create JWT token for authentication
        refresh = RefreshToken.for_user(self.driver)
        self.access_token = str(refresh.access_token)
        
    def authenticate(self):
        """Helper method to authenticate requests."""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
    
    def test_driver_status_toggle(self):
        """Test toggling driver online/offline status."""
        self.authenticate()
        url = reverse('users:driver-toggle-status')
        
        # Initially offline
        self.assertFalse(self.driver_profile.is_online)
        
        # Toggle to online
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertTrue(response.data['is_online'])
        
        # Verify in database
        self.driver_profile.refresh_from_db()
        self.assertTrue(self.driver_profile.is_online)
        
        # Toggle back to offline
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['is_online'])
    
    def test_nearby_drivers_view(self):
        """Test nearby drivers view."""
        # Create a rider to test the view
        rider = User.objects.create_user(
            phone_number='+2348087654321',
            first_name='Jane',
            last_name='Smith',
            user_type='rider',
            is_verified=True
        )
        
        refresh = RefreshToken.for_user(rider)
        access_token = str(refresh.access_token)
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        
        url = reverse('users:nearby-drivers')
        data = {
            'latitude': 6.5244,
            'longitude': 3.3792,
            'radius': 5
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'success')
        self.assertIn('drivers', response.data)
