from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, timedelta

from .models import (
    AIModel, Recommendation, PredictionResult, FraudAlert,
    ConversationSession, ChatMessage, BusinessInsight
)
from .serializers import (
    AIModelSerializer, RecommendationSerializer, PredictionResultSerializer,
    FraudAlertSerializer, ConversationSessionSerializer, ChatMessageSerializer,
    BusinessInsightSerializer, RecommendationRequestSerializer,
    PredictionRequestSerializer, FraudDetectionRequestSerializer,
    ChatMessageRequestSerializer, RecommendationInteractionSerializer
)
from .services.recommendation_service import RecommendationService
from .services.prediction_service import PredictionService
from .services.fraud_detection_service import FraudDetectionService

User = get_user_model()
 

class AIModelViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for AI models"""
    
    queryset = AIModel.objects.all()
    serializer_class = AIModelSerializer
    permission_classes = [IsAdminUser]
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate an AI model"""
        model = self.get_object()
        model.status = 'active'
        model.save()
        return Response({'status': 'Model activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate an AI model"""
        model = self.get_object()
        model.status = 'inactive'
        model.save()
        return Response({'status': 'Model deactivated'})


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for recommendations"""
    
    serializer_class = RecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Recommendation.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """Generate new recommendations for the user"""
        serializer = RecommendationRequestSerializer(data=request.data)
        if serializer.is_valid():
            recommendation_service = RecommendationService()
            recommendations = recommendation_service.generate_recommendations(
                user=request.user,
                recommendation_type=serializer.validated_data.get('recommendation_type'),
                context=serializer.validated_data.get('context', {}),
                limit=serializer.validated_data.get('limit', 5)
            )
            
            serialized_recommendations = RecommendationSerializer(
                recommendations, many=True
            ).data
            
            return Response({
                'recommendations': serialized_recommendations,
                'count': len(recommendations)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def interact(self, request, pk=None):
        """Track user interaction with recommendation"""
        recommendation = self.get_object()
        serializer = RecommendationInteractionSerializer(data=request.data)
        
        if serializer.is_valid():
            interaction_type = serializer.validated_data['interaction_type']
            
            if interaction_type == 'shown':
                recommendation.mark_as_shown()
            elif interaction_type == 'clicked':
                recommendation.mark_as_clicked()
            elif interaction_type == 'accepted':
                recommendation.mark_as_accepted()
            elif interaction_type == 'rejected':
                recommendation.mark_as_rejected()
            
            return Response({'status': f'Interaction {interaction_type} recorded'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get recommendation performance metrics"""
        recommendation_service = RecommendationService()
        performance = recommendation_service.get_recommendation_performance(
            recommendation_type=request.query_params.get('type'),
            days=int(request.query_params.get('days', 30))
        )
        return Response(performance)


class PredictionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for predictions"""
    
    queryset = PredictionResult.objects.all()
    serializer_class = PredictionResultSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def predict(self, request):
        """Generate a new prediction"""
        serializer = PredictionRequestSerializer(data=request.data)
        if serializer.is_valid():
            prediction_service = PredictionService()
            prediction_type = serializer.validated_data['prediction_type']
            input_data = serializer.validated_data['input_data']
            context = serializer.validated_data.get('context', {})
            
            try:
                if prediction_type == 'demand_forecast':
                    result = prediction_service.predict_demand(
                        location=input_data.get('location'),
                        time_range=input_data.get('time_range'),
                        context=context
                    )
                elif prediction_type == 'price_optimization':
                    result = prediction_service.predict_price(
                        pickup_location=input_data.get('pickup_location'),
                        destination_location=input_data.get('destination_location'),
                        time=datetime.fromisoformat(input_data.get('time')),
                        vehicle_type=input_data.get('vehicle_type', 'economy'),
                        context=context
                    )
                elif prediction_type == 'churn_prediction':
                    user_id = input_data.get('user_id')
                    user = User.objects.get(id=user_id)
                    result = prediction_service.predict_churn(user, context)
                else:
                    return Response(
                        {'error': 'Unsupported prediction type'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                serialized_result = PredictionResultSerializer(result).data
                return Response(serialized_result)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FraudAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for fraud alerts"""
    
    queryset = FraudAlert.objects.all()
    serializer_class = FraudAlertSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by alert type
        alert_type = self.request.query_params.get('type')
        if alert_type:
            queryset = queryset.filter(alert_type=alert_type)
        
        # Filter by severity
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'])
    def detect(self, request):
        """Run fraud detection"""
        serializer = FraudDetectionRequestSerializer(data=request.data)
        if serializer.is_valid():
            fraud_service = FraudDetectionService()
            detection_type = serializer.validated_data['detection_type']
            data = serializer.validated_data['data']
            user_id = serializer.validated_data.get('user_id')
            
            try:
                user = None
                if user_id:
                    user = User.objects.get(id=user_id)
                
                if detection_type == 'payment_fraud':
                    result = fraud_service.detect_payment_fraud(data, user)
                elif detection_type == 'account_fraud':
                    if not user:
                        return Response(
                            {'error': 'User ID required for account fraud detection'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    result = fraud_service.detect_account_fraud(user)
                elif detection_type == 'ride_fraud':
                    result = fraud_service.detect_ride_fraud(data)
                else:
                    return Response(
                        {'error': 'Unsupported detection type'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                return Response(result)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a fraud alert"""
        alert = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        
        alert.resolve(request.user, resolution_notes)
        
        return Response({'status': 'Alert resolved'})
    
    @action(detail=True, methods=['post'])
    def escalate(self, request, pk=None):
        """Escalate a fraud alert"""
        alert = self.get_object()
        alert.escalate(request.user)
        
        return Response({'status': 'Alert escalated'})


class ConversationSessionViewSet(viewsets.ModelViewSet):
    """ViewSet for conversation sessions"""
    
    serializer_class = ConversationSessionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return ConversationSession.objects.all()
        return ConversationSession.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def send_message(self, request, pk=None):
        """Send a message in the conversation"""
        session = self.get_object()
        serializer = ChatMessageRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            message = ChatMessage.objects.create(
                session=session,
                message_type=serializer.validated_data['message_type'],
                content=serializer.validated_data['message']
            )
            
            # Here you would integrate with your chatbot service
            # For now, we'll create a simple response
            if serializer.validated_data['message_type'] == 'user':
                bot_response = ChatMessage.objects.create(
                    session=session,
                    message_type='bot',
                    content="Thank you for your message. How can I help you today?",
                    intent='greeting',
                    confidence=0.8
                )
                
                return Response({
                    'user_message': ChatMessageSerializer(message).data,
                    'bot_response': ChatMessageSerializer(bot_response).data
                })
            
            return Response(ChatMessageSerializer(message).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def end_session(self, request, pk=None):
        """End the conversation session"""
        session = self.get_object()
        session.end_session()
        
        return Response({'status': 'Session ended'})


class BusinessInsightViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for business insights"""
    
    queryset = BusinessInsight.objects.filter(is_published=True)
    serializer_class = BusinessInsightSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by insight type
        insight_type = self.request.query_params.get('type')
        if insight_type:
            queryset = queryset.filter(insight_type=insight_type)
        
        # Filter by priority
        priority = self.request.query_params.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        return queryset.order_by('-priority', '-confidence_score', '-created_at')
    
    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Publish a business insight"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        insight = self.get_object()
        insight.publish(request.user)
        
        return Response({'status': 'Insight published'})
