from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "lms_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    task_routes={
        "app.workers.tasks.ingestion.*": {"queue": "ingestion"},
    },
    # Ensure memory is released periodically during heavy processing
    worker_max_tasks_per_child=50,
)

# Autodiscover tasks from the workers.tasks module
celery_app.autodiscover_tasks(["app.workers.tasks.ingestion"])
