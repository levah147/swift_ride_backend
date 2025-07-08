from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import uuid

from apps.common.models import BaseModel

User = get_user_model()


class PromotionType(models.TextChoices):
    DISCOUNT = 'discount', 'Discount'
    REFERRAL = 'referral', 'Referral'
    COUPON = 'coupon', 'Coupon'
    CASHBACK = 'cashback', 'Cashback'
    FREE_RIDE = 'free_ride', 'Free Ride'
    LOYALTY = 'loyalty', 'Loyalty'


class DiscountType(models.TextChoices):
    PERCENTAGE = 'percentage', 'Percentage'
    FIXED_AMOUNT = 'fixed_amount', 'Fixed Amount'
    FREE_DELIVERY = 'free_delivery', 'Free Delivery'


class PromotionStatus(models.TextChoices):
    DRAFT = 'draft', 'Draft'
    ACTIVE = 'active', 'Active'
    PAUSED = 'paused', 'Paused'
    EXPIRED = 'expired', 'Expired'
    CANCELLED = 'cancelled', 'Cancelled'


class UserType(models.TextChoices):
    ALL = 'all', 'All Users'
    NEW = 'new', 'New Users'
    EXISTING = 'existing', 'Existing Users'
    RIDERS = 'riders', 'Riders Only'
    DRIVERS = 'drivers', 'Drivers Only'
    VIP = 'vip', 'VIP Users'


class Promotion(BaseModel):
    """Main promotion model for all types of promotions"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    promotion_type = models.CharField(max_length=20, choices=PromotionType.choices)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    status = models.CharField(max_length=20, choices=PromotionStatus.choices, default=PromotionStatus.DRAFT)
    
    # Promotion code
    code = models.CharField(max_length=50, unique=True, null=True, blank=True)
    
    # Discount values
    discount_percentage = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Usage limits
    usage_limit_per_user = models.PositiveIntegerField(default=1)
    total_usage_limit = models.PositiveIntegerField(null=True, blank=True)
    minimum_ride_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)]
    )
    
    # Time constraints
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Target audience
    target_user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.ALL)
    target_cities = models.ManyToManyField('location.City', blank=True)
    target_vehicle_types = models.ManyToManyField('vehicles.VehicleType', blank=True)
    
    # Referral specific fields
    referrer_reward_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    referee_reward_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Analytics
    total_usage_count = models.PositiveIntegerField(default=0)
    total_discount_given = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_revenue_impact = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Settings
    is_stackable = models.BooleanField(default=False)
    is_auto_apply = models.BooleanField(default=False)
    requires_first_ride = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'promotions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status', 'start_date', 'end_date']),
            models.Index(fields=['promotion_type']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code})"

    @property
    def is_active(self):
        now = timezone.now()
        return (
            self.status == PromotionStatus.ACTIVE and
            self.start_date <= now <= self.end_date
        )

    @property
    def usage_remaining(self):
        if self.total_usage_limit:
            return max(0, self.total_usage_limit - self.total_usage_count)
        return float('inf')

    def calculate_discount(self, ride_amount):
        """Calculate discount amount for a given ride amount"""
        if self.discount_type == DiscountType.PERCENTAGE:
            discount = ride_amount * (self.discount_percentage / 100)
            if self.max_discount_amount:
                discount = min(discount, self.max_discount_amount)
            return discount
        elif self.discount_type == DiscountType.FIXED_AMOUNT:
            return min(self.discount_amount, ride_amount)
        return Decimal('0.00')


class PromotionUsage(BaseModel):
    """Track promotion usage by users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='promotion_usages')
    ride = models.ForeignKey('rides.Ride', on_delete=models.CASCADE, null=True, blank=True)
    
    # Usage details
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Metadata
    usage_date = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'promotion_usages'
        ordering = ['-usage_date']
        indexes = [
            models.Index(fields=['promotion', 'user']),
            models.Index(fields=['usage_date']),
        ]

    def __str__(self):
        return f"{self.user} used {self.promotion.code} - ${self.discount_amount}"


