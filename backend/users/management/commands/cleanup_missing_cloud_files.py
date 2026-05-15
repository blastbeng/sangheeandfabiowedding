from django.core.management.base import BaseCommand
from users.tasks import cleanup_missing_cloud_files


class Command(BaseCommand):
    help = 'Delete Media records whose files are missing from Nextcloud'

    def handle(self, *args, **options):
        cleanup_missing_cloud_files()
        self.stdout.write(self.style.SUCCESS('Cleanup completed.'))
