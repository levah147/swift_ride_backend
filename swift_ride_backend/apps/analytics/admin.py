from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from apps.analytics.models import (
    AnalyticsEvent, DailyAnalytics, UserAnalytics, 
    RideAnalytics, GeographicAnalytics, DriverPerformanceAnalytics,
    PaymentAnalytics, RevenueAnalytics, PredictiveAnalytics,
    AnalyticsReport, AnalyticsSettings
)


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = [
        'event_type', 'user', 'platform', 'session_id', 
        'ip_address', 'created_at'
    ]
    list_filter = [
        'event_type', 'platform', 'created_at'
    ]
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name',
        'session_id', 'ip_address', 'device_id'
    ]
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Event Information', {
            'fields': ('id', 'event_type', 'user', 'session_id', 'platform')
        }),
        ('Event Data', {
            'fields': ('properties',)
        }),
        ('Location', {
            'fields': ('latitude', 'longitude')
        }),
        ('Device Information', {
            'fields': ('user_agent', 'ip_address', 'device_id', 'app_version')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(DailyAnalytics)
class DailyAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_users', 'new_users', 'active_users',
        'total_rides', 'completed_rides', 'total_revenue_display'
    ]
    list_filter = ['date']
    search_fields = ['date']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('User Metrics', {
            'fields': (
                'total_users', 'new_users', 'active_users', 'returning_users'
            )
        }),
        ('Driver Metrics', {
            'fields': (
                'total_drivers', 'active_drivers', 'online_drivers_peak', 'avg_online_drivers'
            )
        }),
        ('Ride Metrics', {
            'fields': (
                'total_rides', 'completed_rides', 'cancelled_rides',
                'avg_ride_duration', 'avg_wait_time'
            )
        }),
        ('Financial Metrics', {
            'fields': (
                'total_revenue', 'platform_commission', 'driver_earnings', 'avg_ride_fare'
            )
        }),
        ('Engagement Metrics', {
            'fields': (
                'app_opens', 'avg_session_duration', 'chat_messages',
                'ratings_given', 'avg_rating'
            )
        }),
        ('Safety Metrics', {
            'fields': ('emergency_alerts', 'safety_checks')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_revenue_display(self, obj):
        return f"${obj.total_revenue:,.2f}"
    total_revenue_display.short_description = 'Total Revenue'


@admin.register(UserAnalytics)
class UserAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'total_sessions', 'last_active', 'total_rides_as_rider',
        'total_rides_as_driver', 'total_spent_display'
    ]
    list_filter = ['last_active', 'user__user_type']
    search_fields = [
        'user__phone_number', 'user__first_name', 'user__last_name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'avg_session_duration',
        'ride_completion_rate_as_rider', 'ride_completion_rate_as_driver'
    ]
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Activity Metrics', {
            'fields': (
                'total_sessions', 'total_session_duration', 'avg_session_duration',
                'last_active', 'days_since_signup'
            )
        }),
        ('Rider Metrics', {
            'fields': (
                'total_rides_as_rider', 'completed_rides_as_rider',
                'cancelled_rides_as_rider', 'ride_completion_rate_as_rider',
                'total_spent', 'avg_ride_rating_given'
            )
        }),
        ('Driver Metrics', {
            'fields': (
                'total_rides_as_driver', 'completed_rides_as_driver',
                'cancelled_rides_as_driver', 'ride_completion_rate_as_driver',
                'total_earned', 'avg_driver_rating', 'total_online_time'
            )
        }),
        ('Engagement', {
            'fields': (
                'chat_messages_sent', 'emergency_alerts_triggered', 'promotions_used'
            )
        }),
        ('Behavioral Data', {
            'fields': (
                'favorite_pickup_locations', 'favorite_destinations',
                'peak_usage_hours', 'preferred_vehicle_types'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_spent_display(self, obj):
        return f"${obj.total_spent:,.2f}"
    total_spent_display.short_description = 'Total Spent'


@admin.register(RideAnalytics)
class RideAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'ride', 'total_ride_time', 'actual_distance', 'final_fare',
        'rider_rating', 'driver_rating'
    ]
    list_filter = ['ride__status', 'ride__created_at']
    search_fields = ['ride__id']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Ride Information', {
            'fields': ('ride',)
        }),
        ('Timing Metrics', {
            'fields': (
                'request_to_acceptance_time', 'acceptance_to_pickup_time',
                'pickup_to_dropoff_time', 'total_ride_time'
            )
        }),
        ('Distance Metrics', {
            'fields': ('estimated_distance', 'actual_distance', 'distance_variance')
        }),
        ('Pricing Metrics', {
            'fields': (
                'estimated_fare', 'final_fare', 'surge_multiplier', 'discount_amount'
            )
        }),
        ('Bargaining Metrics', {
            'fields': (
                'initial_offer', 'final_agreed_price', 'bargaining_rounds', 'bargaining_duration'
            )
        }),
        ('Driver Matching', {
            'fields': (
                'drivers_notified', 'drivers_viewed', 'drivers_declined', 'time_to_find_driver'
            )
        }),
        ('Quality Metrics', {
            'fields': ('rider_rating', 'driver_rating', 'rider_feedback', 'driver_feedback')
        }),
        ('Safety Metrics', {
            'fields': ('safety_checks_completed', 'emergency_alerts', 'route_deviations')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(GeographicAnalytics)
class GeographicAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'area_name', 'date', 'ride_requests', 'completed_rides',
        'active_drivers', 'total_revenue_display'
    ]
    list_filter = ['date', 'area_name']
    search_fields = ['area_name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Location Information', {
            'fields': ('date', 'area_name', 'center_latitude', 'center_longitude', 'radius_km')
        }),
        ('Demand Metrics', {
            'fields': ('ride_requests', 'completed_rides', 'cancelled_rides', 'avg_wait_time')
        }),
        ('Supply Metrics', {
            'fields': ('active_drivers', 'avg_driver_utilization')
        }),
        ('Financial Metrics', {
            'fields': ('total_revenue', 'avg_fare', 'surge_events', 'avg_surge_multiplier')
        }),
        ('Popular Locations', {
            'fields': ('top_pickup_points', 'top_destinations', 'popular_routes'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def total_revenue_display(self, obj):
        return f"${obj.total_revenue:,.2f}"
    total_revenue_display.short_description = 'Total Revenue'


@admin.register(DriverPerformanceAnalytics)
class DriverPerformanceAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'driver', 'date', 'rides_completed', 'gross_earnings_display',
        'avg_rating', 'utilization_rate_display'
    ]
    list_filter = ['date', 'driver']
    search_fields = [
        'driver__phone_number', 'driver__first_name', 'driver__last_name'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'utilization_rate', 'earnings_per_hour'
    ]
    
    fieldsets = (
        ('Driver Information', {
            'fields': ('driver', 'date')
        }),
        ('Activity Metrics', {
            'fields': ('online_time', 'active_time', 'idle_time', 'utilization_rate')
        }),
        ('Ride Metrics', {
            'fields': ('rides_completed', 'rides_cancelled', 'rides_declined', 'total_distance')
        }),
        ('Financial Metrics', {
            'fields': (
                'gross_earnings', 'net_earnings', 'earnings_per_hour',
                'tips_received', 'fuel_costs'
            )
        }),
        ('Quality Metrics', {
            'fields': (
                'avg_rating', 'total_ratings', 'complaints_received', 'compliments_received'
            )
        }),
        ('Efficiency Metrics', {
            'fields': (
                'acceptance_rate', 'completion_rate', 'avg_pickup_time', 'avg_trip_time'
            )
        }),
        ('Safety Metrics', {
            'fields': ('safety_incidents', 'emergency_alerts', 'vehicle_inspections_passed')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def gross_earnings_display(self, obj):
        return f"${obj.gross_earnings:,.2f}"
    gross_earnings_display.short_description = 'Gross Earnings'
    
    def utilization_rate_display(self, obj):
        return f"{obj.utilization_rate:.1f}%"
    utilization_rate_display.short_description = 'Utilization Rate'


@admin.register(PaymentAnalytics)
class PaymentAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_transactions', 'successful_transactions',
        'success_rate_display', 'total_volume_display'
    ]
    list_filter = ['date']
    search_fields = ['date']
    readonly_fields = ['created_at', 'updated_at', 'success_rate']
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Transaction Metrics', {
            'fields': (
                'total_transactions', 'successful_transactions',
                'failed_transactions', 'refunded_transactions', 'success_rate'
            )
        }),
        ('Volume Metrics', {
            'fields': ('total_volume', 'avg_transaction_amount')
        }),
        ('Payment Methods', {
            'fields': (
                'card_transactions', 'card_volume',
                'mobile_money_transactions', 'mobile_money_volume',
                'wallet_transactions', 'wallet_volume'
            )
        }),
        ('Revenue', {
            'fields': ('platform_revenue', 'processing_fees')
        }),
        ('Disputes', {
            'fields': ('disputes_opened', 'disputes_resolved', 'chargeback_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def success_rate_display(self, obj):
        return f"{obj.success_rate:.1f}%"
    success_rate_display.short_description = 'Success Rate'
    
    def total_volume_display(self, obj):
        return f"${obj.total_volume:,.2f}"
    total_volume_display.short_description = 'Total Volume'


@admin.register(RevenueAnalytics)
class RevenueAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'gross_revenue_display', 'net_revenue_display',
        'driver_payouts_display', 'revenue_growth_rate_display'
    ]
    list_filter = ['date']
    search_fields = ['date']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Date', {
            'fields': ('date',)
        }),
        ('Revenue', {
            'fields': (
                'gross_revenue', 'ride_revenue', 'commission_revenue', 'surge_revenue'
            )
        }),
        ('Costs', {
            'fields': (
                'driver_payouts', 'payment_processing_fees',
                'refunds_issued', 'promotional_discounts'
            )
        }),
        ('Net Revenue', {
            'fields': ('net_revenue',)
        }),
        ('Currency Breakdown', {
            'fields': ('revenue_by_currency',),
            'classes': ('collapse',)
        }),
        ('Growth', {
            'fields': ('revenue_growth_rate',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def gross_revenue_display(self, obj):
        return f"${obj.gross_revenue:,.2f}"
    gross_revenue_display.short_description = 'Gross Revenue'
    
    def net_revenue_display(self, obj):
        return f"${obj.net_revenue:,.2f}"
    net_revenue_display.short_description = 'Net Revenue'
    
    def driver_payouts_display(self, obj):
        return f"${obj.driver_payouts:,.2f}"
    driver_payouts_display.short_description = 'Driver Payouts'
    
    def revenue_growth_rate_display(self, obj):
        return f"{obj.revenue_growth_rate:.1f}%"
    revenue_growth_rate_display.short_description = 'Growth Rate'


@admin.register(PredictiveAnalytics)
class PredictiveAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'prediction_type', 'date', 'model_version',
        'confidence_score_display', 'accuracy_score_display'
    ]
    list_filter = ['prediction_type', 'date', 'model_version']
    search_fields = ['prediction_type', 'model_version']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Prediction Information', {
            'fields': ('date', 'prediction_type', 'model_version')
        }),
        ('Predictions', {
            'fields': (
                'predicted_demand', 'predicted_supply',
                'predicted_revenue', 'predicted_surge_areas'
            )
        }),
        ('Model Metadata', {
            'fields': ('confidence_score', 'training_data_period')
        }),
        ('Validation', {
            'fields': ('actual_values', 'accuracy_score')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def confidence_score_display(self, obj):
        return f"{obj.confidence_score * 100:.1f}%"
    confidence_score_display.short_description = 'Confidence'
    
    def accuracy_score_display(self, obj):
        if obj.accuracy_score:
            return f"{obj.accuracy_score * 100:.1f}%"
        return "N/A"
    accuracy_score_display.short_description = 'Accuracy'


@admin.register(AnalyticsReport)
class AnalyticsReportAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'report_type', 'format', 'start_date', 'end_date',
        'is_ready', 'generated_by', 'created_at'
    ]
    list_filter = ['report_type', 'format', 'is_ready', 'created_at']
    search_fields = ['name', 'generated_by__first_name', 'generated_by__last_name']
    readonly_fields = [
        'id', 'data', 'file_path', 'generated_by', 'generation_time',
        'is_ready', 'error_message', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Report Information', {
            'fields': ('id', 'name', 'report_type', 'format')
        }),
        ('Parameters', {
            'fields': ('start_date', 'end_date', 'filters')
        }),
        ('Generation Info', {
            'fields': (
                'generated_by', 'generation_time', 'is_ready', 'error_message'
            )
        }),
        ('Data', {
            'fields': ('data', 'file_path'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(AnalyticsSettings)
class AnalyticsSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'event_retention_days', 'analytics_retention_days',
        'daily_aggregation_enabled', 'real_time_analytics_enabled'
    ]
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Data Retention', {
            'fields': ('event_retention_days', 'analytics_retention_days')
        }),
        ('Aggregation Settings', {
            'fields': (
                'daily_aggregation_enabled', 'real_time_analytics_enabled',
                'predictive_analytics_enabled'
            )
        }),
        ('Privacy Settings', {
            'fields': (
                'anonymize_user_data', 'track_location_data', 'track_device_data'
            )
        }),
        ('Reporting Settings', {
            'fields': (
                'auto_generate_daily_reports', 'auto_generate_weekly_reports',
                'auto_generate_monthly_reports'
            )
        }),
        ('Alert Thresholds', {
            'fields': (
                'low_driver_supply_threshold', 'high_demand_threshold',
                'revenue_drop_threshold'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not AnalyticsSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Don't allow deletion of settings
        return False
