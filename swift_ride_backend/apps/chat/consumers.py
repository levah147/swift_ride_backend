"""
WebSocket consumers for real-time chat.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat.
    """
    
    async def connect(self):
        """
        Connect to WebSocket.
        """
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Check if user is participant in the chat room
        is_participant = await self.check_user_participation(self.room_id, self.user)
        if not is_participant:
            await self.close()
            return
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Send user online status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'online',
                'timestamp': str(timezone.now())
            }
        )
    
    async def disconnect(self, close_code):
        """
        Disconnect from WebSocket.
        """
        # Send user offline status
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'user_id': str(self.user.id),
                'status': 'offline',
                'timestamp': str(timezone.now())
            }
        )
        
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            # Handle different message types
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing_indicator':
                await self.handle_typing_indicator(data)
            elif message_type == 'mark_as_read':
                await self.handle_mark_as_read(data)
            elif message_type == 'voice_message':
                await self.handle_voice_message(data)
            elif message_type == 'location_message':
                await self.handle_location_message(data)
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
    
    async def handle_chat_message(self, data):
        """
        Handle regular chat message.
        """
        content = data.get('content', '').strip()
        reply_to_id = data.get('reply_to_id')
        
        if not content:
            return
        
        # Save message to database
        message = await self.save_message(
            self.room_id,
            self.user,
            content,
            'text',
            reply_to_id
        )
        
        if message:
            # Broadcast message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': await self.serialize_message(message)
                }
            )
    
    async def handle_typing_indicator(self, data):
        """
        Handle typing indicator.
        """
        is_typing = data.get('is_typing', False)
        
        # Broadcast typing indicator to room group (excluding sender)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'typing_indicator',
                'user_id': str(self.user.id),
                'is_typing': is_typing,
                'timestamp': str(timezone.now())
            }
        )
    
    async def handle_mark_as_read(self, data):
        """
        Handle mark messages as read.
        """
        message_ids = data.get('message_ids', [])
        
        # Mark messages as read
        count = await self.mark_messages_as_read(self.room_id, self.user, message_ids)
        
        if count > 0:
            # Broadcast read receipt to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'messages_read',
                    'user_id': str(self.user.id),
                    'message_ids': message_ids,
                    'timestamp': str(timezone.now())
                }
            )
    
    async def handle_voice_message(self, data):
        """
        Handle voice message (metadata only, file uploaded separately).
        """
        voice_message_id = data.get('voice_message_id')
        duration = data.get('duration', 0)
        
        if voice_message_id:
            # Get the voice message from database
            message = await self.get_voice_message(voice_message_id)
            
            if message:
                # Broadcast voice message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'voice_message',
                        'message': await self.serialize_message(message)
                    }
                )
    
    async def handle_location_message(self, data):
        """
        Handle location message.
        """
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        location_name = data.get('location_name', '')
        
        if latitude and longitude:
            # Save location message to database
            message = await self.save_location_message(
                self.room_id,
                self.user,
                latitude,
                longitude,
                location_name
            )
            
            if message:
                # Broadcast location message to room group
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'location_message',
                        'message': await self.serialize_message(message)
                    }
                )
    
    # WebSocket event handlers
    async def chat_message(self, event):
        """
        Send chat message to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    async def voice_message(self, event):
        """
        Send voice message to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    async def location_message(self, event):
        """
        Send location message to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    async def typing_indicator(self, event):
        """
        Send typing indicator to WebSocket (excluding sender).
        """
        # Don't send typing indicator to the sender
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps(event))
    
    async def messages_read(self, event):
        """
        Send read receipt to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    async def user_status(self, event):
        """
        Send user status to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    # Database operations
    @database_sync_to_async
    def check_user_participation(self, room_id, user):
        """
        Check if user is a participant in the chat room.
        """
        from apps.chat.models import ChatRoom
        
        try:
            chat_room = ChatRoom.objects.get(room_id=room_id)
            return user in chat_room.participants
        except ChatRoom.DoesNotExist:
            return False
    
    @database_sync_to_async
    def save_message(self, room_id, sender, content, message_type, reply_to_id=None):
        """
        Save message to database.
        """
        from apps.chat.models import ChatRoom, Message
        from apps.chat.services.chat_service import ChatService
        
        try:
            chat_room = ChatRoom.objects.get(room_id=room_id)
            
            # Get reply_to message if provided
            reply_to = None
            if reply_to_id:
                try:
                    reply_to = Message.objects.get(id=reply_to_id, chat_room=chat_room)
                except Message.DoesNotExist:
                    pass
            
            message = ChatService.send_message(
                chat_room,
                sender,
                content,
                message_type,
                reply_to=reply_to
            )
            
            return message
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def save_location_message(self, room_id, sender, latitude, longitude, location_name):
        """
        Save location message to database.
        """
        from apps.chat.models import ChatRoom
        from apps.chat.services.chat_service import ChatService
        
        try:
            chat_room = ChatRoom.objects.get(room_id=room_id)
            
            message = ChatService.send_location_message(
                chat_room,
                sender,
                latitude,
                longitude,
                location_name
            )
            
            return message
        except ChatRoom.DoesNotExist:
            return None
    
    @database_sync_to_async
    def mark_messages_as_read(self, room_id, user, message_ids):
        """
        Mark messages as read.
        """
        from apps.chat.models import ChatRoom, Message
        
        try:
            chat_room = ChatRoom.objects.get(room_id=room_id)
            
            # Mark specific messages as read
            if message_ids:
                messages = Message.objects.filter(
                    id__in=message_ids,
                    chat_room=chat_room,
                    is_read=False
                ).exclude(sender=user)
                
                count = messages.count()
                messages.update(
                    is_read=True,
                    read_at=timezone.now(),
                    status=Message.MessageStatus.READ
                )
                
                return count
            else:
                # Mark all unread messages as read
                from apps.chat.services.chat_service import ChatService
                return ChatService.mark_messages_as_read(chat_room, user)
        
        except ChatRoom.DoesNotExist:
            return 0
    
    @database_sync_to_async
    def get_voice_message(self, message_id):
        """
        Get voice message from database.
        """
        from apps.chat.models import Message
        
        try:
            return Message.objects.get(id=message_id, message_type=Message.MessageType.VOICE)
        except Message.DoesNotExist:
            return None
    
    @database_sync_to_async
    def serialize_message(self, message):
        """
        Serialize message for WebSocket transmission.
        """
        from apps.chat.serializers import MessageSerializer
        
        serializer = MessageSerializer(message)
        return serializer.data
