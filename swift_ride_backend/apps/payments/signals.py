"""
Signals for payment models.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.payments.models import Payment, Wallet, Transaction


@receiver(post_save, sender=Payment)
def payment_status_changed(sender, instance, created, **kwargs):
    """
    Handle payment status changes.
    """
    if not created and instance.status == Payment.Status.COMPLETED:
        # Send payment completion notification
        from apps.notifications.services.notification_service import NotificationService
        
        NotificationService.send_payment_notification(
            instance,
            'payment_received'
        )


@receiver(post_save, sender='users.CustomUser')
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Create wallet when user is created.
    """
    if created:
        from apps.payments.services.wallet_service import WalletService
        
        # Determine wallet type based on user type
        if hasattr(instance, 'driver_profile'):
            wallet_type = Wallet.WalletType.DRIVER
        else:
            wallet_type = Wallet.WalletType.RIDER
        
        WalletService.get_or_create_wallet(instance, wallet_type)


@receiver(pre_save, sender=Transaction)
def update_transaction_balances(sender, instance, **kwargs):
    """
    Update transaction balance fields before saving.
    """
    if not instance.balance_before:
        instance.balance_before = instance.wallet.balance
    
    # Calculate balance after based on transaction type
    if instance.transaction_type == Transaction.TransactionType.CREDIT:
        instance.balance_after = instance.balance_before + instance.amount
    elif instance.transaction_type == Transaction.TransactionType.DEBIT:
        instance.balance_after = instance.balance_before - instance.amount
    else:
        instance.balance_after = instance.balance_before
