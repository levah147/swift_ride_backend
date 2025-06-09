"""
Authentication views for Swift Ride project.
"""

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenRefreshView

from .serializers import (
    PhoneNumberSerializer,
    OTPVerificationSerializer,
    TokenRefreshSerializer
)
from .services.auth_service import AuthService


class LoginWithOTPView(APIView):
    """
    View for login with OTP.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Generate OTP for login.
        """
        serializer = PhoneNumberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        result = AuthService.login_with_otp(phone_number, request)
        
        return Response(result, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """
    View for OTP verification.
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        Verify OTP and login.
        """
        serializer = OTPVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone_number = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        
        result = AuthService.verify_otp_and_login(phone_number, code, request)
        
        if result['success']:
            return Response(result, status=status.HTTP_200_OK)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Custom token refresh view.
    """
    serializer_class = TokenRefreshSerializer


class LogoutView(APIView):
    """
    View for logout.
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """
        Logout user.
        """
        # Add token to blacklist
        try:
            refresh_token = request.data["refresh"]
            from rest_framework_simplejwt.tokens import RefreshToken
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Logout successful"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
