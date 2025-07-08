from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PromotionViewSet, PromotionUsageViewSet, ReferralProgramViewSet,
    ReferralViewSet, LoyaltyProgramViewSet, LoyaltyAccountViewSet,
    PromotionCampaignViewSet, PromotionAnalyticsViewSet
)

router = DefaultRouter()
router.register(r'promotions', PromotionViewSet)
router.register(r'promotion-usage', PromotionUsageViewSet)
router.register(r'referral-programs', ReferralProgramViewSet)
router.register(r'referrals', ReferralViewSet)
router.register(r'loyalty-programs', LoyaltyProgramViewSet)
router.register(r'loyalty-accounts', LoyaltyAccountViewSet)
router.register(r'campaigns', PromotionCampaignViewSet)
router.register(r'analytics', PromotionAnalyticsViewSet)

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
