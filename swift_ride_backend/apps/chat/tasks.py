"""
Celery tasks for chat app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from apps.chat.models import Message, VoiceNote, ChatRoom


@shared_task
def transcribe_voice_note(voice_note_id):
    """
    Transcribe a voice note to text.
    """
    try:
        voice_note = VoiceNote.objects.get(id=voice_note_id)
        
        # Use voice service to transcribe
        from apps.chat.services.voice_service import VoiceService
        transcription = VoiceService.transcribe_audio(voice_note.audio_file)
        
        if transcription:
            voice_note.transcription = transcription
            voice_note.is_transcribed = True
            voice_note.save()
            
            return f"Voice note {voice_note_id} transcribed successfully"
        else:
            return f"Failed to transcribe voice note {voice_note_id}"
    
    except VoiceNote.DoesNotExist:
        return f"Voice note {voice_note_id} not found"
    except Exception as e:
        return f"Error transcribing voice note {voice_note_id}: {str(e)}"


@shared_task
def auto_delete_old_messages():
    """
    Auto-delete old messages based on chat room settings.
    """
    # Get chat rooms with auto-delete enabled
    chat_rooms = ChatRoom.objects.filter(
        auto_delete_after_days__gt=0
    )
    
    deleted_count = 0
    
    for chat_room in chat_rooms:
        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=chat_room.auto_delete_after_days)
        
        # Delete old messages
        old_messages = Message.objects.filter(
            chat_room=chat_room,
            created_at__lt=cutoff_date,
            is_deleted=False
        )
        
        count = old_messages.count()
        old_messages.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
        
        deleted_count += count
    
    return f"Auto-deleted {deleted_count} old messages"


@shared_task
def cleanup_deleted_messages():
    """
    Permanently delete messages that have been soft-deleted for more than 30 days.
    """
    cutoff_date = timezone.now() - timedelta(days=30)
    
    # Get messages that have been soft-deleted for more than 30 days
    messages_to_delete = Message.objects.filter(
        is_deleted=True,
        deleted_at__lt=cutoff_date
    )
    
    count = messages_to_delete.count()
    
    # Permanently delete
    messages_to_delete.delete()
    
    return f"Permanently deleted {count} old messages"


@shared_task
def send_message_notification(message_id):
    """
    Send push notification for a new message.
    """
    try:
        message = Message.objects.get(id=message_id)
        recipient = message.recipient
        
        # Check if recipient has notifications enabled
        try:
            chat_settings = recipient.chat_settings
            if not chat_settings.message_notifications:
                return f"Notifications disabled for user {recipient.id}"
        except:
            # Default to enabled if no settings
            pass
        
        # Send notification based on message type
        if message.message_type == Message.MessageType.VOICE:
            notification_text = f"{message.sender.get_full_name() or message.sender.phone_number} sent you a voice message"
        elif message.message_type == Message.MessageType.IMAGE:
            notification_text = f"{message.sender.get_full_name() or message.sender.phone_number} sent you an image"
        elif message.message_type == Message.MessageType.FILE:
            notification_text = f"{message.sender.get_full_name() or message.sender.phone_number} sent you a file"
        elif message.message_type == Message.MessageType.LOCATION:
            notification_text = f"{message.sender.get_full_name() or message.sender.phone_number} shared their location"
        else:
            # Text message
            content_preview = message.content[:50] + '...' if len(message.content) > 50 else message.content
            notification_text = f"{message.sender.get_full_name() or message.sender.phone_number}: {content_preview}"
        
        # Here you would send actual push notification
        print(f"Push notification: {notification_text}")
        
        return f"Notification sent for message {message_id}"
    
    except Message.DoesNotExist:
        return f"Message {message_id} not found"
    except Exception as e:
        return f"Error sending notification for message {message_id}: {str(e)}"


@shared_task
def moderate_chat_content(message_id):
    """
    Moderate chat content for inappropriate material.
    """
    try:
        message = Message.objects.get(id=message_id)
        
        # Simple content moderation (in production, use AI services)
        inappropriate_words = ['spam', 'scam', 'fraud']  # Simplified list
        
        if message.content:
            content_lower = message.content.lower()
            
            for word in inappropriate_words:
                if word in content_lower:
                    # Flag message for review
                    from apps.chat.models import ChatModerationLog
                    ChatModerationLog.objects.create(
                        chat_room=message.chat_room,
                        message=message,
                        action_type=ChatModerationLog.ActionType.INAPPROPRIATE_CONTENT,
                        reason=f"Message contains inappropriate word: {word}",
                        automated=True
                    )
                    
                    return f"Message {message_id} flagged for inappropriate content"
        
        return f"Message {message_id} passed moderation"
    
    except Message.DoesNotExist:
        return f"Message {message_id} not found"
    except Exception as e:
        return f"Error moderating message {message_id}: {str(e)}"


@shared_task
def archive_inactive_chat_rooms():
    """
    Archive chat rooms that have been inactive for more than 30 days.
    """
    cutoff_date = timezone.now() - timedelta(days=30)
    
    inactive_rooms = ChatRoom.objects.filter(
        status=ChatRoom.RoomStatus.ACTIVE,
        last_activity__lt=cutoff_date
    )
    
    count = inactive_rooms.count()
    inactive_rooms.update(status=ChatRoom.RoomStatus.ARCHIVED)
    
    return f"Archived {count} inactive chat rooms"
