"""
Service for handling email notifications.
"""

from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

from apps.notifications.models import NotificationLog


class EmailService:
    """
    Service for sending email notifications.
    """
    
    @staticmethod
    def send_email_notification(notification):
        """
        Send email notification to user.
        """
        user = notification.recipient
        
        # Check if user has a valid email
        if not user.email:
            return False, "User has no email address"
        
        try:
            # Prepare email content
            subject = notification.template.render_email_subject(notification.context)
            html_body = notification.template.render_email_body(notification.context)
            text_body = notification.body  # Fallback to plain text
            
            # Send email
            success = EmailService._send_email(
                to_email=user.email,
                subject=subject,
                html_body=html_body,
                text_body=text_body
            )
            
            # Log the attempt
            EmailService._log_notification(
                notification=notification,
                success=success
            )
            
            if success:
                notification.mark_as_sent()
                return True, "Email sent successfully"
            else:
                notification.mark_as_failed("Failed to send email")
                return False, "Failed to send email"
        
        except Exception as e:
            print(f"Error sending email: {e}")
            notification.mark_as_failed(str(e))
            return False, str(e)
    
    @staticmethod
    def _send_email(to_email, subject, html_body, text_body):
        """
        Send email using Django's email backend.
        """
        try:
            # Create email message
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[to_email]
            )
            
            # Attach HTML version
            if html_body:
                email.attach_alternative(html_body, "text/html")
            
            # Send email
            result = email.send()
            return result > 0
        
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    @staticmethod
    def _log_notification(notification, success):
        """
        Log email delivery attempt.
        """
        NotificationLog.objects.create(
            notification=notification,
            channel='email',
            provider='Django',
            success=success,
            response_message='Email sent successfully' if success else 'Failed to send email'
        )
    
    @staticmethod
    def send_ride_receipt_email(ride):
        """
        Send ride receipt email.
        """
        user = ride.rider
        
        if not user.email:
            return False
        
        context = {
            'user_name': user.get_full_name() or user.phone_number,
            'ride': ride,
            'driver_name': ride.driver.get_full_name() if ride.driver else 'Driver',
            'pickup_location': ride.pickup_location,
            'destination': ride.destination,
            'fare_amount': ride.fare_amount,
            'distance': ride.distance_km,
            'duration': ride.duration_minutes,
            'completed_at': ride.completed_at,
        }
        
        # Render email template
        subject = f"Swift Ride Receipt - {ride.pickup_location} to {ride.destination}"
        html_body = render_to_string('emails/ride_receipt.html', context)
        text_body = render_to_string('emails/ride_receipt.txt', context)
        
        return EmailService._send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
    
    @staticmethod
    def send_weekly_summary_email(user, summary_data):
        """
        Send weekly ride summary email.
        """
        if not user.email:
            return False
        
        context = {
            'user_name': user.get_full_name() or user.phone_number,
            'summary': summary_data,
        }
        
        subject = "Your Weekly Swift Ride Summary"
        html_body = render_to_string('emails/weekly_summary.html', context)
        text_body = render_to_string('emails/weekly_summary.txt', context)
        
        return EmailService._send_email(
            to_email=user.email,
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
