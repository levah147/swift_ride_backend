"""
Tests for user services.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, MagicMock

from ..services.user_service import UserService
from ..services.profile_service import ProfileService
from ..services.verification_service import VerificationService
from ..models import DriverProfile, RiderProfile

User = get_user_model()


class UserServiceTest(TestCase):
    """
    Test cases for UserService.
    """
    
    def setUp(self):
        self.user_service = UserService()
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            user_type='rider'
        )
    
    def test_get_user_stats(self):
        """Test getting user statistics."""
        stats = self.user_service.get_user_stats(self.user)
        
        self.assertIn('profile_completion', stats)
        self.assertIn('total_rides', stats)
        self.assertIn('member_since', stats)
        self.assertEqual(stats['total_rides'], 0)
    
    def test_update_user_location(self):
        """Test updating user location."""
        success = self.user_service.update_user_location(self.user, 6.5244, 3.3792)
        
        self.assertTrue(success)
        self.user.refresh_from_db()
        self.assertEqual(float(self.user.current_latitude), 6.5244)
        self.assertEqual(float(self.user.current_longitude), 3.3792)
    
    def test_get_user_location(self):
        """Test getting user location."""
        # First update location
        self.user_service.update_user_location(self.user, 6.5244, 3.3792)
        
        location = self.user_service.get_user_location(self.user)
        
        self.assertIsNotNone(location)
        self.assertEqual(location['latitude'], 6.5244)
        self.assertEqual(location['longitude'], 3.3792)
    
    def test_deactivate_user(self):
        """Test deactivating user account."""
        success = self.user_service.deactivate_user(self.user)
        
        self.assertTrue(success)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.deactivated_at)


class ProfileServiceTest(TestCase):
    """
    Test cases for ProfileService.
    """
    
    def setUp(self):
        self.profile_service = ProfileService()
        self.driver = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            user_type='driver',
            is_verified=True,
            current_latitude=6.5244,
            current_longitude=3.3792
        )
        self.driver_profile = DriverProfile.objects.create(
            user=self.driver,
            is_online=True
        )
    
    def test_get_nearby_drivers(self):
        """Test getting nearby drivers."""
        nearby_drivers = self.profile_service.get_nearby_drivers(6.5244, 3.3792, 5)
        
        self.assertEqual(len(nearby_drivers), 1)
        self.assertEqual(nearby_drivers[0]['driver_id'], self.driver.id)
        self.assertIn('distance', nearby_drivers[0])
        self.assertIn('estimated_arrival', nearby_drivers[0])
    
    def test_update_driver_status(self):
        """Test updating driver status."""
        success = self.profile_service.update_driver_status(self.driver, False)
        
        self.assertTrue(success)
        self.driver_profile.refresh_from_db()
        self.assertFalse(self.driver_profile.is_online)
    
    def test_get_driver_profile_completion(self):
        """Test getting driver profile completion."""
        completion = self.profile_service.get_driver_profile_completion(self.driver)
        
        self.assertIn('completion_percentage', completion)
        self.assertIn('missing_fields', completion)
        self.assertIn('can_go_online', completion)


class VerificationServiceTest(TestCase):
    """
    Test cases for VerificationService.
    """
    
    def setUp(self):
        self.verification_service = VerificationService()
        self.user = User.objects.create_user(
            phone_number='+2348012345678',
            first_name='John',
            last_name='Doe',
            nin='12345678901',
            bvn='12345678901'
        )
    
    @patch.object(VerificationService, '_simulate_nin_verification')
    def test_verify_nin(self, mock_nin_verification):
        """Test NIN verification."""
        mock_nin_verification.return_value = {
            'status': 'verified',
            'message': 'NIN verified successfully'
        }
        
        result = self.verification_service._verify_nin('12345678901')
        
        self.assertEqual(result['status'], 'verified')
        self.assertIn('verified_at', result)
    
    def test_verify_invalid_nin(self):
        """Test verification with invalid NIN."""
        result = self.verification_service._verify_nin('123')  # Invalid format
        
        self.assertEqual(result['status'], 'failed')
        self.assertIn('Invalid NIN format', result['message'])
    
    @patch.object(VerificationService, '_simulate_bvn_verification')
    def test_verify_bvn(self, mock_bvn_verification):
        """Test BVN verification."""
        mock_bvn_verification.return_value = {
            'status': 'verified',
            'message': 'BVN verified successfully'
        }
        
        result = self.verification_service._verify_bvn('12345678901')
        
        self.assertEqual(result['status'], 'verified')
        self.assertIn('verified_at', result)
