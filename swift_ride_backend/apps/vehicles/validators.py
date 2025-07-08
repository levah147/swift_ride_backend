"""
Validators for vehicles app.
"""

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import re


def validate_vehicle_year(value):
    """
    Validate vehicle year.
    """
    current_year = timezone.now().year
    if value < 1990:
        raise ValidationError(_('Vehicle year cannot be before 1990.'))
    if value > current_year + 1:
        raise ValidationError(_('Vehicle year cannot be more than one year in the future.'))


def validate_license_plate(value):
    """
    Validate license plate format.
    """
    if not value:
        raise ValidationError(_('License plate is required.'))
    
    # Remove spaces and hyphens for validation
    clean_value = value.replace(' ', '').replace('-', '')
    
    if len(clean_value) < 3:
        raise ValidationError(_('License plate must have at least 3 characters.'))
    
    if len(clean_value) > 15:
        raise ValidationError(_('License plate cannot exceed 15 characters.'))
    
    # Check for valid characters
    if not re.match(r'^[A-Z0-9\-\s]+$', value.upper()):
        raise ValidationError(_('License plate contains invalid characters. Only letters, numbers, hyphens, and spaces are allowed.'))


def validate_vin_number(value):
    """
    Validate VIN number format.
    """
    if not value:
        raise ValidationError(_('VIN number is required.'))
    
    if len(value) != 17:
        raise ValidationError(_('VIN must be exactly 17 characters long.'))
    
    # Check for valid VIN characters (no I, O, Q)
    if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', value.upper()):
        raise ValidationError(_('VIN contains invalid characters. VIN cannot contain I, O, or Q.'))


def validate_engine_capacity(value):
    """
    Validate engine capacity.
    """
    if value is not None:
        if value <= 0:
            raise ValidationError(_('Engine capacity must be greater than 0.'))
        if value > 10.0:  # 10 liters is quite large for most vehicles
            raise ValidationError(_('Engine capacity seems too large. Please verify.'))


def validate_mileage(value):
    """
    Validate vehicle mileage.
    """
    if value is not None:
        if value < 0:
            raise ValidationError(_('Mileage cannot be negative.'))
        if value > 1000000:  # 1 million km is extremely high
            raise ValidationError(_('Mileage seems too high. Please verify.'))


def validate_document_number(value):
    """
    Validate document number format.
    """
    if not value:
        raise ValidationError(_('Document number is required.'))
    
    if len(value) < 3:
        raise ValidationError(_('Document number must be at least 3 characters long.'))
    
    if len(value) > 100:
        raise ValidationError(_('Document number cannot exceed 100 characters.'))


def validate_policy_number(value):
    """
    Validate insurance policy number.
    """
    if not value:
        raise ValidationError(_('Policy number is required.'))
    
    if len(value) < 5:
        raise ValidationError(_('Policy number must be at least 5 characters long.'))
    
    if len(value) > 100:
        raise ValidationError(_('Policy number cannot exceed 100 characters.'))


def validate_document_dates(issue_date, expiry_date):
    """
    Validate document issue and expiry dates.
    """
    if expiry_date <= issue_date:
        raise ValidationError(_('Expiry date must be after issue date.'))
    
    if expiry_date <= timezone.now().date():
        raise ValidationError(_('Document has already expired.'))
    
    # Check if issue date is too far in the past (10 years)
    from datetime import timedelta
    ten_years_ago = timezone.now().date() - timedelta(days=3650)
    if issue_date < ten_years_ago:
        raise ValidationError(_('Issue date seems too old. Please verify.'))


def validate_insurance_dates(start_date, end_date):
    """
    Validate insurance start and end dates.
    """
    if end_date <= start_date:
        raise ValidationError(_('End date must be after start date.'))
    
    # Insurance can be for future dates
    from datetime import timedelta
    one_year_from_now = timezone.now().date() + timedelta(days=365)
    if start_date > one_year_from_now:
        raise ValidationError(_('Start date cannot be more than one year in the future.'))


def validate_inspection_score(value):
    """
    Validate inspection score.
    """
    if value is not None:
        if value < 0 or value > 100:
            raise ValidationError(_('Inspection score must be between 0 and 100.'))


def validate_premium_amount(value):
    """
    Validate insurance premium amount.
    """
    if value is not None:
        if value <= 0:
            raise ValidationError(_('Premium amount must be greater than 0.'))
        if value > 1000000:  # 1 million seems too high for premium
            raise ValidationError(_('Premium amount seems too high. Please verify.'))


def validate_coverage_amount(value):
    """
    Validate insurance coverage amount.
    """
    if value is not None:
        if value <= 0:
            raise ValidationError(_('Coverage amount must be greater than 0.'))
        if value > 100000000:  # 100 million coverage limit
            raise ValidationError(_('Coverage amount exceeds maximum limit.'))


def validate_maintenance_cost(value):
    """
    Validate maintenance cost.
    """
    if value is not None:
        if value < 0:
            raise ValidationError(_('Maintenance cost cannot be negative.'))
        if value > 1000000:  # 1 million seems too high for maintenance
            raise ValidationError(_('Maintenance cost seems too high. Please verify.'))


def validate_file_size(file):
    """
    Validate uploaded file size.
    """
    max_size = 5 * 1024 * 1024  # 5MB
    if file.size > max_size:
        raise ValidationError(_('File size cannot exceed 5MB.'))


def validate_image_file(file):
    """
    Validate uploaded image file.
    """
    validate_file_size(file)
    
    # Check file extension
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif']
    file_extension = file.name.lower().split('.')[-1]
    if f'.{file_extension}' not in allowed_extensions:
        raise ValidationError(_('Only JPG, JPEG, PNG, and GIF files are allowed.'))


def validate_document_file(file):
    """
    Validate uploaded document file.
    """
    validate_file_size(file)
    
    # Check file extension
    allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png']
    file_extension = file.name.lower().split('.')[-1]
    if f'.{file_extension}' not in allowed_extensions:
        raise ValidationError(_('Only PDF, JPG, JPEG, and PNG files are allowed.'))
