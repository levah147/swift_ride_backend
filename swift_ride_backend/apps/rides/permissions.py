"""
Custom permissions for rides app.
"""

from rest_framework import permissions
from django.utils import timezone

from apps.rides.models import Ride


class IsRiderOrDriver(permissions.BasePermission):
    """
    Permission to check if user is either the rider or driver of the ride.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            return request.user == obj.rider or request.user == obj.driver
        return False


class IsRider(permissions.BasePermission):
    """
    Permission to check if user is the rider of the ride.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            return request.user == obj.rider
        return False


class IsDriver(permissions.BasePermission):
    """
    Permission to check if user is the driver of the ride.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            return request.user == obj.driver
        return False


class CanCancelRide(permissions.BasePermission):
    """
    Permission to check if user can cancel the ride.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            # Check if user is involved in the ride
            if request.user != obj.rider and request.user != obj.driver:
                return False
            
            # Check if ride can be cancelled
            return obj.can_cancel
        return False


class CanMakeBargainOffer(permissions.BasePermission):
    """
    Permission to check if user can make a bargain offer.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            # Check if user is involved in the ride
            if request.user != obj.rider and request.user != obj.driver:
                return False
            
            # Check if ride is in bargaining state
            return obj.is_bargaining
        return False


class IsActiveDriver(permissions.BasePermission):
    """
    Permission to check if user is an active driver.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.is_driver and
            hasattr(request.user, 'driver_profile') and
            request.user.driver_profile.is_active and
            request.user.driver_profile.is_verified
        )


class CanAcceptRide(permissions.BasePermission):
    """
    Permission to check if driver can accept a ride.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            # Must be a driver
            if not request.user.is_driver:
                return False
            
            # Driver must be active and verified
            if not (hasattr(request.user, 'driver_profile') and
                    request.user.driver_profile.is_active and
                    request.user.driver_profile.is_verified):
                return False
            
            # Ride must be in searchable state
            return obj.status in [
                Ride.RideStatus.REQUESTED,
                Ride.RideStatus.SEARCHING,
                Ride.RideStatus.BARGAINING
            ]
        return False


class CanUpdateRideStatus(permissions.BasePermission):
    """
    Permission to check if user can update ride status.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Ride):
            # Check if user is involved in the ride
            if request.user != obj.rider and request.user != obj.driver:
                return False
            
            # Get the new status from request data
            new_status = request.data.get('status')
            
            if new_status == Ride.RideStatus.CANCELLED:
                return obj.can_cancel
            
            elif new_status == Ride.RideStatus.ACCEPTED:
                return (request.user.is_driver and 
                        obj.status in [Ride.RideStatus.SEARCHING, Ride.RideStatus.BARGAINING])
            
            elif new_status == Ride.RideStatus.DRIVER_ARRIVED:
                return (request.user == obj.driver and 
                        obj.status == Ride.RideStatus.DRIVER_ASSIGNED)
            
            elif new_status == Ride.RideStatus.IN_PROGRESS:
                return (request.user == obj.driver and 
                        obj.status == Ride.RideStatus.DRIVER_ARRIVED)
            
            elif new_status == Ride.RideStatus.COMPLETED:
                return (request.user == obj.driver and 
                        obj.status == Ride.RideStatus.IN_PROGRESS)
            
        return False
