"""
Stripe payment provider.
"""

import stripe
from decimal import Decimal
from typing import Dict, Any, Tuple, Optional

from django.conf import settings

from .base import BasePaymentProvider
from apps.payments.models import Payment, PaymentMethod, Refund


class StripeProvider(BasePaymentProvider):
    """
    Stripe payment provider implementation.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        default_config = {
            'secret_key': getattr(settings, 'STRIPE_SECRET_KEY', ''),
            'public_key': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
            'webhook_secret': getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(default_config)
        
        # Configure Stripe
        stripe.api_key = self.config['secret_key']
    
    def get_required_config_keys(self) -> list:
        return ['secret_key', 'public_key']
    
    def get_supported_currencies(self) -> list:
        return ['USD', 'EUR', 'GBP', 'CAD', 'AUD', 'JPY', 'KES', 'NGN', 'ZAR']
    
    def get_supported_payment_methods(self) -> list:
        return ['card', 'bank_account']
    
    def process_payment(self, payment: Payment) -> Tuple[bool, str]:
        """
        Process payment via Stripe.
        """
        try:
            # Create payment intent
            intent_data = {
                'amount': self.format_amount(payment.amount, payment.currency),
                'currency': payment.currency.lower(),
                'metadata': {
                    'payment_id': str(payment.payment_id),
                    'user_id': str(payment.payer.id),
                    'payment_type': payment.payment_type
                },
                'description': payment.description or f"Payment for {payment.payment_type}"
            }
            
            # Add payment method if available
            if payment.payment_method and payment.payment_method.provider_payment_method_id:
                intent_data['payment_method'] = payment.payment_method.provider_payment_method_id
                intent_data['confirm'] = True
            
            # Add customer if exists
            if hasattr(payment.payer, 'stripe_customer_id') and payment.payer.stripe_customer_id:
                intent_data['customer'] = payment.payer.stripe_customer_id
            
            payment_intent = stripe.PaymentIntent.create(**intent_data)
            
            # Update payment with Stripe data
            payment.provider_transaction_id = payment_intent.id
            payment.metadata.update({
                'stripe_payment_intent_id': payment_intent.id,
                'client_secret': payment_intent.client_secret,
                'status': payment_intent.status
            })
            
            if payment_intent.status == 'succeeded':
                payment.status = Payment.Status.COMPLETED
                payment.completed_at = timezone.now()
            elif payment_intent.status in ['requires_payment_method', 'requires_confirmation']:
                payment.status = Payment.Status.PROCESSING
            else:
                payment.status = Payment.Status.PENDING
            
            payment.save()
            
            self.log_transaction('payment_intent_created', {
                'payment_id': str(payment.payment_id),
                'intent_id': payment_intent.id,
                'status': payment_intent.status
            })
            
            return True, "Payment intent created successfully"
        
        except stripe.error.StripeError as e:
            error_message = f"Stripe error: {str(e)}"
            payment.mark_as_failed(error_message)
            return False, error_message
        
        except Exception as e:
            error_message = self.handle_error(e, "Payment processing")
            payment.mark_as_failed(error_message)
            return False, error_message
    
    def process_refund(self, refund: Refund) -> Tuple[bool, str]:
        """
        Process refund via Stripe.
        """
        try:
            refund_data = {
                'payment_intent': refund.payment.provider_transaction_id,
                'amount': self.format_amount(refund.amount, refund.payment.currency),
                'metadata': {
                    'refund_id': str(refund.refund_id),
                    'original_payment_id': str(refund.payment.payment_id)
                },
                'reason': 'requested_by_customer'
            }
            
            if refund.description:
                refund_data['metadata']['description'] = refund.description
            
            stripe_refund = stripe.Refund.create(**refund_data)
            
            refund.provider_refund_id = stripe_refund.id
            refund.save()
            
            self.log_transaction('refund_created', {
                'refund_id': str(refund.refund_id),
                'stripe_refund_id': stripe_refund.id,
                'status': stripe_refund.status
            })
            
            return True, "Refund processed successfully"
        
        except stripe.error.StripeError as e:
            return False, f"Stripe error: {str(e)}"
        
        except Exception as e:
            return False, self.handle_error(e, "Refund processing")
    
    def create_payment_method(self, user, method_data: Dict[str, Any]) -> Tuple[Optional[PaymentMethod], str]:
        """
        Create payment method via Stripe.
        """
        try:
            method_type = method_data.get('method_type')
            
            # Create or get Stripe customer
            customer = self._get_or_create_stripe_customer(user)
            
            if method_type == PaymentMethod.MethodType.CARD:
                # Create payment method
                stripe_pm = stripe.PaymentMethod.create(
                    type='card',
                    card={
                        'number': method_data['card_number'],
                        'exp_month': method_data['exp_month'],
                        'exp_year': method_data['exp_year'],
                        'cvc': method_data['cvc']
                    }
                )
                
                # Attach to customer
                stripe_pm.attach(customer=customer.id)
                
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    method_type=PaymentMethod.MethodType.CARD,
                    provider=PaymentMethod.Provider.STRIPE,
                    display_name=f"{stripe_pm.card.brand.title()} ending in {stripe_pm.card.last4}",
                    last_four=stripe_pm.card.last4,
                    card_brand=stripe_pm.card.brand,
                    card_exp_month=stripe_pm.card.exp_month,
                    card_exp_year=stripe_pm.card.exp_year,
                    provider_payment_method_id=stripe_pm.id,
                    is_verified=True
                )
                
                return payment_method, "Card payment method created successfully"
            
            elif method_type == PaymentMethod.MethodType.BANK_ACCOUNT:
                # For bank accounts, we'd typically use ACH or similar
                # This is a simplified implementation
                payment_method = PaymentMethod.objects.create(
                    user=user,
                    method_type=PaymentMethod.MethodType.BANK_ACCOUNT,
                    provider=PaymentMethod.Provider.STRIPE,
                    display_name=f"Bank account ending in {method_data.get('last4', '****')}",
                    last_four=method_data.get('last4'),
                    bank_name=method_data.get('bank_name'),
                    is_verified=False  # Would need verification process
                )
                
                return payment_method, "Bank account payment method created (verification required)"
            
            else:
                return None, f"Unsupported payment method type: {method_type}"
        
        except stripe.error.StripeError as e:
            return None, f"Stripe error: {str(e)}"
        
        except Exception as e:
            return None, self.handle_error(e, "Payment method creation")
    
    def verify_payment(self, provider_transaction_id: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Verify payment with Stripe.
        """
        try:
            payment_intent = stripe.PaymentIntent.retrieve(provider_transaction_id)
            
            return True, {
                'status': payment_intent.status,
                'amount': self.parse_amount(payment_intent.amount, payment_intent.currency),
                'currency': payment_intent.currency.upper(),
                'payment_intent_id': payment_intent.id,
                'charges': [
                    {
                        'id': charge.id,
                        'amount': self.parse_amount(charge.amount, charge.currency),
                        'status': charge.status,
                        'created': charge.created,
                        'payment_method_details': charge.payment_method_details
                    }
                    for charge in payment_intent.charges.data
                ],
                'created': payment_intent.created,
                'metadata': payment_intent.metadata
            }
        
        except stripe.error.StripeError as e:
            return False, {'error': f"Stripe error: {str(e)}"}
        
        except Exception as e:
            return False, {'error': self.handle_error(e, "Payment verification")}
    
    def handle_webhook(self, payload: str, signature: str = None) -> Tuple[bool, str]:
        """
        Handle Stripe webhook.
        """
        try:
            # Verify webhook signature
            if signature and self.config.get('webhook_secret'):
                event = stripe.Webhook.construct_event(
                    payload, signature, self.config['webhook_secret']
                )
            else:
                import json
                event = json.loads(payload)
            
            event_type = event['type']
            event_data = event['data']['object']
            
            if event_type == 'payment_intent.succeeded':
                # Payment succeeded
                payment_intent_id = event_data['id']
                
                try:
                    payment = Payment.objects.get(provider_transaction_id=payment_intent_id)
                    
                    if payment.status != Payment.Status.COMPLETED:
                        # Update payment details
                        charges = event_data.get('charges', {}).get('data', [])
                        if charges:
                            charge = charges[0]
                            payment.provider_fee = self.parse_amount(
                                charge.get('balance_transaction', {}).get('fee', 0),
                                event_data['currency']
                            )
                        
                        payment.metadata.update({
                            'stripe_charge_id': charges[0]['id'] if charges else None,
                            'payment_method_details': charges[0].get('payment_method_details') if charges else None
                        })
                        payment.save()
                        
                        # Complete payment
                        from apps.payments.services.payment_service import PaymentService
                        PaymentService.complete_payment(payment)
                        
                        self.log_transaction('webhook_payment_succeeded', {
                            'payment_id': str(payment.payment_id),
                            'intent_id': payment_intent_id
                        })
                
                except Payment.DoesNotExist:
                    return False, f"Payment not found: {payment_intent_id}"
            
            elif event_type == 'payment_intent.payment_failed':
                # Payment failed
                payment_intent_id = event_data['id']
                
                try:
                    payment = Payment.objects.get(provider_transaction_id=payment_intent_id)
                    error_message = event_data.get('last_payment_error', {}).get('message', 'Payment failed')
                    payment.mark_as_failed(f"Stripe payment failed: {error_message}")
                    
                    self.log_transaction('webhook_payment_failed', {
                        'payment_id': str(payment.payment_id),
                        'intent_id': payment_intent_id,
                        'error': error_message
                    })
                
                except Payment.DoesNotExist:
                    return False, f"Payment not found: {payment_intent_id}"
            
            elif event_type == 'charge.dispute.created':
                # Handle dispute/chargeback
                charge_id = event_data['charge']
                
                # You would implement dispute handling logic here
                self.log_transaction('webhook_dispute_created', {
                    'charge_id': charge_id,
                    'dispute_id': event_data['id']
                })
            
            return True, f"Webhook processed: {event_type}"
        
        except stripe.error.SignatureVerificationError:
            return False, "Invalid webhook signature"
        
        except Exception as e:
            return False, self.handle_error(e, "Webhook processing")
    
    def calculate_fees(self, amount: Decimal, currency: str = 'USD') -> Dict[str, Decimal]:
        """
        Calculate Stripe fees.
        """
        # Stripe fee structure (as of 2024)
        if currency.upper() == 'USD':
            percentage_fee = amount * Decimal('0.029')  # 2.9%
            fixed_fee = Decimal('0.30')  # $0.30
        else:
            # International cards
            percentage_fee = amount * Decimal('0.034')  # 3.4%
            fixed_fee = Decimal('0.30')  # $0.30
        
        total_fee = percentage_fee + fixed_fee
        
        return {
            'processing_fee': percentage_fee,
            'fixed_fee': fixed_fee,
            'total_fee': total_fee
        }
    
    def _get_or_create_stripe_customer(self, user):
        """
        Get or create Stripe customer for user.
        """
        if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
            try:
                return stripe.Customer.retrieve(user.stripe_customer_id)
            except stripe.error.StripeError:
                pass
        
        # Create new customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.get_full_name(),
            phone=getattr(user, 'phone_number', None),
            metadata={
                'user_id': str(user.id)
            }
        )
        
        # Save customer ID to user
        user.stripe_customer_id = customer.id
        user.save(update_fields=['stripe_customer_id'])
        
        return customer
