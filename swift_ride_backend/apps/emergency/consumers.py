"""
WebSocket consumer for emergency alerts and real-time location sharing.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.emergency.models import EmergencyAlert, LocationShare, SafetyCheck
from apps.emergency.services.emergency_service import EmergencyService
from apps.emergency.services.location_service import LocationService

User = get_user_model()


class EmergencyConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for emergency alerts and real-time location sharing.
    """
    
    async def connect(self):
        """
        Connect to WebSocket and join user-specific emergency group.
        """
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.emergency_group_name = f'emergency_{self.user_id}'
        
        # Check if user exists and has permission
        user_exists = await self.check_user_exists(self.user_id)
        if not user_exists:
            await self.close()
            return
        
        # Join emergency group
        await self.channel_layer.group_add(
            self.emergency_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Send initial emergency status
        emergency_status = await self.get_emergency_status()
        await self.send(text_data=json.dumps({
            'type': 'emergency_status',
            'data': emergency_status
        }))

    async def disconnect(self, close_code):
        """
        Disconnect from WebSocket and leave emergency group.
        """
        # Leave emergency group
        await self.channel_layer.group_discard(
            self.emergency_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        """
        try:
            text_data_json = json.loads(text_data)
            message_type = text_data_json.get('type')
            
            if message_type == 'panic_button':
                # Handle panic button press
                await self.handle_panic_button(text_data_json)
            
            elif message_type == 'location_update':
                # Handle location update
                await self.handle_location_update(text_data_json)
            
            elif message_type == 'safety_check_response':
                # Handle safety check response
                await self.handle_safety_check_response(text_data_json)
            
            elif message_type == 'cancel_emergency':
                # Handle emergency cancellation
                await self.handle_cancel_emergency(text_data_json)
            
            else:
                # Unknown message type
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))
        
        except json.JSONDecodeError:
            # Invalid JSON
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON'
            }))
        
        except Exception as e:
            # General error
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))

    async def handle_panic_button(self, data):
        """
        Handle panic button press.
        """
        location_data = data.get('location', {})
        alert_type = data.get('alert_type', 'panic')
        message = data.get('message', '')
        
        # Create emergency alert
        alert = await self.create_emergency_alert(
            user_id=self.user_id,
            alert_type=alert_type,
            latitude=location_data.get('latitude'),
            longitude=location_data.get('longitude'),
            accuracy=location_data.get('accuracy'),
            message=message
        )
        
        # Send confirmation to user
        await self.send(text_data=json.dumps({
            'type': 'panic_button_confirmation',
            'alert_id': str(alert.id),
            'timestamp': alert.created_at.isoformat(),
            'message': 'Emergency alert activated'
        }))
        
        # Broadcast emergency alert to all connected clients in the group
        await self.channel_layer.group_send(
            self.emergency_group_name,
            {
                'type': 'emergency_alert',
                'alert_id': str(alert.id),
                'alert_type': alert.alert_type,
                'status': alert.status,
                'latitude': float(alert.latitude) if alert.latitude else None,
                'longitude': float(alert.longitude) if alert.longitude else None,
                'timestamp': alert.created_at.isoformat(),
                'message': alert.message
            }
        )

    async def handle_location_update(self, data):
        """
        Handle location update.
        """
        location_data = data.get('location', {})
        emergency_id = data.get('emergency_id')
        
        # Update location share
        location_share = await self.update_location_share(
            user_id=self.user_id,
            emergency_id=emergency_id,
            latitude=location_data.get('latitude'),
            longitude=location_data.get('longitude'),
            accuracy=location_data.get('accuracy'),
            speed=location_data.get('speed'),
            heading=location_data.get('heading'),
            altitude=location_data.get('altitude')
        )
        
        # Send confirmation to user
        await self.send(text_data=json.dumps({
            'type': 'location_update_confirmation',
            'location_id': str(location_share.id),
            'timestamp': location_share.updated_at.isoformat(),
            'message': 'Location updated successfully'
        }))
        
        # Broadcast location update to all connected clients in the group
        await self.channel_layer.group_send(
            self.emergency_group_name,
            {
                'type': 'location_update',
                'location_id': str(location_share.id),
                'emergency_id': str(location_share.emergency.id) if location_share.emergency else None,
                'latitude': float(location_share.latitude),
                'longitude': float(location_share.longitude),
                'accuracy': float(location_share.accuracy) if location_share.accuracy else None,
                'speed': float(location_share.speed) if location_share.speed else None,
                'heading': float(location_share.heading) if location_share.heading else None,
                'timestamp': location_share.updated_at.isoformat()
            }
        )

    async def handle_safety_check_response(self, data):
        """
        Handle safety check response.
        """
        safety_check_id = data.get('safety_check_id')
        response = data.get('response')
        
        # Update safety check
        safety_check = await self.update_safety_check(
            safety_check_id=safety_check_id,
            response=response
        )
        
        # Send confirmation to user
        await self.send(text_data=json.dumps({
            'type': 'safety_check_confirmation',
            'safety_check_id': str(safety_check.id),
            'status': safety_check.status,
            'timestamp': safety_check.updated_at.isoformat(),
            'message': 'Safety check response recorded'
        }))
        
        # Broadcast safety check update to all connected clients in the group
        await self.channel_layer.group_send(
            self.emergency_group_name,
            {
                'type': 'safety_check_update',
                'safety_check_id': str(safety_check.id),
                'status': safety_check.status,
                'response': safety_check.response,
                'timestamp': safety_check.updated_at.isoformat()
            }
        )

    async def handle_cancel_emergency(self, data):
        """
        Handle emergency cancellation.
        """
        emergency_id = data.get('emergency_id')
        reason = data.get('reason', '')
        
        # Cancel emergency alert
        alert = await self.cancel_emergency_alert(
            emergency_id=emergency_id,
            reason=reason
        )
        
        # Send confirmation to user
        await self.send(text_data=json.dumps({
            'type': 'cancel_emergency_confirmation',
            'alert_id': str(alert.id),
            'status': alert.status,
            'timestamp': alert.updated_at.isoformat(),
            'message': 'Emergency alert cancelled'
        }))
        
        # Broadcast emergency cancellation to all connected clients in the group
        await self.channel_layer.group_send(
            self.emergency_group_name,
            {
                'type': 'emergency_cancelled',
                'alert_id': str(alert.id),
                'status': alert.status,
                'reason': reason,
                'timestamp': alert.updated_at.isoformat()
            }
        )

    async def emergency_alert(self, event):
        """
        Receive emergency alert from group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'emergency_alert',
            'alert_id': event['alert_id'],
            'alert_type': event['alert_type'],
            'status': event['status'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'timestamp': event['timestamp'],
            'message': event['message']
        }))

    async def location_update(self, event):
        """
        Receive location update from group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'location_id': event['location_id'],
            'emergency_id': event['emergency_id'],
            'latitude': event['latitude'],
            'longitude': event['longitude'],
            'accuracy': event['accuracy'],
            'speed': event['speed'],
            'heading': event['heading'],
            'timestamp': event['timestamp']
        }))

    async def safety_check_update(self, event):
        """
        Receive safety check update from group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'safety_check_update',
            'safety_check_id': event['safety_check_id'],
            'status': event['status'],
            'response': event['response'],
            'timestamp': event['timestamp']
        }))

    async def emergency_cancelled(self, event):
        """
        Receive emergency cancellation from group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'emergency_cancelled',
            'alert_id': event['alert_id'],
            'status': event['status'],
            'reason': event['reason'],
            'timestamp': event['timestamp']
        }))

    async def safety_check_request(self, event):
        """
        Receive safety check request from group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'safety_check_request',
            'safety_check_id': event['safety_check_id'],
            'message': event['message'],
            'expiry_time': event['expiry_time'],
            'timestamp': event['timestamp']
        }))

    async def emergency_response_update(self, event):
        """
        Receive emergency response update from group and send to WebSocket.
        """
        await self.send(text_data=json.dumps({
            'type': 'emergency_response_update',
            'response_id': event['response_id'],
            'emergency_id': event['emergency_id'],
            'responder_type': event['responder_type'],
            'status': event['status'],
            'eta_minutes': event['eta_minutes'],
            'message': event['message'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def check_user_exists(self, user_id):
        """
        Check if user exists.
        """
        return User.objects.filter(id=user_id).exists()

    @database_sync_to_async
    def get_emergency_status(self):
        """
        Get current emergency status for user.
        """
        try:
            user = User.objects.get(id=self.user_id)
            
            # Get active emergency alerts
            active_alerts = EmergencyAlert.objects.filter(
                user=user,
                status__in=['active', 'responding']
            ).order_by('-created_at')
            
            # Get active safety checks
            active_safety_checks = SafetyCheck.objects.filter(
                user=user,
                status='pending'
            ).order_by('-created_at')
            
            # Get latest location share
            latest_location = LocationShare.objects.filter(
                user=user
            ).order_by('-updated_at').first()
            
            # Format response
            alerts = []
            for alert in active_alerts:
                alerts.append({
                    'id': str(alert.id),
                    'alert_type': alert.alert_type,
                    'status': alert.status,
                    'latitude': float(alert.latitude) if alert.latitude else None,
                    'longitude': float(alert.longitude) if alert.longitude else None,
                    'created_at': alert.created_at.isoformat(),
                    'updated_at': alert.updated_at.isoformat(),
                    'message': alert.message
                })
            
            safety_checks = []
            for check in active_safety_checks:
                safety_checks.append({
                    'id': str(check.id),
                    'status': check.status,
                    'message': check.message,
                    'created_at': check.created_at.isoformat(),
                    'expiry_time': check.expiry_time.isoformat() if check.expiry_time else None
                })
            
            location = None
            if latest_location:
                location = {
                    'id': str(latest_location.id),
                    'latitude': float(latest_location.latitude),
                    'longitude': float(latest_location.longitude),
                    'accuracy': float(latest_location.accuracy) if latest_location.accuracy else None,
                    'speed': float(latest_location.speed) if latest_location.speed else None,
                    'heading': float(latest_location.heading) if latest_location.heading else None,
                    'updated_at': latest_location.updated_at.isoformat()
                }
            
            return {
                'has_active_emergency': len(alerts) > 0,
                'has_pending_safety_check': len(safety_checks) > 0,
                'alerts': alerts,
                'safety_checks': safety_checks,
                'location': location
            }
        
        except User.DoesNotExist:
            return {
                'has_active_emergency': False,
                'has_pending_safety_check': False,
                'alerts': [],
                'safety_checks': [],
                'location': None
            }

    @database_sync_to_async
    def create_emergency_alert(self, user_id, alert_type, latitude, longitude, accuracy, message):
        """
        Create emergency alert.
        """
        emergency_service = EmergencyService()
        user = User.objects.get(id=user_id)
        
        alert = emergency_service.create_alert(
            user=user,
            alert_type=alert_type,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            message=message
        )
        
        return alert

    @database_sync_to_async
    def update_location_share(self, user_id, emergency_id, latitude, longitude, accuracy, speed, heading, altitude):
        """
        Update location share.
        """
        location_service = LocationService()
        user = User.objects.get(id=user_id)
        
        emergency = None
        if emergency_id:
            try:
                emergency = EmergencyAlert.objects.get(id=emergency_id)
            except EmergencyAlert.DoesNotExist:
                pass
        
        location_share = location_service.update_location(
            user=user,
            emergency=emergency,
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
            speed=speed,
            heading=heading,
            altitude=altitude
        )
        
        return location_share

    @database_sync_to_async
    def update_safety_check(self, safety_check_id, response):
        """
        Update safety check.
        """
        emergency_service = EmergencyService()
        
        try:
            safety_check = SafetyCheck.objects.get(id=safety_check_id)
            safety_check = emergency_service.respond_to_safety_check(
                safety_check=safety_check,
                response=response
            )
            return safety_check
        
        except SafetyCheck.DoesNotExist:
            raise ValueError(f"Safety check with ID {safety_check_id} not found")

    @database_sync_to_async
    def cancel_emergency_alert(self, emergency_id, reason):
        """
        Cancel emergency alert.
        """
        emergency_service = EmergencyService()
        
        try:
            alert = EmergencyAlert.objects.get(id=emergency_id)
            alert = emergency_service.cancel_alert(
                alert=alert,
                reason=reason
            )
            return alert
        
        except EmergencyAlert.DoesNotExist:
            raise ValueError(f"Emergency alert with ID {emergency_id} not found")
