import logging

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Error, register
from django.utils.translation import gettext_lazy as _lazy

from . import CELERY_AVAILABLE

logger = logging.getLogger(__name__)


class DjangoBaseModelsAppConfig(AppConfig):
    name = "django_basemodels"
    label = "django_basemodels"
    verbose_name = _lazy("Базовые модели Django")
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        self._register_celery_handlers()

    def _register_celery_handlers(self):
        """Регистрируем обработчики для Celery только если он доступен"""
        try:
            if not CELERY_AVAILABLE:
                return

            if not apps.is_installed("django_celery_beat"):
                logger.debug("django_celery_beat not installed in INSTALLED_APPS")
                return

            self._create_periodic_task()
        except ImportError as e:
            logger.debug("Celery not available for signal registration: %s", e)

    def _create_periodic_task(self):
        """
        Создаем периодическую задачу когда Celery сконфигурирован.
        Вызывается по сигналу on_after_configure.
        """
        try:
            from django_celery_beat.models import IntervalSchedule, PeriodicTask

            # Создаем или получаем интервал
            schedule, _created = IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.MINUTES,
            )
            if _created:
                logger.info("Created interval schedule for models activity update")

            # Создаем или получаем периодическую задачу
            task, _task_created = PeriodicTask.objects.get_or_create(
                interval=schedule,
                name="Models activity update",
                task="django_basemodels.update_activity_status",
                defaults={"enabled": True},
            )

            if _task_created:
                logger.info("Created periodic task 'Models activity update'")
            else:
                logger.debug("Periodic task 'Models activity update' already exists")

        except Exception as exc:
            logger.exception("Failed to create periodic task in Celery signal handler: %s", exc)


@register
def check_dependencies(app_configs, **kwargs):
    errors = []
    required_apps = ["polymorphic", "safedelete"]

    for app in required_apps:
        if app not in settings.INSTALLED_APPS:
            errors.append(
                Error(
                    f"{app} must be in INSTALLED_APPS.",
                    hint=f"Please, add '{app}' to INSTALLED_APPS",
                    id="basemodels.E001",
                )
            )
    return errors
