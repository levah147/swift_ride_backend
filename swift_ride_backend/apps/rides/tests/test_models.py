"""
Tests for rides app models.
"""

from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.users.models import User
from apps.rides.models import Ride, BargainOffer, RideHistory, TripStatus


class RideModelTest(TestCase):
    """
    Test cases for Ride model.
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
        
        self.ride_data = {
            'rider': self.rider,
            'pickup_location': 'Victoria Island, Lagos',
            'dropoff_location': 'Ikeja, Lagos',
            'pickup_latitude': Decimal('6.4281'),
            'pickup_longitude': Decimal('3.4219'),
            'dropoff_latitude': Decimal('6.6018'),
            'dropoff_longitude': Decimal('3.3515'),
            'estimated_fare': Decimal('1500.00'),
            'distance_km': Decimal('15.5'),
            'duration_minutes': 45
        }
    
    def test_create_ride(self):
        """
        Test creating a new ride.
        """
        ride = Ride.objects.create(**self.ride_data)
        
        self.assertEqual(ride.rider, self.rider)
        self.assertEqual(ride.status, Ride.RideStatus.REQUESTED)
        self.assertEqual(ride.pickup_location, 'Victoria Island, Lagos')
        self.assertEqual(ride.estimated_fare, Decimal('1500.00'))
        self.assertIsNotNone(ride.id)
        self.assertIsNotNone(ride.created_at)
    
    def test_ride_str_representation(self):
        """
        Test string representation of ride.
        """
        ride = Ride.objects.create(**self.ride_data)
        expected_str = f"Ride {ride.id} - {self.rider.get_full_name()}"
        self.assertEqual(str(ride), expected_str)
    
    def test_ride_status_transitions(self):
        """
        Test valid ride status transitions.
        """
        ride = Ride.objects.create(**self.ride_data)
        
        # Test valid transitions
        ride.status = Ride.RideStatus.SEARCHING
        ride.save()
        self.assertEqual(ride.status, Ride.RideStatus.SEARCHING)
        
        ride.status = Ride.RideStatus.DRIVER_ASSIGNED
        ride.driver = self.driver
        ride.save()
        self.assertEqual(ride.status, Ride.RideStatus.DRIVER_ASSIGNED)
    
    def test_can_cancel_property(self):
        """
        Test can_cancel property.
        """
        ride = Ride.objects.create(**self.ride_data)
        
        # Can cancel when requested or searching
        self.assertTrue(ride.can_cancel)
        
        ride.status = Ride.RideStatus.SEARCHING
        self.assertTrue(ride.can_cancel)
        
        # Cannot cancel when in progress
        ride.status = Ride.RideStatus.IN_PROGRESS
        self.assertFalse(ride.can_cancel)
        
        # Cannot cancel when completed
        ride.status = Ride.RideStatus.COMPLETED
        self.assertFalse(ride.can_cancel)
    
    def test_is_active_property(self):
        """
        Test is_active property.
        """
        ride = Ride.objects.create(**self.ride_data)
        
        # Active statuses
        active_statuses = [
            Ride.RideStatus.REQUESTED,
            Ride.RideStatus.SEARCHING,
            Ride.RideStatus.BARGAINING,
            Ride.RideStatus.ACCEPTED,
            Ride.RideStatus.DRIVER_ASSIGNED,
            Ride.RideStatus.DRIVER_ARRIVED,
            Ride.RideStatus.IN_PROGRESS
        ]
        
        for status in active_statuses:
            ride.status = status
            self.assertTrue(ride.is_active)
        
        # Inactive statuses
        inactive_statuses = [
            Ride.RideStatus.COMPLETED,
            Ride.RideStatus.CANCELLED
        ]
        
        for status in inactive_statuses:
            ride.status = status
            self.assertFalse(ride.is_active)
    
    def test_coordinate_validation(self):
        """
        Test coordinate validation.
        """
        # Test invalid latitude
        invalid_data = self.ride_data.copy()
        invalid_data['pickup_latitude'] = Decimal('95.0')  # Invalid latitude
        
        with self.assertRaises(ValidationError):
            ride = Ride(**invalid_data)
            ride.full_clean()
        
        # Test invalid longitude
        invalid_data = self.ride_data.copy()
        invalid_data['pickup_longitude'] = Decimal('185.0')  # Invalid longitude
        
        with self.assertRaises(ValidationError):
            ride = Ride(**invalid_data)
            ride.full_clean()
    
    def test_fare_validation(self):
        """
        Test fare validation.
        """
        # Test negative fare
        invalid_data = self.ride_data.copy()
        invalid_data['estimated_fare'] = Decimal('-100.00')
        
        with self.assertRaises(ValidationError):
            ride = Ride(**invalid_data)
            ride.full_clean()
    
    def test_scheduled_ride(self):
        """
        Test scheduled ride functionality.
        """
        schedule_time = timezone.now() + timedelta(hours=2)
        
        ride_data = self.ride_data.copy()
        ride_data.update({
            'is_scheduled': True,
            'schedule_time': schedule_time
        })
        
        ride = Ride.objects.create(**ride_data)
        
        self.assertTrue(ride.is_scheduled)
        self.assertEqual(ride.schedule_time, schedule_time)


class BargainOfferModelTest(TestCase):
    """
    Test cases for BargainOffer model.
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
            status=Ride.RideStatus.BARGAINING
        )
    
    def test_create_bargain_offer(self):
        """
        Test creating a bargain offer.
        """
        offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        self.assertEqual(offer.ride, self.ride)
        self.assertEqual(offer.offered_by, self.rider)
        self.assertEqual(offer.amount, Decimal('1200.00'))
        self.assertEqual(offer.status, BargainOffer.OfferStatus.PENDING)
    
    def test_offer_expiry(self):
        """
        Test offer expiry functionality.
        """
        # Create expired offer
        expired_offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() - timedelta(minutes=5)
        )
        
        self.assertTrue(expired_offer.is_expired)
        
        # Create non-expired offer
        active_offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.driver,
            amount=Decimal('1300.00'),
            offer_type=BargainOffer.OfferType.DRIVER,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        self.assertFalse(active_offer.is_expired)
    
    def test_counter_offer(self):
        """
        Test counter offer functionality.
        """
        # Create original offer
        original_offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        # Create counter offer
        counter_offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.driver,
            amount=Decimal('1400.00'),
            offer_type=BargainOffer.OfferType.DRIVER,
            counter_offer=original_offer,
            expiry_time=timezone.now() + timedelta(minutes=10)
        )
        
        self.assertEqual(counter_offer.counter_offer, original_offer)
        self.assertTrue(counter_offer.is_counter_offer)
        self.assertFalse(original_offer.is_counter_offer)


