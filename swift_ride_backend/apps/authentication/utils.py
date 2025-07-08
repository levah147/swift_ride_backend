"""
Utility functions for authentication app.
"""

import random
import string
from django.conf import settings
from django.utils import timezone


def generate_otp(length=6):
    """
    Generate a random OTP code.
    """
    return ''.join(random.choices(string.digits, k=length))


def is_rate_limited(phone_number, max_attempts=5, window_minutes=15):
    """
    Check if phone number is rate limited for OTP requests.
    """
    from apps.authentication.models import OTP
    from apps.users.models import CustomUser
    
    try:
        user = CustomUser.objects.get(phone_number=phone_number)
        recent_attempts = OTP.objects.get_recent_attempts(
            phone_number, window_minutes
        )
        return recent_attempts >= max_attempts
    except CustomUser.DoesNotExist:
        return False


def format_phone_number(phone_number):
    """
    Format phone number to international format.
    """
    # Remove any non-digit characters
    digits_only = ''.join(filter(str.isdigit, str(phone_number)))
    
    # Handle Nigerian numbers
    if digits_only.startswith('0') and len(digits_only) == 11:
        # Convert 0801234567 to +2348012345678
        return f"+234{digits_only[1:]}"
    elif digits_only.startswith('234') and len(digits_only) == 13:
        # Add + if missing
        return f"+{digits_only}"
    elif len(digits_only) == 10:
        # Assume it's missing country code and leading 0
        return f"+234{digits_only}"
    
    return phone_number


def get_client_ip(request):
    """
    Get client IP address from request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def mask_phone_number(phone_number):
    """
    Mask phone number for security purposes.
    """
    phone_str = str(phone_number)
    if len(phone_str) >= 4:
        return f"{phone_str[:4]}****{phone_str[-2:]}"
    return "****"
