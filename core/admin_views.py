from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, logout
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

from .models import (
    User, Deposit, Withdrawal, Investment, InvestmentPlan, Wallet,
    KYC, News, SiteSetting, Transaction, ReferralCommission,Testimonial
)
from .forms import (
    InvestmentPlanForm, WalletForm, NewsForm, SiteSettingForm,
    AdminUserEditForm, AdminBalanceAdjustForm, DepositReviewForm,
    WithdrawalReviewForm, KYCReviewForm, AdminNotificationForm, AdminLoginForm,TestimonialForm
)
from .decorators import admin_required, AdminRequiredMixin
from .utils import log_transaction, notify_user, broadcast_notification, credit_referral_commission


# ---------------------------------------------------------------------------
# ADMIN AUTH
# ---------------------------------------------------------------------------

def admin_login_view(request):
    if request.user.is_authenticated and (request.user.is_admin_user or request.user.is_staff):
        return redirect("core:admin_dashboard")

    if request.method == "POST":
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user.is_admin_user or user.is_staff:
                login(request, user)
                return redirect("core:admin_dashboard")
            messages.error(request, "This account does not have admin access.")
    else:
        form = AdminLoginForm()

    return render(request, "core/admin/admin_login.html", {"form": form})


@admin_required
def admin_logout_view(request):
    logout(request)
    return redirect("core:admin_login")


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

@admin_required
def admin_dashboard_view(request):
    stats = {
        "total_users": User.objects.count(),
        "total_deposits": Deposit.objects.filter(status="approved").aggregate(
            s=Sum("amount"))["s"] or 0,
        "pending_deposits": Deposit.objects.filter(status="pending").count(),
        "pending_withdrawals": Withdrawal.objects.filter(status="pending").count(),
        "pending_kyc": KYC.objects.filter(status="pending").count(),
        "active_investments": Investment.objects.filter(status="running").count(),
        "total_invested": Investment.objects.filter(status="running").aggregate(
            s=Sum("amount"))["s"] or 0,
    }
    recent_deposits = Deposit.objects.order_by("-created_at")[:8]
    recent_withdrawals = Withdrawal.objects.order_by("-created_at")[:8]
    recent_users = User.objects.order_by("-created_at")[:8]

    return render(request, "core/admin/admin_dashboard.html", {
        "stats": stats,
        "recent_deposits": recent_deposits,
        "recent_withdrawals": recent_withdrawals,
        "recent_users": recent_users,
    })


# ---------------------------------------------------------------------------
# USER MANAGEMENT
# ---------------------------------------------------------------------------

