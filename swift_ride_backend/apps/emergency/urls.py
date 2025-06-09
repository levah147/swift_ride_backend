from django.urls import path
from apps.emergency import views

app_name = 'emergency'

urlpatterns = [
    # Emergency Contacts
    path('contacts/', views.EmergencyContactListCreateView.as_view(), name='contact-list-create'),
    path('contacts/<int:pk>/', views.EmergencyContactDetailView.as_view(), name='contact-detail'),
    
    # Emergency Alerts
    path('alerts/', views.EmergencyAlertListCreateView.as_view(), name='alert-list-create'),
    path('alerts/<uuid:pk>/', views.EmergencyAlertDetailView.as_view(), name='alert-detail'),
    path('alerts/<uuid:alert_id>/acknowledge/', views.acknowledge_alert, name='acknowledge-alert'),
    path('alerts/<uuid:alert_id>/resolve/', views.resolve_alert, name='resolve-alert'),
    
    # Panic Button
    path('panic/', views.panic_button, name='panic-button'),
    
    # Safety Checks
    path('safety-checks/', views.SafetyCheckListView.as_view(), name='safety-check-list'),
    path('safety-checks/<int:check_id>/complete/', views.complete_safety_check, name='complete-safety-check'),
    
    # Location Sharing
    path('location-shares/', views.LocationShareListView.as_view(), name='location-share-list'),
    path('location-shares/<int:share_id>/update/', views.update_location_share, name='update-location-share'),
    
    # Emergency Services
    path('nearby-services/', views.nearby_emergency_services, name='nearby-services'),
    
    # Statistics
    path('stats/', views.emergency_stats, name='emergency-stats'),
    
    # Settings
    path('settings/', views.EmergencySettingsView.as_view(), name='emergency-settings'),
]
