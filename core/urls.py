from django.urls import path
from . import views
from . import admin_views

app_name = "core"

urlpatterns = [
    # Public
    path("", views.landing_page, name="landing"),
    path("news/", views.news_list, name="news_list"),
    path("news/<int:pk>/", views.news_detail, name="news_detail"),
    path("plans/", views.investment_plans_view, name="investment_plans"),

    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("account/password/", views.change_password_view, name="change_password"),

    # Dashboard / profile
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("profile/", views.profile_view, name="profile"),
    path("profile/edit/", views.profile_edit_view, name="profile_edit"),

    # Deposits
    path("deposits/", views.deposit_list_view, name="deposit_list"),
    path("deposits/new/", views.deposit_create_view, name="deposit_create"),
    path("deposits/<int:pk>/", views.deposit_detail_view, name="deposit_detail"),

    # Withdrawals
    path("withdrawals/", views.withdrawal_list_view, name="withdrawal_list"),
    path("withdrawals/new/", views.withdrawal_create_view, name="withdrawal_create"),

    # Investments
    path("investments/", views.investment_list_view, name="investment_list"),
    path("investments/new/", views.investment_create_view, name="investment_create"),
    path("investments/<int:pk>/", views.investment_detail_view, name="investment_detail"),

    # Referrals
    path("referrals/", views.referral_view, name="referral"),

    # Notifications
    path("notifications/", views.notifications_view, name="notifications"),

    # KYC
    path("kyc/", views.kyc_submit_view, name="kyc_submit"),
    path("kyc/status/", views.kyc_status_view, name="kyc_status"),

    # Transactions
    path("transactions/", views.transactions_view, name="transactions"),

    # ------------------------------------------------------------------
    # CUSTOM ADMIN PANEL  (kept in the same urls.py under /panel/ prefix;
    # split into admin_urls.py below if you prefer full separation)
    # ------------------------------------------------------------------
    path("panel/login/", admin_views.admin_login_view, name="admin_login"),
    path("panel/logout/", admin_views.admin_logout_view, name="admin_logout"),
    path("panel/", admin_views.admin_dashboard_view, name="admin_dashboard"),

    path("panel/users/", admin_views.admin_users_list_view, name="admin_users_list"),
    path("panel/users/<uuid:pk>/", admin_views.admin_user_detail_view, name="admin_user_detail"),

    path("panel/deposits/", admin_views.admin_deposits_list_view, name="admin_deposits_list"),
    path("panel/deposits/<int:pk>/", admin_views.admin_deposit_detail_view, name="admin_deposit_detail"),

    path("panel/withdrawals/", admin_views.admin_withdrawals_list_view, name="admin_withdrawals_list"),
    path("panel/withdrawals/<int:pk>/", admin_views.admin_withdrawal_detail_view, name="admin_withdrawal_detail"),

    path("panel/kyc/", admin_views.admin_kyc_list_view, name="admin_kyc_list"),
    path("panel/kyc/<int:pk>/", admin_views.admin_kyc_detail_view, name="admin_kyc_detail"),

    path("panel/plans/", admin_views.AdminPlanListView.as_view(), name="admin_plans_list"),
    path("panel/plans/new/", admin_views.AdminPlanCreateView.as_view(), name="admin_plan_create"),
    path("panel/plans/<int:pk>/edit/", admin_views.AdminPlanUpdateView.as_view(), name="admin_plan_update"),
    path("panel/plans/<int:pk>/delete/", admin_views.AdminPlanDeleteView.as_view(), name="admin_plan_delete"),

    path("panel/wallets/", admin_views.AdminWalletListView.as_view(), name="admin_wallets_list"),
    path("panel/wallets/new/", admin_views.AdminWalletCreateView.as_view(), name="admin_wallet_create"),
    path("panel/wallets/<int:pk>/edit/", admin_views.AdminWalletUpdateView.as_view(), name="admin_wallet_update"),
    path("panel/wallets/<int:pk>/delete/", admin_views.AdminWalletDeleteView.as_view(), name="admin_wallet_delete"),

    path("panel/news/", admin_views.AdminNewsListView.as_view(), name="admin_news_list"),
    path("panel/news/new/", admin_views.AdminNewsCreateView.as_view(), name="admin_news_create"),
    path("panel/news/<int:pk>/edit/", admin_views.AdminNewsUpdateView.as_view(), name="admin_news_update"),
    path("panel/news/<int:pk>/delete/", admin_views.AdminNewsDeleteView.as_view(), name="admin_news_delete"),

    path("panel/settings/", admin_views.admin_site_settings_view, name="admin_site_settings"),
    path("panel/transactions/", admin_views.admin_transactions_list_view, name="admin_transactions_list"),
    path("panel/notify/", admin_views.admin_send_notification_view, name="admin_send_notification"),
]