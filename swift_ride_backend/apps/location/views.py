from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.location.models import (
    Country, State, City, ServiceZone, Place, UserSavedPlace,
    Route, GeofenceZone, PopularDestination, LocationSearchLog
)
from apps.location.serializers import (
    CountrySerializer, StateSerializer, CitySerializer, ServiceZoneSerializer,
    PlaceSerializer, PlaceCreateSerializer, UserSavedPlaceSerializer,
    RouteSerializer, GeofenceZoneSerializer, PopularDestinationSerializer,
    LocationSearchSerializer, RouteRequestSerializer, LocationTrackingSerializer,
    NearbyPlacesSerializer, GeocodeSerializer, ReverseGeocodeSerializer
)
from apps.location.services.location_service import LocationService
from apps.location.services.geospatial_service import GeospatialService


class CountryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for countries"""
    queryset = Country.objects.filter(is_active=True)
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticated]


class StateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for states"""
    serializer_class = StateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = State.objects.filter(is_active=True).select_related('country')
        
        country_id = self.request.query_params.get('country_id')
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        
        return queryset


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for cities"""
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = City.objects.filter(is_active=True).select_related('state', 'state__country')
        
        state_id = self.request.query_params.get('state_id')
        if state_id:
            queryset = queryset.filter(state_id=state_id)
        
        service_available = self.request.query_params.get('service_available')
        if service_available:
            queryset = queryset.filter(service_available=True)
        
        return queryset.order_by('name')


class ServiceZoneViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for service zones"""
    serializer_class = ServiceZoneSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = ServiceZone.objects.filter(is_active=True).select_related('city')
        
        city_id = self.request.query_params.get('city_id')
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        
        zone_type = self.request.query_params.get('zone_type')
        if zone_type:
            queryset = queryset.filter(zone_type=zone_type)
        
        return queryset.order_by('city', 'name')

    @action(detail=False, methods=['get'])
    def for_location(self, request):
        """Get service zone for a specific location"""
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        
        if not latitude or not longitude:
            return Response(
                {'error': 'latitude and longitude parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            zone = GeospatialService.get_service_zone_for_point(
                float(latitude), float(longitude)
            )
            
            if zone:
                serializer = self.get_serializer(zone)
                return Response(serializer.data)
            else:
                return Response(
                    {'message': 'No service zone found for this location'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except ValueError:
            return Response(
                {'error': 'Invalid latitude or longitude'},
                status=status.HTTP_400_BAD_REQUEST
            )


class PlaceViewSet(viewsets.ModelViewSet):
    """ViewSet for places"""
    serializer_class = PlaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Place.objects.filter(is_active=True).select_related('city', 'service_zone')
        
        city_id = self.request.query_params.get('city_id')
        if city_id:
            queryset = queryset.filter(city_id=city_id)
        
        place_type = self.request.query_params.get('place_type')
        if place_type:
            queryset = queryset.filter(place_type=place_type)
        
        is_popular = self.request.query_params.get('is_popular')
        if is_popular:
            queryset = queryset.filter(is_popular=True)
        
        return queryset.order_by('-is_popular', '-pickup_count', 'name')

    def get_serializer_class(self):
        if self.action == 'create':
            return PlaceCreateSerializer
        return PlaceSerializer

    @action(detail=False, methods=['post'])
    def search(self, request):
        """Search for places"""
        serializer = LocationSearchSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                user_location = None
                if serializer.validated_data.get('latitude') and serializer.validated_data.get('longitude'):
                    user_location = (
                        float(serializer.validated_data['latitude']),
                        float(serializer.validated_data['longitude'])
                    )
                
                results = LocationService.search_places(
                    query=serializer.validated_data['query'],
                    user_location=user_location,
                    city_id=serializer.validated_data.get('city_id'),
                    place_type=serializer.validated_data.get('place_type'),
                    limit=serializer.validated_data['limit']
                )
                
                # Log the search
                LocationService.log_search(
                    query=serializer.validated_data['query'],
                    search_type='general',
                    user_id=request.user.id,
                    results_count=len(results),
                    user_location=user_location
                )
                
                return Response(results)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def nearby(self, request):
        """Get nearby places"""
        serializer = NearbyPlacesSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                results = LocationService.get_nearby_places(
                    latitude=float(serializer.validated_data['latitude']),
                    longitude=float(serializer.validated_data['longitude']),
                    radius_km=float(serializer.validated_data['radius_km']),
                    place_type=serializer.validated_data.get('place_type'),
                    limit=serializer.validated_data['limit']
                )
                
                return Response(results)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def popular(self, request):
        """Get popular destinations"""
        city_id = request.query_params.get('city_id')
        destination_type = request.query_params.get('type', 'frequent')
        limit = int(request.query_params.get('limit', 20))
        
        try:
            results = LocationService.get_popular_destinations(
                city_id=int(city_id) if city_id else None,
                destination_type=destination_type,
                limit=limit
            )
            
            return Response(results)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserSavedPlaceViewSet(viewsets.ModelViewSet):
    """ViewSet for user saved places"""
    serializer_class = UserSavedPlaceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserSavedPlace.objects.filter(
            user=self.request.user
        ).select_related('place', 'place__city').order_by('-is_favorite', '-usage_count')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """Toggle favorite status of a saved place"""
        saved_place = self.get_object()
        saved_place.is_favorite = not saved_place.is_favorite
        saved_place.save()
        
        serializer = self.get_serializer(saved_place)
        return Response(serializer.data)


class RouteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for routes"""
    queryset = Route.objects.all()
    serializer_class = RouteSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def calculate(self, request):
        """Calculate route between two points"""
        serializer = RouteRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                route_data = LocationService.get_route(
                    origin_lat=float(serializer.validated_data['origin_latitude']),
                    origin_lng=float(serializer.validated_data['origin_longitude']),
                    dest_lat=float(serializer.validated_data['destination_latitude']),
                    dest_lng=float(serializer.validated_data['destination_longitude']),
                    avoid_tolls=serializer.validated_data['avoid_tolls'],
                    avoid_highways=serializer.validated_data['avoid_highways']
                )
                
                return Response(route_data)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LocationTrackingViewSet(viewsets.ViewSet):
    """ViewSet for location tracking"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def track(self, request):
        """Track user location"""
        serializer = LocationTrackingSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                location_history = LocationService.track_location(
                    user_id=request.user.id,
                    latitude=float(serializer.validated_data['latitude']),
                    longitude=float(serializer.validated_data['longitude']),
                    accuracy=serializer.validated_data.get('accuracy'),
                    activity_type=serializer.validated_data['activity_type'],
                    ride_id=serializer.validated_data.get('ride_id')
                )
                
                return Response({
                    'message': 'Location tracked successfully',
                    'location_id': location_history.id
                })
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """Get user's location history"""
        days = int(request.query_params.get('days', 7))
        
        try:
            patterns = GeospatialService.analyze_location_patterns(
                user_id=request.user.id,
                days=days
            )
            
            return Response(patterns)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class GeocodeViewSet(viewsets.ViewSet):
    """ViewSet for geocoding services"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def geocode(self, request):
        """Geocode an address to coordinates"""
        serializer = GeocodeSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                result = LocationService.geocode_address(
                    address=serializer.validated_data['address']
                )
                
                return Response(result)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def reverse_geocode(self, request):
        """Reverse geocode coordinates to address"""
        serializer = ReverseGeocodeSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                result = LocationService.reverse_geocode(
                    latitude=float(serializer.validated_data['latitude']),
                    longitude=float(serializer.validated_data['longitude'])
                )
                
                return Response(result)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AnalyticsViewSet(viewsets.ViewSet):
    """ViewSet for location analytics"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def heat_map(self, request):
        """Get heat map data"""
        city_id = request.query_params.get('city_id')
        data_type = request.query_params.get('type', 'pickups')
        time_range = request.query_params.get('time_range', 'week')
        
        if not city_id:
            return Response(
                {'error': 'city_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            heat_data = GeospatialService.get_heat_map_data(
                city_id=int(city_id),
                data_type=data_type,
                time_range=time_range
            )
            
            return Response(heat_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def drivers_in_area(self, request):
        """Get available drivers in an area"""
        latitude = request.query_params.get('latitude')
        longitude = request.query_params.get('longitude')
        radius_km = float(request.query_params.get('radius_km', 10.0))
        limit = int(request.query_params.get('limit', 20))
        
        if not latitude or not longitude:
            return Response(
                {'error': 'latitude and longitude parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            drivers = GeospatialService.find_drivers_in_area(
                center_lat=float(latitude),
                center_lng=float(longitude),
                radius_km=radius_km,
                limit=limit
            )
            
            return Response(drivers)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def optimal_pickup(self, request):
        """Find optimal pickup location"""
        user_lat = request.data.get('user_latitude')
        user_lng = request.data.get('user_longitude')
        dest_lat = request.data.get('destination_latitude')
        dest_lng = request.data.get('destination_longitude')
        radius_km = float(request.data.get('radius_km', 2.0))
        
        if not all([user_lat, user_lng, dest_lat, dest_lng]):
            return Response(
                {'error': 'All location parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            optimal_pickup = GeospatialService.find_optimal_pickup_location(
                user_lat=float(user_lat),
                user_lng=float(user_lng),
                destination_lat=float(dest_lat),
                destination_lng=float(dest_lng),
                radius_km=radius_km
            )
            
            return Response(optimal_pickup)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
