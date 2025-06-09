"""
Authentication URLs for Swift Ride project.
"""

from django.urls import path

from .views import (
    LoginWithOTPView,
    VerifyOTPView,
    CustomTokenRefreshView,
    LogoutView
)

urlpatterns = [
    path('login/', LoginWithOTPView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
