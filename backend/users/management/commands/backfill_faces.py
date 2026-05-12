from django.core.management.base import BaseCommand
from users.models import Media
from users.tasks import detect_faces_task


class Command(BaseCommand):
    help = 'Queue face detection for all approved images that have not been attempted yet'

    def handle(self, *args, **options):
        qs = Media.objects.filter(
            status='approved',
            media_type='image',
            face_detection_attempted=False
        )
        count = qs.count()
        for media in qs:
            detect_faces_task.delay(media.id)
        self.stdout.write(f'Queued {count} media items for face detection.')
