"""
Service for wallet operations.
"""

from decimal import Decimal
from django.db import transaction

from apps.payments.models import Wallet, Transaction


class WalletService:
    """
    Service for handling wallet operations.
    """
    
    @staticmethod
    def get_or_create_wallet(user, wallet_type):
        """
        Get or create wallet for user.
        """
        wallet, created = Wallet.objects.get_or_create(
            user=user,
            defaults={'wallet_type': wallet_type}
        )
        return wallet
    
    @staticmethod
    def transfer_funds(from_wallet, to_wallet, amount, description=""):
        """
        Transfer funds between wallets.
        """
        if amount <= 0:
            return False, "Transfer amount must be positive"
        
        if not from_wallet.can_withdraw(amount):
            return False, "Insufficient balance in source wallet"
        
        try:
            with transaction.atomic():
                # Create transfer transactions
                debit_transaction = Transaction.objects.create(
                    wallet=from_wallet,
                    transaction_type=Transaction.TransactionType.TRANSFER,
                    amount=amount,
                    description=description or f"Transfer to {to_wallet.user}",
                    status=Transaction.Status.COMPLETED,
                    to_wallet=to_wallet
                )
                
                credit_transaction = Transaction.objects.create(
                    wallet=to_wallet,
                    transaction_type=Transaction.TransactionType.TRANSFER,
                    amount=amount,
                    description=description or f"Transfer from {from_wallet.user}",
                    status=Transaction.Status.COMPLETED,
                    from_wallet=from_wallet
                )
                
                # Update wallet balances
                from_wallet.balance -= amount
                from_wallet.total_spent += amount
                from_wallet.save(update_fields=['balance', 'total_spent'])
                
                to_wallet.balance += amount
                to_wallet.total_earned += amount
                to_wallet.save(update_fields=['balance', 'total_earned'])
                
                return True, "Transfer completed successfully"
        
        except Exception as e:
            return False, f"Transfer failed: {str(e)}"
    
    @staticmethod
    def freeze_wallet(wallet, reason):
        """
        Freeze a wallet.
        """
        wallet.is_frozen = True
        wallet.freeze_reason = reason
        wallet.save(update_fields=['is_frozen', 'freeze_reason'])
        
        return True, "Wallet frozen successfully"
    
    @staticmethod
    def unfreeze_wallet(wallet):
        """
        Unfreeze a wallet.
        """
        wallet.is_frozen = False
        wallet.freeze_reason = None
        wallet.save(update_fields=['is_frozen', 'freeze_reason'])
        
        return True, "Wallet unfrozen successfully"
    
    @staticmethod
    def get_wallet_transactions(wallet, limit=50, offset=0):
        """
        Get wallet transaction history.
        """
        return Transaction.objects.filter(
            wallet=wallet
        ).order_by('-created_at')[offset:offset + limit]
    
    @staticmethod
    def calculate_wallet_statistics(wallet, days=30):
        """
        Calculate wallet statistics for the specified period.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        transactions = Transaction.objects.filter(
            wallet=wallet,
            created_at__gte=start_date,
            created_at__lte=end_date,
            status=Transaction.Status.COMPLETED
        )
        
        # Calculate statistics
        total_credits = transactions.filter(
            transaction_type__in=[
                Transaction.TransactionType.CREDIT,
                Transaction.TransactionType.BONUS
            ]
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        total_debits = transactions.filter(
            transaction_type__in=[
                Transaction.TransactionType.DEBIT,
                Transaction.TransactionType.FEE,
                Transaction.TransactionType.PENALTY
            ]
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')
        
        transaction_count = transactions.count()
        
        return {
            'period_days': days,
            'total_credits': total_credits,
            'total_debits': total_debits,
            'net_change': total_credits - total_debits,
            'transaction_count': transaction_count,
            'average_transaction': (total_credits + total_debits) / transaction_count if transaction_count > 0 else Decimal('0.00')
        }
    
    @staticmethod
    def process_auto_withdrawals():
        """
        Process automatic withdrawals for eligible wallets.
        """
        from apps.payments.services.payment_service import PaymentService
        
        # Get wallets with auto-withdrawal enabled
        eligible_wallets = Wallet.objects.filter(
            auto_withdraw_enabled=True,
            is_active=True,
            is_frozen=False,
            balance__gte=models.F('auto_withdraw_threshold')
        )
        
        processed_count = 0
        
        for wallet in eligible_wallets:
            # Get user's default withdrawal method
            default_method = wallet.user.payment_methods.filter(
                is_default=True,
                is_active=True,
                method_type__in=[
                    PaymentMethod.MethodType.BANK_ACCOUNT,
                    PaymentMethod.MethodType.MOBILE_MONEY
                ]
            ).first()
            
            if default_method:
                # Calculate withdrawal amount (leave some buffer)
                withdrawal_amount = wallet.balance - Decimal('10.00')  # Keep $10 buffer
                
                if withdrawal_amount >= wallet.auto_withdraw_threshold:
                    success, message = PaymentService.process_withdrawal(
                        wallet.user,
                        withdrawal_amount,
                        default_method
                    )
                    
                    if success:
                        processed_count += 1
        
        return processed_count
