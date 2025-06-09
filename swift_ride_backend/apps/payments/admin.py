"""
Admin configuration for payment models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Avg

from apps.payments.models import (
    PaymentMethod, Payment, Wallet, Transaction, Refund,
    PaymentDispute, PaymentSettings, PaymentAnalytics
)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """
    Admin for PaymentMethod model.
    """
    list_display = (
        'user', 'method_type', 'provider', 'display_name',
        'is_default', 'is_verified', 'is_active', 'status_badge'
    )
    list_filter = ('method_type', 'provider', 'is_default', 'is_verified', 'is_active')
    search_fields = ('user__phone_number', 'display_name', 'last_four')
    readonly_fields = ('created_at', 'updated_at')
    
    def status_badge(self, obj):
        """Display status with color coding."""
        if not obj.is_active:
            color = 'red'
            status = 'Inactive'
        elif obj.is_expired:
            color = 'orange'
            status = 'Expired'
        elif not obj.is_verified:
            color = 'orange'
            status = 'Unverified'
        else:
            color = 'green'
            status = 'Active'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    
    status_badge.short_description = 'Status'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin for Payment model.
    """
    list_display = (
        'payment_id', 'payer', 'payee', 'payment_type', 'amount',
        'currency', 'status_badge', 'created_at'
    )
    list_filter = ('payment_type', 'status', 'currency', 'provider', 'created_at')
    search_fields = ('payment_id', 'payer__phone_number', 'payee__phone_number', 'provider_transaction_id')
    readonly_fields = (
        'payment_id', 'created_at', 'updated_at', 'initiated_at',
        'completed_at', 'failed_at', 'total_fees'
    )
    date_hierarchy = 'created_at'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray',
            'refunded': 'purple',
            'partially_refunded': 'purple'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('payment_id', 'payer', 'payee', 'payment_type', 'description')
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'gross_amount', 'platform_fee', 
                      'payment_processing_fee', 'net_amount', 'total_fees')
        }),
        ('Payment Method', {
            'fields': ('payment_method', 'provider', 'provider_transaction_id', 'provider_fee')
        }),
        ('Status & Timing', {
            'fields': ('status', 'initiated_at', 'completed_at', 'failed_at', 'failure_reason')
        }),
        ('Related Objects', {
            'fields': ('ride',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """
    Admin for Wallet model.
    """
    list_display = (
        'user', 'wallet_type', 'balance', 'pending_balance',
        'available_balance', 'total_earned', 'total_spent',
        'status_badge'
    )
    list_filter = ('wallet_type', 'is_active', 'is_frozen', 'auto_withdraw_enabled')
    search_fields = ('user__phone_number',)
    readonly_fields = ('created_at', 'updated_at', 'available_balance')
    
    def status_badge(self, obj):
        """Display status with color coding."""
        if obj.is_frozen:
            color = 'red'
            status = 'Frozen'
        elif not obj.is_active:
            color = 'orange'
            status = 'Inactive'
        else:
            color = 'green'
            status = 'Active'
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    
    status_badge.short_description = 'Status'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin for Transaction model.
    """
    list_display = (
        'transaction_id', 'wallet_user', 'transaction_type', 'amount',
        'status', 'created_at'
    )
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('transaction_id', 'wallet__user__phone_number', 'description')
    readonly_fields = ('transaction_id', 'balance_before', 'balance_after', 'created_at')
    date_hierarchy = 'created_at'
    
    def wallet_user(self, obj):
        return obj.wallet.user
    
    wallet_user.short_description = 'User'
    wallet_user.admin_order_field = 'wallet__user'


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """
    Admin for Refund model.
    """
    list_display = (
        'refund_id', 'payment', 'refund_type', 'amount', 'reason',
        'status_badge', 'requested_at'
    )
    list_filter = ('refund_type', 'reason', 'status', 'requested_at')
    search_fields = ('refund_id', 'payment__payment_id', 'requested_by__phone_number')
    readonly_fields = ('refund_id', 'requested_at', 'processed_at', 'completed_at')
    date_hierarchy = 'requested_at'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'completed': 'green',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'


@admin.register(PaymentDispute)
class PaymentDisputeAdmin(admin.ModelAdmin):
    """
    Admin for PaymentDispute model.
    """
    list_display = (
        'dispute_id', 'payment', 'dispute_type', 'amount',
        'status_badge', 'is_overdue', 'opened_at'
    )
    list_filter = ('dispute_type', 'status', 'opened_at')
    search_fields = ('dispute_id', 'payment__payment_id', 'provider_dispute_id')
    readonly_fields = ('dispute_id', 'opened_at', 'resolved_at', 'is_overdue')
    date_hierarchy = 'opened_at'
    
    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'open': 'orange',
            'under_review': 'blue',
            'resolved': 'green',
            'lost': 'red',
            'won': 'green',
            'closed': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    
    status_badge.short_description = 'Status'


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(admin.ModelAdmin):
    """
    Admin for PaymentSettings model.
    """
    list_display = (
        'platform_fee_percentage', 'minimum_platform_fee', 'maximum_platform_fee',
        'minimum_withdrawal_amount', 'default_currency', 'created_at'
    )
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """Only allow one settings instance."""
        return not PaymentSettings.objects.exists()


@admin.register(PaymentAnalytics)
class PaymentAnalyticsAdmin(admin.ModelAdmin):
    """
    Admin for PaymentAnalytics model.
    """
    list_display = (
        'date', 'total_transactions', 'successful_transactions',
        'total_volume', 'success_rate', 'platform_fees_collected'
    )
    list_filter = ('date',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'date'
    
    def changelist_view(self, request, extra_context=None):
        """Add summary statistics to changelist."""
        response = super().changelist_view(request, extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
            
            # Calculate summary statistics
            summary = qs.aggregate(
                total_volume=Sum('total_volume'),
                total_fees=Sum('platform_fees_collected'),
                total_success_rate=Sum('success_rate'),  # Get total, not average
                count=Count('id')
            )
            
            # Calculate average success rate manually
            if summary['count'] and summary['count'] > 0:
                summary['avg_success_rate'] = summary['total_success_rate'] / summary['count']
            else:
                summary['avg_success_rate'] = 0
            
            # Remove the intermediate values if you don't need them
            summary.pop('total_success_rate', None)
            summary.pop('count', None)
            
            response.context_data['summary'] = summary
        except (AttributeError, KeyError):
            pass
        
        return response
