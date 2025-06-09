from celery import shared_task
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from apps.analytics.models import (
    AnalyticsEvent, DailyAnalytics, UserAnalytics, 
    DriverPerformanceAnalytics, PaymentAnalytics, RevenueAnalytics,
    AnalyticsSettings
)
from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.reporting_service import ReportingService
from apps.users.models import User
from apps.rides.models import Ride
from apps.payments.models import Payment
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_analytics_task(date_str=None):
    """Generate daily analytics for a specific date"""
    try:
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date() - timedelta(days=1)  # Previous day
        
        analytics = AnalyticsService.generate_daily_analytics(date)
        
        if analytics:
            logger.info(f"Successfully generated daily analytics for {date}")
            return f"Daily analytics generated for {date}"
        else:
            logger.error(f"Failed to generate daily analytics for {date}")
            return f"Failed to generate daily analytics for {date}"
        
    except Exception as e:
        logger.error(f"Error in generate_daily_analytics_task: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def update_user_analytics_task(user_id):
    """Update analytics for a specific user"""
    try:
        user = User.objects.get(id=user_id)
        analytics, created = UserAnalytics.objects.get_or_create(user=user)
        
        # Update basic metrics
        analytics.last_active = timezone.now()
        
        if user.date_joined:
            analytics.days_since_signup = (timezone.now().date() - user.date_joined.date()).days
        
        # Update ride metrics
        rider_rides = Ride.objects.filter(rider=user)
        analytics.total_rides_as_rider = rider_rides.count()
        analytics.completed_rides_as_rider = rider_rides.filter(status='completed').count()
        analytics.cancelled_rides_as_rider = rider_rides.filter(status='cancelled').count()
        
        driver_rides = Ride.objects.filter(driver=user)
        analytics.total_rides_as_driver = driver_rides.count()
        analytics.completed_rides_as_driver = driver_rides.filter(status='completed').count()
        analytics.cancelled_rides_as_driver = driver_rides.filter(status='cancelled').count()
        
        # Update financial metrics
        payments = Payment.objects.filter(user=user, status='completed')
        analytics.total_spent = payments.aggregate(total=Sum('amount'))['total'] or 0
        
        # Update session metrics
        events = AnalyticsEvent.objects.filter(user=user)
        analytics.total_sessions = events.filter(event_type='app_open').count()
        analytics.chat_messages_sent = events.filter(event_type='chat_message').count()
        analytics.emergency_alerts_triggered = events.filter(event_type='emergency_triggered').count()
        analytics.promotions_used = events.filter(event_type='promotion_used').count()
        
        analytics.save()
        
        logger.info(f"Updated user analytics for user {user_id}")
        return f"User analytics updated for {user_id}"
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return f"User {user_id} not found"
    except Exception as e:
        logger.error(f"Error updating user analytics for {user_id}: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def generate_driver_performance_analytics_task(date_str=None):
    """Generate driver performance analytics for a specific date"""
    try:
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date() - timedelta(days=1)
        
        # Get all drivers who were active on this date
        active_drivers = AnalyticsEvent.objects.filter(
            created_at__date=date,
            user__user_type='driver'
        ).values_list('user_id', flat=True).distinct()
        
        for driver_id in active_drivers:
            try:
                driver = User.objects.get(id=driver_id, user_type='driver')
                
                # Get or create performance record
                performance, created = DriverPerformanceAnalytics.objects.get_or_create(
                    driver=driver,
                    date=date,
                    defaults={}
                )
                
                # Calculate metrics for this driver on this date
                driver_rides = Ride.objects.filter(
                    driver=driver,
                    created_at__date=date
                )
                
                performance.rides_completed = driver_rides.filter(status='completed').count()
                performance.rides_cancelled = driver_rides.filter(status='cancelled').count()
                
                # Calculate earnings
                completed_rides = driver_rides.filter(status='completed')
                total_earnings = 0
                for ride in completed_rides:
                    if hasattr(ride, 'payment') and ride.payment.status == 'completed':
                        # Assuming 80% goes to driver (20% commission)
                        total_earnings += ride.payment.amount * 0.8
                
                performance.gross_earnings = total_earnings
                performance.net_earnings = total_earnings  # Simplified
                
                # Calculate rates
                total_ride_requests = driver_rides.count()
                if total_ride_requests > 0:
                    performance.completion_rate = (performance.rides_completed / total_ride_requests) * 100
                
                # Calculate ratings
                from apps.rides.models import RideRating
                ratings = RideRating.objects.filter(
                    ride__driver=driver,
                    ride__created_at__date=date,
                    rating_type='driver'
                )
                
                if ratings.exists():
                    performance.avg_rating = ratings.aggregate(avg=Avg('rating'))['avg']
                    performance.total_ratings = ratings.count()
                
                performance.save()
                
            except User.DoesNotExist:
                continue
            except Exception as e:
                logger.error(f"Error processing driver {driver_id}: {str(e)}")
                continue
        
        logger.info(f"Generated driver performance analytics for {date}")
        return f"Driver performance analytics generated for {date}"
        
    except Exception as e:
        logger.error(f"Error in generate_driver_performance_analytics_task: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def generate_payment_analytics_task(date_str=None):
    """Generate payment analytics for a specific date"""
    try:
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date() - timedelta(days=1)
        
        # Get or create payment analytics record
        analytics, created = PaymentAnalytics.objects.get_or_create(
            date=date,
            defaults={}
        )
        
        # Get payments for the date
        payments = Payment.objects.filter(created_at__date=date)
        
        # Calculate transaction metrics
        analytics.total_transactions = payments.count()
        analytics.successful_transactions = payments.filter(status='completed').count()
        analytics.failed_transactions = payments.filter(status='failed').count()
        analytics.refunded_transactions = payments.filter(status='refunded').count()
        
        # Calculate volume metrics
        successful_payments = payments.filter(status='completed')
        analytics.total_volume = successful_payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        if analytics.successful_transactions > 0:
            analytics.avg_transaction_amount = analytics.total_volume / analytics.successful_transactions
        
        # Payment method breakdown
        analytics.card_transactions = successful_payments.filter(
            payment_method__method_type='card'
        ).count()
        analytics.card_volume = successful_payments.filter(
            payment_method__method_type='card'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        analytics.mobile_money_transactions = successful_payments.filter(
            payment_method__method_type='mobile_money'
        ).count()
        analytics.mobile_money_volume = successful_payments.filter(
            payment_method__method_type='mobile_money'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        analytics.wallet_transactions = successful_payments.filter(
            payment_method__method_type='wallet'
        ).count()
        analytics.wallet_volume = successful_payments.filter(
            payment_method__method_type='wallet'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Revenue metrics (assuming 20% platform commission)
        analytics.platform_revenue = analytics.total_volume * 0.2
        analytics.processing_fees = analytics.total_volume * 0.03  # Estimated 3% processing fee
        
        analytics.save()
        
        logger.info(f"Generated payment analytics for {date}")
        return f"Payment analytics generated for {date}"
        
    except Exception as e:
        logger.error(f"Error in generate_payment_analytics_task: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def generate_revenue_analytics_task(date_str=None):
    """Generate revenue analytics for a specific date"""
    try:
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date() - timedelta(days=1)
        
        # Get or create revenue analytics record
        analytics, created = RevenueAnalytics.objects.get_or_create(
            date=date,
            defaults={}
        )
        
        # Get successful payments for the date
        payments = Payment.objects.filter(
            created_at__date=date,
            status='completed'
        )
        
        # Calculate gross revenue
        analytics.gross_revenue = payments.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        analytics.ride_revenue = analytics.gross_revenue  # All revenue is from rides
        
        # Calculate commission (assuming 20% platform commission)
        commission_rate = 0.2
        analytics.commission_revenue = analytics.gross_revenue * commission_rate
        
        # Calculate driver payouts
        analytics.driver_payouts = analytics.gross_revenue * (1 - commission_rate)
        
        # Calculate costs
        analytics.payment_processing_fees = analytics.gross_revenue * 0.03  # 3% processing fee
        
        # Get refunds
        refunds = Payment.objects.filter(
            created_at__date=date,
            status='refunded'
        )
        analytics.refunds_issued = refunds.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Calculate promotional discounts (simplified)
        analytics.promotional_discounts = 0  # Would be calculated from promotion usage
        
        # Calculate net revenue
        analytics.calculate_net_revenue()
        
        # Calculate growth rate (compare with previous day)
        previous_date = date - timedelta(days=1)
        try:
            previous_analytics = RevenueAnalytics.objects.get(date=previous_date)
            if previous_analytics.gross_revenue > 0:
                analytics.revenue_growth_rate = (
                    (analytics.gross_revenue - previous_analytics.gross_revenue) / 
                    previous_analytics.gross_revenue
                ) * 100
        except RevenueAnalytics.DoesNotExist:
            analytics.revenue_growth_rate = 0
        
        analytics.save()
        
        logger.info(f"Generated revenue analytics for {date}")
        return f"Revenue analytics generated for {date}"
        
    except Exception as e:
        logger.error(f"Error in generate_revenue_analytics_task: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def cleanup_old_analytics_data():
    """Clean up old analytics data based on retention settings"""
    try:
        settings = AnalyticsSettings.get_settings()
        
        # Clean up old events
        event_cutoff = timezone.now() - timedelta(days=settings.event_retention_days)
        deleted_events = AnalyticsEvent.objects.filter(
            created_at__lt=event_cutoff
        ).delete()
        
        # Clean up old analytics
        analytics_cutoff = timezone.now() - timedelta(days=settings.analytics_retention_days)
        
        # Delete old daily analytics
        deleted_daily = DailyAnalytics.objects.filter(
            created_at__lt=analytics_cutoff
        ).delete()
        
        # Delete old driver performance analytics
        deleted_driver = DriverPerformanceAnalytics.objects.filter(
            created_at__lt=analytics_cutoff
        ).delete()
        
        # Delete old payment analytics
        deleted_payment = PaymentAnalytics.objects.filter(
            created_at__lt=analytics_cutoff
        ).delete()
        
        logger.info(f"Cleaned up old analytics data: {deleted_events[0]} events, "
                   f"{deleted_daily[0]} daily analytics, {deleted_driver[0]} driver analytics, "
                   f"{deleted_payment[0]} payment analytics")
        
        return "Analytics data cleanup completed"
        
    except Exception as e:
        logger.error(f"Error in cleanup_old_analytics_data: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def generate_automated_reports():
    """Generate automated reports based on settings"""
    try:
        settings = AnalyticsSettings.get_settings()
        today = timezone.now().date()
        
        reports_generated = []
        
        # Generate daily report
        if settings.auto_generate_daily_reports:
            yesterday = today - timedelta(days=1)
            report = AnalyticsService.generate_analytics_report(
                report_type='daily',
                start_date=yesterday,
                end_date=yesterday
            )
            if report:
                reports_generated.append(f"Daily report for {yesterday}")
        
        # Generate weekly report (on Mondays)
        if settings.auto_generate_weekly_reports and today.weekday() == 0:  # Monday
            week_start = today - timedelta(days=7)
            week_end = today - timedelta(days=1)
            report = AnalyticsService.generate_analytics_report(
                report_type='weekly',
                start_date=week_start,
                end_date=week_end
            )
            if report:
                reports_generated.append(f"Weekly report for {week_start} to {week_end}")
        
        # Generate monthly report (on 1st of month)
        if settings.auto_generate_monthly_reports and today.day == 1:
            # Previous month
            if today.month == 1:
                month_start = today.replace(year=today.year-1, month=12, day=1)
            else:
                month_start = today.replace(month=today.month-1, day=1)
            
            month_end = today - timedelta(days=1)
            report = AnalyticsService.generate_analytics_report(
                report_type='monthly',
                start_date=month_start,
                end_date=month_end
            )
            if report:
                reports_generated.append(f"Monthly report for {month_start} to {month_end}")
        
        logger.info(f"Generated automated reports: {reports_generated}")
        return f"Generated {len(reports_generated)} automated reports"
        
    except Exception as e:
        logger.error(f"Error in generate_automated_reports: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def process_analytics_alerts():
    """Process analytics alerts based on thresholds"""
    try:
        settings = AnalyticsSettings.get_settings()
        today = timezone.now().date()
        
        alerts = []
        
        # Check for low driver supply
        try:
            latest_analytics = DailyAnalytics.objects.filter(date=today).first()
            if latest_analytics and latest_analytics.active_drivers < settings.low_driver_supply_threshold:
                alerts.append(f"Low driver supply: {latest_analytics.active_drivers} active drivers")
        except:
            pass
        
        # Check for high demand
        try:
            latest_analytics = DailyAnalytics.objects.filter(date=today).first()
            if latest_analytics and latest_analytics.total_rides > settings.high_demand_threshold:
                alerts.append(f"High demand: {latest_analytics.total_rides} rides today")
        except:
            pass
        
        # Check for revenue drop
        try:
            today_analytics = DailyAnalytics.objects.filter(date=today).first()
            yesterday_analytics = DailyAnalytics.objects.filter(
                date=today - timedelta(days=1)
            ).first()
            
            if today_analytics and yesterday_analytics:
                if yesterday_analytics.total_revenue > 0:
                    revenue_change = (
                        (today_analytics.total_revenue - yesterday_analytics.total_revenue) / 
                        yesterday_analytics.total_revenue
                    ) * 100
                    
                    if revenue_change < -settings.revenue_drop_threshold:
                        alerts.append(f"Revenue drop: {revenue_change:.1f}% decrease")
        except:
            pass
        
        # Send alerts to admin users if any
        if alerts:
            from apps.notifications.services.notification_service import NotificationService
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            
            for admin in admin_users:
                for alert in alerts:
                    NotificationService.send_notification(
                        user=admin,
                        title="Analytics Alert",
                        message=alert,
                        notification_type='system'
                    )
        
        logger.info(f"Processed {len(alerts)} analytics alerts")
        return f"Processed {len(alerts)} analytics alerts"
        
    except Exception as e:
        logger.error(f"Error in process_analytics_alerts: {str(e)}")
        return f"Error: {str(e)}"


@shared_task
def aggregate_hourly_analytics():
    """Aggregate analytics data hourly for real-time dashboard"""
    try:
        now = timezone.now()
        hour_start = now.replace(minute=0, second=0, microsecond=0)
        hour_end = hour_start + timedelta(hours=1)
        
        # Count events in the last hour
        hourly_events = AnalyticsEvent.objects.filter(
            created_at__range=[hour_start, hour_end]
        ).values('event_type').annotate(count=Count('id'))
        
        # Count active users in the last hour
        active_users = AnalyticsEvent.objects.filter(
            created_at__range=[hour_start, hour_end]
        ).values('user').distinct().count()
        
        # Count rides in the last hour
        hourly_rides = Ride.objects.filter(
            created_at__range=[hour_start, hour_end]
        ).count()
        
        # Store in cache or database for real-time dashboard
        # This would typically be stored in Redis for fast access
        
        logger.info(f"Aggregated hourly analytics: {active_users} active users, "
                   f"{hourly_rides} rides, {len(hourly_events)} event types")
        
        return f"Hourly analytics aggregated for {hour_start}"
        
    except Exception as e:
        logger.error(f"Error in aggregate_hourly_analytics: {str(e)}")
        return f"Error: {str(e)}"
