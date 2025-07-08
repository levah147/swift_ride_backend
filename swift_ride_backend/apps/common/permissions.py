"""
Common permissions for Swift Ride project.
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsDriverOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow drivers to perform certain actions.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'driver_profile') and
            request.user.driver_profile.is_verified
        )


class IsRiderOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow riders to perform certain actions.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_authenticated and 
            hasattr(request.user, 'rider_profile')
        )


class IsActiveUser(permissions.BasePermission):
    """
    Custom permission to only allow active users.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_active and
            not getattr(request.user, 'is_deactivated', False)
        )


class IsVerifiedDriver(permissions.BasePermission):
    """
    Custom permission to only allow verified drivers.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            hasattr(request.user, 'driver_profile') and
            request.user.driver_profile.is_verified and
            request.user.driver_profile.verification_status == 'approved'
        )


class IsAdminOrOwner(permissions.BasePermission):
    """
    Custom permission to allow admin users or object owners.
    """
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_staff or 
            request.user.is_superuser or
            obj.user == request.user
        )
