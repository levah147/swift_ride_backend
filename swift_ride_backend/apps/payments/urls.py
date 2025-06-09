"""
URL configuration for payments app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.payments.views import (
    PaymentViewSet, PaymentMethodViewSet, WalletViewSet,
    RefundViewSet, PaymentWebhookViewSet
)

router = DefaultRouter()
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'payment-methods', PaymentMethodViewSet, basename='payment-method')
router.register(r'wallet', WalletViewSet, basename='wallet')
router.register(r'refunds', RefundViewSet, basename='refund')
router.register(r'webhooks', PaymentWebhookViewSet, basename='payment-webhook')

urlpatterns = [
    path('', include(router.urls)),
]
