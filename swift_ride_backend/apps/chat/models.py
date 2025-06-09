"""
Chat models for Swift Ride project.
"""

import os
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator

from apps.common.models import BaseModel, SoftDeleteModel
from apps.common.utils import get_file_path


class ChatRoom(BaseModel, SoftDeleteModel):
    """
    Model for chat rooms between riders and drivers.
    """
    class RoomType(models.TextChoices):
        RIDE = 'ride', _('Ride Chat')
        SUPPORT = 'support', _('Support Chat')
        GENERAL = 'general', _('General Chat')
    
    class RoomStatus(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')
        BLOCKED = 'blocked', _('Blocked')
    
    room_id = models.CharField(max_length=100, unique=True)
    room_type = models.CharField(
        max_length=10,
        choices=RoomType.choices,
        default=RoomType.RIDE
    )
    status = models.CharField(
        max_length=10,
        choices=RoomStatus.choices,
        default=RoomStatus.ACTIVE
    )
    
    # Participants
    rider = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rider_chat_rooms'
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='driver_chat_rooms'
    )
    
    # Associated ride (if applicable)
    ride = models.OneToOneField(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='chat_room',
        null=True,
        blank=True
    )
    
    # Chat settings
    is_encrypted = models.BooleanField(default=True)
    auto_delete_after_days = models.PositiveIntegerField(default=30)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Chat Room: {self.room_id}"
    
    @property
    def participants(self):
        """Get all participants in the chat room."""
        return [self.rider, self.driver]
    
    @property
    def latest_message(self):
        """Get the latest message in the chat room."""
        return self.messages.filter(is_deleted=False).first()
    
    @property
    def unread_count_for_rider(self):
        """Get unread message count for rider."""
        return self.messages.filter(
            sender=self.driver,
            is_read=False,
            is_deleted=False
        ).count()
    
    @property
    def unread_count_for_driver(self):
        """Get unread message count for driver."""
        return self.messages.filter(
            sender=self.rider,
            is_read=False,
            is_deleted=False
        ).count()
    
    def get_unread_count_for_user(self, user):
        """Get unread message count for a specific user."""
        if user == self.rider:
            return self.unread_count_for_driver
        elif user == self.driver:
            return self.unread_count_for_rider
        return 0
    
    class Meta:
        ordering = ['-last_activity']