@admin_required
def admin_users_list_view(request):
    query = request.GET.get("q", "")
    users = User.objects.all().order_by("-created_at")
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query) | Q(phone__icontains=query)
        )
    paginator = Paginator(users, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/admin/admin_users_list.html", {"page_obj": page, "query": query})


@admin_required
def admin_user_detail_view(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        if "save_profile" in request.POST:
            form = AdminUserEditForm(request.POST, instance=target_user)
            if form.is_valid():
                form.save()
                messages.success(request, "User updated.")
                return redirect("core:admin_user_detail", pk=pk)
        elif "adjust_balance" in request.POST:
            adjust_form = AdminBalanceAdjustForm(request.POST)
            if adjust_form.is_valid():
                field = adjust_form.cleaned_data["balance_field"]
                action = adjust_form.cleaned_data["action"]
                amount = adjust_form.cleaned_data["amount"]
                current = getattr(target_user, field)
                new_value = current + amount if action == "credit" else current - amount
                setattr(target_user, field, new_value)
                target_user.save(update_fields=[field])

                log_transaction(
                    target_user,
                    "deposit" if action == "credit" else "withdrawal",
                    amount,
                    f"Admin {action} on {field}: {adjust_form.cleaned_data.get('reason', '')}"
                )
                notify_user(target_user, "Balance Updated",
                            f"Your {field.replace('_', ' ')} was {action}ed by {amount}.")
                messages.success(request, "Balance adjusted.")
                return redirect("core:admin_user_detail", pk=pk)

    form = AdminUserEditForm(instance=target_user)
    adjust_form = AdminBalanceAdjustForm()
    investments = Investment.objects.filter(user=target_user).order_by("-started_at")
    deposits = Deposit.objects.filter(user=target_user).order_by("-created_at")
    withdrawals = Withdrawal.objects.filter(user=target_user).order_by("-created_at")

    return render(request, "core/admin/admin_user_detail.html", {
        "target_user": target_user,
        "form": form,
        "adjust_form": adjust_form,
        "investments": investments,
        "deposits": deposits,
        "withdrawals": withdrawals,
    })


# ---------------------------------------------------------------------------
# DEPOSITS
# ---------------------------------------------------------------------------

@admin_required
def admin_deposits_list_view(request):
    status = request.GET.get("status", "pending")
    deposits = Deposit.objects.all().order_by("-created_at")
    if status != "all":
        deposits = deposits.filter(status=status)
    paginator = Paginator(deposits, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/admin/admin_deposits_list.html", {
        "page_obj": page, "status": status,
    })


@admin_required
def admin_deposit_detail_view(request, pk):
    deposit = get_object_or_404(Deposit, pk=pk)
    settings_obj = SiteSetting.objects.first()

    if request.method == "POST":
        form = DepositReviewForm(request.POST)
        if form.is_valid() and deposit.status == "pending":
            action = form.cleaned_data["action"]
            if action == "approve":
                deposit.status = "approved"
                deposit.save(update_fields=["status"])

                deposit.user.balance += deposit.amount
                deposit.user.save(update_fields=["balance"])
                log_transaction(deposit.user, "deposit", deposit.amount,
                                 f"Deposit #{deposit.id} approved")
                notify_user(deposit.user, "Deposit Approved",
                            f"Your deposit of {deposit.amount} has been approved.")

                if settings_obj and deposit.user.referred_by:
                    credit_referral_commission(
                        deposit.user, deposit.amount, settings_obj.referral_bonus
                    )
            else:
                deposit.status = "rejected"
                deposit.save(update_fields=["status"])
                notify_user(deposit.user, "Deposit Rejected",
                            f"Your deposit of {deposit.amount} was rejected.")

            messages.success(request, f"Deposit {action}d.")
            return redirect("core:admin_deposits_list")
    else:
        form = DepositReviewForm()

    return render(request, "core/admin/admin_deposit_detail.html", {
        "deposit": deposit, "form": form,
    })


# ---------------------------------------------------------------------------
# WITHDRAWALS
# ---------------------------------------------------------------------------

@admin_required
def admin_withdrawals_list_view(request):
    status = request.GET.get("status", "pending")
    withdrawals = Withdrawal.objects.all().order_by("-created_at")
    if status != "all":
        withdrawals = withdrawals.filter(status=status)
    paginator = Paginator(withdrawals, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/admin/admin_withdrawals_list.html", {
        "page_obj": page, "status": status,
    })


@admin_required
def admin_withdrawal_detail_view(request, pk):
    withdrawal = get_object_or_404(Withdrawal, pk=pk)

    if request.method == "POST":
        form = WithdrawalReviewForm(request.POST)
        if form.is_valid() and withdrawal.status == "pending":
            action = form.cleaned_data["action"]
            if action == "approve":
                withdrawal.status = "approved"
                withdrawal.save(update_fields=["status"])
                notify_user(withdrawal.user, "Withdrawal Approved",
                            f"Your withdrawal of {withdrawal.amount} has been processed.")
            else:
                # funds were held at request time; refund them
                withdrawal.status = "rejected"
                withdrawal.save(update_fields=["status"])
                withdrawal.user.balance += withdrawal.amount
                withdrawal.user.save(update_fields=["balance"])
                notify_user(withdrawal.user, "Withdrawal Rejected",
                            f"Your withdrawal of {withdrawal.amount} was rejected and refunded.")

            messages.success(request, f"Withdrawal {action}d.")
            return redirect("core:admin_withdrawals_list")
    else:
        form = WithdrawalReviewForm()

    return render(request, "core/admin/admin_withdrawal_detail.html", {
        "withdrawal": withdrawal, "form": form,
    })


