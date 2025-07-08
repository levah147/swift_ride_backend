"""
Service for Stripe payment processing.
"""

import stripe
from django.conf import settings
from decimal import Decimal

from apps.payments.models import Payment, PaymentMethod


class StripeService:
    """
    Service for handling Stripe payments.
    """
    
    def __init__(self):
        stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', '')
    
    @staticmethod
    def process_payment(payment):
        """
        Process payment via Stripe.
        """
        try:
            # Convert amount to cents
            amount_cents = int(payment.amount * 100)
            
            # Create payment intent
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=payment.currency.lower(),
                payment_method=payment.payment_method.provider_payment_method_id,
                customer=payment.payment_method.provider_customer_id,
                confirm=True,
                description=payment.description,
                metadata={
                    'payment_id': str(payment.payment_id),
                    'user_id': str(payment.payer.id),
                    'ride_id': str(payment.ride.id) if payment.ride else None,
                }
            )
            
            # Update payment with Stripe data
            payment.provider_transaction_id = intent.id
            payment.provider_fee = Decimal(str(intent.charges.data[0].balance_transaction.fee / 100))
            payment.save()
            
            if intent.status == 'succeeded':
                from apps.payments.services.payment_service import PaymentService
                PaymentService.complete_payment(payment)
                return True, "Payment processed successfully"
            else:
                payment.mark_as_failed(f"Stripe payment failed: {intent.status}")
                return False, f"Payment failed: {intent.status}"
        
        except stripe.error.CardError as e:
            payment.mark_as_failed(f"Card error: {e.user_message}")
            return False, f"Card error: {e.user_message}"
        
        except stripe.error.StripeError as e:
            payment.mark_as_failed(f"Stripe error: {str(e)}")
            return False, f"Payment processing error: {str(e)}"
        
        except Exception as e:
            payment.mark_as_failed(f"Unexpected error: {str(e)}")
            return False, f"Unexpected error: {str(e)}"
    
    @staticmethod
    def create_customer(user):
        """
        Create Stripe customer for user.
        """
        try:
            customer = stripe.Customer.create(
                email=user.email,
                phone=user.phone_number,
                name=user.get_full_name(),
                metadata={
                    'user_id': str(user.id),
                }
            )
            return customer.id, "Customer created successfully"
        
        except stripe.error.StripeError as e:
            return None, f"Error creating customer: {str(e)}"
    
    @staticmethod
    def add_payment_method(user, payment_method_id):
        """
        Add payment method to user's Stripe customer.
        """
        try:
            # Get or create Stripe customer
            customer_id = StripeService._get_or_create_customer(user)
            
            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id,
            )
            
            # Get payment method details
            pm = stripe.PaymentMethod.retrieve(payment_method_id)
            
            # Create PaymentMethod record
            if pm.type == 'card':
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    method_type=PaymentMethod.MethodType.CARD,
                    provider=PaymentMethod.Provider.STRIPE,
                    provider_payment_method_id=payment_method_id,
                    provider_customer_id=customer_id,
                    display_name=f"{pm.card.brand.title()} ending in {pm.card.last4}",
                    last_four=pm.card.last4,
                    card_brand=pm.card.brand,
                    card_exp_month=pm.card.exp_month,
                    card_exp_year=pm.card.exp_year,
                    is_verified=True
                )
                
                return payment_method, "Payment method added successfully"
            else:
                return None, "Unsupported payment method type"
        
        except stripe.error.StripeError as e:
            return None, f"Error adding payment method: {str(e)}"
    
    @staticmethod
    def process_refund(refund):
        """
        Process refund via Stripe.
        """
        try:
            # Convert amount to cents
            amount_cents = int(refund.amount * 100)
            
            # Create refund
            stripe_refund = stripe.Refund.create(
                payment_intent=refund.payment.provider_transaction_id,
                amount=amount_cents,
                reason='requested_by_customer',
                metadata={
                    'refund_id': str(refund.refund_id),
                    'payment_id': str(refund.payment.payment_id),
                }
            )
            
            # Update refund with Stripe data
            refund.provider_refund_id = stripe_refund.id
            refund.save()
            
            if stripe_refund.status == 'succeeded':
                return True, "Refund processed successfully"
            else:
                return False, f"Refund failed: {stripe_refund.status}"
        
        except stripe.error.StripeError as e:
            return False, f"Stripe refund error: {str(e)}"
    
    @staticmethod
    def _get_or_create_customer(user):
        """
        Get or create Stripe customer for user.
        """
        # Check if user already has a Stripe customer ID
        payment_method = PaymentMethod.objects.filter(
            user=user,
            provider=PaymentMethod.Provider.STRIPE,
            provider_customer_id__isnull=False
        ).first()
        
        if payment_method:
            return payment_method.provider_customer_id
        
        # Create new customer
        customer_id, message = StripeService.create_customer(user)
        return customer_id
