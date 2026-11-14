import os
import time

from django.core.management.base import BaseCommand

from users.models import Media
from users.thumbnails import (
    THUMBNAIL_SIZES,
    get_thumbnail_path,
    import_legacy_thumbnail,
    thumbnail_path,
)


class Command(BaseCommand):
    help = (
        'Pre-generate disk-backed thumbnails for approved media. '
        'Use --from-redis to reuse the old 1200px Redis cache (grid only).'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--size',
            choices=sorted(THUMBNAIL_SIZES.keys()),
            default='grid',
            help='Rendition to generate (default: grid).',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Only process the first N media items (0 = all).',
        )
        parser.add_argument(
            '--status',
            default='approved',
            help='Media status to process (default: approved).',
        )
        parser.add_argument(
            '--from-redis',
            action='store_true',
            dest='from_redis',
            help='Import the old media_thumbnail:v4 Redis keys for grid renditions.',
        )

    def handle(self, *args, **options):
        size = options['size']
        limit = options['limit']
        status = options['status']
        from_redis = options['from_redis']

        queryset = Media.objects.filter(status=status).order_by('id')
        total = queryset.count()
        if limit:
            queryset = queryset[:limit]

        self.stdout.write(
            f'Generating {size} thumbnails for {min(total, limit) if limit else total} media items...'
        )

        started = time.time()
        created = 0
        skipped = 0
        failed = 0
        processed = 0

        for media in queryset.iterator():
            processed += 1
            destination = thumbnail_path(media.id, size)
            if os.path.exists(destination):
                skipped += 1
                continue

            path = None
            if from_redis and size == 'grid':
                path = import_legacy_thumbnail(media.id)
            if path is None:
                path = get_thumbnail_path(media.id, size)

            if path:
                created += 1
            else:
                failed += 1

            if processed % 25 == 0:
                elapsed = time.time() - started
                self.stdout.write(
                    f'  {processed} processed: {created} created, '
                    f'{skipped} skipped, {failed} failed ({elapsed:.0f}s)'
                )

        elapsed = time.time() - started
        self.stdout.write(
            self.style.SUCCESS(
                f'Done in {elapsed:.0f}s: {created} created, {skipped} skipped, '
                f'{failed} failed.'
            )
        )
