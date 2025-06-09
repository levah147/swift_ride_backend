"""
Authentication serializers for Swift Ride project.
"""

from rest_framework import serializers
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework_simplejwt.serializers import TokenRefreshSerializer as BaseTokenRefreshSerializer


class PhoneNumberSerializer(serializers.Serializer):
    """
    Serializer for phone number.
    """
    phone_number = PhoneNumberField()


class OTPVerificationSerializer(serializers.Serializer):
    """
    Serializer for OTP verification.
    """
    phone_number = PhoneNumberField()
    code = serializers.CharField(max_length=6, min_length=6)


class TokenRefreshSerializer(BaseTokenRefreshSerializer):
    """
    Custom token refresh serializer.
    """
    pass
