from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone
from decimal import Decimal
from typing import Dict, List, Optional

from apps.reviews.models import (
    Review, ReviewCategory, ReviewRating, ReviewHelpfulness,
    ReviewReport, ReviewAnalytics, ReviewIncentive, ReviewIncentiveUsage
)
from apps.users.models import User
from apps.rides.models import Ride
from core.utils.exceptions import ValidationError


class ReviewService:
    """Service for managing reviews and ratings"""

    @staticmethod
    def create_review(
        ride_id: int,
        reviewer_id: int,
        reviewee_id: int,
        review_type: str,
        overall_rating: float,
        title: str = "",
        comment: str = "",
        category_ratings: Dict[int, float] = None,
        is_anonymous: bool = False
    ) -> Review:
        """Create a new review"""
        try:
            with transaction.atomic():
                # Validate ride and users
                ride = Ride.objects.get(id=ride_id)
                reviewer = User.objects.get(id=reviewer_id)
                reviewee = User.objects.get(id=reviewee_id)
                
                # Check if review already exists
                if Review.objects.filter(
                    ride=ride, 
                    reviewer=reviewer, 
                    reviewee=reviewee
                ).exists():
                    raise ValidationError("Review already exists for this ride")
                
                # Validate reviewer can review this ride
                if not ReviewService._can_review_ride(ride, reviewer, reviewee):
                    raise ValidationError("Not authorized to review this ride")
                
                # Create review
                review = Review.objects.create(
                    ride=ride,
                    reviewer=reviewer,
                    reviewee=reviewee,
                    review_type=review_type,
                    overall_rating=Decimal(str(overall_rating)),
                    title=title,
                    comment=comment,
                    is_anonymous=is_anonymous,
                    status='approved'  # Auto-approve for now
                )
                
                # Add category ratings
                if category_ratings:
                    for category_id, rating in category_ratings.items():
                        category = ReviewCategory.objects.get(id=category_id)
                        ReviewRating.objects.create(
                            review=review,
                            category=category,
                            rating=Decimal(str(rating))
                        )
                
                # Check for incentives
                ReviewService._apply_incentives(review)
                
                # Update user rating averages
                ReviewService._update_user_ratings(reviewee)
                
                return review
                
        except Exception as e:
            raise ValidationError(f"Failed to create review: {str(e)}")

    @staticmethod
    def _can_review_ride(ride: Ride, reviewer: User, reviewee: User) -> bool:
        """Check if user can review this ride"""
        # Rider can review driver
        if ride.rider == reviewer and ride.driver == reviewee:
            return True
        
        # Driver can review rider
        if ride.driver == reviewer and ride.rider == reviewee:
            return True
        
        return False

    @staticmethod
    def update_review(
        review_id: int,
        user_id: int,
        overall_rating: float = None,
        title: str = None,
        comment: str = None,
        category_ratings: Dict[int, float] = None
    ) -> Review:
        """Update an existing review"""
        try:
            review = Review.objects.get(id=review_id, reviewer_id=user_id)
            
            if not review.can_be_edited():
                raise ValidationError("Review can no longer be edited")
            
            with transaction.atomic():
                if overall_rating is not None:
                    review.overall_rating = Decimal(str(overall_rating))
                
                if title is not None:
                    review.title = title
                
                if comment is not None:
                    review.comment = comment
                
                review.save()
                
                # Update category ratings
                if category_ratings:
                    # Remove existing ratings
                    review.review_ratings.all().delete()
                    
                    # Add new ratings
                    for category_id, rating in category_ratings.items():
                        category = ReviewCategory.objects.get(id=category_id)
                        ReviewRating.objects.create(
                            review=review,
                            category=category,
                            rating=Decimal(str(rating))
                        )
                
                # Update user rating averages
                ReviewService._update_user_ratings(review.reviewee)
                
                return review
                
        except Review.DoesNotExist:
            raise ValidationError("Review not found")

    @staticmethod
    def delete_review(review_id: int, user_id: int) -> bool:
        """Delete a review"""
        try:
            review = Review.objects.get(id=review_id, reviewer_id=user_id)
            
            if not review.can_be_edited():
                raise ValidationError("Review can no longer be deleted")
            
            reviewee = review.reviewee
            review.delete()
            
            # Update user rating averages
            ReviewService._update_user_ratings(reviewee)
            
            return True
            
        except Review.DoesNotExist:
            raise ValidationError("Review not found")

    @staticmethod
    def respond_to_review(review_id: int, user_id: int, response: str) -> Review:
        """Add response to a review"""
        try:
            review = Review.objects.get(id=review_id, reviewee_id=user_id)
            
            review.response = response
            review.response_date = timezone.now()
            review.save()
            
            return review
            
        except Review.DoesNotExist:
            raise ValidationError("Review not found")

    @staticmethod
    def vote_helpfulness(review_id: int, user_id: int, vote: str) -> bool:
        """Vote on review helpfulness"""
        try:
            review = Review.objects.get(id=review_id)
            user = User.objects.get(id=user_id)
            
            # Remove existing vote
            ReviewHelpfulness.objects.filter(review=review, user=user).delete()
            
            # Add new vote
            ReviewHelpfulness.objects.create(
                review=review,
                user=user,
                vote=vote
            )
            
            # Update counts
            helpful_count = review.helpfulness_votes.filter(vote='helpful').count()
            not_helpful_count = review.helpfulness_votes.filter(vote='not_helpful').count()
            
            review.helpful_count = helpful_count
            review.not_helpful_count = not_helpful_count
            review.save()
            
            return True
            
        except (Review.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Review or user not found")

    @staticmethod
    def report_review(
        review_id: int,
        reporter_id: int,
        reason: str,
        description: str
    ) -> ReviewReport:
        """Report a review"""
        try:
            review = Review.objects.get(id=review_id)
            reporter = User.objects.get(id=reporter_id)
            
            # Check if already reported by this user
            if ReviewReport.objects.filter(review=review, reporter=reporter).exists():
                raise ValidationError("You have already reported this review")
            
            report = ReviewReport.objects.create(
                review=review,
                reporter=reporter,
                reason=reason,
                description=description
            )
            
            # Update report count
            review.report_count = review.reports.count()
            review.save()
            
            # Auto-flag if too many reports
            if review.report_count >= 5:
                review.status = 'flagged'
                review.save()
            
            return report
            
        except (Review.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Review or user not found")

    @staticmethod
    def get_user_reviews(
        user_id: int,
        review_type: str = None,
        status: str = 'approved',
        page: int = 1,
        page_size: int = 20
    ) -> Dict:
        """Get reviews for a user"""
        try:
            user = User.objects.get(id=user_id)
            
            reviews = Review.objects.filter(
                reviewee=user,
                status=status
            )
            
            if review_type:
                reviews = reviews.filter(review_type=review_type)
            
            # Pagination
            start = (page - 1) * page_size
            end = start + page_size
            
            total_count = reviews.count()
            reviews = reviews[start:end]
            
            # Calculate statistics
            stats = ReviewService.get_user_review_stats(user_id)
            
            return {
                'reviews': reviews,
                'total_count': total_count,
                'page': page,
                'page_size': page_size,
                'has_next': end < total_count,
                'stats': stats
            }
            
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def get_user_review_stats(user_id: int) -> Dict:
        """Get review statistics for a user"""
        try:
            user = User.objects.get(id=user_id)
            
            reviews = Review.objects.filter(reviewee=user, status='approved')
            
            stats = reviews.aggregate(
                total_reviews=Count('id'),
                average_rating=Avg('overall_rating'),
                five_star=Count('id', filter=Q(overall_rating__gte=4.5)),
                four_star=Count('id', filter=Q(overall_rating__gte=3.5, overall_rating__lt=4.5)),
                three_star=Count('id', filter=Q(overall_rating__gte=2.5, overall_rating__lt=3.5)),
                two_star=Count('id', filter=Q(overall_rating__gte=1.5, overall_rating__lt=2.5)),
                one_star=Count('id', filter=Q(overall_rating__lt=1.5))
            )
            
            # Calculate percentages
            total = stats['total_reviews'] or 1
            stats.update({
                'five_star_percent': (stats['five_star'] / total) * 100,
                'four_star_percent': (stats['four_star'] / total) * 100,
                'three_star_percent': (stats['three_star'] / total) * 100,
                'two_star_percent': (stats['two_star'] / total) * 100,
                'one_star_percent': (stats['one_star'] / total) * 100,
            })
            
            # Recent reviews trend
            from datetime import timedelta
            recent_date = timezone.now() - timedelta(days=30)
            recent_reviews = reviews.filter(created_at__gte=recent_date)
            
            stats['recent_reviews'] = recent_reviews.count()
            stats['recent_average'] = recent_reviews.aggregate(
                avg=Avg('overall_rating')
            )['avg']
            
            return stats
            
        except User.DoesNotExist:
            raise ValidationError("User not found")

    @staticmethod
    def _update_user_ratings(user: User):
        """Update user's cached rating averages"""
        reviews = Review.objects.filter(reviewee=user, status='approved')
        
        if reviews.exists():
            avg_rating = reviews.aggregate(avg=Avg('overall_rating'))['avg']
            total_reviews = reviews.count()
            
            # Update user profile
            if hasattr(user, 'driver_profile'):
                user.driver_profile.average_rating = avg_rating
                user.driver_profile.total_reviews = total_reviews
                user.driver_profile.save()
            
            if hasattr(user, 'rider_profile'):
                user.rider_profile.average_rating = avg_rating
                user.rider_profile.total_reviews = total_reviews
                user.rider_profile.save()

    @staticmethod
    def _apply_incentives(review: Review):
        """Apply available incentives for a review"""
        active_incentives = ReviewIncentive.objects.filter(
            is_active=True,
            valid_from__lte=timezone.now()
        ).filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=timezone.now())
        )
        
        for incentive in active_incentives:
            if ReviewService._review_qualifies_for_incentive(review, incentive):
                ReviewIncentiveUsage.objects.create(
                    incentive=incentive,
                    review=review,
                    user=review.reviewer,
                    value_awarded=incentive.value
                )
                
                # Update usage count
                incentive.usage_count += 1
                incentive.save()

    @staticmethod
    def _review_qualifies_for_incentive(review: Review, incentive: ReviewIncentive) -> bool:
        """Check if review qualifies for an incentive"""
        # Check minimum rating
        if incentive.minimum_rating and review.overall_rating < incentive.minimum_rating:
            return False
        
        # Check minimum comment length
        if len(review.comment) < incentive.minimum_comment_length:
            return False
        
        # Check if categories are required
        if incentive.requires_categories and not review.review_ratings.exists():
            return False
        
        # Check usage limit
        if incentive.usage_limit and incentive.usage_count >= incentive.usage_limit:
            return False
        
        return True

    @staticmethod
    def get_review_categories() -> List[ReviewCategory]:
        """Get all active review categories"""
        return ReviewCategory.objects.filter(is_active=True).order_by('order', 'name')

    @staticmethod
    def moderate_review(
        review_id: int,
        moderator_id: int,
        status: str,
        notes: str = ""
    ) -> Review:
        """Moderate a review"""
        try:
            review = Review.objects.get(id=review_id)
            moderator = User.objects.get(id=moderator_id)
            
            review.status = status
            review.moderated_by = moderator
            review.moderated_at = timezone.now()
            review.moderation_notes = notes
            review.save()
            
            # Update user ratings if status changed
            if status in ['approved', 'rejected']:
                ReviewService._update_user_ratings(review.reviewee)
            
            return review
            
        except (Review.DoesNotExist, User.DoesNotExist):
            raise ValidationError("Review or moderator not found")
