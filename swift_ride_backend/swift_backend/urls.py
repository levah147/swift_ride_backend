"""
URL configuration for Swift Ride project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# API Schema view
schema_view = get_schema_view(
    openapi.Info(
        title="Swift Ride API",
        default_version='v1',
        description="API documentation for Swift Ride application",
        terms_of_service="https://www.swiftride.com/terms/",
        contact=openapi.Contact(email="contact@swiftride.com"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# API URL patterns
api_v1_patterns = [
    path('auth/', include('apps.authentication.urls')),
    path('users/', include('apps.users.urls')),
    path('rides/', include('apps.rides.urls')),
    path('vehicles/', include('apps.vehicles.urls')),
    path('chat/', include('apps.chat.urls')),
    path('payments/', include('apps.payments.urls')),
    path('reviews/', include('apps.reviews.urls')),
    path('emergency/', include('apps.emergency.urls')), 
    path('notifications/', include('apps.notifications.urls')),
    path('analytics/', include('apps.analytics.urls')),
    path('locations/', include('apps.location.urls')), 
    path('promotions/', include('apps.promotions.urls')),
    path('ai-features/', include('apps.ai_features.urls')),
]
 
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API v1 endpoints
    path('api/v1/', include(api_v1_patterns)),
    
    # API documentation
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Add debug toolbar URLs in development
if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
    
    # Serve media files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
