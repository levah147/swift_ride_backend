"""
Service for handling push notifications.
"""

import json
import requests
from django.conf import settings

from apps.notifications.models import DeviceToken, NotificationLog


class PushNotificationService:
    """
    Service for sending push notifications via Firebase FCM.
    """
    
    FCM_URL = "https://fcm.googleapis.com/fcm/send"
    
    @staticmethod
    def send_push_notification(notification):
        """
        Send push notification to user's devices.
        """
        user = notification.recipient
        
        # Get active device tokens
        device_tokens = DeviceToken.objects.filter(
            user=user,
            is_active=True
        )
        
        if not device_tokens.exists():
            return False, "No active device tokens found"
        
        success_count = 0
        total_count = device_tokens.count()
        
        for device_token in device_tokens:
            success = PushNotificationService._send_to_device(notification, device_token)
            if success:
                success_count += 1
        
        return success_count > 0, f"Sent to {success_count}/{total_count} devices"
    
    @staticmethod
    def _send_to_device(notification, device_token):
        """
        Send push notification to a specific device.
        """
        try:
            # Prepare FCM payload
            payload = PushNotificationService._prepare_fcm_payload(notification, device_token)
            
            # Send to FCM
            response = PushNotificationService._send_to_fcm(payload)
            
            # Log the attempt
            success = response.get('success', 0) > 0
            PushNotificationService._log_notification(
                notification=notification,
                device_token=device_token,
                success=success,
                response=response
            )
            
            # Handle invalid tokens
            if not success and 'InvalidRegistration' in str(response):
                device_token.is_active = False
                device_token.save()
            
            return success
        
        except Exception as e:
            print(f"Error sending push notification: {e}")
            PushNotificationService._log_notification(
                notification=notification,
                device_token=device_token,
                success=False,
                response={'error': str(e)}
            )
            return False
    
    @staticmethod
    def _prepare_fcm_payload(notification, device_token):
        """
        Prepare FCM payload based on platform.
        """
        # Base payload
        payload = {
            "to": device_token.token,
            "priority": "high" if notification.priority >= 3 else "normal",
        }
        
        # Platform-specific payload
        if device_token.platform == DeviceToken.Platform.ANDROID:
            payload["data"] = {
                "title": notification.title,
                "body": notification.body,
                "notification_id": str(notification.id),
                "type": notification.template.notification_type,
                "data": json.dumps(notification.data),
            }
            
            # Add notification for display when app is in background
            payload["notification"] = {
                "title": notification.title,
                "body": notification.body,
                "sound": notification.template.push_sound,
                "click_action": "FLUTTER_NOTIFICATION_CLICK",
            }
        
        elif device_token.platform == DeviceToken.Platform.IOS:
            payload["notification"] = {
                "title": notification.title,
                "body": notification.body,
                "sound": notification.template.push_sound,
                "badge": 1 if notification.template.push_badge_count else 0,
            }
            
            payload["data"] = {
                "notification_id": str(notification.id),
                "type": notification.template.notification_type,
                "data": json.dumps(notification.data),
            }
            
            # iOS specific
            if notification.template.push_category:
                payload["notification"]["category"] = notification.template.push_category
        
        elif device_token.platform == DeviceToken.Platform.WEB:
            payload["notification"] = {
                "title": notification.title,
                "body": notification.body,
                "icon": "/icon-192x192.png",  # App icon
                "click_action": settings.FRONTEND_URL,
            }
            
            payload["data"] = {
                "notification_id": str(notification.id),
                "type": notification.template.notification_type,
                "url": f"{settings.FRONTEND_URL}/notifications/{notification.id}",
            }
        
        return payload
    
    @staticmethod
    def _send_to_fcm(payload):
        """
        Send payload to Firebase FCM.
        """
        headers = {
            "Authorization": f"key={settings.FCM_SERVER_KEY}",
            "Content-Type": "application/json",
        }
        
        response = requests.post(
            PushNotificationService.FCM_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        return response.json()
    
    @staticmethod
    def _log_notification(notification, device_token, success, response):
        """
        Log notification delivery attempt.
        """
        NotificationLog.objects.create(
            notification=notification,
            channel='push',
            provider='FCM',
            provider_message_id=response.get('multicast_id'),
            success=success,
            response_code=str(response.get('success', 0)),
            response_message=json.dumps(response)
        )
    
    @staticmethod
    def send_bulk_push_notification(notifications):
        """
        Send bulk push notifications efficiently.
        """
        # Group notifications by user
        user_notifications = {}
        for notification in notifications:
            user_id = notification.recipient.id
            if user_id not in user_notifications:
                user_notifications[user_id] = []
            user_notifications[user_id].append(notification)
        
        # Send to each user
        total_sent = 0
        for user_id, user_notifs in user_notifications.items():
            for notification in user_notifs:
                success, message = PushNotificationService.send_push_notification(notification)
                if success:
                    total_sent += 1
        
        return total_sent
