"""
Permissions for payment operations.
"""

from rest_framework import permissions
from django.contrib.auth import get_user_model

from apps.payments.models import Payment, PaymentMethod, Wallet, Refund

User = get_user_model()


class IsPaymentOwner(permissions.BasePermission):
    """
    Permission to check if user is the payment owner (payer or payee).
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Payment):
            return obj.payer == request.user or obj.payee == request.user
        return False


class IsPaymentMethodOwner(permissions.BasePermission):
    """
    Permission to check if user owns the payment method.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PaymentMethod):
            return obj.user == request.user
        return False


class IsWalletOwner(permissions.BasePermission):
    """
    Permission to check if user owns the wallet.
    """
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Wallet):
            return obj.user == request.user
        return False


class CanRequestRefund(permissions.BasePermission):
    """
    Permission to check if user can request a refund.
    """
    
    def has_permission(self, request, view):
        if request.method == 'POST':
            payment_id = request.data.get('payment_id')
            if payment_id:
                try:
                    payment = Payment.objects.get(payment_id=payment_id)
                    return payment.payer == request.user
                except Payment.DoesNotExist:
                    return False
        return True
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Refund):
            return obj.payment.payer == request.user
        return False


class CanProcessPayment(permissions.BasePermission):
    """
    Permission for payment processing operations.
    """
    
    def has_permission(self, request, view):
        # Only authenticated users can process payments
        if not request.user.is_authenticated:
            return False
        
        # Check if user has sufficient wallet balance for withdrawals
        if view.action == 'withdraw':
            try:
                wallet = request.user.wallet
                amount = float(request.data.get('amount', 0))
                return wallet.can_withdraw(amount)
            except (Wallet.DoesNotExist, ValueError, TypeError):
                return False
        
        return True


class IsPaymentAdmin(permissions.BasePermission):
    """
    Permission for payment administrators.
    """
    
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                (request.user.is_staff or request.user.is_superuser))


class CanViewPaymentAnalytics(permissions.BasePermission):
    """
    Permission to view payment analytics.
    """
    
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                (request.user.is_staff or 
                 hasattr(request.user, 'driver_profile')))


class CanManageWallet(permissions.BasePermission):
    """
    Permission to manage wallet operations.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check specific wallet operations
        if view.action in ['freeze', 'unfreeze']:
            return request.user.is_staff
        
        if view.action in ['topup', 'withdraw', 'transfer']:
            # Check if user's wallet is active and not frozen
            try:
                wallet = request.user.wallet
                return wallet.is_active and not wallet.is_frozen
            except Wallet.DoesNotExist:
                return True  # Allow creation
        
        return True


class CanAccessWebhooks(permissions.BasePermission):
    """
    Permission for webhook endpoints.
    """
    
    def has_permission(self, request, view):
        # Webhooks don't require authentication but should validate signatures
        return True


class IsRefundProcessor(permissions.BasePermission):
    """
    Permission to process refunds.
    """
    
    def has_permission(self, request, view):
        return (request.user.is_authenticated and 
                request.user.is_staff)
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Refund):
            # Staff can process any refund
            if request.user.is_staff:
                return True
            # Users can only view their own refund requests
            return obj.requested_by == request.user
        return False


class CanManagePaymentMethods(permissions.BasePermission):
    """
    Permission to manage payment methods.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Limit number of payment methods per user
        if request.method == 'POST':
            user_methods_count = PaymentMethod.objects.filter(
                user=request.user,
                is_active=True
            ).count()
            
            # Allow maximum 5 payment methods per user
            if user_methods_count >= 5:
                return False
        
        return True
    
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PaymentMethod):
            return obj.user == request.user
        return False


class CanViewTransactionHistory(permissions.BasePermission):
    """
    Permission to view transaction history.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Users can view their own transaction history
        # Staff can view any transaction history
        return True


class HasValidPaymentMethod(permissions.BasePermission):
    """
    Permission to check if user has valid payment method for operations.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Check if operation requires payment method
        if view.action in ['topup', 'withdraw']:
            payment_method_id = request.data.get('payment_method_id')
            if payment_method_id:
                try:
                    payment_method = PaymentMethod.objects.get(
                        id=payment_method_id,
                        user=request.user,
                        is_active=True,
                        is_verified=True
                    )
                    
                    # Check if payment method is not expired
                    if payment_method.is_expired:
                        return False
                    
                    return True
                except PaymentMethod.DoesNotExist:
                    return False
        
        return True


class CanCreateDispute(permissions.BasePermission):
    """
    Permission to create payment disputes.
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        if request.method == 'POST':
            payment_id = request.data.get('payment_id')
            if payment_id:
                try:
                    payment = Payment.objects.get(payment_id=payment_id)
                    # Only payer can create disputes
                    return payment.payer == request.user
                except Payment.DoesNotExist:
                    return False
        
        return True
