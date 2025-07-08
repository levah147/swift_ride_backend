"""
Custom permissions for vehicles app.
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

User = get_user_model()


class IsVehicleOwner(permissions.BasePermission):
    """
    Permission to only allow owners of a vehicle to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        
        # Write permissions are only allowed to the owner of the vehicle
        return obj.owner == request.user


class IsDriverOrAdmin(permissions.BasePermission):
    """
    Permission to only allow drivers or admin users.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_driver or request.user.is_staff)
        )


class IsVehicleOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow vehicle owners or admin users.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated and
            (obj.owner == request.user or request.user.is_staff)
        )


class CanVerifyVehicles(permissions.BasePermission):
    """
    Permission for users who can verify vehicles (admin only).
    """
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and request.user.is_staff


class CanConductInspections(permissions.BasePermission):
    """
    Permission for users who can conduct vehicle inspections.
    """
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.is_staff or hasattr(request.user, 'inspector_profile'))
        )


class IsDocumentOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to allow document owners or admin users.
    """
    
    def has_object_permission(self, request, view, obj):
        return (
            request.user.is_authenticated and
            (obj.vehicle.owner == request.user or request.user.is_staff)
        )
