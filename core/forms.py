from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.validators import FileExtensionValidator

from .models import (
    Testimonial, User, Deposit, Withdrawal, Investment, InvestmentPlan,
    Wallet, KYC, News, SiteSetting, Notification
)


# ---------------------------------------------------------------------------
# AUTH / ACCOUNT FORMS
# ---------------------------------------------------------------------------

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False, max_length=20)
    country = forms.CharField(required=False, max_length=100)
    referral_code = forms.CharField(required=False, max_length=20)

    class Meta:
        model = User
        fields = ["username", "email", "phone", "country", "password1", "password2"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_referral_code(self):
        code = self.cleaned_data.get("referral_code")
        if code:
            if not User.objects.filter(referral_code=code).exists():
                raise forms.ValidationError("Invalid referral code.")
        return code


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username or Email")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone", "country"]


class ChangePasswordConfirmForm(forms.Form):
    """Used only if you want a custom wrapper around Django's PasswordChangeForm."""
    pass


class TwoFactorSetupForm(forms.Form):
    code = forms.CharField(max_length=6, min_length=6)


# ---------------------------------------------------------------------------
# FINANCE FORMS (USER SIDE)
# ---------------------------------------------------------------------------

class DepositForm(forms.ModelForm):
    class Meta:
        model = Deposit
        fields = ["wallet", "amount", "txid", "proof"]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["wallet"].queryset = Wallet.objects.filter(active=True)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


class WithdrawalForm(forms.ModelForm):
    class Meta:
        model = Withdrawal
        fields = ["coin", "wallet_address", "amount"]
        widgets = {
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean_amount(self):
        amount = self.cleaned_data["amount"]
        if amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        if self.user and amount > self.user.balance:
            raise forms.ValidationError("Insufficient balance.")
        return amount


class InvestmentForm(forms.Form):
    plan = forms.ModelChoiceField(queryset=InvestmentPlan.objects.filter(active=True))
    amount = forms.DecimalField(max_digits=20, decimal_places=2)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        plan = cleaned.get("plan")
        amount = cleaned.get("amount")
        if plan and amount is not None:
            if amount < plan.minimum or amount > plan.maximum:
                raise forms.ValidationError(
                    f"Amount must be between {plan.minimum} and {plan.maximum} for this plan."
                )
            if self.user and amount > self.user.balance:
                raise forms.ValidationError("Insufficient balance to invest this amount.")
        return cleaned


class KYCForm(forms.ModelForm):
    class Meta:
        model = KYC
        fields = ["document_type", "document", "selfie"]


# ---------------------------------------------------------------------------
# ADMIN PANEL FORMS
# ---------------------------------------------------------------------------

class InvestmentPlanForm(forms.ModelForm):
    class Meta:
        model = InvestmentPlan
        fields = ["name", "minimum", "maximum", "roi", "duration_days", "active"]


class WalletForm(forms.ModelForm):
    class Meta:
        model = Wallet
        fields = ["coin", "wallet_address", "qr_code", "active"]


class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ["title", "image", "content", "published"]


class SiteSettingForm(forms.ModelForm):
    class Meta:
        model = SiteSetting
        fields = [
            "site_name", "logo", "site_description", "og_image",
            "minimum_deposit", "minimum_withdrawal",
            "referral_bonus", "maintenance_mode", "support_email", "support_phone",
        ]
        widgets = {
            "site_description": forms.Textarea(attrs={"rows": 3, "maxlength": 300}),
        }


class AdminUserEditForm(forms.ModelForm):
    """Lets an admin adjust balances / flags on a user account."""

    class Meta:
        model = User
        fields = [
            "balance", "investment_balance", "profit_balance", "referral_balance",
            "is_active", "is_admin_user", "kyc_verified", "email_verified", "phone_verified",
        ]


class AdminBalanceAdjustForm(forms.Form):
    ACTION_CHOICES = (("credit", "Credit"), ("debit", "Debit"))
    BALANCE_CHOICES = (
        ("balance", "Main Balance"),
        ("investment_balance", "Investment Balance"),
        ("profit_balance", "Profit Balance"),
        ("referral_balance", "Referral Balance"),
    )
    balance_field = forms.ChoiceField(choices=BALANCE_CHOICES)
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    amount = forms.DecimalField(max_digits=20, decimal_places=2, min_value=0.01)
    reason = forms.CharField(widget=forms.Textarea, required=False)


class DepositReviewForm(forms.Form):
    ACTION_CHOICES = (("approve", "Approve"), ("reject", "Reject"))
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    admin_note = forms.CharField(widget=forms.Textarea, required=False)


class WithdrawalReviewForm(forms.Form):
    ACTION_CHOICES = (("approve", "Approve"), ("reject", "Reject"))
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    admin_note = forms.CharField(widget=forms.Textarea, required=False)


class KYCReviewForm(forms.Form):
    ACTION_CHOICES = (("approve", "Approve"), ("reject", "Reject"))
    action = forms.ChoiceField(choices=ACTION_CHOICES)
    admin_note = forms.CharField(widget=forms.Textarea, required=False)


class AdminNotificationForm(forms.Form):
    TARGET_CHOICES = (("single", "Single User"), ("all", "All Users"))
    target = forms.ChoiceField(choices=TARGET_CHOICES)
    user = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    title = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)


class AdminLoginForm(AuthenticationForm):
    username = forms.CharField(label="Admin Username")



class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ["client_name", "client_role", "client_photo", "rating", "comment", "is_active", "order"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 3}),
        }