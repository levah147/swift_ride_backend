from celery import shared_task
from django.utils import timezone
from django.db.models import Avg, Count
from datetime import timedelta
from apps.reviews.models import Review, ReviewAnalytics, ReviewIncentive
from apps.notifications.services.notification_service import NotificationService


@shared_task
def process_daily_review_analytics():
    """Process daily review analytics for all users"""
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Get all users who had review activity yesterday
    from apps.users.models import User
    
    users_with_activity = User.objects.filter(
        Q(reviews_given__created_at__date=yesterday) |
        Q(reviews_received__created_at__date=yesterday)
    ).distinct()
    
    for user in users_with_activity:
        calculate_user_daily_analytics.delay(user.id, yesterday.isoformat())


@shared_task
def calculate_user_daily_analytics(user_id, date_str):
    """Calculate daily analytics for a specific user"""
    from apps.users.models import User
    from datetime import datetime
    
    try:
        user = User.objects.get(id=user_id)
        date = datetime.fromisoformat(date_str).date()
        
        # Get reviews for the date
        reviews_given = Review.objects.filter(
            reviewer=user,
            created_at__date=date,
            status='approved'
        )
        
        reviews_received = Review.objects.filter(
            reviewee=user,
            created_at__date=date,
            status='approved'
        )
        
        # Calculate metrics
        reviews_given_count = reviews_given.count()
        reviews_received_count = reviews_received.count()
        
        avg_rating_given = reviews_given.aggregate(
            avg=Avg('overall_rating')
        )['avg']
        
        avg_rating_received = reviews_received.aggregate(
            avg=Avg('overall_rating')
        )['avg']
        
        # Calculate engagement metrics
        helpful_votes = sum(
            review.helpful_count for review in reviews_received
        )
        
        reports_received = sum(
            review.report_count for review in reviews_received
        )
        
        # Update or create analytics record
        analytics, created = ReviewAnalytics.objects.update_or_create(
            user=user,
            date=date,
            defaults={
                'reviews_given': reviews_given_count,
                'reviews_received': reviews_received_count,
                'average_rating_given': avg_rating_given,
                'average_rating_received': avg_rating_received,
                'helpful_votes_received': helpful_votes,
                'reports_received': reports_received,
                'review_response_rate': calculate_response_rate(user),
                'average_review_length': calculate_avg_review_length(user)
            }
        )
        
        return f"Analytics updated for user {user.id} on {date}"
        
    except Exception as e:
        return f"Error calculating analytics: {str(e)}"


@shared_task
def send_review_reminders():
    """Send reminders to users who haven't left reviews for completed rides"""
    from apps.rides.models import Ride
    from datetime import timedelta
    
    # Find completed rides from 24 hours ago where no review was left
    reminder_date = timezone.now() - timedelta(hours=24)
    
    rides_needing_reviews = Ride.objects.filter(
        status='completed',
        completed_at__lte=reminder_date,
        completed_at__gte=reminder_date - timedelta(hours=1)
    ).exclude(
        reviews__isnull=False
    )
    
    for ride in rides_needing_reviews:
        # Send reminder to rider
        if not Review.objects.filter(ride=ride, reviewer=ride.rider).exists():
            NotificationService.send_notification(
                user_id=ride.rider.id,
                notification_type='review_reminder',
                title='Rate Your Recent Ride',
                message=f'How was your ride with {ride.driver.get_full_name()}? Leave a review!',
                data={
                    'ride_id': ride.id,
                    'driver_name': ride.driver.get_full_name()
                }
            )
        
        # Send reminder to driver
        if not Review.objects.filter(ride=ride, reviewer=ride.driver).exists():
            NotificationService.send_notification(
                user_id=ride.driver.id,
                notification_type='review_reminder',
                title='Rate Your Recent Passenger',
                message=f'How was your ride with {ride.rider.get_full_name()}? Leave a review!',
                data={
                    'ride_id': ride.id,
                    'rider_name': ride.rider.get_full_name()
                }
            )


@shared_task
def moderate_flagged_reviews():
    """Auto-moderate reviews that have been flagged"""
    flagged_reviews = Review.objects.filter(status='flagged')
    
    for review in flagged_reviews:
        # Simple auto-moderation logic
        if review.report_count >= 10:
            # Too many reports - reject
            review.status = 'rejected'
            review.moderation_notes = 'Auto-rejected due to excessive reports'
            review.save()
            
            # Notify reviewee
            NotificationService.send_notification(
                user_id=review.reviewee.id,
                notification_type='review_moderated',
                title='Review Removed',
                message='A review about you has been removed due to policy violations',
                data={'review_id': review.id}
            )
        
        elif review.helpful_count > review.not_helpful_count * 2:
            # More helpful than not - approve
            review.status = 'approved'
            review.moderation_notes = 'Auto-approved based on helpfulness votes'
            review.save()


@shared_task
def update_incentive_usage():
    """Update usage counts for review incentives"""
    incentives = ReviewIncentive.objects.filter(is_active=True)
    
    for incentive in incentives:
        actual_usage = incentive.usages.count()
        if incentive.usage_count != actual_usage:
            incentive.usage_count = actual_usage
            incentive.save()


@shared_task
def cleanup_old_review_data():
    """Clean up old review analytics and reports"""
    # Remove analytics older than 2 years
    cutoff_date = timezone.now().date() - timedelta(days=730)
    
    deleted_analytics = ReviewAnalytics.objects.filter(
        date__lt=cutoff_date
    ).delete()
    
    # Archive resolved reports older than 1 year
    report_cutoff = timezone.now() - timedelta(days=365)
    
    old_reports = Review.objects.filter(
        reports__status='resolved',
        reports__resolved_at__lt=report_cutoff
    ).distinct()
    
    return {
        'deleted_analytics': deleted_analytics[0],
        'old_reports_found': old_reports.count()
    }


def calculate_response_rate(user):
    """Calculate user's review response rate"""
    total_reviews = Review.objects.filter(reviewee=user).count()
    if total_reviews == 0:
        return 0.0
    
    responses = Review.objects.filter(
        reviewee=user,
        response__isnull=False
    ).count()
    
    return (responses / total_reviews) * 100


def calculate_avg_review_length(user):
    """Calculate average length of reviews given by user"""
    reviews = Review.objects.filter(reviewer=user, comment__isnull=False)
    if not reviews.exists():
        return 0
    
    total_length = sum(len(review.comment) for review in reviews)
    return total_length // reviews.count()