# ---------------------------------------------------------------------------
# KYC
# ---------------------------------------------------------------------------

@admin_required
def admin_kyc_list_view(request):
    status = request.GET.get("status", "pending")
    submissions = KYC.objects.all().order_by("-submitted_at")
    if status != "all":
        submissions = submissions.filter(status=status)
    paginator = Paginator(submissions, 25)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/admin/admin_kyc_list.html", {
        "page_obj": page, "status": status,
    })


@admin_required
def admin_kyc_detail_view(request, pk):
    kyc = get_object_or_404(KYC, pk=pk)

    if request.method == "POST":
        form = KYCReviewForm(request.POST)
        if form.is_valid() and kyc.status == "pending":
            action = form.cleaned_data["action"]
            kyc.status = "approved" if action == "approve" else "rejected"
            kyc.save(update_fields=["status"])

            kyc.user.kyc_verified = (action == "approve")
            kyc.user.save(update_fields=["kyc_verified"])

            notify_user(kyc.user, "KYC Update", f"Your KYC submission was {kyc.status}.")
            messages.success(request, f"KYC {kyc.status}.")
            return redirect("core:admin_kyc_list")
    else:
        form = KYCReviewForm()

    return render(request, "core/admin/admin_kyc_detail.html", {"kyc": kyc, "form": form})


# ---------------------------------------------------------------------------
# INVESTMENT PLANS (CRUD via CBVs)
# ---------------------------------------------------------------------------

class AdminPlanListView(AdminRequiredMixin, ListView):
    model = InvestmentPlan
    template_name = "core/admin/admin_plans_list.html"
    context_object_name = "plans"
    ordering = ["-created_at"]


class AdminPlanCreateView(AdminRequiredMixin, CreateView):
    model = InvestmentPlan
    form_class = InvestmentPlanForm
    template_name = "core/admin/admin_plan_form.html"
    success_url = reverse_lazy("core:admin_plans_list")


class AdminPlanUpdateView(AdminRequiredMixin, UpdateView):
    model = InvestmentPlan
    form_class = InvestmentPlanForm
    template_name = "core/admin/admin_plan_form.html"
    success_url = reverse_lazy("core:admin_plans_list")


class AdminPlanDeleteView(AdminRequiredMixin, DeleteView):
    model = InvestmentPlan
    template_name = "core/admin/admin_plan_confirm_delete.html"
    success_url = reverse_lazy("core:admin_plans_list")


# ---------------------------------------------------------------------------
# WALLETS (CRUD via CBVs)
# ---------------------------------------------------------------------------

class AdminWalletListView(AdminRequiredMixin, ListView):
    model = Wallet
    template_name = "core/admin/admin_wallets_list.html"
    context_object_name = "wallets"


class AdminWalletCreateView(AdminRequiredMixin, CreateView):
    model = Wallet
    form_class = WalletForm
    template_name = "core/admin/admin_wallet_form.html"
    success_url = reverse_lazy("core:admin_wallets_list")


class AdminWalletUpdateView(AdminRequiredMixin, UpdateView):
    model = Wallet
    form_class = WalletForm
    template_name = "core/admin/admin_wallet_form.html"
    success_url = reverse_lazy("core:admin_wallets_list")


class AdminWalletDeleteView(AdminRequiredMixin, DeleteView):
    model = Wallet
    template_name = "core/admin/admin_wallet_confirm_delete.html"
    success_url = reverse_lazy("core:admin_wallets_list")


# ---------------------------------------------------------------------------
# NEWS (CRUD via CBVs)
# ---------------------------------------------------------------------------

