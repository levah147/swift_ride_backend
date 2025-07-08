"""
Common exceptions for Swift Ride project.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
import logging

logger = logging.getLogger(__name__)


class SwiftRideException(Exception):
    """Base exception for Swift Ride application."""
    default_message = "An error occurred"
    default_code = "error"
    
    def __init__(self, message=None, code=None):
        self.message = message or self.default_message
        self.code = code or self.default_code
        super().__init__(self.message)


class RideNotAvailableException(SwiftRideException):
    """Raised when a ride is not available."""
    default_message = "Ride is not available"
    default_code = "ride_not_available"


class DriverNotAvailableException(SwiftRideException):
    """Raised when no drivers are available."""
    default_message = "No drivers available in your area"
    default_code = "driver_not_available"


class PaymentFailedException(SwiftRideException):
    """Raised when payment processing fails."""
    default_message = "Payment processing failed"
    default_code = "payment_failed"


class InsufficientFundsException(SwiftRideException):
    """Raised when user has insufficient funds."""
    default_message = "Insufficient funds in wallet"
    default_code = "insufficient_funds"


class InvalidLocationException(SwiftRideException):
    """Raised when location data is invalid."""
    default_message = "Invalid location data"
    default_code = "invalid_location"


class RideAlreadyAcceptedException(SwiftRideException):
    """Raised when trying to accept an already accepted ride."""
    default_message = "Ride has already been accepted"
    default_code = "ride_already_accepted"


class UnauthorizedActionException(SwiftRideException):
    """Raised when user tries to perform unauthorized action."""
    default_message = "You are not authorized to perform this action"
    default_code = "unauthorized_action"


class VerificationRequiredException(SwiftRideException):
    """Raised when verification is required."""
    default_message = "Account verification required"
    default_code = "verification_required"


def custom_exception_handler(exc, context):
    """
    Custom exception handler for Swift Ride API.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Log the exception
    logger.error(f"Exception occurred: {exc}", exc_info=True)
    
    if response is not None:
        custom_response_data = {
            'success': False,
            'error': {
                'code': getattr(exc, 'default_code', 'error'),
                'message': str(exc),
                'details': response.data
            }
        }
        response.data = custom_response_data
        return response
    
    # Handle Django validation errors
    if isinstance(exc, DjangoValidationError):
        return Response({
            'success': False,
            'error': {
                'code': 'validation_error',
                'message': 'Validation failed',
                'details': exc.message_dict if hasattr(exc, 'message_dict') else [str(exc)]
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle 404 errors
    if isinstance(exc, Http404):
        return Response({
            'success': False,
            'error': {
                'code': 'not_found',
                'message': 'Resource not found',
                'details': str(exc)
            }
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Handle Swift Ride custom exceptions
    if isinstance(exc, SwiftRideException):
        return Response({
            'success': False,
            'error': {
                'code': exc.code,
                'message': exc.message,
                'details': None
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle unexpected errors
    return Response({
        'success': False,
        'error': {
            'code': 'internal_error',
            'message': 'An unexpected error occurred',
            'details': str(exc) if settings.DEBUG else None
        }
    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
