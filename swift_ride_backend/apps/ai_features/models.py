from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.common.models import BaseModel
import uuid
import json

User = get_user_model()


class AIModel(BaseModel):
    """Model for managing AI/ML models"""
    
    MODEL_TYPES = [
        ('recommendation', 'Recommendation Engine'),
        ('prediction', 'Predictive Analytics'),
        ('classification', 'Classification Model'),
        ('clustering', 'Clustering Model'),
        ('nlp', 'Natural Language Processing'),
        ('computer_vision', 'Computer Vision'),
        ('time_series', 'Time Series Analysis'),
        ('anomaly_detection', 'Anomaly Detection'),
    ]
    
    FRAMEWORKS = [
        ('tensorflow', 'TensorFlow'),
        ('pytorch', 'PyTorch'),
        ('scikit_learn', 'Scikit-learn'),
        ('xgboost', 'XGBoost'),
        ('lightgbm', 'LightGBM'),
        ('custom', 'Custom Implementation'),
    ]
    
    STATUS_CHOICES = [
        ('training', 'Training'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    model_type = models.CharField(max_length=20, choices=MODEL_TYPES)
    framework = models.CharField(max_length=20, choices=FRAMEWORKS)
    version = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='training')
    
    # Model configuration
    config = models.JSONField(default=dict, blank=True)
    hyperparameters = models.JSONField(default=dict, blank=True)
    
    # Performance metrics
    accuracy = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    precision = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    recall = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    f1_score = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Model files and deployment
    model_path = models.CharField(max_length=500, blank=True, null=True)
    deployment_url = models.URLField(blank=True, null=True)
    
    # Training information
    training_data_size = models.PositiveIntegerField(null=True, blank=True)
    training_duration = models.DurationField(null=True, blank=True)
    last_trained_at = models.DateTimeField(null=True, blank=True)
    
    # Usage tracking
    prediction_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ai_models'
        ordering = ['-created_at']
        unique_together = ['name', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.model_type})"
    
    def increment_usage(self):
        """Increment usage counter and update last used timestamp"""
        self.prediction_count += 1
        self.last_used_at = timezone.now()
        self.save(update_fields=['prediction_count', 'last_used_at'])


