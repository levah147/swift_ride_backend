from django.contrib.gis.geos import Point
from django.contrib.gis.measure import Distance
from django.utils import timezone
from apps.emergency.models import LocationShare, EmergencyAlert
from apps.users.models import CustomUser as User
import requests
import logging

logger = logging.getLogger(__name__)


class LocationService:
    """Service for handling location-related emergency operations"""
    
    @staticmethod
    def get_address_from_coordinates(latitude, longitude):
        """Get address from coordinates using reverse geocoding"""
        try:
            # Using a geocoding service (example with OpenStreetMap Nominatim)
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': latitude,
                'lon': longitude,
                'format': 'json',
                'addressdetails': 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return data.get('display_name', f"{latitude}, {longitude}")
            
        except Exception as e:
            logger.error(f"Error getting address from coordinates: {str(e)}")
            return f"{latitude}, {longitude}"
    
    @staticmethod
    def find_nearby_emergency_services(latitude, longitude, service_type='hospital', radius_km=10):
        """Find nearby emergency services"""
        try:
            # Using Overpass API to find nearby services
            overpass_url = "http://overpass-api.de/api/interpreter"
            
            # Define search queries for different service types
            queries = {
                'hospital': 'amenity=hospital',
                'police': 'amenity=police',
                'fire_station': 'amenity=fire_station',
                'pharmacy': 'amenity=pharmacy'
            }
            
            query = f"""
            [out:json][timeout:25];
            (
              node[{queries.get(service_type, 'amenity=hospital')}](around:{radius_km * 1000},{latitude},{longitude});
              way[{queries.get(service_type, 'amenity=hospital')}](around:{radius_km * 1000},{latitude},{longitude});
              relation[{queries.get(service_type, 'amenity=hospital')}](around:{radius_km * 1000},{latitude},{longitude});
            );
            out center;
            """
            
            response = requests.post(overpass_url, data=query, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            services = []
            
            for element in data.get('elements', []):
                if element.get('type') == 'node':
                    lat, lon = element.get('lat'), element.get('lon')
                elif element.get('center'):
                    lat, lon = element['center']['lat'], element['center']['lon']
                else:
                    continue
                
                name = element.get('tags', {}).get('name', 'Unknown')
                phone = element.get('tags', {}).get('phone', '')
                
                # Calculate distance
                distance = LocationService._calculate_distance(
                    latitude, longitude, lat, lon
                )
                
                services.append({
                    'name': name,
                    'latitude': lat,
                    'longitude': lon,
                    'phone': phone,
                    'distance_km': round(distance, 2),
                    'type': service_type
                })
            
            # Sort by distance
            services.sort(key=lambda x: x['distance_km'])
            return services[:10]  # Return top 10 closest
            
        except Exception as e:
            logger.error(f"Error finding nearby emergency services: {str(e)}")
            return []
    
    @staticmethod
    def _calculate_distance(lat1, lon1, lat2, lon2):
        """Calculate distance between two points in kilometers"""
        from math import radians, cos, sin, asin, sqrt
        
        # Convert decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        r = 6371  # Radius of earth in kilometers
        
        return c * r
    
    @staticmethod
    def track_emergency_location(alert_id, latitude, longitude):
        """Track location for an emergency alert"""
        try:
            alert = EmergencyAlert.objects.get(id=alert_id)
            
            # Update alert location
            alert.latitude = latitude
            alert.longitude = longitude
            alert.address = LocationService.get_address_from_coordinates(
                latitude, longitude
            )
            alert.save()
            
            # Update location shares
            location_shares = LocationShare.objects.filter(
                alert=alert,
                is_active=True
            )
            
            for share in location_shares:
                share.current_latitude = latitude
                share.current_longitude = longitude
                share.last_update = timezone.now()
                share.save()
            
            return True
            
        except EmergencyAlert.DoesNotExist:
            logger.error(f"Emergency alert {alert_id} not found")
            return False
        except Exception as e:
            logger.error(f"Error tracking emergency location: {str(e)}")
            return False
    
    @staticmethod
    def check_danger_zones(latitude, longitude):
        """Check if location is in a known danger zone"""
        # This would integrate with a database of known danger zones
        # For now, return False (safe)
        # In production, you would check against:
        # - Crime statistics
        # - Historical incident data
        # - Government safety advisories
        # - Real-time security alerts
        
        return {
            'is_danger_zone': False,
            'risk_level': 'low',
            'warnings': []
        }
    
    @staticmethod
    def get_safe_routes(start_lat, start_lon, end_lat, end_lon):
        """Get safe route recommendations"""
        try:
            # This would integrate with routing services that consider safety
            # For now, return basic route information
            
            routes = [
                {
                    'route_id': 1,
                    'safety_score': 8.5,
                    'estimated_time': 25,
                    'distance_km': 12.5,
                    'safety_features': [
                        'Well-lit streets',
                        'High police patrol frequency',
                        'CCTV coverage'
                    ],
                    'warnings': []
                }
            ]
            
            return routes
            
        except Exception as e:
            logger.error(f"Error getting safe routes: {str(e)}")
            return []
    
    @staticmethod
    def create_geofence_alert(user, latitude, longitude, radius_meters=500):
        """Create a geofence alert for user safety"""
        try:
            # This would create a virtual boundary around the user
            # and trigger alerts if they move outside it unexpectedly
            
            geofence_data = {
                'user_id': user.id,
                'center_lat': latitude,
                'center_lon': longitude,
                'radius': radius_meters,
                'created_at': timezone.now(),
                'is_active': True
            }
            
            # In production, this would be stored and monitored
            logger.info(f"Geofence created for user {user.id}")
            return geofence_data
            
        except Exception as e:
            logger.error(f"Error creating geofence: {str(e)}")
            return None
