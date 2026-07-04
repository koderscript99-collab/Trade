import json

from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Sum

from .models import (
    User, InvestmentPlan, Investment, Wallet, Deposit, Withdrawal,
    ReferralCommission, Notification, News, KYC, Transaction, SiteSetting
)
from .forms import (
    RegisterForm, LoginForm, ProfileForm, DepositForm, WithdrawalForm,
    InvestmentForm, KYCForm,
)
from .utils import generate_referral_code, log_transaction, calculate_investment_returns


# ---------------------------------------------------------------------------
# PUBLIC PAGES
# ---------------------------------------------------------------------------

def landing_page(request):
    plans = InvestmentPlan.objects.filter(active=True)
    news = News.objects.filter(published=True).order_by("-created_at")[:6]
    return render(request, "core/landing.html", {"plans": plans, "news": news})


def news_list(request):
    news = News.objects.filter(published=True).order_by("-created_at")
    paginator = Paginator(news, 12)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/news_list.html", {"page_obj": page})


def news_detail(request, pk):
    article = get_object_or_404(News, pk=pk, published=True)
    return render(request, "core/news_detail.html", {"article": article})


# ---------------------------------------------------------------------------
# AUTH
# ---------------------------------------------------------------------------

def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.phone = form.cleaned_data.get("phone", "")
            user.country = form.cleaned_data.get("country", "")
            user.referral_code = generate_referral_code()

            ref_code = form.cleaned_data.get("referral_code")
            if ref_code:
                referrer = User.objects.filter(referral_code=ref_code).first()
                user.referred_by = referrer

            user.save()
            login(request, user)
            messages.success(request, "Account created successfully. Welcome!")
            return redirect("core:dashboard")
    else:
        form = RegisterForm(initial={"referral_code": request.GET.get("ref", "")})

    return render(request, "core/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, "Logged in successfully.")
            next_url = request.GET.get("next", "core:dashboard")
            return redirect(next_url)
    else:
        form = LoginForm()

    return render(request, "core/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("core:login")


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("core:profile")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "core/change_password.html", {"form": form})


# ---------------------------------------------------------------------------
# DASHBOARD / PROFILE
# ---------------------------------------------------------------------------

@login_required
def dashboard_view(request):
    user = request.user
    active_investments = Investment.objects.filter(user=user, status="running")
    recent_transactions = Transaction.objects.filter(user=user).order_by("-created_at")[:10]
    recent_deposits = Deposit.objects.filter(user=user).order_by("-created_at")[:5]
    latest_unread_notification = Notification.objects.filter(
        user=user, is_read=False
    ).order_by("-created_at").first()

    context = {
        "active_investments": active_investments,
        "recent_transactions": recent_transactions,
        "recent_deposits": recent_deposits,
        "total_invested": active_investments.aggregate(s=Sum("amount"))["s"] or 0,
        "referral_count": user.referrals.count(),
        "latest_unread_notification": latest_unread_notification,
    }
    return render(request, "core/dashboard.html", context)


@login_required
def profile_view(request):
    return render(request, "core/profile.html", {"user_obj": request.user})


@login_required
def profile_edit_view(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated.")
            return redirect("core:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "core/profile_edit.html", {"form": form})


# ---------------------------------------------------------------------------
# DEPOSITS
# ---------------------------------------------------------------------------

@login_required
def deposit_list_view(request):
    deposits = Deposit.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(deposits, 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/deposit_list.html", {"page_obj": page})


@login_required
def deposit_create_view(request):
    if request.method == "POST":
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid():
            deposit = form.save(commit=False)
            deposit.user = request.user
            deposit.save()
            messages.success(request, "Deposit submitted. Awaiting admin approval.")
            return redirect("core:deposit_detail", pk=deposit.pk)
    else:
        form = DepositForm()

    # Build a lookup the template's JS can use to show the address/QR
    # for whichever wallet the user picks in the dropdown.
    wallets = Wallet.objects.filter(active=True)
    wallets_data = {
        str(w.id): {
            "coin": w.coin,
            "address": w.wallet_address,
            "qr": w.qr_code.url if w.qr_code else "",
        }
        for w in wallets
    }

    return render(request, "core/deposit_create.html", {
        "form": form,
        "wallets_data_json": json.dumps(wallets_data),
    })


@login_required
def deposit_detail_view(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk, user=request.user)
    return render(request, "core/deposit_detail.html", {"deposit": deposit})


# ---------------------------------------------------------------------------
# WITHDRAWALS
# ---------------------------------------------------------------------------

@login_required
def withdrawal_list_view(request):
    withdrawals = Withdrawal.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(withdrawals, 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/withdrawal_list.html", {"page_obj": page})


@login_required
def withdrawal_create_view(request):
    settings_obj = SiteSetting.objects.first()

    if request.method == "POST":
        form = WithdrawalForm(request.POST, user=request.user)
        if form.is_valid():
            amount = form.cleaned_data["amount"]
            if settings_obj and amount < settings_obj.minimum_withdrawal:
                messages.error(
                    request,
                    f"Minimum withdrawal is {settings_obj.minimum_withdrawal}."
                )
            else:
                withdrawal = form.save(commit=False)
                withdrawal.user = request.user
                withdrawal.save()

                # hold funds immediately; refunded automatically if rejected
                request.user.balance -= amount
                request.user.save(update_fields=["balance"])
                log_transaction(request.user, "withdrawal", amount,
                                 "Withdrawal request submitted")

                messages.success(request, "Withdrawal request submitted.")
                return redirect("core:withdrawal_list")
    else:
        form = WithdrawalForm(user=request.user)

    return render(request, "core/withdrawal_create.html", {"form": form})


# ---------------------------------------------------------------------------
# INVESTMENTS
# ---------------------------------------------------------------------------

def investment_plans_view(request):
    plans = InvestmentPlan.objects.filter(active=True)
    return render(request, "core/investment_plans.html", {"plans": plans})


@login_required
def investment_create_view(request):
    if request.method == "POST":
        form = InvestmentForm(request.POST, user=request.user)
        if form.is_valid():
            plan = form.cleaned_data["plan"]
            amount = form.cleaned_data["amount"]

            expected_profit, total_return, ends_at = calculate_investment_returns(plan, amount)

            investment = Investment.objects.create(
                user=request.user,
                plan=plan,
                amount=amount,
                expected_profit=expected_profit,
                total_return=total_return,
                ends_at=ends_at,
            )

            request.user.balance -= amount
            request.user.investment_balance += amount
            request.user.save(update_fields=["balance", "investment_balance"])

            log_transaction(request.user, "investment", amount,
                             f"Invested in {plan.name}")
            messages.success(request, f"Successfully invested in {plan.name}.")
            return redirect("core:investment_detail", pk=investment.pk)
    else:
        form = InvestmentForm(user=request.user, initial={"plan": request.GET.get("plan")})

    return render(request, "core/investment_create.html", {"form": form})


@login_required
def investment_list_view(request):
    investments = Investment.objects.filter(user=request.user).order_by("-started_at")
    paginator = Paginator(investments, 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/investment_list.html", {"page_obj": page})


@login_required
def investment_detail_view(request, pk):
    investment = get_object_or_404(Investment, pk=pk, user=request.user)
    return render(request, "core/investment_detail.html", {"investment": investment})


# ---------------------------------------------------------------------------
# REFERRALS
# ---------------------------------------------------------------------------

@login_required
def referral_view(request):
    referrals = request.user.referrals.all()
    commissions = ReferralCommission.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "core/referral.html", {
        "referrals": referrals,
        "commissions": commissions,
        "referral_link": request.build_absolute_uri(
            f"/register/?ref={request.user.referral_code}"
        ),
    })


# ---------------------------------------------------------------------------
# NOTIFICATIONS
# ---------------------------------------------------------------------------

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    notifications.filter(is_read=False).update(is_read=True)
    return render(request, "core/notifications.html", {"notifications": notifications})


# ---------------------------------------------------------------------------
# KYC
# ---------------------------------------------------------------------------

@login_required
def kyc_submit_view(request):
    existing = KYC.objects.filter(user=request.user).first()
    if existing and existing.status in ("pending", "approved"):
        return redirect("core:kyc_status")

    if request.method == "POST":
        form = KYCForm(request.POST, request.FILES, instance=existing)
        if form.is_valid():
            kyc = form.save(commit=False)
            kyc.user = request.user
            kyc.status = "pending"
            kyc.save()
            messages.success(request, "KYC documents submitted for review.")
            return redirect("core:kyc_status")
    else:
        form = KYCForm(instance=existing)

    return render(request, "core/kyc_submit.html", {"form": form})


@login_required
def kyc_status_view(request):
    kyc = KYC.objects.filter(user=request.user).first()
    return render(request, "core/kyc_status.html", {"kyc": kyc})


# ---------------------------------------------------------------------------
# TRANSACTIONS
# ---------------------------------------------------------------------------

@login_required
def transactions_view(request):
    transactions = Transaction.objects.filter(user=request.user).order_by("-created_at")
    paginator = Paginator(transactions, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/transactions.html", {"page_obj": page})


@login_required
def notification_mark_read_view(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    next_url = request.META.get("HTTP_REFERER") or "core:dashboard"
    return redirect(next_url if next_url.startswith("/") else "core:dashboard")