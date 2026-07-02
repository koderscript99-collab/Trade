import random
import string
from decimal import Decimal

from django.utils import timezone
from datetime import timedelta

from .models import Transaction, Notification, ReferralCommission, User


def generate_referral_code(length=8):
    """Generate a unique, uppercase alphanumeric referral code."""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = "".join(random.choices(chars, k=length))
        if not User.objects.filter(referral_code=code).exists():
            return code


def log_transaction(user, transaction_type, amount, description=""):
    return Transaction.objects.create(
        user=user,
        transaction_type=transaction_type,
        amount=amount,
        description=description,
    )


def notify_user(user, title, message):
    return Notification.objects.create(user=user, title=title, message=message)


def broadcast_notification(title, message):
    users = User.objects.filter(is_active=True)
    Notification.objects.bulk_create([
        Notification(user=u, title=title, message=message) for u in users
    ])


def calculate_investment_returns(plan, amount: Decimal):
    """Given a plan and principal amount, return (expected_profit, total_return, ends_at)."""
    expected_profit = (amount * plan.roi) / Decimal("100")
    total_return = amount + expected_profit
    ends_at = timezone.now() + timedelta(days=plan.duration_days)
    return expected_profit, total_return, ends_at


def credit_referral_commission(referred_user, deposit_amount, percentage: Decimal):
    """Credit the referrer when their referred user's deposit is approved."""
    referrer = referred_user.referred_by
    if not referrer:
        return None
    commission_amount = (deposit_amount * percentage) / Decimal("100")
    referrer.referral_balance += commission_amount
    referrer.balance += commission_amount
    referrer.save(update_fields=["referral_balance", "balance"])

    ReferralCommission.objects.create(
        user=referrer,
        referred_user=referred_user,
        amount=commission_amount,
    )
    log_transaction(referrer, "referral", commission_amount,
                     f"Referral commission from {referred_user.username}")
    notify_user(referrer, "Referral Commission",
                f"You earned {commission_amount} from {referred_user.username}'s deposit.")
    return commission_amount


def complete_investment(investment):
    """Mark an investment complete and credit the user's profit + principal."""
    if investment.status != "running":
        return False

    user = investment.user
    user.profit_balance += investment.expected_profit
    user.balance += investment.total_return
    user.investment_balance -= investment.amount
    user.save(update_fields=["profit_balance", "balance", "investment_balance"])

    investment.status = "completed"
    investment.save(update_fields=["status"])

    log_transaction(user, "profit", investment.expected_profit,
                     f"Profit payout for investment #{investment.id}")
    notify_user(user, "Investment Completed",
                f"Your investment of {investment.amount} has matured. "
                f"{investment.total_return} has been credited to your balance.")
    return True