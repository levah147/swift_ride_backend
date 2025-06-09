from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from apps.reviews.models import Review, ReviewAnalytics, ReviewIncentiveUsage
from apps.notifications.services.notification_service import NotificationService


@receiver(post_save, sender=Review)
def handle_review_created(sender, instance, created, **kwargs):
    """Handle review creation"""
    if created:
        # Send notification to reviewee
        NotificationService.send_notification(
            user_id=instance.reviewee.id,
            notification_type='review_received',
            title='New Review Received',
            message=f'You received a {instance.overall_rating}★ review from {instance.reviewer.get_full_name()}',
            data={
                'review_id': instance.id,
                'rating': str(instance.overall_rating),
                'reviewer_name': instance.reviewer.get_full_name()
            }
        )
        
        # Update daily analytics
        update_review_analytics(instance.reviewer, instance.reviewee)


@receiver(post_save, sender=Review)
def handle_review_response(sender, instance, **kwargs):
    """Handle review response"""
    if instance.response and instance.response_date:
        # Send notification to reviewer
        NotificationService.send_notification(
            user_id=instance.reviewer.id,
            notification_type='review_response',
            title='Review Response',
            message=f'{instance.reviewee.get_full_name()} responded to your review',
            data={
                'review_id': instance.id,
                'response': instance.response
            }
        )


@receiver(post_save, sender=ReviewIncentiveUsage)
def handle_incentive_awarded(sender, instance, created, **kwargs):
    """Handle incentive award"""
    if created:
        # Send notification about incentive
        NotificationService.send_notification(
            user_id=instance.user.id,
            notification_type='incentive_awarded',
            title='Review Incentive Earned!',
            message=f'You earned {instance.incentive.name} for your review',
            data={
                'incentive_name': instance.incentive.name,
                'value': str(instance.value_awarded),
                'incentive_type': instance.incentive.incentive_type
            }
        )


def update_review_analytics(reviewer, reviewee):
    """Update daily analytics for both reviewer and reviewee"""
    today = timezone.now().date()
    
    # Update reviewer analytics
    reviewer_analytics, created = ReviewAnalytics.objects.get_or_create(
        user=reviewer,
        date=today,
        defaults={
            'reviews_given': 0,
            'reviews_received': 0
        }
    )
    reviewer_analytics.reviews_given += 1
    
    # Calculate average rating given
    from django.db.models import Avg
    avg_given = Review.objects.filter(
        reviewer=reviewer,
        status='approved'
    ).aggregate(avg=Avg('overall_rating'))['avg']
    reviewer_analytics.average_rating_given = avg_given
    reviewer_analytics.save()
    
    # Update reviewee analytics
    reviewee_analytics, created = ReviewAnalytics.objects.get_or_create(
        user=reviewee,
        date=today,
        defaults={
            'reviews_given': 0,
            'reviews_received': 0
        }
    )
    reviewee_analytics.reviews_received += 1
    
    # Calculate average rating received
    avg_received = Review.objects.filter(
        reviewee=reviewee,
        status='approved'
    ).aggregate(avg=Avg('overall_rating'))['avg']
    reviewee_analytics.average_rating_received = avg_received
    reviewee_analytics.save()
