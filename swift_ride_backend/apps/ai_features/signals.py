from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import AIModel, Recommendation, PredictionResult, FraudAlert

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_recommendations(sender, instance, created, **kwargs):
    """Create initial recommendations for new users"""
    if created:
        try:
            from .services.recommendation_service import RecommendationService
            recommendation_service = RecommendationService()
            # Create welcome recommendations
            recommendation_service.generate_recommendations(
                user=instance,
                recommendation_type='onboarding',
                limit=5
            )
        except Exception as e:
            # Log error but don't fail user creation
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to create recommendations for user {instance.id}: {str(e)}")


@receiver(post_save, sender=AIModel)
def update_model_status(sender, instance, created, **kwargs):
    """Update model status and trigger retraining if needed"""
    if not created and instance.status == 'training':
        # Schedule model training task
        try:
            from .tasks import train_ai_model
            train_ai_model.delay(instance.id)
        except ImportError:
            # Tasks not available yet
            pass


@receiver(pre_delete, sender=AIModel)
def cleanup_model_artifacts(sender, instance, **kwargs):
    """Clean up model files and artifacts before deletion"""
    try:
        # Clean up model files
        if instance.model_path:
            import os
            if os.path.exists(instance.model_path):
                os.remove(instance.model_path)
        
        # Clean up related predictions and recommendations
        PredictionResult.objects.filter(model=instance).delete()
        Recommendation.objects.filter(model=instance).delete()
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to cleanup model artifacts for {instance.id}: {str(e)}")


@receiver(post_save, sender=FraudAlert)
def handle_fraud_alert(sender, instance, created, **kwargs):
    """Handle new fraud alerts"""
    if created and instance.severity == 'high':
        # Send immediate notification for high severity alerts
        try:
            from apps.notifications.services.notification_service import NotificationService
            notification_service = NotificationService()
            
            # Notify admin users
            admin_users = User.objects.filter(is_staff=True, is_active=True)
            for admin in admin_users:
                notification_service.send_notification(
                    user=admin,
                    title="High Severity Fraud Alert",
                    message=f"Fraud detected: {instance.alert_type} - {instance.description}",
                    notification_type='security',
                    priority='high'
                )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send fraud alert notification: {str(e)}")
