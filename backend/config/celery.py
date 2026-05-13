import os
from celery import Celery
from celery.signals import worker_ready

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('config')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

@worker_ready.connect
def schedule_initial_backfill(sender, **kwargs):
    """Queue the backfill task 30 seconds after the worker starts."""
    from users.tasks import backfill_faces_periodic
    backfill_faces_periodic.apply_async(countdown=30)
