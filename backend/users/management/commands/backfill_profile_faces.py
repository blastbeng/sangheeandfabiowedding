from django.core.management.base import BaseCommand
from users.models import CustomUser
from users.tasks import detect_faces_profile_picture


class Command(BaseCommand):
    help = 'Queue face detection for all users with custom profile pictures'

    def handle(self, *args, **options):
        users = CustomUser.objects.exclude(
            profile_picture='profile_pics/default.png'
        ).exclude(profile_picture__isnull=True).exclude(profile_picture='')
        count = 0
        for user in users:
            detect_faces_profile_picture.delay(user.id)
            count += 1
        self.stdout.write(f'Queued {count} users for profile face detection.')
