"""
Tests for rides app WebSocket consumers.
"""

import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model

from apps.rides.models import Ride
from apps.rides.consumers import RideConsumer, DriverLocationConsumer

User = get_user_model()


class RideConsumerTest(TransactionTestCase):
    """
    Test cases for RideConsumer.
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
            pickup_latitude='6.4281',
            pickup_longitude='3.4219',
            dropoff_latitude='6.6018',
            dropoff_longitude='3.3515',
            estimated_fare='1500.00'
        )
    
    async def test_connect_authenticated_rider(self):
        """
        Test WebSocket connection as authenticated rider.
        """
        communicator = WebsocketCommunicator(
            RideConsumer.as_asgi(),
            f"/ws/rides/{self.ride.id}/"
        )
        
        # Mock authentication
        communicator.scope["user"] = self.rider
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        await communicator.disconnect()
    
    async def test_connect_unauthenticated(self):
        """
        Test WebSocket connection without authentication.
        """
        from django.contrib.auth.models import AnonymousUser
        
        communicator = WebsocketCommunicator(
            RideConsumer.as_asgi(),
            f"/ws/rides/{self.ride.id}/"
        )
        
        # Mock anonymous user
        communicator.scope["user"] = AnonymousUser()
        
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
    
    async def test_receive_location_update(self):
        """
        Test receiving location update message.
        """
        communicator = WebsocketCommunicator(
            RideConsumer.as_asgi(),
            f"/ws/rides/{self.ride.id}/"
        )
        
        communicator.scope["user"] = self.driver
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Send location update
        await communicator.send_json_to({
            'type': 'location_update',
            'latitude': 6.4500,
            'longitude': 3.4000,
            'heading': 45.0,
            'speed': 30.0
        })
        
        # Should receive acknowledgment
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'location_update_ack')
        
        await communicator.disconnect()
    
    async def test_receive_status_update(self):
        """
        Test receiving ride status update.
        """
        # Assign driver to ride
        await database_sync_to_async(self._assign_driver_to_ride)()
        
        communicator = WebsocketCommunicator(
            RideConsumer.as_asgi(),
            f"/ws/rides/{self.ride.id}/"
        )
        
        communicator.scope["user"] = self.driver
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Send status update
        await communicator.send_json_to({
            'type': 'status_update',
            'status': 'driver_arrived'
        })
        
        # Should receive acknowledgment
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'status_update_ack')
        
        await communicator.disconnect()
    
    def _assign_driver_to_ride(self):
        """
        Helper method to assign driver to ride.
        """
        self.ride.driver = self.driver
        self.ride.status = Ride.RideStatus.DRIVER_ASSIGNED
        self.ride.save()


class DriverLocationConsumerTest(TransactionTestCase):
    """
    Test cases for DriverLocationConsumer.
    """
    
    def setUp(self):
        """
        Set up test data.
        """
        self.driver = User.objects.create_user(
            email='driver@test.com',
            phone_number='+2348012345679',
            first_name='Test',
            last_name='Driver',
            is_driver=True
        )
    
    async def test_connect_as_driver(self):
        """
        Test WebSocket connection as driver.
        """
        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(),
            "/ws/driver/location/"
        )
        
        communicator.scope["user"] = self.driver
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        await communicator.disconnect()
    
    async def test_connect_as_non_driver(self):
        """
        Test WebSocket connection as non-driver user.
        """
        rider = User.objects.create_user(
            email='rider@test.com',
            phone_number='+2348012345678',
            first_name='Test',
            last_name='Rider'
        )
        
        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(),
            "/ws/driver/location/"
        )
        
        communicator.scope["user"] = rider
        
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
    
    async def test_receive_location_update(self):
        """
        Test receiving location update from driver.
        """
        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(),
            "/ws/driver/location/"
        )
        
        communicator.scope["user"] = self.driver
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Send location update
        await communicator.send_json_to({
            'type': 'location_update',
            'latitude': 6.4500,
            'longitude': 3.4000,
            'heading': 45.0,
            'speed': 30.0,
            'accuracy': 10.0
        })
        
        # Should receive acknowledgment
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'location_update_received')
        
        await communicator.disconnect()
    
    async def test_invalid_location_data(self):
        """
        Test sending invalid location data.
        """
        communicator = WebsocketCommunicator(
            DriverLocationConsumer.as_asgi(),
            "/ws/driver/location/"
        )
        
        communicator.scope["user"] = self.driver
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Send invalid location update (missing required fields)
        await communicator.send_json_to({
            'type': 'location_update',
            'latitude': 6.4500
            # Missing longitude
        })
        
        # Should receive error
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'error')
        
        await communicator.disconnect()
