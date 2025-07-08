"""
Flutterwave payment provider.
"""

import requests
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional

from django.conf import settings

from .base import BasePaymentProvider
from apps.payments.models import Payment, PaymentMethod, Refund


class FlutterwaveProvider(BasePaymentProvider):
    """
    Flutterwave payment provider implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'secret_key': getattr(settings, 'FLUTTERWAVE_SECRET_KEY', ''),
            'public_key': getattr(settings, 'FLUTTERWAVE_PUBLIC_KEY', ''),
            'base_url': 'https://api.flutterwave.com/v3'
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(default_config)
    
    def get_required_config_keys(self) -> list:
        return ['secret_key', 'public_key', 'base_url']
    
    def get_supported_currencies(self) -> list:
        return ['NGN', 'USD', 'EUR', 'GBP', 'KES', 'UGX', 'TZS', 'ZAR', 'GHS']
    
    def get_supported_payment_methods(self) -> list:
        return ['card', 'bank_account', 'mobile_money']
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process payment via Flutterwave.
        """
        try:
            headers = {
                'Authorization': f"Bearer {self.config['secret_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'tx_ref': str(payment.payment_id),
                'amount': str(payment.amount),
                'currency': payment.currency,
                'redirect_url': f"{settings.FRONTEND_URL}/payment/callback",
                'customer': {
                    'email': payment.payer.email,
                    'phonenumber': payment.payer.phone_number,
                    'name': payment.payer.get_full_name()
                },
                'customizations': {
                    'title': 'Swift Ride Payment',
                    'description': payment.description or 'Payment for ride service',
                    'logo': f"{settings.BACKEND_URL}/static/images/logo.png"
                },
                'meta': {
                    'payment_id': str(payment.payment_id),
                    'user_id': str(payment.payer.id),
                    'payment_type': payment.payment_type
                }
            }
            
            # Add payment method specific data
            if payment.payment_method:
                if payment.payment_method.method_type == PaymentMethod.MethodType.CARD:
                    payload['payment_options'] = 'card'
                elif payment.payment_method.method_type == PaymentMethod.MethodType.BANK_ACCOUNT:
                    payload['payment_options'] = 'account'
                elif payment.payment_method.method_type == PaymentMethod.MethodType.MOBILE_MONEY:
                    payloa['payment_options'] = 'mobilemoney'
            
            response = requests.post(
                f"{self.config['base_url']}/payments",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'success':
                    data = result['data']
                    
                    # Update payment with Flutterwave data
                    payment.provider_transaction_id = data['id']
                    payment.metadata.update({
                        'flw_ref': data['flw_ref'],
                        'link': data['link']
                    })
                    payment.status = Payment.Status.PROCESSING
                    payment.save()
                    
                    self.log_transaction('payment_initialized', {
                        'payment_id': str(payment.payment_id),
                        'flw_ref': data['flw_ref']
                    })
                    
                    return True, "Payment initialized successfully"
                else:
                    error_message = result.get('message', 'Payment initialization failed')
                    payment.mark_as_failed(f"Flutterwave error: {error_message}")
                    return False, error_message
            else:
                error_message = f"Flutterwave API error: {response.status_code}"
                payment.mark_as_failed(error_message)
                return False, error_message
        
        except Exception as e:
            error_message = self.handle_error(e, "Payment processing")
            payment.mark_as_failed(error_message)
            return False, error_message
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process refund via Flutterwave.
        """
        try:
            headers = {
                'Authorization': f"Bearer {self.config['secret_key']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'amount': str(refund.amount),
                'comments': refund.description or f"Refund for {refund.payment.payment_id}"
            }
            
            response = requests.post(
                f"{self.config['base_url']}/transactions/{refund.payment.provider_transaction_id}/refund",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'success':
                    refund.provider_refund_id = result['data']['id']
                    refund.save()
                    
                    self.log_transaction('refund_processed', {
                        'refund_id': str(refund.refund_id),
                        'flutterwave_refund_id': result['data']['id']
                    })
                    
                    return True, "Refund processed successfully"
                else:
                    error_message = result.get('message', 'Refund processing failed')
                    return False, error_message
            else:
                return False, f"Flutterwave API error: {response.status_code}"
        
        except Exception as e:
            return False, self.handle_error(e, "Refund processing")
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create payment method via Flutterwave.
        """
        try:
            method_type = method_data.get('method_type')
            
            if method_type == PaymentMethod.MethodType.CARD:
                # For cards, we typically tokenize after successful payment
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    method_type=PaymentMethod.MethodType.CARD,
                    provider=PaymentMethod.Provider.FLUTTERWAVE,
                    display_name=f"Card ending in {method_data.get('last4', '****')}",
                    last_four=method_data.get('last4'),
                    card_brand=method_data.get('card_type'),
                    card_exp_month=method_data.get('exp_month'),
                    card_exp_year=method_data.get('exp_year'),
                    provider_payment_method_id=method_data.get('token'),
                    is_verified=True
                )
                
                return payment_method, "Card payment method created successfully"
            
            elif method_type == PaymentMethod.MethodType.MOBILE_MONEY:
                # Mobile money setup
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    method_type=PaymentMethod.MethodType.MOBILE_MONEY,
                    provider=PaymentMethod.Provider.FLUTTERWAVE,
                    display_name=f"Mobile Money - {method_data.get('phone_number', '****')[-4:]}",
                    phone_number=method_data.get('phone_number'),
                    provider_payment_method_id=method_data.get('network', 'MTN'),
                    is_verified=True
                )
                
                return payment_method, "Mobile money payment method created successfully"
            
            else:
                return None, f"Unsupported payment method type: {method_type}"
        
        except Exception as e:
            return None, self.handle_error(e, "Payment method creation")
    
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify payment with Flutterwave.
        """
        try:
            headers = {
                'Authorization': f"Bearer {self.config['secret_key']}",
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.config['base_url']}/transactions/{provider_transaction_id}/verify",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('status') == 'success':
                    transaction_data = result['data']
                    
                    return True, {
                        'status': transaction_data['status'],
                        'amount': Decimal(str(transaction_data['amount'])),
                        'currency': transaction_data['currency'],
                        'tx_ref': transaction_data['tx_ref'],
                        'flw_ref': transaction_data['flw_ref'],
                        'charged_amount': Decimal(str(transaction_data['charged_amount'])),
                        'app_fee': Decimal(str(transaction_data.get('app_fee', 0))),
                        'merchant_fee': Decimal(str(transaction_data.get('merchant_fee', 0))),
                        'processor_response': transaction_data.get('processor_response'),
                        'card': transaction_data.get('card', {}),
                        'created_at': transaction_data.get('created_at')
                    }
                else:
                    return False, {'error': result.get('message', 'Verification failed')}
            else:
                return False, {'error': f"API error: {response.status_code}"}
        
        except Exception as e:
            return False, {'error': self.handle_error(e, "Payment verification")}
    
    def handle_webhook(self, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle Flutterwave webhook.
        """
        try:
            # Verify webhook signature
            if signature:
                import hmac
                import hashlib
                
                expected_signature = hmac.new(
                    self.config['secret_key'].encode('utf-8'),
                    str(payload).encode('utf-8'),
                    hashlib.sha256
                ).hexdigest()
                
                if not hmac.compare_digest(signature, expected_signature):
                    return False, "Invalid webhook signature"
            
            event = payload.get('event')
            data = payload.get('data', {})
            
            if event == 'charge.completed':
                # Payment completed
                tx_ref = data.get('tx_ref')
                
                try:
                    payment = Payment.objects.get(payment_id=tx_ref)
                    
                    if payment.status != Payment.Status.COMPLETED:
                        # Verify payment first
                        success, verification_data = self.verify_payment(data.get('id'))
                        
                        if success and verification_data.get('status') == 'successful':
                            # Update payment details
                            payment.provider_fee = verification_data.get('app_fee', Decimal('0.00'))
                            payment.metadata.update({
                                'flw_ref': verification_data.get('flw_ref'),
                                'processor_response': verification_data.get('processor_response'),
                                'card_info': verification_data.get('card', {}),
                                'charged_amount': verification_data.get('charged_amount')
                            })
                            payment.save()
                            
                            # Complete payment
                            from apps.payments.services.payment_service import PaymentService
                            PaymentService.complete_payment(payment)
                            
                            self.log_transaction('webhook_charge_completed', {
                                'payment_id': str(payment.payment_id),
                                'tx_ref': tx_ref
                            })
                        else:
                            payment.mark_as_failed("Payment verification failed")
                
                except Payment.DoesNotExist:
                    return False, f"Payment not found: {tx_ref}"
            
            elif event == 'charge.failed':
                # Payment failed
                tx_ref = data.get('tx_ref')
                
                try:
                    payment = Payment.objects.get(payment_id=tx_ref)
                    payment.mark_as_failed(f"Flutterwave payment failed: {data.get('processor_response')}")
                    
                    self.log_transaction('webhook_charge_failed', {
                        'payment_id': str(payment.payment_id),
                        'tx_ref': tx_ref,
                        'reason': data.get('processor_response')
                    })
                
                except Payment.DoesNotExist:
                    return False, f"Payment not found: {tx_ref}"
            
            return True, f"Webhook processed: {event}"
        
        except Exception as e:
            return False, self.handle_error(e, "Webhook processing")
    
    def calculate_fees(self, amount: Decimal, currency: str = 'NGN') -> Dict[str, Decimal]:
        """
        Calculate Flutterwave fees.
        """
        # Flutterwave fee structure (as of 2024)
        if currency == 'NGN':
            fee = amount * Decimal('0.014')  # 1.4%
            if fee < Decimal('10'):  # Minimum fee
                fee = Decimal('10')
        elif currency in ['USD', 'EUR', 'GBP']:
            fee = amount * Decimal('0.034')  # 3.4%
        else:
            # Other African currencies
            fee = amount * Decimal('0.015')  # 1.5%
        
        return {
            'processing_fee': fee,
            'fixed_fee': Decimal('0.00'),
            'total_fee': fee
        }
