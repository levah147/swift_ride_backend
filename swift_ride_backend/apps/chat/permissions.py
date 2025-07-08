"""
Permissions for chat app.
"""

from rest_framework import permissions
from django.db.models import Q

from apps.chat.models import ChatRoom, Message


class IsChatParticipant(permissions.BasePermission):
    """
    Permission to check if user is a participant in the chat room.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user is participant in chat room."""
        if isinstance(obj, ChatRoom):
            return request.user in obj.participants
        elif isinstance(obj, Message):
            return request.user in obj.chat_room.participants
        return False


class IsMessageSender(permissions.BasePermission):
    """
    Permission to check if user is the sender of the message.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user is the message sender."""
        if isinstance(obj, Message):
            return obj.sender == request.user
        return False


class CanDeleteMessage(permissions.BasePermission):
    """
    Permission to check if user can delete a message.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can delete the message."""
        if isinstance(obj, Message):
            # User can delete their own messages or admin can delete any
            return obj.sender == request.user or request.user.is_staff
        return False


class CanModerateChatRoom(permissions.BasePermission):
    """
    Permission to check if user can moderate chat rooms.
    """
    
    def has_permission(self, request, view):
        """Check if user can moderate chat rooms."""
        return request.user.is_staff or request.user.is_superuser


class IsActiveChatRoom(permissions.BasePermission):
    """
    Permission to check if chat room is active.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if chat room is active."""
        if isinstance(obj, ChatRoom):
            return obj.status == ChatRoom.RoomStatus.ACTIVE
        elif isinstance(obj, Message):
            return obj.chat_room.status == ChatRoom.RoomStatus.ACTIVE
        return False


class CanCreateChatRoom(permissions.BasePermission):
    """
    Permission to check if user can create chat rooms.
    """
    
    def has_permission(self, request, view):
        """Check if user can create chat rooms."""
        # Only authenticated users can create chat rooms
        if not request.user.is_authenticated:
            return False
        
        # Check if user is either a rider or driver
        return hasattr(request.user, 'rider_profile') or hasattr(request.user, 'driver_profile')


class CanSendMessage(permissions.BasePermission):
    """
    Permission to check if user can send messages in a chat room.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can send messages."""
        if isinstance(obj, ChatRoom):
            # Check if user is participant and chat room is active
            return (
                request.user in obj.participants and 
                obj.status == ChatRoom.RoomStatus.ACTIVE
            )
        return False


class CanViewChatHistory(permissions.BasePermission):
    """
    Permission to check if user can view chat history.
    """
    
    def has_object_permission(self, request, view, obj):
        """Check if user can view chat history."""
        if isinstance(obj, ChatRoom):
            return request.user in obj.participants
        return False


class IsNotBlocked(permissions.BasePermission):
    """
    Permission to check if user is not blocked from chatting.
    """
    
    def has_permission(self, request, view):
        """Check if user is not blocked."""
        # Check if user has any active blocks
        # This would integrate with a user blocking system
        return True  # Placeholder implementation


class CanUploadFiles(permissions.BasePermission):
    """
    Permission to check if user can upload files in chat.
    """
    
    def has_permission(self, request, view):
        """Check if user can upload files."""
        # Check user's file upload permissions
        # Could be based on user type, subscription, etc.
        return request.user.is_authenticated


class CanSendVoiceMessages(permissions.BasePermission):
    """
    Permission to check if user can send voice messages.
    """
    
    def has_permission(self, request, view):
        """Check if user can send voice messages."""
        # Check user's voice message permissions
        return request.user.is_authenticated


class CanAccessChatSettings(permissions.BasePermission):
    """
    Permission to check if user can access chat settings.
    """
    
    def has_permission(self, request, view):
        """Check if user can access chat settings."""
        return request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access specific chat settings."""
        from apps.chat.models import ChatSettings
        if isinstance(obj, ChatSettings):
            return obj.user == request.user
        return False
