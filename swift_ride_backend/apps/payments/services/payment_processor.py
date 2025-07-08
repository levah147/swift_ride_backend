"""
Payment processor service.
"""

from typing import Dict, Any, Tuple, Optional
from decimal import Decimal

from django.conf import settings

from apps.payments.models import Payment, PaymentMethod, Refund
from apps.payments.providers import (
    StripeProvider, PaystackProvider, FlutterwaveProvider,
    MpesaProvider, BankTransferProvider, CashPaymentProvider
)


class PaymentProcessor:
    """
    Central payment processor that routes payments to appropriate providers.
    """
    
    def __init__(self):
        self.providers = {
            PaymentMethod.Provider.STRIPE: StripeProvider(),
            PaymentMethod.Provider.PAYSTACK: PaystackProvider(),
            PaymentMethod.Provider.FLUTTERWAVE: FlutterwaveProvider(),
            PaymentMethod.Provider.MPESA: MpesaProvider(),
            PaymentMethod.Provider.BANK_TRANSFER: BankTransferProvider(),
            PaymentMethod.Provider.CASH: CashPaymentProvider()
        }
    
    def get_provider(self, provider_name: str):
        """
        Get payment provider instance.
        """
        return self.providers.get(provider_name)
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process payment using appropriate provider.
        """
        try:
            # Determine provider based on payment method
            if payment.payment_method:
                provider = self.get_provider(payment.payment_method.provider)
            else:
                # Default to cash for payments without payment method
                provider = self.get_provider(PaymentMethod.Provider.CASH)
            
            if not provider:
                return False, "Payment provider not available"
            
            if not provider.is_available():
                return False, "Payment provider is not properly configured"
            
            # Validate currency support
            if payment.currency not in provider.get_supported_currencies():
                return False, f"Currency {payment.currency} not supported by provider"
            
            # Process payment
            return provider.process_payment(payment)
        
        except Exception as e:
            return False, f"Payment processing error: {str(e)}"
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process refund using appropriate provider.
        """
        try:
            # Get provider from original payment
            if refund.payment.payment_method:
                provider = self.get_provider(refund.payment.payment_method.provider)
            else:
                provider = self.get_provider(PaymentMethod.Provider.CASH)
            
            if not provider:
                return False, "Refund provider not available"
            
            if not provider.is_available():
                return False, "Refund provider is not properly configured"
            
            # Process refund
            return provider.process_refund(refund)
        
        except Exception as e:
            return False, f"Refund processing error: {str(e)}"
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create payment method using appropriate provider.
        """
        try:
            provider_name = method_data.get('provider')
            if not provider_name:
                return None, "Provider is required"
            
            provider = self.get_provider(provider_name)
            if not provider:
                return None, f"Provider {provider_name} not available"
            
            if not provider.is_available():
                return None, f"Provider {provider_name} is not properly configured"
            
            # Validate method type support
            method_type = method_data.get('method_type')
            if method_type not in provider.get_supported_payment_methods():
                return None, f"Payment method {method_type} not supported by {provider_name}"
            
            # Create payment method
            return provider.create_payment_method(user, method_data)
        
        except Exception as e:
            return None, f"Payment method creation error: {str(e)}"
    
    def verify_payment(self, payment: Payment) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify payment with provider.
        """
        try:
            if payment.payment_method:
                provider = self.get_provider(payment.payment_method.provider)
            else:
                provider = self.get_provider(PaymentMethod.Provider.CASH)
            
            if not provider:
                return False, {'error': 'Payment provider not available'}
            
            if not payment.provider_transaction_id:
                return False, {'error': 'No provider transaction ID found'}
            
            return provider.verify_payment(payment.provider_transaction_id)
        
        except Exception as e:
            return False, {'error': f"Payment verification error: {str(e)}"}
    
    def handle_webhook(self, provider_name: str, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle webhook from payment provider.
        """
        try:
            provider = self.get_provider(provider_name)
            if not provider:
                return False, f"Provider {provider_name} not available"
            
            return provider.handle_webhook(payload, signature)
        
        except Exception as e:
            return False, f"Webhook processing error: {str(e)}"
    
    def calculate_fees(self, amount: Decimal, currency: str, provider_name: str) -> Dict[str, Decimal]:
        """
        Calculate fees for payment provider.
        """
        try:
            provider = self.get_provider(provider_name)
            if not provider:
                return {'error': 'Provider not available'}
            
            return provider.calculate_fees(amount, currency)
        
        except Exception as e:
            return {'error': f"Fee calculation error: {str(e)}"}
    
    def get_supported_providers(self) -> Dict[str, Dict[str, Any]]:
        """
        Get list of supported payment providers and their capabilities.
        """
        providers_info = {}
        
        for provider_name, provider in self.providers.items():
            if provider.is_available():
                providers_info[provider_name] = {
                    'name': provider.get_provider_name(),
                    'supported_currencies': provider.get_supported_currencies(),
                    'supported_payment_methods': provider.get_supported_payment_methods(),
                    'is_available': True
                }
            else:
                providers_info[provider_name] = {
                    'name': provider.get_provider_name(),
                    'is_available': False,
                    'reason': 'Provider not properly configured'
                }
        
        return providers_info
    
    def get_best_provider(self, currency: str, method_type: str, amount: Decimal = None) -> Optional[str]:
        """
        Get the best payment provider for given criteria.
        """
        suitable_providers = []
        
        for provider_name, provider in self.providers.items():
            if (provider.is_available() and 
                currency in provider.get_supported_currencies() and 
                method_type in provider.get_supported_payment_methods()):
                
                # Calculate fees for comparison
                fees = provider.calculate_fees(amount or Decimal('100.00'), currency)
                total_fee = fees.get('total_fee', Decimal('999.99'))
                
                suitable_providers.append({
                    'provider': provider_name,
                    'fee': total_fee
                })
        
        if not suitable_providers:
            return None
        
        # Return provider with lowest fees
        best_provider = min(suitable_providers, key=lambda x: x['fee'])
        return best_provider['provider']
    
    def validate_payment_data(self, payment_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate payment data before processing.
        """
        required_fields = ['amount', 'currency', 'payer_id']
        
        for field in required_fields:
            if field not in payment_data:
                return False, f"Missing required field: {field}"
        
        # Validate amount
        try:
            amount = Decimal(str(payment_data['amount']))
            if amount <= 0:
                return False, "Amount must be greater than zero"
        except (ValueError, TypeError):
            return False, "Invalid amount format"
        
        # Validate currency
        currency = payment_data.get('currency', '').upper()
        if len(currency) != 3:
            return False, "Invalid currency code"
        
        return True, "Payment data is valid"
    
    def get_payment_status(self, payment: Payment) -> Dict[str, Any]:
        """
        Get comprehensive payment status information.
        """
        status_info = {
            'payment_id': str(payment.payment_id),
            'status': payment.status,
            'amount': payment.amount,
            'currency': payment.currency,
            'created_at': payment.created_at,
            'updated_at': payment.updated_at
        }
        
        if payment.payment_method:
            status_info['payment_method'] = {
                'type': payment.payment_method.method_type,
                'provider': payment.payment_method.provider,
                'display_name': payment.payment_method.display_name
            }
        
        if payment.provider_transaction_id:
            status_info['provider_transaction_id'] = payment.provider_transaction_id
        
        if payment.status == Payment.Status.COMPLETED:
            status_info['completed_at'] = payment.completed_at
            status_info['provider_fee'] = payment.provider_fee
            status_info['platform_fee'] = payment.platform_fee
        
        if payment.status == Payment.Status.FAILED:
            status_info['failure_reason'] = payment.failure_reason
            status_info['failed_at'] = payment.failed_at
        
        return status_info
