"""
Utility functions for chat app.
"""

import os
import uuid
import hashlib
from datetime import datetime, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone
from PIL import Image
import mimetypes


def get_chat_file_path(instance, filename):
    """
    Generate file path for chat files.
    """
    # Get file extension
    ext = filename.split('.')[-1].lower()
    
    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    # Determine subfolder based on file type
    if hasattr(instance, 'message'):
        message = instance.message
        chat_room_id = message.chat_room.room_id
        
        if hasattr(instance, 'audio_file'):
            # Voice note
            subfolder = 'voice_notes'
        else:
            # File attachment
            file_type = getattr(instance, 'file_type', '')
            if file_type.startswith('image/'):
                subfolder = 'images'
            else:
                subfolder = 'files'
    else:
        subfolder = 'misc'
        chat_room_id = 'general'
    
    return f"chat/{subfolder}/{chat_room_id}/{unique_filename}"


def compress_image(image_file, max_size=(800, 600), quality=85):
    """
    Compress image file for chat.
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Resize if too large
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save compressed image
        from io import BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return output
    
    except Exception as e:
        print(f"Error compressing image: {e}")
        return image_file


def generate_thumbnail(image_file, size=(150, 150)):
    """
    Generate thumbnail for image.
    """
    try:
        # Open image
        img = Image.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # Create thumbnail
        img.thumbnail(size, Image.Resampling.LANCZOS)
        
        # Save thumbnail
        from io import BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=90)
        output.seek(0)
        
        return output
    
    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return None


def get_file_type_category(file_type):
    """
    Categorize file type.
    """
    if file_type.startswith('image/'):
        return 'image'
    elif file_type.startswith('audio/'):
        return 'audio'
    elif file_type.startswith('video/'):
        return 'video'
    elif file_type in ['application/pdf']:
        return 'document'
    elif file_type in ['application/zip', 'application/x-rar-compressed']:
        return 'archive'
    else:
        return 'file'


def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def format_duration(seconds):
    """
    Format duration in MM:SS format.
    """
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"


def is_file_allowed(filename, allowed_extensions=None):
    """
    Check if file extension is allowed.
    """
    if allowed_extensions is None:
        # Default allowed extensions
        allowed_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.webp',  # Images
            '.mp3', '.wav', '.ogg', '.m4a',  # Audio
            '.mp4', '.avi', '.mov', '.webm',  # Video
            '.pdf', '.doc', '.docx', '.txt',  # Documents
            '.zip', '.rar'  # Archives
        ]
    
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in allowed_extensions


def sanitize_filename(filename):
    """
    Sanitize filename for safe storage.
    """
    # Remove or replace unsafe characters
    unsafe_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Limit filename length
    name, ext = os.path.splitext(filename)
    if len(name) > 100:
        name = name[:100]
    
    return f"{name}{ext}"


def generate_room_id(rider_id, driver_id, ride_id=None):
    """
    Generate unique room ID for chat.
    """
    if ride_id:
        base_string = f"ride_{ride_id}_{rider_id}_{driver_id}"
    else:
        # Sort IDs to ensure consistent room ID regardless of order
        ids = sorted([str(rider_id), str(driver_id)])
        base_string = f"chat_{ids[0]}_{ids[1]}"
    
    # Add timestamp for uniqueness
    timestamp = int(timezone.now().timestamp())
    base_string += f"_{timestamp}"
    
    # Generate hash for shorter ID
    hash_object = hashlib.md5(base_string.encode())
    return hash_object.hexdigest()[:16]


def clean_message_content(content):
    """
    Clean and sanitize message content.
    """
    if not content:
        return content
    
    # Remove excessive whitespace
    content = ' '.join(content.split())
    
    # Limit message length
    max_length = getattr(settings, 'CHAT_MESSAGE_MAX_LENGTH', 1000)
    if len(content) > max_length:
        content = content[:max_length]
    
    return content.strip()


def is_spam_message(content, sender):
    """
    Simple spam detection for messages.
    """
    if not content:
        return False
    
    # Check for repeated characters
    if len(set(content)) < 3 and len(content) > 10:
        return True
    
    # Check for excessive caps
    if content.isupper() and len(content) > 20:
        return True
    
    # Check for repeated messages (would need database check)
    # This is a simplified implementation
    
    return False


def get_message_preview(content, max_length=50):
    """
    Get preview of message content.
    """
    if not content:
        return ""
    
    if len(content) <= max_length:
        return content
    
    return content[:max_length] + "..."


def calculate_read_time(content):
    """
    Calculate estimated read time for message.
    """
    if not content:
        return 0
    
    # Average reading speed: 200 words per minute
    words = len(content.split())
    read_time_minutes = words / 200
    
    # Convert to seconds
    return max(1, int(read_time_minutes * 60))


def get_time_ago(timestamp):
    """
    Get human readable time ago string.
    """
    now = timezone.now()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def is_business_hours():
    """
    Check if current time is within business hours.
    """
    now = timezone.now()
    current_hour = now.hour
    
    # Business hours: 6 AM to 10 PM
    return 6 <= current_hour <= 22


def get_chat_statistics(chat_room):
    """
    Get statistics for a chat room.
    """
    from apps.chat.models import Message
    
    messages = Message.objects.filter(
        chat_room=chat_room,
        is_deleted=False
    )
    
    total_messages = messages.count()
    
    # Messages by type
    text_messages = messages.filter(message_type=Message.MessageType.TEXT).count()
    voice_messages = messages.filter(message_type=Message.MessageType.VOICE).count()
    image_messages = messages.filter(message_type=Message.MessageType.IMAGE).count()
    file_messages = messages.filter(message_type=Message.MessageType.FILE).count()
    location_messages = messages.filter(message_type=Message.MessageType.LOCATION).count()
    
    # Messages by participant
    rider_messages = messages.filter(sender=chat_room.rider).count()
    driver_messages = messages.filter(sender=chat_room.driver).count()
    
    return {
        'total_messages': total_messages,
        'message_types': {
            'text': text_messages,
            'voice': voice_messages,
            'image': image_messages,
            'file': file_messages,
            'location': location_messages,
        },
        'messages_by_participant': {
            'rider': rider_messages,
            'driver': driver_messages,
        },
        'created_at': chat_room.created_at,
        'last_activity': chat_room.last_activity,
    }
