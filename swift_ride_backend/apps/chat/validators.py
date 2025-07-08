"""
Validators for chat app.
"""

import os
import mimetypes
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.conf import settings


def validate_message_content(content):
    """
    Validate message content.
    """
    if not content or not content.strip():
        raise ValidationError("Message content cannot be empty.")
    
    # Check maximum length
    max_length = getattr(settings, 'CHAT_MESSAGE_MAX_LENGTH', 1000)
    if len(content) > max_length:
        raise ValidationError(f"Message content cannot exceed {max_length} characters.")
    
    # Check for minimum length
    if len(content.strip()) < 1:
        raise ValidationError("Message content is too short.")
    
    return content.strip()


def validate_voice_duration(duration):
    """
    Validate voice message duration.
    """
    if duration <= 0:
        raise ValidationError("Voice message duration must be positive.")
    
    # Maximum duration: 5 minutes (300 seconds)
    max_duration = getattr(settings, 'CHAT_VOICE_MAX_DURATION', 300)
    if duration > max_duration:
        raise ValidationError(f"Voice message cannot exceed {max_duration} seconds.")
    
    return duration


def validate_audio_file(file):
    """
    Validate audio file for voice messages.
    """
    # Check file size (max 10MB)
    max_size = getattr(settings, 'CHAT_VOICE_MAX_SIZE', 10 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f"Audio file size cannot exceed {max_size / (1024 * 1024):.1f}MB.")
    
    # Check file extension
    allowed_extensions = ['.mp3', '.wav', '.ogg', '.m4a', '.aac']
    file_extension = os.path.splitext(file.name)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f"Unsupported audio format. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type and not mime_type.startswith('audio/'):
        raise ValidationError("File must be an audio file.")
    
    return file


def validate_image_file(file):
    """
    Validate image file for chat.
    """
    # Check file size (max 25MB)
    max_size = getattr(settings, 'CHAT_IMAGE_MAX_SIZE', 25 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f"Image file size cannot exceed {max_size / (1024 * 1024):.1f}MB.")
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
    file_extension = os.path.splitext(file.name)[1].lower()
    
    if file_extension not in allowed_extensions:
        raise ValidationError(
            f"Unsupported image format. Allowed formats: {', '.join(allowed_extensions)}"
        )
    
    # Check MIME type
    mime_type, _ = mimetypes.guess_type(file.name)
    if mime_type and not mime_type.startswith('image/'):
        raise ValidationError("File must be an image file.")
    
    return file


def validate_chat_file(file):
    """
    Validate general file for chat.
    """
    # Check file size (max 50MB)
    max_size = getattr(settings, 'CHAT_FILE_MAX_SIZE', 50 * 1024 * 1024)
    if file.size > max_size:
        raise ValidationError(f"File size cannot exceed {max_size / (1024 * 1024):.1f}MB.")
    
    # Check for dangerous file extensions
    dangerous_extensions = [
        '.exe', '.bat', '.cmd', '.scr', '.pif', '.com', '.msi',
        '.vbs', '.js', '.jar', '.app', '.deb', '.rpm'
    ]
    file_extension = os.path.splitext(file.name)[1].lower()
    
    if file_extension in dangerous_extensions:
        raise ValidationError("This file type is not allowed for security reasons.")
    
    # Check filename length
    if len(file.name) > 255:
        raise ValidationError("Filename is too long.")
    
    return file


def validate_location_coordinates(latitude, longitude):
    """
    Validate location coordinates.
    """
    try:
        lat = float(latitude)
        lng = float(longitude)
    except (ValueError, TypeError):
        raise ValidationError("Invalid coordinate format.")
    
    # Validate latitude range
    if not -90 <= lat <= 90:
        raise ValidationError("Latitude must be between -90 and 90 degrees.")
    
    # Validate longitude range
    if not -180 <= lng <= 180:
        raise ValidationError("Longitude must be between -180 and 180 degrees.")
    
    return lat, lng


