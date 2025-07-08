"""
Utility functions for the users app.
"""

import re
import random
import string
from typing import Optional, Dict, Any
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from geopy.distance import geodesic 

User = get_user_model()


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate Nigerian phone number format.
    """
    # Nigerian phone number patterns
    patterns = [
        r'^(\+234|234|0)(70|71|80|81|90|91|70|71)\d{8}$',  # MTN, Airtel, Glo, 9mobile
        r'^(\+234|234|0)(80|81|70|71|90|91)\d{8}$',
    ]
    
    for pattern in patterns:
        if re.match(pattern, phone_number):
            return True
    return False


def normalize_phone_number(phone_number: str) -> str:
    """
    Normalize phone number to international format.
    """
    # Remove all non-digit characters
    phone_number = re.sub(r'\D', '', phone_number)
    
    # Handle different formats
    if phone_number.startswith('234'):
        return f'+{phone_number}'
    elif phone_number.startswith('0'):
        return f'+234{phone_number[1:]}'
    elif len(phone_number) == 10:
        return f'+234{phone_number}'
    elif phone_number.startswith('+234'):
        return phone_number
    else:
        raise ValidationError('Invalid phone number format')


def generate_referral_code(length: int = 8) -> str:
    """
    Generate a unique referral code.
    """
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choice(characters) for _ in range(length))
        if not User.objects.filter(referral_code=code).exists():
            return code


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two coordinates in kilometers.
    """
    try:
        point1 = (lat1, lon1)
        point2 = (lat2, lon2)
        return geodesic(point1, point2).kilometers
    except Exception:
        return float('inf')


def format_user_display_name(user) -> str:
    """
    Format user display name for UI.
    """
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    elif user.first_name:
        return user.first_name
    elif user.email:
        return user.email.split('@')[0]
    else:
        return f"User {user.id}"


def get_user_avatar_url(user, size: str = 'medium') -> Optional[str]:
    """
    Get user avatar URL with different sizes.
    """
    if hasattr(user, 'profile_picture') and user.profile_picture:
        return user.profile_picture.url
    
    # Return default avatar based on user type
    if user.user_type == 'driver':
        return f'/static/images/default-driver-avatar-{size}.png'
    else:
        return f'/static/images/default-rider-avatar-{size}.png'


def mask_phone_number(phone_number: str) -> str:
    """
    Mask phone number for privacy (show only last 4 digits).
    """
    if len(phone_number) <= 4:
        return phone_number
    
    return f"****{phone_number[-4:]}"


def mask_email(email: str) -> str:
    """
    Mask email for privacy.
    """
    if '@' not in email:
        return email
    
    username, domain = email.split('@', 1)
    if len(username) <= 2:
        masked_username = username
    else:
        masked_username = f"{username[0]}***{username[-1]}"
    
    return f"{masked_username}@{domain}"


def get_user_rating_display(rating: float) -> Dict[str, Any]:
    """
    Get user rating display information.
    """
    if rating is None or rating == 0:
        return {
            'rating': 0.0,
            'stars': 0,
            'display': 'No rating',
            'color': 'gray'
        }
    
    stars = round(rating)
    
    if rating >= 4.5:
        color = 'green'
        display = 'Excellent'
    elif rating >= 4.0:
        color = 'blue'
        display = 'Very Good'
    elif rating >= 3.5:
        color = 'yellow'
        display = 'Good'
    elif rating >= 3.0:
        color = 'orange'
        display = 'Fair'
    else:
        color = 'red'
        display = 'Poor'
    
    return {
        'rating': round(rating, 1),
        'stars': stars,
        'display': display,
        'color': color
    }


def is_user_online(user) -> bool:
    """
    Check if user is currently online.
    """
    if user.user_type == 'driver':
        try:
            return user.driver_profile.is_online
        except:
            return False
    
    # For riders, check last activity (within last 5 minutes)
    from django.utils import timezone
    from datetime import timedelta
    
    if user.last_login:
        return timezone.now() - user.last_login < timedelta(minutes=5)
    
    return False


def get_user_completion_percentage(user) -> int:
    """
    Calculate user profile completion percentage.
    """
    total_fields = 0
    completed_fields = 0
    
    # Basic user fields
    basic_fields = ['first_name', 'last_name', 'email', 'phone_number']
    for field in basic_fields:
        total_fields += 1
        if getattr(user, field, None):
            completed_fields += 1
    
    # Profile picture
    total_fields += 1
    if getattr(user, 'profile_picture', None):
        completed_fields += 1
    
    # User type specific fields
    if user.user_type == 'driver':
        try:
            driver_profile = user.driver_profile
            driver_fields = ['license_number', 'license_expiry', 'vehicle']
            for field in driver_fields:
                total_fields += 1
                if getattr(driver_profile, field, None):
                    completed_fields += 1
        except:
            total_fields += 3  # Add the fields even if profile doesn't exist
    
    elif user.user_type == 'rider':
        try:
            rider_profile = user.rider_profile
            rider_fields = ['emergency_contact', 'preferred_payment_method']
            for field in rider_fields:
                total_fields += 1
                if getattr(rider_profile, field, None):
                    completed_fields += 1
        except:
            total_fields += 2  # Add the fields even if profile doesn't exist
    
    return int((completed_fields / total_fields) * 100) if total_fields > 0 else 0