class AdminNewsListView(AdminRequiredMixin, ListView):
    model = News
    template_name = "core/admin/admin_news_list.html"
    context_object_name = "news_items"
    ordering = ["-created_at"]


class AdminNewsCreateView(AdminRequiredMixin, CreateView):
    model = News
    form_class = NewsForm
    template_name = "core/admin/admin_news_form.html"
    success_url = reverse_lazy("core:admin_news_list")


class AdminNewsUpdateView(AdminRequiredMixin, UpdateView):
    model = News
    form_class = NewsForm
    template_name = "core/admin/admin_news_form.html"
    success_url = reverse_lazy("core:admin_news_list")


class AdminNewsDeleteView(AdminRequiredMixin, DeleteView):
    model = News
    template_name = "core/admin/admin_news_confirm_delete.html"
    success_url = reverse_lazy("core:admin_news_list")


# ---------------------------------------------------------------------------
# SITE SETTINGS (singleton)
# ---------------------------------------------------------------------------

@admin_required
def admin_site_settings_view(request):
    settings_obj, _ = SiteSetting.objects.get_or_create(
        pk=1, defaults={
            "site_name": "My Crypto Platform",
            "minimum_deposit": 10,
            "minimum_withdrawal": 10,
            "referral_bonus": 5,
            "support_email": "support@example.com",
            "support_phone": "",
        }
    )

    if request.method == "POST":
        form = SiteSettingForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Site settings updated.")
            return redirect("core:admin_site_settings")
    else:
        form = SiteSettingForm(instance=settings_obj)

    return render(request, "core/admin/admin_site_settings.html", {"form": form})


# ---------------------------------------------------------------------------
# TRANSACTIONS (read-only oversight)
# ---------------------------------------------------------------------------

@admin_required
def admin_transactions_list_view(request):
    transactions = Transaction.objects.select_related("user").order_by("-created_at")
    tx_type = request.GET.get("type")
    if tx_type:
        transactions = transactions.filter(transaction_type=tx_type)
    paginator = Paginator(transactions, 40)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "core/admin/admin_transactions_list.html", {
        "page_obj": page, "tx_type": tx_type,
    })


# ---------------------------------------------------------------------------
# NOTIFICATIONS (broadcast / targeted)
# ---------------------------------------------------------------------------

@admin_required
def admin_send_notification_view(request):
    if request.method == "POST":
        form = AdminNotificationForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data["title"]
            message = form.cleaned_data["message"]
            if form.cleaned_data["target"] == "all":
                broadcast_notification(title, message)
                messages.success(request, "Notification broadcast to all users.")
            else:
                target_user = form.cleaned_data["user"]
                if target_user:
                    notify_user(target_user, title, message)
                    messages.success(request, f"Notification sent to {target_user.username}.")
                else:
                    messages.error(request, "Please select a user.")
            return redirect("core:admin_send_notification")
    else:
        form = AdminNotificationForm()

    return render(request, "core/admin/admin_notifications_send.html", {"form": form})


class AdminTestimonialListView(AdminRequiredMixin, ListView):
    model = Testimonial
    template_name = "core/admin/admin_testimonials_list.html"
    context_object_name = "testimonials"


class AdminTestimonialCreateView(AdminRequiredMixin, CreateView):
    model = Testimonial
    form_class = TestimonialForm
    template_name = "core/admin/admin_testimonial_form.html"
    success_url = reverse_lazy("core:admin_testimonials_list")


class AdminTestimonialUpdateView(AdminRequiredMixin, UpdateView):
    model = Testimonial
    form_class = TestimonialForm
    template_name = "core/admin/admin_testimonial_form.html"
    success_url = reverse_lazy("core:admin_testimonials_list")


class AdminTestimonialDeleteView(AdminRequiredMixin, DeleteView):
    model = Testimonial
    template_name = "core/admin/admin_testimonial_confirm_delete.html"
    success_url = reverse_lazy("core:admin_testimonials_list")