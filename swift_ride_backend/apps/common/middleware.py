"""
Common middleware for Swift Ride project.
"""

import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)
User = get_user_model()


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all API requests and responses.
    """
    
    def process_request(self, request):
        request.start_time = time.time()
        
        # Log request details
        logger.info(f"Request: {request.method} {request.path}")
        if request.user.is_authenticated:
            logger.info(f"User: {request.user.id} - {request.user.phone_number}")
    
    def process_response(self, request, response):
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            logger.info(f"Response: {response.status_code} - Duration: {duration:.2f}s")
        
        return response


class RateLimitMiddleware(MiddlewareMixin):
    """
    Simple rate limiting middleware.
    """
    
    def process_request(self, request):
        if not settings.DEBUG:  # Only apply in production
            # Get client IP
            ip = self.get_client_ip(request)
            
            # Rate limit key
            cache_key = f"rate_limit:{ip}"
            
            # Get current request count
            request_count = cache.get(cache_key, 0)
            
            # Check if limit exceeded (100 requests per minute)
            if request_count >= 100:
                return JsonResponse({
                    'success': False,
                    'error': {
                        'code': 'rate_limit_exceeded',
                        'message': 'Too many requests. Please try again later.'
                    }
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, request_count + 1, 60)  # 60 seconds
        
        return None
    
    def get_client_ip(self, request):
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class CorsMiddleware(MiddlewareMixin):
    """
    Custom CORS middleware for Swift Ride.
    """
    
    def process_response(self, request, response):
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response['Access-Control-Max-Age'] = '86400'
        
        return response


class UserActivityMiddleware(MiddlewareMixin):
    """
    Middleware to track user activity and update last seen.
    """
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Update user's last activity
            cache_key = f"user_activity:{request.user.id}"
            cache.set(cache_key, time.time(), 300)  # 5 minutes
            
            # Update location if provided
            if hasattr(request, 'data') and 'location' in request.data:
                location_data = request.data['location']
                if 'latitude' in location_data and 'longitude' in location_data:
                    cache.set(
                        f"user_location:{request.user.id}",
                        {
                            'latitude': location_data['latitude'],
                            'longitude': location_data['longitude'],
                            'timestamp': time.time()
                        },
                        600  # 10 minutes
                    )


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Add security headers to responses.
    """
    
    def process_response(self, request, response):
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
