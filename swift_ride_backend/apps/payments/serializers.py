"""
Serializers for payment models.
"""

from rest_framework import serializers
from decimal import Decimal

from apps.payments.models import (
    Payment, PaymentMethod, Wallet, Transaction, Refund, PaymentDispute
)
from apps.users.serializers import UserSerializer


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentMethod model.
    """
    is_expired = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'method_type', 'provider', 'display_name', 'last_four',
            'card_brand', 'card_exp_month', 'card_exp_year', 'bank_name',
            'account_type', 'phone_number', 'is_default', 'is_verified',
            'is_active', 'is_expired', 'created_at'
        ]
        read_only_fields = [
            'id', 'provider_payment_method_id', 'provider_customer_id',
            'is_verified', 'created_at'
        ]


class PaymentMethodCreateSerializer(serializers.Serializer):
    """
    Serializer for creating payment methods.
    """
    method_type = serializers.ChoiceField(choices=PaymentMethod.MethodType.choices)
    provider = serializers.ChoiceField(choices=PaymentMethod.Provider.choices)
    
    # Card fields
    stripe_payment_method_id = serializers.CharField(required=False)
    
    # Mobile money fields
    phone_number = serializers.CharField(required=False)
    
    # Bank account fields
    bank_name = serializers.CharField(required=False)
    account_number = serializers.CharField(required=False)
    account_type = serializers.CharField(required=False)
    
    def validate(self, data):
        method_type = data.get('method_type')
        
        if method_type == PaymentMethod.MethodType.CARD:
            if not data.get('stripe_payment_method_id'):
                raise serializers.ValidationError("Stripe payment method ID is required for card payments")
        
        elif method_type == PaymentMethod.MethodType.MOBILE_MONEY:
            if not data.get('phone_number'):
                raise serializers.ValidationError("Phone number is required for mobile money")
        
        elif method_type == PaymentMethod.MethodType.BANK_ACCOUNT:
            required_fields = ['bank_name', 'account_number', 'account_type']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError(f"{field} is required for bank account")
        
        return data


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer for Wallet model.
    """
    user = UserSerializer(read_only=True)
    available_balance = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Wallet
        fields = [
            'id', 'user', 'wallet_type', 'balance', 'pending_balance',
            'available_balance', 'total_earned', 'total_spent',
            'auto_withdraw_enabled', 'auto_withdraw_threshold',
            'is_active', 'is_frozen', 'freeze_reason', 'created_at'
        ]
        read_only_fields = [
            'id', 'user', 'wallet_type', 'balance', 'pending_balance',
            'total_earned', 'total_spent', 'is_frozen', 'freeze_reason',
            'created_at'
        ]


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Payment model.
    """
    payer = UserSerializer(read_only=True)
    payee = UserSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    total_fees = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_id', 'payer', 'payee', 'payment_type', 'amount',
            'currency', 'platform_fee', 'payment_processing_fee', 'gross_amount',
            'net_amount', 'total_fees', 'payment_method', 'status', 'provider',
            'provider_transaction_id', 'initiated_at', 'completed_at',
            'failed_at', 'description', 'failure_reason', 'ride', 'created_at'
        ]
        read_only_fields = [
            'id', 'payment_id', 'payer', 'payee', 'platform_fee',
            'payment_processing_fee', 'net_amount', 'status', 'provider',
            'provider_transaction_id', 'initiated_at', 'completed_at',
            'failed_at', 'failure_reason', 'created_at'
        ]


class TransactionSerializer(serializers.ModelSerializer):
    """
    Serializer for Transaction model.
    """
    wallet_user = serializers.CharField(source='wallet.user.get_full_name', read_only=True)
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'transaction_id', 'wallet', 'wallet_user', 'transaction_type',
            'amount', 'balance_before', 'balance_after', 'status', 'description',
            'payment', 'ride', 'from_wallet', 'to_wallet', 'created_at'
        ]
        read_only_fields = [
            'id', 'transaction_id', 'balance_before', 'balance_after',
            'created_at'
        ]


class RefundSerializer(serializers.ModelSerializer):
    """
    Serializer for Refund model.
    """
    payment = PaymentSerializer(read_only=True)
    requested_by = UserSerializer(read_only=True)
    processed_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Refund
        fields = [
            'id', 'refund_id', 'payment', 'refund_type', 'amount', 'reason',
            'status', 'provider_refund_id', 'requested_at', 'processed_at',
            'completed_at', 'description', 'admin_notes', 'requested_by',
            'processed_by'
        ]
        read_only_fields = [
            'id', 'refund_id', 'payment', 'status', 'provider_refund_id',
            'requested_at', 'processed_at', 'completed_at', 'requested_by',
            'processed_by'
        ]


class RefundCreateSerializer(serializers.Serializer):
    """
    Serializer for creating refunds.
    """
    payment_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('0.01'))
    reason = serializers.ChoiceField(choices=Refund.Reason.choices)
    description = serializers.CharField(required=False)
    
    def validate_payment_id(self, value):
        try:
            payment = Payment.objects.get(payment_id=value)
            if payment.status != Payment.Status.COMPLETED:
                raise serializers.ValidationError("Payment must be completed to request refund")
            return value
        except Payment.DoesNotExist:
            raise serializers.ValidationError("Payment not found")
    
    def validate(self, data):
        payment = Payment.objects.get(payment_id=data['payment_id'])
        if data['amount'] > payment.amount:
            raise serializers.ValidationError("Refund amount cannot exceed payment amount")
        return data


class PaymentDisputeSerializer(serializers.ModelSerializer):
    """
    Serializer for PaymentDispute model.
    """
    payment = PaymentSerializer(read_only=True)
    assigned_to = UserSerializer(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PaymentDispute
        fields = [
            'id', 'dispute_id', 'payment', 'dispute_type', 'amount', 'status',
            'provider_dispute_id', 'opened_at', 'due_date', 'resolved_at',
            'reason', 'evidence', 'resolution_notes', 'assigned_to',
            'is_overdue'
        ]
        read_only_fields = [
            'id', 'dispute_id', 'payment', 'provider_dispute_id',
            'opened_at', 'resolved_at'
        ]


class WalletTopupSerializer(serializers.Serializer):
    """
    Serializer for wallet top-up requests.
    """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    payment_method_id = serializers.IntegerField()
    
    def validate_payment_method_id(self, value):
        request = self.context.get('request')
        if request and request.user:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=value,
                    user=request.user,
                    is_active=True
                )
                return value
            except PaymentMethod.DoesNotExist:
                raise serializers.ValidationError("Payment method not found")
        raise serializers.ValidationError("Invalid payment method")


class WithdrawalSerializer(serializers.Serializer):
    """
    Serializer for withdrawal requests.
    """
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal('1.00'))
    payment_method_id = serializers.IntegerField()
    
    def validate_payment_method_id(self, value):
        request = self.context.get('request')
        if request and request.user:
            try:
                payment_method = PaymentMethod.objects.get(
                    id=value,
                    user=request.user,
                    is_active=True,
                    method_type__in=[
                        PaymentMethod.MethodType.BANK_ACCOUNT,
                        PaymentMethod.MethodType.MOBILE_MONEY
                    ]
                )
                return value
            except PaymentMethod.DoesNotExist:
                raise serializers.ValidationError("Valid withdrawal method not found")
        raise serializers.ValidationError("Invalid payment method")


class PaymentStatsSerializer(serializers.Serializer):
    """
    Serializer for payment statistics.
    """
    total_payments = serializers.IntegerField()
    successful_payments = serializers.IntegerField()
    failed_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    success_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    average_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
