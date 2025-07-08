from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import JSONField
from apps.common.models import BaseModel
from apps.users.models import CustomUser as User
import uuid
import math


class Country(BaseModel):
    """Country model for location hierarchy"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=3, unique=True)  # ISO 3166-1 alpha-3
    currency = models.CharField(max_length=3)  # ISO 4217
    phone_code = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    
    # Geospatial data (simplified)
    bounds_coordinates = JSONField(default=dict, blank=True)  # Store polygon coordinates as JSON
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Countries'

    def __str__(self):
        return self.name


class State(BaseModel):
    """State/Province model"""
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name='states')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    
    # Geospatial data (simplified)
    bounds_coordinates = JSONField(default=dict, blank=True)
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    class Meta:
        ordering = ['name']
        unique_together = ['country', 'code']

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class City(BaseModel):
    """City model"""
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='cities')
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    population = models.PositiveIntegerField(null=True, blank=True)
    
    # Service availability
    service_available = models.BooleanField(default=False)
    launch_date = models.DateField(null=True, blank=True)
    
    # Geospatial data (simplified)
    bounds_coordinates = JSONField(default=dict, blank=True)
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Cities'
        unique_together = ['state', 'name']

    def __str__(self):
        return f"{self.name}, {self.state.name}"


class ServiceZone(BaseModel):
    """Service zones within cities for operational management"""
    ZONE_TYPES = [
        ('standard', 'Standard Zone'),
        ('premium', 'Premium Zone'),
        ('airport', 'Airport Zone'),
        ('restricted', 'Restricted Zone'),
        ('surge', 'Surge Zone'),
    ]

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='service_zones')
    name = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES, default='standard')
    is_active = models.BooleanField(default=True)
    
    # Pricing modifiers
    base_fare_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    surge_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    
    # Operational settings
    max_wait_time = models.PositiveIntegerField(default=300)  # seconds
    priority_level = models.PositiveIntegerField(default=1)
    
    # Geospatial data (simplified)
    boundary_coordinates = JSONField(default=list, blank=True)  # Store polygon coordinates
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8)

    class Meta:
        ordering = ['city', 'name']
        unique_together = ['city', 'name']

    def __str__(self):
        return f"{self.name} - {self.city.name}"

    def contains_point(self, latitude, longitude):
        """Check if a point is within this zone - simplified implementation"""
        # This is a simplified implementation
        # For production, you'd want to use proper polygon containment algorithms
        if not self.boundary_coordinates:
            return False
        
        # Simple bounding box check for now
        # You can implement more sophisticated polygon containment later
        return True  # Placeholder


class Place(BaseModel):
    """Places of interest and saved locations"""
    PLACE_TYPES = [
        ('home', 'Home'),
        ('work', 'Work'),
        ('airport', 'Airport'),
        ('hospital', 'Hospital'),
        ('school', 'School'),
        ('mall', 'Shopping Mall'),
        ('restaurant', 'Restaurant'),
        ('hotel', 'Hotel'),
        ('landmark', 'Landmark'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    place_type = models.CharField(max_length=20, choices=PLACE_TYPES, default='other')
    address = models.TextField()
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Hierarchy
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='places')
    service_zone = models.ForeignKey(
        ServiceZone, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='places'
    )
    
    # Metadata
    google_place_id = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    
    # Usage statistics
    pickup_count = models.PositiveIntegerField(default=0)
    dropoff_count = models.PositiveIntegerField(default=0)
    search_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_popular = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-pickup_count', '-dropoff_count', 'name']
        indexes = [
            models.Index(fields=['city', 'place_type']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['is_popular', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.city.name}"

    def distance_to(self, other_place):
        """Calculate distance using Haversine formula"""
        lat1, lon1 = float(self.latitude), float(self.longitude)
        lat2, lon2 = float(other_place.latitude), float(other_place.longitude)
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in kilometers
        r = 6371
        return c * r


class UserSavedPlace(BaseModel):
    """User's saved places"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_places')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='saved_by_users')
    custom_name = models.CharField(max_length=100, blank=True)
    is_favorite = models.BooleanField(default=False)
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['user', 'place']
        ordering = ['-is_favorite', '-usage_count', '-last_used']

    def __str__(self):
        name = self.custom_name or self.place.name
        return f"{self.user.get_full_name()} - {name}"


