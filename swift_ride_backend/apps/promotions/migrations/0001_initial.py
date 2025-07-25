# Generated by Django 4.2.23 on 2025-06-10 22:08

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('location', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('vehicles', '0001_initial'),
        ('rides', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoyaltyProgram',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('points_per_dollar', models.DecimalField(decimal_places=2, default=1, max_digits=5)),
                ('points_per_ride', models.PositiveIntegerField(default=10)),
                ('bonus_points_threshold', models.PositiveIntegerField(default=100)),
                ('bonus_points_multiplier', models.DecimalField(decimal_places=2, default=1.5, max_digits=3)),
                ('points_to_dollar_ratio', models.DecimalField(decimal_places=2, default=100, max_digits=5)),
                ('minimum_redemption_points', models.PositiveIntegerField(default=500)),
            ],
            options={
                'db_table': 'loyalty_programs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('promotion_type', models.CharField(choices=[('discount', 'Discount'), ('referral', 'Referral'), ('coupon', 'Coupon'), ('cashback', 'Cashback'), ('free_ride', 'Free Ride'), ('loyalty', 'Loyalty')], max_length=20)),
                ('discount_type', models.CharField(choices=[('percentage', 'Percentage'), ('fixed_amount', 'Fixed Amount'), ('free_delivery', 'Free Delivery')], max_length=20)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('paused', 'Paused'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('code', models.CharField(blank=True, max_length=50, null=True, unique=True)),
                ('discount_percentage', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('discount_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('max_discount_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('usage_limit_per_user', models.PositiveIntegerField(default=1)),
                ('total_usage_limit', models.PositiveIntegerField(blank=True, null=True)),
                ('minimum_ride_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField()),
                ('target_user_type', models.CharField(choices=[('all', 'All Users'), ('new', 'New Users'), ('existing', 'Existing Users'), ('riders', 'Riders Only'), ('drivers', 'Drivers Only'), ('vip', 'VIP Users')], default='all', max_length=20)),
                ('referrer_reward_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('referee_reward_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)])),
                ('total_usage_count', models.PositiveIntegerField(default=0)),
                ('total_discount_given', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total_revenue_impact', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('is_stackable', models.BooleanField(default=False)),
                ('is_auto_apply', models.BooleanField(default=False)),
                ('requires_first_ride', models.BooleanField(default=False)),
                ('target_cities', models.ManyToManyField(blank=True, to='location.city')),
                ('target_vehicle_types', models.ManyToManyField(blank=True, to='vehicles.vehicletype')),
            ],
            options={
                'db_table': 'promotions',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReferralProgram',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('referrer_reward_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('referee_reward_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('minimum_rides_for_referrer', models.PositiveIntegerField(default=0)),
                ('minimum_rides_for_referee', models.PositiveIntegerField(default=1)),
                ('reward_expiry_days', models.PositiveIntegerField(default=30)),
                ('max_referrals_per_user', models.PositiveIntegerField(blank=True, null=True)),
                ('max_total_referrals', models.PositiveIntegerField(blank=True, null=True)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'referral_programs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PromotionCampaign',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('campaign_type', models.CharField(choices=[('email', 'Email Campaign'), ('push', 'Push Notification'), ('sms', 'SMS Campaign'), ('in_app', 'In-App Banner'), ('social', 'Social Media')], max_length=20)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('scheduled', 'Scheduled'), ('running', 'Running'), ('paused', 'Paused'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], default='draft', max_length=20)),
                ('target_user_type', models.CharField(choices=[('all', 'All Users'), ('new', 'New Users'), ('existing', 'Existing Users'), ('riders', 'Riders Only'), ('drivers', 'Drivers Only'), ('vip', 'VIP Users')], default='all', max_length=20)),
                ('target_age_min', models.PositiveIntegerField(blank=True, null=True)),
                ('target_age_max', models.PositiveIntegerField(blank=True, null=True)),
                ('subject', models.CharField(blank=True, max_length=200, null=True)),
                ('message', models.TextField()),
                ('image_url', models.URLField(blank=True, null=True)),
                ('call_to_action', models.CharField(blank=True, max_length=100, null=True)),
                ('scheduled_start', models.DateTimeField()),
                ('scheduled_end', models.DateTimeField(blank=True, null=True)),
                ('target_audience_size', models.PositiveIntegerField(default=0)),
                ('messages_sent', models.PositiveIntegerField(default=0)),
                ('messages_delivered', models.PositiveIntegerField(default=0)),
                ('messages_opened', models.PositiveIntegerField(default=0)),
                ('messages_clicked', models.PositiveIntegerField(default=0)),
                ('conversions', models.PositiveIntegerField(default=0)),
                ('promotion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='campaigns', to='promotions.promotion')),
                ('target_cities', models.ManyToManyField(blank=True, to='location.city')),
            ],
            options={
                'db_table': 'promotion_campaigns',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LoyaltyAccount',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('total_points_earned', models.PositiveIntegerField(default=0)),
                ('total_points_redeemed', models.PositiveIntegerField(default=0)),
                ('current_points_balance', models.PositiveIntegerField(default=0)),
                ('tier_level', models.CharField(choices=[('bronze', 'Bronze'), ('silver', 'Silver'), ('gold', 'Gold'), ('platinum', 'Platinum'), ('diamond', 'Diamond')], default='bronze', max_length=20)),
                ('tier_progress', models.PositiveIntegerField(default=0)),
                ('total_rides_count', models.PositiveIntegerField(default=0)),
                ('total_amount_spent', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to='promotions.loyaltyprogram')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty_account', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'loyalty_accounts',
            },
        ),
        migrations.CreateModel(
            name='Referral',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('referral_code', models.CharField(max_length=50, unique=True)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('completed', 'Completed'), ('rewarded', 'Rewarded'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='pending', max_length=20)),
                ('signup_date', models.DateTimeField(auto_now_add=True)),
                ('completion_date', models.DateTimeField(blank=True, null=True)),
                ('reward_date', models.DateTimeField(blank=True, null=True)),
                ('expiry_date', models.DateTimeField()),
                ('referrer_reward_given', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('referee_reward_given', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referrals', to='promotions.referralprogram')),
                ('referee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referrals_received', to=settings.AUTH_USER_MODEL)),
                ('referrer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='referrals_made', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'referrals',
                'ordering': ['-signup_date'],
                'indexes': [models.Index(fields=['referral_code'], name='referrals_referra_3eadcc_idx'), models.Index(fields=['status'], name='referrals_status_135a0e_idx')],
                'unique_together': {('referrer', 'referee')},
            },
        ),
        migrations.CreateModel(
            name='PromotionUsage',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('discount_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('original_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('final_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('usage_date', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True, null=True)),
                ('promotion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='usages', to='promotions.promotion')),
                ('ride', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rides.ride')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='promotion_usages', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'db_table': 'promotion_usages',
                'ordering': ['-usage_date'],
                'indexes': [models.Index(fields=['promotion', 'user'], name='promotion_u_promoti_a8d0ef_idx'), models.Index(fields=['usage_date'], name='promotion_u_usage_d_ba8b5b_idx')],
            },
        ),
        migrations.CreateModel(
            name='PromotionAnalytics',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('date', models.DateField()),
                ('total_uses', models.PositiveIntegerField(default=0)),
                ('unique_users', models.PositiveIntegerField(default=0)),
                ('new_users', models.PositiveIntegerField(default=0)),
                ('returning_users', models.PositiveIntegerField(default=0)),
                ('total_discount_given', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total_revenue_generated', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('average_order_value', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('conversion_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('cost_per_acquisition', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('return_on_investment', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('promotion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='analytics', to='promotions.promotion')),
            ],
            options={
                'db_table': 'promotion_analytics',
                'ordering': ['-date'],
                'unique_together': {('promotion', 'date')},
            },
        ),
        migrations.AddIndex(
            model_name='promotion',
            index=models.Index(fields=['code'], name='promotions_code_893bd9_idx'),
        ),
        migrations.AddIndex(
            model_name='promotion',
            index=models.Index(fields=['status', 'start_date', 'end_date'], name='promotions_status_e41777_idx'),
        ),
        migrations.AddIndex(
            model_name='promotion',
            index=models.Index(fields=['promotion_type'], name='promotions_promoti_b9bf01_idx'),
        ),
        migrations.AlterUniqueTogether(
            name='loyaltyaccount',
            unique_together={('user', 'program')},
        ),
    ]
