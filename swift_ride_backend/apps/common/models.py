"""
Common models for Swift Ride project.
"""

import uuid
from django.db import models


class TimeStampedModel(models.Model):
    """
    An abstract base model that provides self-updating
    created and modified fields.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    An abstract base model that uses UUID as primary key.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class BaseModel(UUIDModel, TimeStampedModel):
    """
    An abstract base model that combines UUID and TimeStamped models.
    """
    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    An abstract base model that implements soft delete functionality.
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True
