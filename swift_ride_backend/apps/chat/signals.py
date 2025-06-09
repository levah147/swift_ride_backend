"""
Signals for chat models.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.chat.models import Message, ChatRoom, VoiceNote
  
 
@receiver(post_save, sender=Message)
def message_sent(sender, instance, created, **kwargs):
    """
    Handle message sent event.
    """
    if created:
        # Send push notification to recipient
        recipient = instance.recipient
        
        # Don't send notification for system messages
        if instance.message_type != Message.MessageType.SYSTEM:
            print(f"New message from {instance.sender} to {recipient}")
            # Here you would send actual push notification
            
        # Update chat room last activity
        instance.chat_room.last_activity = instance.created_at
        instance.chat_room.save(update_fields=['last_activity'])


@receiver(post_save, sender=VoiceNote)
def voice_note_uploaded(sender, instance, created, **kwargs):
    """
    Handle voice note upload.
    """
    if created:
        print(f"Voice note uploaded: {instance}")
        # Here you could trigger transcription service
        
        # Start transcription task
        from apps.chat.tasks import transcribe_voice_note
        transcribe_voice_note.delay(str(instance.id))


@receiver(pre_save, sender=Message)
def encrypt_message_content(sender, instance, **kwargs):
    """
    Encrypt message content before saving.
    """
    if instance.chat_room.is_encrypted and instance.content and not instance.encrypted_content:
        from apps.chat.services.encryption_service import EncryptionService
        
        encrypted_content = EncryptionService.encrypt_message(instance.content)
        if encrypted_content:
            instance.encrypted_content = encrypted_content
            # Clear original content for security
            instance.content = "[Encrypted]"
