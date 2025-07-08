from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.location.views import (
    CountryViewSet, StateViewSet, CityViewSet, ServiceZoneViewSet,
    PlaceViewSet, UserSavedPlaceViewSet, RouteViewSet,
    LocationTrackingViewSet, GeocodeViewSet, AnalyticsViewSet
)

router = DefaultRouter()
router.register(r'countries', CountryViewSet, basename='country')
router.register(r'states', StateViewSet, basename='state')
router.register(r'cities', CityViewSet, basename='city')
router.register(r'service-zones', ServiceZoneViewSet, basename='servicezone')
router.register(r'places', PlaceViewSet, basename='place')
router.register(r'saved-places', UserSavedPlaceViewSet, basename='savedplace')
router.register(r'routes', RouteViewSet, basename='route')
router.register(r'tracking', LocationTrackingViewSet, basename='tracking')
router.register(r'geocode', GeocodeViewSet, basename='geocode')
router.register(r'analytics', AnalyticsViewSet, basename='analytics')

app_name = 'location'

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
