from django.core.management.base import BaseCommand
from users.models import Media
from users.tasks import detect_faces_task


class Command(BaseCommand):
    help = 'Queue face detection for all approved images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Reset face_detection_attempted and clear existing tags before queuing',
        )

    def handle(self, *args, **options):
        force = options['force']
        qs = Media.objects.filter(status='approved', media_type='image')
        if not force:
            qs = qs.filter(face_detection_attempted=False)
        count = qs.count()
        for media in qs:
            if force:
                media.face_tags.all().delete()
                media.face_detection_attempted = False
                media.save(update_fields=['face_detection_attempted'])
            detect_faces_task.delay(media.id)
        self.stdout.write(f'Queued {count} media items for face detection.')
