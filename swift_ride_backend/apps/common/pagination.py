"""
Common pagination classes for Swift Ride project.
"""

from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
from collections import OrderedDict


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class for Swift Ride API.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('results', data)
        ]))


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination class for large datasets.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('results', data)
        ]))


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination class for small datasets.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('results', data)
        ]))


class CustomLimitOffsetPagination(LimitOffsetPagination):
    """
    Custom limit/offset pagination for Swift Ride API.
    """
    default_limit = 20
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 100
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('success', True),
            ('count', self.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('limit', self.limit),
            ('offset', self.offset),
            ('results', data)
        ]))


class RidePagination(StandardResultsSetPagination):
    """
    Pagination specifically for ride-related endpoints.
    """
    page_size = 15
    max_page_size = 50


class MessagePagination(StandardResultsSetPagination):
    """
    Pagination for chat messages.
    """
    page_size = 30
    max_page_size = 100
    
    def get_paginated_response(self, data):
        # Reverse the order for messages (newest first)
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('messages', data)
        ]))


class DriverPagination(StandardResultsSetPagination):
    """
    Pagination for driver listings.
    """
    page_size = 25
    max_page_size = 100


class NotificationPagination(StandardResultsSetPagination):
    """
    Pagination for notifications.
    """
    page_size = 20
    max_page_size = 50
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('success', True),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('total_pages', self.page.paginator.num_pages),
            ('current_page', self.page.number),
            ('page_size', self.get_page_size(self.request)),
            ('unread_count', self.get_unread_count()),
            ('notifications', data)
        ]))
    
    def get_unread_count(self):
        """Get count of unread notifications for the user."""
        if hasattr(self.request, 'user') and self.request.user.is_authenticated:
            from apps.notifications.models import Notification
            return Notification.objects.filter(
                user=self.request.user,
                is_read=False
            ).count()
        return 0
