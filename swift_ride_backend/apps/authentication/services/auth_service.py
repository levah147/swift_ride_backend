"""
Authentication service.
"""

from django.utils import timezone

from apps.users.models import CustomUser
from apps.authentication.models import LoginAttempt
from apps.authentication.services.otp_service import OTPService
from apps.authentication.services.jwt_service import JWTService


class AuthService:
    """
    Service for handling authentication operations.
    """
    
    @staticmethod
    def login_with_otp(phone_number, request=None):
        """
        Login with OTP.
        """
        # Generate OTP
        otp = OTPService.generate_otp(phone_number)
        
        # Log login attempt
        if request:
            LoginAttempt.objects.create(
                phone_number=phone_number,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                is_successful=False  # Will be updated after OTP verification
            )
        
        return {
            'message': 'OTP sent successfully',
            'expires_at': otp.expires_at
        }
    
    @staticmethod
    def verify_otp_and_login(phone_number, code, request=None):
        """
        Verify OTP and login.
        """
        # Verify OTP
        is_valid, message = OTPService.verify_otp(phone_number, code)
        
        if not is_valid:
            return {
                'success': False,
                'message': message
            }
        
        # Get user
        try:
            user = CustomUser.objects.get(phone_number=phone_number)
        except CustomUser.DoesNotExist:
            return {
                'success': False,
                'message': 'User not found'
            }
        
        # Update login attempt
        if request:
            LoginAttempt.objects.filter(
                phone_number=phone_number,
                is_successful=False,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=30)
            ).update(is_successful=True)
        
        # Generate tokens
        tokens = JWTService.get_tokens_for_user(user)
        
        return {
            'success': True,
            'message': 'Login successful',
            'tokens': tokens,
            'user': {
                'id': user.id,
                'phone_number': str(user.phone_number),
                'user_type': user.user_type,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'is_verified': user.is_verified
            }
        }