class RideHistoryModelTest(TestCase):
    """
    Test cases for RideHistory model.
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
        
        self.ride = Ride.objects.create(
            rider=self.rider,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00')
        )
    
    def test_create_history_entry(self):
        """
        Test creating a history entry.
        """
        history = RideHistory.objects.create(
            ride=self.ride,
            event_type=RideHistory.EventType.STATUS_CHANGE,
            previous_status=Ride.RideStatus.REQUESTED,
            new_status=Ride.RideStatus.SEARCHING,
            description='Ride status changed to searching'
        )
        
        self.assertEqual(history.ride, self.ride)
        self.assertEqual(history.event_type, RideHistory.EventType.STATUS_CHANGE)
        self.assertEqual(history.previous_status, Ride.RideStatus.REQUESTED)
        self.assertEqual(history.new_status, Ride.RideStatus.SEARCHING)
    
    def test_history_with_location(self):
        """
        Test history entry with location data.
        """
        history = RideHistory.objects.create(
            ride=self.ride,
            event_type=RideHistory.EventType.LOCATION_UPDATE,
            description='Driver location updated',
            latitude=Decimal('6.4500'),
            longitude=Decimal('3.4000')
        )
        
        self.assertEqual(history.latitude, Decimal('6.4500'))
        self.assertEqual(history.longitude, Decimal('3.4000'))
    
    def test_history_with_metadata(self):
        """
        Test history entry with metadata.
        """
        metadata = {
            'driver_id': 'test-driver-id',
            'distance_km': 5.2,
            'speed_kmh': 35
        }
        
        history = RideHistory.objects.create(
            ride=self.ride,
            event_type=RideHistory.EventType.SYSTEM,
            description='System event',
            metadata=metadata
        )
        
        self.assertEqual(history.metadata, metadata)


class TripStatusModelTest(TestCase):
    """
    Test cases for TripStatus model.
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
            driver=self.driver,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00'),
            status=Ride.RideStatus.DRIVER_ASSIGNED
        )
    
    def test_create_trip_status(self):
        """
        Test creating trip status.
        """
        trip_status = TripStatus.objects.create(
            ride=self.ride,
            distance_to_pickup=Decimal('2.5'),
            is_tracking_active=True
        )
        
        self.assertEqual(trip_status.ride, self.ride)
        self.assertEqual(trip_status.distance_to_pickup, Decimal('2.5'))
        self.assertTrue(trip_status.is_tracking_active)
    
    def test_trip_status_updates(self):
        """
        Test updating trip status.
        """
        trip_status = TripStatus.objects.create(
            ride=self.ride,
            distance_to_pickup=Decimal('2.5'),
            is_tracking_active=True
        )
        
        # Update distance
        trip_status.distance_to_pickup = Decimal('1.2')
        trip_status.is_driver_moving = True
        trip_status.save()
        
        self.assertEqual(trip_status.distance_to_pickup, Decimal('1.2'))
        self.assertTrue(trip_status.is_driver_moving)
    
    def test_one_to_one_relationship(self):
        """
        Test one-to-one relationship with Ride.
        """
        trip_status = TripStatus.objects.create(
            ride=self.ride,
            is_tracking_active=True
        )
        
        # Access trip status from ride
        self.assertEqual(self.ride.trip_status, trip_status)
        
        # Cannot create another trip status for the same ride
        with self.assertRaises(Exception):
            TripStatus.objects.create(
                ride=self.ride,
                is_tracking_active=True
            )
