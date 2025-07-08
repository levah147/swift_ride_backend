"""
Tests for chat views.
"""

import json
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.chat.models import ChatRoom, Message

User = get_user_model()


class ChatViewsTest(TestCase):
    """Test chat views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        
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
    
    def test_chat_room_list_authenticated(self):
        """Test chat room list for authenticated user."""
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:chatroom-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['room_id'], 'test_room_123')
    
    def test_chat_room_list_unauthenticated(self):
        """Test chat room list for unauthenticated user."""
        url = reverse('chat:chatroom-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_send_message(self):
        """Test sending a message."""
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:message-list')
        data = {
            'chat_room': self.chat_room.id,
            'content': 'Hello, driver!',
            'message_type': Message.MessageType.TEXT
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Hello, driver!')
        self.assertEqual(response.data['sender'], self.rider.id)
    
    def test_get_messages(self):
        """Test getting messages for a chat room."""
        # Create some messages
        Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='Hello, rider!',
            message_type=Message.MessageType.TEXT
        )
        
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:message-list')
        response = self.client.get(url, {'chat_room': self.chat_room.id})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
    
    def test_mark_messages_as_read(self):
        """Test marking messages as read."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='Hello, rider!',
            message_type=Message.MessageType.TEXT
        )
        
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:chatroom-mark-read', kwargs={'pk': self.chat_room.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that message is marked as read
        message.refresh_from_db()
        self.assertTrue(message.is_read)
    
    def test_chat_room_detail(self):
        """Test getting chat room details."""
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:chatroom-detail', kwargs={'pk': self.chat_room.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['room_id'], 'test_room_123')
        self.assertEqual(response.data['rider'], self.rider.id)
        self.assertEqual(response.data['driver'], self.driver.id)
    
    def test_unauthorized_access_to_chat_room(self):
        """Test unauthorized access to chat room."""
        other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123'
        )
        
        self.client.force_authenticate(user=other_user)
        
        url = reverse('chat:chatroom-detail', kwargs={'pk': self.chat_room.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_delete_message(self):
        """Test deleting a message."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:message-detail', kwargs={'pk': message.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Check that message is soft deleted
        message.refresh_from_db()
        self.assertTrue(message.is_deleted)
    
    def test_cannot_delete_others_message(self):
        """Test that user cannot delete other's messages."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='Hello, rider!',
            message_type=Message.MessageType.TEXT
        )
        
        self.client.force_authenticate(user=self.rider)
        
        url = reverse('chat:message-detail', kwargs={'pk': message.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
