from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from apps.reviews.models import (
    Review, ReviewCategory, ReviewRating, ReviewHelpfulness,
    ReviewReport, ReviewTemplate, ReviewAnalytics, ReviewIncentive,
    ReviewIncentiveUsage
)


@admin.register(ReviewCategory)
class ReviewCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']


class ReviewRatingInline(admin.TabularInline):
    model = ReviewRating
    extra = 0
    readonly_fields = ['created_at']


class ReviewHelpfulnessInline(admin.TabularInline):
    model = ReviewHelpfulness
    extra = 0
    readonly_fields = ['user', 'vote', 'created_at']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'reviewer_link', 'reviewee_link', 'review_type',
        'overall_rating', 'status', 'helpful_count', 'report_count',
        'created_at'
    ]
    list_filter = [
        'review_type', 'status', 'overall_rating', 'is_anonymous',
        'is_featured', 'created_at'
    ]
    search_fields = [
        'reviewer__first_name', 'reviewer__last_name',
        'reviewee__first_name', 'reviewee__last_name',
        'title', 'comment'
    ]
    readonly_fields = [
        'reviewer', 'reviewee', 'ride', 'helpful_count',
        'not_helpful_count', 'report_count', 'created_at', 'updated_at'
    ]
    inlines = [ReviewRatingInline, ReviewHelpfulnessInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': (
                'reviewer', 'reviewee', 'ride', 'review_type',
                'overall_rating', 'title', 'comment'
            )
        }),
        ('Status & Moderation', {
            'fields': (
                'status', 'is_anonymous', 'is_featured',
                'moderated_by', 'moderated_at', 'moderation_notes'
            )
        }),
        ('Engagement', {
            'fields': (
                'helpful_count', 'not_helpful_count', 'report_count'
            )
        }),
        ('Response', {
            'fields': ('response', 'response_date')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )

    def reviewer_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.reviewer.id])
        return format_html('<a href="{}">{}</a>', url, obj.reviewer.get_full_name())
    reviewer_link.short_description = 'Reviewer'

    def reviewee_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.reviewee.id])
        return format_html('<a href="{}">{}</a>', url, obj.reviewee.get_full_name())
    reviewee_link.short_description = 'Reviewee'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'reviewer', 'reviewee', 'ride'
        )


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'review_link', 'reporter_link', 'reason',
        'status', 'created_at', 'resolved_at'
    ]
    list_filter = ['reason', 'status', 'created_at', 'resolved_at']
    search_fields = [
        'reporter__first_name', 'reporter__last_name',
        'description', 'resolution_notes'
    ]
    readonly_fields = ['reporter', 'created_at', 'resolved_at']
    
    fieldsets = (
        ('Report Information', {
            'fields': ('review', 'reporter', 'reason', 'description')
        }),
        ('Status', {
            'fields': ('status', 'created_at')
        }),
        ('Resolution', {
            'fields': (
                'resolved_by', 'resolved_at', 'resolution_notes'
            )
        })
    )

    def review_link(self, obj):
        url = reverse('admin:reviews_review_change', args=[obj.review.id])
        return format_html('<a href="{}">{}</a>', url, f"Review #{obj.review.id}")
    review_link.short_description = 'Review'

    def reporter_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.reporter.id])
        return format_html('<a href="{}">{}</a>', url, obj.reporter.get_full_name())
    reporter_link.short_description = 'Reporter'


@admin.register(ReviewTemplate)
class ReviewTemplateAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'template_type', 'suggested_rating',
        'usage_count', 'is_active', 'created_at'
    ]
    list_filter = ['template_type', 'is_active', 'suggested_rating']
    search_fields = ['title', 'content']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']


@admin.register(ReviewIncentive)
class ReviewIncentiveAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'incentive_type', 'value', 'minimum_rating',
        'usage_count', 'usage_limit', 'is_active', 'valid_from'
    ]
    list_filter = [
        'incentive_type', 'is_active', 'valid_from', 'valid_until'
    ]
    search_fields = ['name', 'description']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'incentive_type', 'value')
        }),
        ('Conditions', {
            'fields': (
                'minimum_rating', 'minimum_comment_length',
                'requires_categories'
            )
        }),
        ('Validity', {
            'fields': (
                'is_active', 'valid_from', 'valid_until',
                'usage_limit', 'usage_count'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )


@admin.register(ReviewIncentiveUsage)
class ReviewIncentiveUsageAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'incentive', 'review_link',
        'value_awarded', 'created_at'
    ]
    list_filter = ['incentive', 'created_at']
    search_fields = [
        'user__first_name', 'user__last_name',
        'incentive__name'
    ]
    readonly_fields = ['created_at']

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_link.short_description = 'User'

    def review_link(self, obj):
        url = reverse('admin:reviews_review_change', args=[obj.review.id])
        return format_html('<a href="{}">{}</a>', url, f"Review #{obj.review.id}")
    review_link.short_description = 'Review'


@admin.register(ReviewAnalytics)
class ReviewAnalyticsAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'date', 'reviews_given', 'reviews_received',
        'average_rating_given', 'average_rating_received'
    ]
    list_filter = ['date']
    search_fields = ['user__first_name', 'user__last_name']
    readonly_fields = ['created_at', 'updated_at']

    def user_link(self, obj):
        url = reverse('admin:users_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name())
    user_link.short_description = 'User'
