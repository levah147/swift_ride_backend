"""
Tests for rides app views.
"""

import json
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status

from apps.users.models import User
from apps.rides.models import Ride, BargainOffer


class RideViewSetTest(APITestCase):
    """
    Test cases for RideViewSet.
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
            'pickup_location': 'Victoria Island, Lagos',
            'dropoff_location': 'Ikeja, Lagos',
            'pickup_latitude': '6.4281',
            'pickup_longitude': '3.4219',
            'dropoff_latitude': '6.6018',
            'dropoff_longitude': '3.3515',
            'payment_method': 'cash'
        }
    
    def test_create_ride_authenticated(self):
        """
        Test creating a ride as authenticated user.
        """
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.post(
            reverse('ride-list'),
            data=self.ride_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ride.objects.count(), 1)
        
        ride = Ride.objects.first()
        self.assertEqual(ride.rider, self.rider)
        self.assertEqual(ride.pickup_location, 'Victoria Island, Lagos')
        self.assertEqual(ride.status, Ride.RideStatus.REQUESTED)
    
    def test_create_ride_unauthenticated(self):
        """
        Test creating a ride without authentication.
        """
        response = self.client.post(
            reverse('ride-list'),
            data=self.ride_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Ride.objects.count(), 0)
    
    def test_list_rides_for_rider(self):
        """
        Test listing rides for a rider.
        """
        # Create rides
        ride1 = Ride.objects.create(
            rider=self.rider,
            pickup_location='Location 1',
            dropoff_location='Location 2',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1000.00')
        )
        
        ride2 = Ride.objects.create(
            rider=self.driver,  # Different rider
            pickup_location='Location 3',
            dropoff_location='Location 4',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1200.00')
        )
        
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.get(reverse('ride-list'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(ride1.id))
    
    def test_retrieve_ride_owner(self):
        """
        Test retrieving a ride as the owner.
        """
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00')
        )
        
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.get(
            reverse('ride-detail', kwargs={'pk': ride.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(ride.id))
    
    def test_retrieve_ride_unauthorized(self):
        """
        Test retrieving a ride without permission.
        """
        ride = Ride.objects.create(
            rider=self.rider,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00')
        )
        
        # Create another user
        other_user = User.objects.create_user(
            email='other@test.com',
            phone_number='+2348012345680',
            first_name='Other',
            last_name='User'
        )
        
        self.client.force_authenticate(user=other_user)
        
        response = self.client.get(
            reverse('ride-detail', kwargs={'pk': ride.id})
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_cancel_ride(self):
        """
        Test cancelling a ride.
        """
        ride = Ride.objects.create(
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
        
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.post(
            reverse('ride-cancel', kwargs={'pk': ride.id}),
            data={'reason': 'Changed my mind'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ride.refresh_from_db()
        self.assertEqual(ride.status, Ride.RideStatus.CANCELLED)
    
    def test_rate_ride(self):
        """
        Test rating a completed ride.
        """
        ride = Ride.objects.create(
            rider=self.rider,
            driver=self.driver,
            pickup_location='Victoria Island, Lagos',
            dropoff_location='Ikeja, Lagos',
            pickup_latitude=Decimal('6.4281'),
            pickup_longitude=Decimal('3.4219'),
            dropoff_latitude=Decimal('6.6018'),
            dropoff_longitude=Decimal('3.3515'),
            estimated_fare=Decimal('1500.00'),
            status=Ride.RideStatus.COMPLETED
        )
        
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.post(
            reverse('ride-rate', kwargs={'pk': ride.id}),
            data={
                'rating': 5,
                'comment': 'Great ride!'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        ride.refresh_from_db()
        self.assertEqual(ride.rider_rating, 5)
        self.assertEqual(ride.rider_comment, 'Great ride!')


class BargainOfferViewSetTest(APITestCase):
    """
    Test cases for BargainOfferViewSet.
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
    
    def test_make_rider_offer(self):
        """
        Test making an offer as a rider.
        """
        self.client.force_authenticate(user=self.rider)
        
        response = self.client.post(
            reverse('bargainoffer-list'),
            data={
                'ride': str(self.ride.id),
                'amount': '1200.00',
                'offer_type': 'rider',
                'notes': 'Please accept this offer'
            },
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(BargainOffer.objects.count(), 1)
        
        offer = BargainOffer.objects.first()
        self.assertEqual(offer.offered_by, self.rider)
        self.assertEqual(offer.amount, Decimal('1200.00'))
        self.assertEqual(offer.offer_type, BargainOffer.OfferType.RIDER)
    
    def test_accept_offer(self):
        """
        Test accepting a bargain offer.
        """
        # Create offer by rider
        offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timezone.timedelta(minutes=10)
        )
        
        self.client.force_authenticate(user=self.driver)
        
        response = self.client.post(
            reverse('bargainoffer-accept', kwargs={'pk': offer.id}),
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        offer.refresh_from_db()
        self.assertEqual(offer.status, BargainOffer.OfferStatus.ACCEPTED)
        
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.RideStatus.DRIVER_ASSIGNED)
        self.assertEqual(self.ride.driver, self.driver)
    
    def test_reject_offer(self):
        """
        Test rejecting a bargain offer.
        """
        # Create offer by rider
        offer = BargainOffer.objects.create(
            ride=self.ride,
            offered_by=self.rider,
            amount=Decimal('1200.00'),
            offer_type=BargainOffer.OfferType.RIDER,
            expiry_time=timezone.now() + timezone.timedelta(minutes=10)
        )
        
        self.client.force_authenticate(user=self.driver)
        
        response = self.client.post(
            reverse('bargainoffer-reject', kwargs={'pk': offer.id}),
            data={'reason': 'Amount too low'},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        offer.refresh_from_db()
        self.assertEqual(offer.status, BargainOffer.OfferStatus.REJECTED)
        self.assertEqual(offer.rejection_reason, 'Amount too low')


class DriverRideViewsTest(APITestCase):
    """
    Test cases for driver-specific ride views.
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
    
    def test_available_rides_for_driver(self):
        """
        Test getting available rides for a driver.
        """
        self.client.force_authenticate(user=self.driver)
        
        response = self.client.get(reverse('available-rides'))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], str(self.ride.id))
    
    def test_accept_ride_request(self):
        """
        Test driver accepting a ride request.
        """
        self.client.force_authenticate(user=self.driver)
        
        response = self.client.post(
            reverse('ride-accept', kwargs={'pk': self.ride.id}),
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.RideStatus.DRIVER_ASSIGNED)
        self.assertEqual(self.ride.driver, self.driver)
    
    def test_update_ride_status(self):
        """
        Test driver updating ride status.
        """
        # Assign driver to ride first
        self.ride.driver = self.driver
        self.ride.status = Ride.RideStatus.DRIVER_ASSIGNED
        self.ride.save()
        
        self.client.force_authenticate(user=self.driver)
        
        response = self.client.patch(
            reverse('ride-detail', kwargs={'pk': self.ride.id}),
            data={'status': Ride.RideStatus.DRIVER_ARRIVED},
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.ride.refresh_from_db()
        self.assertEqual(self.ride.status, Ride.RideStatus.DRIVER_ARRIVED)