class Recommendation(BaseModel):
    """Model for storing AI-generated recommendations"""
    
    RECOMMENDATION_TYPES = [
        ('driver', 'Driver Recommendation'),
        ('destination', 'Destination Suggestion'),
        ('route', 'Route Optimization'),
        ('promotion', 'Promotion Offer'),
        ('vehicle', 'Vehicle Type'),
        ('timing', 'Optimal Timing'),
        ('price', 'Price Suggestion'),
        ('service', 'Service Recommendation'),
    ]
    
    STATUSES = [
        ('pending', 'Pending'),
        ('shown', 'Shown to User'),
        ('clicked', 'Clicked'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='ai_recommendations'
    )
    model = models.ForeignKey(
        AIModel, 
        on_delete=models.CASCADE, 
        related_name='recommendations'
    )
    
    recommendation_type = models.CharField(max_length=20, choices=RECOMMENDATION_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Recommendation data
    recommendation_data = models.JSONField(default=dict)
    context = models.JSONField(default=dict, blank=True)
    
    # Scoring and ranking
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    relevance_score = models.FloatField(
        default=0.5,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    priority = models.PositiveIntegerField(default=1)
    
    # User interaction
    status = models.CharField(max_length=20, choices=STATUSES, default='pending')
    shown_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # A/B testing
    experiment_id = models.CharField(max_length=100, blank=True, null=True)
    variant = models.CharField(max_length=50, blank=True, null=True)
    
    class Meta:
        db_table = 'ai_recommendations'
        ordering = ['-priority', '-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['recommendation_type', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self):
        return f"{self.recommendation_type} for {self.user.email} - {self.title}"
    
    def mark_as_shown(self):
        """Mark recommendation as shown to user"""
        if self.status == 'pending':
            self.status = 'shown'
            self.shown_at = timezone.now()
            self.save(update_fields=['status', 'shown_at'])
    
    def mark_as_clicked(self):
        """Mark recommendation as clicked by user"""
        if self.status in ['pending', 'shown']:
            self.status = 'clicked'
            self.clicked_at = timezone.now()
            self.save(update_fields=['status', 'clicked_at'])
    
    def mark_as_accepted(self):
        """Mark recommendation as accepted by user"""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save(update_fields=['status', 'accepted_at'])
    
    def mark_as_rejected(self):
        """Mark recommendation as rejected by user"""
        self.status = 'rejected'
        self.rejected_at = timezone.now()
        self.save(update_fields=['status', 'rejected_at'])
    
    @property
    def is_expired(self):
        """Check if recommendation has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class PredictionResult(BaseModel):
    """Model for storing AI prediction results"""
    
    PREDICTION_TYPES = [
        ('demand_forecast', 'Demand Forecasting'),
        ('price_optimization', 'Price Optimization'),
        ('eta_prediction', 'ETA Prediction'),
        ('churn_prediction', 'Churn Prediction'),
        ('revenue_forecast', 'Revenue Forecasting'),
        ('fraud_detection', 'Fraud Detection'),
        ('route_optimization', 'Route Optimization'),
        ('driver_matching', 'Driver Matching'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        AIModel, 
        on_delete=models.CASCADE, 
        related_name='predictions'
    )
    
    prediction_type = models.CharField(max_length=30, choices=PREDICTION_TYPES)
    
    # Input and output data
    input_data = models.JSONField(default=dict)
    prediction_value = models.JSONField(default=dict)
    context = models.JSONField(default=dict, blank=True)
    
    # Prediction metadata
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    prediction_timestamp = models.DateTimeField(default=timezone.now)
    
    # Validation and accuracy
    actual_value = models.JSONField(null=True, blank=True)
    accuracy_score = models.FloatField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    
    # Model version tracking
    model_version = models.CharField(max_length=20, blank=True)
    
    class Meta:
        db_table = 'ai_prediction_results'
        ordering = ['-prediction_timestamp']
        indexes = [
            models.Index(fields=['prediction_type', 'prediction_timestamp']),
            models.Index(fields=['model', 'prediction_timestamp']),
            models.Index(fields=['confidence_score']),
        ]
    
    def __str__(self):
        return f"{self.prediction_type} - {self.prediction_timestamp}"
    
    def validate_prediction(self, actual_value):
        """Validate prediction against actual outcome"""
        self.actual_value = actual_value
        self.validated_at = timezone.now()
        
        # Calculate accuracy based on prediction type
        if self.prediction_type in ['demand_forecast', 'revenue_forecast']:
            predicted = self.prediction_value.get('predicted_value', 0)
            actual = actual_value.get('actual_value', 0)
            if actual > 0:
                error_rate = abs(predicted - actual) / actual
                self.accuracy_score = max(0, 1 - error_rate)
        
        self.save(update_fields=['actual_value', 'accuracy_score', 'validated_at'])


class FraudAlert(BaseModel):
    """Model for fraud detection alerts"""
    
    ALERT_TYPES = [
        ('payment_fraud', 'Payment Fraud'),
        ('account_fraud', 'Account Fraud'),
        ('ride_fraud', 'Ride Fraud'),
        ('promotion_abuse', 'Promotion Abuse'),
        ('identity_theft', 'Identity Theft'),
        ('fake_gps', 'Fake GPS Location'),
        ('multiple_accounts', 'Multiple Accounts'),
        ('suspicious_behavior', 'Suspicious Behavior'),
    ]
    
    SEVERITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    STATUSES = [
        ('open', 'Open'),
        ('investigating', 'Under Investigation'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
        ('escalated', 'Escalated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        AIModel, 
        on_delete=models.CASCADE, 
        related_name='fraud_alerts'
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='fraud_alerts',
        null=True, 
        blank=True
    )
    
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    status = models.CharField(max_length=20, choices=STATUSES, default='open')
    
    # Alert details
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Detection data
    detection_data = models.JSONField(default=dict)
    risk_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Investigation
    investigated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='investigated_fraud_alerts'
    )
    investigated_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Actions taken
    actions_taken = models.JSONField(default=list, blank=True)
    auto_resolved = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ai_fraud_alerts'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['alert_type', 'severity']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.severity} - {self.user.email if self.user else 'System'}"
    
    def escalate(self, escalated_by=None):
        """Escalate fraud alert to higher severity"""
        severity_order = ['low', 'medium', 'high', 'critical']
        current_index = severity_order.index(self.severity)
        if current_index < len(severity_order) - 1:
            self.severity = severity_order[current_index + 1]
            self.status = 'escalated'
            if escalated_by:
                self.investigated_by = escalated_by
                self.investigated_at = timezone.now()
            self.save()
    
    def resolve(self, resolved_by, resolution_notes=""):
        """Mark fraud alert as resolved"""
        self.status = 'resolved'
        self.investigated_by = resolved_by
        self.investigated_at = timezone.now()
        self.resolution_notes = resolution_notes
        self.save()


class ConversationSession(BaseModel):
    """Model for chatbot conversation sessions"""
    
    SESSION_TYPES = [
        ('support', 'Customer Support'),
        ('booking', 'Ride Booking'),
        ('general', 'General Inquiry'),
        ('complaint', 'Complaint'),
        ('feedback', 'Feedback'),
    ]
    
    STATUSES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('escalated', 'Escalated to Human'),
        ('abandoned', 'Abandoned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='chat_sessions'
    )
    
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    status = models.CharField(max_length=20, choices=STATUSES, default='active')
    
    # Session metadata
    started_at = models.DateTimeField(default=timezone.now)
    ended_at = models.DateTimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    
    # AI model used
    chatbot_model = models.ForeignKey(
        AIModel, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='chat_sessions'
    )
    
    # Conversation context
    context = models.JSONField(default=dict, blank=True)
    intent = models.CharField(max_length=100, blank=True)
    
    # Human escalation
    escalated_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='escalated_chat_sessions'
    )
    escalation_reason = models.TextField(blank=True)
    
    # Satisfaction
    satisfaction_rating = models.PositiveIntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    feedback = models.TextField(blank=True)
    
    class Meta:
        db_table = 'ai_conversation_sessions'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Chat Session - {self.user.email} - {self.session_type}"
    
    def end_session(self):
        """End the conversation session"""
        if self.status == 'active':
            self.status = 'completed'
            self.ended_at = timezone.now()
            if self.started_at:
                self.duration = self.ended_at - self.started_at
            self.save()
    
    def escalate_to_human(self, agent, reason=""):
        """Escalate conversation to human agent"""
        self.status = 'escalated'
        self.escalated_to = agent
        self.escalation_reason = reason
        self.save()


class ChatMessage(BaseModel):
    """Model for individual chat messages"""
    
    MESSAGE_TYPES = [
        ('user', 'User Message'),
        ('bot', 'Bot Response'),
        ('system', 'System Message'),
        ('agent', 'Human Agent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ConversationSession, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    content = models.TextField()
    
    # AI processing
    intent = models.CharField(max_length=100, blank=True)
    confidence = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    entities = models.JSONField(default=dict, blank=True)
    
    # Response metadata
    response_time = models.DurationField(null=True, blank=True)
    model_version = models.CharField(max_length=20, blank=True)
    
    # User interaction
    is_helpful = models.BooleanField(null=True, blank=True)
    feedback = models.TextField(blank=True)
    
    class Meta:
        db_table = 'ai_chat_messages'
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.message_type} - {self.content[:50]}..."


class BusinessInsight(BaseModel):
    """Model for AI-generated business insights"""
    
    INSIGHT_TYPES = [
        ('trend_analysis', 'Trend Analysis'),
        ('performance_metric', 'Performance Metric'),
        ('anomaly_detection', 'Anomaly Detection'),
        ('recommendation', 'Business Recommendation'),
        ('forecast', 'Business Forecast'),
        ('optimization', 'Optimization Opportunity'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model = models.ForeignKey(
        AIModel, 
        on_delete=models.CASCADE, 
        related_name='business_insights'
    )
    
    insight_type = models.CharField(max_length=30, choices=INSIGHT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS)
    
    # Insight content
    title = models.CharField(max_length=200)
    description = models.TextField()
    summary = models.TextField(blank=True)
    
    # Data and analysis
    analysis_data = models.JSONField(default=dict)
    metrics = models.JSONField(default=dict, blank=True)
    
    # Recommendations
    recommendations = models.JSONField(default=list, blank=True)
    expected_impact = models.TextField(blank=True)
    
    # Confidence and validation
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # Review and action
    reviewed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='reviewed_insights'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True)
    
    # Visibility
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'ai_business_insights'
        ordering = ['-priority', '-confidence_score', '-created_at']
        indexes = [
            models.Index(fields=['insight_type', 'priority']),
            models.Index(fields=['is_published', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.insight_type} - {self.title}"
    
    def publish(self, published_by=None):
        """Publish the business insight"""
        self.is_published = True
        self.published_at = timezone.now()
        if published_by:
            self.reviewed_by = published_by
            self.reviewed_at = timezone.now()
        self.save()
