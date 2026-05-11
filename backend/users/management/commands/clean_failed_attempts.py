from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import FailedAttempt


class Command(BaseCommand):
    help = 'Delete failed attempt records older than 10 minutes'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(minutes=10)
        deleted, _ = FailedAttempt.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(f'Deleted {deleted} old failed attempts.')
