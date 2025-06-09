from rest_framework import serializers
from django.db.models import Avg
from apps.reviews.models import (
    Review, ReviewCategory, ReviewRating, ReviewHelpfulness,
    ReviewReport, ReviewTemplate, ReviewIncentive
)
from apps.users.serializers import UserSerializer
from apps.rides.serializers import RideSerializer


class ReviewCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewCategory
        fields = ['id', 'name', 'description', 'icon', 'order']


class ReviewRatingSerializer(serializers.ModelSerializer):
    category = ReviewCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = ReviewRating
        fields = ['id', 'category', 'category_id', 'rating']


class ReviewHelpfulnessSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ReviewHelpfulness
        fields = ['id', 'user', 'vote', 'created_at']


class ReviewSerializer(serializers.ModelSerializer):
    reviewer = UserSerializer(read_only=True)
    reviewee = UserSerializer(read_only=True)
    ride = RideSerializer(read_only=True)
    review_ratings = ReviewRatingSerializer(many=True, read_only=True)
    helpfulness_votes = ReviewHelpfulnessSerializer(many=True, read_only=True)
    
    # Write-only fields for creation
    ride_id = serializers.IntegerField(write_only=True)
    reviewee_id = serializers.IntegerField(write_only=True)
    category_ratings = serializers.DictField(
        child=serializers.DecimalField(max_digits=3, decimal_places=2),
        write_only=True,
        required=False
    )
    
    # Computed fields
    average_category_rating = serializers.SerializerMethodField()
    helpful_percentage = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'ride', 'ride_id', 'reviewer', 'reviewee', 'reviewee_id',
            'review_type', 'overall_rating', 'title', 'comment',
            'review_ratings', 'category_ratings', 'status', 'is_anonymous',
            'is_featured', 'helpful_count', 'not_helpful_count', 'report_count',
            'response', 'response_date', 'created_at', 'updated_at',
            'helpfulness_votes', 'average_category_rating', 'helpful_percentage',
            'can_edit'
        ]
        read_only_fields = [
            'id', 'reviewer', 'status', 'helpful_count', 'not_helpful_count',
            'report_count', 'response_date', 'created_at', 'updated_at'
        ]

    def get_average_category_rating(self, obj):
        return obj.average_category_rating

    def get_helpful_percentage(self, obj):
        total_votes = obj.helpful_count + obj.not_helpful_count
        if total_votes == 0:
            return 0
        return (obj.helpful_count / total_votes) * 100

    def get_can_edit(self, obj):
        return obj.can_be_edited()

    def create(self, validated_data):
        category_ratings = validated_data.pop('category_ratings', {})
        reviewer = self.context['request'].user
        
        from apps.reviews.services.review_service import ReviewService
        
        return ReviewService.create_review(
            ride_id=validated_data['ride_id'],
            reviewer_id=reviewer.id,
            reviewee_id=validated_data['reviewee_id'],
            review_type=validated_data['review_type'],
            overall_rating=float(validated_data['overall_rating']),
            title=validated_data.get('title', ''),
            comment=validated_data.get('comment', ''),
            category_ratings={int(k): float(v) for k, v in category_ratings.items()},
            is_anonymous=validated_data.get('is_anonymous', False)
        )


class ReviewListSerializer(serializers.ModelSerializer):
    """Simplified serializer for review lists"""
    reviewer_name = serializers.SerializerMethodField()
    reviewee_name = serializers.SerializerMethodField()
    average_category_rating = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'reviewer_name', 'reviewee_name', 'review_type',
            'overall_rating', 'title', 'comment', 'status', 'is_anonymous',
            'helpful_count', 'not_helpful_count', 'created_at',
            'average_category_rating'
        ]

    def get_reviewer_name(self, obj):
        if obj.is_anonymous:
            return "Anonymous"
        return obj.reviewer.get_full_name()

    def get_reviewee_name(self, obj):
        return obj.reviewee.get_full_name()

    def get_average_category_rating(self, obj):
        return obj.average_category_rating


class ReviewReportSerializer(serializers.ModelSerializer):
    reporter = UserSerializer(read_only=True)
    review = ReviewListSerializer(read_only=True)

    class Meta:
        model = ReviewReport
        fields = [
            'id', 'review', 'reporter', 'reason', 'description',
            'status', 'created_at', 'resolved_by', 'resolved_at',
            'resolution_notes'
        ]
        read_only_fields = [
            'id', 'reporter', 'status', 'created_at', 'resolved_by',
            'resolved_at', 'resolution_notes'
        ]


class ReviewTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewTemplate
        fields = [
            'id', 'title', 'content', 'template_type',
            'suggested_rating', 'usage_count'
        ]


class ReviewIncentiveSerializer(serializers.ModelSerializer):
    is_valid = serializers.SerializerMethodField()

    class Meta:
        model = ReviewIncentive
        fields = [
            'id', 'name', 'description', 'incentive_type', 'value',
            'minimum_rating', 'minimum_comment_length', 'requires_categories',
            'valid_from', 'valid_until', 'usage_limit', 'usage_count',
            'is_valid'
        ]

    def get_is_valid(self, obj):
        return obj.is_valid()


class ReviewStatsSerializer(serializers.Serializer):
    """Serializer for review statistics"""
    total_reviews = serializers.IntegerField()
    average_rating = serializers.DecimalField(max_digits=3, decimal_places=2)
    five_star = serializers.IntegerField()
    four_star = serializers.IntegerField()
    three_star = serializers.IntegerField()
    two_star = serializers.IntegerField()
    one_star = serializers.IntegerField()
    five_star_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    four_star_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    three_star_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    two_star_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    one_star_percent = serializers.DecimalField(max_digits=5, decimal_places=2)
    recent_reviews = serializers.IntegerField()
    recent_average = serializers.DecimalField(max_digits=3, decimal_places=2, allow_null=True)


class ReviewResponseSerializer(serializers.Serializer):
    """Serializer for review responses"""
    response = serializers.CharField(max_length=1000)


class ReviewHelpfulnessVoteSerializer(serializers.Serializer):
    """Serializer for helpfulness votes"""
    vote = serializers.ChoiceField(choices=['helpful', 'not_helpful'])
