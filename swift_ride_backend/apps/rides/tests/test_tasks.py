"""
Tests for rides app Celery tasks.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.users.models import User
from apps.rides.models import Ride, BargainOffer
from apps.rides.tasks import (
    process_ride_request, expire_bargain_offers, 
    cleanup_expired_rides, send_ride_reminders
)


class RideTasksTest(TestCase):
    """
    Test cases for ride-related Celery tasks.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.rider = User.objects.create_user(
            email='rider@test.com',
            phone_number='+2348012345678',
            first_name='Test',
            last_name='Rider'
        )
        
        self.driver = User.objects.create_user(
            email='driver@test.com',
            phone_number='+2348012345679',
            first_name='Test',
            last_name='Driver',
            is_driver=True
        )
        
        self.ride = Ride.objects.create(
            rider=self.rider,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00'),
            status=Ride.RideStatus.REQUESTED
        )
    
    @patch('apps.rides.services.driver_allocator.DriverAllocator.allocate_driver_automatically')
    @patch('apps.rides.services.driver_allocator.DriverAllocator.broadcast_ride_to_drivers')
    def test_process_ride_request_auto_allocation(self, mock_broadcast, mock_allocate):
        """
        Test processing ride request with automatic allocation.
        """
        # Mock successful auto allocation
        mock_allocate.return_value = (True, "Driver allocated", self.driver)
        
        result = process_ride_request.apply(args=[str(self.ride.id)])
        
        self.assertTrue(result.successful())
        mock_allocate.assert_called_once_with(self.ride)
        mock_broadcast.assert_not_called()
    
    @patch('apps.rides.services.driver_allocator.DriverAllocator.allocate_driver_automatically')
    @patch('apps.rides.services.driver_allocator.DriverAllocator.broadcast_ride_to_drivers')
    def test_process_ride_request_broadcast(self, mock_broadcast, mock_allocate):
        """
        Test processing ride request with broadcast to drivers.
        """
        # Mock failed auto allocation
        mock_allocate.return_value = (False, "No drivers available", None)
        mock_broadcast.return_value = [self.driver]
        
        result = process_ride_request.apply(args=[str(self.ride.id)])
        
        self.assertTrue(result.successful())
        mock_allocate.assert_called_once_with(self.ride)
        mock_broadcast.assert_called_once_with(self.ride)
    
    def test_expire_bargain_offers(self):
        """
        Test expiring bargain offers task.
        """
        # Create expired offer
        expired_offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() - timedelta(minutes=5)
        )
        
        # Create non-expired offer
        active_offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.driver,
            amount=Decimal('1300.00'),
            offer_type=BargainOffer.OfferType.DRIVER,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        result = expire_bargain_offers.apply()
        
        self.assertTrue(result.successful())
        
        # Check that expired offer was updated
        expired_offer.refresh_from_db()
        self.assertEqual(expired_offer.status, BargainOffer.OfferStatus.EXPIRED)
        
        # Check that active offer was not affected
        active_offer.refresh_from_db()
        self.assertEqual(active_offer.status, BargainOffer.OfferStatus.PENDING)
    
    def test_cleanup_expired_rides(self):
        """
        Test cleaning up expired ride requests.
        """
        # Create expired ride
        expired_ride = Ride.objects.create(
            rider=self.rider,
            pickup_location='Test Location',
            dropoff_location='Test Destination',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1000.00'),
            status=Ride.RideStatus.SEARCHING,
            created_at=timezone.now() - timedelta(minutes=15)
        )
        
        # Manually set created_at to simulate old ride
        Ride.objects.filter(id=expired_ride.id).update(
            created_at=timezone.now() - timedelta(minutes=15)
        )
        
        result = cleanup_expired_rides.apply()
        
        self.assertTrue(result.successful())
        
        # Check that expired ride was cancelled
        expired_ride.refresh_from_db()
        self.assertEqual(expired_ride.status, Ride.RideStatus.CANCELLED)
    
    @patch('apps.notifications.services.notification_service.NotificationService.send_ride_reminder')
    def test_send_ride_reminders(self, mock_send_reminder):
        """
        Test sending ride reminders for scheduled rides.
        """
        # Create scheduled ride due soon
        scheduled_ride = Ride.objects.create(
            rider=self.rider,
            pickup_location='Test Location',
            dropoff_location='Test Destination',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1000.00'),
            is_scheduled=True,
            schedule_time=timezone.now() + timedelta(minutes=25),  # Due in 25 minutes
            status=Ride.RideStatus.REQUESTED
        )
        
        result = send_ride_reminders.apply()
        
        self.assertTrue(result.successful())
        mock_send_reminder.assert_called_once_with(scheduled_ride)
    
    def test_process_nonexistent_ride(self):
        """
        Test processing a ride request that doesn't exist.
        """
        fake_ride_id = '00000000-0000-0000-0000-000000000000'
        
        result = process_ride_request.apply(args=[fake_ride_id])
        
        # Task should handle the error gracefully
        self.assertFalse(result.successful())
    
    @patch('apps.rides.services.driver_allocator.DriverAllocator.allocate_driver_automatically')
    def test_process_ride_request_with_exception(self, mock_allocate):
        """
        Test processing ride request when service raises exception.
        """
        # Mock service to raise exception
        mock_allocate.side_effect = Exception("Service error")
        
        result = process_ride_request.apply(args=[str(self.ride.id)])
        
        # Task should handle the exception
        self.assertFalse(result.successful())
