"""
Views for the payments app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count, Avg
from decimal import Decimal

from apps.payments.models import (
    Payment, PaymentMethod, Wallet, Transaction, Refund, PaymentDispute
)
from apps.payments.serializers import (
    PaymentSerializer, PaymentMethodSerializer, PaymentMethodCreateSerializer,
    WalletSerializer, TransactionSerializer, RefundSerializer,
    RefundCreateSerializer, PaymentDisputeSerializer, WalletTopupSerializer,
    WithdrawalSerializer, PaymentStatsSerializer
)
from apps.payments.services.payment_service import PaymentService
from apps.payments.services.wallet_service import WalletService


class PaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for payments.
    """
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get payments for the current user."""
        return Payment.objects.filter(
            Q(payer=self.request.user) | Q(payee=self.request.user),
            is_deleted=False
        ).order_by('-created_at')
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get payment statistics for the user."""
        user = request.user
        
        # Get user payments
        payments = Payment.objects.filter(
            Q(payer=user) | Q(payee=user),
            is_deleted=False
        )
        
        # Calculate statistics
        total_payments = payments.count()
        successful_payments = payments.filter(status=Payment.Status.COMPLETED).count()
        failed_payments = payments.filter(status=Payment.Status.FAILED).count()
        
        total_amount = payments.filter(
            status=Payment.Status.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
        average_amount = total_amount / successful_payments if successful_payments > 0 else Decimal('0.00')
        
        stats = {
            'total_payments': total_payments,
            'successful_payments': successful_payments,
            'failed_payments': failed_payments,
            'total_amount': total_amount,
            'success_rate': success_rate,
            'average_amount': average_amount
        }
        
        serializer = PaymentStatsSerializer(stats)
        return Response(serializer.data)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    """
    ViewSet for payment methods.
    """
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get payment methods for the current user."""
        return PaymentMethod.objects.filter(user=self.request.user, is_active=True)
    
    def get_serializer_class(self):
        """Get serializer class based on action."""
        if self.action == 'create':
            return PaymentMethodCreateSerializer
        return PaymentMethodSerializer
    
    def create(self, request):
        """Add a new payment method."""
        serializer = PaymentMethodCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            payment_method, message = PaymentService.add_payment_method(request.user, data)
            
            if payment_method:
                response_serializer = PaymentMethodSerializer(payment_method)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """Set payment method as default."""
        payment_method = self.get_object()
        
        # Remove default from other methods
        PaymentMethod.objects.filter(
            user=request.user,
            is_default=True
        ).update(is_default=False)
        
        # Set this method as default
        payment_method.is_default = True
        payment_method.save()
        
        return Response({'message': 'Payment method set as default'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate payment method."""
        payment_method = self.get_object()
        payment_method.is_active = False
        payment_method.save()
        
        return Response({'message': 'Payment method deactivated'})


class WalletViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for wallets.
    """
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get wallet for the current user."""
        return Wallet.objects.filter(user=self.request.user)
    
    def list(self, request):
        """Get user's wallet."""
        try:
            wallet = request.user.wallet
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            # Create wallet if it doesn't exist
            wallet_type = Wallet.WalletType.DRIVER if hasattr(request.user, 'driver_profile') else Wallet.WalletType.RIDER
            wallet = WalletService.get_or_create_wallet(request.user, wallet_type)
            serializer = self.get_serializer(wallet)
            return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def topup(self, request):
        """Top up wallet."""
        serializer = WalletTopupSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Get payment method
            payment_method = PaymentMethod.objects.get(
                id=data['payment_method_id'],
                user=request.user
            )
            
            # Create top-up payment
            payment = PaymentService.create_wallet_topup(
                request.user,
                payment_method,
                data['amount']
            )
            
            # Process payment
            success, message = PaymentService.process_payment(payment)
            
            if success:
                return Response({
                    'message': 'Wallet top-up initiated successfully',
                    'payment_id': payment.payment_id
                })
            else:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def withdraw(self, request):
        """Withdraw from wallet."""
        serializer = WithdrawalSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Get payment method
            payment_method = PaymentMethod.objects.get(
                id=data['payment_method_id'],
                user=request.user
            )
            
            # Process withdrawal
            success, message = PaymentService.process_withdrawal(
                request.user,
                data['amount'],
                payment_method
            )
            
            if success:
                return Response({'message': message})
            else:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def transactions(self, request):
        """Get wallet transactions."""
        try:
            wallet = request.user.wallet
            limit = int(request.query_params.get('limit', 50))
            offset = int(request.query_params.get('offset', 0))
            
            transactions = WalletService.get_wallet_transactions(wallet, limit, offset)
            serializer = TransactionSerializer(transactions, many=True)
            
            return Response(serializer.data)
        except Wallet.DoesNotExist:
            return Response({'transactions': []})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get wallet statistics."""
        try:
            wallet = request.user.wallet
            days = int(request.query_params.get('days', 30))
            
            stats = WalletService.calculate_wallet_statistics(wallet, days)
            return Response(stats)
        except Wallet.DoesNotExist:
            return Response({
                'period_days': 30,
                'total_credits': '0.00',
                'total_debits': '0.00',
                'net_change': '0.00',
                'transaction_count': 0,
                'average_transaction': '0.00'
            })


class RefundViewSet(viewsets.ModelViewSet):
    """
    ViewSet for refunds.
    """
    serializer_class = RefundSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get refunds for the current user."""
        return Refund.objects.filter(
            payment__payer=self.request.user
        ).order_by('-created_at')
    
    def get_serializer_class(self):
        """Get serializer class based on action."""
        if self.action == 'create':
            return RefundCreateSerializer
        return RefundSerializer
    
    def create(self, request):
        """Create a refund request."""
        serializer = RefundCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            data = serializer.validated_data
            
            # Get payment
            payment = Payment.objects.get(payment_id=data['payment_id'])
            
            # Check if user owns the payment
            if payment.payer != request.user:
                return Response(
                    {'error': 'You can only request refunds for your own payments'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Create refund
            refund, message = PaymentService.create_refund(
                payment=payment,
                amount=data['amount'],
                reason=data['reason'],
                requested_by=request.user
            )
            
            if refund:
                response_serializer = RefundSerializer(refund)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentWebhookViewSet(viewsets.ViewSet):
    """
    ViewSet for payment webhooks.
    """
    permission_classes = []  # No authentication required for webhooks
    
    @action(detail=False, methods=['post'], url_path='mpesa/callback')
    def mpesa_callback(self, request):
        """Handle M-Pesa payment callback."""
        from apps.payments.services.mpesa_service import MpesaService
        
        success, message = MpesaService.handle_callback(request.data)
        
        if success:
            return Response({'message': message})
        else:
            return Response(
                {'error': message},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['post'], url_path='stripe/webhook')
    def stripe_webhook(self, request):
        """Handle Stripe webhook."""
        # Implement Stripe webhook handling
        return Response({'message': 'Stripe webhook received'})
