from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import (
    Promotion, PromotionUsage, ReferralProgram, Referral,
    LoyaltyProgram, LoyaltyAccount, PromotionCampaign,
    PromotionAnalytics
)

User = get_user_model()


class PromotionSerializer(serializers.ModelSerializer):
    """Serializer for Promotion model"""
    
    discount_amount_display = serializers.SerializerMethodField()
    usage_remaining = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    
    class Meta:
        model = Promotion
        fields = [
            'id', 'name', 'description', 'promotion_type', 'discount_type',
            'status', 'code', 'discount_percentage', 'discount_amount',
            'max_discount_amount', 'usage_limit_per_user', 'total_usage_limit',
            'minimum_ride_amount', 'start_date', 'end_date', 'target_user_type',
            'referrer_reward_amount', 'referee_reward_amount', 'total_usage_count',
            'total_discount_given', 'total_revenue_impact', 'is_stackable',
            'is_auto_apply', 'requires_first_ride', 'discount_amount_display',
            'usage_remaining', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_usage_count', 'total_discount_given', 'total_revenue_impact',
            'created_at', 'updated_at'
        ]
    
    def get_discount_amount_display(self, obj):
        """Get formatted discount amount for display"""
        if obj.discount_type == 'percentage':
            return f"{obj.discount_percentage}% off"
        elif obj.discount_type == 'fixed_amount':
            return f"${obj.discount_amount} off"
        return "Free delivery"


class PromotionUsageSerializer(serializers.ModelSerializer):
    """Serializer for PromotionUsage model"""
    
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    promotion_code = serializers.CharField(source='promotion.code', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = PromotionUsage
        fields = [
            'id', 'promotion', 'user', 'ride', 'discount_amount',
            'original_amount', 'final_amount', 'usage_date',
            'promotion_name', 'promotion_code', 'user_name'
        ]
        read_only_fields = ['id', 'usage_date']


class ReferralProgramSerializer(serializers.ModelSerializer):
    """Serializer for ReferralProgram model"""
    
    total_referrals = serializers.SerializerMethodField()
    active_referrals = serializers.SerializerMethodField()
    
    class Meta:
        model = ReferralProgram
        fields = [
            'id', 'name', 'description', 'is_active', 'referrer_reward_amount',
            'referee_reward_amount', 'minimum_rides_for_referrer',
            'minimum_rides_for_referee', 'reward_expiry_days',
            'max_referrals_per_user', 'max_total_referrals',
            'start_date', 'end_date', 'total_referrals', 'active_referrals',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_referrals(self, obj):
        return obj.referrals.count()
    
    def get_active_referrals(self, obj):
        return obj.referrals.filter(status='pending').count()


class ReferralSerializer(serializers.ModelSerializer):
    """Serializer for Referral model"""
    
    referrer_name = serializers.CharField(source='referrer.get_full_name', read_only=True)
    referee_name = serializers.CharField(source='referee.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    
    class Meta:
        model = Referral
        fields = [
            'id', 'program', 'referrer', 'referee', 'referral_code',
            'status', 'signup_date', 'completion_date', 'reward_date',
            'expiry_date', 'referrer_reward_given', 'referee_reward_given',
            'referrer_name', 'referee_name', 'program_name'
        ]
        read_only_fields = [
            'id', 'referral_code', 'signup_date', 'completion_date',
            'reward_date', 'referrer_reward_given', 'referee_reward_given'
        ]


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyProgram model"""
    
    total_members = serializers.SerializerMethodField()
    
    class Meta:
        model = LoyaltyProgram
        fields = [
            'id', 'name', 'description', 'is_active', 'points_per_dollar',
            'points_per_ride', 'bonus_points_threshold', 'bonus_points_multiplier',
            'points_to_dollar_ratio', 'minimum_redemption_points',
            'total_members', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_total_members(self, obj):
        return obj.accounts.count()


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    """Serializer for LoyaltyAccount model"""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    program_name = serializers.CharField(source='program.name', read_only=True)
    available_balance_dollars = serializers.ReadOnlyField()
    
    class Meta:
        model = LoyaltyAccount
        fields = [
            'id', 'user', 'program', 'total_points_earned',
            'total_points_redeemed', 'current_points_balance',
            'tier_level', 'tier_progress', 'total_rides_count',
            'total_amount_spent', 'user_name', 'program_name',
            'available_balance_dollars', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'total_points_earned', 'total_points_redeemed',
            'current_points_balance', 'tier_level', 'tier_progress',
            'total_rides_count', 'total_amount_spent', 'created_at', 'updated_at'
        ]


class PromotionCampaignSerializer(serializers.ModelSerializer):
    """Serializer for PromotionCampaign model"""
    
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    promotion_code = serializers.CharField(source='promotion.code', read_only=True)
    delivery_rate = serializers.ReadOnlyField()
    open_rate = serializers.ReadOnlyField()
    click_rate = serializers.ReadOnlyField()
    conversion_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = PromotionCampaign
        fields = [
            'id', 'name', 'description', 'campaign_type', 'status',
            'promotion', 'target_user_type', 'subject', 'message',
            'image_url', 'call_to_action', 'scheduled_start', 'scheduled_end',
            'target_audience_size', 'messages_sent', 'messages_delivered',
            'messages_opened', 'messages_clicked', 'conversions',
            'promotion_name', 'promotion_code', 'delivery_rate',
            'open_rate', 'click_rate', 'conversion_rate',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'target_audience_size', 'messages_sent', 'messages_delivered',
            'messages_opened', 'messages_clicked', 'conversions',
            'created_at', 'updated_at'
        ]


class PromotionAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for PromotionAnalytics model"""
    
    promotion_name = serializers.CharField(source='promotion.name', read_only=True)
    promotion_code = serializers.CharField(source='promotion.code', read_only=True)
    
    class Meta:
        model = PromotionAnalytics
        fields = [
            'id', 'promotion', 'date', 'total_uses', 'unique_users',
            'new_users', 'returning_users', 'total_discount_given',
            'total_revenue_generated', 'average_order_value',
            'conversion_rate', 'cost_per_acquisition', 'return_on_investment',
            'promotion_name', 'promotion_code', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PromotionValidationSerializer(serializers.Serializer):
    """Serializer for promotion validation requests"""
    
    promotion_code = serializers.CharField(max_length=50)
    ride_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class PromotionApplicationSerializer(serializers.Serializer):
    """Serializer for promotion application requests"""
    
    promotion_code = serializers.CharField(max_length=50)
    ride_id = serializers.UUIDField()


class ReferralCreateSerializer(serializers.Serializer):
    """Serializer for creating referrals"""
    
    referee_phone = serializers.CharField(max_length=20)
    program_id = serializers.UUIDField()


class LoyaltyRedemptionSerializer(serializers.Serializer):
    """Serializer for loyalty point redemption"""
    
    points_to_redeem = serializers.IntegerField(min_value=1)
    program_id = serializers.UUIDField()
