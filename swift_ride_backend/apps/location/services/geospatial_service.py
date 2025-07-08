from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import Distance
from django.db.models import Q, Count, Avg, F
from typing import List, Dict, Tuple, Optional
import math
from decimal import Decimal

from apps.location.models import (
    Place, ServiceZone, GeofenceZone, LocationHistory, Route
)
from core.utils.exceptions import ValidationError


class GeospatialService:
    """Service for advanced geospatial operations"""

    @staticmethod
    def find_optimal_pickup_location(
        user_lat: float,
        user_lng: float,
        destination_lat: float,
        destination_lng: float,
        radius_km: float = 2.0
    ) -> Dict:
        """Find optimal pickup location considering traffic and accessibility"""
        try:
            user_point = Point(user_lng, user_lat)
            
            # Find nearby places that could serve as pickup points
            nearby_places = Place.objects.filter(
                is_active=True,
                location__distance_lte=(user_point, Distance(km=radius_km)),
                place_type__in=['mall', 'hotel', 'landmark', 'other']
            ).extra(
                select={
                    'distance_to_user': 'ST_Distance(location, %s)',
                    'pickup_popularity': 'pickup_count'
                },
                select_params=[user_point.wkt]
            )
            
            best_pickup = None
            best_score = 0
            
            for place in nearby_places:
                # Calculate score based on multiple factors
                distance_score = max(0, 100 - (place.distance_to_user * 10))  # Closer is better
                popularity_score = min(50, place.pickup_count / 10)  # Popular places are better
                
                # Check if it's in a good service zone
                zone = GeospatialService.get_service_zone_for_point(
                    float(place.latitude), float(place.longitude)
                )
                zone_score = 30 if zone and zone.zone_type in ['standard', 'premium'] else 0
                
                total_score = distance_score + popularity_score + zone_score
                
                if total_score > best_score:
                    best_score = total_score
                    best_pickup = place
            
            if best_pickup:
                return {
                    'place_id': best_pickup.id,
                    'name': best_pickup.name,
                    'address': best_pickup.address,
                    'latitude': float(best_pickup.latitude),
                    'longitude': float(best_pickup.longitude),
                    'distance_from_user': GeospatialService.calculate_distance(
                        user_lat, user_lng,
                        float(best_pickup.latitude), float(best_pickup.longitude)
                    ),
                    'score': best_score,
                    'walking_time_minutes': GeospatialService.estimate_walking_time(
                        user_lat, user_lng,
                        float(best_pickup.latitude), float(best_pickup.longitude)
                    )
                }
            else:
                # Return user's current location as fallback
                return {
                    'place_id': None,
                    'name': 'Current Location',
                    'address': 'Your current location',
                    'latitude': user_lat,
                    'longitude': user_lng,
                    'distance_from_user': 0,
                    'score': 50,
                    'walking_time_minutes': 0
                }
                
        except Exception as e:
            raise ValidationError(f"Failed to find optimal pickup location: {str(e)}")

    @staticmethod
    def get_service_zone_for_point(latitude: float, longitude: float) -> Optional[ServiceZone]:
        """Get service zone containing a point"""
        try:
            point = Point(longitude, latitude)
            
            zone = ServiceZone.objects.filter(
                is_active=True,
                boundary__contains=point
            ).first()
            
            return zone
            
        except Exception:
            return None

    @staticmethod
    def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """Calculate distance between two points using Haversine formula"""
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
    def estimate_walking_time(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
        """Estimate walking time in minutes (assuming 5 km/h walking speed)"""
        distance_km = GeospatialService.calculate_distance(lat1, lng1, lat2, lng2)
        walking_speed_kmh = 5.0
        time_hours = distance_km / walking_speed_kmh
        return max(1, int(time_hours * 60))

    @staticmethod
    def find_drivers_in_area(
        center_lat: float,
        center_lng: float,
        radius_km: float = 10.0,
        limit: int = 20
    ) -> List[Dict]:
        """Find available drivers in an area"""
        try:
            from apps.users.models import User
            from datetime import timedelta
            from django.utils import timezone
            
            center_point = Point(center_lng, center_lat)
            recent_time = timezone.now() - timedelta(minutes=10)
            
            # Find drivers with recent location updates
            recent_locations = LocationHistory.objects.filter(
                user__driver_profile__isnull=False,
                user__driver_profile__is_available=True,
                created_at__gte=recent_time,
                location__distance_lte=(center_point, Distance(km=radius_km))
            ).select_related('user', 'user__driver_profile').order_by(
                'user', '-created_at'
            ).distinct('user')
            
            drivers = []
            for location in recent_locations[:limit]:
                driver = location.user
                distance = GeospatialService.calculate_distance(
                    center_lat, center_lng,
                    float(location.latitude), float(location.longitude)
                )
                
                drivers.append({
                    'driver_id': driver.id,
                    'name': driver.get_full_name(),
                    'latitude': float(location.latitude),
                    'longitude': float(location.longitude),
                    'distance_km': distance,
                    'rating': float(driver.driver_profile.average_rating or 0),
                    'vehicle_type': driver.driver_profile.vehicle.vehicle_type.name if driver.driver_profile.vehicle else None,
                    'last_seen': location.created_at
                })
            
            return drivers
            
        except Exception as e:
            raise ValidationError(f"Failed to find drivers in area: {str(e)}")

    @staticmethod
    def create_service_zone(
        city_id: int,
        name: str,
        zone_type: str,
        coordinates: List[Tuple[float, float]],
        **kwargs
    ) -> ServiceZone:
        """Create a new service zone"""
        try:
            from apps.location.models import City
            
            city = City.objects.get(id=city_id)
            
            # Create polygon from coordinates
            # Coordinates should be in format [(lng, lat), ...]
            polygon_coords = [(coord[1], coord[0]) for coord in coordinates]  # Convert to (lng, lat)
            polygon = Polygon(polygon_coords)
            
            # Calculate center point
            center = polygon.centroid
            
            service_zone = ServiceZone.objects.create(
                city=city,
                name=name,
                zone_type=zone_type,
                boundary=polygon,
                center=center,
                **kwargs
            )
            
            return service_zone
            
        except Exception as e:
            raise ValidationError(f"Failed to create service zone: {str(e)}")

    @staticmethod
    def create_geofence(
        city_id: int,
        name: str,
        zone_type: str,
        coordinates: List[Tuple[float, float]],
        **kwargs
    ) -> GeofenceZone:
        """Create a new geofence zone"""
        try:
            from apps.location.models import City
            
            city = City.objects.get(id=city_id)
            
            # Create polygon from coordinates
            polygon_coords = [(coord[1], coord[0]) for coord in coordinates]
            polygon = Polygon(polygon_coords)
            
            # Calculate center point
            center = polygon.centroid
            
            geofence = GeofenceZone.objects.create(
                city=city,
                name=name,
                zone_type=zone_type,
                boundary=polygon,
                center=center,
                **kwargs
            )
            
            return geofence
            
        except Exception as e:
            raise ValidationError(f"Failed to create geofence: {str(e)}")

    @staticmethod
    def get_heat_map_data(
        city_id: int,
        data_type: str = 'pickups',
        time_range: str = 'week'
    ) -> List[Dict]:
        """Get heat map data for visualization"""
        try:
            from datetime import timedelta
            from django.utils import timezone
            
            # Calculate time range
            now = timezone.now()
            if time_range == 'day':
                start_time = now - timedelta(days=1)
            elif time_range == 'week':
                start_time = now - timedelta(weeks=1)
            elif time_range == 'month':
                start_time = now - timedelta(days=30)
            else:
                start_time = now - timedelta(weeks=1)
            
            if data_type == 'pickups':
                # Get pickup locations from ride history
                from apps.rides.models import Ride
                
                rides = Ride.objects.filter(
                    pickup_city_id=city_id,
                    created_at__gte=start_time
                ).values('pickup_latitude', 'pickup_longitude').annotate(
                    count=Count('id')
                )
                
                heat_data = []
                for ride in rides:
                    heat_data.append({
                        'latitude': float(ride['pickup_latitude']),
                        'longitude': float(ride['pickup_longitude']),
                        'intensity': ride['count']
                    })
                
                return heat_data
                
            elif data_type == 'dropoffs':
                # Get dropoff locations from ride history
                from apps.rides.models import Ride
                
                rides = Ride.objects.filter(
                    destination_city_id=city_id,
                    created_at__gte=start_time
                ).values('destination_latitude', 'destination_longitude').annotate(
                    count=Count('id')
                )
                
                heat_data = []
                for ride in rides:
                    heat_data.append({
                        'latitude': float(ride['destination_latitude']),
                        'longitude': float(ride['destination_longitude']),
                        'intensity': ride['count']
                    })
                
                return heat_data
                
            else:
                return []
                
        except Exception as e:
            raise ValidationError(f"Failed to get heat map data: {str(e)}")

    @staticmethod
    def analyze_location_patterns(user_id: int, days: int = 30) -> Dict:
        """Analyze user's location patterns"""
        try:
            from datetime import timedelta
            from django.utils import timezone
            
            start_date = timezone.now() - timedelta(days=days)
            
            locations = LocationHistory.objects.filter(
                user_id=user_id,
                created_at__gte=start_date
            ).order_by('created_at')
            
            if not locations.exists():
                return {'patterns': [], 'frequent_locations': [], 'travel_stats': {}}
            
            # Find frequent locations (clustering nearby points)
            frequent_locations = GeospatialService._cluster_locations(locations)
            
            # Analyze travel patterns
            travel_stats = GeospatialService._analyze_travel_stats(locations)
            
            # Find time-based patterns
            patterns = GeospatialService._find_time_patterns(locations)
            
            return {
                'patterns': patterns,
                'frequent_locations': frequent_locations,
                'travel_stats': travel_stats
            }
            
        except Exception as e:
            raise ValidationError(f"Failed to analyze location patterns: {str(e)}")

    @staticmethod
    def _cluster_locations(locations, radius_meters: float = 200) -> List[Dict]:
        """Cluster nearby locations to find frequent places"""
        clusters = []
        processed = set()
        
        for i, location in enumerate(locations):
            if i in processed:
                continue
                
            cluster_locations = [location]
            processed.add(i)
            
            # Find nearby locations
            for j, other_location in enumerate(locations):
                if j in processed or i == j:
                    continue
                    
                distance = GeospatialService.calculate_distance(
                    float(location.latitude), float(location.longitude),
                    float(other_location.latitude), float(other_location.longitude)
                ) * 1000  # Convert to meters
                
                if distance <= radius_meters:
                    cluster_locations.append(other_location)
                    processed.add(j)
            
            if len(cluster_locations) >= 3:  # Minimum visits to be considered frequent
                # Calculate cluster center
                avg_lat = sum(float(loc.latitude) for loc in cluster_locations) / len(cluster_locations)
                avg_lng = sum(float(loc.longitude) for loc in cluster_locations) / len(cluster_locations)
                
                clusters.append({
                    'latitude': avg_lat,
                    'longitude': avg_lng,
                    'visit_count': len(cluster_locations),
                    'first_visit': min(loc.created_at for loc in cluster_locations),
                    'last_visit': max(loc.created_at for loc in cluster_locations)
                })
        
        return sorted(clusters, key=lambda x: x['visit_count'], reverse=True)

    @staticmethod
    def _analyze_travel_stats(locations) -> Dict:
        """Analyze travel statistics"""
        if len(locations) < 2:
            return {}
        
        total_distance = 0
        max_distance = 0
        
        for i in range(1, len(locations)):
            prev_loc = locations[i-1]
            curr_loc = locations[i]
            
            distance = GeospatialService.calculate_distance(
                float(prev_loc.latitude), float(prev_loc.longitude),
                float(curr_loc.latitude), float(curr_loc.longitude)
            )
            
            total_distance += distance
            max_distance = max(max_distance, distance)
        
        return {
            'total_distance_km': round(total_distance, 2),
            'average_distance_per_trip': round(total_distance / (len(locations) - 1), 2),
            'max_distance_km': round(max_distance, 2),
            'total_locations_recorded': len(locations)
        }

    @staticmethod
    def _find_time_patterns(locations) -> List[Dict]:
        """Find time-based location patterns"""
        patterns = []
        
        # Group by hour of day
        hourly_patterns = {}
        for location in locations:
            hour = location.created_at.hour
            if hour not in hourly_patterns:
                hourly_patterns[hour] = []
            hourly_patterns[hour].append(location)
        
        # Find most active hours
        for hour, hour_locations in hourly_patterns.items():
            if len(hour_locations) >= 5:  # Minimum occurrences
                patterns.append({
                    'type': 'hourly',
                    'hour': hour,
                    'location_count': len(hour_locations),
                    'description': f"Active around {hour}:00"
                })
        
        return patterns
