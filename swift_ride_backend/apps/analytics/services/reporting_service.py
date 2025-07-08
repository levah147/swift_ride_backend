from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from apps.analytics.models import (
    AnalyticsEvent, DailyAnalytics, UserAnalytics, RideAnalytics, 
    DriverPerformanceAnalytics, PaymentAnalytics, RevenueAnalytics
)
from apps.rides.models import Ride
from apps.payments.models import Payment
from apps.users.models import CustomUser as User
from decimal import Decimal
import logging
from datetime import datetime, timedelta, date
import csv
import json
from io import StringIO

logger = logging.getLogger(__name__)


class ReportingService:
    """Service for generating various analytics reports"""
    
    @staticmethod
    def generate_executive_summary(start_date=None, end_date=None):
        """Generate executive summary report"""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            # Get daily analytics for the period
            daily_analytics = DailyAnalytics.objects.filter(
                date__range=[start_date, end_date]
            )
            
            if not daily_analytics.exists():
                return None
            
            # Calculate key metrics
            total_revenue = daily_analytics.aggregate(
                sum=Sum('total_revenue')
            )['sum'] or Decimal('0')
            
            total_rides = daily_analytics.aggregate(
                sum=Sum('total_rides')
            )['sum'] or 0
            
            total_completed_rides = daily_analytics.aggregate(
                sum=Sum('completed_rides')
            )['sum'] or 0
            
            avg_daily_revenue = daily_analytics.aggregate(
                avg=Avg('total_revenue')
            )['avg'] or Decimal('0')
            
            # Get latest user count
            latest_analytics = daily_analytics.order_by('-date').first()
            total_users = latest_analytics.total_users if latest_analytics else 0
            total_drivers = latest_analytics.total_drivers if latest_analytics else 0
            
            # Calculate completion rate
            completion_rate = 0
            if total_rides > 0:
                completion_rate = (total_completed_rides / total_rides) * 100
            
            # Calculate growth rates (compare with previous period)
            previous_start = start_date - (end_date - start_date)
            previous_end = start_date - timedelta(days=1)
            
            previous_analytics = DailyAnalytics.objects.filter(
                date__range=[previous_start, previous_end]
            )
            
            revenue_growth = 0
            ride_growth = 0
            
            if previous_analytics.exists():
                previous_revenue = previous_analytics.aggregate(
                    sum=Sum('total_revenue')
                )['sum'] or Decimal('0')
                
                previous_rides = previous_analytics.aggregate(
                    sum=Sum('total_rides')
                )['sum'] or 0
                
                if previous_revenue > 0:
                    revenue_growth = ((total_revenue - previous_revenue) / previous_revenue) * 100
                
                if previous_rides > 0:
                    ride_growth = ((total_rides - previous_rides) / previous_rides) * 100
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': (end_date - start_date).days + 1
                },
                'key_metrics': {
                    'total_revenue': float(total_revenue),
                    'total_rides': total_rides,
                    'total_users': total_users,
                    'total_drivers': total_drivers,
                    'completion_rate': round(completion_rate, 2),
                    'avg_daily_revenue': float(avg_daily_revenue)
                },
                'growth': {
                    'revenue_growth': round(float(revenue_growth), 2),
                    'ride_growth': round(float(ride_growth), 2)
                },
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating executive summary: {str(e)}")
            return None
    
    @staticmethod
    def generate_driver_performance_report(start_date=None, end_date=None, driver_id=None):
        """Generate driver performance report"""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=7)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            queryset = DriverPerformanceAnalytics.objects.filter(
                date__range=[start_date, end_date]
            )
            
            if driver_id:
                queryset = queryset.filter(driver_id=driver_id)
            
            # Aggregate performance metrics
            performance_data = queryset.aggregate(
                total_rides=Sum('rides_completed'),
                total_earnings=Sum('gross_earnings'),
                total_online_time=Sum('online_time'),
                avg_rating=Avg('avg_rating'),
                total_distance=Sum('total_distance')
            )
            
            # Get top performers
            top_performers = queryset.values(
                'driver__first_name', 'driver__last_name', 'driver_id'
            ).annotate(
                total_earnings=Sum('gross_earnings'),
                total_rides=Sum('rides_completed'),
                avg_rating=Avg('avg_rating')
            ).order_by('-total_earnings')[:10]
            
            # Calculate efficiency metrics
            drivers_count = queryset.values('driver').distinct().count()
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': {
                    'total_drivers': drivers_count,
                    'total_rides': performance_data['total_rides'] or 0,
                    'total_earnings': float(performance_data['total_earnings'] or 0),
                    'avg_rating': float(performance_data['avg_rating'] or 0),
                    'total_distance': float(performance_data['total_distance'] or 0)
                },
                'top_performers': list(top_performers),
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating driver performance report: {str(e)}")
            return None
    
    @staticmethod
    def generate_financial_report(start_date=None, end_date=None):
        """Generate financial report"""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            # Get revenue analytics
            revenue_analytics = RevenueAnalytics.objects.filter(
                date__range=[start_date, end_date]
            )
            
            # Get payment analytics
            payment_analytics = PaymentAnalytics.objects.filter(
                date__range=[start_date, end_date]
            )
            
            # Calculate totals
            revenue_totals = revenue_analytics.aggregate(
                gross_revenue=Sum('gross_revenue'),
                net_revenue=Sum('net_revenue'),
                driver_payouts=Sum('driver_payouts'),
                processing_fees=Sum('payment_processing_fees'),
                refunds=Sum('refunds_issued')
            )
            
            payment_totals = payment_analytics.aggregate(
                total_transactions=Sum('total_transactions'),
                successful_transactions=Sum('successful_transactions'),
                failed_transactions=Sum('failed_transactions'),
                total_volume=Sum('total_volume')
            )
            
            # Calculate success rate
            success_rate = 0
            if payment_totals['total_transactions']:
                success_rate = (
                    payment_totals['successful_transactions'] / 
                    payment_totals['total_transactions']
                ) * 100
            
            # Daily breakdown
            daily_breakdown = []
            for analytics in revenue_analytics.order_by('date'):
                daily_breakdown.append({
                    'date': analytics.date.isoformat(),
                    'gross_revenue': float(analytics.gross_revenue),
                    'net_revenue': float(analytics.net_revenue),
                    'driver_payouts': float(analytics.driver_payouts),
                    'processing_fees': float(analytics.payment_processing_fees)
                })
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'revenue_summary': {
                    'gross_revenue': float(revenue_totals['gross_revenue'] or 0),
                    'net_revenue': float(revenue_totals['net_revenue'] or 0),
                    'driver_payouts': float(revenue_totals['driver_payouts'] or 0),
                    'processing_fees': float(revenue_totals['processing_fees'] or 0),
                    'refunds_issued': float(revenue_totals['refunds'] or 0)
                },
                'payment_summary': {
                    'total_transactions': payment_totals['total_transactions'] or 0,
                    'successful_transactions': payment_totals['successful_transactions'] or 0,
                    'failed_transactions': payment_totals['failed_transactions'] or 0,
                    'success_rate': round(success_rate, 2),
                    'total_volume': float(payment_totals['total_volume'] or 0)
                },
                'daily_breakdown': daily_breakdown,
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating financial report: {str(e)}")
            return None
    
    
    
    
    
    
    
    
    
    
    @staticmethod
    def generate_user_engagement_report(start_date=None, end_date=None):
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=30)
        if not end_date:
            end_date = timezone.now().date()

        try:
            daily_analytics = DailyAnalytics.objects.filter(
                date__range=[start_date, end_date]
            )

            engagement_totals = daily_analytics.aggregate(
                total_app_opens=Sum('app_opens'),
                total_chat_messages=Sum('chat_messages'),
                total_ratings=Sum('ratings_given'),
                avg_rating=Avg('avg_rating')
            )

            active_users = UserAnalytics.objects.filter(
                last_active__date__range=[start_date, end_date]
            )

            total_users = active_users.count()
            returning_users = active_users.filter(user__date_joined__date__lt=start_date).count()

            retention_rate = (returning_users / total_users) * 100 if total_users > 0 else 0

            most_engaged = active_users.order_by('-total_sessions')[:10]

            engaged_users_data = []
            for user_analytics in most_engaged:
                engaged_users_data.append({
                    'user_id': str(user_analytics.user.id),
                    'name': user_analytics.user.get_full_name(),
                    'total_sessions': user_analytics.total_sessions,
                    'total_rides': user_analytics.total_rides_as_rider + user_analytics.total_rides_as_driver,
                    'avg_session_duration': str(user_analytics.avg_session_duration),
                    'last_active': user_analytics.last_active.isoformat() if user_analytics.last_active else None
                })

            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'engagement_summary': {
                    'total_app_opens': engagement_totals['total_app_opens'] or 0,
                    'total_chat_messages': engagement_totals['total_chat_messages'] or 0,
                    'total_ratings': engagement_totals['total_ratings'] or 0,
                    'avg_rating': float(engagement_totals['avg_rating'] or 0),
                    'retention_rate': round(retention_rate, 2)
                },
                'most_engaged_users': engaged_users_data,
                'generated_at': timezone.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating user engagement report: {str(e)}", exc_info=True)
            return None
    
    @staticmethod
    def export_report_to_csv(report_data, report_type):
        """Export report data to CSV format"""
        try:
            output = StringIO()
            
            if report_type == 'executive_summary':
                writer = csv.writer(output)
                writer.writerow(['Metric', 'Value'])
                
                # Write key metrics
                for key, value in report_data['key_metrics'].items():
                    writer.writerow([key.replace('_', ' ').title(), value])
                
                # Write growth metrics
                for key, value in report_data['growth'].items():
                    writer.writerow([key.replace('_', ' ').title(), f"{value}%"])
            
            elif report_type == 'driver_performance':
                writer = csv.writer(output)
                writer.writerow(['Driver Name', 'Total Earnings', 'Total Rides', 'Average Rating'])
                
                for performer in report_data['top_performers']:
                    name = f"{performer['driver__first_name']} {performer['driver__last_name']}"
                    writer.writerow([
                        name,
                        performer['total_earnings'],
                        performer['total_rides'],
                        performer['avg_rating']
                    ])
            
            elif report_type == 'financial':
                writer = csv.writer(output)
                writer.writerow(['Date', 'Gross Revenue', 'Net Revenue', 'Driver Payouts', 'Processing Fees'])
                
                for day in report_data['daily_breakdown']:
                    writer.writerow([
                        day['date'],
                        day['gross_revenue'],
                        day['net_revenue'],
                        day['driver_payouts'],
                        day['processing_fees']
                    ])
            
            return output.getvalue()
            
        except Exception as e:
            logger.error(f"Error exporting report to CSV: {str(e)}")
            return None
    
    @staticmethod
    def generate_ride_analytics_report(start_date=None, end_date=None):
        """Generate detailed ride analytics report"""
        if not start_date:
            start_date = timezone.now().date() - timedelta(days=7)
        if not end_date:
            end_date = timezone.now().date()
        
        try:
            # Get rides for the period
            rides = Ride.objects.filter(
                created_at__date__range=[start_date, end_date]
            )
            
            # Basic ride metrics
            total_rides = rides.count()
            completed_rides = rides.filter(status='completed').count()
            cancelled_rides = rides.filter(status='cancelled').count()
            
            # Calculate completion rate
            completion_rate = 0
            if total_rides > 0:
                completion_rate = (completed_rides / total_rides) * 100
            
            # Average metrics for completed rides
            completed_rides_qs = rides.filter(status='completed')
            
            avg_metrics = {}
            if completed_rides_qs.exists():
                # Calculate average duration
                durations = []
                distances = []
                fares = []
                
                for ride in completed_rides_qs:
                    if ride.started_at and ride.completed_at:
                        duration = ride.completed_at - ride.started_at
                        durations.append(duration.total_seconds() / 60)  # minutes
                    
                    if hasattr(ride, 'analytics'):
                        if ride.analytics.actual_distance:
                            distances.append(float(ride.analytics.actual_distance))
                        if ride.analytics.final_fare:
                            fares.append(float(ride.analytics.final_fare))
                
                avg_metrics = {
                    'avg_duration_minutes': sum(durations) / len(durations) if durations else 0,
                    'avg_distance_km': sum(distances) / len(distances) if distances else 0,
                    'avg_fare': sum(fares) / len(fares) if fares else 0
                }
            
            # Ride distribution by hour
            hourly_distribution = {}
            for hour in range(24):
                hourly_distribution[hour] = rides.filter(
                    created_at__hour=hour
                ).count()
            
            # Most popular routes
            pickup_locations = {}
            destination_locations = {}
            
            for ride in rides:
                pickup = ride.pickup_location
                destination = ride.destination
                
                if pickup:
                    pickup_locations[pickup] = pickup_locations.get(pickup, 0) + 1
                if destination:
                    destination_locations[destination] = destination_locations.get(destination, 0) + 1
            
            # Sort and get top 10
            top_pickups = sorted(pickup_locations.items(), key=lambda x: x[1], reverse=True)[:10]
            top_destinations = sorted(destination_locations.items(), key=lambda x: x[1], reverse=True)[:10]
            
            return {
                'period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'ride_summary': {
                    'total_rides': total_rides,
                    'completed_rides': completed_rides,
                    'cancelled_rides': cancelled_rides,
                    'completion_rate': round(completion_rate, 2)
                },
                'average_metrics': avg_metrics,
                'hourly_distribution': hourly_distribution,
                'popular_locations': {
                    'top_pickups': [{'location': loc, 'count': count} for loc, count in top_pickups],
                    'top_destinations': [{'location': loc, 'count': count} for loc, count in top_destinations]
                },
                'generated_at': timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating ride analytics report: {str(e)}")
            return None
    
    @staticmethod
    def generate_real_time_dashboard():
        """Generate real-time dashboard data"""
        try:
            now = timezone.now()
            today = now.date()
            
            # Current active metrics
            active_rides = Ride.objects.filter(
                status__in=['accepted', 'started', 'picked_up']
            ).count()
            
            # Today's metrics
            today_rides = Ride.objects.filter(created_at__date=today)
            today_completed = today_rides.filter(status='completed').count()
            today_revenue = Payment.objects.filter(
                created_at__date=today,
                status='completed'
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
            
            # Active users (users with events in last hour)
            active_users = AnalyticsEvent.objects.filter(
                created_at__gte=now - timedelta(hours=1)
            ).values('user').distinct().count()
            
            # Recent activity (last 24 hours)
            recent_signups = User.objects.filter(
                date_joined__gte=now - timedelta(hours=24)
            ).count()
            
            # Hourly ride requests for today
            hourly_requests = []
            for hour in range(24):
                hour_start = today.replace(hour=hour)
                hour_end = hour_start + timedelta(hours=1)
                
                if hour_end > now:
                    hour_end = now
                
                requests = Ride.objects.filter(
                    created_at__range=[hour_start, hour_end]
                ).count()
                
                hourly_requests.append({
                    'hour': hour,
                    'requests': requests
                })
            
            return {
                'timestamp': now.isoformat(),
                'active_metrics': {
                    'active_rides': active_rides,
                    'active_users': active_users
                },
                'today_metrics': {
                    'total_rides': today_rides.count(),
                    'completed_rides': today_completed,
                    'revenue': float(today_revenue),
                    'new_signups': recent_signups
                },
                'hourly_requests': hourly_requests
            }
            
        except Exception as e:
            logger.error(f"Error generating real-time dashboard: {str(e)}")
            return None


class MetricsService:
    """Service for calculating specific metrics and KPIs"""
    
    @staticmethod
    def calculate_user_lifetime_value(user_id):
        """Calculate user lifetime value"""
        try:
            user = User.objects.get(id=user_id)
            
            # Get all payments made by user
            payments = Payment.objects.filter(
                user=user,
                status='completed'
            )
            
            total_spent = payments.aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0')
            
            # Calculate days since signup
            days_since_signup = (timezone.now().date() - user.date_joined.date()).days
            if days_since_signup == 0:
                days_since_signup = 1
            
            # Calculate average spend per day
            avg_daily_spend = total_spent / days_since_signup
            
            # Estimate lifetime (assume 2 years average)
            estimated_lifetime_days = 730
            estimated_ltv = avg_daily_spend * estimated_lifetime_days
            
            return {
                'user_id': str(user_id),
                'total_spent': float(total_spent),
                'days_since_signup': days_since_signup,
                'avg_daily_spend': float(avg_daily_spend),
                'estimated_ltv': float(estimated_ltv)
            }
            
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error calculating LTV for user {user_id}: {str(e)}")
            return None
    
    @staticmethod
    def calculate_driver_efficiency_score(driver_id, date=None):
        """Calculate driver efficiency score"""
        if not date:
            date = timezone.now().date()
        
        try:
            driver = User.objects.get(id=driver_id, user_type='driver')
            
            # Get driver performance for the date
            try:
                performance = DriverPerformanceAnalytics.objects.get(
                    driver=driver,
                    date=date
                )
            except DriverPerformanceAnalytics.DoesNotExist:
                return None
            
            # Calculate efficiency components
            utilization_score = min(performance.utilization_rate, 100) / 100  # 0-1
            acceptance_score = performance.acceptance_rate / 100  # 0-1
            completion_score = performance.completion_rate / 100  # 0-1
            rating_score = (performance.avg_rating - 1) / 4  # Convert 1-5 to 0-1
            
            # Weighted efficiency score
            efficiency_score = (
                utilization_score * 0.3 +
                acceptance_score * 0.25 +
                completion_score * 0.25 +
                rating_score * 0.2
            ) * 100
            
            return {
                'driver_id': str(driver_id),
                'date': date.isoformat(),
                'efficiency_score': round(efficiency_score, 2),
                'components': {
                    'utilization': round(utilization_score * 100, 2),
                    'acceptance': round(acceptance_score * 100, 2),
                    'completion': round(completion_score * 100, 2),
                    'rating': round(rating_score * 100, 2)
                }
            }
            
        except User.DoesNotExist:
            return None
        except Exception as e:
            logger.error(f"Error calculating efficiency score for driver {driver_id}: {str(e)}")
            return None
    
    @staticmethod
    def calculate_market_penetration(geographic_area=None):
        """Calculate market penetration metrics"""
        try:
            # This would calculate how well the platform is doing in a specific area
            # For now, we'll provide a simplified implementation
            
            total_population = 1000000  # Placeholder - would come from census data
            total_users = User.objects.count()
            active_users = User.objects.filter(
                last_login__gte=timezone.now() - timedelta(days=30)
            ).count()
            
            penetration_rate = (total_users / total_population) * 100
            active_penetration_rate = (active_users / total_population) * 100
            
            return {
                'geographic_area': geographic_area or 'All Areas',
                'total_population': total_population,
                'total_users': total_users,
                'active_users': active_users,
                'penetration_rate': round(penetration_rate, 4),
                'active_penetration_rate': round(active_penetration_rate, 4)
            }
            
        except Exception as e:
            logger.error(f"Error calculating market penetration: {str(e)}")
            return None
