"""
Custom permissions for authentication app.
"""

from rest_framework.permissions import BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user


class IsVerifiedUser(BasePermission):
    """
    Permission to check if user is verified.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_verified', False)
        )


class CanRequestOTP(BasePermission):
    """
    Permission to check if user can request OTP.
    """
    
    def has_permission(self, request, view):
        # Allow unauthenticated users to request OTP
        return True
