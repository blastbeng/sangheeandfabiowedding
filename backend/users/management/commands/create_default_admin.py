from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Create default admin user'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        username = os.environ.get('ADMIN_USERNAME', 'admin')
        password = os.environ.get('ADMIN_PASSWORD', 'admin$')
        email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                is_active=True
            )
            user = User.objects.get(username=username)
            user.email_verified = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Admin user "{username}" created'))
        else:
            self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists'))
