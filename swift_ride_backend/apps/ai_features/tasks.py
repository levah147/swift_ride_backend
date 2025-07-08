from celery import shared_task
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

from .models import AIModel, Recommendation, FraudAlert, ConversationSession
from .services.recommendation_service import RecommendationService
from .services.prediction_service import PredictionService
from .services.fraud_detection_service import FraudDetectionService

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task
def train_ai_model(model_id):
    """Train an AI model"""
    try:
        model = AIModel.objects.get(id=model_id)
        model.status = 'training'
        model.save()
        
        # Simulate training process
        # In a real implementation, this would trigger actual ML training
        logger.info(f"Starting training for model {model.name}")
        
        # Update model status after training
        model.status = 'active'
        model.last_trained_at = timezone.now()
        model.save()
        
        logger.info(f"Training completed for model {model.name}")
        
    except AIModel.DoesNotExist:
        logger.error(f"AI model with id {model_id} not found")
    except Exception as e:
        logger.error(f"Error training AI model {model_id}: {str(e)}")


@shared_task
def generate_daily_recommendations():
    """Generate daily recommendations for active users"""
    try:
        # Get active users (users who have used the app in the last 30 days)
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=30),
            is_active=True
        )
        
        recommendation_service = RecommendationService()
        
        for user in active_users:
            try:
                # Generate recommendations for each user
                recommendations = recommendation_service.generate_recommendations(
                    user=user,
                    limit=3
                )
                logger.info(f"Generated {len(recommendations)} recommendations for user {user.id}")
                
            except Exception as e:
                logger.error(f"Error generating recommendations for user {user.id}: {str(e)}")
        
        logger.info(f"Daily recommendation generation completed for {active_users.count()} users")
        
    except Exception as e:
        logger.error(f"Error in daily recommendation generation: {str(e)}")


@shared_task
def cleanup_expired_recommendations():
    """Clean up expired recommendations"""
    try:
        expired_recommendations = Recommendation.objects.filter(
            expires_at__lt=timezone.now(),
            status__in=['pending', 'shown']
        )
        
        count = expired_recommendations.count()
        expired_recommendations.update(status='expired')
        
        logger.info(f"Marked {count} recommendations as expired")
        
    except Exception as e:
        logger.error(f"Error cleaning up expired recommendations: {str(e)}")


@shared_task
def run_fraud_detection_scan():
    """Run periodic fraud detection scan"""
    try:
        fraud_service = FraudDetectionService()
        
        # Scan recent transactions for fraud
        recent_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(hours=24)
        )
        
        fraud_alerts_created = 0
        
        for user in recent_users:
            try:
                # Run account fraud detection
                result = fraud_service.detect_account_fraud(user)
                if result.get('fraud_detected'):
                    fraud_alerts_created += 1
                    
            except Exception as e:
                logger.error(f"Error running fraud detection for user {user.id}: {str(e)}")
        
        logger.info(f"Fraud detection scan completed. Created {fraud_alerts_created} alerts")
        
    except Exception as e:
        logger.error(f"Error in fraud detection scan: {str(e)}")


@shared_task
def update_model_performance():
    """Update AI model performance metrics"""
    try:
        active_models = AIModel.objects.filter(status='active')
        
        for model in active_models:
            try:
                # Calculate performance metrics based on recent predictions
                recent_predictions = model.predictions.filter(
                    prediction_timestamp__gte=timezone.now() - timedelta(days=7),
                    actual_value__isnull=False
                )
                
                if recent_predictions.exists():
                    # Calculate average accuracy
                    avg_accuracy = sum(
                        pred.accuracy_score for pred in recent_predictions 
                        if pred.accuracy_score
                    ) / recent_predictions.count()
                    
                    model.accuracy = avg_accuracy
                    model.save()
                    
                    logger.info(f"Updated performance for model {model.name}: {avg_accuracy:.3f}")
                
            except Exception as e:
                logger.error(f"Error updating performance for model {model.id}: {str(e)}")
        
        logger.info(f"Model performance update completed for {active_models.count()} models")
        
    except Exception as e:
        logger.error(f"Error updating model performance: {str(e)}")


@shared_task
def cleanup_old_chat_sessions():
    """Clean up old chat sessions"""
    try:
        # Close sessions that have been inactive for more than 24 hours
        inactive_sessions = ConversationSession.objects.filter(
            status='active',
            started_at__lt=timezone.now() - timedelta(hours=24)
        )
        
        count = inactive_sessions.count()
        
        for session in inactive_sessions:
            session.end_session()
            session.status = 'abandoned'
            session.save()
        
        logger.info(f"Cleaned up {count} inactive chat sessions")
        
    except Exception as e:
        logger.error(f"Error cleaning up chat sessions: {str(e)}")


@shared_task
def generate_business_insights():
    """Generate AI-powered business insights"""
    try:
        from .models import BusinessInsight
        
        # This would typically involve running complex analytics
        # For now, we'll create a simple example insight
        
        insight = BusinessInsight.objects.create(
            model=AIModel.objects.filter(model_type='prediction').first(),
            insight_type='trend_analysis',
            priority='medium',
            title='Daily Ride Demand Analysis',
            description='Analysis of ride demand patterns over the past week',
            summary='Ride demand has increased by 15% compared to last week',
            analysis_data={
                'period': '7_days',
                'demand_increase': 0.15,
                'peak_hours': [8, 9, 17, 18, 19],
                'growth_areas': ['downtown', 'airport']
            },
            recommendations=[
                'Increase driver incentives during peak hours',
                'Focus marketing efforts in growth areas',
                'Consider dynamic pricing adjustments'
            ],
            confidence_score=0.8
        )
        
        logger.info(f"Generated business insight: {insight.title}")
        
    except Exception as e:
        logger.error(f"Error generating business insights: {str(e)}")


@shared_task
def validate_predictions():
    """Validate predictions against actual outcomes"""
    try:
        from apps.rides.models import Ride
        
        # Find predictions that can be validated
        unvalidated_predictions = model.predictions.filter(
            prediction_type='demand_forecast',
            actual_value__isnull=True,
            prediction_timestamp__lt=timezone.now() - timedelta(hours=1)
        )
        
        validated_count = 0
        
        for prediction in unvalidated_predictions:
            try:
                # Get actual demand for the predicted time and location
                input_data = prediction.input_data
                location = input_data.get('location', {})
                
                if location:
                    actual_rides = Ride.objects.filter(
                        pickup_latitude__range=[
                            location['lat'] - 0.01, 
                            location['lat'] + 0.01
                        ],
                        pickup_longitude__range=[
                            location['lng'] - 0.01, 
                            location['lng'] + 0.01
                        ],
                        created_at__range=[
                            prediction.prediction_timestamp,
                            prediction.prediction_timestamp + timedelta(hours=1)
                        ]
                    ).count()
                    
                    # Validate the prediction
                    prediction.validate_prediction({'actual_value': actual_rides})
                    validated_count += 1
                
            except Exception as e:
                logger.error(f"Error validating prediction {prediction.id}: {str(e)}")
        
        logger.info(f"Validated {validated_count} predictions")
        
    except Exception as e:
        logger.error(f"Error in prediction validation: {str(e)}")
