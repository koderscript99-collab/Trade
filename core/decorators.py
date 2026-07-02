from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin


def admin_required(view_func):
    """Function-based view decorator restricting access to admin users."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("core:admin_login")
        if not (request.user.is_admin_user or request.user.is_staff):
            messages.error(request, "You do not have permission to access the admin panel.")
            return redirect("core:dashboard")
        return view_func(request, *args, **kwargs)
    return _wrapped


class AdminRequiredMixin(UserPassesTestMixin):
    """Class-based view mixin restricting access to admin users."""
    login_url = "core:admin_login"

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.is_admin_user or self.request.user.is_staff
        )

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access the admin panel.")
        return redirect("core:admin_login")


def verified_email_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.email_verified:
            messages.warning(request, "Please verify your email address to continue.")
            return redirect("core:email_verify_pending")
        return view_func(request, *args, **kwargs)
    return _wrapped