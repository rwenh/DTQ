import os
from celery import Celery
REDIS_URL = os.environ.get("REDIS_URL", "redis:://localhost:6379/0")
app = Celery(
    'task_queue',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks'],
)
app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=["json"],
    result_serializer='json',

# Timezone
    timezone="UTC",
    enable_utc=True,
    # Execution behaviour
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

# Results
    result_expires=3600,

    # Route each task type to its own queue so workers can be specialized
    task_routes={
        'tasks.send_bulk_email':    {'queue': 'email'},
        'tasks.generate_report':    {'queue': 'reports'},
        'tasks.process_images':     {'queue': 'images'},
        'tasks.notify_completion':  {'queue': 'email'},
    },
    task_dewwfault_queue='default',
)
