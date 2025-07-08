"""
Refund service for handling payment refunds.
"""

from typing import Dict, Any, Tuple, Optional, List
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

from apps.payments.models import Payment, Refund, PaymentSettings
from apps.payments.utils import is_payment_refundable, calculate_refund_amount

User = get_user_model()


class RefundService:
    """
    Service for handling payment refunds.
    """
    
    @staticmethod
    def create_refund_request(payment: Payment, requested_by: User, 
                            refund_type: str = 'full', amount: Decimal = None,
                            reason: str = None, description: str = None) -> Tuple[bool, str, Optional[Refund]]:
        """
        Create a refund request.
        """
        try:
            # Validate if payment is refundable
            is_refundable, message = is_payment_refundable(payment)
            if not is_refundable:
                return False, message, None
            
            # Calculate refund amount
            if refund_type == 'full':
                refund_amount = payment.amount
            elif refund_type == 'partial':
                if not amount:
                    return False, "Amount is required for partial refunds", None
                if amount > payment.amount:
                    return False, "Refund amount cannot exceed payment amount", None
                refund_amount = amount
            else:
                return False, f"Invalid refund type: {refund_type}", None
            
            # Check if there are existing refunds
            existing_refunds = Refund.objects.filter(
                payment=payment,
                status__in=[Refund.Status.PENDING, Refund.Status.PROCESSING, Refund.Status.COMPLETED]
            )
            
            total_existing_refunds = sum(r.amount for r in existing_refunds)
            if total_existing_refunds + refund_amount > payment.amount:
                return False, "Total refund amount would exceed payment amount", None
            
            with transaction.atomic():
                # Create refund request
                refund = Refund.objects.create(
                    payment=payment,
                    amount=refund_amount,
                    reason=reason or 'Customer request',
                    description=description,
                    requested_by=requested_by,
                    status=Refund.Status.PENDING
                )
                
                # Update payment status if full refund
                if refund_type == 'full' and not existing_refunds:
                    payment.status = Payment.Status.REFUND_PENDING
                    payment.save()
                elif existing_refunds or refund_type == 'partial':
                    payment.status = Payment.Status.PARTIALLY_REFUNDED
                    payment.save()
                
                return True, "Refund request created successfully", refund
        
        except Exception as e:
            return False, f"Error creating refund request: {str(e)}", None
    
    @staticmethod
    def process_refund(refund: Refund, processed_by: User = None) -> Tuple[bool, str]:
        """
        Process a refund request.
        """
        try:
            if refund.status != Refund.Status.PENDING:
                return False, f"Refund is not in pending status: {refund.status}"
            
            # Update refund status
            refund.status = Refund.Status.PROCESSING
            refund.processed_by = processed_by
            refund.processed_at = timezone.now()
            refund.save()
            
            # Process refund through payment processor
            from apps.payments.services.payment_processor import PaymentProcessor
            processor = PaymentProcessor()
            
            success, message = processor.process_refund(refund)
            
            if success:
                refund.status = Refund.Status.COMPLETED
                refund.completed_at = timezone.now()
                refund.save()
                
                # Update payment status
                RefundService._update_payment_refund_status(refund.payment)
                
                # Process wallet credit if applicable
                RefundService._process_wallet_credit(refund)
                
                return True, "Refund processed successfully"
            else:
                refund.status = Refund.Status.FAILED
                refund.failure_reason = message
                refund.failed_at = timezone.now()
                refund.save()
                
                return False, f"Refund processing failed: {message}"
        
        except Exception as e:
            refund.status = Refund.Status.FAILED
            refund.failure_reason = str(e)
            refund.failed_at = timezone.now()
            refund.save()
            
            return False, f"Error processing refund: {str(e)}"
    
    @staticmethod
    def approve_refund(refund: Refund, approved_by: User, notes: str = None) -> Tuple[bool, str]:
        """
        Approve a refund request.
        """
        try:
            if refund.status != Refund.Status.PENDING:
                return False, f"Refund is not in pending status: {refund.status}"
            
            # Update refund with approval
            refund.approved_by = approved_by
            refund.approved_at = timezone.now()
            refund.admin_notes = notes
            refund.save()
            
            # Process the refund
            return RefundService.process_refund(refund, approved_by)
        
        except Exception as e:
            return False, f"Error approving refund: {str(e)}"
    
    @staticmethod
    def reject_refund(refund: Refund, rejected_by: User, reason: str) -> Tuple[bool, str]:
        """
        Reject a refund request.
        """
        try:
            if refund.status != Refund.Status.PENDING:
                return False, f"Refund is not in pending status: {refund.status}"
            
            # Update refund with rejection
            refund.status = Refund.Status.REJECTED
            refund.rejected_by = rejected_by
            refund.rejected_at = timezone.now()
            refund.rejection_reason = reason
            refund.save()
            
            # Revert payment status if needed
            RefundService._update_payment_refund_status(refund.payment)
            
            return True, "Refund request rejected"
        
        except Exception as e:
            return False, f"Error rejecting refund: {str(e)}"
    
    @staticmethod
    def cancel_refund(refund: Refund, cancelled_by: User, reason: str = None) -> Tuple[bool, str]:
        """
        Cancel a refund request.
        """
        try:
            if refund.status not in [Refund.Status.PENDING, Refund.Status.PROCESSING]:
                return False, f"Refund cannot be cancelled in current status: {refund.status}"
            
            # Update refund with cancellation
            refund.status = Refund.Status.CANCELLED
            refund.cancelled_by = cancelled_by
            refund.cancelled_at = timezone.now()
            refund.cancellation_reason = reason
            refund.save()
            
            # Revert payment status if needed
            RefundService._update_payment_refund_status(refund.payment)
            
            return True, "Refund request cancelled"
        
        except Exception as e:
            return False, f"Error cancelling refund: {str(e)}"
    
    @staticmethod
    def get_refund_eligibility(payment: Payment) -> Dict[str, Any]:
        """
        Check refund eligibility for a payment.
        """
        is_eligible, reason = is_payment_refundable(payment)
        
        eligibility_info = {
            'is_eligible': is_eligible,
            'reason': reason,
            'payment_id': str(payment.payment_id),
            'payment_status': payment.status,
            'payment_amount': payment.amount,
            'currency': payment.currency
        }
        
        if is_eligible:
            # Calculate available refund amount
            existing_refunds = Refund.objects.filter(
                payment=payment,
                status__in=[Refund.Status.PENDING, Refund.Status.PROCESSING, Refund.Status.COMPLETED]
            )
            
            total_refunded = sum(r.amount for r in existing_refunds)
            available_amount = payment.amount - total_refunded
            
            eligibility_info.update({
                'available_refund_amount': available_amount,
                'total_refunded': total_refunded,
                'existing_refunds_count': existing_refunds.count(),
                'refund_deadline': payment.completed_at + timedelta(days=30) if payment.completed_at else None
            })
        
        return eligibility_info
    
    @staticmethod
    def get_refund_history(payment: Payment) -> List[Dict[str, Any]]:
        """
        Get refund history for a payment.
        """
        refunds = Refund.objects.filter(payment=payment).order_by('-created_at')
        
        history = []
        for refund in refunds:
            refund_info = {
                'refund_id': str(refund.refund_id),
                'amount': refund.amount,
                'status': refund.status,
                'reason': refund.reason,
                'description': refund.description,
                'created_at': refund.created_at,
                'requested_by': refund.requested_by.get_full_name() if refund.requested_by else None
            }
            
            if refund.status == Refund.Status.COMPLETED:
                refund_info.update({
                    'completed_at': refund.completed_at,
                    'processed_by': refund.processed_by.get_full_name() if refund.processed_by else None
                })
            elif refund.status == Refund.Status.FAILED:
                refund_info.update({
                    'failed_at': refund.failed_at,
                    'failure_reason': refund.failure_reason
                })
            elif refund.status == Refund.Status.REJECTED:
                refund_info.update({
                    'rejected_at': refund.rejected_at,
                    'rejected_by': refund.rejected_by.get_full_name() if refund.rejected_by else None,
                    'rejection_reason': refund.rejection_reason
                })
            
            history.append(refund_info)
        
        return history
    
    @staticmethod
    def _update_payment_refund_status(payment: Payment) -> None:
        """
        Update payment status based on refund status.
        """
        refunds = Refund.objects.filter(
            payment=payment,
            status__in=[Refund.Status.PENDING, Refund.Status.PROCESSING, Refund.Status.COMPLETED]
        )
        
        if not refunds.exists():
            # No active refunds, revert to completed
            if payment.status in [Payment.Status.REFUND_PENDING, Payment.Status.PARTIALLY_REFUNDED]:
                payment.status = Payment.Status.COMPLETED
                payment.save()
            return
        
        total_refunded = sum(r.amount for r in refunds.filter(status=Refund.Status.COMPLETED))
        pending_refunds = refunds.filter(status__in=[Refund.Status.PENDING, Refund.Status.PROCESSING])
        
        if total_refunded >= payment.amount:
            payment.status = Payment.Status.REFUNDED
        elif total_refunded > 0:
            payment.status = Payment.Status.PARTIALLY_REFUNDED
        elif pending_refunds.exists():
            payment.status = Payment.Status.REFUND_PENDING
        else:
            payment.status = Payment.Status.COMPLETED
        
        payment.save()
    
    @staticmethod
    def _process_wallet_credit(refund: Refund) -> None:
        """
        Process wallet credit for refund if applicable.
        """
        try:
            # Check if refund should be credited to wallet
            if refund.payment.payment_method and refund.payment.payment_method.method_type == 'wallet':
                from apps.payments.services.wallet_service import WalletService
                
                # Credit refund amount to user's wallet
                WalletService.credit_wallet(
                    user=refund.payment.payer,
                    amount=refund.amount,
                    description=f"Refund for payment {refund.payment.payment_id}",
                    reference=f"refund_{refund.refund_id}"
                )
        
        except Exception as e:
            # Log error but don't fail the refund
            import logging
            logger = logging.getLogger('payments.refund')
            logger.error(f"Failed to process wallet credit for refund {refund.refund_id}: {str(e)}")
    
    @staticmethod
    def get_refund_statistics(start_date=None, end_date=None) -> Dict[str, Any]:
        """
        Get refund statistics for a given period.
        """
        queryset = Refund.objects.all()
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        total_refunds = queryset.count()
        completed_refunds = queryset.filter(status=Refund.Status.COMPLETED).count()
        pending_refunds = queryset.filter(status=Refund.Status.PENDING).count()
        failed_refunds = queryset.filter(status=Refund.Status.FAILED).count()
        rejected_refunds = queryset.filter(status=Refund.Status.REJECTED).count()
        
        total_amount = sum(r.amount for r in queryset.filter(status=Refund.Status.COMPLETED))
        
        return {
            'total_refunds': total_refunds,
            'completed_refunds': completed_refunds,
            'pending_refunds': pending_refunds,
            'failed_refunds': failed_refunds,
            'rejected_refunds': rejected_refunds,
            'total_refunded_amount': total_amount,
            'success_rate': (completed_refunds / total_refunds * 100) if total_refunds > 0 else 0,
            'average_refund_amount': total_amount / completed_refunds if completed_refunds > 0 else 0
        }
