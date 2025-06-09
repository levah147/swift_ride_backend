"""
WebSocket consumers for real-time notifications.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    """
    
    async def connect(self):
        """
        Connect to WebSocket.
        """
        self.user = self.scope['user']
        
        # Check if user is authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f'notifications_{self.user.id}'
        
        # Join user notification group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Send unread notification count
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """
        Disconnect from WebSocket.
        """
        # Leave user notification group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            if message_type == 'mark_as_read':
                await self.handle_mark_as_read(data)
            elif message_type == 'get_notifications':
                await self.handle_get_notifications(data)
        
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
    
    async def handle_mark_as_read(self, data):
        """
        Handle mark notification as read.
        """
        notification_id = data.get('notification_id')
        
        if notification_id:
            success = await self.mark_notification_as_read(notification_id)
            
            if success:
                # Send updated unread count
                unread_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count',
                    'count': unread_count
                }))
    
    async def handle_get_notifications(self, data):
        """
        Handle get notifications request.
        """
        limit = data.get('limit', 20)
        offset = data.get('offset', 0)
        unread_only = data.get('unread_only', False)
        
        notifications = await self.get_user_notifications(limit, offset, unread_only)
        
        await self.send(text_data=json.dumps({
            'type': 'notifications',
            'notifications': notifications
        }))
    
    # WebSocket event handlers
    async def new_notification(self, event):
        """
        Send new notification to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    async def notification_update(self, event):
        """
        Send notification update to WebSocket.
        """
        await self.send(text_data=json.dumps(event))
    
    # Database operations
    @database_sync_to_async
    def get_unread_count(self):
        """
        Get unread notification count for user.
        """
        from apps.notifications.services.notification_service import NotificationService
        return NotificationService.get_unread_count(self.user)
    
    @database_sync_to_async
    def mark_notification_as_read(self, notification_id):
        """
        Mark notification as read.
        """
        from apps.notifications.services.notification_service import NotificationService
        success, message = NotificationService.mark_notification_as_read(notification_id, self.user)
        return success
    
    @database_sync_to_async
    def get_user_notifications(self, limit, offset, unread_only):
        """
        Get user notifications.
        """
        from apps.notifications.services.notification_service import NotificationService
        from apps.notifications.serializers import NotificationSerializer
        
        notifications = NotificationService.get_user_notifications(
            self.user, limit, offset, unread_only
        )
        
        serializer = NotificationSerializer(notifications, many=True)
        return serializer.data
