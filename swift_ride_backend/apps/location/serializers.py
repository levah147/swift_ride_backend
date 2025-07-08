from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from apps.location.models import (
    Country, State, City, ServiceZone, Place, UserSavedPlace,
    Route, GeofenceZone, LocationHistory, PopularDestination,
    LocationSearchLog, TrafficCondition
)
 

class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'code', 'currency', 'phone_code', 'is_active']


class StateSerializer(serializers.ModelSerializer):
    country = CountrySerializer(read_only=True)

    class Meta:
        model = State
        fields = ['id', 'name', 'code', 'country', 'is_active']


class CitySerializer(serializers.ModelSerializer):
    state = StateSerializer(read_only=True)
    country_name = serializers.CharField(source='state.country.name', read_only=True)

    class Meta:
        model = City
        fields = [
            'id', 'name', 'state', 'country_name', 'population',
            'service_available', 'launch_date', 'is_active'
        ]


class ServiceZoneSerializer(GeoFeatureModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = ServiceZone
        geo_field = 'boundary'
        fields = [
            'id', 'name', 'zone_type', 'city', 'is_active',
            'base_fare_multiplier', 'surge_multiplier',
            'max_wait_time', 'priority_level'
        ]


class PlaceSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    service_zone = ServiceZoneSerializer(read_only=True)
    distance_km = serializers.DecimalField(
        max_digits=8, decimal_places=2, read_only=True
    )

    class Meta:
        model = Place
        fields = [
            'id', 'name', 'place_type', 'address', 'latitude', 'longitude',
            'city', 'service_zone', 'google_place_id', 'phone_number',
            'website', 'rating', 'pickup_count', 'dropoff_count',
            'search_count', 'is_verified', 'is_popular', 'distance_km'
        ]


class PlaceCreateSerializer(serializers.ModelSerializer):
    city_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Place
        fields = [
            'name', 'place_type', 'address', 'latitude', 'longitude',
            'city_id', 'google_place_id', 'phone_number', 'website'
        ]

    def create(self, validated_data):
        city_id = validated_data.pop('city_id')
        validated_data['city_id'] = city_id
        return super().create(validated_data)


class UserSavedPlaceSerializer(serializers.ModelSerializer):
    place = PlaceSerializer(read_only=True)
    place_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = UserSavedPlace
        fields = [
            'id', 'place', 'place_id', 'custom_name', 'is_favorite',
            'usage_count', 'last_used', 'created_at'
        ]
        read_only_fields = ['usage_count', 'last_used']


class RouteSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField()
    duration_minutes = serializers.SerializerMethodField()
    traffic_duration_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Route
        fields = [
            'id', 'distance_meters', 'duration_seconds', 'polyline',
            'origin_address', 'destination_address', 'traffic_duration_seconds',
            'traffic_condition', 'distance_km', 'duration_minutes',
            'traffic_duration_minutes', 'usage_count', 'created_at'
        ]

    def get_distance_km(self, obj):
        return obj.distance_km

    def get_duration_minutes(self, obj):
        return obj.duration_minutes

    def get_traffic_duration_minutes(self, obj):
        if obj.traffic_duration_seconds:
            return round(obj.traffic_duration_seconds / 60, 1)
        return None


class GeofenceZoneSerializer(GeoFeatureModelSerializer):
    city = CitySerializer(read_only=True)

    class Meta:
        model = GeofenceZone
        geo_field = 'boundary'
        fields = [
            'id', 'name', 'zone_type', 'description', 'city',
            'radius_meters', 'is_active', 'trigger_on_enter',
            'trigger_on_exit', 'metadata'
        ]


class LocationHistorySerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = LocationHistory
        fields = [
            'id', 'user_name', 'latitude', 'longitude', 'accuracy',
            'activity_type', 'ride', 'device_id', 'app_version',
            'created_at'
        ]
        read_only_fields = ['user_name']


class PopularDestinationSerializer(serializers.ModelSerializer):
    place = PlaceSerializer(read_only=True)

    class Meta:
        model = PopularDestination
        fields = [
            'id', 'place', 'destination_type', 'score', 'weekly_visits', 'monthly_visits',
            'peak_hours', 'peak_days', 'season', 'is_active', 'last_updated'
        ]


class LocationSearchLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    selected_place = PlaceSerializer(read_only=True)

    class Meta:
        model = LocationSearchLog
        fields = [
            'id', 'user_name', 'query', 'search_type', 'results_count',
            'selected_place', 'session_id', 'response_time_ms', 'created_at'
        ]


class TrafficConditionSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)

    class Meta:
        model = TrafficCondition
        fields = [
            'id', 'route', 'severity', 'speed_kmh', 'delay_minutes',
            'incident_type', 'description', 'expires_at', 'is_active',
            'created_at'
        ]


