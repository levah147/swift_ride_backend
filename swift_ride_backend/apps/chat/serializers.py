"""
Serializers for chat models.
"""

from rest_framework import serializers
from django.utils import timezone

from apps.chat.models import (
    ChatRoom, Message, VoiceNote, FileAttachment, 
    MessageStatus, ChatSettings
)
from apps.users.serializers import UserSerializer  

 
class VoiceNoteSerializer(serializers.ModelSerializer):
    """
    Serializer for VoiceNote model.
    """
    duration_formatted = serializers.CharField(read_only=True)
    file_size_formatted = serializers.CharField(read_only=True)
    
    class Meta:
        model = VoiceNote
        fields = [
            'id', 'audio_file', 'duration_seconds', 'duration_formatted',
            'file_size', 'file_size_formatted', 'transcription', 'is_transcribed'
        ]


class FileAttachmentSerializer(serializers.ModelSerializer):
    """
    Serializer for FileAttachment model.
    """
    file_size_formatted = serializers.CharField(read_only=True)
    is_image = serializers.BooleanField(read_only=True)
    file_extension = serializers.CharField(read_only=True)
    
    class Meta:
        model = FileAttachment
        fields = [
            'id', 'file', 'original_filename', 'file_type', 'file_size',
            'file_size_formatted', 'width', 'height', 'thumbnail',
            'is_image', 'file_extension'
        ]


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for Message model.
    """
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True)
    voice_note = VoiceNoteSerializer(read_only=True)
    file_attachment = FileAttachmentSerializer(read_only=True)
    reply_to = serializers.SerializerMethodField()
    is_voice_message = serializers.BooleanField(read_only=True)
    is_file_message = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'chat_room', 'sender', 'recipient', 'message_type',
            'content', 'status', 'is_read', 'read_at', 'delivered_at',
            'reply_to', 'latitude', 'longitude', 'location_name',
            'metadata', 'voice_note', 'file_attachment', 'is_voice_message',
            'is_file_message', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'sender', 'recipient', 'status', 'is_read', 'read_at',
            'delivered_at', 'created_at', 'updated_at'
        ]
    
    def get_reply_to(self, obj):
        """Get reply_to message with limited fields."""
        if obj.reply_to:
            return {
                'id': obj.reply_to.id,
                'sender': UserSerializer(obj.reply_to.sender).data,
                'content': obj.reply_to.content[:100] + '...' if len(obj.reply_to.content) > 100 else obj.reply_to.content,
                'message_type': obj.reply_to.message_type,
                'created_at': obj.reply_to.created_at
            }
        return None


class ChatRoomSerializer(serializers.ModelSerializer):
    """
    Serializer for ChatRoom model.
    """
    rider = UserSerializer(read_only=True)
    driver = UserSerializer(read_only=True)
    latest_message = MessageSerializer(read_only=True)
    participants = UserSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_id', 'room_type', 'status', 'rider', 'driver',
            'ride', 'is_encrypted', 'auto_delete_after_days', 'last_activity',
            'latest_message', 'participants', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'room_id', 'rider', 'driver', 'ride', 'created_at', 'updated_at'
        ]


class ChatRoomListSerializer(serializers.ModelSerializer):
    """
    Serializer for ChatRoom list view with unread counts.
    """
    rider = UserSerializer(read_only=True)
    driver = UserSerializer(read_only=True)
    latest_message = MessageSerializer(read_only=True)
    unread_count = serializers.SerializerMethodField()
    other_participant = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatRoom
        fields = [
            'id', 'room_id', 'room_type', 'status', 'rider', 'driver',
            'ride', 'last_activity', 'latest_message', 'unread_count',
            'other_participant', 'created_at'
        ]
    
    def get_unread_count(self, obj):
        """Get unread count for the current user."""
        request = self.context.get('request')
        if request and request.user:
            return obj.get_unread_count_for_user(request.user)
        return 0
    
    def get_other_participant(self, obj):
        """Get the other participant (not the current user)."""
        request = self.context.get('request')
        if request and request.user:
            if request.user == obj.rider:
                return UserSerializer(obj.driver).data
            else:
                return UserSerializer(obj.rider).data
        return None


class MessageCreateSerializer(serializers.Serializer):
    """
    Serializer for creating messages.
    """
    content = serializers.CharField(max_length=1000)
    message_type = serializers.ChoiceField(
        choices=Message.MessageType.choices,
        default=Message.MessageType.TEXT
    )
    reply_to_id = serializers.UUIDField(required=False)
    
    # Location fields
    latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False
    )
    longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False
    )
    location_name = serializers.CharField(max_length=255, required=False)
    
    def validate(self, data):
        """Validate message data."""
        message_type = data.get('message_type')
        
        # Validate location message
        if message_type == Message.MessageType.LOCATION:
            if not data.get('latitude') or not data.get('longitude'):
                raise serializers.ValidationError(
                    "Latitude and longitude are required for location messages"
                )
        
        return data


class VoiceMessageUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading voice messages.
    """
    audio_file = serializers.FileField()
    duration_seconds = serializers.IntegerField(min_value=1, max_value=300)  # Max 5 minutes
    
    def validate_audio_file(self, value):
        """Validate audio file."""
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Audio file too large. Maximum size is 10MB.")
        
        # Check file extension
        allowed_extensions = ['.mp3', '.wav', '.ogg', '.m4a']
        file_extension = value.name.lower().split('.')[-1]
        
        if f'.{file_extension}' not in allowed_extensions:
            raise serializers.ValidationError(
                f"Unsupported audio format. Allowed formats: {', '.join(allowed_extensions)}"
            )
        
        return value


class FileMessageUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading file messages.
    """
    file = serializers.FileField()
    
    def validate_file(self, value):
        """Validate file."""
        # Check file size (max 50MB)
        if value.size > 50 * 1024 * 1024:
            raise serializers.ValidationError("File too large. Maximum size is 50MB.")
        
        # Check for potentially dangerous file types
        dangerous_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
        file_extension = value.name.lower().split('.')[-1]
        
        if f'.{file_extension}' in dangerous_extensions:
            raise serializers.ValidationError("This file type is not allowed for security reasons.")
        
        return value


class ChatSettingsSerializer(serializers.ModelSerializer):
    """
    Serializer for ChatSettings model.
    """
    class Meta:
        model = ChatSettings
        fields = [
            'id', 'message_notifications', 'voice_message_notifications',
            'file_notifications', 'read_receipts', 'online_status',
            'auto_delete_messages', 'auto_delete_after_days',
            'voice_message_auto_play', 'voice_transcription'
        ]
        read_only_fields = ['id']
