"""
Views for the vehicles app.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers  # This was missing
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from apps.vehicles.models import (
    VehicleType, Vehicle, VehicleDocument, Insurance, Inspection
)
from apps.vehicles.serializers import (
    VehicleTypeSerializer, VehicleSerializer, VehicleCreateSerializer,
    VehicleDocumentSerializer, InsuranceSerializer, InspectionSerializer,
    DocumentUploadSerializer, InsuranceCreateSerializer
)
from apps.vehicles.services.vehicle_service import VehicleService
from apps.vehicles.services.document_service import DocumentService
from apps.vehicles.services.inspection_service import InspectionService


class VehicleTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for vehicle types.
    """
    queryset = VehicleType.objects.filter(is_active=True)
    serializer_class = VehicleTypeSerializer
    permission_classes = [IsAuthenticated]


class VehicleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vehicles.
    """
    serializer_class = VehicleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get queryset based on user type."""
        user = self.request.user
        
        if user.is_driver:
            return Vehicle.objects.filter(owner=user).order_by('-created_at')
        elif user.is_staff:
            return Vehicle.objects.all().order_by('-created_at')
        else:
            return Vehicle.objects.none()
    
    def get_serializer_class(self):
        """Get serializer class based on action."""
        if self.action == 'create':
            return VehicleCreateSerializer
        return VehicleSerializer
    
    def perform_create(self, serializer):
        """Create vehicle for the current user."""
        if not self.request.user.is_driver:
            raise serializers.ValidationError("Only drivers can register vehicles")

        vehicle = VehicleService.register_vehicle(
            self.request.user,
            serializer.validated_data
        )
        serializer.instance = vehicle  # 💡 Important

        
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a vehicle (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can verify vehicles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle = self.get_object()
        verification_status = request.data.get('status')
        rejection_reason = request.data.get('rejection_reason')
        
        if verification_status not in [choice[0] for choice in Vehicle.VerificationStatus.choices]:
            return Response(
                {'error': 'Invalid verification status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        verified_vehicle = VehicleService.verify_vehicle(
            vehicle,
            request.user,
            verification_status,
            rejection_reason
        )
        
        return Response(VehicleSerializer(verified_vehicle).data)
    
    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        """Suspend a vehicle (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can suspend vehicles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle = self.get_object()
        reason = request.data.get('reason', 'No reason provided')
        
        suspended_vehicle = VehicleService.suspend_vehicle(vehicle, reason)
        
        return Response(VehicleSerializer(suspended_vehicle).data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a suspended vehicle (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can activate vehicles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicle = self.get_object()
        activated_vehicle = VehicleService.activate_vehicle(vehicle)
        
        return Response(VehicleSerializer(activated_vehicle).data)
    
    @action(detail=True, methods=['get'])
    def eligibility(self, request, pk=None):
        """Check vehicle eligibility for rides."""
        vehicle = self.get_object()
        
        # Check if user owns the vehicle or is admin
        if vehicle.owner != request.user and not request.user.is_staff:
            return Response(
                {'error': 'You do not have permission to check this vehicle'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        is_eligible, message = VehicleService.check_vehicle_eligibility(vehicle)
        
        return Response({
            'is_eligible': is_eligible,
            'message': message
        })
    
    @action(detail=True, methods=['post'])
    def upload_document(self, request, pk=None):
        """Upload a document for the vehicle."""
        vehicle = self.get_object()
        
        # Check if user owns the vehicle
        if vehicle.owner != request.user:
            return Response(
                {'error': 'You can only upload documents for your own vehicles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DocumentUploadSerializer(data=request.data)
        if serializer.is_valid():
            document_file = serializer.validated_data.pop('document_file')
            document = DocumentService.upload_document(
                vehicle,
                serializer.validated_data,
                document_file
            )
            
            return Response(
                VehicleDocumentSerializer(document).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def upload_insurance(self, request, pk=None):
        """Upload insurance for the vehicle."""
        vehicle = self.get_object()
        
        # Check if user owns the vehicle
        if vehicle.owner != request.user:
            return Response(
                {'error': 'You can only upload insurance for your own vehicles'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = InsuranceCreateSerializer(data=request.data)
        if serializer.is_valid():
            certificate_file = serializer.validated_data.pop('certificate_file')
            insurance = DocumentService.create_insurance(
                vehicle,
                serializer.validated_data,
                certificate_file
            )
            
            return Response(
                InsuranceSerializer(insurance).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def needing_attention(self, request):
        """Get vehicles needing attention (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can view this information'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        vehicles = VehicleService.get_vehicles_needing_attention()
        serializer = VehicleSerializer(vehicles, many=True)
        
        return Response(serializer.data)


class VehicleDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for vehicle documents.
    """
    serializer_class = VehicleDocumentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get queryset based on user type."""
        user = self.request.user
        
        if user.is_driver:
            return VehicleDocument.objects.filter(
                vehicle__owner=user
            ).order_by('-created_at')
        elif user.is_staff:
            return VehicleDocument.objects.all().order_by('-created_at')
        else:
            return VehicleDocument.objects.none()
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a document (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can verify documents'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        document = self.get_object()
        is_verified = request.data.get('is_verified', False)
        notes = request.data.get('notes', '')
        
        verified_document = DocumentService.verify_document(
            document,
            request.user,
            is_verified,
            notes
        )
        
        return Response(VehicleDocumentSerializer(verified_document).data)
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get expiring documents (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can view this information'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        days_ahead = int(request.query_params.get('days', 30))
        documents = DocumentService.get_expiring_documents(days_ahead)
        serializer = VehicleDocumentSerializer(documents, many=True)
        
        return Response(serializer.data)


class InspectionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for vehicle inspections.
    """
    serializer_class = InspectionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get queryset based on user type."""
        user = self.request.user
        
        if user.is_driver:
            return Inspection.objects.filter(
                vehicle__owner=user
            ).order_by('-scheduled_date')
        elif user.is_staff:
            return Inspection.objects.all().order_by('-scheduled_date')
        else:
            return Inspection.objects.none()
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start an inspection (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can start inspections'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        inspection = self.get_object()
        started_inspection = InspectionService.start_inspection(
            inspection,
            request.user
        )
        
        return Response(InspectionSerializer(started_inspection).data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete an inspection (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can complete inspections'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        inspection = self.get_object()
        
        # Validate inspection results
        required_fields = [
            'exterior_condition', 'interior_condition', 'engine_condition',
            'brake_condition', 'tire_condition', 'lights_condition', 'overall_score'
        ]
        
        inspection_results = {}
        for field in required_fields:
            if field in request.data:
                inspection_results[field] = request.data[field]
        
        if 'notes' in request.data:
            inspection_results['notes'] = request.data['notes']
        if 'recommendations' in request.data:
            inspection_results['recommendations'] = request.data['recommendations']
        
        completed_inspection = InspectionService.complete_inspection(
            inspection,
            inspection_results
        )
        
        return Response(InspectionSerializer(completed_inspection).data)
    
    @action(detail=False, methods=['get'])
    def due(self, request):
        """Get due inspections (admin only)."""
        if not request.user.is_staff:
            return Response(
                {'error': 'Only admin users can view this information'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        due_inspections = InspectionService.get_due_inspections()
        serializer = InspectionSerializer(due_inspections, many=True)
        
        return Response(serializer.data)
