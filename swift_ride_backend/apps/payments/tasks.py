"""
Celery tasks for payments app.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.payments.models import Payment, PaymentAnalytics, Wallet


@shared_task
def process_pending_payments():
    """
    Process pending payments.
    """
    from apps.payments.services.payment_service import PaymentService
    
    # Get payments that are pending for more than 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)
    
    pending_payments = Payment.objects.filter(
        status=Payment.Status.PENDING,
        created_at__lt=cutoff_time,
        is_deleted=False
    )
    
    processed_count = 0
    
    for payment in pending_payments:
        try:
            success, message = PaymentService.process_payment(payment)
            if success:
                processed_count += 1
        except Exception as e:
            payment.mark_as_failed(f"Processing error: {str(e)}")
    
    return f"Processed {processed_count} pending payments"


@shared_task
def process_auto_withdrawals():
    """
    Process automatic withdrawals.
    """
    from apps.payments.services.wallet_service import WalletService
    
    processed_count = WalletService.process_auto_withdrawals()
    return f"Processed {processed_count} auto-withdrawals"


@shared_task
def generate_payment_analytics():
    """
    Generate daily payment analytics.
    """
    yesterday = timezone.now().date() - timedelta(days=1)
    
    # Get payments from yesterday
    payments = Payment.objects.filter(
        created_at__date=yesterday,
        is_deleted=False
    )
    
    if not payments.exists():
        return "No payments found for analytics generation"
    
    # Calculate metrics
    total_transactions = payments.count()
    successful_transactions = payments.filter(status=Payment.Status.COMPLETED).count()
    failed_transactions = payments.filter(status=Payment.Status.FAILED).count()
    
    successful_payments = payments.filter(status=Payment.Status.COMPLETED)
    total_volume = successful_payments.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    successful_volume = total_volume
    
    platform_fees_collected = successful_payments.aggregate(
        total=models.Sum('platform_fee')
    )['total'] or Decimal('0.00')
    
    processing_fees_paid = successful_payments.aggregate(
        total=models.Sum('payment_processing_fee')
    )['total'] or Decimal('0.00')
    
    # Payment method breakdown
    card_transactions = payments.filter(
        payment_method__method_type='card'
    ).count()
    
    cash_transactions = payments.filter(
        payment_method__isnull=True
    ).count()
    
    mobile_money_transactions = payments.filter(
        payment_method__method_type='mobile_money'
    ).count()
    
    wallet_transactions = payments.filter(
        payment_type='wallet_topup'
    ).count()
    
    # Refunds
    refunds = payments.filter(
        status__in=[Payment.Status.REFUNDED, Payment.Status.PARTIALLY_REFUNDED]
    )
    refunds_issued = refunds.count()
    refund_amount = refunds.aggregate(
        total=models.Sum('amount')
    )['total'] or Decimal('0.00')
    
    # Create or update analytics record
    analytics, created = PaymentAnalytics.objects.get_or_create(
        date=yesterday,
        defaults={
            'total_transactions': total_transactions,
            'successful_transactions': successful_transactions,
            'failed_transactions': failed_transactions,
            'total_volume': total_volume,
            'successful_volume': successful_volume,
            'platform_fees_collected': platform_fees_collected,
            'processing_fees_paid': processing_fees_paid,
            'card_transactions': card_transactions,
            'cash_transactions': cash_transactions,
            'mobile_money_transactions': mobile_money_transactions,
            'wallet_transactions': wallet_transactions,
            'refunds_issued': refunds_issued,
            'refund_amount': refund_amount,
        }
    )
    
    if not created:
        # Update existing record
        analytics.total_transactions = total_transactions
        analytics.successful_transactions = successful_transactions
        analytics.failed_transactions = failed_transactions
        analytics.total_volume = total_volume
        analytics.successful_volume = successful_volume
        analytics.platform_fees_collected = platform_fees_collected
        analytics.processing_fees_paid = processing_fees_paid
        analytics.card_transactions = card_transactions
        analytics.cash_transactions = cash_transactions
        analytics.mobile_money_transactions = mobile_money_transactions
        analytics.wallet_transactions = wallet_transactions
        analytics.refunds_issued = refunds_issued
        analytics.refund_amount = refund_amount
    
    # Calculate success rate
    analytics.calculate_success_rate()
    analytics.save()
    
    return f"Generated payment analytics for {yesterday}"


@shared_task
def cleanup_expired_payment_methods():
    """
    Clean up expired payment methods.
    """
    from apps.payments.models import PaymentMethod
    
    # Deactivate expired cards
    expired_cards = PaymentMethod.objects.filter(
        method_type=PaymentMethod.MethodType.CARD,
        is_active=True
    )
    
    deactivated_count = 0
    
    for card in expired_cards:
        if card.is_expired:
            card.is_active = False
            card.save()
            deactivated_count += 1
    
    return f"Deactivated {deactivated_count} expired payment methods"


@shared_task
def send_payment_reminders():
    """
    Send payment reminders for failed payments.
    """
    from apps.notifications.services.notification_service import NotificationService
    
    # Get failed payments from the last 24 hours
    cutoff_time = timezone.now() - timedelta(hours=24)
    
    failed_payments = Payment.objects.filter(
        status=Payment.Status.FAILED,
        failed_at__gte=cutoff_time,
        payment_type=Payment.PaymentType.RIDE_PAYMENT
    )
    
    reminder_count = 0
    
    for payment in failed_payments:
        # Send reminder notification
        NotificationService.send_payment_notification(
            payment,
            'payment_failed'
        )
        reminder_count += 1
    
    return f"Sent {reminder_count} payment reminders"


@shared_task
def reconcile_wallet_balances():
    """
    Reconcile wallet balances with transaction history.
    """
    from django.db.models import Sum
    from apps.payments.models import Transaction
    
    wallets = Wallet.objects.filter(is_active=True)
    reconciled_count = 0
    discrepancy_count = 0
    
    for wallet in wallets:
        # Calculate balance from transactions
        credits = Transaction.objects.filter(
            wallet=wallet,
            transaction_type__in=[
                Transaction.TransactionType.CREDIT,
                Transaction.TransactionType.BONUS
            ],
            status=Transaction.Status.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        debits = Transaction.objects.filter(
            wallet=wallet,
            transaction_type__in=[
                Transaction.TransactionType.DEBIT,
                Transaction.TransactionType.FEE,
                Transaction.TransactionType.PENALTY
            ],
            status=Transaction.Status.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        calculated_balance = credits - debits
        
        # Check for discrepancies
        if abs(wallet.balance - calculated_balance) > Decimal('0.01'):
            discrepancy_count += 1
            
            # Log discrepancy (in production, you might want to alert admins)
            print(f"Wallet balance discrepancy for user {wallet.user.id}: "
                  f"Recorded: {wallet.balance}, Calculated: {calculated_balance}")
        else:
            reconciled_count += 1
    
    return f"Reconciled {reconciled_count} wallets, found {discrepancy_count} discrepancies"