def validate_room_id(room_id):
    """
    Validate chat room ID format.
    """
    if not room_id or not room_id.strip():
        raise ValidationError("Room ID cannot be empty.")
    
    # Check length
    if len(room_id) < 5 or len(room_id) > 100:
        raise ValidationError("Room ID must be between 5 and 100 characters.")
    
    # Check for valid characters (alphanumeric, underscore, hyphen)
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', room_id):
        raise ValidationError("Room ID can only contain letters, numbers, underscores, and hyphens.")
    
    return room_id.strip()


def validate_chat_room_type(room_type):
    """
    Validate chat room type.
    """
    from apps.chat.models import ChatRoom
    
    valid_types = [choice[0] for choice in ChatRoom.RoomType.choices]
    
    if room_type not in valid_types:
        raise ValidationError(f"Invalid room type. Must be one of: {', '.join(valid_types)}")
    
    return room_type


def validate_message_type(message_type):
    """
    Validate message type.
    """
    from apps.chat.models import Message
    
    valid_types = [choice[0] for choice in Message.MessageType.choices]
    
    if message_type not in valid_types:
        raise ValidationError(f"Invalid message type. Must be one of: {', '.join(valid_types)}")
    
    return message_type


def validate_auto_delete_days(days):
    """
    Validate auto delete days setting.
    """
    if days is not None:
        if days < 0:
            raise ValidationError("Auto delete days cannot be negative.")
        
        if days > 365:
            raise ValidationError("Auto delete days cannot exceed 365 days.")
    
    return days


def validate_transcription_text(text):
    """
    Validate transcription text.
    """
    if text and len(text) > 5000:
        raise ValidationError("Transcription text cannot exceed 5000 characters.")
    
    return text


def validate_metadata(metadata):
    """
    Validate message metadata.
    """
    if metadata is None:
        return {}
    
    if not isinstance(metadata, dict):
        raise ValidationError("Metadata must be a dictionary.")
    
    # Check metadata size (serialized)
    import json
    try:
        serialized = json.dumps(metadata)
        if len(serialized) > 10000:  # 10KB limit
            raise ValidationError("Metadata is too large.")
    except (TypeError, ValueError):
        raise ValidationError("Metadata contains non-serializable data.")
    
    return metadata


def validate_chat_settings(settings_data):
    """
    Validate chat settings data.
    """
    if not isinstance(settings_data, dict):
        raise ValidationError("Settings data must be a dictionary.")
    
    # Validate boolean fields
    boolean_fields = [
        'message_notifications', 'voice_message_notifications',
        'file_notifications', 'read_receipts', 'online_status',
        'auto_delete_messages', 'voice_message_auto_play',
        'voice_transcription'
    ]
    
    for field in boolean_fields:
        if field in settings_data:
            if not isinstance(settings_data[field], bool):
                raise ValidationError(f"{field} must be a boolean value.")
    
    # Validate auto_delete_after_days
    if 'auto_delete_after_days' in settings_data:
        days = settings_data['auto_delete_after_days']
        if not isinstance(days, int) or days < 1 or days > 365:
            raise ValidationError("auto_delete_after_days must be between 1 and 365.")
    
    return settings_data


class ChatFileValidator:
    """
    Custom validator class for chat files.
    """
    
    def __init__(self, allowed_types=None, max_size=None):
        self.allowed_types = allowed_types or ['image', 'audio', 'document']
        self.max_size = max_size or 50 * 1024 * 1024  # 50MB default
    
    def __call__(self, file):
        # Check file size
        if file.size > self.max_size:
            raise ValidationError(
                f"File size cannot exceed {self.max_size / (1024 * 1024):.1f}MB."
            )
        
        # Check file type
        mime_type, _ = mimetypes.guess_type(file.name)
        if mime_type:
            file_category = mime_type.split('/')[0]
            if file_category not in self.allowed_types:
                raise ValidationError(
                    f"File type not allowed. Allowed types: {', '.join(self.allowed_types)}"
                )
        
        return file


class VoiceMessageValidator:
    """
    Custom validator for voice messages.
    """
    
    def __init__(self, max_duration=300, max_size=10*1024*1024):
        self.max_duration = max_duration
        self.max_size = max_size
    
    def validate_file(self, file):
        return validate_audio_file(file)
    
    def validate_duration(self, duration):
        return validate_voice_duration(duration)
