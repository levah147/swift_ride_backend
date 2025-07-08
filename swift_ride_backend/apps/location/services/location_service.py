from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import Distance
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.conf import settings
from typing import Dict, List, Tuple, Optional
import requests
import hashlib
import json
from decimal import Decimal

from apps.location.models import (
    Place, ServiceZone, Route, LocationHistory, GeofenceZone,
    PopularDestination, LocationSearchLog, TrafficCondition
)
from apps.users.models import CustomUser as User
from core.utils.exceptions import ValidationError


class LocationService:
    """Service for location-related operations"""

    @staticmethod
    def search_places(
        query: str,
        user_location: Tuple[float, float] = None,
        city_id: int = None,
        place_type: str = None,
        limit: int = 10
    ) -> List[Dict]:
        """Search for places based on query"""
        try:
            places = Place.objects.filter(is_active=True)
            
            # Text search
            if query:
                places = places.filter(
                    Q(name__icontains=query) |
                    Q(address__icontains=query)
                )
            
            # Filter by city
            if city_id:
                places = places.filter(city_id=city_id)
            
            # Filter by place type
            if place_type:
                places = places.filter(place_type=place_type)
            
            # Order by relevance
            if user_location:
                user_point = Point(user_location[1], user_location[0])  # lng, lat
                places = places.extra(
                    select={
                        'distance': 'ST_Distance(location, %s)'
                    },
                    select_params=[user_point.wkt]
                ).order_by('distance', '-pickup_count', '-dropoff_count')
            else:
                places = places.order_by('-pickup_count', '-dropoff_count', 'name')
            
            # Limit results
            places = places[:limit]
            
            # Format results
            results = []
            for place in places:
                result = {
                    'id': place.id,
                    'name': place.name,
                    'address': place.address,
                    'place_type': place.place_type,
                    'latitude': float(place.latitude),
                    'longitude': float(place.longitude),
                    'city': place.city.name,
                    'is_popular': place.is_popular,
                    'pickup_count': place.pickup_count,
                    'dropoff_count': place.dropoff_count
                }
                
                if user_location:
                    distance = LocationService.calculate_distance(
                        user_location[0], user_location[1],
                        float(place.latitude), float(place.longitude)
                    )
                    result['distance_km'] = distance
                
                results.append(result)
            
            return results
            
        except Exception as e:
            raise ValidationError(f"Failed to search places: {str(e)}")

    @staticmethod
    def get_nearby_places(
        latitude: float,
        longitude: float,
        radius_km: float = 5.0,
        place_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """Get nearby places"""
        try:
            user_point = Point(longitude, latitude)
            
            places = Place.objects.filter(
                is_active=True,
                location__distance_lte=(user_point, Distance(km=radius_km))
            )
            
            if place_type:
                places = places.filter(place_type=place_type)
            
            places = places.extra(
                select={
                    'distance': 'ST_Distance(location, %s)'
                },
                select_params=[user_point.wkt]
            ).order_by('distance')[:limit]
            
            results = []
            for place in places:
                distance = LocationService.calculate_distance(
                    latitude, longitude,
                    float(place.latitude), float(place.longitude)
                )
                
                results.append({
                    'id': place.id,
                    'name': place.name,
                    'address': place.address,
                    'place_type': place.place_type,
                    'latitude': float(place.latitude),
                    'longitude': float(place.longitude),
                    'distance_km': distance,
                    'is_popular': place.is_popular
                })
            
            return results
            
        except Exception as e:
            raise ValidationError(f"Failed to get nearby places: {str(e)}")

    @staticmethod
    def geocode_address(address: str) -> Dict:
        """Geocode an address to coordinates"""
        try:
            # This would integrate with Google Geocoding API or similar
            # For now, return mock data
            
            return {
                'latitude': 0.0,
                'longitude': 0.0,
                'formatted_address': address,
                'place_id': 'mock_place_id',
                'components': {
                    'street_number': '',
                    'route': '',
                    'locality': '',
                    'administrative_area_level_1': '',
                    'country': '',
                    'postal_code': ''
                }
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to geocode address: {str(e)}")

    @staticmethod
    def reverse_geocode(latitude: float, longitude: float) -> Dict:
        """Reverse geocode coordinates to address"""
        try:
            # This would integrate with Google Reverse Geocoding API or similar
            # For now, return mock data
            
            return {
                'formatted_address': f"Address near {latitude}, {longitude}",
                'place_id': 'mock_place_id',
                'components': {
                    'street_number': '',
                    'route': '',
                    'locality': '',
                    'administrative_area_level_1': '',
                    'country': '',
                    'postal_code': ''
                }
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to reverse geocode: {str(e)}")

    @staticmethod
    def save_user_location(
        user_id: int,
        name: str,
        location_type: str,
        latitude: float,
        longitude: float,
        address: str,
        place_id: int = None
    ) -> Dict:
        """Save a location for a user"""
        try:
            user = User.objects.get(id=user_id)
            location = Point(longitude, latitude)
            
            # Check if location type already exists for user
            existing = LocationService.get_user_saved_location(user_id, location_type)
            
            if existing:
                # Update existing location
                existing.name = name
                existing.location = location
                existing.address = address
                if place_id:
                    existing.place_id = place_id
                existing.save()
                return {'message': 'Location updated successfully'}
            else:
                # Create new location
                saved_location = LocationService.create_user_saved_location(
                    user_id, name, location_type, latitude, longitude, address, place_id
                )
                return {'message': 'Location saved successfully'}
                
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def get_user_saved_location(user_id: int, location_type: str) -> Optional[Dict]:
        """Get a saved location for a user by type"""
        try:
            user = User.objects.get(id=user_id)
            saved_location = LocationService.get_user_saved_locations(user_id).filter(
                location_type=location_type
            ).first()
            if saved_location:
                return {
                    'id': saved_location.id,
                    'name': saved_location.name,
                    'location_type': saved_location.location_type,
                    'latitude': float(saved_location.latitude),
                    'longitude': float(saved_location.longitude),
                    'address': saved_location.address,
                    'place_id': saved_location.place_id
                }
            return None
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def create_user_saved_location(
        user_id: int,
        name: str,
        location_type: str,
        latitude: float,
        longitude: float,
        address: str,
        place_id: int = None
    ) -> Dict:
        """Create a new saved location for a user"""
        try:
            user = User.objects.get(id=user_id)
            location = Point(longitude, latitude)
            
            saved_location = LocationService.get_user_saved_locations(user_id).create(
                user=user,
                name=name,
                location_type=location_type,
                location=location,
                address=address,
                place_id=place_id
            )
            return {
                'id': saved_location.id,
                'name': saved_location.name,
                'location_type': saved_location.location_type,
                'latitude': float(saved_location.latitude),
                'longitude': float(saved_location.longitude),
                'address': saved_location.address,
                'place_id': saved_location.place_id
            }
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def get_user_saved_locations(user_id: int) -> List[Dict]:
        """Get all saved locations for a user"""
        try:
            user = User.objects.get(id=user_id)
            saved_locations = user.savedlocation_set.all().order_by('-usage_count', 'name')
            return [
                {
                    'id': loc.id,
                    'name': loc.name,
                    'location_type': loc.location_type,
                    'latitude': float(loc.latitude),
                    'longitude': float(loc.longitude),
                    'address': loc.address,
                    'place_id': loc.place_id
                }
                for loc in saved_locations
            ]
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def calculate_route(
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        optimize: bool = True
    ) -> Dict:
        """Calculate route between two points"""
        start_point = Point(start_lng, start_lat)
        end_point = Point(end_lng, end_lat)
        
        # Generate route hash for caching
        route_data = f"{start_lat},{start_lng}|{end_lat},{end_lng}"
        route_hash = hashlib.md5(route_data.encode()).hexdigest()
        
        # Check if route exists in cache
        cached_route = Route.objects.filter(route_hash=route_hash).first()
        if cached_route:
            cached_route.usage_count += 1
            cached_route.save()
            
            return {
                'distance_km': float(cached_route.distance_km),
                'duration_minutes': cached_route.duration_minutes,
                'route_geometry': cached_route.route_geometry,
                'base_fare': float(cached_route.base_fare),
                'surge_multiplier': float(cached_route.surge_multiplier),
                'traffic_level': cached_route.traffic_level
            }
        
        # Calculate new route (in production, use routing service)
        # For now, using simple distance calculation
        distance_km = start_point.distance(end_point) * 111  # Rough conversion to km
        duration_minutes = int(distance_km * 2)  # Rough estimate
        
        # Calculate base fare
        base_fare = LocationService._calculate_base_fare(distance_km)
        
        # Create route record
        route = Route.objects.create(
            start_location=start_point,
            end_location=end_point,
            distance_km=Decimal(str(round(distance_km, 2))),
            duration_minutes=duration_minutes,
            route_hash=route_hash,
            base_fare=base_fare,
            usage_count=1
        )
        
        return {
            'distance_km': distance_km,
            'duration_minutes': duration_minutes,
            'route_geometry': None,
            'base_fare': float(base_fare),
            'surge_multiplier': 1.0,
            'traffic_level': 'moderate'
        }

    @staticmethod
    def _calculate_base_fare(distance_km: float) -> Decimal:
        """Calculate base fare for a route"""
        # Simple fare calculation - in production, use complex pricing model
        base_rate = Decimal('2.50')  # Base fare
        per_km_rate = Decimal('1.20')  # Per km rate
        
        fare = base_rate + (Decimal(str(distance_km)) * per_km_rate)
        return round(fare, 2)

    @staticmethod
    def check_geofences(latitude: float, longitude: float) -> List[Dict]:
        """Check if location is within any geofences"""
        location = Point(longitude, latitude)
        
        active_geofences = GeofenceZone.objects.filter(
            is_active=True,
            boundary__contains=location
        ).order_by('-priority')
        
        result = []
        for geofence in active_geofences:
            # Check time-based rules
            if LocationService._is_geofence_active_now(geofence):
                result.append({
                    'id': geofence.id,
                    'name': geofence.name,
                    'type': geofence.zone_type,
                    'fare_multiplier': float(geofence.fare_multiplier),
                    'additional_fee': float(geofence.additional_fee),
                    'allow_pickup': geofence.allow_pickup,
                    'allow_dropoff': geofence.allow_dropoff,
                    'max_waiting_time': geofence.max_waiting_time,
                    'description': geofence.description
                })
        
        return result

    @staticmethod
    def _is_geofence_active_now(geofence: GeofenceZone) -> bool:
        """Check if geofence is currently active based on time rules"""
        now = timezone.now()
        
        # Check time of day
        if geofence.start_time and geofence.end_time:
            current_time = now.time()
            if not (geofence.start_time <= current_time <= geofence.end_time):
                return False
        
        # Check day of week
        if geofence.days_of_week:
            try:
                allowed_days = json.loads(geofence.days_of_week)
                current_day = now.weekday()  # 0 = Monday
                if current_day not in allowed_days:
                    return False
            except (json.JSONDecodeError, TypeError):
                pass
        
        return True

    @staticmethod
    def track_location(
        user_id: int,
        latitude: float,
        longitude: float,
        accuracy: float = None,
        activity_type: str = 'idle',
        ride_id: int = None
    ) -> LocationHistory:
        """Track user location"""
        try:
            user = User.objects.get(id=user_id)
            
            location_history = LocationHistory.objects.create(
                user=user,
                latitude=Decimal(str(latitude)),
                longitude=Decimal(str(longitude)),
                accuracy=accuracy,
                activity_type=activity_type,
                ride_id=ride_id
            )
            
            # Check geofences
            LocationService._check_geofences(user, latitude, longitude)
            
            return location_history
            
        except User.DoesNotExist:
            raise ValidationError("User not found")
        except Exception as e:
            raise ValidationError(f"Failed to track location: {str(e)}")

    @staticmethod
    def _check_geofences(user: User, latitude: float, longitude: float):
        """Check if user entered/exited any geofences"""
        try:
            point = Point(longitude, latitude)
            
            # Find active geofences containing this point
            active_geofences = GeofenceZone.objects.filter(
                is_active=True,
                boundary__contains=point
            )
            
            for geofence in active_geofences:
                if geofence.trigger_on_enter:
                    # Trigger geofence enter event
                    LocationService._trigger_geofence_event(
                        user, geofence, 'enter', latitude, longitude
                    )
            
        except Exception:
            pass  # Geofence errors shouldn't break location tracking

    @staticmethod
    def _trigger_geofence_event(
        user: User,
        geofence: GeofenceZone,
        event_type: str,
        latitude: float,
        longitude: float
    ):
        """Trigger geofence event"""
        try:
            from apps.notifications.services.notification_service import NotificationService
            
            # Send notification based on geofence type
            if geofence.zone_type == 'notification':
                NotificationService.send_notification(
                    user_id=user.id,
                    notification_type='geofence_trigger',
                    title=f'Entered {geofence.name}',
                    message=geofence.description or f'You have entered {geofence.name}',
                    data={
                        'geofence_id': geofence.id,
                        'geofence_name': geofence.name,
                        'event_type': event_type,
                        'latitude': latitude,
                        'longitude': longitude
                    }
                )
            
        except Exception:
            pass

    @staticmethod
    def log_search(
        query: str,
        search_type: str,
        user_id: int = None,
        results_count: int = 0,
        selected_place_id: int = None,
        user_location: Tuple[float, float] = None,
        response_time_ms: int = None
    ) -> LocationSearchLog:
        """Log location search for analytics"""
        try:
            user = None
            if user_id:
                user = User.objects.get(id=user_id)
            
            user_point = None
            if user_location:
                user_point = Point(user_location[1], user_location[0])
            
            selected_place = None
            if selected_place_id:
                selected_place = Place.objects.get(id=selected_place_id)
            
            search_log = LocationSearchLog.objects.create(
                user=user,
                query=query,
                search_type=search_type,
                results_count=results_count,
                selected_place=selected_place,
                user_location=user_point,
                response_time_ms=response_time_ms
            )
            
            # Update place search count if place was selected
            if selected_place:
                selected_place.search_count += 1
                selected_place.save()
            
            return search_log
            
        except Exception as e:
            # Search logging shouldn't break the search
            pass

    @staticmethod
    def get_popular_destinations(
        city_id: int = None,
        destination_type: str = 'frequent',
        limit: int = 20
    ) -> List[Dict]:
        """Get popular destinations"""
        try:
            destinations = PopularDestination.objects.filter(
                is_active=True,
                destination_type=destination_type
            ).select_related('place', 'place__city')
            
            if city_id:
                destinations = destinations.filter(place__city_id=city_id)
            
            destinations = destinations.order_by('-score', '-weekly_visits')[:limit]
            
            results = []
            for dest in destinations:
                results.append({
                    'id': dest.place.id,
                    'name': dest.place.name,
                    'address': dest.place.address,
                    'place_type': dest.place.place_type,
                    'latitude': float(dest.place.latitude),
                    'longitude': float(dest.place.longitude),
                    'city': dest.place.city.name,
                    'score': float(dest.score),
                    'weekly_visits': dest.weekly_visits,
                    'peak_hours': dest.peak_hours,
                    'peak_days': dest.peak_days
                })
            
            return results
            
        except Exception as e:
            raise ValidationError(f"Failed to get popular destinations: {str(e)}")

    @staticmethod
    def get_service_zone(latitude: float, longitude: float) -> Optional[ServiceZone]:
        """Get service zone for a location"""
        try:
            point = Point(longitude, latitude)
            
            zone = ServiceZone.objects.filter(
                is_active=True,
                boundary__contains=point
            ).first()
            
            return zone
            
        except Exception as e:
            return None

    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points in kilometers"""
        try:
            point1 = Point(lng1, lat1)
            point2 = Point(lng2, lat2)
            
            # Calculate distance using PostGIS
            distance = point1.distance(point2) * 111.32  # Convert to km (approximate)
            return round(distance, 2)
            
        except Exception as e:
            # Fallback to Haversine formula
            import math
            
            R = 6371  # Earth's radius in kilometers
            
            lat1_rad = math.radians(lat1)
            lat2_rad = math.radians(lat2)
            delta_lat = math.radians(lat2 - lat1)
            delta_lng = math.radians(lng2 - lng1)
            
            a = (math.sin(delta_lat / 2) ** 2 +
                 math.cos(lat1_rad) * math.cos(lat2_rad) *
                 math.sin(delta_lng / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            
            return round(R * c, 2)

    @staticmethod
    def get_route(
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
        avoid_tolls: bool = False,
        avoid_highways: bool = False
    ) -> Dict:
        """Get route information between two points"""
        try:
            # Check cache first
            cached_route = LocationService._get_cached_route(
                origin_lat, origin_lng, dest_lat, dest_lng
            )
            
            if cached_route:
                return cached_route
            
            # Get route from external service (Google Maps, etc.)
            route_data = LocationService._fetch_route_from_api(
                origin_lat, origin_lng, dest_lat, dest_lng,
                avoid_tolls, avoid_highways
            )
            
            # Cache the route
            LocationService._cache_route(route_data)
            
            return route_data
            
        except Exception as e:
            raise ValidationError(f"Failed to get route: {str(e)}")

    @staticmethod
    def _get_cached_route(
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float
    ) -> Optional[Dict]:
        """Get cached route if available"""
        try:
            origin_point = Point(origin_lng, origin_lat)
            dest_point = Point(dest_lng, dest_lat)
            
            # Find routes within 100m of origin and destination
            route = Route.objects.filter(
                origin__distance_lte=(origin_point, Distance(m=100)),
                destination__distance_lte=(dest_point, Distance(m=100)),
                expires_at__gt=timezone.now()
            ).first()
            
            if route:
                route.usage_count += 1
                route.save()
                
                return {
                    'distance_meters': route.distance_meters,
                    'duration_seconds': route.duration_seconds,
                    'polyline': route.polyline,
                    'origin_address': route.origin_address,
                    'destination_address': route.destination_address,
                    'traffic_duration_seconds': route.traffic_duration_seconds,
                    'traffic_condition': route.traffic_condition
                }
            
            return None
            
        except Exception:
            return None

    @staticmethod
    def _fetch_route_from_api(
        origin_lat: float, origin_lng: float,
        dest_lat: float, dest_lng: float,
        avoid_tolls: bool = False,
        avoid_highways: bool = False
    ) -> Dict:
        """Fetch route from external API"""
        # This would integrate with Google Maps, Mapbox, or other routing service
        # For now, return mock data
        
        distance = LocationService.calculate_distance(
            origin_lat, origin_lng, dest_lat, dest_lng
        )
        
        # Estimate duration (assuming 30 km/h average speed in city)
        duration_seconds = int((distance / 30) * 3600)
        
        return {
            'distance_meters': int(distance * 1000),
            'duration_seconds': duration_seconds,
            'polyline': 'mock_polyline_data',
            'origin_address': f"Origin: {origin_lat}, {origin_lng}",
            'destination_address': f"Destination: {dest_lat}, {dest_lng}",
            'traffic_duration_seconds': duration_seconds + 300,  # Add 5 min for traffic
            'traffic_condition': 'moderate'
        }

    @staticmethod
    def _cache_route(route_data: Dict):
        """Cache route data"""
        try:
            # Extract coordinates from addresses (in real implementation)
            # For now, use mock coordinates
            origin_point = Point(0, 0)  # Would extract from route_data
            dest_point = Point(0, 0)    # Would extract from route_data
            
            # Cache for 1 hour
            expires_at = timezone.now() + timezone.timedelta(hours=1)
            
            Route.objects.create(
                origin=origin_point,
                destination=dest_point,
                distance_meters=route_data['distance_meters'],
                duration_seconds=route_data['duration_seconds'],
                polyline=route_data['polyline'],
                origin_address=route_data['origin_address'],
                destination_address=route_data['destination_address'],
                traffic_duration_seconds=route_data.get('traffic_duration_seconds'),
                traffic_condition=route_data.get('traffic_condition', 'light'),
                expires_at=expires_at
            )
            
        except Exception:
            pass  # Cache failure shouldn't break the request
