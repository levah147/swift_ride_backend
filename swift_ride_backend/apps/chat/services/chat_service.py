"""
Service for handling chat operations.
"""

import uuid
from django.utils import timezone
from django.db import transaction

from apps.chat.models import ChatRoom, Message, VoiceNote, FileAttachment
from apps.rides.models import Ride


class ChatService:
    """
    Service for handling chat operations.
    """
    
    @staticmethod
    def create_ride_chat_room(ride):
        """
        Create a chat room for a ride.
        """
        # Generate unique room ID
        room_id = f"ride_{ride.id}_{uuid.uuid4().hex[:8]}"
        
        chat_room = ChatRoom.objects.create(
            room_id=room_id,
            room_type=ChatRoom.RoomType.RIDE,
            rider=ride.rider,
            driver=ride.driver,
            ride=ride
        )
        
        # Send welcome message
        ChatService.send_system_message(
            chat_room,
            "Chat room created for your ride. You can now communicate with each other."
        )
        
        return chat_room
    
    @staticmethod
    def get_or_create_chat_room(rider, driver, ride=None):
        """
        Get existing chat room or create a new one.
        """
        # Try to find existing active chat room
        chat_room = ChatRoom.objects.filter(
            rider=rider,
            driver=driver,
            status=ChatRoom.RoomStatus.ACTIVE,
            ride=ride
        ).first()
        
        if not chat_room:
            # Create new chat room
            room_id = f"chat_{rider.id}_{driver.id}_{uuid.uuid4().hex[:8]}"
            
            chat_room = ChatRoom.objects.create(
                room_id=room_id,
                room_type=ChatRoom.RoomType.RIDE if ride else ChatRoom.RoomType.GENERAL,
                rider=rider,
                driver=driver,
                ride=ride
            )
        
        return chat_room
    
    @staticmethod
    def send_message(chat_room, sender, content, message_type=Message.MessageType.TEXT, **kwargs):
        """
        Send a message in a chat room.
        """
        with transaction.atomic():
            # Create message
            message = Message.objects.create(
                chat_room=chat_room,
                sender=sender,
                content=content,
                message_type=message_type,
                **kwargs
            )
            
            # Update chat room last activity
            chat_room.last_activity = timezone.now()
            chat_room.save(update_fields=['last_activity'])
            
            # Mark as delivered immediately (in real app, this would be done via WebSocket)
            message.mark_as_delivered()
            
            return message
    
    @staticmethod
    def send_voice_message(chat_room, sender, audio_file, duration_seconds):
        """
        Send a voice message.
        """
        with transaction.atomic():
            # Create message
            message = ChatService.send_message(
                chat_room,
                sender,
                "Voice message",
                Message.MessageType.VOICE
            )
            
            # Create voice note
            voice_note = VoiceNote.objects.create(
                message=message,
                audio_file=audio_file,
                duration_seconds=duration_seconds,
                file_size=audio_file.size
            )
            
            return message, voice_note
    
    @staticmethod
    def send_file_message(chat_room, sender, file, original_filename):
        """
        Send a file message.
        """
        with transaction.atomic():
            # Determine message type based on file
            file_type = ChatService._get_file_type(file)
            message_type = Message.MessageType.IMAGE if file_type.startswith('image/') else Message.MessageType.FILE
            
            # Create message
            message = ChatService.send_message(
                chat_room,
                sender,
                f"Shared a file: {original_filename}",
                message_type
            )
            
            # Create file attachment
            file_attachment = FileAttachment.objects.create(
                message=message,
                file=file,
                original_filename=original_filename,
                file_type=file_type,
                file_size=file.size
            )
            
            return message, file_attachment
    
    @staticmethod
    def send_location_message(chat_room, sender, latitude, longitude, location_name=None):
        """
        Send a location message.
        """
        message = ChatService.send_message(
            chat_room,
            sender,
            f"Shared location: {location_name or 'Current location'}",
            Message.MessageType.LOCATION,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name
        )
        
        return message
    
    @staticmethod
    def send_system_message(chat_room, content):
        """
        Send a system message.
        """
        # Use the first participant as sender for system messages
        sender = chat_room.rider
        
        message = Message.objects.create(
            chat_room=chat_room,
            sender=sender,
            content=content,
            message_type=Message.MessageType.SYSTEM,
            status=Message.MessageStatus.READ,
            is_read=True
        )
        
        return message
    
    @staticmethod
    def mark_messages_as_read(chat_room, user):
        """
        Mark all unread messages as read for a user.
        """
        # Get unread messages from other participants
        unread_messages = Message.objects.filter(
            chat_room=chat_room,
            is_read=False,
            is_deleted=False
        ).exclude(sender=user)
        
        # Mark as read
        unread_messages.update(
            is_read=True,
            read_at=timezone.now(),
            status=Message.MessageStatus.READ
        )
        
        return unread_messages.count()
    
    @staticmethod
    def get_chat_history(chat_room, user, limit=50, offset=0):
        """
        Get chat history for a user.
        """
        # Check if user is participant
        if user not in chat_room.participants:
            return Message.objects.none()
        
        messages = Message.objects.filter(
            chat_room=chat_room,
            is_deleted=False
        ).order_by('-created_at')[offset:offset + limit]
        
        return messages
    
    @staticmethod
    def delete_message(message, user):
        """
        Delete a message (soft delete).
        """
        # Check if user is the sender or admin
        if message.sender != user and not user.is_staff:
            return False, "You can only delete your own messages"
        
        # Soft delete
        message.is_deleted = True
        message.deleted_at = timezone.now()
        message.save(update_fields=['is_deleted', 'deleted_at'])
        
        return True, "Message deleted successfully"
    
    @staticmethod
    def archive_chat_room(chat_room):
        """
        Archive a chat room.
        """
        chat_room.status = ChatRoom.RoomStatus.ARCHIVED
        chat_room.save(update_fields=['status'])
        
        return chat_room
    
    @staticmethod
    def block_chat_room(chat_room, reason=None):
        """
        Block a chat room.
        """
        chat_room.status = ChatRoom.RoomStatus.BLOCKED
        chat_room.save(update_fields=['status'])
        
        # Log moderation action
        from apps.chat.models import ChatModerationLog
        ChatModerationLog.objects.create(
            chat_room=chat_room,
            action_type=ChatModerationLog.ActionType.CHAT_BLOCKED,
            reason=reason or "Chat room blocked",
            automated=True
        )
        
        return chat_room
    
    @staticmethod
    def get_user_chat_rooms(user):
        """
        Get all chat rooms for a user.
        """
        chat_rooms = ChatRoom.objects.filter(
            models.Q(rider=user) | models.Q(driver=user),
            status=ChatRoom.RoomStatus.ACTIVE,
            is_deleted=False
        ).order_by('-last_activity')
        
        return chat_rooms
    
    @staticmethod
    def _get_file_type(file):
        """
        Get file MIME type.
        """
        import mimetypes
        
        # Try to guess from filename
        file_type, _ = mimetypes.guess_type(file.name)
        
        if not file_type:
            # Default to application/octet-stream
            file_type = 'application/octet-stream'
        
        return file_type
