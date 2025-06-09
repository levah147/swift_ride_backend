from django.utils import timezone
from django.db.models import Count, Avg, Sum, Q, F
from django.contrib.auth import get_user_model
from apps.analytics.models import (
    AnalyticsEvent, DailyAnalytics, UserAnalytics, 
    RideAnalytics, GeographicAnalytics, DriverPerformanceAnalytics,
    PaymentAnalytics, RevenueAnalytics, AnalyticsSettings
)
from apps.rides.models import Ride
from apps.payments.models import Payment
from decimal import Decimal
import logging
from datetime import datetime, timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for handling analytics operations"""
    
    @staticmethod
    def track_event(event_type, user=None, properties=None, location=None, 
                   session_id=None, platform='api', request=None):
        """Track an analytics event"""
        try:
            event_data = {
                'event_type': event_type,
                'user': user,
                'properties': properties or {},
                'session_id': session_id,
                'platform': platform,
            }
            
            # Add location data if provided
            if location:
                event_data['latitude'] = location.get('latitude')
                event_data['longitude'] = location.get('longitude')
            
            # Extract request data if available
            if request:
                event_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
                event_data['ip_address'] = AnalyticsService._get_client_ip(request)
                event_data['device_id'] = request.META.get('HTTP_X_DEVICE_ID')
                event_data['app_version'] = request.META.get('HTTP_X_APP_VERSION')
            
            event = AnalyticsEvent.objects.create(**event_data)
            
            # Update user analytics if user is provided
            if user:
                AnalyticsService._update_user_analytics(user, event_type, properties)
            
            return event
            
        except Exception as e:
            logger.error(f"Error tracking event {event_type}: {str(e)}")
            return None
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    @staticmethod
    def _update_user_analytics(user, event_type, properties):
        """Update user analytics based on event"""
        try:
            analytics, created = UserAnalytics.objects.get_or_create(user=user)
            
            # Update last active
            analytics.last_active = timezone.now()
            
            # Update days since signup
            if user.date_joined:
                analytics.days_since_signup = (timezone.now().date() - user.date_joined.date()).days
            
            # Update specific metrics based on event type
            if event_type == 'app_open':
                analytics.total_sessions += 1
            elif event_type == 'chat_message':
                analytics.chat_messages_sent += 1
            elif event_type == 'emergency_triggered':
                analytics.emergency_alerts_triggered += 1
            elif event_type == 'promotion_used':
                analytics.promotions_used += 1
            
            analytics.save()
            
        except Exception as e:
            logger.error(f"Error updating user analytics: {str(e)}")
    
    @staticmethod
    def generate_daily_analytics(date=None):
        """Generate daily analytics for a specific date"""
        if date is None:
            date = timezone.now().date()
        
        try:
            # Get or create daily analytics record
            daily_analytics, created = DailyAnalytics.objects.get_or_create(
                date=date,
                defaults={}
            )
            
            # Calculate user metrics
            AnalyticsService._calculate_user_metrics(daily_analytics, date)
            
            # Calculate driver metrics
            AnalyticsService._calculate_driver_metrics(daily_analytics, date)
            
            # Calculate ride metrics
            AnalyticsService._calculate_ride_metrics(daily_analytics, date)
            
            # Calculate financial metrics
            AnalyticsService._calculate_financial_metrics(daily_analytics, date)
            
            # Calculate engagement metrics
            AnalyticsService._calculate_engagement_metrics(daily_analytics, date)
            
            # Calculate emergency metrics
            AnalyticsService._calculate_emergency_metrics(daily_analytics, date)
            
            daily_analytics.save()
            
            logger.info(f"Generated daily analytics for {date}")
            return daily_analytics
            
        except Exception as e:
            logger.error(f"Error generating daily analytics for {date}: {str(e)}")
            return None
    
    @staticmethod
    def _calculate_user_metrics(daily_analytics, date):
        """Calculate user metrics for daily analytics"""
        # Total users
        daily_analytics.total_users = User.objects.filter(
            date_joined__date__lte=date
        ).count()
        
        # New users
        daily_analytics.new_users = User.objects.filter(
            date_joined__date=date
        ).count()
        
        # Active users (users who had events on this date)
        daily_analytics.active_users = AnalyticsEvent.objects.filter(
            created_at__date=date,
            user__isnull=False
        ).values('user').distinct().count()
        
        # Returning users (active users who signed up before today)
        returning_user_ids = AnalyticsEvent.objects.filter(
            created_at__date=date,
            user__isnull=False,
            user__date_joined__date__lt=date
        ).values_list('user_id', flat=True).distinct()
        daily_analytics.returning_users = len(returning_user_ids)
    
    @staticmethod
    def _calculate_driver_metrics(daily_analytics, date):
        """Calculate driver metrics for daily analytics"""
        # Total drivers
        daily_analytics.total_drivers = User.objects.filter(
            user_type='driver',
            date_joined__date__lte=date
        ).count()
        
        # Active drivers (drivers who had events on this date)
        daily_analytics.active_drivers = AnalyticsEvent.objects.filter(
            created_at__date=date,
            user__user_type='driver'
        ).values('user').distinct().count()
        
        # Online drivers metrics would require tracking driver online/offline events
        # For now, we'll use active drivers as a proxy
        daily_analytics.online_drivers_peak = daily_analytics.active_drivers
        daily_analytics.avg_online_drivers = Decimal(str(daily_analytics.active_drivers))
    
    @staticmethod
    def _calculate_ride_metrics(daily_analytics, date):
        """Calculate ride metrics for daily analytics"""
        rides = Ride.objects.filter(created_at__date=date)
        
        daily_analytics.total_rides = rides.count()
        daily_analytics.completed_rides = rides.filter(status='completed').count()
        daily_analytics.cancelled_rides = rides.filter(status='cancelled').count()
        
        # Calculate average ride duration for completed rides
        completed_rides = rides.filter(
            status='completed',
            started_at__isnull=False,
            completed_at__isnull=False
        )
        
        if completed_rides.exists():
            durations = []
            for ride in completed_rides:
                duration = ride.completed_at - ride.started_at
                durations.append(duration)
            
            if durations:
                avg_duration = sum(durations, timedelta()) / len(durations)
                daily_analytics.avg_ride_duration = avg_duration
        
        # Calculate average wait time (pickup time - request time)
        picked_up_rides = rides.filter(
            picked_up_at__isnull=False
        )
        
        if picked_up_rides.exists():
            wait_times = []
            for ride in picked_up_rides:
                wait_time = ride.picked_up_at - ride.created_at
                wait_times.append(wait_time)
            
            if wait_times:
                avg_wait_time = sum(wait_times, timedelta()) / len(wait_times)
                daily_analytics.avg_wait_time = avg_wait_time
    
    @staticmethod
    def _calculate_financial_metrics(daily_analytics, date):
        """Calculate financial metrics for daily analytics"""
        # Get payments for the date
        payments = Payment.objects.filter(
            created_at__date=date,
            status='completed'
        )
        
        total_revenue = payments.aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        
        daily_analytics.total_revenue = total_revenue
        
        # Calculate platform commission (assuming 20% commission rate)
        commission_rate = Decimal('0.20')
        daily_analytics.platform_commission = total_revenue * commission_rate
        daily_analytics.driver_earnings = total_revenue * (Decimal('1') - commission_rate)
        
        # Calculate average ride fare
        if daily_analytics.completed_rides > 0:
            daily_analytics.avg_ride_fare = total_revenue / daily_analytics.completed_rides
    
    @staticmethod
    def _calculate_engagement_metrics(daily_analytics, date):
        """Calculate engagement metrics for daily analytics"""
        events = AnalyticsEvent.objects.filter(created_at__date=date)
        
        # App opens
        daily_analytics.app_opens = events.filter(event_type='app_open').count()
        
        # Chat messages
        daily_analytics.chat_messages = events.filter(event_type='chat_message').count()
        
        # Ratings given
        daily_analytics.ratings_given = events.filter(event_type='rating_given').count()
        
        # Calculate average rating from ride analytics
        from apps.rides.models import RideRating
        ratings = RideRating.objects.filter(created_at__date=date)
        if ratings.exists():
            avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
            daily_analytics.avg_rating = avg_rating or Decimal('0')
    
    @staticmethod
    def _calculate_emergency_metrics(daily_analytics, date):
        """Calculate emergency metrics for daily analytics"""
        events = AnalyticsEvent.objects.filter(created_at__date=date)
        
        daily_analytics.emergency_alerts = events.filter(
            event_type='emergency_triggered'
        ).count()
        
        # Safety checks would be tracked separately
        # For now, we'll use a placeholder
        daily_analytics.safety_checks = 0
    
    @staticmethod
    def get_analytics_dashboard_data(start_date=None, end_date=None):
        """Get analytics data for dashboard"""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            # Get daily analytics for the period
            daily_analytics = DailyAnalytics.objects.filter(
                date__range=[start_date, end_date]
            ).order_by('date')
            
            # Calculate totals and trends
            total_users = daily_analytics.aggregate(
                max_users=models.Max('total_users')
            )['max_users'] or 0
            
            total_rides = daily_analytics.aggregate(
                sum_rides=Sum('total_rides')
            )['sum_rides'] or 0
            
            total_revenue = daily_analytics.aggregate(
                sum_revenue=Sum('total_revenue')
            )['sum_revenue'] or Decimal('0')
            
            # Calculate growth rates
            if daily_analytics.count() >= 2:
                first_day = daily_analytics.first()
                last_day = daily_analytics.last()
                
                user_growth = AnalyticsService._calculate_growth_rate(
                    first_day.total_users, last_day.total_users
                )
                revenue_growth = AnalyticsService._calculate_growth_rate(
                    first_day.total_revenue, last_day.total_revenue
                )
            else:
                user_growth = 0
                revenue_growth = 0
            
            # Prepare chart data
            chart_data = []
            for analytics in daily_analytics:
                chart_data.append({
                    'date': analytics.date.isoformat(),
                    'users': analytics.active_users,
                    'rides': analytics.total_rides,
                    'revenue': float(analytics.total_revenue),
                    'drivers': analytics.active_drivers
                })
            
            return {
                'summary': {
                    'total_users': total_users,
                    'total_rides': total_rides,
                    'total_revenue': float(total_revenue),
                    'user_growth': user_growth,
                    'revenue_growth': revenue_growth
                },
                'chart_data': chart_data,
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            return None
    
    @staticmethod
    def _calculate_growth_rate(old_value, new_value):
        """Calculate growth rate percentage"""
        if old_value == 0:
            return 100 if new_value > 0 else 0
        return ((new_value - old_value) / old_value) * 100
    
    @staticmethod
    def get_user_analytics(user_id):
        """Get analytics for a specific user"""
        try:
            user = User.objects.get(id=user_id)
            analytics, created = UserAnalytics.objects.get_or_create(user=user)
            
            # Get recent events
            recent_events = AnalyticsEvent.objects.filter(
                user=user
            ).order_by('-created_at')[:50]
            
            # Get ride analytics if user is a rider or driver
            ride_analytics = []
            if user.user_type in ['rider', 'driver']:
                rides = Ride.objects.filter(
                    Q(rider=user) | Q(driver=user)
                ).order_by('-created_at')[:20]
                
                for ride in rides:
                    try:
                        ride_analytics.append(ride.analytics)
                    except:
                        pass
            
            return {
                'user_analytics': analytics,
                'recent_events': recent_events,
                'ride_analytics': ride_analytics
            }
            
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return None
    
    @staticmethod
    def get_geographic_analytics(date=None):
        """Get geographic analytics"""
        if not date:
            date = timezone.now().date()
        
        try:
            geographic_data = GeographicAnalytics.objects.filter(date=date)
            
            # If no data for the date, generate it
            if not geographic_data.exists():
                AnalyticsService._generate_geographic_analytics(date)
                geographic_data = GeographicAnalytics.objects.filter(date=date)
            
            return geographic_data
            
        except Exception as e:
            logger.error(f"Error getting geographic analytics: {str(e)}")
            return GeographicAnalytics.objects.none()
    
    @staticmethod
    def _generate_geographic_analytics(date):
        """Generate geographic analytics for a date"""
        # This would analyze rides by geographic areas
        # For now, we'll create a placeholder implementation
        
        # Define some sample areas (in production, this would be dynamic)
        areas = [
            {'name': 'Downtown', 'lat': 1.2966, 'lng': 36.8219, 'radius': 2.0},
            {'name': 'Airport', 'lat': 1.3192, 'lng': 36.9275, 'radius': 3.0},
            {'name': 'University', 'lat': 1.2921, 'lng': 36.8219, 'radius': 1.5},
        ]
        
        for area in areas:
            # Calculate metrics for this area
            # This is a simplified implementation
            GeographicAnalytics.objects.create(
                date=date,
                area_name=area['name'],
                center_latitude=area['lat'],
                center_longitude=area['lng'],
                radius_km=area['radius'],
                ride_requests=10,  # Placeholder
                completed_rides=8,  # Placeholder
                cancelled_rides=2,  # Placeholder
                active_drivers=5,  # Placeholder
                total_revenue=Decimal('500.00'),  # Placeholder
                avg_fare=Decimal('62.50')  # Placeholder
            )
    
    @staticmethod
    def generate_analytics_report(report_type, start_date, end_date, filters=None):
        """Generate an analytics report"""
        try:
            from apps.analytics.models import AnalyticsReport
            
            # Create report record
            report = AnalyticsReport.objects.create(
                name=f"{report_type.title()} Report - {start_date} to {end_date}",
                report_type=report_type,
                start_date=start_date,
                end_date=end_date,
                filters=filters or {}
            )
            
            # Generate report data based on type
            if report_type == 'daily':
                report_data = AnalyticsService._generate_daily_report(start_date, end_date, filters)
            elif report_type == 'weekly':
                report_data = AnalyticsService._generate_weekly_report(start_date, end_date, filters)
            elif report_type == 'monthly':
                report_data = AnalyticsService._generate_monthly_report(start_date, end_date, filters)
            else:
                report_data = AnalyticsService._generate_custom_report(start_date, end_date, filters)
            
            # Save report data
            report.data = report_data
            report.is_ready = True
            report.save()
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating analytics report: {str(e)}")
            return None
    
    @staticmethod
    def _generate_daily_report(start_date, end_date, filters):
        """Generate daily report data"""
        daily_analytics = DailyAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        report_data = {
            'summary': {
                'total_days': daily_analytics.count(),
                'avg_daily_rides': daily_analytics.aggregate(avg=Avg('total_rides'))['avg'] or 0,
                'avg_daily_revenue': daily_analytics.aggregate(avg=Avg('total_revenue'))['avg'] or 0,
                'total_revenue': daily_analytics.aggregate(sum=Sum('total_revenue'))['sum'] or 0,
            },
            'daily_data': []
        }
        
        for analytics in daily_analytics:
            report_data['daily_data'].append({
                'date': analytics.date.isoformat(),
                'total_users': analytics.total_users,
                'new_users': analytics.new_users,
                'active_users': analytics.active_users,
                'total_rides': analytics.total_rides,
                'completed_rides': analytics.completed_rides,
                'cancelled_rides': analytics.cancelled_rides,
                'total_revenue': float(analytics.total_revenue),
                'active_drivers': analytics.active_drivers,
            })
        
        return report_data
    
    @staticmethod
    def _generate_weekly_report(start_date, end_date, filters):
        """Generate weekly report data"""
        # Group daily analytics by week
        daily_analytics = DailyAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        weekly_data = {}
        for analytics in daily_analytics:
            # Get week start date (Monday)
            week_start = analytics.date - timedelta(days=analytics.date.weekday())
            week_key = week_start.isoformat()
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {
                    'week_start': week_key,
                    'total_rides': 0,
                    'total_revenue': 0,
                    'total_users': 0,
                    'days': []
                }
            
            weekly_data[week_key]['total_rides'] += analytics.total_rides
            weekly_data[week_key]['total_revenue'] += float(analytics.total_revenue)
            weekly_data[week_key]['total_users'] = max(
                weekly_data[week_key]['total_users'], 
                analytics.total_users
            )
            weekly_data[week_key]['days'].append(analytics.date.isoformat())
        
        return {
            'summary': {
                'total_weeks': len(weekly_data),
                'weekly_data': list(weekly_data.values())
            }
        }
    
    @staticmethod
    def _generate_monthly_report(start_date, end_date, filters):
        """Generate monthly report data"""
        # Similar to weekly but grouped by month
        daily_analytics = DailyAnalytics.objects.filter(
            date__range=[start_date, end_date]
        ).order_by('date')
        
        monthly_data = {}
        for analytics in daily_analytics:
            month_key = analytics.date.strftime('%Y-%m')
            
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': month_key,
                    'total_rides': 0,
                    'total_revenue': 0,
                    'max_users': 0,
                    'days_count': 0
                }
            
            monthly_data[month_key]['total_rides'] += analytics.total_rides
            monthly_data[month_key]['total_revenue'] += float(analytics.total_revenue)
            monthly_data[month_key]['max_users'] = max(
                monthly_data[month_key]['max_users'], 
                analytics.total_users
            )
            monthly_data[month_key]['days_count'] += 1
        
        return {
            'summary': {
                'total_months': len(monthly_data),
                'monthly_data': list(monthly_data.values())
            }
        }
    
    @staticmethod
    def _generate_custom_report(start_date, end_date, filters):
        """Generate custom report data"""
        # This would be customizable based on filters
        return AnalyticsService._generate_daily_report(start_date, end_date, filters)
