from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from apps.common.models import BaseModel
from decimal import Decimal
import uuid

User = get_user_model()


class AnalyticsEvent(BaseModel):
    """Model for tracking analytics events"""
    
    EVENT_TYPES = [
        ('user_signup', 'User Signup'),
        ('user_login', 'User Login'),
        ('ride_request', 'Ride Request'),
        ('ride_completed', 'Ride Completed'),
        ('ride_cancelled', 'Ride Cancelled'),
        ('payment_made', 'Payment Made'),
        ('driver_online', 'Driver Online'),
        ('driver_offline', 'Driver Offline'),
        ('app_open', 'App Open'),
        ('app_close', 'App Close'),
        ('search_location', 'Search Location'),
        ('view_profile', 'View Profile'),
        ('emergency_triggered', 'Emergency Triggered'),
        ('chat_message', 'Chat Message'),
        ('rating_given', 'Rating Given'),
        ('promotion_used', 'Promotion Used'),
    ]
    
    PLATFORMS = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web'),
        ('api', 'API'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='analytics_events',
        null=True, 
        blank=True
    )
    session_id = models.CharField(max_length=100, null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    platform = models.CharField(max_length=10, choices=PLATFORMS, default='api')
    
    # Event data
    properties = models.JSONField(default=dict, blank=True)
    
    # Location data
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True
    )
    
    # Device/Browser info
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    app_version = models.CharField(max_length=20, null=True, blank=True)
    
    class Meta:
        db_table = 'analytics_events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['platform', 'created_at']),
            models.Index(fields=['session_id']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.user or 'Anonymous'} - {self.created_at}"


class DailyAnalytics(BaseModel):
    """Model for daily aggregated analytics"""
    
    date = models.DateField(unique=True)
    
    # User metrics
    total_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    returning_users = models.PositiveIntegerField(default=0)
    
    # Driver metrics
    total_drivers = models.PositiveIntegerField(default=0)
    active_drivers = models.PositiveIntegerField(default=0)
    online_drivers_peak = models.PositiveIntegerField(default=0)
    avg_online_drivers = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Ride metrics
    total_rides = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    cancelled_rides = models.PositiveIntegerField(default=0)
    avg_ride_duration = models.DurationField(null=True, blank=True)
    avg_wait_time = models.DurationField(null=True, blank=True)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    platform_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    driver_earnings = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_ride_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Engagement metrics
    app_opens = models.PositiveIntegerField(default=0)
    avg_session_duration = models.DurationField(null=True, blank=True)
    chat_messages = models.PositiveIntegerField(default=0)
    ratings_given = models.PositiveIntegerField(default=0)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Emergency metrics
    emergency_alerts = models.PositiveIntegerField(default=0)
    safety_checks = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'daily_analytics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.date}"


