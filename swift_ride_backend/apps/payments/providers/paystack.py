"""
Paystack payment provider.
"""

import requests
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional

from django.conf import settings

from .base import BasePaymentProvider
from apps.payments.models import Payment, PaymentMethod, Refund


class PaystackProvider(BasePaymentProvider):
    """
    Paystack payment provider implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'secret_key': getattr(settings, 'PAYSTACK_SECRET_KEY', ''),
            'public_key': getattr(settings, 'PAYSTACK_PUBLIC_KEY', ''),
            'base_url': 'https://api.paystack.co'
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(default_config)
    
    def get_required_config_keys(self) -> list:
        return ['secret_key', 'public_key', 'base_url']
    
    def get_supported_currencies(self) -> list:
        return ['NGN', 'USD', 'GHS', 'ZAR', 'KES']
    
    def get_supported_payment_methods(self) -> list:
        return ['card', 'bank_account', 'mobile_money']
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process payment via Paystack.
        """
        try:
            headers = {
                'Authorization': f"Bearer {self.config['secret_key']}",
                'Content-Type': 'application/json'
            }
            
            # Convert amount to kobo (for NGN) or cents
            amount = self.format_amount(payment.amount, payment.currency)
            
            payload = {
                'email': payment.payer.email,
                'amount': amount,
                'currency': payment.currency,
                'reference': str(payment.payment_id),
                'callback_url': f"{settings.BACKEND_URL}/api/payments/webhooks/paystack/callback/",
                'metadata': {
                    'payment_id': str(payment.payment_id),
                    'user_id': str(payment.payer.id),
                    'payment_type': payment.payment_type
                }
            }
            
            # Add payment method specific data
            if payment.payment_method:
                if payment.payment_method.method_type == PaymentMethod.MethodType.CARD:
                    payload['authorization_code'] = payment.payment_method.provider_payment_method_id
                elif payment.payment_method.method_type == PaymentMethod.MethodType.BANK_ACCOUNT:
                    payload['bank'] = {
                        'code': payment.payment_method.provider_payment_method_id,
                        'account_number': payment.payment_method.last_four
                    }
            
            response = requests.post(
                f"{self.config['base_url']}/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status'):
                    # Update payment with Paystack data
                    payment.provider_transaction_id = result['data']['reference']
                    payment.metadata.update({
                        'paystack_access_code': result['data']['access_code'],
                        'authorization_url': result['data']['authorization_url']
                    })
                    payment.status = Payment.Status.PROCESSING
                    payment.save()
                    
                    self.log_transaction('payment_initialized', {
                        'payment_id': str(payment.payment_id),
                        'reference': result['data']['reference']
                    })
                    
                    return True, "Payment initialized successfully"
                else:
                    error_message = result.get('message', 'Payment initialization failed')
                    payment.mark_as_failed(f"Paystack error: {error_message}")
                    return False, error_message
            else:
                error_message = f"Paystack API error: {response.status_code}"
                payment.mark_as_failed(error_message)
                return False, error_message
        
        except Exception as e:
            error_message = self.handle_error(e, "Payment processing")
            payment.mark_as_failed(error_message)
            return False, error_message
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process refund via Paystack.
        """
        try:
            headers = {
                'Authorization': f"Bearer {self.config['secret_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'transaction': refund.payment.provider_transaction_id,
                'amount': self.format_amount(refund.amount, refund.payment.currency),
                'currency': refund.payment.currency,
                'customer_note': refund.description or f"Refund for {refund.payment.payment_id}",
                'merchant_note': f"Refund requested by {refund.requested_by.get_full_name()}"
            }
            
            response = requests.post(
                f"{self.config['base_url']}/refund",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status'):
                    refund.provider_refund_id = result['data']['id']
                    refund.save()
                    
                    self.log_transaction('refund_processed', {
                        'refund_id': str(refund.refund_id),
                        'paystack_refund_id': result['data']['id']
                    })
                    
                    return True, "Refund processed successfully"
                else:
                    error_message = result.get('message', 'Refund processing failed')
                    return False, error_message
            else:
                return False, f"Paystack API error: {response.status_code}"
        
        except Exception as e:
            return False, self.handle_error(e, "Refund processing")
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create payment method via Paystack.
        """
        try:
            method_type = method_data.get('method_type')
            
            if method_type == PaymentMethod.MethodType.CARD:
                # For cards, we typically get authorization code after successful payment
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    method_type=PaymentMethod.MethodType.CARD,
                    provider=PaymentMethod.Provider.PAYSTACK,
                    display_name=f"Card ending in {method_data.get('last4', '****')}",
                    last_four=method_data.get('last4'),
                    card_brand=method_data.get('card_type'),
                    card_exp_month=method_data.get('exp_month'),
                    card_exp_year=method_data.get('exp_year'),
                    provider_payment_method_id=method_data.get('authorization_code'),
                    is_verified=True
                )
                
                return payment_method, "Card payment method created successfully"
            
            elif method_type == PaymentMethod.MethodType.BANK_ACCOUNT:
                # Verify bank account
                bank_code = method_data.get('bank_code')
                account_number = method_data.get('account_number')
                
                if not bank_code or not account_number:
                    return None, "Bank code and account number are required"
                
                # Verify account with Paystack
                headers = {
                    'Authorization': f"Bearer {self.config['secret_key']}",
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(
                    f"{self.config['base_url']}/bank/resolve",
                    params={
                        'account_number': account_number,
                        'bank_code': bank_code
                    },
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    if result.get('status'):
                        account_data = result['data']
                        
                        payment_method = PaymentMethod.objects.create(
                            user=user,
                            method_type=PaymentMethod.MethodType.BANK_ACCOUNT,
                            provider=PaymentMethod.Provider.PAYSTACK,
                            display_name=f"{method_data.get('bank_name', 'Bank')} - {account_number[-4:]}",
                            last_four=account_number[-4:],
                            bank_name=method_data.get('bank_name'),
                            provider_payment_method_id=bank_code,
                            is_verified=True
                        )
                        
                        return payment_method, "Bank account verified and added successfully"
                    else:
                        return None, result.get('message', 'Account verification failed')
                else:
                    return None, "Failed to verify bank account"
            
            else:
                return None, f"Unsupported payment method type: {method_type}"
        
        except Exception as e:
            return None, self.handle_error(e, "Payment method creation")
    
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify payment with Paystack.
        """
        try:
            headers = {
                'Authorization': f"Bearer {self.config['secret_key']}",
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.config['base_url']}/transaction/verify/{provider_transaction_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status'):
                    transaction_data = result['data']
                    
                    return True, {
                        'status': transaction_data['status'],
                        'amount': self.parse_amount(transaction_data['amount'], transaction_data['currency']),
                        'currency': transaction_data['currency'],
                        'reference': transaction_data['reference'],
                        'paid_at': transaction_data.get('paid_at'),
                        'fees': self.parse_amount(transaction_data.get('fees', 0), transaction_data['currency']),
                        'authorization': transaction_data.get('authorization', {})
                    }
                else:
                    return False, {'error': result.get('message', 'Verification failed')}
            else:
                return False, {'error': f"API error: {response.status_code}"}
        
        except Exception as e:
            return False, {'error': self.handle_error(e, "Payment verification")}
    
    def handle_webhook(self, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle Paystack webhook.
        """
        try:
            # Verify webhook signature
            if signature:
                import hmac
                import hashlib
                
                expected_signature = hmac.new(
                    self.config['secret_key'].encode('utf-8'),
                    str(payload).encode('utf-8'),
                    hashlib.sha512
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    return False, "Invalid webhook signature"
            
            event = payload.get('event')
            data = payload.get('data', {})
            
            if event == 'charge.success':
                # Payment successful
                reference = data.get('reference')
                
                try:
                    payment = Payment.objects.get(payment_id=reference)
                    
                    if payment.status != Payment.Status.COMPLETED:
                        # Update payment details
                        payment.provider_fee = self.parse_amount(
                            data.get('fees', 0), 
                            data.get('currency', 'NGN')
                        )
                        payment.metadata.update({
                            'paystack_transaction_id': data.get('id'),
                            'paid_at': data.get('paid_at'),
                            'channel': data.get('channel'),
                            'authorization': data.get('authorization', {})
                        })
                        payment.save()
                        
                        # Complete payment
                        from apps.payments.services.payment_service import PaymentService
                        PaymentService.complete_payment(payment)
                        
                        self.log_transaction('webhook_charge_success', {
                            'payment_id': str(payment.payment_id),
                            'reference': reference
                        })
                
                except Payment.DoesNotExist:
                    return False, f"Payment not found: {reference}"
            
            elif event == 'charge.failed':
                # Payment failed
                reference = data.get('reference')
                
                try:
                    payment = Payment.objects.get(payment_id=reference)
                    payment.mark_as_failed(f"Paystack payment failed: {data.get('gateway_response')}")
                    
                    self.log_transaction('webhook_charge_failed', {
                        'payment_id': str(payment.payment_id),
                        'reference': reference,
                        'reason': data.get('gateway_response')
                    })
                
                except Payment.DoesNotExist:
                    return False, f"Payment not found: {reference}"
            
            return True, f"Webhook processed: {event}"
        
        except Exception as e:
            return False, self.handle_error(e, "Webhook processing")
    
    def calculate_fees(self, amount: Decimal, currency: str = 'NGN') -> Dict[str, Decimal]:
        """
        Calculate Paystack fees.
        """
        # Paystack fee structure (as of 2024)
        if currency == 'NGN':
            if amount <= Decimal('2500'):
                fee = amount * Decimal('0.015')  # 1.5%
            else:
                fee = amount * Decimal('0.015')
                if fee > Decimal('2000'):  # Cap at ₦2000
                    fee = Decimal('2000')
        else:
            # International transactions
            fee = amount * Decimal('0.039') + Decimal('0.50')  # 3.9% + $0.50
        
        return {
            'processing_fee': fee,
            'fixed_fee': Decimal('0.00'),
            'total_fee': fee
        }
