from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
from typing import List, Optional, Dict, Any
import logging

from ..models import (
    Promotion, PromotionUsage, ReferralProgram, Referral,
    LoyaltyProgram, LoyaltyAccount, PromotionCampaign,
    PromotionAnalytics, PromotionStatus, UserType
)
from apps.rides.models import Ride
from core.utils.exceptions import ValidationError

User = get_user_model() 
logger = logging.getLogger(__name__)


class PromotionService:
    """Service for managing promotions and discounts"""
    
    @staticmethod
    def validate_promotion(promotion_code: str, user: User, ride_amount: Decimal) -> Dict[str, Any]:
        """Validate if a promotion can be used by a user"""
        try:
            promotion = Promotion.objects.get(code=promotion_code)
        except Promotion.DoesNotExist:
            return {'valid': False, 'error': 'Invalid promotion code'}
        
        # Check if promotion is active
        if not promotion.is_active:
            return {'valid': False, 'error': 'Promotion is not active'}
        
        # Check minimum ride amount
        if ride_amount < promotion.minimum_ride_amount:
            return {
                'valid': False, 
                'error': f'Minimum ride amount is ${promotion.minimum_ride_amount}'
            }
        
        # Check user type eligibility
        if not PromotionService._check_user_eligibility(promotion, user):
            return {'valid': False, 'error': 'You are not eligible for this promotion'}
        
        # Check usage limits
        user_usage_count = PromotionUsage.objects.filter(
            promotion=promotion, user=user
        ).count()
        
        if user_usage_count >= promotion.usage_limit_per_user:
            return {'valid': False, 'error': 'You have reached the usage limit for this promotion'}
        
        # Check total usage limit
        if promotion.total_usage_limit and promotion.total_usage_count >= promotion.total_usage_limit:
            return {'valid': False, 'error': 'Promotion usage limit reached'}
        
        # Check if user is new and promotion requires first ride
        if promotion.requires_first_ride:
            user_ride_count = Ride.objects.filter(rider=user).count()
            if user_ride_count > 0:
                return {'valid': False, 'error': 'This promotion is only for first-time riders'}
        
        # Calculate discount
        discount_amount = promotion.calculate_discount(ride_amount)
        
        return {
            'valid': True,
            'promotion': promotion,
            'discount_amount': discount_amount,
            'final_amount': ride_amount - discount_amount
        }
    
    @staticmethod
    def apply_promotion(promotion_code: str, user: User, ride: Ride) -> Dict[str, Any]:
        """Apply a promotion to a ride"""
        validation_result = PromotionService.validate_promotion(
            promotion_code, user, ride.total_amount
        )
        
        if not validation_result['valid']:
            return validation_result
        
        promotion = validation_result['promotion']
        discount_amount = validation_result['discount_amount']
        final_amount = validation_result['final_amount']
        
        try:
            with transaction.atomic():
                # Create promotion usage record
                usage = PromotionUsage.objects.create(
                    promotion=promotion,
                    user=user,
                    ride=ride,
                    discount_amount=discount_amount,
                    original_amount=ride.total_amount,
                    final_amount=final_amount
                )
                
                # Update promotion statistics
                promotion.total_usage_count += 1
                promotion.total_discount_given += discount_amount
                promotion.save()
                
                # Update ride amount
                ride.discount_amount = discount_amount
                ride.final_amount = final_amount
                ride.promotion_code = promotion_code
                ride.save()
                
                logger.info(f"Promotion {promotion_code} applied to ride {ride.id} for user {user.id}")
                
                return {
                    'success': True,
                    'usage': usage,
                    'discount_amount': discount_amount,
                    'final_amount': final_amount
                }
                
        except Exception as e:
            logger.error(f"Error applying promotion {promotion_code}: {str(e)}")
            return {'success': False, 'error': 'Failed to apply promotion'}
    
    @staticmethod
    def get_available_promotions(user: User, ride_amount: Decimal = None) -> List[Promotion]:
        """Get all available promotions for a user"""
        now = timezone.now()
        
        # Base queryset for active promotions
        promotions = Promotion.objects.filter(
            status=PromotionStatus.ACTIVE,
            start_date__lte=now,
            end_date__gte=now
        )
        
        # Filter by user eligibility
        eligible_promotions = []
        for promotion in promotions:
            if PromotionService._check_user_eligibility(promotion, user):
                # Check usage limits
                user_usage_count = PromotionUsage.objects.filter(
                    promotion=promotion, user=user
                ).count()
                
                if user_usage_count < promotion.usage_limit_per_user:
                    # Check total usage limit
                    if not promotion.total_usage_limit or promotion.total_usage_count < promotion.total_usage_limit:
                        # Check minimum ride amount if provided
                        if not ride_amount or ride_amount >= promotion.minimum_ride_amount:
                            eligible_promotions.append(promotion)
        
        return eligible_promotions
    
    @staticmethod
    def get_auto_apply_promotions(user: User, ride_amount: Decimal) -> List[Promotion]:
        """Get promotions that should be automatically applied"""
        available_promotions = PromotionService.get_available_promotions(user, ride_amount)
        return [p for p in available_promotions if p.is_auto_apply]
    
    @staticmethod
    def _check_user_eligibility(promotion: Promotion, user: User) -> bool:
        """Check if user is eligible for a promotion"""
        # Check user type
        if promotion.target_user_type == UserType.NEW:
            # Check if user is new (registered within last 30 days)
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            if user.date_joined < thirty_days_ago:
                return False
        elif promotion.target_user_type == UserType.EXISTING:
            # Check if user is existing (registered more than 30 days ago)
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            if user.date_joined >= thirty_days_ago:
                return False
        elif promotion.target_user_type == UserType.RIDERS:
            if not hasattr(user, 'rider_profile'):
                return False
        elif promotion.target_user_type == UserType.DRIVERS:
            if not hasattr(user, 'driver_profile'):
                return False
        elif promotion.target_user_type == UserType.VIP:
            # Check if user has VIP status (could be based on ride count, spending, etc.)
            if not getattr(user, 'is_vip', False):
                return False
        
        # Check city targeting
        if promotion.target_cities.exists():
            user_city = getattr(user, 'city', None)
            if not user_city or user_city not in promotion.target_cities.all():
                return False
        
        return True
    
    @staticmethod
    def calculate_promotion_roi(promotion: Promotion) -> Dict[str, Any]:
        """Calculate return on investment for a promotion"""
        total_discount = promotion.total_discount_given
        total_revenue = promotion.total_revenue_impact
        
        if total_discount > 0:
            roi = ((total_revenue - total_discount) / total_discount) * 100
        else:
            roi = 0
        
        return {
            'total_discount_given': total_discount,
            'total_revenue_generated': total_revenue,
            'roi_percentage': roi,
            'total_usage_count': promotion.total_usage_count
        }
    
    @staticmethod
    def get_promotion_analytics(promotion: Promotion, start_date=None, end_date=None) -> Dict[str, Any]:
        """Get detailed analytics for a promotion"""
        if not start_date:
            start_date = promotion.start_date.date()
        if not end_date:
            end_date = timezone.now().date()
        
        analytics = PromotionAnalytics.objects.filter(
            promotion=promotion,
            date__range=[start_date, end_date]
        ).aggregate(
            total_uses=models.Sum('total_uses'),
            total_unique_users=models.Sum('unique_users'),
            total_discount=models.Sum('total_discount_given'),
            total_revenue=models.Sum('total_revenue_generated'),
            avg_conversion_rate=models.Avg('conversion_rate')
        )
        
        return {
            'promotion': promotion,
            'period': {'start': start_date, 'end': end_date},
            'metrics': analytics,
            'roi': PromotionService.calculate_promotion_roi(promotion)
        }


