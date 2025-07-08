from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'models', views.AIModelViewSet)
router.register(r'recommendations', views.RecommendationViewSet, basename='recommendation')
router.register(r'predictions', views.PredictionViewSet)
router.register(r'fraud-alerts', views.FraudAlertViewSet)
router.register(r'conversations', views.ConversationSessionViewSet, basename='conversation')
router.register(r'insights', views.BusinessInsightViewSet)

app_name = 'ai_features'

urlpatterns = [
    path('api/v1/ai/', include(router.urls)),
]
