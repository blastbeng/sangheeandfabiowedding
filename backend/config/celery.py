import os
from celery import Celery
from celery.signals import worker_ready
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'cleanup-empty-face-groups-every-hour': {
        'task': 'users.tasks.cleanup_empty_face_groups',
        'schedule': 3600.0,  # every hour
    },
    'backfill-content-hashes-daily': {
        'task': 'users.tasks.backfill_content_hashes',
        'schedule': 86400.0,  # every 24 hours
    },
    'clean-orphaned-facetag-files-daily': {
        'task': 'users.tasks.clean_orphaned_facetag_files',
        'schedule': crontab(hour=3, minute=0),  # daily at 3 AM
    },
    'compute-similarity-ordering-daily': {
        'task': 'users.tasks.compute_similarity_ordering',
        'schedule': 86400.0,  # every 24 hours
    },
    # 'cleanup-missing-cloud-files-every-hour': {
    #     'task': 'users.tasks.cleanup_missing_cloud_files',
    #     'schedule': crontab(minute=0, hour='*'),  # every hour
    # },
    # 'deduplicate-faces-every-hour': {
    #     'task': 'users.tasks.deduplicate_faces',
    #     'schedule': crontab(minute=0, hour='*'),  # every hour
    # },
}

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

@worker_ready.connect
def schedule_initial_backfill(sender, **kwargs):
    """Queue the backfill task 30 seconds after the worker starts."""
    from users.tasks import backfill_faces_periodic
    backfill_faces_periodic.apply_async(countdown=30)
