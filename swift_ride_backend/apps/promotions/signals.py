from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import PromotionUsage, Referral, LoyaltyAccount
from apps.rides.models import Ride


@receiver(post_save, sender=PromotionUsage)
def update_promotion_analytics(sender, instance, created, **kwargs):
    """Update promotion analytics when usage is created"""
    if created:
        promotion = instance.promotion
        
        # Update promotion totals
        promotion.total_usage_count += 1
        promotion.total_discount_given += instance.discount_amount
        promotion.total_revenue_impact += instance.final_amount
        promotion.save()


@receiver(post_save, sender=Ride)
def process_loyalty_points(sender, instance, created, **kwargs):
    """Award loyalty points when ride is completed"""
    if not created and instance.status == 'completed':
        from .services.promotion_service import LoyaltyService
        from .models import LoyaltyProgram
        
        # Get active loyalty program
        try:
            program = LoyaltyProgram.objects.filter(is_active=True).first()
            if program:
                LoyaltyService.award_points(
                    user=instance.rider,
                    ride=instance,
                    program=program
                )
        except Exception as e:
            # Log error but don't fail the ride completion
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error awarding loyalty points: {str(e)}")


@receiver(post_save, sender=Ride)
def check_referral_completion(sender, instance, created, **kwargs):
    """Check if referral should be completed when ride is finished"""
    if not created and instance.status == 'completed':
        from .services.promotion_service import ReferralService
        
        # Check if this user has any pending referrals as referee
        pending_referrals = Referral.objects.filter(
            referee=instance.rider,
            status=Referral.ReferralStatus.PENDING
        )
        
        for referral in pending_referrals:
            try:
                ReferralService.complete_referral(referral)
            except Exception as e:
                # Log error but don't fail the ride completion
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error completing referral: {str(e)}")


@receiver(pre_save, sender=Referral)
def set_referral_expiry(sender, instance, **kwargs):
    """Set referral expiry date if not set"""
    if not instance.expiry_date and instance.program:
        instance.expiry_date = timezone.now() + timezone.timedelta(
            days=instance.program.reward_expiry_days
        )
