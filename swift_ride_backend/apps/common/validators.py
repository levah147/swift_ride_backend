"""
Common validators for Swift Ride project.
"""

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_nigerian_phone(value):
    """
    Validate Nigerian phone number format.
    Accepts formats: +234XXXXXXXXXX, 234XXXXXXXXXX, 0XXXXXXXXXX
    """
    # Remove any spaces or dashes
    phone = re.sub(r'[\s\-]', '', str(value))
    
    # Pattern for Nigerian phone numbers
    patterns = [
        r'^\+234[789][01]\d{8}$',  # +234XXXXXXXXXX
        r'^234[789][01]\d{8}$',    # 234XXXXXXXXXX
        r'^0[789][01]\d{8}$',      # 0XXXXXXXXXX
    ]
    
    if not any(re.match(pattern, phone) for pattern in patterns):
        raise ValidationError(
            _('Enter a valid Nigerian phone number. Format: +234XXXXXXXXXX, 234XXXXXXXXXX, or 0XXXXXXXXXX'),
            code='invalid_phone'
        )


def validate_nin(value):
    """
    Validate Nigerian National Identification Number (NIN).
    NIN is 11 digits.
    """
    nin = str(value).strip()
    
    if not re.match(r'^\d{11}$', nin):
        raise ValidationError(
            _('NIN must be exactly 11 digits.'),
            code='invalid_nin'
        )


def validate_bvn(value):
    """
    Validate Bank Verification Number (BVN).
    BVN is 11 digits.
    """
    bvn = str(value).strip()
    
    if not re.match(r'^\d{11}$', bvn):
        raise ValidationError(
            _('BVN must be exactly 11 digits.'),
            code='invalid_bvn'
        )


def validate_license_number(value):
    """
    Validate Nigerian driver's license number.
    Format: AAA-DDDDDDDD-AA (3 letters, 8 digits, 2 letters)
    """
    license_num = str(value).strip().upper()
    
    if not re.match(r'^[A-Z]{3}-\d{8}-[A-Z]{2}$', license_num):
        raise ValidationError(
            _('Enter a valid Nigerian driver\'s license number. Format: AAA-DDDDDDDD-AA'),
            code='invalid_license'
        )


def validate_vehicle_plate_number(value):
    """
    Validate Nigerian vehicle plate number.
    Various formats: ABC-123-DE, AB-123-CDE, etc.
    """
    plate = str(value).strip().upper()
    
    patterns = [
        r'^[A-Z]{3}-\d{3}-[A-Z]{2}$',  # ABC-123-DE
        r'^[A-Z]{2}-\d{3}-[A-Z]{3}$',  # AB-123-CDE
        r'^[A-Z]{3}\d{3}[A-Z]{2}$',    # ABC123DE
        r'^[A-Z]{2}\d{3}[A-Z]{3}$',    # AB123CDE
    ]
    
    if not any(re.match(pattern, plate) for pattern in patterns):
        raise ValidationError(
            _('Enter a valid Nigerian vehicle plate number.'),
            code='invalid_plate'
        )


def validate_positive_decimal(value):
    """
    Validate that a decimal value is positive.
    """
    if value <= 0:
        raise ValidationError(
            _('This value must be greater than zero.'),
            code='invalid_positive'
        )


def validate_rating(value):
    """
    Validate rating is between 1 and 5.
    """
    if not (1 <= value <= 5):
        raise ValidationError(
            _('Rating must be between 1 and 5.'),
            code='invalid_rating'
        )


def validate_coordinates(value):
    """
    Validate latitude/longitude coordinates.
    """
    try:
        lat, lng = map(float, str(value).split(','))
        if not (-90 <= lat <= 90):
            raise ValidationError(_('Latitude must be between -90 and 90.'))
        if not (-180 <= lng <= 180):
            raise ValidationError(_('Longitude must be between -180 and 180.'))
    except (ValueError, TypeError):
        raise ValidationError(
            _('Enter valid coordinates in format: latitude,longitude'),
            code='invalid_coordinates'
        )