class Message(BaseModel, SoftDeleteModel):
    """
    Model for chat messages.
    """
    class MessageType(models.TextChoices):
        TEXT = 'text', _('Text Message')
        VOICE = 'voice', _('Voice Message')
        IMAGE = 'image', _('Image')
        FILE = 'file', _('File')
        LOCATION = 'location', _('Location')
        SYSTEM = 'system', _('System Message')
    
    class MessageStatus(models.TextChoices):
        SENT = 'sent', _('Sent')
        DELIVERED = 'delivered', _('Delivered')
        READ = 'read', _('Read')
        FAILED = 'failed', _('Failed')
    
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    message_type = models.CharField(
        max_length=10,
        choices=MessageType.choices,
        default=MessageType.TEXT
    )
    
    # Message content
    content = models.TextField(blank=True, null=True)
    encrypted_content = models.TextField(blank=True, null=True)
    
    # Message status
    status = models.CharField(
        max_length=10,
        choices=MessageStatus.choices,
        default=MessageStatus.SENT
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    # Reply functionality
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='replies',
        null=True,
        blank=True
    )
    
    # Location data (for location messages)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    location_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Message from {self.sender} in {self.chat_room.room_id}"
    
    @property
    def is_voice_message(self):
        return self.message_type == self.MessageType.VOICE
    
    @property
    def is_file_message(self):
        return self.message_type in [self.MessageType.IMAGE, self.MessageType.FILE]
    
    @property
    def recipient(self):
        """Get the recipient of the message."""
        if self.sender == self.chat_room.rider:
            return self.chat_room.driver
        return self.chat_room.rider
    
    def mark_as_read(self):
        """Mark message as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = models.functions.Now()
            self.status = self.MessageStatus.READ
            self.save(update_fields=['is_read', 'read_at', 'status'])
    
    def mark_as_delivered(self):
        """Mark message as delivered."""
        if self.status == self.MessageStatus.SENT:
            self.status = self.MessageStatus.DELIVERED
            self.delivered_at = models.functions.Now()
            self.save(update_fields=['status', 'delivered_at'])
    
    class Meta:
        ordering = ['-created_at']


class VoiceNote(BaseModel):
    """
    Model for voice notes in chat.
    """
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name='voice_note'
    )
    audio_file = models.FileField(
        upload_to=get_file_path,
        validators=[FileExtensionValidator(allowed_extensions=['mp3', 'wav', 'ogg', 'm4a'])]
    )
    duration_seconds = models.PositiveIntegerField()
    file_size = models.PositiveIntegerField()  # Size in bytes
    transcription = models.TextField(blank=True, null=True)
    is_transcribed = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Voice note for message {self.message.id}"
    
    @property
    def duration_formatted(self):
        """Format duration in MM:SS format with error handling"""
        try:
            if self.duration_seconds is None or self.duration_seconds < 0:
                return "00:00"
            
            minutes = int(self.duration_seconds) // 60
            seconds = int(self.duration_seconds) % 60
            return f"{minutes:02d}:{seconds:02d}"
        except (TypeError, ValueError):
            return "00:00"
    
    @property
    def file_size_formatted(self):
    # """Return formatted file size or appropriate message if size is not available."""
    
    # Handle None/null file_size
        if self.file_size is None:
            return "Size unknown"
    
    # Handle zero or negative file_size
        if self.file_size <= 0:
            return "0 bytes"
    
    # Format file size in human-readable format
        if self.file_size < 1024:
            return f"{self.file_size} bytes"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"
    # @property
    # def file_size_formatted(self):
    #     """Get formatted file size."""
    #     if self.file_size < 1024:
    #         return f"{self.file_size} B"
    #     elif self.file_size < 1024 * 1024:
    #         return f"{self.file_size / 1024:.1f} KB"
    #     else:
    #         return f"{self.file_size / (1024 * 1024):.1f} MB"


class FileAttachment(BaseModel):
    """
    Model for file attachments in chat.
    """
    message = models.OneToOneField(
        Message,
        on_delete=models.CASCADE,
        related_name='file_attachment'
    )
    file = models.FileField(upload_to=get_file_path)
    original_filename = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.PositiveIntegerField()  # Size in bytes
    
    # Image-specific fields
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    
    # Thumbnail for images/videos
    thumbnail = models.ImageField(
        upload_to=get_file_path,
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"File attachment: {self.original_filename}"
    
    @property
    def file_size_formatted(self):
        """Get formatted file size."""
        if self.file_size is None or self.file_size == 0:
            return "Unknown"
    
        if self.file_size < 1024:
            return f"{self.file_size} bytes"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        elif self.file_size < 1024 * 1024 * 1024:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
        else:
            return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"
        
    @property
    def is_image(self):
        """Check if file is an image."""
        image_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
        return self.file_type in image_types
    
    @property
    def file_extension(self):
        """Get file extension."""
        return os.path.splitext(self.original_filename)[1].lower()


class MessageStatus(BaseModel):
    """
    Model for tracking message delivery and read status.
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='status_updates'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='message_statuses'
    )
    status = models.CharField(
        max_length=10,
        choices=Message.MessageStatus.choices
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user} - {self.message} - {self.status}"
    
    class Meta:
        unique_together = ['message', 'user', 'status']
        ordering = ['-timestamp']


class ChatModerationLog(BaseModel):
    """
    Model for chat moderation logs.
    """
    class ActionType(models.TextChoices):
        WARNING = 'warning', _('Warning')
        MESSAGE_DELETED = 'message_deleted', _('Message Deleted')
        USER_MUTED = 'user_muted', _('User Muted')
        CHAT_BLOCKED = 'chat_blocked', _('Chat Blocked')
        INAPPROPRIATE_CONTENT = 'inappropriate_content', _('Inappropriate Content')
    
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='moderation_logs'
    )
    message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        related_name='moderation_logs',
        null=True,
        blank=True
    )
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='moderation_actions',
        null=True,
        blank=True
    )
    action_type = models.CharField(
        max_length=25,
        choices=ActionType.choices
    )
    reason = models.TextField()
    automated = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Moderation: {self.action_type} in {self.chat_room.room_id}"
    
    class Meta:
        ordering = ['-created_at']


class ChatSettings(BaseModel):
    """
    Model for user chat settings.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='chat_settings'
    )
    
    # Notification settings
    message_notifications = models.BooleanField(default=True)
    voice_message_notifications = models.BooleanField(default=True)
    file_notifications = models.BooleanField(default=True)
    
    # Privacy settings
    read_receipts = models.BooleanField(default=True)
    online_status = models.BooleanField(default=True)
    
    # Auto-delete settings
    auto_delete_messages = models.BooleanField(default=False)
    auto_delete_after_days = models.PositiveIntegerField(default=30)
    
    # Voice settings
    voice_message_auto_play = models.BooleanField(default=False)
    voice_transcription = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Chat settings for {self.user}"
