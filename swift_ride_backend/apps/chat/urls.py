"""
URL configuration for chat app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.chat.views import ChatRoomViewSet, MessageViewSet, ChatSettingsViewSet

router = DefaultRouter()
router.register(r'rooms', ChatRoomViewSet, basename='chat-room')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'settings', ChatSettingsViewSet, basename='chat-settings')

urlpatterns = [
    path('', include(router.urls)),
]
