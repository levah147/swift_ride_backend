"""
Tests for chat services.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.chat.models import ChatRoom, Message
from apps.chat.services.chat_service import ChatService
from apps.chat.services.message_handler import MessageHandler
from apps.chat.services.file_handler import FileHandler

User = get_user_model()


class ChatServiceTest(TestCase):
    """Test ChatService."""
    
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
        chat_room = ChatService.create_chat_room(
            rider=self.rider,
            driver=self.driver,
            room_type=ChatRoom.RoomType.RIDE_CHAT
        )
        
        self.assertIsNotNone(chat_room)
        self.assertEqual(chat_room.rider, self.rider)
        self.assertEqual(chat_room.driver, self.driver)
        self.assertEqual(chat_room.room_type, ChatRoom.RoomType.RIDE_CHAT)
    
    def test_get_or_create_chat_room(self):
        """Test getting or creating a chat room."""
        # First call should create
        chat_room1 = ChatService.get_or_create_chat_room(
            rider=self.rider,
            driver=self.driver
        )
        
        # Second call should return existing
        chat_room2 = ChatService.get_or_create_chat_room(
            rider=self.rider,
            driver=self.driver
        )
        
        self.assertEqual(chat_room1.id, chat_room2.id)
    
    def test_send_message(self):
        """Test sending a message."""
        chat_room = ChatService.create_chat_room(
            rider=self.rider,
            driver=self.driver
        )
        
        message = ChatService.send_message(
            chat_room=chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertIsNotNone(message)
        self.assertEqual(message.content, 'Hello, driver!')
        self.assertEqual(message.sender, self.rider)


class MessageHandlerTest(TestCase):
    """Test MessageHandler."""
    
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
    
    def test_process_incoming_message(self):
        """Test processing incoming message."""
        message = MessageHandler.process_incoming_message(
            chat_room=self.chat_room,
            sender=self.rider,
            content='Hello, driver!',
            message_type=Message.MessageType.TEXT
        )
        
        self.assertIsNotNone(message)
        self.assertEqual(message.content, 'Hello, driver!')
        self.assertEqual(message.sender, self.rider)
    
    def test_mark_messages_as_read(self):
        """Test marking messages as read."""
        # Create some messages
        message1 = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='Hello, rider!',
            message_type=Message.MessageType.TEXT
        )
        message2 = Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='How are you?',
            message_type=Message.MessageType.TEXT
        )
        
        # Mark as read
        count = MessageHandler.mark_messages_as_read(
            chat_room=self.chat_room,
            user=self.rider
        )
        
        self.assertEqual(count, 2)
        
        # Check messages are marked as read
        message1.refresh_from_db()
        message2.refresh_from_db()
        
        self.assertTrue(message1.is_read)
        self.assertTrue(message2.is_read)
    
    def test_get_unread_count(self):
        """Test getting unread message count."""
        # Create some messages
        Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='Hello, rider!',
            message_type=Message.MessageType.TEXT
        )
        Message.objects.create(
            chat_room=self.chat_room,
            sender=self.driver,
            content='How are you?',
            message_type=Message.MessageType.TEXT
        )
        
        count = MessageHandler.get_unread_count(
            chat_room=self.chat_room,
            user=self.rider
        )
        
        self.assertEqual(count, 2)


class FileHandlerTest(TestCase):
    """Test FileHandler."""
    
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
            content='',
            message_type=Message.MessageType.FILE
        )
    
    def test_validate_file_upload(self):
        """Test file upload validation."""
        # Create a test file
        test_file = SimpleUploadedFile(
            "test.txt",
            b"file_content",
            content_type="text/plain"
        )
        
        is_valid, message = FileHandler.validate_file_upload(
            file=test_file,
            user=self.rider
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(message, "File upload allowed")
    
    def test_validate_large_file_upload(self):
        """Test validation of large file upload."""
        # Create a large test file (simulate)
        large_content = b"x" * (100 * 1024 * 1024)  # 100MB
        test_file = SimpleUploadedFile(
            "large_test.txt",
            large_content,
            content_type="text/plain"
        )
        
        is_valid, message = FileHandler.validate_file_upload(
            file=test_file,
            user=self.rider
        )
        
        self.assertFalse(is_valid)
        self.assertIn("size exceeds", message)
