from django.urls import path
from apps.analytics import views

app_name = 'analytics'

urlpatterns = [
    # Analytics Events
    path('events/', views.AnalyticsEventListCreateView.as_view(), name='events-list'),
    path('events/track/', views.track_event, name='track-event'),
    
    # Daily Analytics
    path('daily/', views.DailyAnalyticsListView.as_view(), name='daily-analytics'),
    path('daily/generate/', views.generate_daily_analytics, name='generate-daily-analytics'),
    
    # Dashboard
    path('dashboard/', views.dashboard_data, name='dashboard-data'),
    path('dashboard/real-time/', views.real_time_dashboard, name='real-time-dashboard'),
    path('dashboard/executive-summary/', views.executive_summary, name='executive-summary'),
    
    # User Analytics
    path('users/<uuid:user_id>/', views.UserAnalyticsDetailView.as_view(), name='user-analytics'),
    path('users/<uuid:user_id>/metrics/', views.user_metrics, name='user-metrics'),
    
    # Geographic Analytics
    path('geographic/', views.GeographicAnalyticsListView.as_view(), name='geographic-analytics'),
    
    # Driver Performance
    path('drivers/performance/', views.DriverPerformanceAnalyticsListView.as_view(), name='driver-performance'),
    path('drivers/performance/report/', views.driver_performance_report, name='driver-performance-report'),
    
    # Reports
    path('reports/', views.AnalyticsReportListView.as_view(), name='reports-list'),
    path('reports/<uuid:pk>/', views.AnalyticsReportDetailView.as_view(), name='report-detail'),
    path('reports/generate/', views.generate_report, name='generate-report'),
    path('reports/financial/', views.financial_report, name='financial-report'),
    path('reports/engagement/', views.user_engagement_report, name='engagement-report'),
    
    # Metrics
    path('metrics/market-penetration/', views.market_penetration, name='market-penetration'),
    
    # Settings
    path('settings/', views.AnalyticsSettingsView.as_view(), name='analytics-settings'),
]
