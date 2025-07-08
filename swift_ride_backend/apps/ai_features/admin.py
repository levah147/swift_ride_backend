from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    AIModel, Recommendation, PredictionResult, FraudAlert,
    ConversationSession, ChatMessage, BusinessInsight
)


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'model_type', 'framework', 'version', 'status',
        'accuracy_display', 'prediction_count', 'last_used_at'
    ]
    list_filter = ['model_type', 'framework', 'status', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['prediction_count', 'last_used_at', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'model_type', 'framework', 'version', 'status')
        }),
        ('Configuration', {
            'fields': ('config', 'hyperparameters'),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': ('accuracy', 'precision', 'recall', 'f1_score'),
            'classes': ('collapse',)
        }),
        ('Deployment', {
            'fields': ('model_path', 'deployment_url'),
            'classes': ('collapse',)
        }),
        ('Training Information', {
            'fields': ('training_data_size', 'training_duration', 'last_trained_at'),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('prediction_count', 'last_used_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def accuracy_display(self, obj):
        if obj.accuracy:
            color = 'green' if obj.accuracy > 0.8 else 'orange' if obj.accuracy > 0.6 else 'red'
            return format_html(
                '<span style="color: {};">{:.1%}</span>',
                color, obj.accuracy
            )
        return '-'
    accuracy_display.short_description = 'Accuracy'


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'recommendation_type', 'status',
        'confidence_display', 'priority', 'created_at'
    ]
    list_filter = ['recommendation_type', 'status', 'priority', 'created_at']
    search_fields = ['title', 'description', 'user__email']
    readonly_fields = ['shown_at', 'clicked_at', 'accepted_at', 'rejected_at', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'model', 'recommendation_type', 'title', 'description')
        }),
        ('Recommendation Data', {
            'fields': ('recommendation_data', 'context'),
            'classes': ('collapse',)
        }),
        ('Scoring', {
            'fields': ('confidence_score', 'relevance_score', 'priority')
        }),
        ('User Interaction', {
            'fields': ('status', 'shown_at', 'clicked_at', 'accepted_at', 'rejected_at')
        }),
        ('Expiration & Testing', {
            'fields': ('expires_at', 'experiment_id', 'variant'),
            'classes': ('collapse',)
        }),
    )
    
    def confidence_display(self, obj):
        color = 'green' if obj.confidence_score > 0.8 else 'orange' if obj.confidence_score > 0.6 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, obj.confidence_score
        )
    confidence_display.short_description = 'Confidence'


@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = [
        'prediction_type', 'model', 'confidence_display',
        'accuracy_display', 'prediction_timestamp'
    ]
    list_filter = ['prediction_type', 'model', 'prediction_timestamp']
    search_fields = ['prediction_type', 'model__name']
    readonly_fields = ['prediction_timestamp', 'validated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('model', 'prediction_type', 'model_version')
        }),
        ('Input & Output', {
            'fields': ('input_data', 'prediction_value', 'context'),
            'classes': ('collapse',)
        }),
        ('Confidence & Validation', {
            'fields': ('confidence_score', 'actual_value', 'accuracy_score', 'validated_at')
        }),
        ('Timestamps', {
            'fields': ('prediction_timestamp',)
        }),
    )
    
    def confidence_display(self, obj):
        color = 'green' if obj.confidence_score > 0.8 else 'orange' if obj.confidence_score > 0.6 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, obj.confidence_score
        )
    confidence_display.short_description = 'Confidence'
    
    def accuracy_display(self, obj):
        if obj.accuracy_score:
            color = 'green' if obj.accuracy_score > 0.8 else 'orange' if obj.accuracy_score > 0.6 else 'red'
            return format_html(
                '<span style="color: {};">{:.1%}</span>',
                color, obj.accuracy_score
            )
        return '-'
    accuracy_display.short_description = 'Accuracy'


@admin.register(FraudAlert)
class FraudAlertAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'user', 'alert_type', 'severity_display',
        'status', 'risk_score_display', 'created_at'
    ]
    list_filter = ['alert_type', 'severity', 'status', 'auto_resolved', 'created_at']
    search_fields = ['title', 'description', 'user__email']
    readonly_fields = ['investigated_at', 'created_at']
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('model', 'user', 'alert_type', 'severity', 'status')
        }),
        ('Details', {
            'fields': ('title', 'description', 'detection_data')
        }),
        ('Risk Assessment', {
            'fields': ('risk_score', 'confidence_score')
        }),
        ('Investigation', {
            'fields': ('investigated_by', 'investigated_at', 'resolution_notes')
        }),
        ('Actions', {
            'fields': ('actions_taken', 'auto_resolved'),
            'classes': ('collapse',)
        }),
    )
    
    def severity_display(self, obj):
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.severity, 'black'), obj.severity.upper()
        )
    severity_display.short_description = 'Severity'
    
    def risk_score_display(self, obj):
        color = 'darkred' if obj.risk_score > 0.8 else 'red' if obj.risk_score > 0.6 else 'orange' if obj.risk_score > 0.4 else 'green'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{:.1%}</span>',
            color, obj.risk_score
        )
    risk_score_display.short_description = 'Risk Score'


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ['created_at', 'response_time']
    fields = ['message_type', 'content', 'intent', 'confidence', 'created_at']


@admin.register(ConversationSession)
class ConversationSessionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'session_type', 'status', 'started_at',
        'duration', 'satisfaction_rating'
    ]
    list_filter = ['session_type', 'status', 'started_at']
    search_fields = ['user__email', 'intent']
    readonly_fields = ['started_at', 'ended_at', 'duration']
    inlines = [ChatMessageInline]
    
    fieldsets = (
        ('Session Information', {
            'fields': ('user', 'session_type', 'status', 'chatbot_model')
        }),
        ('Timing', {
            'fields': ('started_at', 'ended_at', 'duration')
        }),
        ('Context', {
            'fields': ('context', 'intent'),
            'classes': ('collapse',)
        }),
        ('Escalation', {
            'fields': ('escalated_to', 'escalation_reason'),
            'classes': ('collapse',)
        }),
        ('Feedback', {
            'fields': ('satisfaction_rating', 'feedback'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BusinessInsight)
class BusinessInsightAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'insight_type', 'priority_display',
        'confidence_display', 'is_published', 'created_at'
    ]
    list_filter = ['insight_type', 'priority', 'is_published', 'created_at']
    search_fields = ['title', 'description', 'summary']
    readonly_fields = ['reviewed_at', 'published_at', 'created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('model', 'insight_type', 'priority', 'title', 'description')
        }),
        ('Analysis', {
            'fields': ('summary', 'analysis_data', 'metrics'),
            'classes': ('collapse',)
        }),
        ('Recommendations', {
            'fields': ('recommendations', 'expected_impact', 'confidence_score')
        }),
        ('Review & Publishing', {
            'fields': ('reviewed_by', 'reviewed_at', 'action_taken', 'is_published', 'published_at')
        }),
    )
    
    def priority_display(self, obj):
        colors = {
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
            'urgent': 'darkred'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, 'black'), obj.priority.upper()
        )
    priority_display.short_description = 'Priority'
    
    def confidence_display(self, obj):
        color = 'green' if obj.confidence_score > 0.8 else 'orange' if obj.confidence_score > 0.6 else 'red'
        return format_html(
            '<span style="color: {};">{:.1%}</span>',
            color, obj.confidence_score
        )
    confidence_display.short_description = 'Confidence'
