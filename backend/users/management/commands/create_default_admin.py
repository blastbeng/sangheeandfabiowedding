from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.conf import settings
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

            # Ensure default profile picture exists
            if not user.profile_picture or not user.profile_picture.storage.exists(user.profile_picture.name):
                try:
                    default_pic_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'default_profile_pic.png')
                    with open(default_pic_path, 'rb') as f:
                        user.profile_picture.save('default.png', ContentFile(f.read()), save=True)
                    self.stdout.write(self.style.SUCCESS('Default profile picture set'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not set default profile picture: {e}'))
        else:
            user = User.objects.get(username=username)
            user.is_active = True
            user.email_verified = True
            user.save()
            self.stdout.write(self.style.WARNING(f'Admin user "{username}" already exists, ensured active'))

            # Ensure default profile picture exists
            if not user.profile_picture or not user.profile_picture.storage.exists(user.profile_picture.name):
                try:
                    default_pic_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'default_profile_pic.png')
                    with open(default_pic_path, 'rb') as f:
                        user.profile_picture.save('default.png', ContentFile(f.read()), save=True)
                    self.stdout.write(self.style.SUCCESS('Default profile picture set'))
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Could not set default profile picture: {e}'))
