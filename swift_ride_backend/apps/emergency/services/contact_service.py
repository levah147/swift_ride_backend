from django.utils import timezone
from apps.emergency.models import EmergencyAlert, EmergencyContact, EmergencyResponse
from apps.notifications.services.notification_service import NotificationService
from apps.notifications.services.sms_service import SMSService
from apps.notifications.services.email_service import EmailService
import logging

logger = logging.getLogger(__name__)


class ContactService:
    """Service for handling emergency contact operations"""
    
    @staticmethod
    def notify_emergency_contacts(alert, message_type='emergency'):
        """Notify all emergency contacts about an alert"""
        try:
            contacts = EmergencyContact.objects.filter(
                user=alert.user,
                is_active=True
            ).order_by('-is_primary')
            
            results = []
            
            for contact in contacts:
                result = ContactService._notify_single_contact(
                    contact, alert, message_type
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error notifying emergency contacts: {str(e)}")
            return []
    
    @staticmethod
    def _notify_single_contact(contact, alert, message_type):
        """Notify a single emergency contact"""
        try:
            # Prepare message content
            messages = ContactService._get_message_content(alert, message_type)
            
            result = {
                'contact_id': contact.id,
                'contact_name': contact.name,
                'phone_number': contact.phone_number,
                'sms_sent': False,
                'email_sent': False,
                'errors': []
            }
            
            # Send SMS
            try:
                sms_result = SMSService.send_sms(
                    phone_number=contact.phone_number,
                    message=messages['sms']
                )
                result['sms_sent'] = sms_result.get('success', False)
                if not result['sms_sent']:
                    result['errors'].append(f"SMS failed: {sms_result.get('error', 'Unknown error')}")
            except Exception as e:
                result['errors'].append(f"SMS error: {str(e)}")
            
            # Send Email if available
            if contact.email:
                try:
                    email_result = EmailService.send_email(
                        to_email=contact.email,
                        subject=messages['email_subject'],
                        message=messages['email_body']
                    )
                    result['email_sent'] = email_result.get('success', False)
                    if not result['email_sent']:
                        result['errors'].append(f"Email failed: {email_result.get('error', 'Unknown error')}")
                except Exception as e:
                    result['errors'].append(f"Email error: {str(e)}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error notifying contact {contact.id}: {str(e)}")
            return {
                'contact_id': contact.id,
                'contact_name': contact.name,
                'phone_number': contact.phone_number,
                'sms_sent': False,
                'email_sent': False,
                'errors': [str(e)]
            }
    
    @staticmethod
    def _get_message_content(alert, message_type):
        """Get message content for different alert types"""
        user_name = alert.user.get_full_name()
        alert_time = alert.created_at.strftime('%Y-%m-%d %H:%M:%S')
        
        if message_type == 'emergency':
            sms_message = (
                f"🚨 EMERGENCY ALERT 🚨\n"
                f"{user_name} has triggered an emergency alert.\n"
                f"Type: {alert.get_alert_type_display()}\n"
                f"Time: {alert_time}\n"
                f"Please contact them immediately or call emergency services."
            )
            
            email_subject = f"🚨 Emergency Alert - {user_name}"
            email_body = f"""
            <h2 style="color: red;">🚨 EMERGENCY ALERT 🚨</h2>
            
            <p><strong>{user_name}</strong> has triggered an emergency alert.</p>
            
            <h3>Alert Details:</h3>
            <ul>
                <li><strong>Type:</strong> {alert.get_alert_type_display()}</li>
                <li><strong>Severity:</strong> {alert.get_severity_display()}</li>
                <li><strong>Time:</strong> {alert_time}</li>
                <li><strong>Status:</strong> {alert.get_status_display()}</li>
            </ul>
            
            {f'<p><strong>Description:</strong> {alert.description}</p>' if alert.description else ''}
            
            {f'<p><strong>Location:</strong> {alert.address}</p>' if alert.address else ''}
            
            <h3>Immediate Actions Required:</h3>
            <ol>
                <li>Try to contact {user_name} immediately</li>
                <li>If you cannot reach them, consider calling emergency services</li>
                <li>Monitor for updates on their status</li>
            </ol>
            
            <p style="color: red; font-weight: bold;">
                This is an automated emergency notification. Please take immediate action.
            </p>
            """
            
        elif message_type == 'safety_check':
            sms_message = (
                f"Safety Check: {user_name}\n"
                f"Time: {alert_time}\n"
                f"Please confirm you are safe by responding to this message."
            )
            
            email_subject = f"Safety Check - {user_name}"
            email_body = f"""
            <h2>Safety Check</h2>
            <p>This is a safety check for <strong>{user_name}</strong>.</p>
            <p><strong>Time:</strong> {alert_time}</p>
            <p>Please confirm you are safe by responding to this message.</p>
            """
            
        elif message_type == 'resolved':
            sms_message = (
                f"Emergency Resolved: {user_name}\n"
                f"The emergency alert has been resolved.\n"
                f"Time: {alert_time}"
            )
            
            email_subject = f"Emergency Resolved - {user_name}"
            email_body = f"""
            <h2 style="color: green;">Emergency Resolved</h2>
            <p>The emergency alert for <strong>{user_name}</strong> has been resolved.</p>
            <p><strong>Resolution Time:</strong> {alert_time}</p>
            <p>Thank you for your concern and quick response.</p>
            """
        
        else:
            # Default message
            sms_message = f"Alert from {user_name} at {alert_time}"
            email_subject = f"Alert - {user_name}"
            email_body = f"<p>Alert from <strong>{user_name}</strong> at {alert_time}</p>"
        
        return {
            'sms': sms_message,
            'email_subject': email_subject,
            'email_body': email_body
        }
    
    @staticmethod
    def call_emergency_contact(contact_id, alert_id):
        """Initiate a call to an emergency contact"""
        try:
            contact = EmergencyContact.objects.get(id=contact_id)
            
            # Create response record
            response = EmergencyResponse.objects.create(
                alert_id=alert_id,
                action_type='call_user',
                status='in_progress'
            )
            
            # In production, this would integrate with a calling service
            # like Twilio Voice API to make automated calls
            
            # For now, we'll simulate the call
            call_result = ContactService._simulate_emergency_call(contact)
            
            # Update response
            response.status = 'completed' if call_result['success'] else 'failed'
            response.success = call_result['success']
            response.notes = call_result['message']
            response.completed_at = timezone.now()
            response.save()
            
            return call_result
            
        except EmergencyContact.DoesNotExist:
            return {'success': False, 'message': 'Contact not found'}
        except Exception as e:
            logger.error(f"Error calling emergency contact: {str(e)}")
            return {'success': False, 'message': str(e)}
    
    @staticmethod
    def _simulate_emergency_call(contact):
        """Simulate an emergency call (replace with real calling service)"""
        # In production, integrate with Twilio Voice API or similar
        return {
            'success': True,
            'message': f'Call initiated to {contact.name} at {contact.phone_number}',
            'call_duration': 0,
            'call_status': 'initiated'
        }
    
    @staticmethod
    def validate_emergency_contact(phone_number, email=None):
        """Validate emergency contact information"""
        errors = []
        
        # Validate phone number format
        import re
        phone_pattern = r'^\+?1?\d{9,15}$'
        if not re.match(phone_pattern, phone_number):
            errors.append("Invalid phone number format")
        
        # Validate email if provided
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("Invalid email format")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def get_contact_response_history(contact_id, days=30):
        """Get response history for a contact"""
        try:
            from datetime import timedelta
            
            contact = EmergencyContact.objects.get(id=contact_id)
            since_date = timezone.now() - timedelta(days=days)
            
            # Get alerts where this contact was notified
            alerts = EmergencyAlert.objects.filter(
                user=contact.user,
                created_at__gte=since_date
            ).order_by('-created_at')
            
            history = []
            for alert in alerts:
                history.append({
                    'alert_id': str(alert.id),
                    'alert_type': alert.get_alert_type_display(),
                    'severity': alert.get_severity_display(),
                    'status': alert.get_status_display(),
                    'created_at': alert.created_at,
                    'resolved_at': alert.resolved_at
                })
            
            return {
                'contact': {
                    'id': contact.id,
                    'name': contact.name,
                    'phone_number': contact.phone_number,
                    'relationship': contact.get_relationship_display()
                },
                'history': history,
                'total_alerts': len(history)
            }
            
        except EmergencyContact.DoesNotExist:
            return {'error': 'Contact not found'}
        except Exception as e:
            logger.error(f"Error getting contact history: {str(e)}")
            return {'error': str(e)}
