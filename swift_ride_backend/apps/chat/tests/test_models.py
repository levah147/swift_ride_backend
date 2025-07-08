"""
Tests for chat models.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.chat.models import ChatRoom, Message, MessageStatus, ChatSettings
from apps.rides.models import Ride

User = get_user_model()


class ChatRoomModelTest(TestCase):
    """Test ChatRoom model."""
    
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
    
    def test_create_chat_room(self):
        """Test creating a chat room."""
        chat_room = ChatRoom.objects.create(
            room_id='test_room_123',
            rider=self.rider,
            driver=self.driver,
            room_type=ChatRoom.RoomType.RIDE_CHAT
        )
        
        self.assertEqual(chat_room.room_id, 'test_room_123')
        self.assertEqual(chat_room.rider, self.rider)
        self.assertEqual(chat_room.driver, self.driver)
        self.assertEqual(chat_room.status, ChatRoom.RoomStatus.ACTIVE)
        self.assertIn(self.rider, chat_room.participants)
        self.assertIn(self.driver, chat_room.participants)
    
    def test_chat_room_str(self):
        """Test chat room string representation."""
        chat_room = ChatRoom.objects.create(
            room_id='test_room_123',
            rider=self.rider,
            driver=self.driver
        )
        
        expected_str = f"Chat: {self.rider.email} - {self.driver.email}"
        self.assertEqual(str(chat_room), expected_str)
    
    def test_participants_property(self):
        """Test participants property."""
        chat_room = ChatRoom.objects.create(
            room_id='test_room_123',
            rider=self.rider,
            driver=self.driver
        )
        
        participants = chat_room.participants
        self.assertEqual(len(participants), 2)
        self.assertIn(self.rider, participants)
        self.assertIn(self.driver, participants)
    
    def test_unique_room_id(self):
        """Test room_id uniqueness."""
        ChatRoom.objects.create(
            room_id='test_room_123',
            rider=self.rider,
            driver=self.driver
        )
        
        with self.assertRaises(Exception):
            ChatRoom.objects.create(
                room_id='test_room_123',
                rider=self.driver,
                driver=self.rider
            )


class MessageModelTest(TestCase):
    """Test Message model."""
    
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
    
    def test_create_text_message(self):
        """Test creating a text message."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertEqual(message.content, 'Hello, driver!')
        self.assertEqual(message.sender, self.rider)
        self.assertEqual(message.message_type, Message.MessageType.TEXT)
        self.assertEqual(message.status, Message.MessageStatus.SENT)
        self.assertFalse(message.is_read)
        self.assertFalse(message.is_deleted)
    
    def test_message_str(self):
        """Test message string representation."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        expected_str = f"Message from {self.rider.email}: Hello, driver!"
        self.assertEqual(str(message), expected_str)
    
    def test_recipient_property(self):
        """Test recipient property."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertEqual(message.recipient, self.driver)
        
        # Test with driver as sender
        message2 = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='Hello, rider!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertEqual(message2.recipient, self.rider)
    
    def test_mark_as_read(self):
        """Test marking message as read."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertFalse(message.is_read)
        self.assertIsNone(message.read_at)
        
        message.mark_as_read()
        
        self.assertTrue(message.is_read)
        self.assertIsNotNone(message.read_at)
        self.assertEqual(message.status, Message.MessageStatus.READ)
    
    def test_soft_delete(self):
        """Test soft delete functionality."""
        message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertFalse(message.is_deleted)
        self.assertIsNone(message.deleted_at)
        
        message.soft_delete()
        
        self.assertTrue(message.is_deleted)
        self.assertIsNotNone(message.deleted_at)


class MessageStatusModelTest(TestCase):
    """Test MessageStatus model."""
    
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
        self.message = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
    
    def test_create_message_status(self):
        """Test creating message status."""
        status = MessageStatus.objects.create(
            message=self.message,
            user=self.driver,
            status=MessageStatus.Status.DELIVERED
        )
        
        self.assertEqual(status.message, self.message)
        self.assertEqual(status.user, self.driver)
        self.assertEqual(status.status, MessageStatus.Status.DELIVERED)
        self.assertIsNotNone(status.timestamp)
    
    def test_message_status_str(self):
        """Test message status string representation."""
        status = MessageStatus.objects.create(
            message=self.message,
            user=self.driver,
            status=MessageStatus.Status.READ
        )
        
        expected_str = f"Message {self.message.id} - {self.driver.email}: READ"
        self.assertEqual(str(status), expected_str)


class ChatSettingsModelTest(TestCase):
    """Test ChatSettings model."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123'
        )
    
    def test_create_chat_settings(self):
        """Test creating chat settings."""
        settings = ChatSettings.objects.create(
            user=self.user,
            message_notifications=False,
            voice_message_notifications=True
        )
        
        self.assertEqual(settings.user, self.user)
        self.assertFalse(settings.message_notifications)
        self.assertTrue(settings.voice_message_notifications)
        self.assertTrue(settings.read_receipts)  # Default value
    
    def test_chat_settings_str(self):
        """Test chat settings string representation."""
        settings = ChatSettings.objects.create(user=self.user)
        
        expected_str = f"Chat settings for {self.user.email}"
        self.assertEqual(str(settings), expected_str)
    
    def test_unique_user_settings(self):
        """Test that each user can have only one settings record."""
        ChatSettings.objects.create(user=self.user)
        
        with self.assertRaises(Exception):
            ChatSettings.objects.create(user=self.user)