class Route(BaseModel):
    """Route information between locations"""
    # Origin and destination coordinates
    origin_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    origin_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    destination_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    destination_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Route data
    distance_meters = models.PositiveIntegerField()
    duration_seconds = models.PositiveIntegerField()
    polyline = models.TextField()  # Encoded polyline
    
    # Route details
    origin_address = models.TextField()
    destination_address = models.TextField()
    
    # Traffic and conditions
    traffic_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    traffic_condition = models.CharField(
        max_length=20,
        choices=[
            ('light', 'Light Traffic'),
            ('moderate', 'Moderate Traffic'),
            ('heavy', 'Heavy Traffic'),
            ('severe', 'Severe Traffic'),
        ],
        default='light'
    )
    
    # Route options
    avoid_tolls = models.BooleanField(default=False)
    avoid_highways = models.BooleanField(default=False)
    
    # Caching
    expires_at = models.DateTimeField()
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['expires_at']),
            models.Index(fields=['usage_count']),
            models.Index(fields=['origin_latitude', 'origin_longitude']),
            models.Index(fields=['destination_latitude', 'destination_longitude']),
        ]

    def __str__(self):
        return f"Route: {self.distance_meters}m, {self.duration_seconds}s"

    @property
    def distance_km(self):
        return round(self.distance_meters / 1000, 2)

    @property
    def duration_minutes(self):
        return round(self.duration_seconds / 60, 1)

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class GeofenceZone(BaseModel):
    """Geofence zones for location-based triggers"""
    ZONE_TYPES = [
        ('pickup', 'Pickup Zone'),
        ('dropoff', 'Dropoff Zone'),
        ('restricted', 'Restricted Zone'),
        ('speed_limit', 'Speed Limit Zone'),
        ('notification', 'Notification Zone'),
    ]

    name = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES)
    description = models.TextField(blank=True)
    
    # Geospatial data (simplified)
    boundary_coordinates = JSONField(default=list, blank=True)  # Store polygon coordinates
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    radius_meters = models.PositiveIntegerField(null=True, blank=True)
    
    # Zone settings
    is_active = models.BooleanField(default=True)
    trigger_on_enter = models.BooleanField(default=True)
    trigger_on_exit = models.BooleanField(default=False)
    
    # Metadata
    metadata = JSONField(default=dict, blank=True)
    
    # Related locations
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='geofence_zones')

    class Meta:
        ordering = ['city', 'name']

    def __str__(self):
        return f"{self.name} ({self.zone_type})"

    def contains_point(self, latitude, longitude):
        """Check if a point is within this geofence - simplified implementation"""
        if self.radius_meters:
            # Simple circular geofence
            distance = self._calculate_distance(
                float(self.center_latitude), float(self.center_longitude),
                latitude, longitude
            )
            return distance <= self.radius_meters
        return False  # Placeholder for polygon containment
    
    def _calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance in meters using Haversine formula"""
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        return c * 6371000  # Earth radius in meters


class LocationHistory(BaseModel):
    """Track user location history for analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='location_history')
    
    # Location data
    latitude = models.DecimalField(max_digits=10, decimal_places=8)
    longitude = models.DecimalField(max_digits=11, decimal_places=8)
    accuracy = models.FloatField(null=True, blank=True)  # meters
    
    # Context
    activity_type = models.CharField(
        max_length=20,
        choices=[
            ('idle', 'Idle'),
            ('driving', 'Driving'),
            ('walking', 'Walking'),
            ('in_ride', 'In Ride'),
            ('waiting', 'Waiting'),
        ],
        default='idle'
    )
    
    # Related data
    ride = models.ForeignKey(
        'rides.Ride', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='location_history'
    )
    
    # Device info
    device_id = models.CharField(max_length=100, blank=True)
    app_version = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['ride', 'created_at']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.created_at}"