class ReferralProgram(BaseModel):
    """Referral program configuration"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    # Rewards
    referrer_reward_amount = models.DecimalField(max_digits=10, decimal_places=2)
    referee_reward_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Conditions
    minimum_rides_for_referrer = models.PositiveIntegerField(default=0)
    minimum_rides_for_referee = models.PositiveIntegerField(default=1)
    reward_expiry_days = models.PositiveIntegerField(default=30)
    
    # Limits
    max_referrals_per_user = models.PositiveIntegerField(null=True, blank=True)
    max_total_referrals = models.PositiveIntegerField(null=True, blank=True)
    
    # Time constraints
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'referral_programs'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class Referral(BaseModel):
    """Individual referral tracking"""
    
    class ReferralStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'
        REWARDED = 'rewarded', 'Rewarded'
        EXPIRED = 'expired', 'Expired'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(ReferralProgram, on_delete=models.CASCADE, related_name='referrals')
    referrer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_made')
    referee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referrals_received')
    
    # Referral details
    referral_code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=ReferralStatus.choices, default=ReferralStatus.PENDING)
    
    # Tracking
    signup_date = models.DateTimeField(auto_now_add=True)
    completion_date = models.DateTimeField(null=True, blank=True)
    reward_date = models.DateTimeField(null=True, blank=True)
    expiry_date = models.DateTimeField()
    
    # Rewards
    referrer_reward_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    referee_reward_given = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'referrals'
        ordering = ['-signup_date']
        unique_together = ['referrer', 'referee']
        indexes = [
            models.Index(fields=['referral_code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.referrer} referred {self.referee}"


class LoyaltyProgram(BaseModel):
    """Loyalty program for frequent users"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    
    # Point system
    points_per_dollar = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    points_per_ride = models.PositiveIntegerField(default=10)
    bonus_points_threshold = models.PositiveIntegerField(default=100)  # Rides per month
    bonus_points_multiplier = models.DecimalField(max_digits=3, decimal_places=2, default=1.5)
    
    # Redemption
    points_to_dollar_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=100)  # 100 points = $1
    minimum_redemption_points = models.PositiveIntegerField(default=500)
    
    class Meta:
        db_table = 'loyalty_programs'
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class LoyaltyAccount(BaseModel):
    """User loyalty account"""
    
    class TierLevel(models.TextChoices):
        BRONZE = 'bronze', 'Bronze'
        SILVER = 'silver', 'Silver'
        GOLD = 'gold', 'Gold'
        PLATINUM = 'platinum', 'Platinum'
        DIAMOND = 'diamond', 'Diamond'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='loyalty_account')
    program = models.ForeignKey(LoyaltyProgram, on_delete=models.CASCADE, related_name='accounts')
    
    # Points
    total_points_earned = models.PositiveIntegerField(default=0)
    total_points_redeemed = models.PositiveIntegerField(default=0)
    current_points_balance = models.PositiveIntegerField(default=0)
    
    # Tier
    tier_level = models.CharField(max_length=20, choices=TierLevel.choices, default=TierLevel.BRONZE)
    tier_progress = models.PositiveIntegerField(default=0)  # Progress towards next tier
    
    # Statistics
    total_rides_count = models.PositiveIntegerField(default=0)
    total_amount_spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'loyalty_accounts'
        unique_together = ['user', 'program']

    def __str__(self):
        return f"{self.user} - {self.tier_level} ({self.current_points_balance} points)"

    @property
    def available_balance_dollars(self):
        """Convert points to dollar value"""
        return self.current_points_balance / self.program.points_to_dollar_ratio


class PromotionCampaign(BaseModel):
    """Marketing campaign management"""
    
    class CampaignType(models.TextChoices):
        EMAIL = 'email', 'Email Campaign'
        PUSH = 'push', 'Push Notification'
        SMS = 'sms', 'SMS Campaign'
        IN_APP = 'in_app', 'In-App Banner'
        SOCIAL = 'social', 'Social Media'
    
    class CampaignStatus(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SCHEDULED = 'scheduled', 'Scheduled'
        RUNNING = 'running', 'Running'
        PAUSED = 'paused', 'Paused'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    campaign_type = models.CharField(max_length=20, choices=CampaignType.choices)
    status = models.CharField(max_length=20, choices=CampaignStatus.choices, default=CampaignStatus.DRAFT)
    
    # Associated promotion
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='campaigns')
    
    # Targeting
    target_user_type = models.CharField(max_length=20, choices=UserType.choices, default=UserType.ALL)
    target_cities = models.ManyToManyField('location.City', blank=True)
    target_age_min = models.PositiveIntegerField(null=True, blank=True)
    target_age_max = models.PositiveIntegerField(null=True, blank=True)
    
    # Campaign content
    subject = models.CharField(max_length=200, null=True, blank=True)
    message = models.TextField()
    image_url = models.URLField(null=True, blank=True)
    call_to_action = models.CharField(max_length=100, null=True, blank=True)
    
    # Scheduling
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(null=True, blank=True)
    
    # Analytics
    target_audience_size = models.PositiveIntegerField(default=0)
    messages_sent = models.PositiveIntegerField(default=0)
    messages_delivered = models.PositiveIntegerField(default=0)
    messages_opened = models.PositiveIntegerField(default=0)
    messages_clicked = models.PositiveIntegerField(default=0)
    conversions = models.PositiveIntegerField(default=0)
    
    class Meta:
        db_table = 'promotion_campaigns'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.campaign_type}"

    @property
    def delivery_rate(self):
        if self.messages_sent > 0:
            return (self.messages_delivered / self.messages_sent) * 100
        return 0

    @property
    def open_rate(self):
        if self.messages_delivered > 0:
            return (self.messages_opened / self.messages_delivered) * 100
        return 0

    @property
    def click_rate(self):
        if self.messages_opened > 0:
            return (self.messages_clicked / self.messages_opened) * 100
        return 0

    @property
    def conversion_rate(self):
        if self.messages_clicked > 0:
            return (self.conversions / self.messages_clicked) * 100
        return 0


class PromotionAnalytics(BaseModel):
    """Daily promotion analytics"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE, related_name='analytics')
    date = models.DateField()
    
    # Usage metrics
    total_uses = models.PositiveIntegerField(default=0)
    unique_users = models.PositiveIntegerField(default=0)
    new_users = models.PositiveIntegerField(default=0)
    returning_users = models.PositiveIntegerField(default=0)
    
    # Financial metrics
    total_discount_given = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_revenue_generated = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Performance metrics
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cost_per_acquisition = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    return_on_investment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        db_table = 'promotion_analytics'
        unique_together = ['promotion', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.promotion.name} - {self.date}"
