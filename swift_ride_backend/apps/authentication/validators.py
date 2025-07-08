"""
Validators for authentication app.
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def validate_otp_code(value):
    """
    Validate OTP code format.
    """
    if not value.isdigit():
        raise ValidationError(
            _('OTP code must contain only digits.'),
            code='invalid_otp_format'
        )
    
    if len(value) != 6:
        raise ValidationError(
            _('OTP code must be exactly 6 digits.'),
            code='invalid_otp_length'
        )


def validate_nigerian_phone(value):
    """
    Validate Nigerian phone number format.
    """
    # Convert to string and remove any non-digit characters
    phone_str = re.sub(r'\D', '', str(value))
    
    # Check various Nigerian phone number formats
    valid_patterns = [
        r'^0[789][01]\d{8}$',  # 0801234567, 0701234567, 0901234567
        r'^234[789][01]\d{8}$',  # 2348012345678
        r'^[789][01]\d{8}$',  # 8012345678
    ]
    
    is_valid = any(re.match(pattern, phone_str) for pattern in valid_patterns)
    
    if not is_valid:
        raise ValidationError(
            _('Enter a valid Nigerian phone number.'),
            code='invalid_phone'
        )


def validate_strong_password(value):
    """
    Validate password strength (if needed for admin users).
    """
    if len(value) < 8:
        raise ValidationError(
            _('Password must be at least 8 characters long.'),
            code='password_too_short'
        )
    
    if not re.search(r'[A-Z]', value):
        raise ValidationError(
            _('Password must contain at least one uppercase letter.'),
            code='password_no_upper'
        )
    
    if not re.search(r'[a-z]', value):
        raise ValidationError(
            _('Password must contain at least one lowercase letter.'),
            code='password_no_lower'
        )
    
    if not re.search(r'\d', value):
        raise ValidationError(
            _('Password must contain at least one digit.'),
            code='password_no_digit'
        )
