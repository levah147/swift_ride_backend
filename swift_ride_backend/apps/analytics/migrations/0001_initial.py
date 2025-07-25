# Generated by Django 5.2.2 on 2025-06-08 23:53

import datetime
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rides', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AnalyticsSettings',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('event_retention_days', models.PositiveIntegerField(default=365)),
                ('analytics_retention_days', models.PositiveIntegerField(default=1095)),
                ('daily_aggregation_enabled', models.BooleanField(default=True)),
                ('real_time_analytics_enabled', models.BooleanField(default=True)),
                ('predictive_analytics_enabled', models.BooleanField(default=False)),
                ('anonymize_user_data', models.BooleanField(default=True)),
                ('track_location_data', models.BooleanField(default=True)),
                ('track_device_data', models.BooleanField(default=True)),
                ('auto_generate_daily_reports', models.BooleanField(default=True)),
                ('auto_generate_weekly_reports', models.BooleanField(default=True)),
                ('auto_generate_monthly_reports', models.BooleanField(default=True)),
                ('low_driver_supply_threshold', models.PositiveIntegerField(default=5)),
                ('high_demand_threshold', models.PositiveIntegerField(default=50)),
                ('revenue_drop_threshold', models.DecimalField(decimal_places=2, default=10.0, max_digits=5)),
            ],
            options={
                'verbose_name': 'Analytics Settings',
                'verbose_name_plural': 'Analytics Settings',
                'db_table': 'analytics_settings',
            },
        ),
        migrations.CreateModel(
            name='DailyAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField(unique=True)),
                ('total_users', models.PositiveIntegerField(default=0)),
                ('new_users', models.PositiveIntegerField(default=0)),
                ('active_users', models.PositiveIntegerField(default=0)),
                ('returning_users', models.PositiveIntegerField(default=0)),
                ('total_drivers', models.PositiveIntegerField(default=0)),
                ('active_drivers', models.PositiveIntegerField(default=0)),
                ('online_drivers_peak', models.PositiveIntegerField(default=0)),
                ('avg_online_drivers', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('total_rides', models.PositiveIntegerField(default=0)),
                ('completed_rides', models.PositiveIntegerField(default=0)),
                ('cancelled_rides', models.PositiveIntegerField(default=0)),
                ('avg_ride_duration', models.DurationField(blank=True, null=True)),
                ('avg_wait_time', models.DurationField(blank=True, null=True)),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('platform_commission', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('driver_earnings', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('avg_ride_fare', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('app_opens', models.PositiveIntegerField(default=0)),
                ('avg_session_duration', models.DurationField(blank=True, null=True)),
                ('chat_messages', models.PositiveIntegerField(default=0)),
                ('ratings_given', models.PositiveIntegerField(default=0)),
                ('avg_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('emergency_alerts', models.PositiveIntegerField(default=0)),
                ('safety_checks', models.PositiveIntegerField(default=0)),
            ],
            options={
                'db_table': 'daily_analytics',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='PaymentAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('total_transactions', models.PositiveIntegerField(default=0)),
                ('successful_transactions', models.PositiveIntegerField(default=0)),
                ('failed_transactions', models.PositiveIntegerField(default=0)),
                ('refunded_transactions', models.PositiveIntegerField(default=0)),
                ('total_volume', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('avg_transaction_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('card_transactions', models.PositiveIntegerField(default=0)),
                ('card_volume', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('mobile_money_transactions', models.PositiveIntegerField(default=0)),
                ('mobile_money_volume', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('wallet_transactions', models.PositiveIntegerField(default=0)),
                ('wallet_volume', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('platform_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('processing_fees', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('disputes_opened', models.PositiveIntegerField(default=0)),
                ('disputes_resolved', models.PositiveIntegerField(default=0)),
                ('chargeback_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
            ],
            options={
                'db_table': 'payment_analytics',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='RevenueAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('gross_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('ride_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('commission_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('surge_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('driver_payouts', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('payment_processing_fees', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('refunds_issued', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('promotional_discounts', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('net_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('revenue_by_currency', models.JSONField(blank=True, default=dict)),
                ('revenue_growth_rate', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
            ],
            options={
                'db_table': 'revenue_analytics',
                'ordering': ['-date'],
            },
        ),
        migrations.CreateModel(
            name='AnalyticsReport',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('report_type', models.CharField(choices=[('daily', 'Daily Report'), ('weekly', 'Weekly Report'), ('monthly', 'Monthly Report'), ('quarterly', 'Quarterly Report'), ('yearly', 'Yearly Report'), ('custom', 'Custom Report')], max_length=20)),
                ('format', models.CharField(choices=[('json', 'JSON'), ('csv', 'CSV'), ('pdf', 'PDF'), ('excel', 'Excel')], default='json', max_length=10)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('filters', models.JSONField(blank=True, default=dict)),
                ('data', models.JSONField(blank=True, default=dict)),
                ('file_path', models.CharField(blank=True, max_length=500, null=True)),
                ('generation_time', models.DurationField(blank=True, null=True)),
                ('is_ready', models.BooleanField(default=False)),
                ('error_message', models.TextField(blank=True, null=True)),
                ('generated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='generated_reports', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'analytics_reports',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='GeographicAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('area_name', models.CharField(max_length=100)),
                ('center_latitude', models.DecimalField(decimal_places=8, max_digits=10)),
                ('center_longitude', models.DecimalField(decimal_places=8, max_digits=11)),
                ('radius_km', models.DecimalField(decimal_places=2, default=1.0, max_digits=6)),
                ('ride_requests', models.PositiveIntegerField(default=0)),
                ('completed_rides', models.PositiveIntegerField(default=0)),
                ('cancelled_rides', models.PositiveIntegerField(default=0)),
                ('avg_wait_time', models.DurationField(blank=True, null=True)),
                ('active_drivers', models.PositiveIntegerField(default=0)),
                ('avg_driver_utilization', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('avg_fare', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('surge_events', models.PositiveIntegerField(default=0)),
                ('avg_surge_multiplier', models.DecimalField(decimal_places=2, default=1.0, max_digits=4)),
                ('top_pickup_points', models.JSONField(blank=True, default=list)),
                ('top_destinations', models.JSONField(blank=True, default=list)),
                ('popular_routes', models.JSONField(blank=True, default=list)),
            ],
            options={
                'db_table': 'geographic_analytics',
                'ordering': ['-date', 'area_name'],
                'unique_together': {('date', 'area_name')},
            },
        ),
        migrations.CreateModel(
            name='PredictiveAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('prediction_type', models.CharField(max_length=50)),
                ('predicted_demand', models.JSONField(blank=True, default=dict)),
                ('predicted_supply', models.JSONField(blank=True, default=dict)),
                ('predicted_revenue', models.DecimalField(blank=True, decimal_places=2, max_digits=15, null=True)),
                ('predicted_surge_areas', models.JSONField(blank=True, default=list)),
                ('model_version', models.CharField(max_length=20)),
                ('confidence_score', models.DecimalField(decimal_places=4, default=0, max_digits=5)),
                ('training_data_period', models.CharField(max_length=50)),
                ('actual_values', models.JSONField(blank=True, default=dict)),
                ('accuracy_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
            ],
            options={
                'db_table': 'predictive_analytics',
                'ordering': ['-date'],
                'unique_together': {('date', 'prediction_type')},
            },
        ),
        migrations.CreateModel(
            name='RideAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('request_to_acceptance_time', models.DurationField(blank=True, null=True)),
                ('acceptance_to_pickup_time', models.DurationField(blank=True, null=True)),
                ('pickup_to_dropoff_time', models.DurationField(blank=True, null=True)),
                ('total_ride_time', models.DurationField(blank=True, null=True)),
                ('estimated_distance', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('actual_distance', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('distance_variance', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('estimated_fare', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('final_fare', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('surge_multiplier', models.DecimalField(decimal_places=2, default=1.0, max_digits=4)),
                ('discount_amount', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('initial_offer', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('final_agreed_price', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('bargaining_rounds', models.PositiveIntegerField(default=0)),
                ('bargaining_duration', models.DurationField(blank=True, null=True)),
                ('drivers_notified', models.PositiveIntegerField(default=0)),
                ('drivers_viewed', models.PositiveIntegerField(default=0)),
                ('drivers_declined', models.PositiveIntegerField(default=0)),
                ('time_to_find_driver', models.DurationField(blank=True, null=True)),
                ('rider_rating', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('driver_rating', models.DecimalField(blank=True, decimal_places=2, max_digits=3, null=True)),
                ('rider_feedback', models.TextField(blank=True, null=True)),
                ('driver_feedback', models.TextField(blank=True, null=True)),
                ('safety_checks_completed', models.PositiveIntegerField(default=0)),
                ('emergency_alerts', models.PositiveIntegerField(default=0)),
                ('route_deviations', models.PositiveIntegerField(default=0)),
                ('ride', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analytics', to='rides.ride')),
            ],
            options={
                'db_table': 'ride_analytics',
            },
        ),
        migrations.CreateModel(
            name='UserAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('total_sessions', models.PositiveIntegerField(default=0)),
                ('total_session_duration', models.DurationField(default=datetime.timedelta(0))),
                ('last_active', models.DateTimeField(blank=True, null=True)),
                ('days_since_signup', models.PositiveIntegerField(default=0)),
                ('total_rides_as_rider', models.PositiveIntegerField(default=0)),
                ('completed_rides_as_rider', models.PositiveIntegerField(default=0)),
                ('cancelled_rides_as_rider', models.PositiveIntegerField(default=0)),
                ('total_spent', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('avg_ride_rating_given', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('total_rides_as_driver', models.PositiveIntegerField(default=0)),
                ('completed_rides_as_driver', models.PositiveIntegerField(default=0)),
                ('cancelled_rides_as_driver', models.PositiveIntegerField(default=0)),
                ('total_earned', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('avg_driver_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('total_online_time', models.DurationField(default=datetime.timedelta(0))),
                ('chat_messages_sent', models.PositiveIntegerField(default=0)),
                ('emergency_alerts_triggered', models.PositiveIntegerField(default=0)),
                ('promotions_used', models.PositiveIntegerField(default=0)),
                ('favorite_pickup_locations', models.JSONField(blank=True, default=list)),
                ('favorite_destinations', models.JSONField(blank=True, default=list)),
                ('peak_usage_hours', models.JSONField(blank=True, default=list)),
                ('preferred_vehicle_types', models.JSONField(blank=True, default=list)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='analytics', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'user_analytics',
            },
        ),
        migrations.CreateModel(
            name='AnalyticsEvent',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('session_id', models.CharField(blank=True, max_length=100, null=True)),
                ('event_type', models.CharField(choices=[('user_signup', 'User Signup'), ('user_login', 'User Login'), ('ride_request', 'Ride Request'), ('ride_completed', 'Ride Completed'), ('ride_cancelled', 'Ride Cancelled'), ('payment_made', 'Payment Made'), ('driver_online', 'Driver Online'), ('driver_offline', 'Driver Offline'), ('app_open', 'App Open'), ('app_close', 'App Close'), ('search_location', 'Search Location'), ('view_profile', 'View Profile'), ('emergency_triggered', 'Emergency Triggered'), ('chat_message', 'Chat Message'), ('rating_given', 'Rating Given'), ('promotion_used', 'Promotion Used')], max_length=30)),
                ('platform', models.CharField(choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web'), ('api', 'API')], default='api', max_length=10)),
                ('properties', models.JSONField(blank=True, default=dict)),
                ('latitude', models.DecimalField(blank=True, decimal_places=8, max_digits=10, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=8, max_digits=11, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('device_id', models.CharField(blank=True, max_length=255, null=True)),
                ('app_version', models.CharField(blank=True, max_length=20, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='analytics_events', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'analytics_events',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['event_type', 'created_at'], name='analytics_e_event_t_c3dcde_idx'), models.Index(fields=['user', 'created_at'], name='analytics_e_user_id_7e4ee5_idx'), models.Index(fields=['platform', 'created_at'], name='analytics_e_platfor_7b0bf2_idx'), models.Index(fields=['session_id'], name='analytics_e_session_b3cbf5_idx')],
            },
        ),
        migrations.CreateModel(
            name='DriverPerformanceAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('online_time', models.DurationField(default=datetime.timedelta(0))),
                ('active_time', models.DurationField(default=datetime.timedelta(0))),
                ('idle_time', models.DurationField(default=datetime.timedelta(0))),
                ('rides_completed', models.PositiveIntegerField(default=0)),
                ('rides_cancelled', models.PositiveIntegerField(default=0)),
                ('rides_declined', models.PositiveIntegerField(default=0)),
                ('total_distance', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('gross_earnings', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('net_earnings', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('tips_received', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('fuel_costs', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('avg_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('total_ratings', models.PositiveIntegerField(default=0)),
                ('complaints_received', models.PositiveIntegerField(default=0)),
                ('compliments_received', models.PositiveIntegerField(default=0)),
                ('acceptance_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('completion_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('avg_pickup_time', models.DurationField(blank=True, null=True)),
                ('avg_trip_time', models.DurationField(blank=True, null=True)),
                ('safety_incidents', models.PositiveIntegerField(default=0)),
                ('emergency_alerts', models.PositiveIntegerField(default=0)),
                ('vehicle_inspections_passed', models.PositiveIntegerField(default=0)),
                ('driver', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='driver_performance', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'driver_performance_analytics',
                'ordering': ['-date', 'driver'],
                'unique_together': {('driver', 'date')},
            },
        ),
    ]
