from celery import shared_task
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from datetime import date, timedelta
import logging

from .models import (
    Promotion, PromotionUsage, Referral, PromotionAnalytics,
    PromotionCampaign, PromotionStatus
)
from .services.campaign_service import CampaignService

logger = logging.getLogger(__name__)


@shared_task
def update_promotion_analytics():
    """Update daily promotion analytics"""
    try:
        yesterday = date.today() - timedelta(days=1)
        
        # Get all active promotions
        promotions = Promotion.objects.filter(status=PromotionStatus.ACTIVE)
        
        for promotion in promotions:
            # Get usage data for yesterday
            usage_data = PromotionUsage.objects.filter(
                promotion=promotion,
                usage_date__date=yesterday
            ).aggregate(
                total_uses=Count('id'),
                unique_users=Count('user', distinct=True),
                total_discount=Sum('discount_amount'),
                total_revenue=Sum('final_amount'),
                avg_order_value=Avg('final_amount')
            )
            
            # Create or update analytics record
            analytics, created = PromotionAnalytics.objects.get_or_create(
                promotion=promotion,
                date=yesterday,
                defaults={
                    'total_uses': usage_data['total_uses'] or 0,
                    'unique_users': usage_data['unique_users'] or 0,
                    'total_discount_given': usage_data['total_discount'] or 0,
                    'total_revenue_generated': usage_data['total_revenue'] or 0,
                    'average_order_value': usage_data['avg_order_value'] or 0
                }
            )
            
            if not created:
                # Update existing record
                analytics.total_uses = usage_data['total_uses'] or 0
                analytics.unique_users = usage_data['unique_users'] or 0
                analytics.total_discount_given = usage_data['total_discount'] or 0
                analytics.total_revenue_generated = usage_data['total_revenue'] or 0
                analytics.average_order_value = usage_data['avg_order_value'] or 0
                analytics.save()
        
        logger.info(f"Updated promotion analytics for {yesterday}")
        
    except Exception as e:
        logger.error(f"Error updating promotion analytics: {str(e)}")


@shared_task
def expire_promotions():
    """Mark expired promotions as expired"""
    try:
        now = timezone.now()
        expired_count = Promotion.objects.filter(
            status=PromotionStatus.ACTIVE,
            end_date__lt=now
        ).update(status=PromotionStatus.EXPIRED)
        
        logger.info(f"Expired {expired_count} promotions")
        
    except Exception as e:
        logger.error(f"Error expiring promotions: {str(e)}")


@shared_task
def expire_referrals():
    """Mark expired referrals as expired"""
    try:
        now = timezone.now()
        expired_count = Referral.objects.filter(
            status=Referral.ReferralStatus.PENDING,
            expiry_date__lt=now
        ).update(status=Referral.ReferralStatus.EXPIRED)
        
        logger.info(f"Expired {expired_count} referrals")
        
    except Exception as e:
        logger.error(f"Error expiring referrals: {str(e)}")


@shared_task
def launch_scheduled_campaigns():
    """Launch campaigns that are scheduled to start"""
    try:
        now = timezone.now()
        scheduled_campaigns = PromotionCampaign.objects.filter(
            status=PromotionCampaign.CampaignStatus.SCHEDULED,
            scheduled_start__lte=now
        )
        
        launched_count = 0
        for campaign in scheduled_campaigns:
            result = CampaignService.launch_campaign(campaign)
            if result.get('success'):
                launched_count += 1
        
        logger.info(f"Launched {launched_count} scheduled campaigns")
        
    except Exception as e:
        logger.error(f"Error launching scheduled campaigns: {str(e)}")


@shared_task
def complete_campaigns():
    """Mark completed campaigns as completed"""
    try:
        now = timezone.now()
        completed_count = PromotionCampaign.objects.filter(
            status=PromotionCampaign.CampaignStatus.RUNNING,
            scheduled_end__lt=now
        ).update(status=PromotionCampaign.CampaignStatus.COMPLETED)
        
        logger.info(f"Completed {completed_count} campaigns")
        
    except Exception as e:
        logger.error(f"Error completing campaigns: {str(e)}")


@shared_task
def cleanup_old_analytics():
    """Clean up old analytics data (older than 2 years)"""
    try:
        cutoff_date = date.today() - timedelta(days=730)  # 2 years
        deleted_count = PromotionAnalytics.objects.filter(
            date__lt=cutoff_date
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old analytics records")
        
    except Exception as e:
        logger.error(f"Error cleaning up old analytics: {str(e)}")


@shared_task
def send_promotion_reminders():
    """Send reminders for promotions about to expire"""
    try:
        # Get promotions expiring in 24 hours
        tomorrow = timezone.now() + timedelta(days=1)
        expiring_promotions = Promotion.objects.filter(
            status=PromotionStatus.ACTIVE,
            end_date__date=tomorrow.date()
        )
        
        from apps.notifications.services.notification_service import NotificationService
        
        for promotion in expiring_promotions:
            # Get users who have used this promotion
            users = PromotionUsage.objects.filter(
                promotion=promotion
            ).values_list('user', flat=True).distinct()
            
            for user_id in users:
                try:
                    from django.contrib.auth import get_user_model
                    User = get_user_model()
                    user = User.objects.get(id=user_id)
                    
                    NotificationService.create_notification(
                        user=user,
                        title="Promotion Expiring Soon!",
                        message=f"Your promotion '{promotion.name}' expires tomorrow. Use it before it's gone!",
                        notification_type='promotion_reminder',
                        data={'promotion_code': promotion.code}
                    )
                except Exception as e:
                    logger.error(f"Error sending reminder to user {user_id}: {str(e)}")
        
        logger.info(f"Sent reminders for {len(expiring_promotions)} expiring promotions")
        
    except Exception as e:
        logger.error(f"Error sending promotion reminders: {str(e)}")
