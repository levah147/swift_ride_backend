"""
Billing service for handling recurring payments and billing cycles.
"""

from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.payments.models import Payment, PaymentMethod, PaymentSettings

User = get_user_model()


class BillingService:
    """
    Service for handling billing and recurring payments.
    """
    
    @staticmethod
    def create_billing_cycle(user: User, amount: Decimal, currency: str = 'USD',
                           frequency: str = 'monthly', start_date: datetime = None,
                           end_date: datetime = None, description: str = None,
                           payment_method: PaymentMethod = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Create a billing cycle for recurring payments.
        """
        try:
            if not start_date:
                start_date = timezone.now()
            
            # Validate frequency
            valid_frequencies = ['daily', 'weekly', 'monthly', 'yearly']
            if frequency not in valid_frequencies:
                return False, f"Invalid frequency: {frequency}", None
            
            # Validate payment method
            if payment_method and payment_method.user != user:
                return False, "Payment method does not belong to user", None
            
            billing_cycle = {
                'user_id': user.id,
                'amount': amount,
                'currency': currency,
                'frequency': frequency,
                'start_date': start_date,
                'end_date': end_date,
                'description': description or f"Recurring {frequency} payment",
                'payment_method_id': payment_method.id if payment_method else None,
                'status': 'active',
                'created_at': timezone.now(),
                'next_billing_date': BillingService._calculate_next_billing_date(start_date, frequency)
            }
            
            return True, "Billing cycle created successfully", billing_cycle
        
        except Exception as e:
            return False, f"Error creating billing cycle: {str(e)}", None
    
    @staticmethod
    def process_recurring_payment(billing_cycle: Dict[str, Any]) -> Tuple[bool, str, Optional[Payment]]:
        """
        Process a recurring payment for a billing cycle.
        """
        try:
            user = User.objects.get(id=billing_cycle['user_id'])
            
            # Get payment method
            payment_method = None
            if billing_cycle.get('payment_method_id'):
                try:
                    payment_method = PaymentMethod.objects.get(
                        id=billing_cycle['payment_method_id'],
                        user=user,
                        is_active=True
                    )
                except PaymentMethod.DoesNotExist:
                    return False, "Payment method not found or inactive", None
            
            # Create payment
            from apps.payments.services.payment_service import PaymentService
            
            payment_data = {
                'amount': billing_cycle['amount'],
                'currency': billing_cycle['currency'],
                'description': f"{billing_cycle['description']} - {timezone.now().strftime('%Y-%m-%d')}",
                'payment_type': 'subscription',
                'payment_method_id': payment_method.id if payment_method else None,
                'metadata': {
                    'billing_cycle_id': billing_cycle.get('id'),
                    'frequency': billing_cycle['frequency'],
                    'is_recurring': True
                }
            }
            
            success, message, payment = PaymentService.create_payment(
                payer=user,
                payee=None,  # Platform payment
                **payment_data
            )
            
            if success:
                # Process the payment
                success, process_message = PaymentService.process_payment(payment)
                
                if success:
                    # Update next billing date
                    next_date = BillingService._calculate_next_billing_date(
                        timezone.now(), 
                        billing_cycle['frequency']
                    )
                    billing_cycle['next_billing_date'] = next_date
                    billing_cycle['last_billing_date'] = timezone.now()
                    
                    return True, "Recurring payment processed successfully", payment
                else:
                    return False, f"Payment processing failed: {process_message}", payment
            else:
                return False, f"Payment creation failed: {message}", None
        
        except Exception as e:
            return False, f"Error processing recurring payment: {str(e)}", None
    
    @staticmethod
    def calculate_billing_amount(base_amount: Decimal, user: User, 
                               billing_type: str = 'standard') -> Dict[str, Decimal]:
        """
        Calculate billing amount including taxes, fees, and discounts.
        """
        try:
            settings = PaymentSettings.get_current_settings()
            
            # Start with base amount
            subtotal = base_amount
            
            # Apply user-specific discounts
            discount = BillingService._calculate_user_discount(user, billing_type)
            discount_amount = subtotal * (discount / 100)
            
            # Calculate platform fee
            platform_fee = subtotal * (settings.platform_fee_percentage / 100)
            
            # Calculate tax (if applicable)
            tax_rate = BillingService._get_tax_rate(user)
            tax_amount = (subtotal - discount_amount) * (tax_rate / 100)
            
            # Calculate total
            total = subtotal - discount_amount + platform_fee + tax_amount
            
            return {
                'subtotal': subtotal,
                'discount_percentage': discount,
                'discount_amount': discount_amount,
                'platform_fee': platform_fee,
                'tax_rate': tax_rate,
                'tax_amount': tax_amount,
                'total': total
            }
        
        except Exception as e:
            # Return base calculation on error
            return {
                'subtotal': base_amount,
                'discount_percentage': Decimal('0.00'),
                'discount_amount': Decimal('0.00'),
                'platform_fee': Decimal('0.00'),
                'tax_rate': Decimal('0.00'),
                'tax_amount': Decimal('0.00'),
                'total': base_amount
            }
    
    @staticmethod
    def generate_invoice(user: User, billing_period: Dict[str, Any], 
                        line_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an invoice for billing period.
        """
        try:
            invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{user.id}"
            
            # Calculate totals
            subtotal = sum(Decimal(str(item['amount'])) for item in line_items)
            billing_calculation = BillingService.calculate_billing_amount(subtotal, user)
            
            invoice = {
                'invoice_number': invoice_number,
                'user_id': user.id,
                'user_name': user.get_full_name(),
                'user_email': user.email,
                'billing_period': billing_period,
                'line_items': line_items,
                'subtotal': billing_calculation['subtotal'],
                'discount_amount': billing_calculation['discount_amount'],
                'platform_fee': billing_calculation['platform_fee'],
                'tax_amount': billing_calculation['tax_amount'],
                'total': billing_calculation['total'],
                'currency': 'USD',  # Default currency
                'status': 'pending',
                'created_at': timezone.now(),
                'due_date': timezone.now() + timedelta(days=30)
            }
            
            return invoice
        
        except Exception as e:
            raise Exception(f"Error generating invoice: {str(e)}")
    
    @staticmethod
    def process_invoice_payment(invoice: Dict[str, Any], payment_method: PaymentMethod = None) -> Tuple[bool, str, Optional[Payment]]:
        """
        Process payment for an invoice.
        """
        try:
            user = User.objects.get(id=invoice['user_id'])
            
            # Create payment for invoice
            from apps.payments.services.payment_service import PaymentService
            
            payment_data = {
                'amount': invoice['total'],
                'currency': invoice['currency'],
                'description': f"Invoice payment - {invoice['invoice_number']}",
                'payment_type': 'invoice',
                'payment_method_id': payment_method.id if payment_method else None,
                'metadata': {
                    'invoice_number': invoice['invoice_number'],
                    'billing_period': invoice['billing_period'],
                    'is_invoice_payment': True
                }
            }
            
            success, message, payment = PaymentService.create_payment(
                payer=user,
                payee=None,  # Platform payment
                **payment_data
            )
            
            if success:
                # Process the payment
                success, process_message = PaymentService.process_payment(payment)
                
                if success:
                    # Update invoice status
                    invoice['status'] = 'paid'
                    invoice['paid_at'] = timezone.now()
                    invoice['payment_id'] = str(payment.payment_id)
                    
                    return True, "Invoice payment processed successfully", payment
                else:
                    return False, f"Payment processing failed: {process_message}", payment
            else:
                return False, f"Payment creation failed: {message}", None
        
        except Exception as e:
            return False, f"Error processing invoice payment: {str(e)}", None
    
    @staticmethod
    def get_billing_history(user: User, start_date: datetime = None, 
                          end_date: datetime = None) -> List[Dict[str, Any]]:
        """
        Get billing history for a user.
        """
        try:
            # Get payments related to billing
            payments = Payment.objects.filter(
                payer=user,
                payment_type__in=['subscription', 'invoice', 'billing']
            )
            
            if start_date:
                payments = payments.filter(created_at__gte=start_date)
            if end_date:
                payments = payments.filter(created_at__lte=end_date)
            
            billing_history = []
            for payment in payments.order_by('-created_at'):
                history_item = {
                    'payment_id': str(payment.payment_id),
                    'amount': payment.amount,
                    'currency': payment.currency,
                    'status': payment.status,
                    'description': payment.description,
                    'payment_type': payment.payment_type,
                    'created_at': payment.created_at,
                    'completed_at': payment.completed_at
                }
                
                # Add billing-specific metadata
                if payment.metadata:
                    if payment.metadata.get('invoice_number'):
                        history_item['invoice_number'] = payment.metadata['invoice_number']
                    if payment.metadata.get('billing_period'):
                        history_item['billing_period'] = payment.metadata['billing_period']
                    if payment.metadata.get('frequency'):
                        history_item['frequency'] = payment.metadata['frequency']
                
                billing_history.append(history_item)
            
            return billing_history
        
        except Exception as e:
            return []
    
    @staticmethod
    def _calculate_next_billing_date(current_date: datetime, frequency: str) -> datetime:
        """
        Calculate next billing date based on frequency.
        """
        if frequency == 'daily':
            return current_date + timedelta(days=1)
        elif frequency == 'weekly':
            return current_date + timedelta(weeks=1)
        elif frequency == 'monthly':
            return current_date + relativedelta(months=1)
        elif frequency == 'yearly':
            return current_date + relativedelta(years=1)
        else:
            return current_date + timedelta(days=30)  # Default to monthly
    
    @staticmethod
    def _calculate_user_discount(user: User, billing_type: str) -> Decimal:
        """
        Calculate user-specific discount percentage.
        """
        discount = Decimal('0.00')
        
        # Example discount logic
        if hasattr(user, 'driver_profile'):
            # Driver discounts
            if billing_type == 'subscription':
                discount = Decimal('10.00')  # 10% discount for drivers
        
        if hasattr(user, 'premium_member') and user.premium_member:
            # Premium member discounts
            discount += Decimal('5.00')  # Additional 5% for premium members
        
        # Long-term user discounts
        if user.date_joined < timezone.now() - timedelta(days=365):
            discount += Decimal('2.50')  # 2.5% for users over 1 year
        
        return min(discount, Decimal('25.00'))  # Cap at 25% discount
    
    @staticmethod
    def _get_tax_rate(user: User) -> Decimal:
        """
        Get tax rate based on user location.
        """
        # This would typically be based on user's location/country
        # For now, return a default rate
        
        # Example tax rates by country
        tax_rates = {
            'US': Decimal('8.25'),   # Average US sales tax
            'KE': Decimal('16.00'),  # Kenya VAT
            'UG': Decimal('18.00'),  # Uganda VAT
            'TZ': Decimal('18.00'),  # Tanzania VAT
            'NG': Decimal('7.50'),   # Nigeria VAT
            'GH': Decimal('12.50'),  # Ghana VAT
        }
        
        # Get user's country (this would come from user profile)
        user_country = getattr(user, 'country', 'US')
        
        return tax_rates.get(user_country, Decimal('0.00'))
    
    @staticmethod
    def get_billing_summary(user: User, period: str = 'current_month') -> Dict[str, Any]:
        """
        Get billing summary for a user.
        """
        try:
            # Calculate date range based on period
            now = timezone.now()
            
            if period == 'current_month':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = (start_date + relativedelta(months=1)) - timedelta(seconds=1)
            elif period == 'last_month':
                start_date = (now.replace(day=1) - relativedelta(months=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
            elif period == 'current_year':
                start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = now
            else:
                # Default to current month
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                end_date = (start_date + relativedelta(months=1)) - timedelta(seconds=1)
            
            # Get billing-related payments
            payments = Payment.objects.filter(
                payer=user,
                payment_type__in=['subscription', 'invoice', 'billing'],
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            total_amount = sum(p.amount for p in payments.filter(status=Payment.Status.COMPLETED))
            total_count = payments.count()
            successful_count = payments.filter(status=Payment.Status.COMPLETED).count()
            failed_count = payments.filter(status=Payment.Status.FAILED).count()
            
            return {
                'period': period,
                'start_date': start_date,
                'end_date': end_date,
                'total_amount': total_amount,
                'total_payments': total_count,
                'successful_payments': successful_count,
                'failed_payments': failed_count,
                'success_rate': (successful_count / total_count * 100) if total_count > 0 else 0,
                'average_payment': total_amount / successful_count if successful_count > 0 else Decimal('0.00')
            }
        
        except Exception as e:
            return {
                'error': f"Error generating billing summary: {str(e)}"
            }