class ReferralService:
    """Service for managing referral programs"""
    
    @staticmethod
    def create_referral(referrer: User, referee_phone: str, program: ReferralProgram) -> Dict[str, Any]:
        """Create a new referral"""
        try:
            # Check if referrer has reached max referrals
            if program.max_referrals_per_user:
                referrer_count = Referral.objects.filter(
                    referrer=referrer, program=program
                ).count()
                if referrer_count >= program.max_referrals_per_user:
                    return {'success': False, 'error': 'Maximum referrals reached'}
            
            # Check if program has reached max total referrals
            if program.max_total_referrals:
                total_count = Referral.objects.filter(program=program).count()
                if total_count >= program.max_total_referrals:
                    return {'success': False, 'error': 'Referral program limit reached'}
            
            # Generate unique referral code
            referral_code = f"REF{referrer.id}{timezone.now().strftime('%Y%m%d%H%M%S')}"
            
            # Calculate expiry date
            expiry_date = timezone.now() + timezone.timedelta(days=program.reward_expiry_days)
            
            # Create referral record (referee will be linked when they sign up)
            referral = Referral.objects.create(
                program=program,
                referrer=referrer,
                referral_code=referral_code,
                expiry_date=expiry_date
            )
            
            return {
                'success': True,
                'referral': referral,
                'referral_code': referral_code
            }
            
        except Exception as e:
            logger.error(f"Error creating referral: {str(e)}")
            return {'success': False, 'error': 'Failed to create referral'}
    
    @staticmethod
    def process_referral_signup(referral_code: str, referee: User) -> Dict[str, Any]:
        """Process when a referred user signs up"""
        try:
            referral = Referral.objects.get(
                referral_code=referral_code,
                status=Referral.ReferralStatus.PENDING
            )
            
            # Check if referral is still valid
            if timezone.now() > referral.expiry_date:
                referral.status = Referral.ReferralStatus.EXPIRED
                referral.save()
                return {'success': False, 'error': 'Referral code has expired'}
            
            # Link referee to referral
            referral.referee = referee
            referral.save()
            
            return {'success': True, 'referral': referral}
            
        except Referral.DoesNotExist:
            return {'success': False, 'error': 'Invalid referral code'}
        except Exception as e:
            logger.error(f"Error processing referral signup: {str(e)}")
            return {'success': False, 'error': 'Failed to process referral'}
    
    @staticmethod
    def complete_referral(referral: Referral) -> Dict[str, Any]:
        """Complete referral when referee meets requirements"""
        try:
            with transaction.atomic():
                # Check if referee has completed required rides
                referee_rides = Ride.objects.filter(
                    rider=referral.referee,
                    status='completed'
                ).count()
                
                if referee_rides < referral.program.minimum_rides_for_referee:
                    return {
                        'success': False, 
                        'error': f'Referee needs {referral.program.minimum_rides_for_referee} completed rides'
                    }
                
                # Check if referrer has completed required rides
                referrer_rides = Ride.objects.filter(
                    rider=referral.referrer,
                    status='completed'
                ).count()
                
                if referrer_rides < referral.program.minimum_rides_for_referrer:
                    return {
                        'success': False, 
                        'error': f'Referrer needs {referral.program.minimum_rides_for_referrer} completed rides'
                    }
                
                # Mark referral as completed
                referral.status = Referral.ReferralStatus.COMPLETED
                referral.completion_date = timezone.now()
                referral.save()
                
                # Award rewards (this would integrate with wallet service)
                # For now, just record the amounts
                referral.referrer_reward_given = referral.program.referrer_reward_amount
                referral.referee_reward_given = referral.program.referee_reward_amount
                referral.status = Referral.ReferralStatus.REWARDED
                referral.reward_date = timezone.now()
                referral.save()
                
                return {
                    'success': True,
                    'referral': referral,
                    'referrer_reward': referral.referrer_reward_given,
                    'referee_reward': referral.referee_reward_given
                }
                
        except Exception as e:
            logger.error(f"Error completing referral: {str(e)}")
            return {'success': False, 'error': 'Failed to complete referral'}


