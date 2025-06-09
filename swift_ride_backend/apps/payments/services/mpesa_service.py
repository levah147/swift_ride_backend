"""
Service for M-Pesa payment processing.
"""

import requests
import base64
from datetime import datetime
from django.conf import settings

from apps.payments.models import Payment


class MpesaService:
    """
    Service for handling M-Pesa payments.
    """
    
    BASE_URL = getattr(settings, 'MPESA_BASE_URL', 'https://sandbox.safaricom.co.ke')
    CONSUMER_KEY = getattr(settings, 'MPESA_CONSUMER_KEY', '')
    CONSUMER_SECRET = getattr(settings, 'MPESA_CONSUMER_SECRET', '')
    BUSINESS_SHORT_CODE = getattr(settings, 'MPESA_BUSINESS_SHORT_CODE', '')
    PASSKEY = getattr(settings, 'MPESA_PASSKEY', '')
    
    @staticmethod
    def process_payment(payment):
        """
        Process payment via M-Pesa STK Push.
        """
        try:
            # Get access token
            access_token = MpesaService._get_access_token()
            if not access_token:
                payment.mark_as_failed("Failed to get M-Pesa access token")
                return False, "Failed to get M-Pesa access token"
            
            # Prepare STK Push request
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            password = base64.b64encode(
                f"{MpesaService.BUSINESS_SHORT_CODE}{MpesaService.PASSKEY}{timestamp}".encode()
            ).decode('utf-8')
            
            payload = {
                "BusinessShortCode": MpesaService.BUSINESS_SHORT_CODE,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": int(payment.amount),
                "PartyA": payment.payment_method.phone_number,
                "PartyB": MpesaService.BUSINESS_SHORT_CODE,
                "PhoneNumber": payment.payment_method.phone_number,
                "CallBackURL": f"{settings.BACKEND_URL}/api/payments/mpesa/callback/",
                "AccountReference": str(payment.payment_id),
                "TransactionDesc": payment.description or "Swift Ride Payment"
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            # Send STK Push request
            response = requests.post(
                f"{MpesaService.BASE_URL}/mpesa/stkpush/v1/processrequest",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ResponseCode') == '0':
                    # Update payment with M-Pesa data
                    payment.provider_transaction_id = result.get('CheckoutRequestID')
                    payment.status = Payment.Status.PROCESSING
                    payment.save()
                    
                    return True, "STK Push sent successfully"
                else:
                    payment.mark_as_failed(f"M-Pesa error: {result.get('ResponseDescription')}")
                    return False, result.get('ResponseDescription', 'M-Pesa payment failed')
            else:
                payment.mark_as_failed(f"M-Pesa API error: {response.status_code}")
                return False, f"M-Pesa API error: {response.status_code}"
        
        except Exception as e:
            payment.mark_as_failed(f"M-Pesa processing error: {str(e)}")
            return False, f"M-Pesa processing error: {str(e)}"
    
    @staticmethod
    def handle_callback(callback_data):
        """
        Handle M-Pesa payment callback.
        """
        try:
            # Extract callback data
            stk_callback = callback_data.get('Body', {}).get('stkCallback', {})
            checkout_request_id = stk_callback.get('CheckoutRequestID')
            result_code = stk_callback.get('ResultCode')
            
            # Find payment by checkout request ID
            payment = Payment.objects.filter(
                provider_transaction_id=checkout_request_id
            ).first()
            
            if not payment:
                return False, "Payment not found"
            
            if result_code == 0:
                # Payment successful
                callback_metadata = stk_callback.get('CallbackMetadata', {}).get('Item', [])
                
                # Extract transaction details
                mpesa_receipt_number = None
                transaction_date = None
                phone_number = None
                
                for item in callback_metadata:
                    if item.get('Name') == 'MpesaReceiptNumber':
                        mpesa_receipt_number = item.get('Value')
                    elif item.get('Name') == 'TransactionDate':
                        transaction_date = item.get('Value')
                    elif item.get('Name') == 'PhoneNumber':
                        phone_number = item.get('Value')
                
                # Update payment
                payment.metadata.update({
                    'mpesa_receipt_number': mpesa_receipt_number,
                    'transaction_date': transaction_date,
                    'phone_number': phone_number
                })
                payment.save()
                
                # Complete payment
                from apps.payments.services.payment_service import PaymentService
                PaymentService.complete_payment(payment)
                
                return True, "Payment completed successfully"
            else:
                # Payment failed
                result_desc = stk_callback.get('ResultDesc', 'Payment failed')
                payment.mark_as_failed(f"M-Pesa payment failed: {result_desc}")
                
                return False, result_desc
        
        except Exception as e:
            return False, f"Callback processing error: {str(e)}"
    
    @staticmethod
    def _get_access_token():
        """
        Get M-Pesa access token.
        """
        try:
            # Encode credentials
            credentials = base64.b64encode(
                f"{MpesaService.CONSUMER_KEY}:{MpesaService.CONSUMER_SECRET}".encode()
            ).decode('utf-8')
            
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{MpesaService.BASE_URL}/oauth/v1/generate?grant_type=client_credentials",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('access_token')
            
            return None
        
        except Exception:
            return None