class LocationAnalytics(BaseModel):
    """Analytics data for locations and zones"""
    date = models.DateField()
    
    # Location reference
    place = models.ForeignKey(
        Place, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='analytics'
    )
    service_zone = models.ForeignKey(
        ServiceZone, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='analytics'
    )
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='analytics')
    
    # Metrics
    total_pickups = models.PositiveIntegerField(default=0)
    total_dropoffs = models.PositiveIntegerField(default=0)
    total_searches = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    
    # Time-based metrics
    peak_hour_pickups = models.PositiveIntegerField(default=0)
    peak_hour_start = models.TimeField(null=True, blank=True)
    peak_hour_end = models.TimeField(null=True, blank=True)
    
    # Performance metrics
    average_wait_time = models.PositiveIntegerField(default=0)  # seconds
    average_surge_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=1.00)
    
    # Revenue metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    average_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['-date']
        unique_together = ['date', 'place', 'service_zone', 'city']
        indexes = [
            models.Index(fields=['date', 'city']),
            models.Index(fields=['total_pickups']),
            models.Index(fields=['total_revenue']),
        ]

    def __str__(self):
        location = self.place or self.service_zone or self.city
        return f"{location} - {self.date}"


class PopularDestination(BaseModel):
    """Track popular destinations for recommendations"""
    DESTINATION_TYPES = [
        ('frequent', 'Frequently Visited'),
        ('trending', 'Trending'),
        ('seasonal', 'Seasonal'),
        ('event', 'Event-based'),
    ]

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='popularity_records')
    destination_type = models.CharField(max_length=20, choices=DESTINATION_TYPES)
    
    # Popularity metrics
    score = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    weekly_visits = models.PositiveIntegerField(default=0)
    monthly_visits = models.PositiveIntegerField(default=0)
    
    # Time-based data
    peak_hours = JSONField(default=list, blank=True)  # List of peak hours
    peak_days = JSONField(default=list, blank=True)   # List of peak days
    
    # Seasonal data
    season = models.CharField(
        max_length=20,
        choices=[
            ('spring', 'Spring'),
            ('summer', 'Summer'),
            ('autumn', 'Autumn'),
            ('winter', 'Winter'),
            ('all_year', 'All Year'),
        ],
        default='all_year'
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-score', '-weekly_visits']
        unique_together = ['place', 'destination_type', 'season']

    def __str__(self):
        return f"{self.place.name} - {self.destination_type} ({self.score})"


class LocationSearchLog(BaseModel):
    """Log location searches for analytics and improvements"""
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='location_searches'
    )
    
    # Search data
    query = models.CharField(max_length=500)
    search_type = models.CharField(
        max_length=20,
        choices=[
            ('pickup', 'Pickup Location'),
            ('destination', 'Destination'),
            ('general', 'General Search'),
        ]
    )
    
    # Results
    results_count = models.PositiveIntegerField(default=0)
    selected_place = models.ForeignKey(
        Place, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='search_selections'
    )
    
    # Context
    user_latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    user_longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    session_id = models.UUIDField(default=uuid.uuid4)
    
    # Performance
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['query']),
            models.Index(fields=['search_type']),
        ]

    def __str__(self):
        user_name = self.user.get_full_name() if self.user else "Anonymous"
        return f"{user_name}: {self.query}"


class TrafficCondition(BaseModel):
    """Real-time traffic conditions for routes"""
    SEVERITY_LEVELS = [
        ('light', 'Light'),
        ('moderate', 'Moderate'),
        ('heavy', 'Heavy'),
        ('severe', 'Severe'),
    ]

    # Location
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name='traffic_conditions')
    segment_start_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    segment_start_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    segment_end_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    segment_end_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    
    # Traffic data
    severity = models.CharField(max_length=20, choices=SEVERITY_LEVELS)
    speed_kmh = models.PositiveIntegerField()
    delay_minutes = models.PositiveIntegerField(default=0)
    
    # Incident data
    incident_type = models.CharField(
        max_length=30,
        choices=[
            ('accident', 'Accident'),
            ('construction', 'Construction'),
            ('event', 'Event'),
            ('weather', 'Weather'),
            ('congestion', 'Congestion'),
            ('other', 'Other'),
        ],
        blank=True
    )
    description = models.TextField(blank=True)
    
    # Validity
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['route', 'is_active']),
            models.Index(fields=['severity']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Traffic: {self.severity} - {self.route}"

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at