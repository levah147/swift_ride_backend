# Generated by Django 5.2.2 on 2025-06-08 11:14

import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('rides', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentSettings',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('platform_fee_percentage', models.DecimalField(decimal_places=2, default=Decimal('10.00'), help_text='Platform fee percentage', max_digits=5)),
                ('minimum_platform_fee', models.DecimalField(decimal_places=2, default=Decimal('0.50'), help_text='Minimum platform fee amount', max_digits=8)),
                ('maximum_platform_fee', models.DecimalField(decimal_places=2, default=Decimal('50.00'), help_text='Maximum platform fee amount', max_digits=8)),
                ('card_processing_fee_percentage', models.DecimalField(decimal_places=2, default=Decimal('2.90'), help_text='Card processing fee percentage', max_digits=5)),
                ('card_processing_fee_fixed', models.DecimalField(decimal_places=2, default=Decimal('0.30'), help_text='Fixed card processing fee', max_digits=5)),
                ('minimum_withdrawal_amount', models.DecimalField(decimal_places=2, default=Decimal('10.00'), max_digits=8)),
                ('withdrawal_fee', models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=8)),
                ('auto_withdrawal_enabled', models.BooleanField(default=True)),
                ('auto_withdrawal_schedule', models.CharField(default='daily', help_text='daily, weekly, monthly', max_length=20)),
                ('default_currency', models.CharField(choices=[('USD', 'US Dollar'), ('KES', 'Kenyan Shilling'), ('UGX', 'Ugandan Shilling'), ('TZS', 'Tanzanian Shilling'), ('NGN', 'Nigerian Naira'), ('GHS', 'Ghanaian Cedi')], default='USD', max_length=3)),
                ('supported_currencies', models.JSONField(default=list, help_text='List of supported currency codes')),
                ('cash_payments_enabled', models.BooleanField(default=True)),
                ('card_payments_enabled', models.BooleanField(default=True)),
                ('mobile_money_enabled', models.BooleanField(default=True)),
                ('fraud_detection_enabled', models.BooleanField(default=True)),
                ('maximum_daily_transaction_amount', models.DecimalField(decimal_places=2, default=Decimal('1000.00'), max_digits=10)),
            ],
            options={
                'verbose_name_plural': 'Payment Settings',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('is_deleted', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('payment_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('payment_type', models.CharField(choices=[('ride_payment', 'Ride Payment'), ('wallet_topup', 'Wallet Top-up'), ('withdrawal', 'Withdrawal'), ('refund', 'Refund'), ('commission', 'Commission'), ('bonus', 'Bonus'), ('penalty', 'Penalty')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('currency', models.CharField(choices=[('USD', 'US Dollar'), ('KES', 'Kenyan Shilling'), ('UGX', 'Ugandan Shilling'), ('TZS', 'Tanzanian Shilling'), ('NGN', 'Nigerian Naira'), ('GHS', 'Ghanaian Cedi')], default='USD', max_length=3)),
                ('platform_fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=8)),
                ('payment_processing_fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=8)),
                ('gross_amount', models.DecimalField(decimal_places=2, help_text='Amount before fees', max_digits=10)),
                ('net_amount', models.DecimalField(decimal_places=2, help_text='Amount after fees', max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded'), ('partially_refunded', 'Partially Refunded')], default='pending', max_length=20)),
                ('provider', models.CharField(blank=True, max_length=50, null=True)),
                ('provider_transaction_id', models.CharField(blank=True, max_length=255, null=True)),
                ('provider_fee', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=8)),
                ('initiated_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('failed_at', models.DateTimeField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('failure_reason', models.TextField(blank=True, null=True)),
                ('payee', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payments_received', to=settings.AUTH_USER_MODEL)),
                ('payer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments_made', to=settings.AUTH_USER_MODEL)),
                ('ride', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='rides.ride')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('total_transactions', models.PositiveIntegerField(default=0)),
                ('successful_transactions', models.PositiveIntegerField(default=0)),
                ('failed_transactions', models.PositiveIntegerField(default=0)),
                ('total_volume', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('successful_volume', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('platform_fees_collected', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('processing_fees_paid', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('card_transactions', models.PositiveIntegerField(default=0)),
                ('cash_transactions', models.PositiveIntegerField(default=0)),
                ('mobile_money_transactions', models.PositiveIntegerField(default=0)),
                ('wallet_transactions', models.PositiveIntegerField(default=0)),
                ('success_rate', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=5)),
                ('refunds_issued', models.PositiveIntegerField(default=0)),
                ('refund_amount', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('disputes_opened', models.PositiveIntegerField(default=0)),
            ],
            options={
                'verbose_name_plural': 'Payment Analytics',
                'ordering': ['-date'],
                'unique_together': {('date',)},
            },
        ),
        migrations.CreateModel(
            name='PaymentDispute',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('dispute_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('dispute_type', models.CharField(choices=[('chargeback', 'Chargeback'), ('inquiry', 'Inquiry'), ('fraud', 'Fraud'), ('authorization', 'Authorization'), ('processing_error', 'Processing Error')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('status', models.CharField(choices=[('open', 'Open'), ('under_review', 'Under Review'), ('resolved', 'Resolved'), ('lost', 'Lost'), ('won', 'Won'), ('closed', 'Closed')], default='open', max_length=15)),
                ('provider_dispute_id', models.CharField(blank=True, max_length=255, null=True)),
                ('opened_at', models.DateTimeField(auto_now_add=True)),
                ('due_date', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('reason', models.TextField()),
                ('evidence', models.JSONField(blank=True, default=dict)),
                ('resolution_notes', models.TextField(blank=True, null=True)),
                ('assigned_to', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='assigned_disputes', to=settings.AUTH_USER_MODEL)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='disputes', to='payments.payment')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PaymentMethod',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('method_type', models.CharField(choices=[('card', 'Credit/Debit Card'), ('bank_account', 'Bank Account'), ('mobile_money', 'Mobile Money'), ('digital_wallet', 'Digital Wallet'), ('cash', 'Cash')], max_length=20)),
                ('provider', models.CharField(choices=[('stripe', 'Stripe'), ('paypal', 'PayPal'), ('mpesa', 'M-Pesa'), ('airtel_money', 'Airtel Money'), ('bank_transfer', 'Bank Transfer'), ('cash', 'Cash')], max_length=20)),
                ('display_name', models.CharField(max_length=100)),
                ('last_four', models.CharField(blank=True, max_length=4, null=True)),
                ('provider_payment_method_id', models.CharField(blank=True, max_length=255, null=True)),
                ('provider_customer_id', models.CharField(blank=True, max_length=255, null=True)),
                ('card_brand', models.CharField(blank=True, max_length=20, null=True)),
                ('card_exp_month', models.IntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(12)])),
                ('card_exp_year', models.IntegerField(blank=True, null=True)),
                ('bank_name', models.CharField(blank=True, max_length=100, null=True)),
                ('account_type', models.CharField(blank=True, max_length=20, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=20, null=True)),
                ('is_default', models.BooleanField(default=False)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_methods', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-is_default', '-created_at'],
            },
        ),
        migrations.AddField(
            model_name='payment',
            name='payment_method',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='payments', to='payments.paymentmethod'),
        ),
        migrations.CreateModel(
            name='Refund',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('refund_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('refund_type', models.CharField(choices=[('full', 'Full Refund'), ('partial', 'Partial Refund')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('reason', models.CharField(choices=[('ride_cancelled', 'Ride Cancelled'), ('driver_no_show', 'Driver No Show'), ('poor_service', 'Poor Service'), ('technical_issue', 'Technical Issue'), ('duplicate_charge', 'Duplicate Charge'), ('fraudulent', 'Fraudulent Transaction'), ('other', 'Other')], max_length=20)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('processing', 'Processing'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=15)),
                ('provider_refund_id', models.CharField(blank=True, max_length=255, null=True)),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('admin_notes', models.TextField(blank=True, null=True)),
                ('payment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refunds', to='payments.payment')),
                ('processed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='processed_refunds', to=settings.AUTH_USER_MODEL)),
                ('requested_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='requested_refunds', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Wallet',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('wallet_type', models.CharField(choices=[('rider', 'Rider Wallet'), ('driver', 'Driver Wallet'), ('admin', 'Admin Wallet')], max_length=10)),
                ('balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('pending_balance', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('total_earned', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('total_spent', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('auto_withdraw_enabled', models.BooleanField(default=False)),
                ('auto_withdraw_threshold', models.DecimalField(decimal_places=2, default=Decimal('100.00'), max_digits=8)),
                ('is_active', models.BooleanField(default=True)),
                ('is_frozen', models.BooleanField(default=False)),
                ('freeze_reason', models.TextField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='wallet', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('transaction_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('transaction_type', models.CharField(choices=[('credit', 'Credit'), ('debit', 'Debit'), ('transfer', 'Transfer'), ('refund', 'Refund'), ('fee', 'Fee'), ('bonus', 'Bonus'), ('penalty', 'Penalty')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('balance_before', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('balance_after', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=10)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'), ('cancelled', 'Cancelled')], default='pending', max_length=10)),
                ('description', models.TextField()),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('payment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='payments.payment')),
                ('ride', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='rides.ride')),
                ('from_wallet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='outgoing_transfers', to='payments.wallet')),
                ('to_wallet', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='incoming_transfers', to='payments.wallet')),
                ('wallet', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='transactions', to='payments.wallet')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['payer', 'status'], name='payments_pa_payer_i_ebdbf4_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['payee', 'status'], name='payments_pa_payee_i_80dac9_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['payment_type', 'created_at'], name='payments_pa_payment_63f0d0_idx'),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(fields=['provider_transaction_id'], name='payments_pa_provide_edad36_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['wallet', 'transaction_type'], name='payments_tr_wallet__f5c525_idx'),
        ),
        migrations.AddIndex(
            model_name='transaction',
            index=models.Index(fields=['status', 'created_at'], name='payments_tr_status_e3597b_idx'),
        ),
    ]
