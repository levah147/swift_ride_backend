"""
Tests for rides app serializers.
"""

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from apps.users.models import User
from apps.rides.models import Ride, BargainOffer
from apps.rides.serializers import (
    RideSerializer, RideCreateSerializer, BargainOfferSerializer
)


class RideSerializerTest(TestCase):
    """
    Test cases for RideSerializer.
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
            distance_km=Decimal('15.5'),
            duration_minutes=45
        )
    
    def test_serialize_ride(self):
        """
        Test serializing a ride.
        """
        serializer = RideSerializer(self.ride)
        data = serializer.data
        
        self.assertEqual(data['id'], str(self.ride.id))
        self.assertEqual(data['pickup_location'], 'Victoria Island, Lagos')
        self.assertEqual(data['dropoff_location'], 'Ikeja, Lagos')
        self.assertEqual(data['estimated_fare'], '1500.00')
        self.assertEqual(data['status'], Ride.RideStatus.REQUESTED)
        
        # Check nested rider data
        self.assertEqual(data['rider']['id'], str(self.rider.id))
        self.assertEqual(data['rider']['first_name'], 'Test')
        
        # Check nested driver data
        self.assertEqual(data['driver']['id'], str(self.driver.id))
        self.assertEqual(data['driver']['first_name'], 'Test')
    
    def test_serialize_ride_without_driver(self):
        """
        Test serializing a ride without assigned driver.
        """
        ride_without_driver = Ride.objects.create(
            rider=self.rider,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00')
        )
        
        serializer = RideSerializer(ride_without_driver)
        data = serializer.data
        
        self.assertIsNone(data['driver'])


class RideCreateSerializerTest(TestCase):
    """
    Test cases for RideCreateSerializer.
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
        
        self.valid_data = {
            'pickup_location': 'Victoria Island, Lagos',
            'dropoff_location': 'Ikeja, Lagos',
            'pickup_latitude': '6.4281',
            'pickup_longitude': '3.4219',
            'dropoff_latitude': '6.6018',
            'dropoff_longitude': '3.3515',
            'payment_method': 'cash'
        }
    
    def test_create_ride_valid_data(self):
        """
        Test creating a ride with valid data.
        """
        serializer = RideCreateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        
        ride = serializer.save(rider=self.rider)
        
        self.assertEqual(ride.rider, self.rider)
        self.assertEqual(ride.pickup_location, 'Victoria Island, Lagos')
        self.assertEqual(ride.dropoff_location, 'Ikeja, Lagos')
        self.assertEqual(ride.payment_method, 'cash')
        self.assertIsNotNone(ride.estimated_fare)
        self.assertIsNotNone(ride.distance_km)
    
    def test_create_ride_invalid_coordinates(self):
        """
        Test creating a ride with invalid coordinates.
        """
        invalid_data = self.valid_data.copy()
        invalid_data['pickup_latitude'] = '95.0'  # Invalid latitude
        
        serializer = RideCreateSerializer(data=invalid_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('pickup_latitude', serializer.errors)
    
    def test_create_ride_missing_required_fields(self):
        """
        Test creating a ride with missing required fields.
        """
        incomplete_data = {
            'pickup_location': 'Victoria Island, Lagos',
            # Missing other required fields
        }
        
        serializer = RideCreateSerializer(data=incomplete_data)
        self.assertFalse(serializer.is_valid())
        
        required_fields = [
            'dropoff_location', 'pickup_latitude', 'pickup_longitude',
            'dropoff_latitude', 'dropoff_longitude'
        ]
        
        for field in required_fields:
            self.assertIn(field, serializer.errors)
    
    def test_create_scheduled_ride(self):
        """
        Test creating a scheduled ride.
        """
        scheduled_data = self.valid_data.copy()
        scheduled_data.update({
            'is_scheduled': True,
            'schedule_time': (timezone.now() + timezone.timedelta(hours=2)).isoformat()
        })
        
        serializer = RideCreateSerializer(data=scheduled_data)
        self.assertTrue(serializer.is_valid())
        
        ride = serializer.save(rider=self.rider)
        
        self.assertTrue(ride.is_scheduled)
        self.assertIsNotNone(ride.schedule_time)


class BargainOfferSerializerTest(TestCase):
    """
    Test cases for BargainOfferSerializer.
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
        
        self.offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timezone.timedelta(minutes=10)
        )
    
    def test_serialize_bargain_offer(self):
        """
        Test serializing a bargain offer.
        """
        serializer = BargainOfferSerializer(self.offer)
        data = serializer.data
        
        self.assertEqual(data['id'], str(self.offer.id))
        self.assertEqual(data['amount'], '1200.00')
        self.assertEqual(data['offer_type'], BargainOffer.OfferType.RIDER)
        self.assertEqual(data['status'], BargainOffer.OfferStatus.PENDING)
        
        # Check nested data
        self.assertEqual(data['ride']['id'], str(self.ride.id))
        self.assertEqual(data['offered_by']['id'], str(self.rider.id))
    
    def test_create_bargain_offer_valid_data(self):
        """
        Test creating a bargain offer with valid data.
        """
        offer_data = {
            'ride': str(self.ride.id),
            'amount': '1300.00',
            'offer_type': BargainOffer.OfferType.DRIVER,
            'notes': 'Counter offer'
        }
        
        serializer = BargainOfferSerializer(data=offer_data)
        self.assertTrue(serializer.is_valid())
        
        offer = serializer.save(offered_by=self.driver)
        
        self.assertEqual(offer.ride, self.ride)
        self.assertEqual(offer.offered_by, self.driver)
        self.assertEqual(offer.amount, Decimal('1300.00'))
        self.assertEqual(offer.offer_type, BargainOffer.OfferType.DRIVER)
    
    def test_create_bargain_offer_invalid_amount(self):
        """
        Test creating a bargain offer with invalid amount.
        """
        offer_data = {
            'ride': str(self.ride.id),
            'amount': '-100.00',  # Negative amount
            'offer_type': BargainOffer.OfferType.RIDER
        }
        
        serializer = BargainOfferSerializer(data=offer_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
    
    def test_create_bargain_offer_missing_ride(self):
        """
        Test creating a bargain offer without specifying ride.
        """
        offer_data = {
            'amount': '1300.00',
            'offer_type': BargainOffer.OfferType.RIDER
            # Missing ride field
        }
        
        serializer = BargainOfferSerializer(data=offer_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('ride', serializer.errors)
