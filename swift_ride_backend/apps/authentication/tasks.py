"""
Celery tasks for authentication app.
"""

from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import OTP, LoginAttempt


@shared_task
def cleanup_expired_otps():
    """
    Clean up expired OTPs.
    """
    try:
        deleted_count = OTP.objects.cleanup_expired()
        return f"Cleaned up {deleted_count} expired OTPs"
    except Exception as e:
        return f"Error cleaning up OTPs: {str(e)}"


@shared_task
def cleanup_old_login_attempts():
    """
    Clean up old login attempts.
    """
    try:
        deleted_count = LoginAttempt.objects.cleanup_old_attempts()
        return f"Cleaned up {deleted_count} old login attempts"
    except Exception as e:
        return f"Error cleaning up login attempts: {str(e)}"


@shared_task
def send_otp_sms(phone_number, otp_code):
    """
    Send OTP via SMS using Twilio.
    """
    try:
        if settings.DEBUG:
            # In development, just log the OTP
            print(f"SMS OTP for {phone_number}: {otp_code}")
            return f"Development mode: OTP {otp_code} logged for {phone_number}"
        
        # In production, use Twilio
        from twilio.rest import Client
        
        client = Client(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN
        )
        
        message = client.messages.create(
            body=f"Your Swift Ride verification code is: {otp_code}. Valid for 10 minutes.",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=str(phone_number)
        )
        
        return f"SMS sent successfully. SID: {message.sid}"
        
    except Exception as e:
        return f"Error sending SMS: {str(e)}"


@shared_task
def log_security_event(event_type, phone_number, details=None):
    """
    Log security events for monitoring.
    """
    try:
        # In a real app, you'd send this to your security monitoring system
        security_log = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'phone_number': phone_number,
            'details': details or {}
        }
        
        print(f"Security Event: {security_log}")
        
        # You could send to external monitoring service here
        # monitoring_service.log_event(security_log)
        
        return f"Security event logged: {event_type}"
        
    except Exception as e:
        return f"Error logging security event: {str(e)}"
