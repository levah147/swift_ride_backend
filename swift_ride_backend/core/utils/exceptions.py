"""
Custom exception handling for Swift Ride API.
"""

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

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
