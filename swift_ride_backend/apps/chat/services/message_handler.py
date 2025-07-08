"""
Service for handling message operations and processing.
"""

import re
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from apps.chat.models import ChatRoom, Message, MessageStatus
from apps.notifications.services.notification_service import NotificationService


class MessageHandler:
    """
    Service for handling message operations.
    """
    
    @staticmethod
    def process_incoming_message(chat_room, sender, content, message_type, **kwargs):
        """
        Process incoming message with validation and filtering.
        """
        try:
            with transaction.atomic():
                # Validate message content
                if message_type == Message.MessageType.TEXT:
                    content = MessageHandler._clean_text_content(content)
                    
                    # Check for spam
                    if MessageHandler._is_spam_message(content, sender):
                        raise ValueError("Message flagged as spam")
                
                # Create message
                message = Message.objects.create(
                    chat_room=chat_room,
                    sender=sender,
                    content=content,
                    message_type=message_type,
                    **kwargs
                )
                
                # Update chat room activity
                chat_room.last_activity = timezone.now()
                chat_room.save(update_fields=['last_activity'])
                
                # Process message based on type
                MessageHandler._post_process_message(message)
                
                return message
        
        except Exception as e:
            print(f"Error processing message: {e}")
            raise
    
    @staticmethod
    def _clean_text_content(content):
        """
        Clean and sanitize text content.
        """
        if not content:
            return content
        
        # Remove excessive whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        
        # Remove potentially harmful content
        content = MessageHandler._sanitize_content(content)
        
        return content
    
    @staticmethod
    def _sanitize_content(content):
        """
        Sanitize message content for security.
        """
        # Remove script tags and other potentially harmful content
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'javascript:', '', content, flags=re.IGNORECASE)
        content = re.sub(r'on\w+\s*=', '', content, flags=re.IGNORECASE)
        
        return content
    
    @staticmethod
    def _is_spam_message(content, sender):
        """
        Check if message is spam.
        """
        # Check for repeated characters
        if len(set(content)) < 3 and len(content) > 10:
            return True
        
        # Check for excessive caps
        caps_ratio = sum(1 for c in content if c.isupper()) / len(content) if content else 0
        if caps_ratio > 0.7 and len(content) > 20:
            return True
        
        # Check for repeated messages from same sender
        recent_messages = Message.objects.filter(
            sender=sender,
            created_at__gte=timezone.now() - timedelta(minutes=5)
        ).values_list('content', flat=True)
        
        if list(recent_messages).count(content) > 3:
            return True
        
        # Check for common spam patterns
        spam_patterns = [
            r'(buy|sell|cheap|free|win|prize|money|cash|loan)',
            r'(click here|visit now|act now|limited time)',
            r'(www\.|http|\.com|\.net|\.org)',
        ]
        
        for pattern in spam_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                # Additional checks could be added here
                pass
        
        return False
    
    @staticmethod
    def _post_process_message(message):
        """
        Post-process message after creation.
        """
        # Send notification to recipient
        MessageHandler._send_message_notification(message)
        
        # Update message status
        MessageHandler._update_message_status(message)
        
        # Check for auto-moderation
        MessageHandler._auto_moderate_message(message)
    
    @staticmethod
    def _send_message_notification(message):
        """
        Send notification for new message.
        """
        try:
            recipient = message.recipient
            
            # Check if recipient wants notifications
            try:
                chat_settings = recipient.chat_settings
                if not chat_settings.message_notifications:
                    return
            except:
                pass  # Default to sending notifications
            
            # Create notification content
            if message.message_type == Message.MessageType.TEXT:
                preview = message.content[:50] + '...' if len(message.content) > 50 else message.content
                notification_text = f"New message: {preview}"
            elif message.message_type == Message.MessageType.VOICE:
                notification_text = "New voice message"
            elif message.message_type == Message.MessageType.IMAGE:
                notification_text = "New image"
            elif message.message_type == Message.MessageType.FILE:
                notification_text = "New file"
            elif message.message_type == Message.MessageType.LOCATION:
                notification_text = "Location shared"
            else:
                notification_text = "New message"
            
            # Send notification (async task)
            from apps.chat.tasks import send_message_notification
            send_message_notification.delay(str(message.id))
        
        except Exception as e:
            print(f"Error sending message notification: {e}")
    
    @staticmethod
    def _update_message_status(message):
        """
        Update message delivery status.
        """
        try:
            # Mark as delivered (in real implementation, this would be done via WebSocket)
            message.status = Message.MessageStatus.DELIVERED
            message.delivered_at = timezone.now()
            message.save(update_fields=['status', 'delivered_at'])
        
        except Exception as e:
            print(f"Error updating message status: {e}")
    
    @staticmethod
    def _auto_moderate_message(message):
        """
        Auto-moderate message content.
        """
        try:
            # Start moderation task
            from apps.chat.tasks import moderate_chat_content
            moderate_chat_content.delay(str(message.id))
        
        except Exception as e:
            print(f"Error starting auto-moderation: {e}")
    
    @staticmethod
    def mark_messages_as_read(chat_room, user, message_ids=None):
        """
        Mark messages as read for a user.
        """
        try:
            with transaction.atomic():
                # Get messages to mark as read
                messages_query = Message.objects.filter(
                    chat_room=chat_room,
                    is_read=False,
                    is_deleted=False
                ).exclude(sender=user)
                
                if message_ids:
                    messages_query = messages_query.filter(id__in=message_ids)
                
                # Update messages
                count = messages_query.update(
                    is_read=True,
                    read_at=timezone.now(),
                    status=Message.MessageStatus.READ
                )
                
                # Cache the read status for real-time updates
                cache_key = f"chat_read_status_{chat_room.id}_{user.id}"
                cache.set(cache_key, timezone.now().isoformat(), timeout=3600)
                
                return count
        
        except Exception as e:
            print(f"Error marking messages as read: {e}")
            return 0
    
    @staticmethod
    def get_unread_count(chat_room, user):
        """
        Get unread message count for user.
        """
        try:
            return Message.objects.filter(
                chat_room=chat_room,
                is_read=False,
                is_deleted=False
            ).exclude(sender=user).count()
        
        except Exception as e:
            print(f"Error getting unread count: {e}")
            return 0
    
    @staticmethod
    def search_messages(chat_room, user, query, limit=50):
        """
        Search messages in chat room.
        """
        try:
            # Check if user is participant
            if user not in chat_room.participants:
                return Message.objects.none()
            
            # Search in message content
            messages = Message.objects.filter(
                chat_room=chat_room,
                content__icontains=query,
                is_deleted=False
            ).order_by('-created_at')[:limit]
            
            return messages
        
        except Exception as e:
            print(f"Error searching messages: {e}")
            return Message.objects.none()
    
    @staticmethod
    def get_message_thread(message):
        """
        Get message thread (replies to a message).
        """
        try:
            return Message.objects.filter(
                reply_to=message,
                is_deleted=False
            ).order_by('created_at')
        
        except Exception as e:
            print(f"Error getting message thread: {e}")
            return Message.objects.none()
    
    @staticmethod
    def delete_message(message, user):
        """
        Delete a message (soft delete).
        """
        try:
            # Check permissions
            if message.sender != user and not user.is_staff:
                return False, "You can only delete your own messages"
            
            # Check if message is already deleted
            if message.is_deleted:
                return False, "Message is already deleted"
            
            # Soft delete
            with transaction.atomic():
                message.is_deleted = True
                message.deleted_at = timezone.now()
                message.save(update_fields=['is_deleted', 'deleted_at'])
                
                # Log deletion
                print(f"Message {message.id} deleted by user {user.id}")
                
                return True, "Message deleted successfully"
        
        except Exception as e:
            print(f"Error deleting message: {e}")
            return False, "Error deleting message"
    
    @staticmethod
    def edit_message(message, user, new_content):
        """
        Edit a message (if allowed).
        """
        try:
            # Check permissions
            if message.sender != user:
                return False, "You can only edit your own messages"
            
            # Check if message is too old to edit (e.g., 15 minutes)
            time_limit = timezone.now() - timedelta(minutes=15)
            if message.created_at < time_limit:
                return False, "Message is too old to edit"
            
            # Check if message type allows editing
            if message.message_type != Message.MessageType.TEXT:
                return False, "Only text messages can be edited"
            
            # Update message
            with transaction.atomic():
                message.content = MessageHandler._clean_text_content(new_content)
                message.updated_at = timezone.now()
                message.save(update_fields=['content', 'updated_at'])
                
                return True, "Message edited successfully"
        
        except Exception as e:
            print(f"Error editing message: {e}")
            return False, "Error editing message"
    
    @staticmethod
    def get_chat_statistics(chat_room, user):
        """
        Get chat statistics for a user.
        """
        try:
            if user not in chat_room.participants:
                return {}
            
            messages = Message.objects.filter(
                chat_room=chat_room,
                is_deleted=False
            )
            
            total_messages = messages.count()
            user_messages = messages.filter(sender=user).count()
            other_user = chat_room.driver if user == chat_room.rider else chat_room.rider
            other_messages = messages.filter(sender=other_user).count()
            
            # Message types
            text_messages = messages.filter(message_type=Message.MessageType.TEXT).count()
            voice_messages = messages.filter(message_type=Message.MessageType.VOICE).count()
            image_messages = messages.filter(message_type=Message.MessageType.IMAGE).count()
            file_messages = messages.filter(message_type=Message.MessageType.FILE).count()
            
            return {
                'total_messages': total_messages,
                'user_messages': user_messages,
                'other_messages': other_messages,
                'message_types': {
                    'text': text_messages,
                    'voice': voice_messages,
                    'image': image_messages,
                    'file': file_messages,
                },
                'chat_duration': (timezone.now() - chat_room.created_at).days,
                'last_activity': chat_room.last_activity,
            }
        
        except Exception as e:
            print(f"Error getting chat statistics: {e}")
            return {}
