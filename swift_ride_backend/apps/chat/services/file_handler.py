"""
Service for handling file uploads and processing in chat.
"""

import os
import uuid
import mimetypes
from PIL import Image
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings

from apps.chat.models import FileAttachment
from apps.chat.utils import compress_image, generate_thumbnail


class FileHandler:
    """
    Service for handling file operations in chat.
    """
    
    @staticmethod
    def process_file_upload(file, message):
        """
        Process uploaded file and create attachment.
        """
        try:
            # Get file information
            original_filename = file.name
            file_type = FileHandler._get_file_type(file)
            file_size = file.size
            
            # Process file based on type
            processed_file = FileHandler._process_file_by_type(file, file_type)
            
            # Create file attachment
            file_attachment = FileAttachment.objects.create(
                message=message,
                file=processed_file,
                original_filename=original_filename,
                file_type=file_type,
                file_size=file_size
            )
            
            # Generate thumbnail if it's an image
            if file_type.startswith('image/'):
                FileHandler._generate_image_thumbnail(file_attachment)
                FileHandler._extract_image_dimensions(file_attachment)
            
            return file_attachment
        
        except Exception as e:
            print(f"Error processing file upload: {e}")
            raise
    
    @staticmethod
    def _get_file_type(file):
        """
        Get MIME type of file.
        """
        # Try to guess from filename
        mime_type, _ = mimetypes.guess_type(file.name)
        
        if not mime_type:
            # Try to detect from file content
            mime_type = FileHandler._detect_mime_type_from_content(file)
        
        return mime_type or 'application/octet-stream'
    
    @staticmethod
    def _detect_mime_type_from_content(file):
        """
        Detect MIME type from file content.
        """
        try:
            # Read first few bytes
            file.seek(0)
            header = file.read(512)
            file.seek(0)
            
            # Check for common file signatures
            if header.startswith(b'\xFF\xD8\xFF'):
                return 'image/jpeg'
            elif header.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'image/png'
            elif header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                return 'image/gif'
            elif header.startswith(b'RIFF') and b'WEBP' in header[:12]:
                return 'image/webp'
            elif header.startswith(b'%PDF'):
                return 'application/pdf'
            elif header.startswith(b'PK\x03\x04'):
                return 'application/zip'
            elif header.startswith(b'ID3') or header.startswith(b'\xFF\xFB'):
                return 'audio/mpeg'
            elif header.startswith(b'OggS'):
                return 'audio/ogg'
            elif header.startswith(b'ftyp'):
                return 'video/mp4'
            
            return None
        
        except Exception as e:
            print(f"Error detecting MIME type: {e}")
            return None
    
    @staticmethod
    def _process_file_by_type(file, file_type):
        """
        Process file based on its type.
        """
        if file_type.startswith('image/'):
            return FileHandler._process_image_file(file)
        elif file_type.startswith('audio/'):
            return FileHandler._process_audio_file(file)
        elif file_type.startswith('video/'):
            return FileHandler._process_video_file(file)
        else:
            return FileHandler._process_generic_file(file)
    
    @staticmethod
    def _process_image_file(file):
        """
        Process image file (compress, optimize).
        """
        try:
            # Check if compression is needed
            max_size = getattr(settings, 'CHAT_IMAGE_MAX_SIZE', 25 * 1024 * 1024)
            
            if file.size > max_size // 2:  # Compress if larger than half max size
                compressed_file = compress_image(file)
                if compressed_file:
                    return compressed_file
            
            return file
        
        except Exception as e:
            print(f"Error processing image file: {e}")
            return file
    
    @staticmethod
    def _process_audio_file(file):
        """
        Process audio file.
        """
        # For now, return as-is
        # Could add audio processing like format conversion, compression
        return file
    
    @staticmethod
    def _process_video_file(file):
        """
        Process video file.
        """
        # For now, return as-is
        # Could add video processing like thumbnail generation, compression
        return file
    
    @staticmethod
    def _process_generic_file(file):
        """
        Process generic file.
        """
        # Basic processing for other file types
        return file
    
    @staticmethod
    def _generate_image_thumbnail(file_attachment):
        """
        Generate thumbnail for image attachment.
        """
        try:
            if not file_attachment.file_type.startswith('image/'):
                return
            
            # Generate thumbnail
            thumbnail_content = generate_thumbnail(file_attachment.file)
            
            if thumbnail_content:
                # Create thumbnail filename
                base_name = os.path.splitext(file_attachment.original_filename)[0]
                thumbnail_name = f"{base_name}_thumb.jpg"
                
                # Save thumbnail
                thumbnail_file = ContentFile(
                    thumbnail_content.getvalue(),
                    name=thumbnail_name
                )
                
                file_attachment.thumbnail = thumbnail_file
                file_attachment.save(update_fields=['thumbnail'])
        
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
    
    @staticmethod
    def _extract_image_dimensions(file_attachment):
        """
        Extract image dimensions.
        """
        try:
            if not file_attachment.file_type.startswith('image/'):
                return
            
            # Open image to get dimensions
            with Image.open(file_attachment.file) as img:
                file_attachment.width = img.width
                file_attachment.height = img.height
                file_attachment.save(update_fields=['width', 'height'])
        
        except Exception as e:
            print(f"Error extracting image dimensions: {e}")
    
    @staticmethod
    def delete_file_attachment(file_attachment):
        """
        Delete file attachment and associated files.
        """
        try:
            # Delete main file
            if file_attachment.file:
                default_storage.delete(file_attachment.file.name)
            
            # Delete thumbnail
            if file_attachment.thumbnail:
                default_storage.delete(file_attachment.thumbnail.name)
            
            # Delete database record
            file_attachment.delete()
            
            return True
        
        except Exception as e:
            print(f"Error deleting file attachment: {e}")
            return False
    
    @staticmethod
    def get_file_info(file_attachment):
        """
        Get comprehensive file information.
        """
        try:
            info = {
                'id': file_attachment.id,
                'original_filename': file_attachment.original_filename,
                'file_type': file_attachment.file_type,
                'file_size': file_attachment.file_size,
                'file_size_formatted': file_attachment.file_size_formatted,
                'file_extension': file_attachment.file_extension,
                'is_image': file_attachment.is_image,
                'url': file_attachment.file.url if file_attachment.file else None,
                'created_at': file_attachment.created_at,
            }
            
            # Add image-specific info
            if file_attachment.is_image:
                info.update({
                    'width': file_attachment.width,
                    'height': file_attachment.height,
                    'thumbnail_url': file_attachment.thumbnail.url if file_attachment.thumbnail else None,
                })
            
            return info
        
        except Exception as e:
            print(f"Error getting file info: {e}")
            return {}
    
    @staticmethod
    def validate_file_upload(file, user):
        """
        Validate file upload permissions and constraints.
        """
        try:
            # Check file size
            max_size = getattr(settings, 'CHAT_FILE_MAX_SIZE', 50 * 1024 * 1024)
            if file.size > max_size:
                return False, f"File size exceeds {max_size // (1024 * 1024)}MB limit"
            
            # Check file type
            file_type = FileHandler._get_file_type(file)
            if not FileHandler._is_file_type_allowed(file_type):
                return False, "File type not allowed"
            
            # Check user permissions
            if not FileHandler._user_can_upload_files(user):
                return False, "User not allowed to upload files"
            
            # Check daily upload limit
            if not FileHandler._check_daily_upload_limit(user):
                return False, "Daily upload limit exceeded"
            
            return True, "File upload allowed"
        
        except Exception as e:
            print(f"Error validating file upload: {e}")
            return False, "Validation error"
    
    @staticmethod
    def _is_file_type_allowed(file_type):
        """
        Check if file type is allowed.
        """
        allowed_types = getattr(settings, 'CHAT_ALLOWED_FILE_TYPES', [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'audio/mpeg', 'audio/wav', 'audio/ogg',
            'video/mp4', 'video/webm',
            'application/pdf',
            'text/plain',
        ])
        
        return file_type in allowed_types
    
    @staticmethod
    def _user_can_upload_files(user):
        """
        Check if user can upload files.
        """
        # Basic permission check
        return user.is_authenticated
    
    @staticmethod
    def _check_daily_upload_limit(user):
        """
        Check daily upload limit for user.
        """
        from datetime import datetime, timedelta
        from django.db.models import Sum
        
        try:
            # Get today's uploads
            today = datetime.now().date()
            today_uploads = FileAttachment.objects.filter(
                message__sender=user,
                created_at__date=today
            ).aggregate(
                total_size=Sum('file_size')
            )
            
            total_size = today_uploads['total_size'] or 0
            daily_limit = getattr(settings, 'CHAT_DAILY_UPLOAD_LIMIT', 500 * 1024 * 1024)  # 500MB
            
            return total_size < daily_limit
        
        except Exception as e:
            print(f"Error checking daily upload limit: {e}")
            return True  # Allow upload if check fails
    
    @staticmethod
    def cleanup_old_files(days_old=30):
        """
        Cleanup old file attachments.
        """
        from datetime import datetime, timedelta
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            old_attachments = FileAttachment.objects.filter(
                created_at__lt=cutoff_date
            )
            
            deleted_count = 0
            for attachment in old_attachments:
                if FileHandler.delete_file_attachment(attachment):
                    deleted_count += 1
            
            return deleted_count
        
        except Exception as e:
            print(f"Error cleaning up old files: {e}")
            return 0
    
    @staticmethod
    def get_storage_usage(user):
        """
        Get storage usage for user.
        """
        try:
            from django.db.models import Sum
            
            usage = FileAttachment.objects.filter(
                message__sender=user
            ).aggregate(
                total_size=Sum('file_size'),
                total_files=Count('id')
            )
            
            return {
                'total_size': usage['total_size'] or 0,
                'total_files': usage['total_files'] or 0,
                'formatted_size': FileHandler._format_file_size(usage['total_size'] or 0)
            }
        
        except Exception as e:
            print(f"Error getting storage usage: {e}")
            return {'total_size': 0, 'total_files': 0, 'formatted_size': '0 B'}
    
    @staticmethod
    def _format_file_size(size_bytes):
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
