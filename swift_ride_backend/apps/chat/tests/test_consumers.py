"""
Tests for chat WebSocket consumers.
"""

import json
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.chat.consumers import ChatConsumer
from apps.chat.models import ChatRoom, Message

User = get_user_model()


class ChatConsumerTest(TestCase):
    """Test ChatConsumer WebSocket functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.rider = User.objects.create_user(
            email='rider@test.com',
            password='testpass123'
        )
        self.driver = User.objects.create_user(
            email='driver@test.com',
            password='testpass123'
        )
        
        self.chat_room = ChatRoom.objects.create(
            room_id='test_room_123',
            rider=self.rider,
            driver=self.driver
        )
    
    async def test_chat_consumer_connect(self):
        """Test WebSocket connection."""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.chat_room.room_id}/"
        )
        
        # Mock authentication
        communicator.scope["user"] = self.rider
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        await communicator.disconnect()
    
    async def test_chat_consumer_send_message(self):
        """Test sending message through WebSocket."""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.chat_room.room_id}/"
        )
        
        # Mock authentication
        communicator.scope["user"] = self.rider
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Send message
        message_data = {
            'type': 'chat_message',
            'message': 'Hello, driver!',
            'message_type': 'text'
        }
        
        await communicator.send_json_to(message_data)
        
        # Receive message
        response = await communicator.receive_json_from()
        
        self.assertEqual(response['type'], 'chat_message')
        self.assertEqual(response['message'], 'Hello, driver!')
        
        await communicator.disconnect()
    
    async def test_chat_consumer_unauthorized_access(self):
        """Test unauthorized access to chat room."""
        other_user = await database_sync_to_async(User.objects.create_user)(
            email='other@test.com',
            password='testpass123'
        )
        
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.chat_room.room_id}/"
        )
        
        # Mock authentication with unauthorized user
        communicator.scope["user"] = other_user
        
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)
    
    async def test_chat_consumer_typing_indicator(self):
        """Test typing indicator functionality."""
        communicator = WebsocketCommunicator(
            ChatConsumer.as_asgi(),
            f"/ws/chat/{self.chat_room.room_id}/"
        )
        
        # Mock authentication
        communicator.scope["user"] = self.rider
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Send typing indicator
        typing_data = {
            'type': 'typing_indicator',
            'is_typing': True
        }
        
        await communicator.send_json_to(typing_data)
        
        # Should receive typing indicator
        response = await communicator.receive_json_from()
        
        self.assertEqual(response['type'], 'typing_indicator')
        self.assertTrue(response['is_typing'])
        
        await communicator.disconnect()