class UserAnalytics(BaseModel):
    """Model for user-specific analytics"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='analytics'
    )
    
    # Activity metrics
    total_sessions = models.PositiveIntegerField(default=0)
    total_session_duration = models.DurationField(default=timezone.timedelta(0))
    last_active = models.DateTimeField(null=True, blank=True)
    days_since_signup = models.PositiveIntegerField(default=0)
    
    # Ride metrics (for riders)
    total_rides_as_rider = models.PositiveIntegerField(default=0)
    completed_rides_as_rider = models.PositiveIntegerField(default=0)
    cancelled_rides_as_rider = models.PositiveIntegerField(default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_ride_rating_given = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    # Driver metrics (for drivers)
    total_rides_as_driver = models.PositiveIntegerField(default=0)
    completed_rides_as_driver = models.PositiveIntegerField(default=0)
    cancelled_rides_as_driver = models.PositiveIntegerField(default=0)
    total_earned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_driver_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_online_time = models.DurationField(default=timezone.timedelta(0))
    
    # Engagement metrics
    chat_messages_sent = models.PositiveIntegerField(default=0)
    emergency_alerts_triggered = models.PositiveIntegerField(default=0)
    promotions_used = models.PositiveIntegerField(default=0)
    
    # Behavioral metrics
    favorite_pickup_locations = models.JSONField(default=list, blank=True)
    favorite_destinations = models.JSONField(default=list, blank=True)
    peak_usage_hours = models.JSONField(default=list, blank=True)
    preferred_vehicle_types = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'user_analytics'
    
    def __str__(self):
        return f"Analytics for {self.user.get_full_name()}"
    
    @property
    def avg_session_duration(self):
        if self.total_sessions > 0:
            return self.total_session_duration / self.total_sessions
        return timezone.timedelta(0)
    
    @property
    def ride_completion_rate_as_rider(self):
        if self.total_rides_as_rider > 0:
            return (self.completed_rides_as_rider / self.total_rides_as_rider) * 100
        return 0
    
    @property
    def ride_completion_rate_as_driver(self):
        if self.total_rides_as_driver > 0:
            return (self.completed_rides_as_driver / self.total_rides_as_driver) * 100
        return 0


class RideAnalytics(BaseModel):
    """Model for ride-specific analytics"""
    
    ride = models.OneToOneField(
        'rides.Ride', 
        on_delete=models.CASCADE, 
        related_name='analytics'
    )
    
    # Timing metrics
    request_to_acceptance_time = models.DurationField(null=True, blank=True)
    acceptance_to_pickup_time = models.DurationField(null=True, blank=True)
    pickup_to_dropoff_time = models.DurationField(null=True, blank=True)
    total_ride_time = models.DurationField(null=True, blank=True)
    
    # Distance metrics
    estimated_distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    actual_distance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    distance_variance = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    
    # Pricing metrics
    estimated_fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    final_fare = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    surge_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    discount_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Bargaining metrics
    initial_offer = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    final_agreed_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    bargaining_rounds = models.PositiveIntegerField(default=0)
    bargaining_duration = models.DurationField(null=True, blank=True)
    
    # Driver matching metrics
    drivers_notified = models.PositiveIntegerField(default=0)
    drivers_viewed = models.PositiveIntegerField(default=0)
    drivers_declined = models.PositiveIntegerField(default=0)
    time_to_find_driver = models.DurationField(null=True, blank=True)
    
    # Quality metrics
    rider_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    driver_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    rider_feedback = models.TextField(blank=True, null=True)
    driver_feedback = models.TextField(blank=True, null=True)
    
    # Safety metrics
    safety_checks_completed = models.PositiveIntegerField(default=0)
    emergency_alerts = models.PositiveIntegerField(default=0)
    route_deviations = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'ride_analytics'
    
    def __str__(self):
        return f"Analytics for Ride {self.ride.id}"


class GeographicAnalytics(BaseModel):
    """Model for geographic analytics"""
    
    date = models.DateField()
    area_name = models.CharField(max_length=100)
    
    # Location data
    center_latitude = models.DecimalField(max_digits=10, decimal_places=8)
    center_longitude = models.DecimalField(max_digits=11, decimal_places=8)
    radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    
    # Demand metrics
    ride_requests = models.PositiveIntegerField(default=0)
    completed_rides = models.PositiveIntegerField(default=0)
    cancelled_rides = models.PositiveIntegerField(default=0)
    avg_wait_time = models.DurationField(null=True, blank=True)
    
    # Supply metrics
    active_drivers = models.PositiveIntegerField(default=0)
    avg_driver_utilization = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Financial metrics
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    avg_fare = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    surge_events = models.PositiveIntegerField(default=0)
    avg_surge_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.0)
    
    # Popular routes
    top_pickup_points = models.JSONField(default=list, blank=True)
    top_destinations = models.JSONField(default=list, blank=True)
    popular_routes = models.JSONField(default=list, blank=True)
    
    class Meta:
        db_table = 'geographic_analytics'
        unique_together = ['date', 'area_name']
        ordering = ['-date', 'area_name']
    
    def __str__(self):
        return f"Geographic Analytics - {self.area_name} - {self.date}"


class DriverPerformanceAnalytics(BaseModel):
    """Model for driver performance analytics"""
    
    driver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='driver_performance'
    )
    date = models.DateField()
    
    # Activity metrics
    online_time = models.DurationField(default=timezone.timedelta(0))
    active_time = models.DurationField(default=timezone.timedelta(0))  # Time with passengers
    idle_time = models.DurationField(default=timezone.timedelta(0))
    
    # Ride metrics
    rides_completed = models.PositiveIntegerField(default=0)
    rides_cancelled = models.PositiveIntegerField(default=0)
    rides_declined = models.PositiveIntegerField(default=0)
    total_distance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Financial metrics
    gross_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tips_received = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fuel_costs = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
    # Quality metrics
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings = models.PositiveIntegerField(default=0)
    complaints_received = models.PositiveIntegerField(default=0)
    compliments_received = models.PositiveIntegerField(default=0)
    
    # Efficiency metrics
    acceptance_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_pickup_time = models.DurationField(null=True, blank=True)
    avg_trip_time = models.DurationField(null=True, blank=True)
    
    # Safety metrics
    safety_incidents = models.PositiveIntegerField(default=0)
    emergency_alerts = models.PositiveIntegerField(default=0)
    vehicle_inspections_passed = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'driver_performance_analytics'
        unique_together = ['driver', 'date']
        ordering = ['-date', 'driver']
    
    def __str__(self):
        return f"Driver Performance - {self.driver.get_full_name()} - {self.date}"
    
    @property
    def utilization_rate(self):
        if self.online_time.total_seconds() > 0:
            return (self.active_time.total_seconds() / self.online_time.total_seconds()) * 100
        return 0
    
    @property
    def earnings_per_hour(self):
        if self.online_time.total_seconds() > 0:
            hours = self.online_time.total_seconds() / 3600
            return self.gross_earnings / Decimal(str(hours))
        return Decimal('0')


class PaymentAnalytics(BaseModel):
    """Model for payment analytics"""
    
    date = models.DateField()
    
    # Transaction metrics
    total_transactions = models.PositiveIntegerField(default=0)
    successful_transactions = models.PositiveIntegerField(default=0)
    failed_transactions = models.PositiveIntegerField(default=0)
    refunded_transactions = models.PositiveIntegerField(default=0)
    
    # Volume metrics
    total_volume = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_transaction_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment method breakdown
    card_transactions = models.PositiveIntegerField(default=0)
    card_volume = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    mobile_money_transactions = models.PositiveIntegerField(default=0)
    mobile_money_volume = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wallet_transactions = models.PositiveIntegerField(default=0)
    wallet_volume = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Revenue metrics
    platform_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    processing_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Dispute metrics
    disputes_opened = models.PositiveIntegerField(default=0)
    disputes_resolved = models.PositiveIntegerField(default=0)
    chargeback_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'payment_analytics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Payment Analytics - {self.date}"
    
    @property
    def success_rate(self):
        if self.total_transactions > 0:
            return (self.successful_transactions / self.total_transactions) * 100
        return 0


class RevenueAnalytics(BaseModel):
    """Model for revenue analytics"""
    
    date = models.DateField()
    
    # Gross revenue
    gross_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ride_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    surge_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Costs
    driver_payouts = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_processing_fees = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refunds_issued = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    promotional_discounts = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Net revenue
    net_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Metrics by currency
    revenue_by_currency = models.JSONField(default=dict, blank=True)
    
    # Growth metrics
    revenue_growth_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'revenue_analytics'
        ordering = ['-date']
    
    def __str__(self):
        return f"Revenue Analytics - {self.date}"
    
    def calculate_net_revenue(self):
        """Calculate net revenue"""
        self.net_revenue = (
            self.gross_revenue - 
            self.driver_payouts - 
            self.payment_processing_fees - 
            self.refunds_issued - 
            self.promotional_discounts
        )


class PredictiveAnalytics(BaseModel):
    """Model for predictive analytics and forecasting"""
    
    date = models.DateField()
    prediction_type = models.CharField(max_length=50)
    
    # Predictions
    predicted_demand = models.JSONField(default=dict, blank=True)
    predicted_supply = models.JSONField(default=dict, blank=True)
    predicted_revenue = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    predicted_surge_areas = models.JSONField(default=list, blank=True)
    
    # Model metadata
    model_version = models.CharField(max_length=20)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=4, default=0)
    training_data_period = models.CharField(max_length=50)
    
    # Actual vs predicted (filled after the fact)
    actual_values = models.JSONField(default=dict, blank=True)
    accuracy_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    
    class Meta:
        db_table = 'predictive_analytics'
        unique_together = ['date', 'prediction_type']
        ordering = ['-date']
    
    def __str__(self):
        return f"Prediction - {self.prediction_type} - {self.date}"


class AnalyticsReport(BaseModel):
    """Model for generated analytics reports"""
    
    REPORT_TYPES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('quarterly', 'Quarterly Report'),
        ('yearly', 'Yearly Report'),
        ('custom', 'Custom Report'),
    ]
    
    REPORT_FORMATS = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    format = models.CharField(max_length=10, choices=REPORT_FORMATS, default='json')
    
    # Report parameters
    start_date = models.DateField()
    end_date = models.DateField()
    filters = models.JSONField(default=dict, blank=True)
    
    # Report data
    data = models.JSONField(default=dict, blank=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    
    # Generation info
    generated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='generated_reports'
    )
    generation_time = models.DurationField(null=True, blank=True)
    
    # Status
    is_ready = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'analytics_reports'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report: {self.name} ({self.report_type})"


class AnalyticsSettings(BaseModel):
    """Model for analytics configuration"""
    
    # Data retention
    event_retention_days = models.PositiveIntegerField(default=365)
    analytics_retention_days = models.PositiveIntegerField(default=1095)  # 3 years
    
    # Aggregation settings
    daily_aggregation_enabled = models.BooleanField(default=True)
    real_time_analytics_enabled = models.BooleanField(default=True)
    predictive_analytics_enabled = models.BooleanField(default=False)
    
    # Privacy settings
    anonymize_user_data = models.BooleanField(default=True)
    track_location_data = models.BooleanField(default=True)
    track_device_data = models.BooleanField(default=True)
    
    # Reporting settings
    auto_generate_daily_reports = models.BooleanField(default=True)
    auto_generate_weekly_reports = models.BooleanField(default=True)
    auto_generate_monthly_reports = models.BooleanField(default=True)
    
    # Alert thresholds
    low_driver_supply_threshold = models.PositiveIntegerField(default=5)
    high_demand_threshold = models.PositiveIntegerField(default=50)
    revenue_drop_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    
    class Meta:
        db_table = 'analytics_settings'
        verbose_name = 'Analytics Settings'
        verbose_name_plural = 'Analytics Settings'
    
    def __str__(self):
        return "Analytics Settings"
    
    @classmethod
    def get_settings(cls):
        """Get or create analytics settings"""
        settings, created = cls.objects.get_or_create(id=1)
        return settings
