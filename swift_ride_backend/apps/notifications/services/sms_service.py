"""
Service for handling SMS notifications.
"""

import requests
from django.conf import settings

from apps.notifications.models import NotificationLog


class SMSService:
    """
    Service for sending SMS notifications via Twilio.
    """
    
    @staticmethod
    def send_sms_notification(notification):
        """
        Send SMS notification to user.
        """
        user = notification.recipient
        
        # Check if user has a valid phone number
        if not user.phone_number:
            return False, "User has no phone number"
        
        try:
            # Prepare SMS content
            message_body = notification.template.render_sms(notification.context)
            
            # Send SMS
            response = SMSService._send_via_twilio(
                to_number=user.phone_number,
                message_body=message_body
            )
            
            # Log the attempt
            success = response.get('status') in ['queued', 'sent', 'delivered']
            SMSService._log_notification(
                notification=notification,
                success=success,
                response=response
            )
            
            if success:
                notification.mark_as_sent()
                return True, "SMS sent successfully"
            else:
                notification.mark_as_failed(response.get('error_message', 'Unknown error'))
                return False, response.get('error_message', 'Failed to send SMS')
        
        except Exception as e:
            print(f"Error sending SMS: {e}")
            notification.mark_as_failed(str(e))
            return False, str(e)
    
    @staticmethod
    def _send_via_twilio(to_number, message_body):
        """
        Send SMS via Twilio API.
        """
        # Twilio credentials from settings
        account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        if not all([account_sid, auth_token, from_number]):
            return {'status': 'failed', 'error_message': 'Twilio credentials not configured'}
        
        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
        
        data = {
            'From': from_number,
            'To': to_number,
            'Body': message_body
        }
        
        try:
            response = requests.post(
                url,
                data=data,
                auth=(account_sid, auth_token),
                timeout=30
            )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    'status': result.get('status'),
                    'sid': result.get('sid'),
                    'message': 'SMS sent successfully'
                }
            else:
                error_data = response.json()
                return {
                    'status': 'failed',
                    'error_code': error_data.get('code'),
                    'error_message': error_data.get('message')
                }
        
        except requests.RequestException as e:
            return {
                'status': 'failed',
                'error_message': f'Request failed: {str(e)}'
            }
    
    @staticmethod
    def _log_notification(notification, success, response):
        """
        Log SMS delivery attempt.
        """
        NotificationLog.objects.create(
            notification=notification,
            channel='sms',
            provider='Twilio',
            provider_message_id=response.get('sid'),
            success=success,
            response_code=str(response.get('status')),
            response_message=response.get('error_message') or response.get('message')
        )
    
    @staticmethod
    def send_verification_sms(phone_number, verification_code):
        """
        Send SMS verification code.
        """
        message_body = f"Your Swift Ride verification code is: {verification_code}. This code expires in 10 minutes."
        
        response = SMSService._send_via_twilio(
            to_number=phone_number,
            message_body=message_body
        )
        
        return response.get('status') in ['queued', 'sent', 'delivered']
    
    @staticmethod
    def send_emergency_sms(phone_number, emergency_message):
        """
        Send emergency SMS.
        """
        response = SMSService._send_via_twilio(
            to_number=phone_number,
            message_body=emergency_message
        )
        
        return response.get('status') in ['queued', 'sent', 'delivered']
