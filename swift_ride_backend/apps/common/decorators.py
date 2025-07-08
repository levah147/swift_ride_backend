"""
Common decorators for Swift Ride project.
"""

import functools
import time
from django.core.cache import cache
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework.response import Response
from rest_framework import status
from .exceptions import RateLimitExceededException, VerificationRequiredException


def rate_limit(max_requests=60, window=60):
    """
    Rate limiting decorator.
    
    Args:
        max_requests: Maximum number of requests allowed
        window: Time window in seconds
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # Get user identifier
            if request.user.is_authenticated:
                identifier = f"user:{request.user.id}"
            else:
                identifier = f"ip:{request.META.get('REMOTE_ADDR')}"
            
            cache_key = f"rate_limit:{identifier}:{func.__name__}"
            
            # Get current request count
            current_requests = cache.get(cache_key, 0)
            
            if current_requests >= max_requests:
                return JsonResponse({
                    'success': False,
                    'error': {
                        'code': 'rate_limit_exceeded',
                        'message': f'Rate limit exceeded. Max {max_requests} requests per {window} seconds.'
                    }
                }, status=429)
            
            # Increment counter
            cache.set(cache_key, current_requests + 1, window)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_verification(verification_type='basic'):
    """
    Decorator to require user verification.
    
    Args:
        verification_type: Type of verification required ('basic', 'driver', 'phone', 'email')
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'authentication_required',
                        'message': 'Authentication required'
                    }
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            user = request.user
            
            # Check verification based on type
            if verification_type == 'phone' and not user.phone_verified:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'phone_verification_required',
                        'message': 'Phone verification required'
                    }
                }, status=status.HTTP_403_FORBIDDEN)
            
            elif verification_type == 'email' and not user.email_verified:
                return Response({
                    'success': False,
                    'error': {
                        'code': 'email_verification_required',
                        'message': 'Email verification required'
                    }
                }, status=status.HTTP_403_FORBIDDEN)
            
            elif verification_type == 'driver':
                if not hasattr(user, 'driver_profile'):
                    return Response({
                        'success': False,
                        'error': {
                            'code': 'driver_profile_required',
                            'message': 'Driver profile required'
                        }
                    }, status=status.HTTP_403_FORBIDDEN)
                
                if not user.driver_profile.is_verified:
                    return Response({
                        'success': False,
                        'error': {
                            'code': 'driver_verification_required',
                            'message': 'Driver verification required'
                        }
                    }, status=status.HTTP_403_FORBIDDEN)
            
            return func(request, *args, **kwargs)
        return wrapper
    return decorator


def cache_response(timeout=300, key_prefix=''):
    """
    Cache response decorator.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response:
                return cached_response
            
            # Execute function and cache result
            response = func(request, *args, **kwargs)
            cache.set(cache_key, response, timeout)
            
            return response
        return wrapper
    return decorator


def log_execution_time(func):
    """
    Decorator to log function execution time.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        
        execution_time = end_time - start_time
        print(f"{func.__name__} executed in {execution_time:.4f} seconds")
        
        return result
    return wrapper


def require_driver_online(func):
    """
    Decorator to ensure driver is online.
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response({
                'success': False,
                'error': {
                    'code': 'authentication_required',
                    'message': 'Authentication required'
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        if not hasattr(request.user, 'driver_profile'):
            return Response({
                'success': False,
                'error': {
                    'code': 'driver_profile_required',
                    'message': 'Driver profile required'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        if not request.user.driver_profile.is_online:
            return Response({
                'success': False,
                'error': {
                    'code': 'driver_offline',
                    'message': 'Driver must be online to perform this action'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        return func(request, *args, **kwargs)
    return wrapper


def validate_json_request(func):
    """
    Decorator to validate JSON request data.
    """
    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        if request.content_type != 'application/json':
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'invalid_content_type',
                    'message': 'Content-Type must be application/json'
                }
            }, status=400)
        
        try:
            import json
            json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': {
                    'code': 'invalid_json',
                    'message': 'Invalid JSON data'
                }
            }, status=400)
        
        return func(request, *args, **kwargs)
    return wrapper
