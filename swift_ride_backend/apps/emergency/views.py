from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count, Q, Avg
from apps.emergency.models import (
    EmergencyContact, EmergencyAlert, SafetyCheck, 
    EmergencyResponse, LocationShare, EmergencySettings
)
from apps.emergency.serializers import (
    EmergencyContactSerializer, EmergencyAlertSerializer,
    EmergencyAlertCreateSerializer, SafetyCheckSerializer,
    SafetyCheckResponseSerializer, EmergencyResponseSerializer,
    LocationShareSerializer, LocationUpdateSerializer,
    EmergencySettingsSerializer, PanicButtonSerializer,
    EmergencyStatsSerializer
)
from apps.emergency.services.emergency_service import EmergencyService
from apps.emergency.services.location_service import LocationService
from apps.emergency.services.contact_service import ContactService
from core.utils.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class EmergencyContactListCreateView(generics.ListCreateAPIView):
    """List and create emergency contacts"""
    
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EmergencyContact.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-is_primary', 'name')


class EmergencyContactDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, and delete emergency contacts"""
    
    serializer_class = EmergencyContactSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EmergencyContact.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        """Soft delete by setting is_active to False"""
        instance.is_active = False
        instance.save()


class EmergencyAlertListCreateView(generics.ListCreateAPIView):
    """List and create emergency alerts"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EmergencyAlertCreateSerializer
        return EmergencyAlertSerializer
    
    def get_queryset(self):
        queryset = EmergencyAlert.objects.filter(user=self.request.user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by alert type
        alert_type = self.request.query_params.get('alert_type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        return queryset.order_by('-created_at')
    
    def perform_create(self, serializer):
        """Create emergency alert and trigger response"""
        alert = serializer.save()
        
        # Trigger emergency response
        try:
            EmergencyService._initiate_emergency_response(alert)
            EmergencyService._send_emergency_notifications(alert)
        except Exception as e:
            logger.error(f"Error triggering emergency response: {str(e)}")


class EmergencyAlertDetailView(generics.RetrieveUpdateAPIView):
    """Retrieve and update emergency alerts"""
    
    serializer_class = EmergencyAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EmergencyAlert.objects.filter(user=self.request.user)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def panic_button(request):
    """Trigger panic button"""
    try:
        serializer = PanicButtonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        location = None
        
        if data.get('latitude') and data.get('longitude'):
            location = {
                'latitude': data['latitude'],
                'longitude': data['longitude'],
                'address': data.get('address')
            }
        
        # Get ride if provided
        ride = None
        if data.get('ride_id'):
            from apps.rides.models import Ride
            try:
                ride = Ride.objects.get(id=data['ride_id'], rider=request.user)
            except Ride.DoesNotExist:
                pass
        
        # Trigger panic button
        alert = EmergencyService.trigger_panic_button(
            user=request.user,
            ride=ride,
            location=location,
            description=data.get('description'),
            audio_file=data.get('audio_recording')
        )
        
        serializer = EmergencyAlertSerializer(alert)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error in panic button: {str(e)}")
        return Response(
            {'error': 'Failed to trigger panic button'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def acknowledge_alert(request, alert_id):
    """Acknowledge an emergency alert"""
    try:
        alert = EmergencyService.acknowledge_alert(
            alert_id=alert_id,
            acknowledged_by=request.user
        )
        
        serializer = EmergencyAlertSerializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error acknowledging alert: {str(e)}")
        return Response(
            {'error': 'Failed to acknowledge alert'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def resolve_alert(request, alert_id):
    """Resolve an emergency alert"""
    try:
        resolution_notes = request.data.get('resolution_notes', '')
        
        alert = EmergencyService.resolve_alert(
            alert_id=alert_id,
            resolved_by=request.user,
            resolution_notes=resolution_notes
        )
        
        serializer = EmergencyAlertSerializer(alert)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error resolving alert: {str(e)}")
        return Response(
            {'error': 'Failed to resolve alert'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class SafetyCheckListView(generics.ListAPIView):
    """List safety checks for user"""
    
    serializer_class = SafetyCheckSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return SafetyCheck.objects.filter(
            user=self.request.user
        ).order_by('-scheduled_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def complete_safety_check(request, check_id):
    """Complete a safety check"""
    try:
        serializer = SafetyCheckResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        location = None
        
        if data.get('latitude') and data.get('longitude'):
            location = {
                'latitude': data['latitude'],
                'longitude': data['longitude']
            }
        
        check = EmergencyService.complete_safety_check(
            check_id=check_id,
            is_safe=data['is_safe'],
            response_message=data.get('response_message'),
            location=location
        )
        
        serializer = SafetyCheckSerializer(check)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error completing safety check: {str(e)}")
        return Response(
            {'error': 'Failed to complete safety check'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class LocationShareListView(generics.ListAPIView):
    """List location shares for user"""
    
    serializer_class = LocationShareSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LocationShare.objects.filter(
            Q(user=self.request.user) | Q(shared_with=self.request.user)
        ).distinct().order_by('-created_at')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_location_share(request, share_id):
    """Update location for a location share"""
    try:
        serializer = LocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        
        share = EmergencyService.update_location_share(
            share_id=share_id,
            latitude=data['latitude'],
            longitude=data['longitude']
        )
        
        serializer = LocationShareSerializer(share)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error updating location share: {str(e)}")
        return Response(
            {'error': 'Failed to update location'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def nearby_emergency_services(request):
    """Get nearby emergency services"""
    try:
        latitude = float(request.query_params.get('latitude'))
        longitude = float(request.query_params.get('longitude'))
        service_type = request.query_params.get('type', 'hospital')
        radius_km = int(request.query_params.get('radius', 10))
        
        services = LocationService.find_nearby_emergency_services(
            latitude=latitude,
            longitude=longitude,
            service_type=service_type,
            radius_km=radius_km
        )
        
        return Response({'services': services}, status=status.HTTP_200_OK)
        
    except (ValueError, TypeError):
        return Response(
            {'error': 'Invalid latitude or longitude'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error finding emergency services: {str(e)}")
        return Response(
            {'error': 'Failed to find emergency services'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def emergency_stats(request):
    """Get emergency statistics for user"""
    try:
        user = request.user
        
        # Get alert counts
        alerts = EmergencyAlert.objects.filter(user=user)
        total_alerts = alerts.count()
        active_alerts = alerts.filter(status__in=['active', 'acknowledged', 'responding']).count()
        resolved_alerts = alerts.filter(status='resolved').count()
        false_alarms = alerts.filter(status='false_alarm').count()
        
        # Calculate average response time
        acknowledged_alerts = alerts.filter(acknowledged_at__isnull=False)
        avg_response_time = None
        if acknowledged_alerts.exists():
            response_times = []
            for alert in acknowledged_alerts:
                if alert.response_time:
                    response_times.append(alert.response_time.total_seconds())
            
            if response_times:
                avg_seconds = sum(response_times) / len(response_times)
                avg_response_time = timezone.timedelta(seconds=avg_seconds)
        
        # Get alerts by type
        alerts_by_type = dict(
            alerts.values('alert_type').annotate(count=Count('id')).values_list('alert_type', 'count')
        )
        
        # Get alerts by severity
        alerts_by_severity = dict(
            alerts.values('severity').annotate(count=Count('id')).values_list('severity', 'count')
        )
        
        # Monthly trend (last 12 months)
        from datetime import datetime, timedelta
        monthly_trend = []
        for i in range(12):
            month_start = timezone.now().replace(day=1) - timedelta(days=30*i)
            month_end = month_start + timedelta(days=30)
            
            month_alerts = alerts.filter(
                created_at__gte=month_start,
                created_at__lt=month_end
            ).count()
            
            monthly_trend.append({
                'month': month_start.strftime('%Y-%m'),
                'alerts': month_alerts
            })
        
        monthly_trend.reverse()
        
        stats_data = {
            'total_alerts': total_alerts,
            'active_alerts': active_alerts,
            'resolved_alerts': resolved_alerts,
            'false_alarms': false_alarms,
            'average_response_time': avg_response_time,
            'alerts_by_type': alerts_by_type,
            'alerts_by_severity': alerts_by_severity,
            'monthly_trend': monthly_trend
        }
        
        serializer = EmergencyStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error getting emergency stats: {str(e)}")
        return Response(
            {'error': 'Failed to get emergency statistics'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class EmergencySettingsView(generics.RetrieveUpdateAPIView):
    """Get and update emergency settings"""
    
    serializer_class = EmergencySettingsSerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get_object(self):
        return EmergencySettings.get_settings()
