from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    User, InvestmentPlan, Investment, Wallet, Deposit, Withdrawal,
    ReferralCommission, Notification, News, Transaction, KYC, SiteSetting,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = (
        "username", "email", "balance", "investment_balance",
        "kyc_verified", "is_admin_user", "is_active", "created_at",
    )
    list_filter = ("is_admin_user", "kyc_verified", "is_active")
    search_fields = ("username", "email", "phone", "referral_code")
    readonly_fields = ("id", "created_at", "referral_code")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Crypto Platform Info", {
            "fields": (
                "phone", "country", "referral_code", "referred_by",
                "balance", "investment_balance", "profit_balance", "referral_balance",
                "email_verified", "phone_verified", "kyc_verified",
                "two_factor_enabled", "is_admin_user",
            )
        }),
    )


@admin.register(InvestmentPlan)
class InvestmentPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "minimum", "maximum", "roi", "duration_days", "active")
    list_filter = ("active",)
    search_fields = ("name",)


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "amount", "expected_profit", "status", "started_at", "ends_at")
    list_filter = ("status", "plan")
    search_fields = ("user__username",)


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("coin", "wallet_address", "active")
    list_filter = ("active", "coin")


@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet", "amount", "status", "created_at")
    list_filter = ("status", "wallet")
    search_fields = ("user__username", "txid")


@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ("user", "coin", "amount", "fee", "status", "created_at")
    list_filter = ("status", "coin")
    search_fields = ("user__username", "wallet_address")


@admin.register(ReferralCommission)
class ReferralCommissionAdmin(admin.ModelAdmin):
    list_display = ("user", "referred_user", "amount", "created_at")
    search_fields = ("user__username", "referred_user__username")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "published", "created_at")
    list_filter = ("published",)
    search_fields = ("title",)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("user", "transaction_type", "amount", "created_at")
    list_filter = ("transaction_type",)
    search_fields = ("user__username",)


@admin.register(KYC)
class KYCAdmin(admin.ModelAdmin):
    list_display = ("user", "document_type", "status", "submitted_at")
    list_filter = ("status",)
    search_fields = ("user__username",)


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("site_name", "minimum_deposit", "minimum_withdrawal", "maintenance_mode")