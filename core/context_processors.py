from .models import SiteSetting, Notification


def site_settings(request):
    """Expose the singleton SiteSetting row to every template as `site_settings`."""
    return {"site_settings": SiteSetting.objects.first()}


def notifications_badge(request):
    """Expose the authenticated user's unread notification count for the header bell icon."""
    if request.user.is_authenticated:
        count = Notification.objects.filter(user=request.user, is_read=False).count()
    else:
        count = 0
    return {"unread_notifications_count": count}