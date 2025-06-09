"""
Admin configuration for chat models.
"""

from django.contrib import admin
from django.utils.html import format_html

from apps.chat.models import (
    ChatRoom, Message, VoiceNote, FileAttachment, 
    MessageStatus, ChatModerationLog, ChatSettings
)


class MessageInline(admin.TabularInline):
    """
    Inline admin for Message.
    """
    model = Message
    extra = 0
    readonly_fields = ['sender', 'message_type', 'status', 'created_at']
    fields = ['sender', 'message_type', 'content', 'status', 'is_read', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """
    Admin for ChatRoom model.
    """
    list_display = (
        'room_id', 'rider', 'driver', 'room_type', 'status', 
        'last_activity', 'message_count', 'created_at'
    )
    list_filter = ('room_type', 'status', 'is_encrypted', 'created_at')
    search_fields = ('room_id', 'rider__phone_number', 'driver__phone_number')
    readonly_fields = ('room_id', 'created_at', 'updated_at', 'last_activity')
    date_hierarchy = 'created_at'
    inlines = [MessageInline]
    
    def message_count(self, obj):
        """Get message count for the chat room."""
        return obj.messages.filter(is_deleted=False).count()
    
    message_count.short_description = 'Messages'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """
    Admin for Message model.
    """
    list_display = (
        'id', 'chat_room', 'sender', 'message_type', 'status',
        'is_read', 'content_preview', 'created_at'
    )
    list_filter = ('message_type', 'status', 'is_read', 'created_at')
    search_fields = ('chat_room__room_id', 'sender__phone_number', 'content')
    readonly_fields = ('created_at', 'updated_at', 'delivered_at', 'read_at')
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        """Show content preview."""
        if obj.content:
            preview = obj.content[:50]
            if len(obj.content) > 50:
                preview += '...'
            return preview
        return '-'
    
    content_preview.short_description = 'Content'


@admin.register(VoiceNote)
class VoiceNoteAdmin(admin.ModelAdmin):
    """
    Admin for VoiceNote model.
    """
    list_display = (
        'id', 'message', 'duration_formatted', 'file_size_formatted',
        'is_transcribed', 'created_at'
    )
    list_filter = ('is_transcribed', 'created_at')
    search_fields = ('message__chat_room__room_id', 'transcription')
    readonly_fields = ('created_at', 'updated_at', 'duration_formatted', 'file_size_formatted')


@admin.register(FileAttachment)
class FileAttachmentAdmin(admin.ModelAdmin):
    """
    Admin for FileAttachment model.
    """
    list_display = (
        'id', 'message', 'original_filename', 'file_type',
        'file_size_formatted', 'is_image', 'created_at'
    )
    list_filter = ('file_type', 'created_at')
    search_fields = ('message__chat_room__room_id', 'original_filename')
    readonly_fields = ('created_at', 'updated_at', 'file_size_formatted', 'is_image')


@admin.register(ChatModerationLog)
class ChatModerationLogAdmin(admin.ModelAdmin):
    """
    Admin for ChatModerationLog model.
    """
    list_display = (
        'id', 'chat_room', 'action_type', 'moderator', 
        'automated', 'created_at'
    )
    list_filter = ('action_type', 'automated', 'created_at')
    search_fields = ('chat_room__room_id', 'reason')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'


@admin.register(ChatSettings)
class ChatSettingsAdmin(admin.ModelAdmin):
    """
    Admin for ChatSettings model.
    """
    list_display = (
        'user', 'message_notifications', 'voice_message_notifications',
        'read_receipts', 'auto_delete_messages'
    )
    list_filter = (
        'message_notifications', 'voice_message_notifications', 
        'read_receipts', 'auto_delete_messages'
    )
    search_fields = ('user__phone_number',)
