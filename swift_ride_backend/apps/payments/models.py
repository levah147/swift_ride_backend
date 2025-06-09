"""
Payment models for Swift Ride project.
"""

import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.common.models import BaseModel, SoftDeleteModel


class PaymentMethod(BaseModel):
    """
    Model for storing user payment methods.
    """
    class MethodType(models.TextChoices):
        CARD = 'card', _('Credit/Debit Card')
        BANK_ACCOUNT = 'bank_account', _('Bank Account')
        MOBILE_MONEY = 'mobile_money', _('Mobile Money')
        DIGITAL_WALLET = 'digital_wallet', _('Digital Wallet')
        CASH = 'cash', _('Cash')
    
    class Provider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        PAYPAL = 'paypal', _('PayPal')
        MPESA = 'mpesa', _('M-Pesa')
        AIRTEL_MONEY = 'airtel_money', _('Airtel Money')
        BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
        CASH = 'cash', _('Cash')
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods'
    )
    
    # Basic information
    method_type = models.CharField(
        max_length=20,
        choices=MethodType.choices
    )
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices
    )
    
    # Display information
    display_name = models.CharField(max_length=100)
    last_four = models.CharField(max_length=4, blank=True, null=True)
    
    # Provider-specific data
    provider_payment_method_id = models.CharField(max_length=255, blank=True, null=True)
    provider_customer_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Card-specific fields
    card_brand = models.CharField(max_length=20, blank=True, null=True)
    card_exp_month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        null=True,
        blank=True
    )
    card_exp_year = models.IntegerField(null=True, blank=True)
    
    # Bank account fields
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_type = models.CharField(max_length=20, blank=True, null=True)
    
    # Mobile money fields
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    # Status
    is_default = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user} - {self.display_name}"
    
    def save(self, *args, **kwargs):
        # Ensure only one default payment method per user
        if self.is_default:
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(id=self.id).update(is_default=False)
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if card is expired."""
        if self.method_type == self.MethodType.CARD and self.card_exp_month and self.card_exp_year:
            from django.utils import timezone
            now = timezone.now()
            return (self.card_exp_year < now.year or 
                   (self.card_exp_year == now.year and self.card_exp_month < now.month))
        return False
    
    class Meta:
        ordering = ['-is_default', '-created_at']


class Wallet(BaseModel):
    """
    Model for user wallets.
    """
    class WalletType(models.TextChoices):
        RIDER = 'rider', _('Rider Wallet')
        DRIVER = 'driver', _('Driver Wallet')
        ADMIN = 'admin', _('Admin Wallet')
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    
    wallet_type = models.CharField(
        max_length=10,
        choices=WalletType.choices
    )
    
    # Balance information
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Pending amounts
    pending_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    
    # Lifetime statistics
    total_earned = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Settings
    auto_withdraw_enabled = models.BooleanField(default=False)
    auto_withdraw_threshold = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('100.00')
    )
    
    # Status
    is_active = models.BooleanField(default=True)
    is_frozen = models.BooleanField(default=False)
    freeze_reason = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user} - {self.wallet_type} - ${self.balance}"
    
    @property
    def available_balance(self):
        """Get available balance (total - pending)."""
        return self.balance - self.pending_balance
    
    def can_withdraw(self, amount):
        """Check if user can withdraw the specified amount."""
        return (self.is_active and 
                not self.is_frozen and 
                self.available_balance >= amount)
    
    def add_funds(self, amount, description=""):
        """Add funds to wallet."""
        if amount > 0:
            self.balance += amount
            self.total_earned += amount
            self.save(update_fields=['balance', 'total_earned'])
            
            # Create transaction record
            Transaction.objects.create(
                wallet=self,
                transaction_type=Transaction.TransactionType.CREDIT,
                amount=amount,
                description=description or "Funds added to wallet",
                status=Transaction.Status.COMPLETED
            )
    
    def deduct_funds(self, amount, description=""):
        """Deduct funds from wallet."""
        if amount > 0 and self.can_withdraw(amount):
            self.balance -= amount
            self.total_spent += amount
            self.save(update_fields=['balance', 'total_spent'])
            
            # Create transaction record
            Transaction.objects.create(
                wallet=self,
                transaction_type=Transaction.TransactionType.DEBIT,
                amount=amount,
                description=description or "Funds deducted from wallet",
                status=Transaction.Status.COMPLETED
            )
            return True
        return False
    
    class Meta:
        ordering = ['-created_at']


class Payment(BaseModel, SoftDeleteModel):
    """
    Model for payments.
    """
    class PaymentType(models.TextChoices):
        RIDE_PAYMENT = 'ride_payment', _('Ride Payment')
        WALLET_TOPUP = 'wallet_topup', _('Wallet Top-up')
        WITHDRAWAL = 'withdrawal', _('Withdrawal')
        REFUND = 'refund', _('Refund')
        COMMISSION = 'commission', _('Commission')
        BONUS = 'bonus', _('Bonus')
        PENALTY = 'penalty', _('Penalty')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
        REFUNDED = 'refunded', _('Refunded')
        PARTIALLY_REFUNDED = 'partially_refunded', _('Partially Refunded')
    
    class Currency(models.TextChoices):
        USD = 'USD', _('US Dollar')
        KES = 'KES', _('Kenyan Shilling')
        UGX = 'UGX', _('Ugandan Shilling')
        TZS = 'TZS', _('Tanzanian Shilling')
        NGN = 'NGN', _('Nigerian Naira')
        GHS = 'GHS', _('Ghanaian Cedi')
    
    # Unique payment identifier
    payment_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Payment details
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_made'
    )
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments_received',
        null=True,
        blank=True
    )
    
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentType.choices
    )
    
    # Amount information
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD
    )
    
    # Fee breakdown
    platform_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    payment_processing_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Net amounts
    gross_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount before fees"
    )
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount after fees"
    )
    
    # Payment method
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Provider information
    provider = models.CharField(max_length=50, blank=True, null=True)
    provider_transaction_id = models.CharField(max_length=255, blank=True, null=True)
    provider_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Timestamps
    initiated_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    description = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True, null=True)
    
    # Related objects
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='payments',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"Payment {self.payment_id} - {self.amount} {self.currency}"
    
    def save(self, *args, **kwargs):
        # Calculate net amount if not set
        if not self.net_amount:
            self.net_amount = self.gross_amount - self.platform_fee - self.payment_processing_fee
        
        super().save(*args, **kwargs)
    
    @property
    def total_fees(self):
        """Calculate total fees."""
        return self.platform_fee + self.payment_processing_fee + self.provider_fee
    
    def mark_as_completed(self):
        """Mark payment as completed."""
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    def mark_as_failed(self, reason):
        """Mark payment as failed."""
        from django.utils import timezone
        self.status = self.Status.FAILED
        self.failed_at = timezone.now()
        self.failure_reason = reason
        self.save(update_fields=['status', 'failed_at', 'failure_reason'])
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payer', 'status']),
            models.Index(fields=['payee', 'status']),
            models.Index(fields=['payment_type', 'created_at']),
            models.Index(fields=['provider_transaction_id']),
        ]


class Transaction(BaseModel):
    """
    Model for wallet transactions.
    """
    class TransactionType(models.TextChoices):
        CREDIT = 'credit', _('Credit')
        DEBIT = 'debit', _('Debit')
        TRANSFER = 'transfer', _('Transfer')
        REFUND = 'refund', _('Refund')
        FEE = 'fee', _('Fee')
        BONUS = 'bonus', _('Bonus')
        PENALTY = 'penalty', _('Penalty')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    # Transaction identifier
    transaction_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Wallet and user
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    
    # Transaction details
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    # Balance tracking
    balance_before = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    balance_after = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Status and description
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING
    )
    description = models.TextField()
    
    # Related objects
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True
    )
    ride = models.ForeignKey(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True
    )
    
    # Transfer-specific fields
    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='outgoing_transfers',
        null=True,
        blank=True
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='incoming_transfers',
        null=True,
        blank=True
    )
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.transaction_type} - {self.amount} - {self.wallet.user}"
    
    def save(self, *args, **kwargs):
        # Set balance before if not set
        if not self.balance_before:
            self.balance_before = self.wallet.balance
        
        # Calculate balance after
        if self.transaction_type == self.TransactionType.CREDIT:
            self.balance_after = self.balance_before + self.amount
        elif self.transaction_type == self.TransactionType.DEBIT:
            self.balance_after = self.balance_before - self.amount
        else:
            self.balance_after = self.balance_before
        
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['wallet', 'transaction_type']),
            models.Index(fields=['status', 'created_at']),
        ]


class Refund(BaseModel):
    """
    Model for payment refunds.
    """
    class RefundType(models.TextChoices):
        FULL = 'full', _('Full Refund')
        PARTIAL = 'partial', _('Partial Refund')
    
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        CANCELLED = 'cancelled', _('Cancelled')
    
    class Reason(models.TextChoices):
        RIDE_CANCELLED = 'ride_cancelled', _('Ride Cancelled')
        DRIVER_NO_SHOW = 'driver_no_show', _('Driver No Show')
        POOR_SERVICE = 'poor_service', _('Poor Service')
        TECHNICAL_ISSUE = 'technical_issue', _('Technical Issue')
        DUPLICATE_CHARGE = 'duplicate_charge', _('Duplicate Charge')
        FRAUDULENT = 'fraudulent', _('Fraudulent Transaction')
        OTHER = 'other', _('Other')
    
    # Refund identifier
    refund_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Original payment
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='refunds'
    )
    
    # Refund details
    refund_type = models.CharField(
        max_length=10,
        choices=RefundType.choices
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    reason = models.CharField(
        max_length=20,
        choices=Reason.choices
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Provider information
    provider_refund_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    description = models.TextField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    
    # Requester information
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_refunds'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='processed_refunds',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"Refund {self.refund_id} - {self.amount}"
    
    def can_refund(self):
        """Check if refund is possible."""
        return (self.payment.status == Payment.Status.COMPLETED and
                self.status == self.Status.PENDING)
    
    def mark_as_completed(self):
        """Mark refund as completed."""
        from django.utils import timezone
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at'])
    
    class Meta:
        ordering = ['-created_at']


class PaymentDispute(BaseModel):
    """
    Model for payment disputes.
    """
    class DisputeType(models.TextChoices):
        CHARGEBACK = 'chargeback', _('Chargeback')
        INQUIRY = 'inquiry', _('Inquiry')
        FRAUD = 'fraud', _('Fraud')
        AUTHORIZATION = 'authorization', _('Authorization')
        PROCESSING_ERROR = 'processing_error', _('Processing Error')
    
    class Status(models.TextChoices):
        OPEN = 'open', _('Open')
        UNDER_REVIEW = 'under_review', _('Under Review')
        RESOLVED = 'resolved', _('Resolved')
        LOST = 'lost', _('Lost')
        WON = 'won', _('Won')
        CLOSED = 'closed', _('Closed')
    
    # Dispute identifier
    dispute_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Related payment
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='disputes'
    )
    
    # Dispute details
    dispute_type = models.CharField(
        max_length=20,
        choices=DisputeType.choices
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    # Status and tracking
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.OPEN
    )
    
    # Provider information
    provider_dispute_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    opened_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Details
    reason = models.TextField()
    evidence = models.JSONField(default=dict, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)
    
    # Staff handling
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='assigned_disputes',
        null=True,
        blank=True
    )
    
    def __str__(self):
        return f"Dispute {self.dispute_id} - {self.dispute_type}"
    
    @property
    def is_overdue(self):
        """Check if dispute is overdue."""
        if self.due_date and self.status in [self.Status.OPEN, self.Status.UNDER_REVIEW]:
            from django.utils import timezone
            return timezone.now() > self.due_date
        return False
    
    class Meta:
        ordering = ['-created_at']


class PaymentSettings(BaseModel):
    """
    Model for payment system settings.
    """
    # Platform fees
    platform_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
        help_text="Platform fee percentage"
    )
    minimum_platform_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.50'),
        help_text="Minimum platform fee amount"
    )
    maximum_platform_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('50.00'),
        help_text="Maximum platform fee amount"
    )
    
    # Payment processing fees
    card_processing_fee_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.90'),
        help_text="Card processing fee percentage"
    )
    card_processing_fee_fixed = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.30'),
        help_text="Fixed card processing fee"
    )
    
    # Withdrawal settings
    minimum_withdrawal_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('10.00')
    )
    withdrawal_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('1.00')
    )
    
    # Auto-withdrawal settings
    auto_withdrawal_enabled = models.BooleanField(default=True)
    auto_withdrawal_schedule = models.CharField(
        max_length=20,
        default='daily',
        help_text="daily, weekly, monthly"
    )
    
    # Currency settings
    default_currency = models.CharField(
        max_length=3,
        choices=Payment.Currency.choices,
        default=Payment.Currency.USD
    )
    supported_currencies = models.JSONField(
        default=list,
        help_text="List of supported currency codes"
    )
    
    # Payment method settings
    cash_payments_enabled = models.BooleanField(default=True)
    card_payments_enabled = models.BooleanField(default=True)
    mobile_money_enabled = models.BooleanField(default=True)
    
    # Security settings
    fraud_detection_enabled = models.BooleanField(default=True)
    maximum_daily_transaction_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1000.00')
    )
    
    def __str__(self):
        return f"Payment Settings - {self.created_at.date()}"
    
    @classmethod
    def get_current_settings(cls):
        """Get current payment settings."""
        return cls.objects.first() or cls.objects.create()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Payment Settings"


class PaymentAnalytics(BaseModel):
    """
    Model for payment analytics and metrics.
    """
    date = models.DateField()
    
    # Transaction volumes
    total_transactions = models.PositiveIntegerField(default=0)
    successful_transactions = models.PositiveIntegerField(default=0)
    failed_transactions = models.PositiveIntegerField(default=0)
    
    # Transaction amounts
    total_volume = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    successful_volume = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Fees collected
    platform_fees_collected = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    processing_fees_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Payment methods breakdown
    card_transactions = models.PositiveIntegerField(default=0)
    cash_transactions = models.PositiveIntegerField(default=0)
    mobile_money_transactions = models.PositiveIntegerField(default=0)
    wallet_transactions = models.PositiveIntegerField(default=0)
    
    # Success rates
    success_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    
    # Refunds and disputes
    refunds_issued = models.PositiveIntegerField(default=0)
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    disputes_opened = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Payment Analytics - {self.date}"
    
    def calculate_success_rate(self):
        """Calculate transaction success rate."""
        if self.total_transactions > 0:
            self.success_rate = (self.successful_transactions / self.total_transactions) * 100
        else:
            self.success_rate = Decimal('0.00')
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
        verbose_name_plural = "Payment Analytics"
