"""
WebSocket routing for rides app.
"""

from django.urls import re_path
from apps.rides.consumers import RideConsumer, DriverLocationConsumer

websocket_urlpatterns = [
    re_path(r'ws/rides/(?P<ride_id>[0-9a-f-]+)/$', RideConsumer.as_asgi()),
    re_path(r'ws/driver/location/$', DriverLocationConsumer.as_asgi()),
]
