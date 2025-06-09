from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.common.models import BaseModel
from apps.users.models import CustomUser as  User
from apps.rides.models import Ride


class ReviewCategory(BaseModel):
    """Categories for different types of reviews"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Review Category'
        verbose_name_plural = 'Review Categories'

    def __str__(self):
        return self.name


class Review(BaseModel):
    """Main review model for drivers and riders"""
    REVIEW_TYPES = [
        ('driver_review', 'Driver Review'),
        ('rider_review', 'Rider Review'),
        ('platform_review', 'Platform Review'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('flagged', 'Flagged'),
    ]

    # Core fields
    ride = models.ForeignKey(Ride, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    reviewee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    review_type = models.CharField(max_length=20, choices=REVIEW_TYPES)
    
    # Rating and content
    overall_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    title = models.CharField(max_length=200, blank=True)
    comment = models.TextField(blank=True)
    
    # Category ratings
    categories = models.ManyToManyField(ReviewCategory, through='ReviewRating', blank=True)
    
    # Status and moderation
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_anonymous = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    # Moderation fields
    moderated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='moderated_reviews'
    )
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderation_notes = models.TextField(blank=True)
    
    # Engagement metrics
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    report_count = models.PositiveIntegerField(default=0)
    
    # Response from reviewee
    response = models.TextField(blank=True)
    response_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['ride', 'reviewer', 'reviewee']
        indexes = [
            models.Index(fields=['reviewee', 'status']),
            models.Index(fields=['review_type', 'status']),
            models.Index(fields=['overall_rating']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.reviewer.get_full_name()} -> {self.reviewee.get_full_name()} ({self.overall_rating}★)"

    @property
    def average_category_rating(self):
        """Calculate average rating across all categories"""
        ratings = self.review_ratings.all()
        if not ratings:
            return self.overall_rating
        return sum(rating.rating for rating in ratings) / len(ratings)

    def can_be_edited(self):
        """Check if review can still be edited"""
        from django.utils import timezone
        from datetime import timedelta
        
        edit_window = timezone.now() - timedelta(hours=24)
        return self.created_at > edit_window and self.status == 'pending'


class ReviewRating(BaseModel):
    """Individual category ratings within a review"""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='review_ratings')
    category = models.ForeignKey(ReviewCategory, on_delete=models.CASCADE)
    rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )

    class Meta:
        unique_together = ['review', 'category']

    def __str__(self):
        return f"{self.review} - {self.category.name}: {self.rating}★"


class ReviewHelpfulness(BaseModel):
    """Track user votes on review helpfulness"""
    VOTE_CHOICES = [
        ('helpful', 'Helpful'),
        ('not_helpful', 'Not Helpful'),
    ]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpfulness_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vote = models.CharField(max_length=20, choices=VOTE_CHOICES)

    class Meta:
        unique_together = ['review', 'user']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.vote}"


class ReviewReport(BaseModel):
    """Reports for inappropriate reviews"""
    REPORT_REASONS = [
        ('inappropriate', 'Inappropriate Content'),
        ('spam', 'Spam'),
        ('fake', 'Fake Review'),
        ('harassment', 'Harassment'),
        ('discrimination', 'Discrimination'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('dismissed', 'Dismissed'),
    ]

    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Resolution fields
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_review_reports'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['review', 'reporter']

    def __str__(self):
        return f"Report: {self.review} - {self.reason}"


class ReviewTemplate(BaseModel):
    """Pre-defined review templates for quick reviews"""
    TEMPLATE_TYPES = [
        ('positive', 'Positive'),
        ('neutral', 'Neutral'),
        ('negative', 'Negative'),
    ]

    title = models.CharField(max_length=200)
    content = models.TextField()
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)
    suggested_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    is_active = models.BooleanField(default=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['template_type', 'suggested_rating']

    def __str__(self):
        return f"{self.title} ({self.template_type})"


class ReviewAnalytics(BaseModel):
    """Analytics data for reviews"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_analytics')
    date = models.DateField()
    
    # Review counts
    reviews_given = models.PositiveIntegerField(default=0)
    reviews_received = models.PositiveIntegerField(default=0)
    
    # Rating averages
    average_rating_given = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    average_rating_received = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    
    # Engagement metrics
    helpful_votes_received = models.PositiveIntegerField(default=0)
    reports_received = models.PositiveIntegerField(default=0)
    
    # Quality metrics
    review_response_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    average_review_length = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.date}"


class ReviewIncentive(BaseModel):
    """Incentives for leaving reviews"""
    INCENTIVE_TYPES = [
        ('discount', 'Discount'),
        ('points', 'Loyalty Points'),
        ('credit', 'Ride Credit'),
        ('badge', 'Achievement Badge'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    incentive_type = models.CharField(max_length=20, choices=INCENTIVE_TYPES)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Conditions
    minimum_rating = models.DecimalField(
        max_digits=3, 
        decimal_places=2,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)],
        null=True,
        blank=True
    )
    minimum_comment_length = models.PositiveIntegerField(default=0)
    requires_categories = models.BooleanField(default=False)
    
    # Validity
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(null=True, blank=True)
    usage_limit = models.PositiveIntegerField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.incentive_type})"

    def is_valid(self):
        """Check if incentive is currently valid"""
        from django.utils import timezone
        now = timezone.now()
        
        if not self.is_active:
            return False
        
        if self.valid_from > now:
            return False
        
        if self.valid_until and self.valid_until < now:
            return False
        
        if self.usage_limit and self.usage_count >= self.usage_limit:
            return False
        
        return True


class ReviewIncentiveUsage(BaseModel):
    """Track usage of review incentives"""
    incentive = models.ForeignKey(ReviewIncentive, on_delete=models.CASCADE, related_name='usages')
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='incentive_usages')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='review_incentive_usages')
    value_awarded = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ['incentive', 'review']

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.incentive.name}"
