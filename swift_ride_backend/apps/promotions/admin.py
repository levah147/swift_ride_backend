from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import (
    Promotion, PromotionUsage, ReferralProgram, Referral,
    LoyaltyProgram, LoyaltyAccount, PromotionCampaign,
    PromotionAnalytics
)


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'code', 'promotion_type', 'discount_type', 'status',
        'usage_count', 'discount_given', 'start_date', 'end_date', 'is_active_display'
    ]
    list_filter = ['promotion_type', 'discount_type', 'status', 'target_user_type']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['total_usage_count', 'total_discount_given', 'total_revenue_impact']
    filter_horizontal = ['target_cities', 'target_vehicle_types']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'promotion_type', 'discount_type', 'status', 'code')
        }),
        ('Discount Settings', {
            'fields': ('discount_percentage', 'discount_amount', 'max_discount_amount')
        }),
        ('Usage Limits', {
            'fields': ('usage_limit_per_user', 'total_usage_limit', 'minimum_ride_amount')
        }),
        ('Time Constraints', {
            'fields': ('start_date', 'end_date')
        }),
        ('Targeting', {
            'fields': ('target_user_type', 'target_cities', 'target_vehicle_types')
        }),
        ('Referral Settings', {
            'fields': ('referrer_reward_amount', 'referee_reward_amount'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_stackable', 'is_auto_apply', 'requires_first_ride')
        }),
        ('Analytics', {
            'fields': ('total_usage_count', 'total_discount_given', 'total_revenue_impact'),
            'classes': ('collapse',)
        })
    )
    
    def usage_count(self, obj):
        return obj.total_usage_count
    usage_count.short_description = 'Usage Count'
    
    def discount_given(self, obj):
        return f"${obj.total_discount_given:,.2f}"
    discount_given.short_description = 'Total Discount'
    
    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Active')
        return format_html('<span style="color: red;">●</span> Inactive')
    is_active_display.short_description = 'Status'


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    list_display = [
        'promotion_code', 'user_name', 'discount_amount', 'original_amount',
        'final_amount', 'usage_date'
    ]
    list_filter = ['usage_date', 'promotion__promotion_type']
    search_fields = ['promotion__code', 'user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = ['usage_date']
    
    def promotion_code(self, obj):
        return obj.promotion.code
    promotion_code.short_description = 'Promotion Code'
    
    def user_name(self, obj):
        return obj.user.get_full_name()
    user_name.short_description = 'User'


@admin.register(ReferralProgram)
class ReferralProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'is_active', 'referrer_reward_amount', 'referee_reward_amount',
        'total_referrals', 'start_date', 'end_date'
    ]
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    
    def total_referrals(self, obj):
        return obj.referrals.count()
    total_referrals.short_description = 'Total Referrals'


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'referral_code', 'referrer_name', 'referee_name', 'status',
        'signup_date', 'completion_date', 'reward_status'
    ]
    list_filter = ['status', 'signup_date', 'completion_date']
    search_fields = ['referral_code', 'referrer__phone_number', 'referee__phone_number']
    readonly_fields = ['referral_code', 'signup_date', 'completion_date', 'reward_date']
    
    def referrer_name(self, obj):
        return obj.referrer.get_full_name()
    referrer_name.short_description = 'Referrer'
    
    def referee_name(self, obj):
        return obj.referee.get_full_name() if obj.referee else 'Pending'
    referee_name.short_description = 'Referee'
    
    def reward_status(self, obj):
        if obj.status == 'rewarded':
            return format_html('<span style="color: green;">●</span> Rewarded')
        elif obj.status == 'completed':
            return format_html('<span style="color: orange;">●</span> Completed')
        elif obj.status == 'pending':
            return format_html('<span style="color: blue;">●</span> Pending')
        return format_html('<span style="color: red;">●</span> {}'.format(obj.status.title()))
    reward_status.short_description = 'Reward Status'


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'is_active', 'points_per_dollar', 'points_per_ride',
        'points_to_dollar_ratio', 'total_members'
    ]
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    
    def total_members(self, obj):
        return obj.accounts.count()
    total_members.short_description = 'Total Members'


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = [
        'user_name', 'tier_level', 'current_points_balance', 'total_points_earned',
        'total_rides_count', 'total_amount_spent'
    ]
    list_filter = ['tier_level', 'program']
    search_fields = ['user__phone_number', 'user__first_name', 'user__last_name']
    readonly_fields = [
        'total_points_earned', 'total_points_redeemed', 'current_points_balance',
        'tier_level', 'tier_progress', 'total_rides_count', 'total_amount_spent'
    ]
    
    def user_name(self, obj):
        return obj.user.get_full_name()
    user_name.short_description = 'User'


@admin.register(PromotionCampaign)
class PromotionCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'campaign_type', 'status', 'promotion_code', 'target_audience_size',
        'messages_sent', 'conversion_rate_display', 'scheduled_start'
    ]
    list_filter = ['campaign_type', 'status', 'target_user_type']
    search_fields = ['name', 'promotion__code']
    readonly_fields = [
        'target_audience_size', 'messages_sent', 'messages_delivered',
        'messages_opened', 'messages_clicked', 'conversions'
    ]
    filter_horizontal = ['target_cities']
    
    def promotion_code(self, obj):
        return obj.promotion.code
    promotion_code.short_description = 'Promotion Code'
    
    def conversion_rate_display(self, obj):
        return f"{obj.conversion_rate:.2f}%"
    conversion_rate_display.short_description = 'Conversion Rate'


@admin.register(PromotionAnalytics)
class PromotionAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'promotion_name', 'date', 'total_uses', 'unique_users',
        'total_discount_given', 'total_revenue_generated', 'conversion_rate'
    ]
    list_filter = ['date', 'promotion__promotion_type']
    search_fields = ['promotion__name', 'promotion__code']
    readonly_fields = ['created_at', 'updated_at']
    
    def promotion_name(self, obj):
        return obj.promotion.name
    promotion_name.short_description = 'Promotion'
