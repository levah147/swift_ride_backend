"""
Custom validators for the users app.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password
from django.core.validators import RegexValidator
from datetime import date, timedelta


def validate_nigerian_phone(value):
    """
    Validate Nigerian phone number format.
    """
    # Remove all non-digit characters for validation
    phone_digits = re.sub(r'\D', '', value)
    
    # Nigerian phone number patterns
    valid_patterns = [
        r'^(234|0)(70|71|80|81|90|91)\d{8}$',  # Standard Nigerian numbers
        r'^(\+234)(70|71|80|81|90|91)\d{8}$',  # International format
    ]
    
    is_valid = False
    for pattern in valid_patterns:
        if re.match(pattern, value):
            is_valid = True
            break
    
    if not is_valid:
        raise ValidationError(
            _('Enter a valid Nigerian phone number (e.g., +2348012345678 or 08012345678)'),
            code='invalid_phone'
        )


def validate_license_number(value):
    """
    Validate Nigerian driver's license number format.
    """
    # Nigerian license format: ABC-12345678-AB (state code-8 digits-category)
    pattern = r'^[A-Z]{3}-\d{8}-[A-Z]{2}$'
    
    if not re.match(pattern, value.upper()):
        raise ValidationError(
            _('Enter a valid Nigerian driver\'s license number (e.g., LAG-12345678-AA)'),
            code='invalid_license'
        )


def validate_license_expiry(value):
    """
    Validate that license expiry date is in the future.
    """
    if value <= date.today():
        raise ValidationError(
            _('License expiry date must be in the future'),
            code='expired_license'
        )
    
    # Check if expiry is too far in the future (more than 10 years)
    max_expiry = date.today() + timedelta(days=365 * 10)
    if value > max_expiry:
        raise ValidationError(
            _('License expiry date cannot be more than 10 years in the future'),
            code='invalid_expiry_date'
        )


def validate_age(value):
    """
    Validate that user is at least 18 years old.
    """
    if not value:
        return
    
    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    
    if age < 18:
        raise ValidationError(
            _('You must be at least 18 years old to register'),
            code='underage'
        )
    
    if age > 100:
        raise ValidationError(
            _('Please enter a valid birth date'),
            code='invalid_age'
        )


def validate_emergency_contact(value):
    """
    Validate emergency contact phone number.
    """
    if value:
        validate_nigerian_phone(value)


def validate_referral_code(value):
    """
    Validate referral code format.
    """
    if not value:
        return
    
    # Referral code should be 6-10 alphanumeric characters
    pattern = r'^[A-Z0-9]{6,10}$'
    
    if not re.match(pattern, value.upper()):
        raise ValidationError(
            _('Referral code must be 6-10 alphanumeric characters'),
            code='invalid_referral_code'
        )


def validate_nin(value):
    """
    Validate Nigerian National Identification Number (NIN).
    """
    if not value:
        return
    
    # NIN is 11 digits
    pattern = r'^\d{11}$'
    
    if not re.match(pattern, value):
        raise ValidationError(
            _('NIN must be exactly 11 digits'),
            code='invalid_nin'
        )


def validate_bvn(value):
    """
    Validate Bank Verification Number (BVN).
    """
    if not value:
        return
    
    # BVN is 11 digits
    pattern = r'^\d{11}$'
    
    if not re.match(pattern, value):
        raise ValidationError(
            _('BVN must be exactly 11 digits'),
            code='invalid_bvn'
        )


def validate_strong_password(password):
    """
    Validate that password meets security requirements.
    """
    if len(password) < 8:
        raise ValidationError(
            _('Password must be at least 8 characters long'),
            code='password_too_short'
        )
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError(
            _('Password must contain at least one uppercase letter'),
            code='password_no_upper'
        )
    
    if not re.search(r'[a-z]', password):
        raise ValidationError(
            _('Password must contain at least one lowercase letter'),
            code='password_no_lower'
        )
    
    if not re.search(r'\d', password):
        raise ValidationError(
            _('Password must contain at least one digit'),
            code='password_no_digit'
        )
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError(
            _('Password must contain at least one special character'),
            code='password_no_special'
        )


# Regex validators for common fields
phone_validator = RegexValidator(
    regex=r'^(\+234|234|0)(70|71|80|81|90|91)\d{8}$',
    message=_('Enter a valid Nigerian phone number'),
    code='invalid_phone'
)

license_validator = RegexValidator(
    regex=r'^[A-Z]{3}-\d{8}-[A-Z]{2}$',
    message=_('Enter a valid Nigerian driver\'s license number'),
    code='invalid_license'
)

nin_validator = RegexValidator(
    regex=r'^\d{11}$',
    message=_('NIN must be exactly 11 digits'),
    code='invalid_nin'
)

bvn_validator = RegexValidator(
    regex=r'^\d{11}$',
    message=_('BVN must be exactly 11 digits'),
    code='invalid_bvn'
)

referral_code_validator = RegexValidator(
    regex=r'^[A-Z0-9]{6,10}$',
    message=_('Referral code must be 6-10 alphanumeric characters'),
    code='invalid_referral_code'
)
