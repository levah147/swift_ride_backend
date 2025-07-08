"""
Tests for rides app services.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.users.models import User
from apps.rides.models import Ride, BargainOffer
from apps.rides.services.fare_calculator import FareCalculator
from apps.rides.services.bargain_handler import BargainHandler
from apps.rides.services.driver_allocator import DriverAllocator
from apps.rides.services.route_optimizer import RouteOptimizer


class FareCalculatorTest(TestCase):
    """
    Test cases for FareCalculator service.
    """
    
    def test_calculate_base_fare(self):
        """
        Test basic fare calculation.
        """
        distance_km = 10.0
        duration_minutes = 30
        
        fare = FareCalculator.calculate_base_fare(distance_km, duration_minutes)
        
        # Base fare (200) + distance (10 * 80) + time (30 * 15) = 1450
        expected_fare = Decimal('200.00') + Decimal('800.00') + Decimal('450.00')
        self.assertEqual(fare, expected_fare)
    
    def test_minimum_fare_applied(self):
        """
        Test that minimum fare is applied for short rides.
        """
        distance_km = 0.5  # Very short distance
        duration_minutes = 5
        
        fare = FareCalculator.calculate_base_fare(distance_km, duration_minutes)
        
        # Should return minimum fare
        self.assertEqual(fare, FareCalculator.MINIMUM_FARE)
    
    def test_calculate_estimated_fare_with_multipliers(self):
        """
        Test fare calculation with vehicle and time multipliers.
        """
        pickup_lat, pickup_lon = 6.4281, 3.4219
        dropoff_lat, dropoff_lon = 6.6018, 3.3515
        
        result = FareCalculator.calculate_estimated_fare(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
            vehicle_type='suv'
        )
        
        self.assertIn('estimated_fare', result)
        self.assertIn('base_fare', result)
        self.assertIn('vehicle_multiplier', result)
        self.assertIn('distance_km', result)
        self.assertIn('breakdown', result)
        
        # SUV should have higher multiplier
        self.assertEqual(result['vehicle_multiplier'], 1.3)
    
    def test_calculate_cancellation_fee(self):
        """
        Test cancellation fee calculation.
        """
        # No fee for early cancellation
        fee = FareCalculator.calculate_cancellation_fee('searching', 5)
        self.assertEqual(fee, Decimal('0.00'))
        
        # Small fee for accepted rides
        fee = FareCalculator.calculate_cancellation_fee('accepted', 10)
        self.assertEqual(fee, Decimal('50.00'))
        
        # Higher fee for assigned driver
        fee = FareCalculator.calculate_cancellation_fee('driver_assigned', 15)
        self.assertEqual(fee, Decimal('100.00'))
    
    def test_calculate_driver_earnings(self):
        """
        Test driver earnings calculation.
        """
        total_fare = Decimal('1000.00')
        commission_rate = 0.20
        
        result = FareCalculator.calculate_driver_earnings(total_fare, commission_rate)
        
        self.assertEqual(result['total_fare'], 1000.0)
        self.assertEqual(result['commission_rate'], 0.20)
        self.assertEqual(result['commission_amount'], 200.0)
        self.assertEqual(result['driver_earnings'], 800.0)


class BargainHandlerTest(TestCase):
    """
    Test cases for BargainHandler service.
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
            status=Ride.RideStatus.SEARCHING
        )
    
    def test_initiate_bargaining(self):
        """
        Test initiating bargaining process.
        """
        success, message = BargainHandler.initiate_bargaining(self.ride)
        
        self.assertTrue(success)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.RideStatus.BARGAINING)
    
    def test_initiate_bargaining_invalid_status(self):
        """
        Test initiating bargaining with invalid ride status.
        """
        self.ride.status = Ride.RideStatus.COMPLETED
        self.ride.save()
        
        success, message = BargainHandler.initiate_bargaining(self.ride)
        
        self.assertFalse(success)
        self.assertIn('searching status', message)
    
    @patch('apps.rides.services.bargain_handler.BargainHandler._send_offer_notification')
    def test_make_offer_valid(self, mock_notification):
        """
        Test making a valid bargain offer.
        """
        self.ride.status = Ride.RideStatus.BARGAINING
        self.ride.save()
        
        success, message, offer = BargainHandler.make_offer(
            self.ride, self.rider, Decimal('1200.00'), 
            BargainOffer.OfferType.RIDER, 'Please accept'
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(offer)
        self.assertEqual(offer.amount, Decimal('1200.00'))
        self.assertEqual(offer.offered_by, self.rider)
        mock_notification.assert_called_once()
    
    def test_make_offer_invalid_amount(self):
        """
        Test making an offer with invalid amount.
        """
        self.ride.status = Ride.RideStatus.BARGAINING
        self.ride.save()
        
        # Amount too low (less than 50% of estimated fare)
        success, message, offer = BargainHandler.make_offer(
            self.ride, self.rider, Decimal('500.00'), 
            BargainOffer.OfferType.RIDER
        )
        
        self.assertFalse(success)
        self.assertIsNone(offer)
        self.assertIn('too low', message)
    
    @patch('apps.rides.services.bargain_handler.BargainHandler._send_acceptance_notification')
    def test_accept_offer(self, mock_notification):
        """
        Test accepting a bargain offer.
        """
        self.ride.status = Ride.RideStatus.BARGAINING
        self.ride.save()
        
        # Create offer
        offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        success, message = BargainHandler.accept_offer(offer, self.driver)
        
        self.assertTrue(success)
        offer.refresh_from_db()
        self.assertEqual(offer.status, BargainOffer.OfferStatus.ACCEPTED)
        
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.final_fare, Decimal('1200.00'))
        self.assertEqual(self.ride.driver, self.driver)
        mock_notification.assert_called_once()
    
    def test_reject_offer(self):
        """
        Test rejecting a bargain offer.
        """
        self.ride.status = Ride.RideStatus.BARGAINING
        self.ride.save()
        
        # Create offer
        offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        success, message = BargainHandler.reject_offer(
            offer, self.driver, 'Amount too low'
        )
        
        self.assertTrue(success)
        offer.refresh_from_db()
        self.assertEqual(offer.status, BargainOffer.OfferStatus.REJECTED)
        self.assertEqual(offer.rejection_reason, 'Amount too low')