class LoyaltyService:
    """Service for managing loyalty programs"""
    
    @staticmethod
    def get_or_create_loyalty_account(user: User, program: LoyaltyProgram) -> LoyaltyAccount:
        """Get or create loyalty account for user"""
        account, created = LoyaltyAccount.objects.get_or_create(
            user=user,
            program=program,
            defaults={
                'total_points_earned': 0,
                'total_points_redeemed': 0,
                'current_points_balance': 0,
                'tier_level': LoyaltyAccount.TierLevel.BRONZE,
                'tier_progress': 0,
                'total_rides_count': 0,
                'total_amount_spent': Decimal('0.00')
            }
        )
        return account
    
    @staticmethod
    def award_points(user: User, ride: Ride, program: LoyaltyProgram) -> Dict[str, Any]:
        """Award loyalty points for a completed ride"""
        try:
            account = LoyaltyService.get_or_create_loyalty_account(user, program)
            
            # Calculate points
            points_from_amount = int(ride.final_amount * program.points_per_dollar)
            points_from_ride = program.points_per_ride
            
            # Check for bonus points
            current_month_rides = Ride.objects.filter(
                rider=user,
                status='completed',
                created_at__month=timezone.now().month,
                created_at__year=timezone.now().year
            ).count()
            
            bonus_multiplier = 1
            if current_month_rides >= program.bonus_points_threshold:
                bonus_multiplier = float(program.bonus_points_multiplier)
            
            total_points = int((points_from_amount + points_from_ride) * bonus_multiplier)
            
            # Update account
            account.total_points_earned += total_points
            account.current_points_balance += total_points
            account.total_rides_count += 1
            account.total_amount_spent += ride.final_amount
            
            # Update tier if necessary
            LoyaltyService._update_tier(account)
            
            account.save()
            
            return {
                'success': True,
                'points_awarded': total_points,
                'total_balance': account.current_points_balance,
                'tier_level': account.tier_level
            }
            
        except Exception as e:
            logger.error(f"Error awarding loyalty points: {str(e)}")
            return {'success': False, 'error': 'Failed to award points'}
    
    @staticmethod
    def redeem_points(user: User, points_to_redeem: int, program: LoyaltyProgram) -> Dict[str, Any]:
        """Redeem loyalty points for discount"""
        try:
            account = LoyaltyService.get_or_create_loyalty_account(user, program)
            
            # Check minimum redemption
            if points_to_redeem < program.minimum_redemption_points:
                return {
                    'success': False, 
                    'error': f'Minimum redemption is {program.minimum_redemption_points} points'
                }
            
            # Check available balance
            if points_to_redeem > account.current_points_balance:
                return {'success': False, 'error': 'Insufficient points balance'}
            
            # Calculate dollar value
            dollar_value = points_to_redeem / program.points_to_dollar_ratio
            
            # Update account
            account.current_points_balance -= points_to_redeem
            account.total_points_redeemed += points_to_redeem
            account.save()
            
            return {
                'success': True,
                'points_redeemed': points_to_redeem,
                'dollar_value': dollar_value,
                'remaining_balance': account.current_points_balance
            }
            
        except Exception as e:
            logger.error(f"Error redeeming loyalty points: {str(e)}")
            return {'success': False, 'error': 'Failed to redeem points'}
    
    @staticmethod
    def _update_tier(account: LoyaltyAccount):
        """Update user tier based on activity"""
        # Simple tier calculation based on total rides
        if account.total_rides_count >= 500:
            account.tier_level = LoyaltyAccount.TierLevel.DIAMOND
        elif account.total_rides_count >= 200:
            account.tier_level = LoyaltyAccount.TierLevel.PLATINUM
        elif account.total_rides_count >= 100:
            account.tier_level = LoyaltyAccount.TierLevel.GOLD
        elif account.total_rides_count >= 50:
            account.tier_level = LoyaltyAccount.TierLevel.SILVER
        else:
            account.tier_level = LoyaltyAccount.TierLevel.BRONZE
