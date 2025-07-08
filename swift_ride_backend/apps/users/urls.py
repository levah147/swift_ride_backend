"""
URL configuration for the users app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views

app_name = 'users'

urlpatterns = [
    # User profile management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/rider/', views.RiderProfileView.as_view(), name='rider-profile'),
    path('profile/driver/', views.DriverProfileView.as_view(), name='driver-profile'),
    path('preferences/', views.UserPreferencesView.as_view(), name='user-preferences'),
    
    # User management (admin)
    path('list/', views.UserListView.as_view(), name='user-list'),
    path('<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    
    # Driver specific endpoints
    path('driver/toggle-status/', views.DriverStatusToggleView.as_view(), name='driver-toggle-status'),
    path('nearby-drivers/', views.NearbyDriversView.as_view(), name='nearby-drivers'),
    
    # User actions
    path('update-location/', views.update_location, name='update-location'),
    path('stats/', views.UserStatsView.as_view(), name='user-stats'),
    path('deactivate/', views.deactivate_account, name='deactivate-account'),
]
