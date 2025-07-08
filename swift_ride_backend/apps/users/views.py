"""
Views for the users app.
"""

from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.db import transaction

from .models import RiderProfile, DriverProfile, UserPreferences
from .serializers import (
    UserSerializer, UserBasicSerializer, RiderProfileSerializer,
    DriverProfileSerializer, UserPreferenceSerializer as UserPreferencesSerializer,
    UserUpdateSerializer
)
from .permissions import (
    IsOwnerOrReadOnly, IsProfileOwner, CanManageDriverProfile,
    CanManageRiderProfile, IsVerifiedUser
)

from .services.user_service import UserService
from .services.profile_service import ProfileService


User = get_user_model()


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update user profile.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    
    def get_object(self):
        return self.request.user
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return UserUpdateSerializer
        return UserSerializer


class UserListView(generics.ListAPIView):
    """
    List all users (admin only).
    """
    queryset = User.objects.all()
    serializer_class = UserBasicSerializer
    permission_classes = [permissions.IsAdminUser]


class UserDetailView(generics.RetrieveAPIView):
    """
    Retrieve user details (admin only or own profile).
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]


class RiderProfileView(generics.RetrieveUpdateAPIView):
    """
    Manage rider profile.
    """
    serializer_class = RiderProfileSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageRiderProfile]
    
    def get_object(self):
        rider_profile, created = RiderProfile.objects.get_or_create(
            user=self.request.user
        )
        return rider_profile
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class DriverProfileView(generics.RetrieveUpdateAPIView):
    """
    Manage driver profile.
    """
    serializer_class = DriverProfileSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageDriverProfile]
    
    def get_object(self):
        driver_profile, created = DriverProfile.objects.get_or_create(
            user=self.request.user
        )
        return driver_profile
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class UserPreferencesView(generics.RetrieveUpdateAPIView):
    """
    Manage user preferences.
    """
    serializer_class = UserPreferencesSerializer
    permission_classes = [permissions.IsAuthenticated, IsProfileOwner]
    
    def get_object(self):
        preferences, created = UserPreferences.objects.get_or_create(
            user=self.request.user
        )
        return preferences
    
    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class DriverStatusToggleView(APIView):
    """
    Toggle driver online/offline status.
    """
    permission_classes = [permissions.IsAuthenticated, CanManageDriverProfile]
    
    def post(self, request):
        try:
            driver_profile = DriverProfile.objects.get(user=request.user)
            driver_profile.is_online = not driver_profile.is_online
            driver_profile.save()
            
            return Response({
                'status': 'success',
                'is_online': driver_profile.is_online,
                'message': f'Driver status changed to {"online" if driver_profile.is_online else "offline"}'
            })
        except DriverProfile.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Driver profile not found'
            }, status=status.HTTP_404_NOT_FOUND)


class UserStatsView(APIView):
    """
    Get user statistics.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user_service = UserService()
        stats = user_service.get_user_stats(request.user)
        return Response(stats)


class NearbyDriversView(APIView):
    """
    Get nearby drivers for riders.
    """
    permission_classes = [permissions.IsAuthenticated, IsVerifiedUser]
    
    def post(self, request):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        radius = request.data.get('radius', 5)  # Default 5km radius
        
        if not latitude or not longitude:
            return Response({
                'status': 'error',
                'message': 'Latitude and longitude are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        profile_service = ProfileService()
        nearby_drivers = profile_service.get_nearby_drivers(
            latitude, longitude, radius
        )
        
        return Response({
            'status': 'success',
            'drivers': nearby_drivers
        })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_location(request):
    """
    Update user's current location.
    """
    latitude = request.data.get('latitude')
    longitude = request.data.get('longitude')
    
    if not latitude or not longitude:
        return Response({
            'status': 'error',
            'message': 'Latitude and longitude are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user_service = UserService()
    success = user_service.update_user_location(
        request.user, latitude, longitude
    )
    
    if success:
        return Response({
            'status': 'success',
            'message': 'Location updated successfully'
        })
    else:
        return Response({
            'status': 'error',
            'message': 'Failed to update location'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def deactivate_account(request):
    """
    Deactivate user account.
    """
    password = request.data.get('password')
    
    if not password:
        return Response({
            'status': 'error',
            'message': 'Password is required for account deactivation'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if not request.user.check_password(password):
        return Response({
            'status': 'error',
            'message': 'Invalid password'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user_service = UserService()
    success = user_service.deactivate_user(request.user)
    
    if success:
        return Response({
            'status': 'success',
            'message': 'Account deactivated successfully'
        })
    else:
        return Response({
            'status': 'error',
            'message': 'Failed to deactivate account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)