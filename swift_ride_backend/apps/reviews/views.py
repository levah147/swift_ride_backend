from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.shortcuts import get_object_or_404

from apps.reviews.models import (
    Review, ReviewCategory, ReviewReport, ReviewTemplate, ReviewIncentive
)
from apps.reviews.serializers import (
    ReviewSerializer, ReviewListSerializer, ReviewCategorySerializer,
    ReviewReportSerializer, ReviewTemplateSerializer, ReviewIncentiveSerializer,
    ReviewStatsSerializer, ReviewResponseSerializer, ReviewHelpfulnessVoteSerializer
) 
from apps.reviews.services.review_service import ReviewService
from apps.users.models import User


class ReviewViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reviews"""
    serializer_class = ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Review.objects.select_related(
            'reviewer', 'reviewee', 'ride'
        ).prefetch_related(
            'review_ratings__category', 'helpfulness_votes'
        )
        
        # Filter by user
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(reviewee_id=user_id)
        
        # Filter by review type
        review_type = self.request.query_params.get('review_type')
        if review_type:
            queryset = queryset.filter(review_type=review_type)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', 'approved')
        queryset = queryset.filter(status=status_filter)
        
        return queryset.order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return ReviewListSerializer
        return ReviewSerializer

    def perform_create(self, serializer):
        serializer.save()

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        """Add response to a review"""
        review = self.get_object()
        serializer = ReviewResponseSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                updated_review = ReviewService.respond_to_review(
                    review_id=review.id,
                    user_id=request.user.id,
                    response=serializer.validated_data['response']
                )
                
                response_serializer = ReviewSerializer(updated_review)
                return Response(response_serializer.data)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def vote_helpfulness(self, request, pk=None):
        """Vote on review helpfulness"""
        review = self.get_object()
        serializer = ReviewHelpfulnessVoteSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                ReviewService.vote_helpfulness(
                    review_id=review.id,
                    user_id=request.user.id,
                    vote=serializer.validated_data['vote']
                )
                
                return Response({'message': 'Vote recorded successfully'})
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """Report a review"""
        review = self.get_object()
        serializer = ReviewReportSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                report = ReviewService.report_review(
                    review_id=review.id,
                    reporter_id=request.user.id,
                    reason=serializer.validated_data['reason'],
                    description=serializer.validated_data['description']
                )
                
                response_serializer = ReviewReportSerializer(report)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': str(e)},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Get review statistics for a user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            stats = ReviewService.get_user_review_stats(int(user_id))
            serializer = ReviewStatsSerializer(stats)
            return Response(serializer.data)
            
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def my_reviews(self, request):
        """Get reviews given by the current user"""
        reviews = Review.objects.filter(
            reviewer=request.user
        ).select_related(
            'reviewee', 'ride'
        ).order_by('-created_at')
        
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = ReviewListSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def pending_reviews(self, request):
        """Get pending reviews for the current user"""
        from apps.rides.models import Ride
        
        # Find completed rides where user hasn't left a review
        completed_rides = Ride.objects.filter(
            Q(rider=request.user) | Q(driver=request.user),
            status='completed'
        ).exclude(
            reviews__reviewer=request.user
        ).select_related('rider', 'driver')
        
        pending_reviews = []
        for ride in completed_rides:
            if ride.rider == request.user:
                # User is rider, can review driver
                pending_reviews.append({
                    'ride_id': ride.id,
                    'reviewee_id': ride.driver.id,
                    'reviewee_name': ride.driver.get_full_name(),
                    'review_type': 'driver_review',
                    'ride_date': ride.created_at,
                    'pickup_location': ride.pickup_location,
                    'destination': ride.destination
                })
            else:
                # User is driver, can review rider
                pending_reviews.append({
                    'ride_id': ride.id,
                    'reviewee_id': ride.rider.id,
                    'reviewee_name': ride.rider.get_full_name(),
                    'review_type': 'rider_review',
                    'ride_date': ride.created_at,
                    'pickup_location': ride.pickup_location,
                    'destination': ride.destination
                })
        
        return Response(pending_reviews)


class ReviewCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for review categories"""
    queryset = ReviewCategory.objects.filter(is_active=True)
    serializer_class = ReviewCategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class ReviewTemplateViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for review templates"""
    queryset = ReviewTemplate.objects.filter(is_active=True)
    serializer_class = ReviewTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        
        template_type = self.request.query_params.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        
        return queryset.order_by('template_type', 'suggested_rating')


class ReviewIncentiveViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for review incentives"""
    serializer_class = ReviewIncentiveSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReviewIncentive.objects.filter(
            is_active=True
        ).order_by('-created_at')

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get currently active incentives"""
        incentives = [
            incentive for incentive in self.get_queryset()
            if incentive.is_valid()
        ]
        
        serializer = self.get_serializer(incentives, many=True)
        return Response(serializer.data)


class ReviewReportViewSet(viewsets.ModelViewSet):
    """ViewSet for review reports (admin only)"""
    queryset = ReviewReport.objects.all()
    serializer_class = ReviewReportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Only allow staff to view reports
        if not self.request.user.is_staff:
            return ReviewReport.objects.none()
        
        return super().get_queryset().select_related(
            'review', 'reporter', 'resolved_by'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Resolve a review report"""
        if not request.user.is_staff:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        report = self.get_object()
        resolution_notes = request.data.get('resolution_notes', '')
        new_status = request.data.get('status', 'resolved')
        
        report.status = new_status
        report.resolved_by = request.user
        report.resolved_at = timezone.now()
        report.resolution_notes = resolution_notes
        report.save()
        
        serializer = self.get_serializer(report)
        return Response(serializer.data)
