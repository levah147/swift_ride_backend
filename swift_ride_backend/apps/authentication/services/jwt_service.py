"""
JWT service for authentication.
"""

from rest_framework_simplejwt.tokens import RefreshToken


class JWTService:
    """
    Service for handling JWT operations.
    """
    
    @staticmethod
    def get_tokens_for_user(user):
        """
        Generate JWT tokens for the given user.
        """
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims
        refresh['user_type'] = user.user_type
        refresh['phone_number'] = str(user.phone_number)
        
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
