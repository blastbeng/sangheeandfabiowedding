from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Create default admin user'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', 'admin$')

        # Check if ANY superuser/admin exists
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username=username,
                email=f'{username}@admin.com',
                password=password,
                is_staff=True,
                is_superuser=True
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created admin user: {username}'))
        else:
            self.stdout.write(self.style.SUCCESS('Admin user already exists, skipping creation'))
