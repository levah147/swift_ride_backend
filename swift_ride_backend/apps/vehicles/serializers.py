"""
Serializers for vehicle models.
"""

from rest_framework import serializers
from django.utils import timezone

from apps.vehicles.models import (
    VehicleType, Vehicle, VehicleDocument, Insurance, 
    Inspection, VehicleMaintenanceRecord
)
from apps.users.serializers import UserSerializer


class VehicleTypeSerializer(serializers.ModelSerializer):
    """
    Serializer for VehicleType model.
    """
    class Meta:
        model = VehicleType
        fields = [
            'id', 'name', 'description', 'base_fare', 'per_km_rate',
            'per_minute_rate', 'capacity', 'icon', 'is_active'
        ]


class VehicleDocumentSerializer(serializers.ModelSerializer):
    """
    Serializer for VehicleDocument model.
    """
    verified_by = UserSerializer(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = VehicleDocument
        fields = [
            'id', 'vehicle', 'document_type', 'document_number',
            'document_file', 'issue_date', 'expiry_date', 'issuing_authority',
            'is_verified', 'verified_at', 'verified_by', 'notes',
            'is_expired', 'days_until_expiry', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'vehicle', 'is_verified', 'verified_at', 'verified_by',
            'created_at', 'updated_at'
        ]


class InsuranceSerializer(serializers.ModelSerializer):
    """
    Serializer for Insurance model.
    """
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Insurance
        fields = [
            'id', 'vehicle', 'insurance_type', 'policy_number',
            'insurance_company', 'premium_amount', 'coverage_amount',
            'start_date', 'end_date', 'certificate_file', 'is_active',
            'is_expired', 'days_until_expiry', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'vehicle', 'created_at', 'updated_at']


class InspectionSerializer(serializers.ModelSerializer):
    """
    Serializer for Inspection model.
    """
    inspector = UserSerializer(read_only=True)
    is_passed = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Inspection
        fields = [
            'id', 'vehicle', 'inspection_type', 'status', 'scheduled_date',
            'completed_date', 'inspector', 'inspection_center',
            'exterior_condition', 'interior_condition', 'engine_condition',
            'brake_condition', 'tire_condition', 'lights_condition',
            'overall_score', 'notes', 'recommendations', 'next_inspection_date',
            'inspection_photos', 'is_passed', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'vehicle', 'completed_date', 'inspector',
            'created_at', 'updated_at'
        ]


class VehicleMaintenanceRecordSerializer(serializers.ModelSerializer):
    """
    Serializer for VehicleMaintenanceRecord model.
    """
    class Meta:
        model = VehicleMaintenanceRecord
        fields = [
            'id', 'vehicle', 'maintenance_type', 'description',
            'service_provider', 'cost', 'mileage_at_service',
            'service_date', 'next_service_date', 'next_service_mileage',
            'receipt_file', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'vehicle', 'created_at', 'updated_at']


class VehicleSerializer(serializers.ModelSerializer):
    """
    Serializer for Vehicle model.
    """
    owner = UserSerializer(read_only=True)
    vehicle_type = VehicleTypeSerializer(read_only=True)
    verified_by = UserSerializer(read_only=True)
    documents = VehicleDocumentSerializer(many=True, read_only=True)
    insurance = InsuranceSerializer(read_only=True)
    latest_inspection = serializers.SerializerMethodField()
    is_verified = serializers.BooleanField(read_only=True)
    display_name = serializers.CharField(read_only=True)
    has_valid_documents = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'id', 'owner', 'vehicle_type', 'make', 'model', 'year', 'color',
            'license_plate', 'vin_number', 'fuel_type', 'engine_capacity',
            'mileage', 'verification_status', 'is_active', 'is_eco_friendly',
            'front_photo', 'back_photo', 'side_photo', 'interior_photo',
            'verified_at', 'verified_by', 'rejection_reason', 'documents',
            'insurance', 'latest_inspection', 'is_verified', 'display_name',
            'has_valid_documents', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'owner', 'verification_status', 'verified_at', 'verified_by',
            'rejection_reason', 'created_at', 'updated_at'
        ]
    
    def get_latest_inspection(self, obj):
        """Get the latest inspection for the vehicle."""
        latest = obj.inspections.first()
        if latest:
            return InspectionSerializer(latest).data
        return None


class VehicleCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating a vehicle.
    """
    vehicle_type_id = serializers.UUIDField(write_only=True)
    
    class Meta:
        model = Vehicle
        fields = [
            'vehicle_type_id', 'make', 'model', 'year', 'color',
            'license_plate', 'vin_number', 'fuel_type', 'engine_capacity',
            'mileage', 'front_photo', 'back_photo', 'side_photo', 'interior_photo'
        ]
    
    def validate_year(self, value):
        """Validate vehicle year."""
        current_year = timezone.now().year
        if value < 1990 or value > current_year + 1:
            raise serializers.ValidationError(
                f"Year must be between 1990 and {current_year + 1}"
            )
        return value
    
    def validate_license_plate(self, value):
        """Validate license plate format."""
        if len(value.replace(' ', '').replace('-', '')) < 3:
            raise serializers.ValidationError(
                "License plate must have at least 3 characters"
            )
        return value.upper()
    
    def create(self, validated_data):
        """Create vehicle with vehicle type."""
        from apps.vehicles.models import VehicleType
        
        vehicle_type_id = validated_data.pop('vehicle_type_id')
        try:
            vehicle_type = VehicleType.objects.get(id=vehicle_type_id)
        except VehicleType.DoesNotExist:
            raise serializers.ValidationError("Invalid vehicle type")
        
        vehicle = Vehicle.objects.create(
            vehicle_type=vehicle_type,
            **validated_data
        )
        
        return vehicle


class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer for uploading vehicle documents.
    """
    document_type = serializers.ChoiceField(choices=VehicleDocument.DocumentType.choices)
    document_number = serializers.CharField(max_length=100)
    document_file = serializers.FileField()
    issue_date = serializers.DateField()
    expiry_date = serializers.DateField()
    issuing_authority = serializers.CharField(max_length=100)
    
    def validate(self, data):
        """Validate document dates."""
        if data['expiry_date'] <= data['issue_date']:
            raise serializers.ValidationError(
                "Expiry date must be after issue date"
            )
        
        if data['expiry_date'] <= timezone.now().date():
            raise serializers.ValidationError(
                "Document has already expired"
            )
        
        return data


class InsuranceCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating insurance.
    """
    certificate_file = serializers.FileField()
    
    class Meta:
        model = Insurance
        fields = [
            'insurance_type', 'policy_number', 'insurance_company',
            'premium_amount', 'coverage_amount', 'start_date', 'end_date',
            'certificate_file'
        ]
    
    def validate(self, data):
        """Validate insurance dates."""
        if data['end_date'] <= data['start_date']:
            raise serializers.ValidationError(
                "End date must be after start date"
            )
        
        return data
