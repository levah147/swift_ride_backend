"""
Views for the chat app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
 
from apps.chat.models import ChatRoom, Message, ChatSettings
from apps.chat.serializers import (
    ChatRoomSerializer, ChatRoomListSerializer, MessageSerializer,
    MessageCreateSerializer, VoiceMessageUploadSerializer,
    FileMessageUploadSerializer, ChatSettingsSerializer
)
from apps.chat.services.chat_service import ChatService
from apps.users.models import CustomUser


class ChatRoomViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat rooms.
    """
    serializer_class = ChatRoomSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get chat rooms for the current user."""
        user = self.request.user
        return ChatRoom.objects.filter(
            Q(rider=user) | Q(driver=user),
            status=ChatRoom.RoomStatus.ACTIVE,
            is_deleted=False
        ).order_by('-last_activity')
    
    def get_serializer_class(self):
        """Get serializer class based on action."""
        if self.action == 'list':
            return ChatRoomListSerializer
        return ChatRoomSerializer
    
    @action(detail=False, methods=['post'])
    def create_or_get(self, request):
        """Create or get chat room with another user."""
        other_user_id = request.data.get('user_id')
        ride_id = request.data.get('ride_id')
        
        if not other_user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            other_user = CustomUser.objects.get(id=other_user_id)
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Determine rider and driver
        if request.user.is_rider and other_user.is_driver:
            rider, driver = request.user, other_user
        elif request.user.is_driver and other_user.is_rider:
            rider, driver = other_user, request.user
        else:
            return Response(
                {'error': 'Chat can only be created between rider and driver'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get associated ride if provided
        ride = None
        if ride_id:
            from apps.rides.models import Ride
            try:
                ride = Ride.objects.get(id=ride_id)
                # Verify user is involved in the ride
                if request.user not in [ride.rider, ride.driver]:
                    return Response(
                        {'error': 'You are not involved in this ride'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Ride.DoesNotExist:
                return Response(
                    {'error': 'Ride not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Create or get chat room
        chat_room = ChatService.get_or_create_chat_room(rider, driver, ride)
        
        return Response(
            ChatRoomSerializer(chat_room).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        """Get messages for a chat room."""
        chat_room = self.get_object()
        
        # Check if user is participant
        if request.user not in chat_room.participants:
            return Response(
                {'error': 'You are not a participant in this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get pagination parameters
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        # Get messages
        messages = ChatService.get_chat_history(chat_room, request.user, limit, offset)
        serializer = MessageSerializer(messages, many=True)
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in the chat room."""
        chat_room = self.get_object()
        
        # Check if user is participant
        if request.user not in chat_room.participants:
            return Response(
                {'error': 'You are not a participant in this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if chat room is active
        if chat_room.status != ChatRoom.RoomStatus.ACTIVE:
            return Response(
                {'error': 'Chat room is not active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MessageCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Get reply_to message if provided
            reply_to = None
            if data.get('reply_to_id'):
                try:
                    reply_to = Message.objects.get(
                        id=data['reply_to_id'],
                        chat_room=chat_room
                    )
                except Message.DoesNotExist:
                    return Response(
                        {'error': 'Reply message not found'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Send message based on type
            if data['message_type'] == Message.MessageType.LOCATION:
                message = ChatService.send_location_message(
                    chat_room,
                    request.user,
                    data['latitude'],
                    data['longitude'],
                    data.get('location_name', '')
                )
            else:
                message = ChatService.send_message(
                    chat_room,
                    request.user,
                    data['content'],
                    data['message_type'],
                    reply_to=reply_to
                )
            
            return Response(
                MessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def send_voice_message(self, request, pk=None):
        """Send a voice message in the chat room."""
        chat_room = self.get_object()
        
        # Check if user is participant
        if request.user not in chat_room.participants:
            return Response(
                {'error': 'You are not a participant in this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = VoiceMessageUploadSerializer(data=request.data)
        if serializer.is_valid():
            audio_file = serializer.validated_data['audio_file']
            duration_seconds = serializer.validated_data['duration_seconds']
            
            message, voice_note = ChatService.send_voice_message(
                chat_room,
                request.user,
                audio_file,
                duration_seconds
            )
            
            return Response(
                MessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def send_file(self, request, pk=None):
        """Send a file in the chat room."""
        chat_room = self.get_object()
        
        # Check if user is participant
        if request.user not in chat_room.participants:
            return Response(
                {'error': 'You are not a participant in this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = FileMessageUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer.validated_data['file']
            
            message, file_attachment = ChatService.send_file_message(
                chat_room,
                request.user,
                file,
                file.name
            )
            
            return Response(
                MessageSerializer(message).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark messages as read."""
        chat_room = self.get_object()
        
        # Check if user is participant
        if request.user not in chat_room.participants:
            return Response(
                {'error': 'You are not a participant in this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Mark messages as read
        count = ChatService.mark_messages_as_read(chat_room, request.user)
        
        return Response({
            'message': f'{count} messages marked as read'
        })
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a chat room."""
        chat_room = self.get_object()
        
        # Check if user is participant
        if request.user not in chat_room.participants:
            return Response(
                {'error': 'You are not a participant in this chat'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        archived_room = ChatService.archive_chat_room(chat_room)
        
        return Response(
            ChatRoomSerializer(archived_room).data
        )


class MessageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for messages.
    """
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get messages for the current user."""
        user = self.request.user
        return Message.objects.filter(
            Q(chat_room__rider=user) | Q(chat_room__driver=user),
            is_deleted=False
        ).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def delete(self, request, pk=None):
        """Delete a message."""
        message = self.get_object()
        
        success, message_text = ChatService.delete_message(message, request.user)
        
        if success:
            return Response({'message': message_text})
        else:
            return Response(
                {'error': message_text},
                status=status.HTTP_403_FORBIDDEN
            )


class ChatSettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for chat settings.
    """
    serializer_class = ChatSettingsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get chat settings for the current user."""
        return ChatSettings.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create chat settings for the current user."""
        settings, created = ChatSettings.objects.get_or_create(
            user=self.request.user
        )
        return settings
    
    def list(self, request):
        """Get chat settings for the current user."""
        settings = self.get_object()
        serializer = self.get_serializer(settings)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Update chat settings."""
        settings = self.get_object()
        serializer = self.get_serializer(settings, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
