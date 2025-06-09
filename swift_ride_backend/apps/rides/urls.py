"""
URL configuration for rides app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.rides.views import RideViewSet, BargainOfferViewSet

router = DefaultRouter()
router.register(r'rides', RideViewSet, basename='ride')
router.register(r'bargain-offers', BargainOfferViewSet, basename='bargain-offer')

urlpatterns = [
    path('', include(router.urls)),
]
