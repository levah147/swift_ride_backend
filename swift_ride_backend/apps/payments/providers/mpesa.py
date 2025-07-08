"""
M-Pesa payment provider (Safaricom).
"""

import requests
import base64
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional

from django.conf import settings
from django.utils import timezone

from .base import BasePaymentProvider
from apps.payments.models import Payment, PaymentMethod, Refund


class MpesaProvider(BasePaymentProvider):
    """
    M-Pesa payment provider implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'consumer_key': getattr(settings, 'MPESA_CONSUMER_KEY', ''),
            'consumer_secret': getattr(settings, 'MPESA_CONSUMER_SECRET', ''),
            'business_short_code': getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', ''),
            'passkey': getattr(settings, 'MPESA_PASSKEY', ''),
            'base_url': getattr(settings, 'MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke'),
            'callback_url': getattr(settings, 'MPESA_CALLBACK_URL', ''),
            'timeout_url': getattr(settings, 'MPESA_TIMEOUT_URL', '')
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(default_config)
    
    def get_required_config_keys(self) -> list:
        return ['consumer_key', 'consumer_secret', 'business_short_code', 'passkey', 'base_url']
    
    def get_supported_currencies(self) -> list:
        return ['KES']
    
    def get_supported_payment_methods(self) -> list:
        return ['mobile_money']
    
    def _get_access_token(self) -> Optional[str]:
        """
        Get M-Pesa access token.
        """
        try:
            # Encode credentials
            credentials = base64.b64encode(
                f"{self.config['consumer_key']}:{self.config['consumer_secret']}".encode()
            ).decode()
            
            headers = {
                'Authorization': f'Basic {credentials}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.config['base_url']}/oauth/v1/generate?grant_type=client_credentials",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('access_token')
            
            return None
        
        except Exception as e:
            self.handle_error(e, "Access token generation")
            return None
    
    def _generate_password(self) -> Tuple[str, str]:
        """
        Generate M-Pesa password and timestamp.
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_string = f"{self.config['business_short_code']}{self.config['passkey']}{timestamp}"
        password = base64.b64encode(password_string.encode()).decode()
        
        return password, timestamp
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process payment via M-Pesa STK Push.
        """
        try:
            access_token = self._get_access_token()
            if not access_token:
                return False, "Failed to get M-Pesa access token"
            
            password, timestamp = self._generate_password()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get phone number from payment method or user
            phone_number = None
            if payment.payment_method and payment.payment_method.phone_number:
                phone_number = payment.payment_method.phone_number
            elif hasattr(payment.payer, 'phone_number'):
                phone_number = payment.payer.phone_number
            
            if not phone_number:
                return False, "Phone number is required for M-Pesa payment"
            
            # Format phone number (remove + and ensure it starts with 254)
            phone_number = phone_number.replace('+', '').replace(' ', '')
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number
            
            payload = {
                'BusinessShortCode': self.config['business_short_code'],
                'Password': password,
                'Timestamp': timestamp,
                'TransactionType': 'CustomerPayBillOnline',
                'Amount': int(payment.amount),  # M-Pesa expects integer
                'PartyA': phone_number,
                'PartyB': self.config['business_short_code'],
                'PhoneNumber': phone_number,
                'CallBackURL': self.config.get('callback_url', ''),
                'AccountReference': str(payment.payment_id),
                'TransactionDesc': payment.description or f'Payment for {payment.payment_type}'
            }
            
            response = requests.post(
                f"{self.config['base_url']}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ResponseCode') == '0':
                    # STK Push sent successfully
                    payment.provider_transaction_id = result.get('CheckoutRequestID')
                    payment.metadata.update({
                        'mpesa_checkout_request_id': result.get('CheckoutRequestID'),
                        'mpesa_merchant_request_id': result.get('MerchantRequestID'),
                        'phone_number': phone_number
                    })
                    payment.status = Payment.Status.PROCESSING
                    payment.save()
                    
                    self.log_transaction('stk_push_sent', {
                        'payment_id': str(payment.payment_id),
                        'checkout_request_id': result.get('CheckoutRequestID')
                    })
                    
                    return True, "STK Push sent successfully"
                else:
                    error_message = result.get('ResponseDescription', 'STK Push failed')
                    payment.mark_as_failed(f"M-Pesa error: {error_message}")
                    return False, error_message
            else:
                error_message = f"M-Pesa API error: {response.status_code}"
                payment.mark_as_failed(error_message)
                return False, error_message
        
        except Exception as e:
            error_message = self.handle_error(e, "M-Pesa payment processing")
            payment.mark_as_failed(error_message)
            return False, error_message
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process refund via M-Pesa reversal.
        """
        try:
            access_token = self._get_access_token()
            if not access_token:
                return False, "Failed to get M-Pesa access token"
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'Initiator': 'testapi',  # This should be your initiator name
                'SecurityCredential': 'your_security_credential',  # Encrypted credential
                'CommandID': 'TransactionReversal',
                'TransactionID': refund.payment.provider_transaction_id,
                'Amount': int(refund.amount),
                'ReceiverParty': self.config['business_short_code'],
                'RecieverIdentifierType': '11',
                'ResultURL': self.config.get('callback_url', ''),
                'QueueTimeOutURL': self.config.get('timeout_url', ''),
                'Remarks': refund.description or f'Refund for {refund.payment.payment_id}',
                'Occasion': f'Refund-{refund.refund_id}'
            }
            
            response = requests.post(
                f"{self.config['base_url']}/mpesa/reversal/v1/request",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ResponseCode') == '0':
                    refund.provider_refund_id = result.get('ConversationID')
                    refund.save()
                    
                    self.log_transaction('refund_initiated', {
                        'refund_id': str(refund.refund_id),
                        'conversation_id': result.get('ConversationID')
                    })
                    
                    return True, "Refund initiated successfully"
                else:
                    error_message = result.get('ResponseDescription', 'Refund failed')
                    return False, error_message
            else:
                return False, f"M-Pesa API error: {response.status_code}"
        
        except Exception as e:
            return False, self.handle_error(e, "M-Pesa refund processing")
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create M-Pesa payment method.
        """
        try:
            phone_number = method_data.get('phone_number')
            if not phone_number:
                return None, "Phone number is required for M-Pesa"
            
            # Format and validate phone number
            phone_number = phone_number.replace('+', '').replace(' ', '')
            if phone_number.startswith('0'):
                phone_number = '254' + phone_number[1:]
            elif not phone_number.startswith('254'):
                phone_number = '254' + phone_number
            
            # Validate Kenyan mobile number
            if not (phone_number.startswith('2547') or phone_number.startswith('2541')):
                return None, "Invalid Kenyan mobile number"
            
            payment_method = PaymentMethod.objects.create(
                user=user,
                method_type=PaymentMethod.MethodType.MOBILE_MONEY,
                provider=PaymentMethod.Provider.MPESA,
                display_name=f"M-Pesa - {phone_number[-4:]}",
                phone_number=phone_number,
                is_verified=True  # M-Pesa numbers are considered verified
            )
            
            return payment_method, "M-Pesa payment method created successfully"
        
        except Exception as e:
            return None, self.handle_error(e, "M-Pesa payment method creation")
    
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify M-Pesa payment status.
        """
        try:
            access_token = self._get_access_token()
            if not access_token:
                return False, {'error': 'Failed to get access token'}
            
            password, timestamp = self._generate_password()
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'BusinessShortCode': self.config['business_short_code'],
                'Password': password,
                'Timestamp': timestamp,
                'CheckoutRequestID': provider_transaction_id
            }
            
            response = requests.post(
                f"{self.config['base_url']}/mpesa/stkpushquery/v1/query",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                return True, {
                    'status': result.get('ResultCode'),
                    'description': result.get('ResultDesc'),
                    'checkout_request_id': result.get('CheckoutRequestID'),
                    'merchant_request_id': result.get('MerchantRequestID'),
                    'amount': result.get('Amount'),
                    'mpesa_receipt_number': result.get('MpesaReceiptNumber'),
                    'transaction_date': result.get('TransactionDate'),
                    'phone_number': result.get('PhoneNumber')
                }
            else:
                return False, {'error': f"API error: {response.status_code}"}
        
        except Exception as e:
            return False, {'error': self.handle_error(e, "M-Pesa payment verification")}
    
    def handle_webhook(self, payload: Dict[str, Any], signature: str = None) -> Tuple[bool, str]:
        """
        Handle M-Pesa callback.
        """
        try:
            # M-Pesa callback structure
            stk_callback = payload.get('Body', {}).get('stkCallback', {})
            
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            result_desc = stk_callback.get('ResultDesc')
            
            if not checkout_request_id:
                return False, "Invalid callback: missing CheckoutRequestID"
            
            try:
                payment = Payment.objects.get(provider_transaction_id=checkout_request_id)
                
                if result_code == 0:
                    # Payment successful
                    callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                    metadata = {}
                    
                    for item in callback_metadata:
                        name = item.get('Name')
                        value = item.get('Value')
                        if name and value:
                            metadata[name] = value
                    
                    # Update payment with M-Pesa details
                    payment.metadata.update({
                        'mpesa_receipt_number': metadata.get('MpesaReceiptNumber'),
                        'transaction_date': metadata.get('TransactionDate'),
                        'phone_number': metadata.get('PhoneNumber'),
                        'amount': metadata.get('Amount')
                    })
                    payment.save()
                    
                    # Complete payment
                    from apps.payments.services.payment_service import PaymentService
                    PaymentService.complete_payment(payment)
                    
                    self.log_transaction('callback_payment_success', {
                        'payment_id': str(payment.payment_id),
                        'checkout_request_id': checkout_request_id,
                        'mpesa_receipt': metadata.get('MpesaReceiptNumber')
                    })
                
                else:
                    # Payment failed
                    payment.mark_as_failed(f"M-Pesa payment failed: {result_desc}")
                    
                    self.log_transaction('callback_payment_failed', {
                        'payment_id': str(payment.payment_id),
                        'checkout_request_id': checkout_request_id,
                        'result_code': result_code,
                        'result_desc': result_desc
                    })
            
            except Payment.DoesNotExist:
                return False, f"Payment not found: {checkout_request_id}"
            
            return True, f"Callback processed: {result_desc}"
        
        except Exception as e:
            return False, self.handle_error(e, "M-Pesa callback processing")
    
    def calculate_fees(self, amount: Decimal, currency: str = 'KES') -> Dict[str, Decimal]:
        """
        Calculate M-Pesa fees (simplified structure).
        """
        # M-Pesa charges are typically borne by the customer
        # This is a simplified fee structure
        if amount <= Decimal('100'):
            fee = Decimal('0.00')
        elif amount <= Decimal('500'):
            fee = Decimal('7.00')
        elif amount <= Decimal('1000'):
            fee = Decimal('13.00')
        elif amount <= Decimal('1500'):
            fee = Decimal('23.00')
        elif amount <= Decimal('2500'):
            fee = Decimal('33.00')
        elif amount <= Decimal('3500'):
            fee = Decimal('53.00')
        elif amount <= Decimal('5000'):
            fee = Decimal('57.00')
        else:
            fee = Decimal('61.00')
        
        return {
            'processing_fee': fee,
            'fixed_fee': Decimal('0.00'),
            'total_fee': fee
        }
