"""
Serializers for user models.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.users.models import UserProfile, DriverProfile, RiderProfile, UserPreferences, UserDocument

User = get_user_model()


class UserBasicSerializer(serializers.ModelSerializer):
    """
    Basic serializer for User model - used for simple user references.
    """
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'is_verified'
        ]
        read_only_fields = ['id', 'is_active', 'is_verified']


class UserPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for UserPreference model.
    """
    class Meta:
        model = UserPreferences
        fields = [
            'id', 'language', 'currency', 'dark_mode', 'accessibility_features',
            'email_notifications', 'push_notifications', 'sms_notifications',
            'ride_notifications', 'chat_notifications', 'marketing_notifications',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for UserDocument model.
    """
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    verification_status_display = serializers.CharField(source='get_verification_status_display', read_only=True)
    is_expired = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = UserDocument
        fields = [
            'id', 'user', 'document_type', 'document_type_display', 'document_number',
            'document_file', 'expiry_date', 'is_expired', 'days_until_expiry',
            'verification_status', 'verification_status_display', 'verified_at',
            'verification_notes', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user', 'verification_status', 'verified_at',
            'verification_notes', 'created_at', 'updated_at'
        ]
    
    def get_is_expired(self, obj):
        """Check if document is expired."""
        if obj.expiry_date:
            return obj.expiry_date < timezone.now().date()
        return False
    
    def get_days_until_expiry(self, obj):
        """Get days until document expires."""
        if obj.expiry_date:
            delta = obj.expiry_date - timezone.now().date()
            return max(0, delta.days)
        return None


class DriverProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for DriverProfile model.
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    vehicle_type_display = serializers.CharField(source='get_vehicle_type_display', read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    total_rides = serializers.IntegerField(read_only=True)
    total_earnings = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    is_online = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = DriverProfile
        fields = [
            'id', 'status', 'status_display', 'approved_at', 'vehicle_type',
            'vehicle_type_display', 'license_number', 'experience_years',
            'average_rating', 'total_rides', 'total_earnings', 'is_online',
            'current_latitude', 'current_longitude', 'last_location_update',
            'availability_status', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'approved_at', 'average_rating', 'total_rides',
            'total_earnings', 'is_online', 'created_at', 'updated_at'
        ]


class RiderProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for RiderProfile model.
    """
    average_rating = serializers.FloatField(read_only=True)
    total_rides = serializers.IntegerField(read_only=True)
    total_spent = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = RiderProfile
        fields = [
            'id', 'home_address', 'work_address', 'home_latitude', 'home_longitude',
            'work_latitude', 'work_longitude', 'average_rating', 'total_rides',
            'total_spent', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'average_rating', 'total_rides', 'total_spent',
            'created_at', 'updated_at'
        ]


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for UserProfile model.
    """
    class Meta:
        model = UserProfile
        fields = [
            'id', 'bio', 'profile_picture', 'date_of_birth', 'gender',
            'address', 'city', 'state', 'country', 'postal_code',
            'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_contact_phone', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    """
    profile = UserProfileSerializer(read_only=True)
    driver_profile = DriverProfileSerializer(read_only=True)
    rider_profile = RiderProfileSerializer(read_only=True)
    preferences = UserPreferenceSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    is_driver = serializers.BooleanField(read_only=True)
    is_rider = serializers.BooleanField(read_only=True)
    is_verified = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'first_name', 'last_name', 'full_name',
            'is_active', 'is_verified', 'is_driver', 'is_rider', 'date_joined',
            'last_login', 'profile', 'driver_profile', 'rider_profile', 'preferences'
        ]
        read_only_fields = [
            'id', 'is_active', 'is_verified', 'date_joined', 'last_login'
        ]


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating User model.
    """
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating UserProfile model.
    """
    class Meta:
        model = UserProfile
        fields = [
            'bio', 'profile_picture', 'date_of_birth', 'gender',
            'address', 'city', 'state', 'country', 'postal_code',
            'emergency_contact_name', 'emergency_contact_relationship',
            'emergency_contact_phone'
        ]


class DriverProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating DriverProfile model.
    """
    class Meta:
        model = DriverProfile
        fields = [
            'vehicle_type', 'license_number', 'experience_years',
            'current_latitude', 'current_longitude', 'availability_status'
        ]


class RiderProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating RiderProfile model.
    """
    class Meta:
        model = RiderProfile
        fields = [
            'home_address', 'work_address', 'home_latitude', 'home_longitude',
            'work_latitude', 'work_longitude'
        ]


class UserPreferenceUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating UserPreference model.
    """
    class Meta:
        model = UserPreferences
        fields = [
            'language', 'currency', 'dark_mode', 'accessibility_features',
            'email_notifications', 'push_notifications', 'sms_notifications',
            'ride_notifications', 'chat_notifications', 'marketing_notifications'
        ]


class UserDocumentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating UserDocument model.
    """
    class Meta:
        model = UserDocument
        fields = [
            'document_type', 'document_number', 'document_file', 'expiry_date'
        ]
        
    def validate_expiry_date(self, value):
        """Validate expiry date is in the future."""
        if value and value <= timezone.now().date():
            raise serializers.ValidationError("Expiry date must be in the future")
        return value
    
    def validate_document_number(self, value):
        """Validate document number is not empty and has reasonable length."""
        if not value or not value.strip():
            raise serializers.ValidationError("Document number cannot be empty")
        
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Document number must be at least 3 characters long")
            
        return value.strip()
    
    def validate_document_file(self, value):
        """Validate document file size and type."""
        if value:
            # Check file size (e.g., max 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError("File size cannot exceed 5MB")
            
            # Check file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'application/pdf']
            if hasattr(value, 'content_type') and value.content_type not in allowed_types:
                raise serializers.ValidationError(
                    "Only JPEG, PNG, GIF, and PDF files are allowed"
                )
        
        return value
    
    def validate(self, attrs):
        """Custom validation for the entire object."""
        # Check for duplicate document numbers for the same user and document type
        user = self.context.get('request').user if self.context.get('request') else None
        
        if user and 'document_type' in attrs and 'document_number' in attrs:
            existing = UserDocument.objects.filter(
                user=user,
                document_type=attrs['document_type'],
                document_number=attrs['document_number']
            ).exists()
            
            if existing:
                raise serializers.ValidationError(
                    "A document with this type and number already exists for this user"
                )
        
        return attrs
    
    def create(self, validated_data):
        """Create UserDocument with the authenticated user."""
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class UserRegistrationSerializer(serializers.Serializer):
    """
    Serializer for user registration.
    """
    phone_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=30)
    last_name = serializers.CharField(max_length=30)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(min_length=8, write_only=True)
    user_type = serializers.ChoiceField(choices=['rider', 'driver', 'both'])
    
    def validate_phone_number(self, value):
        """Validate phone number is unique."""
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("This phone number is already registered")
        return value
    
    def validate_email(self, value):
        """Validate email is unique if provided."""
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """
    Serializer for password change.
    """
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, data):
        """Validate passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.
    """
    phone_number = serializers.CharField(max_length=20)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.
    """
    phone_number = serializers.CharField(max_length=20)
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    
    def validate(self, data):
        """Validate passwords match."""
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match"})
        return data


class UserListSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for User list view.
    """
    full_name = serializers.CharField(read_only=True)
    user_type = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'phone_number', 'email', 'full_name', 'user_type',
            'is_active', 'is_verified', 'date_joined'
        ]
    
    def get_user_type(self, obj):
        """Get user type (rider, driver, or both)."""
        is_driver = hasattr(obj, 'driver_profile')
        is_rider = hasattr(obj, 'rider_profile')
        
        if is_driver and is_rider:
            return 'both'
        elif is_driver:
            return 'driver'
        elif is_rider:
            return 'rider'
        else:
            return 'unknown' 