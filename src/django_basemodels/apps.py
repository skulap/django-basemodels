import importlib
import logging

from django.apps import AppConfig, apps
from django.conf import settings
from django.core.checks import Error, register
from django.db.models.signals import post_migrate
from django.utils.translation import gettext_lazy as _lazy

logger = logging.getLogger(__name__)


class DjangoBaseModelsAppConfig(AppConfig):
    name = 'django_basemodels'
    label = 'django_basemodels'
    verbose_name = _lazy("Базовые модели Django")
    default_auto_field = "django.db.models.AutoField"

    def ready(self):
        self._register_signal_handlers()

    def _register_signal_handlers(self):
        self._setup_periodic_task()

    def _setup_periodic_task(self):
        if not apps.is_installed("django_celery_beat"):
            logger.debug("django_celery_beat not installed in INSTALLED_APPS — skipping periodic task creation")
            return

        # Дополнительно проверяем, что пакет реально импортируется (установлен)
        try:
            importlib.import_module("django_celery_beat")
        except ImportError:
            logger.debug("django_celery_beat package not importable — skipping periodic task creation")
            return

        post_migrate.connect(
            self.create_models_activity_periodic_task,
            dispatch_uid="django_basemodels_create_models_activity_periodic_task",
        )

    @staticmethod
    def create_models_activity_periodic_task(sender, **kwargs):
        """
        Создаем расписание и периодическую задачу, если django_celery_beat доступен.
        Этот обработчик вызывается после миграций (post_migrate) — значит таблицы должны существовать.
        """
        # локальный импорт моделей через apps.get_model чтобы избежать раннего импорта
        try:
            IntervalSchedule = apps.get_model("django_celery_beat", "IntervalSchedule")
            PeriodicTask = apps.get_model("django_celery_beat", "PeriodicTask")
        except LookupError:
            # Модели недоступны (возможно пакет не подключен) — ничего не делаем
            logger.debug("django_celery_beat models not available — skipping creation")
            return

        try:
            # Обернём DB-операции в try/except — на случай что БД недоступна в процессе 'makemigrations' и т.п.
            schedule, _created = IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.MINUTES,
            )
            PeriodicTask.objects.get_or_create(
                interval=schedule,
                name="Models activity update",
                task="django_basemodels.update_activity_status",
            )
            logger.info("Ensured periodic task 'Models activity update' exists (django_celery_beat)")
        except Exception as exc:
            # Логируем, но не пробрасываем — чтобы не ломать команды manage.py
            logger.exception("Failed to ensure periodic task for models activity: %s", exc)


@register
def check_dependencies(app_configs, **kwargs):
    errors = []
    required_apps = ['polymorphic', 'safedelete']

    for app in required_apps:
        if app not in settings.INSTALLED_APPS:
            errors.append(
                Error(
                    f"{app} must be in INSTALLED_APPS.",
                    hint=f"Please, add '{app}' to INSTALLED_APPS",
                    id='basemodels.E001',
                )
            )
    return errors
