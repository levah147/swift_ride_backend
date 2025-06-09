"""
Service for handling payment operations.
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.payments.models import Payment, PaymentMethod, Wallet, Transaction, PaymentSettings


class PaymentService:
    """
    Service for handling payment operations.
    """
    
    @staticmethod
    def create_ride_payment(ride, payment_method, amount):
        """
        Create a payment for a ride.
        """
        settings = PaymentSettings.get_current_settings()
        
        # Calculate fees
        platform_fee = PaymentService._calculate_platform_fee(amount, settings)
        processing_fee = PaymentService._calculate_processing_fee(amount, payment_method, settings)
        
        # Create payment
        payment = Payment.objects.create(
            payer=ride.rider,
            payee=ride.driver,
            payment_type=Payment.PaymentType.RIDE_PAYMENT,
            amount=amount,
            gross_amount=amount,
            platform_fee=platform_fee,
            payment_processing_fee=processing_fee,
            payment_method=payment_method,
            ride=ride,
            description=f"Payment for ride from {ride.pickup_location} to {ride.destination}",
            provider=payment_method.provider if payment_method else 'cash'
        )
        
        return payment
    
    @staticmethod
    def process_payment(payment):
        """
        Process a payment based on the payment method.
        """
        try:
            if not payment.payment_method:
                # Cash payment
                return PaymentService._process_cash_payment(payment)
            
            elif payment.payment_method.provider == PaymentMethod.Provider.STRIPE:
                from apps.payments.services.stripe_service import StripeService
                return StripeService.process_payment(payment)
            
            elif payment.payment_method.provider == PaymentMethod.Provider.MPESA:
                from apps.payments.services.mpesa_service import MpesaService
                return MpesaService.process_payment(payment)
            
            else:
                payment.mark_as_failed("Unsupported payment provider")
                return False, "Unsupported payment provider"
        
        except Exception as e:
            payment.mark_as_failed(str(e))
            return False, str(e)
    
    @staticmethod
    def complete_payment(payment):
        """
        Complete a payment and update wallets.
        """
        with transaction.atomic():
            # Mark payment as completed
            payment.mark_as_completed()
            
            # Update driver wallet
            if payment.payee:
                driver_wallet = PaymentService._get_or_create_wallet(
                    payment.payee, 
                    Wallet.WalletType.DRIVER
                )
                
                # Add net amount to driver wallet
                driver_wallet.add_funds(
                    payment.net_amount,
                    f"Payment for ride {payment.ride.id if payment.ride else 'N/A'}"
                )
            
            # Create transaction records
            PaymentService._create_payment_transactions(payment)
            
            # Send notifications
            PaymentService._send_payment_notifications(payment)
            
            return True, "Payment completed successfully"
    
    @staticmethod
    def create_wallet_topup(user, payment_method, amount):
        """
        Create a wallet top-up payment.
        """
        settings = PaymentSettings.get_current_settings()
        processing_fee = PaymentService._calculate_processing_fee(amount, payment_method, settings)
        
        payment = Payment.objects.create(
            payer=user,
            payment_type=Payment.PaymentType.WALLET_TOPUP,
            amount=amount,
            gross_amount=amount,
            payment_processing_fee=processing_fee,
            payment_method=payment_method,
            description="Wallet top-up",
            provider=payment_method.provider
        )
        
        return payment
    
    @staticmethod
    def process_withdrawal(user, amount, payment_method):
        """
        Process a withdrawal from user's wallet.
        """
        wallet = PaymentService._get_or_create_wallet(user, Wallet.WalletType.DRIVER)
        settings = PaymentSettings.get_current_settings()
        
        # Check minimum withdrawal amount
        if amount < settings.minimum_withdrawal_amount:
            return False, f"Minimum withdrawal amount is {settings.minimum_withdrawal_amount}"
        
        # Check if user has sufficient balance
        total_amount = amount + settings.withdrawal_fee
        if not wallet.can_withdraw(total_amount):
            return False, "Insufficient balance"
        
        with transaction.atomic():
            # Create withdrawal payment
            payment = Payment.objects.create(
                payer=user,
                payment_type=Payment.PaymentType.WITHDRAWAL,
                amount=amount,
                gross_amount=amount,
                platform_fee=settings.withdrawal_fee,
                payment_method=payment_method,
                description="Wallet withdrawal",
                provider=payment_method.provider
            )
            
            # Deduct from wallet
            wallet.deduct_funds(total_amount, f"Withdrawal {payment.payment_id}")
            
            # Process withdrawal via provider
            success, message = PaymentService._process_withdrawal_via_provider(payment)
            
            if success:
                payment.mark_as_completed()
            else:
                # Refund to wallet if withdrawal fails
                wallet.add_funds(total_amount, f"Refund for failed withdrawal {payment.payment_id}")
                payment.mark_as_failed(message)
            
            return success, message
    
    @staticmethod
    def create_refund(payment, amount, reason, requested_by):
        """
        Create a refund for a payment.
        """
        from apps.payments.models import Refund
        
        # Validate refund amount
        if amount > payment.amount:
            return None, "Refund amount cannot exceed payment amount"
        
        # Check if payment can be refunded
        if payment.status != Payment.Status.COMPLETED:
            return None, "Payment must be completed to create refund"
        
        # Determine refund type
        refund_type = Refund.RefundType.FULL if amount == payment.amount else Refund.RefundType.PARTIAL
        
        refund = Refund.objects.create(
            payment=payment,
            refund_type=refund_type,
            amount=amount,
            reason=reason,
            requested_by=requested_by,
            description=f"Refund for payment {payment.payment_id}"
        )
        
        return refund, "Refund created successfully"
    
    @staticmethod
    def process_refund(refund):
        """
        Process a refund.
        """
        if not refund.can_refund():
            return False, "Refund cannot be processed"
        
        try:
            with transaction.atomic():
                # Update refund status
                refund.status = refund.Status.PROCESSING
                refund.processed_at = timezone.now()
                refund.save()
                
                # Process refund via payment provider
                if refund.payment.payment_method:
                    success, message = PaymentService._process_refund_via_provider(refund)
                else:
                    # Cash refund - add to rider wallet
                    rider_wallet = PaymentService._get_or_create_wallet(
                        refund.payment.payer,
                        Wallet.WalletType.RIDER
                    )
                    rider_wallet.add_funds(refund.amount, f"Refund {refund.refund_id}")
                    success, message = True, "Cash refund processed"
                
                if success:
                    refund.mark_as_completed()
                    
                    # Update original payment status
                    if refund.refund_type == refund.RefundType.FULL:
                        refund.payment.status = Payment.Status.REFUNDED
                    else:
                        refund.payment.status = Payment.Status.PARTIALLY_REFUNDED
                    refund.payment.save()
                
                return success, message
        
        except Exception as e:
            refund.status = refund.Status.FAILED
            refund.save()
            return False, str(e)
    
    @staticmethod
    def get_user_payment_methods(user):
        """
        Get user's payment methods.
        """
        return PaymentMethod.objects.filter(user=user, is_active=True)
    
    @staticmethod
    def add_payment_method(user, method_data):
        """
        Add a new payment method for user.
        """
        # Validate and create payment method based on type
        method_type = method_data.get('method_type')
        
        if method_type == PaymentMethod.MethodType.CARD:
            return PaymentService._add_card_payment_method(user, method_data)
        elif method_type == PaymentMethod.MethodType.MOBILE_MONEY:
            return PaymentService._add_mobile_money_method(user, method_data)
        elif method_type == PaymentMethod.MethodType.BANK_ACCOUNT:
            return PaymentService._add_bank_account_method(user, method_data)
        else:
            return None, "Unsupported payment method type"
    
    @staticmethod
    def get_payment_history(user, limit=50, offset=0):
        """
        Get payment history for user.
        """
        payments = Payment.objects.filter(
            models.Q(payer=user) | models.Q(payee=user),
            is_deleted=False
        ).order_by('-created_at')[offset:offset + limit]
        
        return payments
    
    @staticmethod
    def get_wallet_balance(user):
        """
        Get user's wallet balance.
        """
        try:
            if hasattr(user, 'driver_profile'):
                wallet = user.wallet
                return wallet.balance, wallet.pending_balance
            else:
                # Rider wallet
                wallet = PaymentService._get_or_create_wallet(user, Wallet.WalletType.RIDER)
                return wallet.balance, wallet.pending_balance
        except Wallet.DoesNotExist:
            return Decimal('0.00'), Decimal('0.00')
    
    # Private helper methods
    @staticmethod
    def _calculate_platform_fee(amount, settings):
        """Calculate platform fee."""
        fee = amount * (settings.platform_fee_percentage / 100)
        return max(settings.minimum_platform_fee, min(fee, settings.maximum_platform_fee))
    
    @staticmethod
    def _calculate_processing_fee(amount, payment_method, settings):
        """Calculate payment processing fee."""
        if not payment_method or payment_method.method_type == PaymentMethod.MethodType.CASH:
            return Decimal('0.00')
        
        if payment_method.method_type == PaymentMethod.MethodType.CARD:
            return (amount * (settings.card_processing_fee_percentage / 100)) + settings.card_processing_fee_fixed
        
        return Decimal('0.00')  # No fee for other methods
    
    @staticmethod
    def _get_or_create_wallet(user, wallet_type):
        """Get or create wallet for user."""
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'wallet_type': wallet_type}
        )
        return wallet
    
    @staticmethod
    def _process_cash_payment(payment):
        """Process cash payment."""
        # Cash payments are automatically completed
        PaymentService.complete_payment(payment)
        return True, "Cash payment processed"
    
    @staticmethod
    def _create_payment_transactions(payment):
        """Create transaction records for payment."""
        # Create transaction for payer (if applicable)
        if payment.payment_type == Payment.PaymentType.WALLET_TOPUP:
            payer_wallet = PaymentService._get_or_create_wallet(
                payment.payer,
                Wallet.WalletType.RIDER
            )
            Transaction.objects.create(
                wallet=payer_wallet,
                transaction_type=Transaction.TransactionType.CREDIT,
                amount=payment.net_amount,
                description=f"Wallet top-up {payment.payment_id}",
                payment=payment,
                status=Transaction.Status.COMPLETED
            )
    
    @staticmethod
    def _send_payment_notifications(payment):
        """Send payment notifications."""
        from apps.notifications.services.notification_service import NotificationService
        
        # Send notification to payer
        NotificationService.send_payment_notification(
            payment,
            'payment_received' if payment.status == Payment.Status.COMPLETED else 'payment_failed'
        )
    
    @staticmethod
    def _process_withdrawal_via_provider(payment):
        """Process withdrawal via payment provider."""
        # Implement provider-specific withdrawal logic
        return True, "Withdrawal processed successfully"
    
    @staticmethod
    def _process_refund_via_provider(refund):
        """Process refund via payment provider."""
        # Implement provider-specific refund logic
        return True, "Refund processed successfully"
    
    @staticmethod
    def _add_card_payment_method(user, method_data):
        """Add card payment method."""
        # Implement card tokenization via Stripe
        return None, "Card payment method not implemented"
    
    @staticmethod
    def _add_mobile_money_method(user, method_data):
        """Add mobile money payment method."""
        payment_method = PaymentMethod.objects.create(
            user=user,
            method_type=PaymentMethod.MethodType.MOBILE_MONEY,
            provider=method_data.get('provider', PaymentMethod.Provider.MPESA),
            display_name=f"{method_data.get('provider', 'Mobile Money')} - {method_data.get('phone_number', '')[-4:]}",
            phone_number=method_data.get('phone_number'),
            is_verified=False
        )
        
        return payment_method, "Mobile money method added successfully"
    
    @staticmethod
    def _add_bank_account_method(user, method_data):
        """Add bank account payment method."""
        payment_method = PaymentMethod.objects.create(
            user=user,
            method_type=PaymentMethod.MethodType.BANK_ACCOUNT,
            provider=PaymentMethod.Provider.BANK_TRANSFER,
            display_name=f"{method_data.get('bank_name', 'Bank')} - {method_data.get('account_number', '')[-4:]}",
            bank_name=method_data.get('bank_name'),
            account_type=method_data.get('account_type'),
            is_verified=False
        )
        
        return payment_method, "Bank account method added successfully"
