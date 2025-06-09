"""
URL configuration for notifications app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.notifications.views import (
    NotificationViewSet, NotificationPreferenceViewSet,
    DeviceTokenViewSet, NotificationBatchViewSet
)

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='notification-preference')
router.register(r'device-tokens', DeviceTokenViewSet, basename='device-token')
router.register(r'batches', NotificationBatchViewSet, basename='notification-batch')

urlpatterns = [
    path('', include(router.urls)),
]
