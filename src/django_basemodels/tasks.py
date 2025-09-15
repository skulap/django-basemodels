import logging

from celery import group, shared_task
from django.apps import apps

from .models import BaseModel

logger = logging.getLogger(__name__)


def _get_models_with_activity():
    for model in apps.get_models():
        if (issubclass(model, BaseModel)
                and not model._meta.abstract
                and not model._meta.proxy):
            yield model


@shared_task(name='django_basemodels.update_model_activity')
def update_model_activity(model_label: str):
    model = apps.get_model(model_label)
    updated = model.objects.update_activity_status()

    logger.info(f"[{model_label}] Updated {updated} objects")


@shared_task(name='django_basemodels.update_activity_status')
def update_activity_status():
    tasks = [update_model_activity.s(model._meta.label_lower) for model in _get_models_with_activity()]
    group(tasks).apply_async()
