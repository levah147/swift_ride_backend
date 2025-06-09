"""
Management command to create default notification templates.
"""

from django.core.management.base import BaseCommand
from apps.notifications.models import NotificationTemplate


class Command(BaseCommand):
    help = 'Create default notification templates'
    
    def handle(self, *args, **options):
        templates = [
            # Ride notifications
            {
                'name': 'Ride Request - Push',
                'notification_type': NotificationTemplate.NotificationType.RIDE_REQUEST,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'New Ride Request',
                'body_template': 'You have a new ride request from {{pickup_location}} to {{destination}}',
                'priority': 3,
                'variables': ['pickup_location', 'destination', 'fare']
            },
            {
                'name': 'Ride Accepted - Push',
                'notification_type': NotificationTemplate.NotificationType.RIDE_ACCEPTED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Ride Accepted!',
                'body_template': '{{driver_name}} has accepted your ride request. They will arrive in {{eta}} minutes.',
                'priority': 3,
                'variables': ['driver_name', 'eta', 'vehicle_info']
            },
            {
                'name': 'Driver Arrived - Push',
                'notification_type': NotificationTemplate.NotificationType.DRIVER_ARRIVED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Driver Arrived',
                'body_template': '{{driver_name}} has arrived at your pickup location.',
                'priority': 4,
                'variables': ['driver_name', 'vehicle_info']
            },
            {
                'name': 'Ride Started - Push',
                'notification_type': NotificationTemplate.NotificationType.RIDE_STARTED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Ride Started',
                'body_template': 'Your ride to {{destination}} has started. Estimated arrival: {{eta}}',
                'priority': 2,
                'variables': ['destination', 'eta']
            },
            {
                'name': 'Ride Completed - Push',
                'notification_type': NotificationTemplate.NotificationType.RIDE_COMPLETED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Ride Completed',
                'body_template': 'Your ride is complete. Total fare: {{fare}}. Thank you for using Swift Ride!',
                'priority': 2,
                'variables': ['fare', 'duration', 'distance']
            },
            
            # Chat notifications
            {
                'name': 'New Message - Push',
                'notification_type': NotificationTemplate.NotificationType.NEW_MESSAGE,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'New Message from {{sender_name}}',
                'body_template': '{{message_preview}}',
                'priority': 2,
                'variables': ['sender_name', 'message_preview']
            },
            {
                'name': 'Voice Message - Push',
                'notification_type': NotificationTemplate.NotificationType.VOICE_MESSAGE,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Voice Message from {{sender_name}}',
                'body_template': 'You received a voice message',
                'priority': 2,
                'variables': ['sender_name']
            },
            
            # Payment notifications
            {
                'name': 'Payment Received - Push',
                'notification_type': NotificationTemplate.NotificationType.PAYMENT_RECEIVED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Payment Received',
                'body_template': 'Payment of {{amount}} {{currency}} received successfully.',
                'priority': 2,
                'variables': ['amount', 'currency', 'payment_method']
            },
            {
                'name': 'Payment Failed - Push',
                'notification_type': NotificationTemplate.NotificationType.PAYMENT_FAILED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Payment Failed',
                'body_template': 'Payment of {{amount}} {{currency}} failed. Please try again.',
                'priority': 3,
                'variables': ['amount', 'currency', 'error_reason']
            },
            
            # Emergency notifications
            {
                'name': 'Emergency Alert - SMS',
                'notification_type': NotificationTemplate.NotificationType.EMERGENCY_ALERT,
                'channel': NotificationTemplate.Channel.SMS,
                'title_template': 'EMERGENCY ALERT',
                'body_template': 'EMERGENCY: {{user_name}} needs help at {{location}}. Time: {{timestamp}}',
                'sms_template': 'EMERGENCY ALERT: {{user_name}} needs help at {{location}}. Time: {{timestamp}}. This is an automated message from Swift Ride.',
                'priority': 4,
                'variables': ['user_name', 'location', 'timestamp', 'emergency_type']
            },
            
            # Vehicle notifications
            {
                'name': 'Vehicle Approved - Push',
                'notification_type': NotificationTemplate.NotificationType.VEHICLE_APPROVED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Vehicle Approved',
                'body_template': 'Your vehicle {{vehicle_info}} has been approved. You can now start accepting rides!',
                'priority': 2,
                'variables': ['vehicle_info']
            },
            {
                'name': 'Document Verified - Push',
                'notification_type': NotificationTemplate.NotificationType.DOCUMENT_VERIFIED,
                'channel': NotificationTemplate.Channel.PUSH,
                'title_template': 'Document Verified',
                'body_template': 'Your {{document_type}} has been verified successfully.',
                'priority': 2,
                'variables': ['document_type']
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for template_data in templates:
            template, created = NotificationTemplate.objects.get_or_create(
                notification_type=template_data['notification_type'],
                channel=template_data['channel'],
                defaults=template_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created template: {template.name}')
                )
            else:
                # Update existing template
                for key, value in template_data.items():
                    setattr(template, key, value)
                template.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated template: {template.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {created_count + updated_count} templates '
                f'({created_count} created, {updated_count} updated)'
            )
        )
