"""
Cash payment provider.
"""

from decimal import Decimal
from typing import Dict, Any, Tuple, Optional
from datetime import datetime

from django.utils import timezone

from .base import BasePaymentProvider
from apps.payments.models import Payment, PaymentMethod, Refund


class CashPaymentProvider(BasePaymentProvider):
    """
    Cash payment provider implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'max_amount': Decimal('200.00'),  # Maximum cash payment amount
            'require_confirmation': True,
            'auto_complete': False
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(default_config)
    
    def get_required_config_keys(self) -> list:
        return []  # No required config for cash payments
    
    def get_supported_currencies(self) -> list:
        return ['USD', 'KES', 'UGX', 'TZS', 'NGN', 'GHS']
    
    def get_supported_payment_methods(self) -> list:
        return ['cash']
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process cash payment.
        """
        try:
            # Validate cash payment amount
            max_amount = self.config.get('max_amount', Decimal('200.00'))
            if payment.amount > max_amount:
                payment.mark_as_failed(f"Cash payment amount exceeds maximum of {max_amount}")
                return False, f"Cash payment amount exceeds maximum of {max_amount}"
            
            # Generate cash payment reference
            payment.provider_transaction_id = f"CASH_{payment.payment_id}_{int(timezone.now().timestamp())}"
            
            # Update payment metadata
            payment.metadata.update({
                'payment_method': 'cash',
                'requires_confirmation': self.config.get('require_confirmation', True),
                'max_amount': str(max_amount),
                'initiated_at': timezone.now().isoformat()
            })
            
            # Set payment status based on configuration
            if self.config.get('auto_complete', False):
                payment.status = Payment.Status.COMPLETED
                payment.completed_at = timezone.now()
            else:
                payment.status = Payment.Status.PENDING
            
            payment.save()
            
            self.log_transaction('cash_payment_initiated', {
                'payment_id': str(payment.payment_id),
                'amount': str(payment.amount),
                'currency': payment.currency
            })
            
            if payment.status == Payment.Status.COMPLETED:
                return True, "Cash payment completed automatically"
            else:
                return True, "Cash payment initiated - awaiting confirmation"
        
        except Exception as e:
            error_message = self.handle_error(e, "Cash payment processing")
            payment.mark_as_failed(error_message)
            return False, error_message
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process cash refund.
        """
        try:
            # Cash refunds are typically handled manually
            refund.provider_refund_id = f"CASH_REFUND_{refund.refund_id}_{int(timezone.now().timestamp())}"
            refund.metadata = {
                'refund_method': 'cash',
                'requires_manual_processing': True,
                'initiated_at': timezone.now().isoformat(),
                'instructions': 'Cash refund to be processed manually by driver/agent'
            }
            refund.save()
            
            self.log_transaction('cash_refund_initiated', {
                'refund_id': str(refund.refund_id),
                'amount': str(refund.amount),
                'original_payment_id': str(refund.payment.payment_id)
            })
            
            return True, "Cash refund initiated - requires manual processing"
        
        except Exception as e:
            return False, self.handle_error(e, "Cash refund processing")
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create cash payment method.
        """
        try:
            # Cash payment method is simple - no external validation needed
            payment_method = PaymentMethod.objects.create(
                user=user,
                method_type=PaymentMethod.MethodType.CASH,
                provider=PaymentMethod.Provider.CASH,
                display_name="Cash Payment",
                is_verified=True,  # Cash is always "verified"
                metadata={
                    'max_amount': str(self.config.get('max_amount', Decimal('200.00'))),
                    'created_at': timezone.now().isoformat()
                }
            )
            
            return payment_method, "Cash payment method created successfully"
        
        except Exception as e:
            return None, self.handle_error(e, "Cash payment method creation")
    
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify cash payment.
        """
        try:
            # Cash payments are verified manually or through driver confirmation
            return True, {
                'status': 'requires_manual_verification',
                'transaction_id': provider_transaction_id,
                'verification_method': 'manual',
                'message': 'Cash payment requires manual verification by driver or agent'
            }
        
        except Exception as e:
            return False, {'error': self.handle_error(e, "Cash payment verification")}
    
    def handle_webhook(self, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle cash payment confirmation webhook.
        """
        try:
            # Cash payment confirmations might come from driver app or admin system
            payment_id = payload.get('payment_id')
            action = payload.get('action')  # 'confirm' or 'reject'
            confirmed_by = payload.get('confirmed_by')  # driver_id or admin_id
            amount_received = payload.get('amount_received')
            
            if not payment_id or not action:
                return False, "Invalid webhook: missing required fields"
            
            try:
                payment = Payment.objects.get(payment_id=payment_id)
                
                if action == 'confirm':
                    # Cash payment confirmed
                    payment.metadata.update({
                        'confirmed_by': confirmed_by,
                        'amount_received': amount_received,
                        'confirmed_at': timezone.now().isoformat(),
                        'confirmation_method': 'webhook'
                    })
                    payment.save()
                    
                    # Complete payment
                    from apps.payments.services.payment_service import PaymentService
                    PaymentService.complete_payment(payment)
                    
                    self.log_transaction('cash_payment_confirmed', {
                        'payment_id': str(payment.payment_id),
                        'confirmed_by': confirmed_by,
                        'amount_received': amount_received
                    })
                
                elif action == 'reject':
                    # Cash payment rejected
                    reason = payload.get('reason', 'Payment rejected')
                    payment.mark_as_failed(f"Cash payment rejected: {reason}")
                    
                    self.log_transaction('cash_payment_rejected', {
                        'payment_id': str(payment.payment_id),
                        'rejected_by': confirmed_by,
                        'reason': reason
                    })
            
            except Payment.DoesNotExist:
                return False, f"Payment not found: {payment_id}"
            
            return True, f"Cash payment {action} processed"
        
        except Exception as e:
            return False, self.handle_error(e, "Cash payment webhook processing")
    
    def calculate_fees(self, amount: Decimal, currency: str = 'USD') -> Dict[str, Decimal]:
        """
        Calculate cash payment fees (typically none).
        """
        return {
            'processing_fee': Decimal('0.00'),
            'fixed_fee': Decimal('0.00'),
            'total_fee': Decimal('0.00')
        }
    
    def confirm_payment(self, payment: Payment, confirmed_by: str, amount_received: Decimal = None) -> Tuple[bool, str]:
        """
        Manually confirm cash payment.
        """
        try:
            if payment.status != Payment.Status.PENDING:
                return False, f"Payment is not in pending status: {payment.status}"
            
            # Validate amount if provided
            if amount_received and amount_received != payment.amount:
                return False, f"Amount received ({amount_received}) does not match payment amount ({payment.amount})"
            
            # Update payment with confirmation details
            payment.metadata.update({
                'confirmed_by': confirmed_by,
                'amount_received': str(amount_received or payment.amount),
                'confirmed_at': timezone.now().isoformat(),
                'confirmation_method': 'manual'
            })
            payment.save()
            
            # Complete payment
            from apps.payments.services.payment_service import PaymentService
            PaymentService.complete_payment(payment)
            
            self.log_transaction('cash_payment_manually_confirmed', {
                'payment_id': str(payment.payment_id),
                'confirmed_by': confirmed_by,
                'amount_received': str(amount_received or payment.amount)
            })
            
            return True, "Cash payment confirmed successfully"
        
        except Exception as e:
            return False, self.handle_error(e, "Cash payment confirmation")
    
    def reject_payment(self, payment: Payment, rejected_by: str, reason: str = None) -> Tuple[bool, str]:
        """
        Manually reject cash payment.
        """
        try:
            if payment.status not in [Payment.Status.PENDING, Payment.Status.PROCESSING]:
                return False, f"Payment cannot be rejected in current status: {payment.status}"
            
            # Mark payment as failed with rejection details
            rejection_reason = f"Cash payment rejected by {rejected_by}"
            if reason:
                rejection_reason += f": {reason}"
            
            payment.mark_as_failed(rejection_reason)
            payment.metadata.update({
                'rejected_by': rejected_by,
                'rejection_reason': reason,
                '
_at': timezone.now().isoformat()
            })
            payment.save()
            
            self.log_transaction('cash_payment_manually_rejected', {
                'payment_id': str(payment.payment_id),
                'rejected_by': rejected_by,
                'reason': reason
            })
            
            return True, "Cash payment rejected successfully"
        
        except Exception as e:
            return False, self.handle_error(e, "Cash payment rejection")
    
    def get_payment_instructions(self, payment: Payment) -> Dict[str, Any]:
        """
        Get cash payment instructions.
        """
        return {
            'payment_method': 'Cash',
            'amount': str(payment.amount),
            'currency': payment.currency,
            'reference': str(payment.payment_id),
            'instructions': [
                f"Pay {payment.amount} {payment.currency} in cash to the driver",
                f"Payment reference: {payment.payment_id}",
                "Ensure you receive a receipt or confirmation",
                "Payment will be confirmed by the driver"
            ],
            'max_amount': str(self.config.get('max_amount', Decimal('200.00'))),
            'requires_confirmation': self.config.get('require_confirmation', True)
        }
