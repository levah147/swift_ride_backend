"""
Common mixins for Swift Ride project.
"""

from django.db import models
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.core.cache import cache
from django.utils import timezone
from .models import TimeStampedModel, SoftDeleteModel

User = get_user_model()


class TimestampMixin(models.Model):
    """
    Mixin to add timestamp fields to models.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class SoftDeleteMixin(models.Model):
    """
    Mixin to add soft delete functionality to models.
    """
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True
    
    def soft_delete(self):
        """Soft delete the instance."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        """Restore a soft-deleted instance."""
        self.is_deleted = False
        self.deleted_at = None
        self.save()


class UserOwnedMixin(models.Model):
    """
    Mixin for models that are owned by a user.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='%(class)s_set'
    )
    
    class Meta:
        abstract = True


class LocationMixin(models.Model):
    """
    Mixin to add location fields to models.
    """
    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=8,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=11,
        decimal_places=8,
        null=True,
        blank=True
    )
    address = models.TextField(blank=True)
    
    class Meta:
        abstract = True
    
    @property
    def coordinates(self):
        """Return coordinates as tuple."""
        if self.latitude and self.longitude:
            return (float(self.latitude), float(self.longitude))
        return None


class StatusMixin(models.Model):
    """
    Mixin to add status field to models.
    """
    status = models.CharField(max_length=50, default='active')
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True


class CacheableMixin:
    """
    Mixin to add caching functionality to models.
    """
    cache_timeout = 300  # 5 minutes default
    
    def get_cache_key(self, suffix=''):
        """Generate cache key for the instance."""
        return f"{self.__class__.__name__.lower()}:{self.pk}:{suffix}"
    
    def cache_set(self, key, value, timeout=None):
        """Set cache value."""
        timeout = timeout or self.cache_timeout
        cache.set(key, value, timeout)
    
    def cache_get(self, key):
        """Get cache value."""
        return cache.get(key)
    
    def cache_delete(self, key):
        """Delete cache value."""
        cache.delete(key)
    
    def invalidate_cache(self):
        """Invalidate all cache for this instance."""
        base_key = self.get_cache_key()
        # This is a simplified version - in production, you'd want to track all cache keys
        cache.delete(base_key)


class APIResponseMixin:
    """
    Mixin to standardize API responses.
    """
    
    def success_response(self, data=None, message="Success", status_code=status.HTTP_200_OK):
        """Return standardized success response."""
        response_data = {
            'success': True,
            'message': message,
            'data': data
        }
        return Response(response_data, status=status_code)
    
    def error_response(self, message="Error occurred", errors=None, status_code=status.HTTP_400_BAD_REQUEST):
        """Return standardized error response."""
        response_data = {
            'success': False,
            'message': message,
            'errors': errors
        }
        return Response(response_data, status=status_code)
    
    def paginated_response(self, queryset, serializer_class, request):
        """Return paginated response."""
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = serializer_class(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        
        serializer = serializer_class(queryset, many=True, context={'request': request})
        return self.success_response(serializer.data)


class BulkActionMixin:
    """
    Mixin to add bulk actions to ViewSets.
    """
    
    @action(detail=False, methods=['post'])
    def bulk_delete(self, request):
        """Bulk delete items."""
        ids = request.data.get('ids', [])
        if not ids:
            return self.error_response("No IDs provided")
        
        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.count()
        queryset.delete()
        
        return self.success_response(
            data={'deleted_count': count},
            message=f"Successfully deleted {count} items"
        )
    
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update items."""
        ids = request.data.get('ids', [])
        update_data = request.data.get('data', {})
        
        if not ids or not update_data:
            return self.error_response("IDs and update data required")
        
        queryset = self.get_queryset().filter(id__in=ids)
        count = queryset.update(**update_data)
        
        return self.success_response(
            data={'updated_count': count},
            message=f"Successfully updated {count} items"
        )


class ExportMixin:
    """
    Mixin to add export functionality to ViewSets.
    """
    
    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        """Export data as CSV."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.get_export_filename()}.csv"'
        
        writer = csv.writer(response)
        
        # Write headers
        headers = self.get_export_headers()
        writer.writerow(headers)
        
        # Write data
        queryset = self.get_queryset()
        for obj in queryset:
            row = self.get_export_row(obj)
            writer.writerow(row)
        
        return response
    
    def get_export_filename(self):
        """Get filename for export."""
        return f"{self.get_queryset().model.__name__.lower()}_export"
    
    def get_export_headers(self):
        """Get headers for export."""
        return ['ID', 'Created At', 'Updated At']
    
    def get_export_row(self, obj):
        """Get row data for export."""
        return [obj.id, obj.created_at, obj.updated_at]


class SearchMixin:
    """
    Mixin to add search functionality to ViewSets.
    """
    search_fields = []
    
    def get_search_queryset(self, queryset, search_term):
        """Filter queryset based on search term."""
        if not search_term or not self.search_fields:
            return queryset
        
        from django.db.models import Q
        
        search_query = Q()
        for field in self.search_fields:
            search_query |= Q(**{f"{field}__icontains": search_term})
        
        return queryset.filter(search_query)
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search endpoint."""
        search_term = request.query_params.get('q', '')
        queryset = self.get_search_queryset(self.get_queryset(), search_term)
        
        return self.paginated_response(
            queryset,
            self.get_serializer_class(),
            request
        )
