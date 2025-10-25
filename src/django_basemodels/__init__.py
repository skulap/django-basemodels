try:
    import celery
    import celery_hchecker
    import django_celery_beat

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

__version__ = "0.0.5"
__all__ = ["CELERY_AVAILABLE"]

# Импортируем задачи, чтобы они зарегистрировались в Celery
if CELERY_AVAILABLE:
    from .celery import update_activity_status_task, update_model_activity_task
