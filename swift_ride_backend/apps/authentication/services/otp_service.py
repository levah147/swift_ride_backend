"""
OTP service for authentication.
"""

from django.utils import timezone
from django.conf import settings

from apps.authentication.models import OTP
from apps.users.models import CustomUser


class OTPService:
    """
    Service for handling OTP operations.
    """
    
    @staticmethod
    def generate_otp(phone_number):
        """
        Generate OTP for the given phone number.
        """
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            # Create a new user if not exists
            user = CustomUser.objects.create_user(phone_number=phone_number)
        
        # Create OTP
        otp = OTP.create_for_user(user)
        
        # Send OTP via SMS
        OTPService._send_otp_sms(phone_number, otp.code)
        
        return otp
    
    @staticmethod
    def verify_otp(phone_number, code):
        """
        Verify OTP for the given phone number.
        """
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return False, "User not found"
        
        # Get the latest unused OTP
        try:
            otp = OTP.objects.filter(
                user=user,
                is_used=False,
                expires_at__gt=timezone.now()
            ).latest('created_at')
        except OTP.DoesNotExist:
            return False, "OTP expired or not found"
        
        # Verify OTP
        if otp.code != code:
            return False, "Invalid OTP"
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Mark user as verified
        user.is_verified = True
        user.save()
        
        return True, "OTP verified successfully"
    
    @staticmethod
    def _send_otp_sms(phone_number, code):
        """
        Send OTP via SMS.
        """
        # In development, just print the OTP
        if settings.DEBUG:
            print(f"OTP for {phone_number}: {code}")
            return
        
        # In production, use Twilio or other SMS service
        try:
            from twilio.rest import Client
            
            client = Client(
                settings.TWILIO_ACCOUNT_SID,
                settings.TWILIO_AUTH_TOKEN
            )
            
            message = client.messages.create(
                body=f"Your Swift Ride verification code is: {code}",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=str(phone_number)
            )
            
            return message.sid
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return None
