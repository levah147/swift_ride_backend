from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q
from decimal import Decimal

from .models import (
    Promotion, PromotionUsage, ReferralProgram, Referral,
    LoyaltyProgram, LoyaltyAccount, PromotionCampaign,
    PromotionAnalytics
)
from .serializers import (
    PromotionSerializer, PromotionUsageSerializer, ReferralProgramSerializer,
    ReferralSerializer, LoyaltyProgramSerializer, LoyaltyAccountSerializer,
    PromotionCampaignSerializer, PromotionAnalyticsSerializer,
    PromotionValidationSerializer, PromotionApplicationSerializer,
    ReferralCreateSerializer, LoyaltyRedemptionSerializer
)
from .services.promotion_service import PromotionService, ReferralService, LoyaltyService
from .services.campaign_service import CampaignService


class PromotionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing promotions"""
    
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by promotion type
        type_filter = self.request.query_params.get('type')
        if type_filter:
            queryset = queryset.filter(promotion_type=type_filter)
        
        # Filter active promotions
        active_only = self.request.query_params.get('active_only')
        if active_only == 'true':
            now = timezone.now()
            queryset = queryset.filter(
                status='active',
                start_date__lte=now,
                end_date__gte=now
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def validate_promotion(self, request):
        """Validate a promotion code for a user"""
        serializer = PromotionValidationSerializer(data=request.data)
        if serializer.is_valid():
            result = PromotionService.validate_promotion(
                promotion_code=serializer.validated_data['promotion_code'],
                user=request.user,
                ride_amount=serializer.validated_data['ride_amount']
            )
            return Response(result)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def apply_promotion(self, request):
        """Apply a promotion to a ride"""
        serializer = PromotionApplicationSerializer(data=request.data)
        if serializer.is_valid():
            from apps.rides.models import Ride
            try:
                ride = Ride.objects.get(id=serializer.validated_data['ride_id'])
                result = PromotionService.apply_promotion(
                    promotion_code=serializer.validated_data['promotion_code'],
                    user=request.user,
                    ride=ride
                )
                return Response(result)
            except Ride.DoesNotExist:
                return Response(
                    {'error': 'Ride not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def available_promotions(self, request):
        """Get available promotions for the current user"""
        ride_amount = request.query_params.get('ride_amount')
        if ride_amount:
            ride_amount = Decimal(ride_amount)
        
        promotions = PromotionService.get_available_promotions(
            user=request.user,
            ride_amount=ride_amount
        )
        serializer = PromotionSerializer(promotions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get analytics for a specific promotion"""
        promotion = self.get_object()
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        analytics = PromotionService.get_promotion_analytics(
            promotion=promotion,
            start_date=start_date,
            end_date=end_date
        )
        return Response(analytics)


class PromotionUsageViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing promotion usage"""
    
    queryset = PromotionUsage.objects.all()
    serializer_class = PromotionUsageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        # Filter by promotion
        promotion_id = self.request.query_params.get('promotion_id')
        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)
        
        return queryset


class ReferralProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for managing referral programs"""
    
    queryset = ReferralProgram.objects.all()
    serializer_class = ReferralProgramSerializer
    permission_classes = [IsAuthenticated]


class ReferralViewSet(viewsets.ModelViewSet):
    """ViewSet for managing referrals"""
    
    queryset = Referral.objects.all()
    serializer_class = ReferralSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user (referrer or referee)
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(referrer=self.request.user) | Q(referee=self.request.user)
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def create_referral(self, request):
        """Create a new referral"""
        serializer = ReferralCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                program = ReferralProgram.objects.get(
                    id=serializer.validated_data['program_id']
                )
                result = ReferralService.create_referral(
                    referrer=request.user,
                    referee_phone=serializer.validated_data['referee_phone'],
                    program=program
                )
                return Response(result)
            except ReferralProgram.DoesNotExist:
                return Response(
                    {'error': 'Referral program not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def process_signup(self, request):
        """Process referral signup"""
        referral_code = request.data.get('referral_code')
        if referral_code:
            result = ReferralService.process_referral_signup(
                referral_code=referral_code,
                referee=request.user
            )
            return Response(result)
        return Response(
            {'error': 'Referral code is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


class LoyaltyProgramViewSet(viewsets.ModelViewSet):
    """ViewSet for managing loyalty programs"""
    
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]


class LoyaltyAccountViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing loyalty accounts"""
    
    queryset = LoyaltyAccount.objects.all()
    serializer_class = LoyaltyAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by user
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_account(self, request):
        """Get current user's loyalty account"""
        try:
            account = LoyaltyAccount.objects.get(user=request.user)
            serializer = LoyaltyAccountSerializer(account)
            return Response(serializer.data)
        except LoyaltyAccount.DoesNotExist:
            return Response(
                {'error': 'Loyalty account not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def redeem_points(self, request):
        """Redeem loyalty points"""
        serializer = LoyaltyRedemptionSerializer(data=request.data)
        if serializer.is_valid():
            try:
                program = LoyaltyProgram.objects.get(
                    id=serializer.validated_data['program_id']
                )
                result = LoyaltyService.redeem_points(
                    user=request.user,
                    points_to_redeem=serializer.validated_data['points_to_redeem'],
                    program=program
                )
                return Response(result)
            except LoyaltyProgram.DoesNotExist:
                return Response(
                    {'error': 'Loyalty program not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PromotionCampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for managing promotion campaigns"""
    
    queryset = PromotionCampaign.objects.all()
    serializer_class = PromotionCampaignSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=True, methods=['post'])
    def launch(self, request, pk=None):
        """Launch a campaign"""
        campaign = self.get_object()
        result = CampaignService.launch_campaign(campaign)
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def analytics(self, request, pk=None):
        """Get campaign analytics"""
        campaign = self.get_object()
        analytics = CampaignService.get_campaign_analytics(campaign)
        return Response(analytics)


class PromotionAnalyticsViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing promotion analytics"""
    
    queryset = PromotionAnalytics.objects.all()
    serializer_class = PromotionAnalyticsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by promotion
        promotion_id = self.request.query_params.get('promotion_id')
        if promotion_id:
            queryset = queryset.filter(promotion_id=promotion_id)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(date__range=[start_date, end_date])
        
        return queryset
