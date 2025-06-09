"""
WebSocket consumers for real-time ride updates.
"""

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from django.utils import timezone


class RideConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time ride updates.
    """
    
    async def connect(self):
        """
        Connect to WebSocket.
        """
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.ride_group_name = f'ride_{self.ride_id}'
        
        # Join ride group
        await self.channel_layer.group_add(
            self.ride_group_name,
            self.channel_name
        )
        
        # Accept connection
        await self.accept()
        
        # Send initial ride status
        ride_status = await self.get_ride_status(self.ride_id)
        await self.send(text_data=json.dumps(ride_status))
    
    async def disconnect(self, close_code):
        """
        Disconnect from WebSocket.
        """
        # Leave ride group
        await self.channel_layer.group_discard(
            self.ride_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        """
        data = json.loads(text_data)
        message_type = data.get('type', '')
        
        # Handle different message types
        if message_type == 'location_update':
            await self.handle_location_update(data)
        elif message_type == 'status_update':
            await self.handle_status_update(data)
        elif message_type == 'bargain_offer':
            await self.handle_bargain_offer(data)
        
    async def ride_update(self, event):
        """
        Receive ride update from group and send to client.
        """
        # Send update to WebSocket
        await self.send(text_data=json.dumps(event))
    
    async def handle_location_update(self, data):
        """
        Handle location update from client.
        """
        # Update location in database
        await self.update_ride_location(
            self.ride_id,
            data.get('latitude'),
            data.get('longitude'),
            data.get('bearing')
        )
        
        # Broadcast location update to group
        await self.channel_layer.group_send(
            self.ride_group_name,
            {
                'type': 'ride_update',
                'update_type': 'location_update',
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'bearing': data.get('bearing'),
                'timestamp': str(timezone.now())
            }
        )
    
    async def handle_status_update(self, data):
        """
        Handle status update from client.
        """
        # Update status in database
        success, message = await self.update_ride_status(
            self.ride_id,
            data.get('status'),
            data.get('user_id')
        )
        
        if success:
            # Broadcast status update to group
            await self.channel_layer.group_send(
                self.ride_group_name,
                {
                    'type': 'ride_update',
                    'update_type': 'status_update',
                    'status': data.get('status'),
                    'user_id': data.get('user_id'),
                    'timestamp': str(timezone.now())
                }
            )
        else:
            # Send error message to client
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': message
            }))
    
    async def handle_bargain_offer(self, data):
        """
        Handle bargain offer from client.
        """
        # Create bargain offer in database
        offer, message = await self.create_bargain_offer(
            self.ride_id,
            data.get('user_id'),
            data.get('amount'),
            data.get('message')
        )
        
        if offer:
            # Broadcast bargain offer to group
            await self.channel_layer.group_send(
                self.ride_group_name,
                {
                    'type': 'ride_update',
                    'update_type': 'bargain_offer',
                    'offer_id': offer.get('id'),
                    'user_id': data.get('user_id'),
                    'amount': data.get('amount'),
                    'message': data.get('message'),
                    'offer_type': offer.get('offer_type'),
                    'expiry_time': offer.get('expiry_time'),
                    'timestamp': str(timezone.now())
                }
            )
        else:
            # Send error message to client
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': message
            }))
    
    @database_sync_to_async
    def get_ride_status(self, ride_id):
        """
        Get current ride status.
        """
        try:
            from apps.rides.models import Ride, TripStatus
            from apps.rides.serializers import RideSerializer
            
            ride = Ride.objects.get(id=ride_id)
            serializer = RideSerializer(ride)
            
            return {
                'type': 'initial_status',
                'ride': serializer.data
            }
        except Ride.DoesNotExist:
            return {
                'type': 'error',
                'message': 'Ride not found'
            }
    
    @database_sync_to_async
    def update_ride_location(self, ride_id, latitude, longitude, bearing=None):
        """
        Update ride location.
        """
        from apps.rides.services.ride_service import RideService
        from apps.rides.models import Ride, TripStatus
        
        try:
            ride = Ride.objects.get(id=ride_id)
            trip_status = RideService.update_ride_location(ride, latitude, longitude)
            
            if bearing is not None and trip_status:
                trip_status.driver_bearing = bearing
                trip_status.save()
                
            return True
        except Exception as e:
            print(f"Error updating location: {e}")
            return False
    
    @database_sync_to_async
    def update_ride_status(self, ride_id, status, user_id):
        """
        Update ride status.
        """
        from apps.rides.models import Ride
        from apps.users.models import CustomUser
        
        try:
            ride = Ride.objects.get(id=ride_id)
            user = CustomUser.objects.get(id=user_id)
            
            # Handle different status updates
            if status == Ride.RideStatus.DRIVER_ARRIVED:
                # Update ride status
                ride.status = status
                ride.save()
                
                # Create history entry
                from apps.rides.models import RideHistory
                RideHistory.objects.create(
                    ride=ride,
                    event_type=RideHistory.EventType.STATUS_CHANGE,
                    previous_status=Ride.RideStatus.DRIVER_ASSIGNED,
                    new_status=status
                )
                
                return True, "Status updated successfully"
                
            elif status == Ride.RideStatus.IN_PROGRESS:
                # Update ride status
                ride.status = status
                ride.pickup_time = timezone.now()
                ride.save()
                
                # Create history entry
                from apps.rides.models import RideHistory
                RideHistory.objects.create(
                    ride=ride,
                    event_type=RideHistory.EventType.STATUS_CHANGE,
                    previous_status=Ride.RideStatus.DRIVER_ARRIVED,
                    new_status=status
                )
                
                return True, "Status updated successfully"
                
            elif status == Ride.RideStatus.COMPLETED:
                from apps.rides.services.ride_service import RideService
                success, message = RideService.complete_ride(ride)
                return success, message
                
            elif status == Ride.RideStatus.CANCELLED:
                from apps.rides.services.ride_service import RideService
                success, message = RideService.cancel_ride(ride, user)
                return success, message
                
            else:
                return False, "Invalid status update"
                
        except Ride.DoesNotExist:
            return False, "Ride not found"
            
        except CustomUser.DoesNotExist:
            return False, "User not found"
            
        except Exception as e:
            print(f"Error updating status: {e}")
            return False, str(e)
    
    @database_sync_to_async
    def create_bargain_offer(self, ride_id, user_id, amount, message=None):
        """
        Create a bargain offer.
        """
        from apps.rides.models import Ride
        from apps.users.models import CustomUser
        from apps.rides.services.bargain_service import BargainService
        
        try:
            ride = Ride.objects.get(id=ride_id)
            user = CustomUser.objects.get(id=user_id)
            
            # Check if ride is in bargaining state
            if not ride.is_bargaining:
                return None, "Ride is not in bargaining state"
            
            # Create offer
            offer = BargainService.make_offer(ride, user, amount, message)
            
            return {
                'id': str(offer.id),
                'offer_type': offer.offer_type,
                'expiry_time': str(offer.expiry_time)
            }, "Offer created successfully"
            
        except Ride.DoesNotExist:
            return None, "Ride not found"
            
        except CustomUser.DoesNotExist:
            return None, "User not found"
            
        except Exception as e:
            print(f"Error creating offer: {e}")
            return None, str(e)
