"""
Custom exception handling for Swift Ride API.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError


# Custom Exception Classes
class ValidationError(DjangoValidationError):
    """Custom validation error that extends Django's ValidationError"""
    pass


class LocationServiceError(Exception):
    """Base exception for location service errors"""
    pass


class GeocodeError(LocationServiceError):
    """Raised when geocoding fails"""
    pass


class RouteCalculationError(LocationServiceError):
    """Raised when route calculation fails"""
    pass


class ServiceZoneError(LocationServiceError):
    """Raised when service zone operations fail"""
    pass


class PlaceNotFoundError(LocationServiceError):
    """Raised when a place cannot be found"""
    pass


class InvalidCoordinatesError(ValidationError):
    """Raised when coordinates are invalid"""
    pass


class APIError(Exception):
    """Base exception for external API errors"""
    def __init__(self, message, status_code=None, response=None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class GoogleMapsAPIError(APIError):
    """Raised when Google Maps API calls fail"""
    pass


class ThirdPartyServiceError(APIError):
    """Raised when third-party service calls fail"""
    pass


# Exception Handler Function
def custom_exception_handler(exc, context):
    """
    Custom exception handler for the API.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # If response is already handled by DRF, return it
    if response is not None:
        return response
    
    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        return Response(
            {'detail': exc.messages},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle database integrity errors
    if isinstance(exc, IntegrityError):
        return Response(
            {'detail': 'Database integrity error occurred.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Handle any other exceptions
    return Response(
        {'detail': 'An unexpected error occurred.'},
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )