from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from apps.analytics.models import (
    AnalyticsEvent, DailyAnalytics, UserAnalytics, 
    RideAnalytics, GeographicAnalytics, DriverPerformanceAnalytics,
    PaymentAnalytics, RevenueAnalytics, AnalyticsReport, AnalyticsSettings
)
from apps.analytics.serializers import (
    AnalyticsEventSerializer, DailyAnalyticsSerializer, UserAnalyticsSerializer,
    RideAnalyticsSerializer, GeographicAnalyticsSerializer, 
    DriverPerformanceAnalyticsSerializer, PaymentAnalyticsSerializer,
    RevenueAnalyticsSerializer, AnalyticsReportSerializer, AnalyticsSettingsSerializer,
    DashboardDataSerializer, ExecutiveSummarySerializer, RealTimeDashboardSerializer,
    TrackEventSerializer, ReportGenerationSerializer, MetricsSerializer
)
from apps.analytics.services.analytics_service import AnalyticsService
from apps.analytics.services.reporting_service import ReportingService, MetricsService
from core.utils.exceptions import ValidationError
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AnalyticsEventListCreateView(generics.ListCreateAPIView):
    """List and create analytics events"""
    
    serializer_class = AnalyticsEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = AnalyticsEvent.objects.all()
        
        # Filter by user if specified
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by event type
        event_type = self.request.query_params.get('event_type')
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(
                created_at__date__range=[start_date, end_date]
            )
        
        return queryset.order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def track_event(request):
    """Track an analytics event"""
    try:
        serializer = TrackEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        location = None
        
        if data.get('latitude') and data.get('longitude'):
            location = {
                'latitude': data['latitude'],
                'longitude': data['longitude']
            }
        
        event = AnalyticsService.track_event(
            event_type=data['event_type'],
            user=request.user,
            properties=data.get('properties', {}),
            location=location,
            session_id=data.get('session_id'),
            platform=data.get('platform', 'api'),
            request=request
        )
        
        if event:
            serializer = AnalyticsEventSerializer(event)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Failed to track event'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        logger.error(f"Error tracking event: {str(e)}")
        return Response(
            {'error': 'Failed to track event'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class DailyAnalyticsListView(generics.ListAPIView):
    """List daily analytics"""
    
    serializer_class = DailyAnalyticsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = DailyAnalytics.objects.all()
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        
        return queryset.order_by('-date')


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def dashboard_data(request):
    """Get analytics dashboard data"""
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        dashboard_data = AnalyticsService.get_analytics_dashboard_data(
            start_date=start_date,
            end_date=end_date
        )
        
        if dashboard_data:
            serializer = DashboardDataSerializer(dashboard_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to get dashboard data'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}")
        return Response(
            {'error': 'Failed to get dashboard data'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def executive_summary(request):
    """Get executive summary report"""
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        summary = ReportingService.generate_executive_summary(
            start_date=start_date,
            end_date=end_date
        )
        
        if summary:
            serializer = ExecutiveSummarySerializer(summary)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to generate executive summary'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error generating executive summary: {str(e)}")
        return Response(
            {'error': 'Failed to generate executive summary'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def real_time_dashboard(request):
    """Get real-time dashboard data"""
    try:
        dashboard_data = ReportingService.generate_real_time_dashboard()
        
        if dashboard_data:
            serializer = RealTimeDashboardSerializer(dashboard_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to get real-time dashboard data'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        logger.error(f"Error getting real-time dashboard: {str(e)}")
        return Response(
            {'error': 'Failed to get real-time dashboard data'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class UserAnalyticsDetailView(generics.RetrieveAPIView):
    """Get analytics for a specific user"""
    
    serializer_class = UserAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        user_id = self.kwargs.get('user_id')
        
        # Users can only view their own analytics unless they're admin
        if not self.request.user.is_staff and str(self.request.user.id) != user_id:
            raise PermissionDenied("You can only view your own analytics")
        
        analytics_data = AnalyticsService.get_user_analytics(user_id)
        if analytics_data:
            return analytics_data['user_analytics']
        else:
            raise NotFound("User analytics not found")


class GeographicAnalyticsListView(generics.ListAPIView):
    """List geographic analytics"""
    
    serializer_class = GeographicAnalyticsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        queryset = GeographicAnalytics.objects.all()
        
        # Filter by date
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(date=date)
        
        # Filter by area
        area = self.request.query_params.get('area')
        if area:
            queryset = queryset.filter(area_name__icontains=area)
        
        return queryset.order_by('-date', 'area_name')


class DriverPerformanceAnalyticsListView(generics.ListAPIView):
    """List driver performance analytics"""
    
    serializer_class = DriverPerformanceAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = DriverPerformanceAnalytics.objects.all()
        
        # Drivers can only see their own performance
        if not self.request.user.is_staff:
            queryset = queryset.filter(driver=self.request.user)
        
        # Filter by driver
        driver_id = self.request.query_params.get('driver_id')
        if driver_id and self.request.user.is_staff:
            queryset = queryset.filter(driver_id=driver_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        
        return queryset.order_by('-date')


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def driver_performance_report(request):
    """Get driver performance report"""
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        driver_id = request.query_params.get('driver_id')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        report = ReportingService.generate_driver_performance_report(
            start_date=start_date,
            end_date=end_date,
            driver_id=driver_id
        )
        
        if report:
            return Response(report, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to generate driver performance report'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error generating driver performance report: {str(e)}")
        return Response(
            {'error': 'Failed to generate driver performance report'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def financial_report(request):
    """Get financial report"""
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        report = ReportingService.generate_financial_report(
            start_date=start_date,
            end_date=end_date
        )
        
        if report:
            return Response(report, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to generate financial report'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error generating financial report: {str(e)}")
        return Response(
            {'error': 'Failed to generate financial report'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def user_engagement_report(request):
    """Get user engagement report"""
    try:
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if start_date:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        if end_date:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        report = ReportingService.generate_user_engagement_report(
            start_date=start_date,
            end_date=end_date
        )
        
        if report:
            return Response(report, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to generate user engagement report'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error generating user engagement report: {str(e)}")
        return Response(
            {'error': 'Failed to generate user engagement report'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def generate_report(request):
    """Generate a custom analytics report"""
    try:
        serializer = ReportGenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        report = AnalyticsService.generate_analytics_report(
            report_type=data['report_type'],
            start_date=data['start_date'],
            end_date=data['end_date'],
            filters=data.get('filters', {})
        )
        
        if report:
            serializer = AnalyticsReportSerializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Failed to generate report'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return Response(
            {'error': 'Failed to generate report'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AnalyticsReportListView(generics.ListAPIView):
    """List analytics reports"""
    
    serializer_class = AnalyticsReportSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_queryset(self):
        return AnalyticsReport.objects.all().order_by('-created_at')


class AnalyticsReportDetailView(generics.RetrieveAPIView):
    """Get analytics report details"""
    
    serializer_class = AnalyticsReportSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = AnalyticsReport.objects.all()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_metrics(request, user_id):
    """Get specific metrics for a user"""
    try:
        # Users can only view their own metrics unless they're admin
        if not request.user.is_staff and str(request.user.id) != user_id:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        metrics = {}
        
        # Calculate user lifetime value
        ltv = MetricsService.calculate_user_lifetime_value(user_id)
        if ltv:
            metrics['user_lifetime_value'] = ltv
        
        # Calculate driver efficiency if user is a driver
        from apps.users.models import User
        try:
            user = User.objects.get(id=user_id)
            if user.user_type == 'driver':
                efficiency = MetricsService.calculate_driver_efficiency_score(user_id)
                if efficiency:
                    metrics['driver_efficiency_score'] = efficiency
        except User.DoesNotExist:
            pass
        
        serializer = MetricsSerializer(metrics)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting user metrics: {str(e)}")
        return Response(
            {'error': 'Failed to get user metrics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAdminUser])
def market_penetration(request):
    """Get market penetration metrics"""
    try:
        geographic_area = request.query_params.get('area')
        
        penetration = MetricsService.calculate_market_penetration(
            geographic_area=geographic_area
        )
        
        if penetration:
            return Response(penetration, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': 'Failed to calculate market penetration'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except Exception as e:
        logger.error(f"Error calculating market penetration: {str(e)}")
        return Response(
            {'error': 'Failed to calculate market penetration'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class AnalyticsSettingsView(generics.RetrieveUpdateAPIView):
    """Get and update analytics settings"""
    
    serializer_class = AnalyticsSettingsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        return AnalyticsSettings.get_settings()


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def generate_daily_analytics(request):
    """Manually trigger daily analytics generation"""
    try:
        date_str = request.data.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        analytics = AnalyticsService.generate_daily_analytics(date)
        
        if analytics:
            serializer = DailyAnalyticsSerializer(analytics)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response(
                {'error': 'Failed to generate daily analytics'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
    except ValueError:
        return Response(
            {'error': 'Invalid date format. Use YYYY-MM-DD'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error generating daily analytics: {str(e)}")
        return Response(
            {'error': 'Failed to generate daily analytics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
