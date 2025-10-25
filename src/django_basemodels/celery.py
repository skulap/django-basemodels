"""
Celery-specific code for django-basemodels.
This module is only used when Celery extras are installed.
"""

import logging

from celery import group, shared_task
from django.apps import apps

logger = logging.getLogger(__name__)


def get_models_with_activity():
    """Генератор моделей, которые наследуются от BaseModel и имеют активность"""
    from .models import BaseModel

    for model in apps.get_models():
        if issubclass(model, BaseModel) and not model._meta.abstract and not model._meta.proxy:
            yield model


@shared_task(name="django_basemodels.update_model_activity")
def update_model_activity_task(model_label: str):
    """Задача для обновления активности конкретной модели"""
    try:
        model = apps.get_model(model_label)
        updated = model.objects.update_activity_status()
        logger.debug(f"[{model_label}] Updated {updated} objects")
        return updated
    except Exception as e:
        logger.error(f"Error updating activity for {model_label}: {e}")
        raise


@shared_task(name="django_basemodels.update_activity_status")
def update_activity_status_task():
    """Основная задача для обновления активности всех моделей"""
    tasks = []
    for model in get_models_with_activity():
        tasks.append(update_model_activity_task.s(model._meta.label_lower))

    if tasks:
        group(tasks).apply_async()
        logger.info(f"Started activity update for {len(tasks)} models")
        return f"Started update for {len(tasks)} models"
    else:
        logger.debug("No models found for activity update")
        return "No models to update"
