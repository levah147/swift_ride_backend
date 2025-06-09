"""
Common utilities for Swift Ride project.
"""

import os
import uuid
from datetime import datetime


def get_file_path(instance, filename):
    """
    Generate a unique file path for uploaded files.
    """
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"{instance.__class__.__name__.lower()}", filename)


def generate_otp():
    """
    Generate a 6-digit OTP.
    """
    import random
    return str(random.randint(100000, 999999))


def soft_delete(instance):
    """
    Soft delete an instance by setting is_deleted to True and deleted_at to current time.
    """
    instance.is_deleted = True
    instance.deleted_at = datetime.now()
    instance.save()
