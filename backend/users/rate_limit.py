from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import PermissionDenied
from .models import FailedAttempt

MAX_ATTEMPTS = 5          # allowed failures
TIME_WINDOW = timedelta(minutes=10)


def get_client_ip(request):
    """Extract real IP even behind a reverse proxy."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(request, endpoint):
    """
    Raise PermissionDenied if the IP has exceeded the allowed failures
    for the given endpoint within the time window.
    """
    ip = get_client_ip(request)
    cutoff = timezone.now() - TIME_WINDOW
    count = FailedAttempt.objects.filter(
        ip_address=ip,
        endpoint=endpoint,
        timestamp__gte=cutoff
    ).count()
    if count >= MAX_ATTEMPTS:
        raise PermissionDenied("Too many failed attempts. Please try again later.")


def record_failed_attempt(request, endpoint):
    """Log a failed attempt for the current IP and endpoint."""
    ip = get_client_ip(request)
    FailedAttempt.objects.create(ip_address=ip, endpoint=endpoint)
