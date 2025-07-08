"""
Utility functions for vehicles app.
"""

import os
import uuid
from django.utils import timezone
from django.core.files.storage import default_storage
from PIL import Image
import io


def get_vehicle_photo_path(instance, filename):
    """
    Generate file path for vehicle photos.
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('vehicles', str(instance.id), 'photos', filename)


def get_document_path(instance, filename):
    """
    Generate file path for vehicle documents.
    """
    ext = filename.split('.')[-1]
    filename = f"{instance.document_type}_{uuid.uuid4()}.{ext}"
    return os.path.join('vehicles', str(instance.vehicle.id), 'documents', filename)


def get_insurance_path(instance, filename):
    """
    Generate file path for insurance certificates.
    """
    ext = filename.split('.')[-1]
    filename = f"insurance_{uuid.uuid4()}.{ext}"
    return os.path.join('vehicles', str(instance.vehicle.id), 'insurance', filename)


def compress_image(image_file, max_size=(800, 600), quality=85):
    """
    Compress and resize image file.
    """
    try:
        image = Image.open(image_file)
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Resize image
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save compressed image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        output.seek(0)
        
        return output
    except Exception as e:
        print(f"Error compressing image: {e}")
        return image_file


def validate_vehicle_year(year):
    """
    Validate vehicle year.
    """
    current_year = timezone.now().year
    if year < 1990 or year > current_year + 1:
        return False, f"Year must be between 1990 and {current_year + 1}"
    return True, "Valid year"


def validate_license_plate(license_plate):
    """
    Validate license plate format.
    """
    # Remove spaces and hyphens for validation
    clean_plate = license_plate.replace(' ', '').replace('-', '')
    
    if len(clean_plate) < 3:
        return False, "License plate must have at least 3 characters"
    
    if len(clean_plate) > 15:
        return False, "License plate cannot exceed 15 characters"
    
    # Check for valid characters (letters, numbers, spaces, hyphens)
    import re
    if not re.match(r'^[A-Z0-9\-\s]+$', license_plate.upper()):
        return False, "License plate contains invalid characters"
    
    return True, "Valid license plate"


def validate_vin_number(vin):
    """
    Validate VIN number format.
    """
    if len(vin) != 17:
        return False, "VIN must be exactly 17 characters"
    
    # Check for valid VIN characters (no I, O, Q)
    import re
    if not re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin.upper()):
        return False, "VIN contains invalid characters"
    
    return True, "Valid VIN"


def calculate_vehicle_age(year):
    """
    Calculate vehicle age in years.
    """
    current_year = timezone.now().year
    return current_year - year


def get_vehicle_depreciation_rate(vehicle):
    """
    Calculate vehicle depreciation rate based on age and type.
    """
    age = calculate_vehicle_age(vehicle.year)
    
    # Base depreciation rates by vehicle type
    base_rates = {
        'sedan': 0.15,
        'suv': 0.12,
        'hatchback': 0.18,
        'truck': 0.10,
        'motorcycle': 0.20,
    }
    
    vehicle_type_name = vehicle.vehicle_type.name.lower()
    base_rate = base_rates.get(vehicle_type_name, 0.15)
    
    # Adjust for age
    if age <= 2:
        return base_rate
    elif age <= 5:
        return base_rate * 1.2
    elif age <= 10:
        return base_rate * 1.5
    else:
        return base_rate * 2.0


def format_license_plate(license_plate):
    """
    Format license plate for display.
    """
    return license_plate.upper().strip()


def generate_vehicle_qr_code(vehicle):
    """
    Generate QR code for vehicle verification.
    """
    try:
        import qrcode
        from django.conf import settings
        
        # Create QR code data
        qr_data = {
            'vehicle_id': str(vehicle.id),
            'license_plate': vehicle.license_plate,
            'owner': vehicle.owner.phone_number,
            'verification_url': f"{settings.FRONTEND_URL}/verify-vehicle/{vehicle.id}"
        }
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save to BytesIO
        qr_buffer = io.BytesIO()
        qr_image.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        return qr_buffer
    except ImportError:
        print("qrcode library not installed")
        return None
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None


def check_document_expiry_status(document):
    """
    Check document expiry status and return appropriate message.
    """
    days_until_expiry = document.days_until_expiry
    
    if days_until_expiry < 0:
        return 'expired', f"Document expired {abs(days_until_expiry)} days ago"
    elif days_until_expiry == 0:
        return 'expires_today', "Document expires today"
    elif days_until_expiry <= 7:
        return 'expires_soon', f"Document expires in {days_until_expiry} days"
    elif days_until_expiry <= 30:
        return 'expires_this_month', f"Document expires in {days_until_expiry} days"
    else:
        return 'valid', f"Document valid for {days_until_expiry} days"


def get_vehicle_status_color(vehicle):
    """
    Get color code for vehicle status display.
    """
    status_colors = {
        'pending': '#FFA500',  # Orange
        'approved': '#008000',  # Green
        'rejected': '#FF0000',  # Red
        'suspended': '#800080',  # Purple
    }
    
    return status_colors.get(vehicle.verification_status, '#808080')  # Gray default


def clean_vehicle_data_for_export(vehicle):
    """
    Clean vehicle data for export/API response.
    """
    return {
        'id': str(vehicle.id),
        'license_plate': vehicle.license_plate,
        'make': vehicle.make,
        'model': vehicle.model,
        'year': vehicle.year,
        'color': vehicle.color,
        'fuel_type': vehicle.fuel_type,
        'verification_status': vehicle.verification_status,
        'is_active': vehicle.is_active,
        'owner_phone': vehicle.owner.phone_number,
        'created_at': vehicle.created_at.isoformat(),
    }