class LocationSearchSerializer(serializers.Serializer):
    """Serializer for location search requests"""
    query = serializers.CharField(max_length=500)
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
    city_id = serializers.IntegerField(required=False)
    place_type = serializers.CharField(max_length=20, required=False)
    limit = serializers.IntegerField(default=10, max_value=50)


class RouteRequestSerializer(serializers.Serializer):
    """Serializer for route calculation requests"""
    origin_latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    origin_longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    destination_latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    destination_longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    avoid_tolls = serializers.BooleanField(default=False)
    avoid_highways = serializers.BooleanField(default=False)


class LocationTrackingSerializer(serializers.Serializer):
    """Serializer for location tracking requests"""
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    accuracy = serializers.FloatField(required=False)
    activity_type = serializers.ChoiceField(
        choices=['idle', 'driving', 'walking', 'in_ride', 'waiting'],
        default='idle'
    )
    ride_id = serializers.IntegerField(required=False)


class NearbyPlacesSerializer(serializers.Serializer):
    """Serializer for nearby places requests"""
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    radius_km = serializers.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    place_type = serializers.CharField(max_length=20, required=False)
    limit = serializers.IntegerField(default=20, max_value=100)


class GeocodeSerializer(serializers.Serializer):
    """Serializer for geocoding requests"""
    address = serializers.CharField(max_length=500)


class ReverseGeocodeSerializer(serializers.Serializer):
    """Serializer for reverse geocoding requests"""
    latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
    longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
    
# from rest_framework import serializers
# from rest_framework_gis.serializers import GeoFeatureModelSerializer
# from apps.location.models import (
#     Country, State, City, ServiceZone, Place, UserSavedPlace,
#     Route, GeofenceZone, LocationHistory, PopularDestination,
#     LocationSearchLog, TrafficCondition
# )
 

# class CountrySerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Country
#         fields = ['id', 'name', 'code', 'currency', 'phone_code', 'is_active']


# class StateSerializer(serializers.ModelSerializer):
#     country = CountrySerializer(read_only=True)

#     class Meta:
#         model = State
#         fields = ['id', 'name', 'code', 'country', 'is_active']


# class CitySerializer(serializers.ModelSerializer):
#     state = StateSerializer(read_only=True)
#     country_name = serializers.CharField(source='state.country.name', read_only=True)

#     class Meta:
#         model = City
#         fields = [
#             'id', 'name', 'state', 'country_name', 'population',
#             'service_available', 'launch_date', 'is_active'
#         ]


# class ServiceZoneSerializer(GeoFeatureModelSerializer):
#     city = CitySerializer(read_only=True)

#     class Meta:
#         model = ServiceZone
#         geo_field = 'boundary'
#         fields = [
#             'id', 'name', 'zone_type', 'city', 'is_active',
#             'base_fare_multiplier', 'surge_multiplier',
#             'max_wait_time', 'priority_level'
#         ]


# class PlaceSerializer(serializers.ModelSerializer):
#     city = CitySerializer(read_only=True)
#     service_zone = ServiceZoneSerializer(read_only=True)
#     distance_km = serializers.DecimalField(
#         max_digits=8, decimal_places=2, read_only=True
#     )

#     class Meta:
#         model = Place
#         fields = [
#             'id', 'name', 'place_type', 'address', 'latitude', 'longitude',
#             'city', 'service_zone', 'google_place_id', 'phone_number',
#             'website', 'rating', 'pickup_count', 'dropoff_count',
#             'search_count', 'is_verified', 'is_popular', 'distance_km'
#         ]


# class PlaceCreateSerializer(serializers.ModelSerializer):
#     city_id = serializers.IntegerField(write_only=True)

#     class Meta:
#         model = Place
#         fields = [
#             'name', 'place_type', 'address', 'latitude', 'longitude',
#             'city_id', 'google_place_id', 'phone_number', 'website'
#         ]

#     def create(self, validated_data):
#         city_id = validated_data.pop('city_id')
#         validated_data['city_id'] = city_id
#         return super().create(validated_data)


# class UserSavedPlaceSerializer(serializers.ModelSerializer):
#     place = PlaceSerializer(read_only=True)
#     place_id = serializers.IntegerField(write_only=True)

#     class Meta:
#         model = UserSavedPlace
#         fields = [
#             'id', 'place', 'place_id', 'custom_name', 'is_favorite',
#             'usage_count', 'last_used', 'created_at'
#         ]
#         read_only_fields = ['usage_count', 'last_used']


# class RouteSerializer(serializers.ModelSerializer):
#     distance_km = serializers.SerializerMethodField()
#     duration_minutes = serializers.SerializerMethodField()
#     traffic_duration_minutes = serializers.SerializerMethodField()

