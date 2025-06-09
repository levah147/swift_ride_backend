"""
URL configuration for vehicles app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.vehicles.views import (
    VehicleTypeViewSet, VehicleViewSet, VehicleDocumentViewSet, InspectionViewSet
)

router = DefaultRouter()
router.register(r'vehicle-types', VehicleTypeViewSet, basename='vehicle-type')
router.register(r'vehicles', VehicleViewSet, basename='vehicle')
router.register(r'documents', VehicleDocumentViewSet, basename='vehicle-document')
router.register(r'inspections', InspectionViewSet, basename='inspection')

urlpatterns = [
    path('', include(router.urls)),
]
