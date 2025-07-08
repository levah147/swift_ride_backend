"""
Bank transfer payment provider.
"""

from decimal import Decimal
from typing import Dict, Any, Tuple, Optional

from .base import BasePaymentProvider
from apps.payments.models import Payment, PaymentMethod, Refund


class BankTransferProvider(BasePaymentProvider):
    """
    Bank transfer payment provider implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'bank_name': 'Swift Ride Bank',
            'account_number': '1234567890',
            'routing_number': '123456789',
            'swift_code': 'SWIFTXXX'
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(default_config)
    
    def get_required_config_keys(self) -> list:
        return ['bank_name', 'account_number']
    
    def get_supported_currencies(self) -> list:
        return ['USD', 'KES', 'UGX', 'TZS', 'NGN', 'GHS']
    
    def get_supported_payment_methods(self) -> list:
        return ['bank_account']
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process bank transfer payment.
        """
        try:
            # Bank transfers are typically manual processes
            # This would integrate with banking APIs in a real implementation
            
            # Generate bank transfer instructions
            transfer_instructions = {
                'bank_name': self.config['bank_name'],
                'account_number': self.config['account_number'],
                'routing_number': self.config.get('routing_number'),
                'swift_code': self.config.get('swift_code'),
                'reference': str(payment.payment_id),
                'amount': str(payment.amount),
                'currency': payment.currency,
                'beneficiary': 'Swift Ride Ltd',
                'purpose': payment.description or f'Payment for {payment.payment_type}'
            }
            
            # Update payment with transfer instructions
            payment.provider_transaction_id = f"BT_{payment.payment_id}"
            payment.metadata.update({
                'transfer_instructions': transfer_instructions,
                'payment_method': 'bank_transfer',
                'status': 'awaiting_transfer'
            })
            payment.status = Payment.Status.PENDING
            payment.save()
            
            self.log_transaction('bank_transfer_initiated', {
                'payment_id': str(payment.payment_id),
                'reference': str(payment.payment_id)
            })
            
            return True, "Bank transfer instructions generated"
        
        except Exception as e:
            error_message = self.handle_error(e, "Bank transfer processing")
            payment.mark_as_failed(error_message)
            return False, error_message
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process bank transfer refund.
        """
        try:
            # Get original payment method details for refund
            original_payment = refund.payment
            
            if not original_payment.payment_method:
                return False, "Original payment method not found for refund"
            
            # Generate refund transfer instructions
            refund_instructions = {
                'bank_name': original_payment.payment_method.bank_name,
                'account_number': original_payment.payment_method.provider_payment_method_id,
                'account_holder': original_payment.payer.get_full_name(),
                'amount': str(refund.amount),
                'currency': original_payment.currency,
                'reference': f"REFUND_{refund.refund_id}",
                'description': refund.description or f"Refund for payment {original_payment.payment_id}"
            }
            
            refund.provider_refund_id = f"BTR_{refund.refund_id}"
            refund.metadata = {
                'refund_instructions': refund_instructions,
                'refund_method': 'bank_transfer'
            }
            refund.save()
            
            self.log_transaction('bank_transfer_refund_initiated', {
                'refund_id': str(refund.refund_id),
                'original_payment_id': str(original_payment.payment_id)
            })
            
            return True, "Bank transfer refund instructions generated"
        
        except Exception as e:
            return False, self.handle_error(e, "Bank transfer refund processing")
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create bank account payment method.
        """
        try:
            required_fields = ['bank_name', 'account_number', 'account_holder_name']
            
            for field in required_fields:
                if not method_data.get(field):
                    return None, f"{field} is required"
            
            payment_method = PaymentMethod.objects.create(
                user=user,
                method_type=PaymentMethod.MethodType.BANK_ACCOUNT,
                provider=PaymentMethod.Provider.BANK_TRANSFER,
                display_name=f"{method_data['bank_name']} - {method_data['account_number'][-4:]}",
                last_four=method_data['account_number'][-4:],
                bank_name=method_data['bank_name'],
                provider_payment_method_id=method_data['account_number'],
                metadata={
                    'account_holder_name': method_data['account_holder_name'],
                    'routing_number': method_data.get('routing_number'),
                    'swift_code': method_data.get('swift_code'),
                    'branch_code': method_data.get('branch_code')
                },
                is_verified=False  # Bank accounts typically need verification
            )
            
            return payment_method, "Bank account payment method created (verification required)"
        
        except Exception as e:
            return None, self.handle_error(e, "Bank account payment method creation")
    
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify bank transfer payment.
        """
        try:
            # In a real implementation, this would check with banking APIs
            # For now, we'll return a placeholder response
            
            return True, {
                'status': 'pending_verification',
                'transaction_id': provider_transaction_id,
                'verification_method': 'manual',
                'message': 'Bank transfer requires manual verification'
            }
        
        except Exception as e:
            return False, {'error': self.handle_error(e, "Bank transfer verification")}
    
    def handle_webhook(self, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle bank transfer webhook/notification.
        """
        try:
            # Bank transfer webhooks would come from banking partners
            # This is a placeholder implementation
            
            transaction_id = payload.get('transaction_id')
            status = payload.get('status')
            amount = payload.get('amount')
            reference = payload.get('reference')
            
            if not transaction_id or not reference:
                return False, "Invalid webhook: missing required fields"
            
            try:
                payment = Payment.objects.get(payment_id=reference)
                
                if status == 'completed':
                    # Bank transfer completed
                    payment.metadata.update({
                        'bank_transaction_id': transaction_id,
                        'verified_amount': amount,
                        'verification_date': payload.get('transaction_date')
                    })
                    payment.save()
                    
                    # Complete payment
                    from apps.payments.services.payment_service import PaymentService
                    PaymentService.complete_payment(payment)
                    
                    self.log_transaction('bank_transfer_completed', {
                        'payment_id': str(payment.payment_id),
                        'bank_transaction_id': transaction_id
                    })
                
                elif status == 'failed':
                    # Bank transfer failed
                    payment.mark_as_failed(f"Bank transfer failed: {payload.get('reason', 'Unknown error')}")
                    
                    self.log_transaction('bank_transfer_failed', {
                        'payment_id': str(payment.payment_id),
                        'reason': payload.get('reason')
                    })
            
            except Payment.DoesNotExist:
                return False, f"Payment not found: {reference}"
            
            return True, f"Bank transfer webhook processed: {status}"
        
        except Exception as e:
            return False, self.handle_error(e, "Bank transfer webhook processing")
    
    def calculate_fees(self, amount: Decimal, currency: str = 'USD') -> Dict[str, Decimal]:
        """
        Calculate bank transfer fees.
        """
        # Bank transfer fees are typically fixed
        if currency == 'USD':
            fee = Decimal('25.00')  # $25 for international transfers
        else:
            # Local transfers
            fee = Decimal('5.00')  # Equivalent local currency
        
        return {
            'processing_fee': fee,
            'fixed_fee': Decimal('0.00'),
            'total_fee': fee
        }
    
    def get_transfer_instructions(self, payment: Payment) -> Dict[str, Any]:
        """
        Get bank transfer instructions for a payment.
        """
        return {
            'bank_name': self.config['bank_name'],
            'account_number': self.config['account_number'],
            'routing_number': self.config.get('routing_number'),
            'swift_code': self.config.get('swift_code'),
            'beneficiary_name': 'Swift Ride Ltd',
            'reference': str(payment.payment_id),
            'amount': str(payment.amount),
            'currency': payment.currency,
            'purpose': payment.description or f'Payment for {payment.payment_type}',
            'instructions': [
                f"Transfer {payment.amount} {payment.currency} to the above account",
                f"Use reference: {payment.payment_id}",
                "Include your name and phone number in the transfer description",
                "Payment will be processed within 1-3 business days after verification"
            ]
        }
