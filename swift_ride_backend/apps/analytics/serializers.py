from rest_framework import serializers
from apps.analytics.models import (
    AnalyticsEvent, DailyAnalytics, UserAnalytics, 
    RideAnalytics, GeographicAnalytics, DriverPerformanceAnalytics,
    PaymentAnalytics, RevenueAnalytics, AnalyticsReport, AnalyticsSettings
)
from apps.users.serializers import UserBasicSerializer


class AnalyticsEventSerializer(serializers.ModelSerializer):
    """Serializer for analytics events"""
    
    user = UserBasicSerializer(read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    platform_display = serializers.CharField(source='get_platform_display', read_only=True)
    
    class Meta:
        model = AnalyticsEvent
        fields = [
            'id', 'user', 'session_id', 'event_type', 'event_type_display',
            'platform', 'platform_display', 'properties', 'latitude', 'longitude',
            'user_agent', 'ip_address', 'device_id', 'app_version', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DailyAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for daily analytics"""
    
    class Meta:
        model = DailyAnalytics
        fields = [
            'id', 'date', 'total_users', 'new_users', 'active_users', 'returning_users',
            'total_drivers', 'active_drivers', 'online_drivers_peak', 'avg_online_drivers',
            'total_rides', 'completed_rides', 'cancelled_rides', 'avg_ride_duration',
            'avg_wait_time', 'total_revenue', 'platform_commission', 'driver_earnings',
            'avg_ride_fare', 'app_opens', 'avg_session_duration', 'chat_messages',
            'ratings_given', 'avg_rating', 'emergency_alerts', 'safety_checks',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for user analytics"""
    
    user = UserBasicSerializer(read_only=True)
    avg_session_duration = serializers.DurationField(read_only=True)
    ride_completion_rate_as_rider = serializers.FloatField(read_only=True)
    ride_completion_rate_as_driver = serializers.FloatField(read_only=True)
    
    class Meta:
        model = UserAnalytics
        fields = [
            'id', 'user', 'total_sessions', 'total_session_duration', 'avg_session_duration',
            'last_active', 'days_since_signup', 'total_rides_as_rider', 'completed_rides_as_rider',
            'cancelled_rides_as_rider', 'ride_completion_rate_as_rider', 'total_spent',
            'avg_ride_rating_given', 'total_rides_as_driver', 'completed_rides_as_driver',
            'cancelled_rides_as_driver', 'ride_completion_rate_as_driver', 'total_earned',
            'avg_driver_rating', 'total_online_time', 'chat_messages_sent',
            'emergency_alerts_triggered', 'promotions_used', 'favorite_pickup_locations',
            'favorite_destinations', 'peak_usage_hours', 'preferred_vehicle_types',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RideAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for ride analytics"""
    
    class Meta:
        model = RideAnalytics
        fields = [
            'id', 'ride', 'request_to_acceptance_time', 'acceptance_to_pickup_time',
            'pickup_to_dropoff_time', 'total_ride_time', 'estimated_distance',
            'actual_distance', 'distance_variance', 'estimated_fare', 'final_fare',
            'surge_multiplier', 'discount_amount', 'initial_offer', 'final_agreed_price',
            'bargaining_rounds', 'bargaining_duration', 'drivers_notified',
            'drivers_viewed', 'drivers_declined', 'time_to_find_driver',
            'rider_rating', 'driver_rating', 'rider_feedback', 'driver_feedback',
            'safety_checks_completed', 'emergency_alerts', 'route_deviations',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class GeographicAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for geographic analytics"""
    
    class Meta:
        model = GeographicAnalytics
        fields = [
            'id', 'date', 'area_name', 'center_latitude', 'center_longitude',
            'radius_km', 'ride_requests', 'completed_rides', 'cancelled_rides',
            'avg_wait_time', 'active_drivers', 'avg_driver_utilization',
            'total_revenue', 'avg_fare', 'surge_events', 'avg_surge_multiplier',
            'top_pickup_points', 'top_destinations', 'popular_routes',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DriverPerformanceAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for driver performance analytics"""
    
    driver = UserBasicSerializer(read_only=True)
    utilization_rate = serializers.FloatField(read_only=True)
    earnings_per_hour = serializers.DecimalField(max_digits=8, decimal_places=2, read_only=True)
    
    class Meta:
        model = DriverPerformanceAnalytics
        fields = [
            'id', 'driver', 'date', 'online_time', 'active_time', 'idle_time',
            'utilization_rate', 'rides_completed', 'rides_cancelled', 'rides_declined',
            'total_distance', 'gross_earnings', 'net_earnings', 'earnings_per_hour',
            'tips_received', 'fuel_costs', 'avg_rating', 'total_ratings',
            'complaints_received', 'compliments_received', 'acceptance_rate',
            'completion_rate', 'avg_pickup_time', 'avg_trip_time', 'safety_incidents',
            'emergency_alerts', 'vehicle_inspections_passed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for payment analytics"""
    
    success_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = PaymentAnalytics
        fields = [
            'id', 'date', 'total_transactions', 'successful_transactions',
            'failed_transactions', 'refunded_transactions', 'success_rate',
            'total_volume', 'avg_transaction_amount', 'card_transactions',
            'card_volume', 'mobile_money_transactions', 'mobile_money_volume',
            'wallet_transactions', 'wallet_volume', 'platform_revenue',
            'processing_fees', 'disputes_opened', 'disputes_resolved',
            'chargeback_amount', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RevenueAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for revenue analytics"""
    
    class Meta:
        model = RevenueAnalytics
        fields = [
            'id', 'date', 'gross_revenue', 'ride_revenue', 'commission_revenue',
            'surge_revenue', 'driver_payouts', 'payment_processing_fees',
            'refunds_issued', 'promotional_discounts', 'net_revenue',
            'revenue_by_currency', 'revenue_growth_rate', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalyticsReportSerializer(serializers.ModelSerializer):
    """Serializer for analytics reports"""
    
    generated_by = UserBasicSerializer(read_only=True)
    report_type_display = serializers.CharField(source='get_report_type_display', read_only=True)
    format_display = serializers.CharField(source='get_format_display', read_only=True)
    
    class Meta:
        model = AnalyticsReport
        fields = [
            'id', 'name', 'report_type', 'report_type_display', 'format',
            'format_display', 'start_date', 'end_date', 'filters', 'data',
            'file_path', 'generated_by', 'generation_time', 'is_ready',
            'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'data', 'file_path', 'generated_by', 'generation_time',
            'is_ready', 'error_message', 'created_at', 'updated_at'
        ]


class AnalyticsSettingsSerializer(serializers.ModelSerializer):
    """Serializer for analytics settings"""
    
    class Meta:
        model = AnalyticsSettings
        fields = [
            'id', 'event_retention_days', 'analytics_retention_days',
            'daily_aggregation_enabled', 'real_time_analytics_enabled',
            'predictive_analytics_enabled', 'anonymize_user_data',
            'track_location_data', 'track_device_data', 'auto_generate_daily_reports',
            'auto_generate_weekly_reports', 'auto_generate_monthly_reports',
            'low_driver_supply_threshold', 'high_demand_threshold',
            'revenue_drop_threshold', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DashboardDataSerializer(serializers.Serializer):
    """Serializer for dashboard data"""
    
    summary = serializers.DictField()
    chart_data = serializers.ListField()
    period = serializers.DictField()


class ExecutiveSummarySerializer(serializers.Serializer):
    """Serializer for executive summary"""
    
    period = serializers.DictField()
    key_metrics = serializers.DictField()
    growth = serializers.DictField()
    generated_at = serializers.DateTimeField()


class RealTimeDashboardSerializer(serializers.Serializer):
    """Serializer for real-time dashboard"""
    
    timestamp = serializers.DateTimeField()
    active_metrics = serializers.DictField()
    today_metrics = serializers.DictField()
    hourly_requests = serializers.ListField()


class TrackEventSerializer(serializers.Serializer):
    """Serializer for tracking events"""
    
    event_type = serializers.ChoiceField(choices=AnalyticsEvent.EVENT_TYPES)
    properties = serializers.DictField(required=False, default=dict)
    session_id = serializers.CharField(required=False, allow_blank=True)
    platform = serializers.ChoiceField(
        choices=AnalyticsEvent.PLATFORMS, 
        default='api'
    )
    latitude = serializers.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        required=False
    )
    longitude = serializers.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        required=False
    )


class ReportGenerationSerializer(serializers.Serializer):
    """Serializer for report generation requests"""
    
    report_type = serializers.ChoiceField(choices=AnalyticsReport.REPORT_TYPES)
    format = serializers.ChoiceField(
        choices=AnalyticsReport.REPORT_FORMATS, 
        default='json'
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    filters = serializers.DictField(required=False, default=dict)
    
    def validate(self, data):
        """Validate date range"""
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date must be before end date")
        return data


class MetricsSerializer(serializers.Serializer):
    """Serializer for various metrics"""
    
    user_lifetime_value = serializers.DictField(required=False)
    driver_efficiency_score = serializers.DictField(required=False)
    market_penetration = serializers.DictField(required=False)
