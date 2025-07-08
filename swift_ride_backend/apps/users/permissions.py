"""
Custom permissions for the users app.
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj == request.user


class IsDriverOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow drivers to perform certain actions.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return (
            request.user.is_authenticated and 
            request.user.user_type in ['driver', 'admin']
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
            request.user.user_type in ['rider', 'admin']
        )


class IsProfileOwner(permissions.BasePermission):
    """
    Custom permission to only allow users to access their own profile.
    """
    def has_object_permission(self, request, view, obj):
        # Check if the user is accessing their own profile
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return obj == request.user


class IsVerifiedUser(permissions.BasePermission):
    """
    Custom permission to only allow verified users.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.is_verified
        )


class CanManageDriverProfile(permissions.BasePermission):
    """
    Custom permission for driver profile management.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type in ['driver', 'admin'] and
            request.user.is_verified
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user


class CanManageRiderProfile(permissions.BasePermission):
    """
    Custom permission for rider profile management.
    """
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type in ['rider', 'admin'] and
            request.user.is_verified
        )
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        return obj.user == request.user
