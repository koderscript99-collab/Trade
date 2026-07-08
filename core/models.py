from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    phone = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, blank=True)

    referral_code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )

    balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    investment_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    profit_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    referral_balance = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    kyc_verified = models.BooleanField(default=False)
    two_factor_enabled = models.BooleanField(default=False)

    is_admin_user = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username


class InvestmentPlan(models.Model):

    name = models.CharField(max_length=100)

    minimum = models.DecimalField(max_digits=20, decimal_places=2)

    maximum = models.DecimalField(max_digits=20, decimal_places=2)

    roi = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Percentage"
    )

    duration_days = models.PositiveIntegerField()

    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Investment(models.Model):

    STATUS = (
        ("running", "Running"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)

    plan = models.ForeignKey(
        InvestmentPlan,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(max_digits=20, decimal_places=2)

    expected_profit = models.DecimalField(max_digits=20, decimal_places=2)

    total_return = models.DecimalField(max_digits=20, decimal_places=2)

    started_at = models.DateTimeField(auto_now_add=True)

    ends_at = models.DateTimeField()

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="running"
    )

    def __str__(self):
        return f"{self.user} - {self.plan}"
    

class Wallet(models.Model):

    NETWORK = (
        ("BTC","Bitcoin"),
        ("ETH","Ethereum"),
        ("USDT TRC20","USDT TRC20"),
        ("USDT ERC20","USDT ERC20"),
        ("USDT BEP20","USDT BEP20"),
        ("BNB","BNB"),
        ("DOGE","Dogecoin"),
        ("LTC","Litecoin"),
    )

    coin = models.CharField(max_length=30, choices=NETWORK)
     
    wallet_address = models.TextField()

    qr_code = models.ImageField(
        upload_to="wallet_qr/",
        blank=True,
        null=True
    )

    active = models.BooleanField(default=True)

    def __str__(self):
        return self.coin
    
class Deposit(models.Model):

    STATUS = (
        ("pending","Pending"),
        ("approved","Approved"),
        ("rejected","Rejected"),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE)

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE
    )

    amount = models.DecimalField(max_digits=20, decimal_places=2)

    txid = models.CharField(max_length=200)

    proof = models.ImageField(
        upload_to="deposit_proofs/",
        blank=True,
        null=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

class Withdrawal(models.Model):

    STATUS = (
        ("pending","Pending"),
        ("approved","Approved"),
        ("rejected","Rejected"),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE)

    coin = models.CharField(max_length=50)

    wallet_address = models.TextField()

    amount = models.DecimalField(max_digits=20, decimal_places=2)

    fee = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)

class ReferralCommission(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="earned_referrals"
    )

    referred_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="generated_referrals"
    )

    amount = models.DecimalField(max_digits=20, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):

    user = models.ForeignKey(User,on_delete=models.CASCADE)

    title = models.CharField(max_length=200)

    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

class News(models.Model):

    title = models.CharField(max_length=200)

    image = models.ImageField(upload_to="news/")

    content = models.TextField()

    published = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    

class Transaction(models.Model):

    TYPES = (
        ("deposit","Deposit"),
        ("withdrawal","Withdrawal"),
        ("investment","Investment"),
        ("profit","Profit"),
        ("referral","Referral"),
    )

    user = models.ForeignKey(User,on_delete=models.CASCADE)

    transaction_type = models.CharField(
        max_length=30,
        choices=TYPES
    )

    amount = models.DecimalField(max_digits=20, decimal_places=2)

    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

class KYC(models.Model):

    STATUS = (
        ("pending","Pending"),
        ("approved","Approved"),
        ("rejected","Rejected"),
    )

    user = models.OneToOneField(User,on_delete=models.CASCADE)

    document_type = models.CharField(max_length=100)

    document = models.ImageField(upload_to="kyc/")

    selfie = models.ImageField(upload_to="kyc/selfie/")

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )

    submitted_at = models.DateTimeField(auto_now_add=True)

class SiteSetting(models.Model):
    site_name = models.CharField(max_length=100)
    logo = models.ImageField(upload_to="logo/", blank=True, null=True)   # <-- add blank=True, null=True

    # Link preview (Open Graph / WhatsApp / Facebook / Twitter) fields
    site_description = models.CharField(
        max_length=300,
        blank=True,
        help_text="Shown as the description in link previews (WhatsApp, Facebook, Telegram, etc.)"
    )
    og_image = models.ImageField(
        upload_to="og_images/",
        blank=True,
        null=True,
        help_text="Recommended size: 1200x630px. Used as the thumbnail when your site link is shared."
    )

    minimum_deposit = models.DecimalField(max_digits=20, decimal_places=2)
    minimum_withdrawal = models.DecimalField(max_digits=20, decimal_places=2)
    referral_bonus = models.DecimalField(max_digits=5, decimal_places=2)
    maintenance_mode = models.BooleanField(default=False)
    support_email = models.EmailField()
    support_phone = models.CharField(max_length=30)



class Testimonial(models.Model):

    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    client_name = models.CharField(max_length=100)

    client_role = models.CharField(
        max_length=100, blank=True,
        help_text="e.g. Verified Trader, Elite Investor"
    )

    client_photo = models.ImageField(
        upload_to="testimonials/", blank=True, null=True
    )

    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, default=5)

    comment = models.TextField()

    is_active = models.BooleanField(default=True)

    order = models.PositiveIntegerField(
        default=0, help_text="Lower numbers appear first"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "-created_at"]

    def __str__(self):
        return f"{self.client_name} ({self.rating}★)"