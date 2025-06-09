from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.reviews.views import (
    ReviewViewSet, ReviewCategoryViewSet, ReviewTemplateViewSet,
    ReviewIncentiveViewSet, ReviewReportViewSet
)

router = DefaultRouter()
router.register(r'reviews', ReviewViewSet, basename='review')
router.register(r'categories', ReviewCategoryViewSet, basename='reviewcategory')
router.register(r'templates', ReviewTemplateViewSet, basename='reviewtemplate')
router.register(r'incentives', ReviewIncentiveViewSet, basename='reviewincentive')
router.register(r'reports', ReviewReportViewSet, basename='reviewreport')

app_name = 'reviews'

urlpatterns = [
    path('api/v1/', include(router.urls)),
]