#     class Meta:
#         model = Route
#         fields = [
#             'id', 'distance_meters', 'duration_seconds', 'polyline',
#             'origin_address', 'destination_address', 'traffic_duration_seconds',
#             'traffic_condition', 'distance_km', 'duration_minutes',
#             'traffic_duration_minutes', 'usage_count', 'created_at'
#         ]

#     def get_distance_km(self, obj):
#         return obj.distance_km

#     def get_duration_minutes(self, obj):
#         return obj.duration_minutes

#     def get_traffic_duration_minutes(self, obj):
#         if obj.traffic_duration_seconds:
#             return round(obj.traffic_duration_seconds / 60, 1)
#         return None


# class GeofenceZoneSerializer(GeoFeatureModelSerializer):
#     city = CitySerializer(read_only=True)

#     class Meta:
#         model = GeofenceZone
#         geo_field = 'boundary'
#         fields = [
#             'id', 'name', 'zone_type', 'description', 'city',
#             'radius_meters', 'is_active', 'trigger_on_enter',
#             'trigger_on_exit', 'metadata'
#         ]


# class LocationHistorySerializer(serializers.ModelSerializer):
#     user_name = serializers.CharField(source='user.get_full_name', read_only=True)

#     class Meta:
#         model = LocationHistory
#         fields = [
#             'id', 'user_name', 'latitude', 'longitude', 'accuracy',
#             'activity_type', 'ride', 'device_id', 'app_version',
#             'created_at'
#         ]
#         read_only_fields = ['user_name']


# class PopularDestinationSerializer(serializers.ModelSerializer):
#     place = PlaceSerializer(read_only=True)

#     class Meta:
#         model = PopularDestination
#         fields = [ 
#             'id', 'place', 'destination_type', 
#         model = PopularDestination
#         fields = [
#             'id', 'place', 'destination_type', 'score', 'weekly_visits', 'monthly_visits',
#             'peak_hours', 'peak_days', 'season', 'is_active', 'last_updated'
#         ]


# class LocationSearchLogSerializer(serializers.ModelSerializer):
#     user_name = serializers.CharField(source='user.get_full_name', read_only=True)
#     selected_place = PlaceSerializer(read_only=True)

#     class Meta:
#         model = LocationSearchLog
#         fields = [
#             'id', 'user_name', 'query', 'search_type', 'results_count',
#             'selected_place', 'session_id', 'response_time_ms', 'created_at'
#         ]


# class TrafficConditionSerializer(serializers.ModelSerializer):
#     route = RouteSerializer(read_only=True)

#     class Meta:
#         model = TrafficCondition
#         fields = [
#             'id', 'route', 'severity', 'speed_kmh', 'delay_minutes',
#             'incident_type', 'description', 'expires_at', 'is_active',
#             'created_at'
#         ]


# class LocationSearchSerializer(serializers.Serializer):
#     """Serializer for location search requests"""
#     query = serializers.CharField(max_length=500)
#     latitude = serializers.DecimalField(max_digits=10, decimal_places=8, required=False)
#     longitude = serializers.DecimalField(max_digits=11, decimal_places=8, required=False)
#     city_id = serializers.IntegerField(required=False)
#     place_type = serializers.CharField(max_length=20, required=False)
#     limit = serializers.IntegerField(default=10, max_value=50)


# class RouteRequestSerializer(serializers.Serializer):
#     """Serializer for route calculation requests"""
#     origin_latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
#     origin_longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
#     destination_latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
#     destination_longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
#     avoid_tolls = serializers.BooleanField(default=False)
#     avoid_highways = serializers.BooleanField(default=False)


# class LocationTrackingSerializer(serializers.Serializer):
#     """Serializer for location tracking requests"""
#     latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
#     longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
#     accuracy = serializers.FloatField(required=False)
#     activity_type = serializers.ChoiceField(
#         choices=['idle', 'driving', 'walking', 'in_ride', 'waiting'],
#         default='idle'
#     )
#     ride_id = serializers.IntegerField(required=False)


# class NearbyPlacesSerializer(serializers.Serializer):
#     """Serializer for nearby places requests"""
#     latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
#     longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
#     radius_km = serializers.DecimalField(max_digits=5, decimal_places=2, default=5.0)
#     place_type = serializers.CharField(max_length=20, required=False)
#     limit = serializers.IntegerField(default=20, max_value=100)


# class GeocodeSerializer(serializers.Serializer):
#     """Serializer for geocoding requests"""
#     address = serializers.CharField(max_length=500)


# class ReverseGeocodeSerializer(serializers.Serializer):
#     """Serializer for reverse geocoding requests"""
#     latitude = serializers.DecimalField(max_digits=10, decimal_places=8)
#     longitude = serializers.DecimalField(max_digits=11, decimal_places=8)