class DriverAllocatorTest(TestCase):
    """
    Test cases for DriverAllocator service.
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
            status=Ride.RideStatus.SEARCHING
        )
    
    @patch('apps.rides.services.driver_allocator.DriverAllocator._get_available_drivers')
    def test_find_best_drivers(self, mock_get_drivers):
        """
        Test finding best drivers for a ride.
        """
        mock_get_drivers.return_value = [self.driver]
        
        with patch.object(DriverAllocator, '_calculate_driver_score', return_value=0.8):
            with patch.object(DriverAllocator, '_calculate_distance_to_pickup', return_value=5.0):
                with patch.object(DriverAllocator, '_estimate_arrival_time', return_value=15):
                    drivers = DriverAllocator.find_best_drivers(self.ride, limit=5)
        
        self.assertEqual(len(drivers), 1)
        self.assertEqual(drivers[0]['driver'], self.driver)
        self.assertEqual(drivers[0]['score'], 0.8)
        self.assertEqual(drivers[0]['distance_km'], 5.0)
    
    @patch('apps.rides.services.driver_allocator.DriverAllocator.find_best_drivers')
    @patch('apps.rides.services.driver_allocator.DriverAllocator._is_driver_available')
    def test_allocate_driver_automatically(self, mock_is_available, mock_find_drivers):
        """
        Test automatic driver allocation.
        """
        mock_find_drivers.return_value = [{
            'driver': self.driver,
            'score': 0.8,
            'distance_km': 5.0
        }]
        mock_is_available.return_value = True
        
        success, message, driver = DriverAllocator.allocate_driver_automatically(self.ride)
        
        self.assertTrue(success)
        self.assertEqual(driver, self.driver)
        
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.driver, self.driver)
        self.assertEqual(self.ride.status, Ride.RideStatus.DRIVER_ASSIGNED)
    
    def test_handle_driver_acceptance(self):
        """
        Test handling driver acceptance of ride request.
        """
        with patch.object(DriverAllocator, '_is_driver_available', return_value=True):
            success, message = DriverAllocator.handle_driver_response(
                self.ride, self.driver, 'accept'
            )
        
        self.assertTrue(success)
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.driver, self.driver)
        self.assertEqual(self.ride.status, Ride.RideStatus.DRIVER_ASSIGNED)


class RouteOptimizerTest(TestCase):
    """
    Test cases for RouteOptimizer service.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.rider1 = User.objects.create_user(
            email='rider1@test.com',
            phone_number='+2348012345678',
            first_name='Test',
            last_name='Rider1'
        )
        
        self.rider2 = User.objects.create_user(
            email='rider2@test.com',
            phone_number='+2348012345679',
            first_name='Test',
            last_name='Rider2'
        )
        
        self.driver = User.objects.create_user(
            email='driver@test.com',
            phone_number='+2348012345680',
            first_name='Test',
            last_name='Driver',
            is_driver=True
        )
        
        self.ride1 = Ride.objects.create(
            rider=self.rider1,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00')
        )
        
        self.ride2 = Ride.objects.create(
            rider=self.rider2,
            pickup_location='Lekki, Lagos',
            dropoff_location='Surulere, Lagos',
            pickup_latitude=Decimal('6.4698'),
            pickup_longitude=Decimal('3.5852'),
            dropoff_latitude=Decimal('6.4969'),
            dropoff_longitude=Decimal('3.3529'),
            estimated_fare=Decimal('1200.00')
        )
    
    @patch('apps.rides.services.route_optimizer.RouteOptimizer._get_driver_location')
    def test_optimize_driver_route(self, mock_get_location):
        """
        Test route optimization for multiple rides.
        """
        mock_get_location.return_value = (6.4500, 3.4000)  # Mock driver location
        
        available_rides = [self.ride1, self.ride2]
        
        optimized_route = RouteOptimizer.optimize_driver_route(
            str(self.driver.id), available_rides
        )
        
        self.assertIsNotNone(optimized_route)
        self.assertGreater(len(optimized_route.points), 0)
        self.assertGreater(optimized_route.total_distance_km, 0)
        self.assertGreater(optimized_route.total_duration_minutes, 0)
    
    def test_suggest_ride_sequence(self):
        """
        Test ride sequence suggestion.
        """
        rides = [self.ride1, self.ride2]
        
        with patch.object(RouteOptimizer, '_get_driver_location', return_value=(6.4500, 3.4000)):
            suggestions = RouteOptimizer.suggest_ride_sequence(str(self.driver.id), rides)
        
        self.assertEqual(len(suggestions), 2)
        
        for suggestion in suggestions:
            self.assertIn('ride', suggestion)
            self.assertIn('priority', suggestion)
            self.assertIn('estimated_pickup_time', suggestion)
            self.assertIn('efficiency_rating', suggestion)
    
    def test_calculate_route_efficiency(self):
        """
        Test route efficiency calculation.
        """
        from apps.rides.services.route_optimizer import RoutePoint
        
        route_points = [
            RoutePoint(6.4281, 3.4219, 'Pickup 1', 'pickup', str(self.ride1.id)),
            RoutePoint(6.6018, 3.3515, 'Dropoff 1', 'dropoff', str(self.ride1.id)),
        ]
        
        start_location = (6.4500, 3.4000)
        
        efficiency = RouteOptimizer.calculate_route_efficiency(route_points, start_location)
        
        self.assertIsInstance(efficiency, float)
        self.assertGreaterEqual(efficiency, 0.0)
        self.assertLessEqual(efficiency, 1.0)
