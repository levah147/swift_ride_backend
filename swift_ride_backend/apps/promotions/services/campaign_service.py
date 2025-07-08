from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import List, Dict, Any
import logging

from ..models import PromotionCampaign, Promotion, UserType
from apps.notifications.services.notification_service import NotificationService

User = get_user_model()
logger = logging.getLogger(__name__)


class CampaignService:
    """Service for managing promotion campaigns"""
    
    @staticmethod
    def create_campaign(campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new promotion campaign"""
        try:
            campaign = PromotionCampaign.objects.create(**campaign_data)
            
            # Calculate target audience size
            target_users = CampaignService._get_target_audience(campaign)
            campaign.target_audience_size = target_users.count()
            campaign.save()
            
            return {'success': True, 'campaign': campaign}
            
        except Exception as e:
            logger.error(f"Error creating campaign: {str(e)}")
            return {'success': False, 'error': 'Failed to create campaign'}
    
    @staticmethod
    def launch_campaign(campaign: PromotionCampaign) -> Dict[str, Any]:
        """Launch a promotion campaign"""
        try:
            if campaign.status != PromotionCampaign.CampaignStatus.SCHEDULED:
                return {'success': False, 'error': 'Campaign is not scheduled'}
            
            # Get target audience
            target_users = CampaignService._get_target_audience(campaign)
            
            # Update campaign status
            campaign.status = PromotionCampaign.CampaignStatus.RUNNING
            campaign.save()
            
            # Send notifications based on campaign type
            if campaign.campaign_type == PromotionCampaign.CampaignType.PUSH:
                CampaignService._send_push_notifications(campaign, target_users)
            elif campaign.campaign_type == PromotionCampaign.CampaignType.EMAIL:
                CampaignService._send_email_campaign(campaign, target_users)
            elif campaign.campaign_type == PromotionCampaign.CampaignType.SMS:
                CampaignService._send_sms_campaign(campaign, target_users)
            elif campaign.campaign_type == PromotionCampaign.CampaignType.IN_APP:
                CampaignService._send_in_app_notifications(campaign, target_users)
            
            return {'success': True, 'campaign': campaign, 'target_count': target_users.count()}
            
        except Exception as e:
            logger.error(f"Error launching campaign: {str(e)}")
            return {'success': False, 'error': 'Failed to launch campaign'}
    
    @staticmethod
    def _get_target_audience(campaign: PromotionCampaign):
        """Get target audience for campaign"""
        users = User.objects.filter(is_active=True)
        
        # Filter by user type
        if campaign.target_user_type == UserType.NEW:
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            users = users.filter(date_joined__gte=thirty_days_ago)
        elif campaign.target_user_type == UserType.EXISTING:
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            users = users.filter(date_joined__lt=thirty_days_ago)
        elif campaign.target_user_type == UserType.RIDERS:
            users = users.filter(rider_profile__isnull=False)
        elif campaign.target_user_type == UserType.DRIVERS:
            users = users.filter(driver_profile__isnull=False)
        elif campaign.target_user_type == UserType.VIP:
            users = users.filter(is_vip=True)
        
        # Filter by cities
        if campaign.target_cities.exists():
            users = users.filter(city__in=campaign.target_cities.all())
        
        # Filter by age
        if campaign.target_age_min or campaign.target_age_max:
            from datetime import date
            today = date.today()
            
            if campaign.target_age_min:
                max_birth_date = date(today.year - campaign.target_age_min, today.month, today.day)
                users = users.filter(date_of_birth__lte=max_birth_date)
            
            if campaign.target_age_max:
                min_birth_date = date(today.year - campaign.target_age_max, today.month, today.day)
                users = users.filter(date_of_birth__gte=min_birth_date)
        
        return users
    
    @staticmethod
    def _send_push_notifications(campaign: PromotionCampaign, users):
        """Send push notifications for campaign"""
        notification_data = {
            'title': campaign.subject or campaign.name,
            'message': campaign.message,
            'data': {
                'campaign_id': str(campaign.id),
                'promotion_code': campaign.promotion.code,
                'type': 'promotion_campaign'
            }
        }
        
        sent_count = 0
        for user in users:
            try:
                NotificationService.send_push_notification(
                    user=user,
                    **notification_data
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send push notification to user {user.id}: {str(e)}")
        
        # Update campaign metrics
        campaign.messages_sent = sent_count
        campaign.save()
    
    @staticmethod
    def _send_email_campaign(campaign: PromotionCampaign, users):
        """Send email campaign"""
        sent_count = 0
        for user in users:
            try:
                NotificationService.send_email_notification(
                    user=user,
                    subject=campaign.subject,
                    message=campaign.message,
                    template_data={
                        'promotion_code': campaign.promotion.code,
                        'campaign_name': campaign.name,
                        'call_to_action': campaign.call_to_action
                    }
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email to user {user.id}: {str(e)}")
        
        # Update campaign metrics
        campaign.messages_sent = sent_count
        campaign.save()
    
    @staticmethod
    def _send_sms_campaign(campaign: PromotionCampaign, users):
        """Send SMS campaign"""
        sent_count = 0
        for user in users:
            try:
                NotificationService.send_sms_notification(
                    user=user,
                    message=f"{campaign.message}\nUse code: {campaign.promotion.code}"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send SMS to user {user.id}: {str(e)}")
        
        # Update campaign metrics
        campaign.messages_sent = sent_count
        campaign.save()
    
    @staticmethod
    def _send_in_app_notifications(campaign: PromotionCampaign, users):
        """Send in-app notifications"""
        sent_count = 0
        for user in users:
            try:
                NotificationService.create_notification(
                    user=user,
                    title=campaign.subject or campaign.name,
                    message=campaign.message,
                    notification_type='promotion',
                    data={
                        'campaign_id': str(campaign.id),
                        'promotion_code': campaign.promotion.code
                    }
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send in-app notification to user {user.id}: {str(e)}")
        
        # Update campaign metrics
        campaign.messages_sent = sent_count
        campaign.save()
    
    @staticmethod
    def track_campaign_interaction(campaign: PromotionCampaign, interaction_type: str):
        """Track campaign interactions"""
        if interaction_type == 'delivered':
            campaign.messages_delivered += 1
        elif interaction_type == 'opened':
            campaign.messages_opened += 1
        elif interaction_type == 'clicked':
            campaign.messages_clicked += 1
        elif interaction_type == 'converted':
            campaign.conversions += 1
        
        campaign.save()
    
    @staticmethod
    def get_campaign_analytics(campaign: PromotionCampaign) -> Dict[str, Any]:
        """Get campaign performance analytics"""
        return {
            'campaign': campaign,
            'metrics': {
                'target_audience_size': campaign.target_audience_size,
                'messages_sent': campaign.messages_sent,
                'messages_delivered': campaign.messages_delivered,
                'messages_opened': campaign.messages_opened,
                'messages_clicked': campaign.messages_clicked,
                'conversions': campaign.conversions,
                'delivery_rate': campaign.delivery_rate,
                'open_rate': campaign.open_rate,
                'click_rate': campaign.click_rate,
                'conversion_rate': campaign.conversion_rate
            }
        }
