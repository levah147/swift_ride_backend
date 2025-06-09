"""
WebSocket routing configuration for Swift Ride project.
"""

from django.urls import path

from apps.rides.consumers import RideConsumer
from apps.chat.consumers import ChatConsumer
from apps.emergency.consumers import EmergencyConsumer  
from apps.notifications.consumers import NotificationConsumer
 
websocket_urlpatterns = [
    path('ws/rides/<str:ride_id>/', RideConsumer.as_asgi()),
    path('ws/chat/<str:room_id>/', ChatConsumer.as_asgi()),
    path('ws/notifications/<str:user_id>/', NotificationConsumer.as_asgi()),
    path('ws/emergency/<str:user_id>/', EmergencyConsumer.as_asgi()),
]
