"""
Views for the notifications app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone

from apps.notifications.models import (
    Notification, NotificationPreference, DeviceToken, NotificationBatch
)
from apps.notifications.serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    DeviceTokenSerializer, DeviceTokenCreateSerializer,
    NotificationBatchSerializer, BulkNotificationSerializer
)
from apps.notifications.services.notification_service import NotificationService


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get notifications for the current user."""
        return NotificationService.get_user_notifications(self.request.user)
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count."""
        count = NotificationService.get_unread_count(request.user)
        return Response({'unread_count': count})
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications."""
        notifications = NotificationService.get_user_notifications(
            request.user, 
            unread_only=True
        )
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read."""
        success, message = NotificationService.mark_notification_as_read(pk, request.user)
        
        if success:
            return Response({'message': message})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read."""
        notifications = Notification.objects.filter(
            recipient=request.user,
            is_deleted=False
        ).exclude(status=Notification.Status.READ)
        
        count = notifications.count()
        notifications.update(
            status=Notification.Status.READ,
            read_at=timezone.now()
        )
        
        return Response({
            'message': f'{count} notifications marked as read'
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for notification preferences.
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get notification preferences for the current user."""
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Get or create notification preferences for the current user."""
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def list(self, request):
        """Get notification preferences for the current user."""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Update notification preferences."""
        preferences = self.get_object()
        serializer = self.get_serializer(preferences, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeviceTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet for device tokens.
    """
    serializer_class = DeviceTokenSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get device tokens for the current user."""
        return DeviceToken.objects.filter(user=self.request.user)
    
    def get_serializer_class(self):
        """Get serializer class based on action."""
        if self.action == 'create':
            return DeviceTokenCreateSerializer
        return DeviceTokenSerializer
    
    def create(self, request):
        """Register a new device token."""
        serializer = DeviceTokenCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            device_token, created = NotificationService.register_device_token(
                user=request.user,
                token=data['token'],
                platform=data['platform'],
                device_id=data.get('device_id'),
                device_name=data.get('device_name'),
                app_version=data.get('app_version')
            )
            
            response_serializer = DeviceTokenSerializer(device_token)
            status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
            
            return Response(response_serializer.data, status=status_code)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a device token."""
        device_token = self.get_object()
        device_token.is_active = False
        device_token.save()
        
        return Response({'message': 'Device token deactivated'})


class NotificationBatchViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for notification batches (admin only).
    """
    serializer_class = NotificationBatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get notification batches (admin only)."""
        if self.request.user.is_staff:
            return NotificationBatch.objects.all()
        return NotificationBatch.objects.none()
    
    @action(detail=False, methods=['post'])
    def send_bulk(self, request):
        """Send bulk notification (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = BulkNotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Get recipients based on filters
            from apps.users.models import CustomUser
            recipients = CustomUser.objects.filter(**data.get('recipient_filters', {}))
            
            if not recipients.exists():
                return Response(
                    {'error': 'No recipients found with the specified filters'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Send bulk notification
            batch = NotificationService.send_bulk_notification(
                recipients=list(recipients),
                notification_type=data['notification_type'],
                context=data.get('context', {}),
                channels=data.get('channels'),
                scheduled_at=data.get('scheduled_at')
            )
            
            if batch:
                return Response(
                    NotificationBatchSerializer(batch).data,
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {'error': 'Failed to create notification batch'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
