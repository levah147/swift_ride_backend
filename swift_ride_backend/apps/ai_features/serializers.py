from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    AIModel, Recommendation, PredictionResult, FraudAlert,
    ConversationSession, ChatMessage, BusinessInsight
)

User = get_user_model()


class AIModelSerializer(serializers.ModelSerializer):
    """Serializer for AI models"""
    
    class Meta:
        model = AIModel
        fields = [
            'id', 'name', 'description', 'model_type', 'framework',
            'version', 'status', 'accuracy', 'precision', 'recall',
            'f1_score', 'prediction_count', 'last_used_at', 'created_at'
        ]
        read_only_fields = ['id', 'prediction_count', 'last_used_at', 'created_at']


class RecommendationSerializer(serializers.ModelSerializer):
    """Serializer for recommendations"""
    
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = Recommendation
        fields = [
            'id', 'recommendation_type', 'title', 'description',
            'recommendation_data', 'confidence_score', 'relevance_score',
            'priority', 'status', 'shown_at', 'clicked_at', 'accepted_at',
            'expires_at', 'model_name', 'created_at'
        ]
        read_only_fields = [
            'id', 'shown_at', 'clicked_at', 'accepted_at', 'model_name', 'created_at'
        ]


class PredictionResultSerializer(serializers.ModelSerializer):
    """Serializer for prediction results"""
    
    model_name = serializers.CharField(source='model.name', read_only=True)
    
    class Meta:
        model = PredictionResult
        fields = [
            'id', 'prediction_type', 'input_data', 'prediction_value',
            'confidence_score', 'prediction_timestamp', 'actual_value',
            'accuracy_score', 'validated_at', 'model_name', 'model_version'
        ]
        read_only_fields = [
            'id', 'prediction_timestamp', 'actual_value', 'accuracy_score',
            'validated_at', 'model_name'
        ]


class FraudAlertSerializer(serializers.ModelSerializer):
    """Serializer for fraud alerts"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    model_name = serializers.CharField(source='model.name', read_only=True)
    investigated_by_name = serializers.CharField(
        source='investigated_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = FraudAlert
        fields = [
            'id', 'alert_type', 'severity', 'status', 'title', 'description',
            'detection_data', 'risk_score', 'confidence_score', 'actions_taken',
            'investigated_at', 'resolution_notes', 'auto_resolved',
            'user_email', 'model_name', 'investigated_by_name', 'created_at'
        ]
        read_only_fields = [
            'id', 'user_email', 'model_name', 'investigated_by_name', 'created_at'
        ]


class ConversationSessionSerializer(serializers.ModelSerializer):
    """Serializer for conversation sessions"""
    
    user_email = serializers.CharField(source='user.email', read_only=True)
    escalated_to_name = serializers.CharField(
        source='escalated_to.get_full_name', read_only=True
    )
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ConversationSession
        fields = [
            'id', 'session_type', 'status', 'started_at', 'ended_at',
            'duration', 'intent', 'escalation_reason', 'satisfaction_rating',
            'feedback', 'user_email', 'escalated_to_name', 'message_count'
        ]
        read_only_fields = [
            'id', 'started_at', 'ended_at', 'duration', 'user_email',
            'escalated_to_name', 'message_count'
        ]
    
    def get_message_count(self, obj):
        return obj.messages.count()


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    
    class Meta:
        model = ChatMessage
        fields = [
            'id', 'message_type', 'content', 'intent', 'confidence',
            'entities', 'response_time', 'model_version', 'is_helpful',
            'feedback', 'created_at'
        ]
        read_only_fields = [
            'id', 'intent', 'confidence', 'entities', 'response_time',
            'model_version', 'created_at'
        ]


class BusinessInsightSerializer(serializers.ModelSerializer):
    """Serializer for business insights"""
    
    model_name = serializers.CharField(source='model.name', read_only=True)
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.get_full_name', read_only=True
    )
    
    class Meta:
        model = BusinessInsight
        fields = [
            'id', 'insight_type', 'priority', 'title', 'description',
            'summary', 'analysis_data', 'metrics', 'recommendations',
            'expected_impact', 'confidence_score', 'reviewed_at',
            'action_taken', 'is_published', 'published_at',
            'model_name', 'reviewed_by_name', 'created_at'
        ]
        read_only_fields = [
            'id', 'model_name', 'reviewed_by_name', 'created_at'
        ]


# Request/Response serializers for API endpoints

class RecommendationRequestSerializer(serializers.Serializer):
    """Serializer for recommendation requests"""
    
    recommendation_type = serializers.ChoiceField(
        choices=['driver', 'destination', 'promotion', 'vehicle', 'timing'],
        required=False
    )
    context = serializers.JSONField(required=False, default=dict)
    limit = serializers.IntegerField(min_value=1, max_value=20, default=5)


class PredictionRequestSerializer(serializers.Serializer):
    """Serializer for prediction requests"""
    
    prediction_type = serializers.ChoiceField(
        choices=[
            'demand_forecast', 'price_optimization', 'eta_prediction',
            'churn_prediction', 'revenue_forecast'
        ]
    )
    input_data = serializers.JSONField()
    context = serializers.JSONField(required=False, default=dict)


class FraudDetectionRequestSerializer(serializers.Serializer):
    """Serializer for fraud detection requests"""
    
    detection_type = serializers.ChoiceField(
        choices=['payment_fraud', 'account_fraud', 'ride_fraud']
    )
    data = serializers.JSONField()
    user_id = serializers.UUIDField(required=False)


class ChatMessageRequestSerializer(serializers.Serializer):
    """Serializer for chat message requests"""
    
    session_id = serializers.UUIDField()
    message = serializers.CharField(max_length=1000)
    message_type = serializers.ChoiceField(
        choices=['user', 'system'],
        default='user'
    )


class RecommendationInteractionSerializer(serializers.Serializer):
    """Serializer for recommendation interaction tracking"""
    
    recommendation_id = serializers.UUIDField()
    interaction_type = serializers.ChoiceField(
        choices=['shown', 'clicked', 'accepted', 'rejected']
    )
    metadata = serializers.JSONField(required=False, default=dict)
