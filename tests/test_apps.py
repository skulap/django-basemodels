from unittest import mock

import pytest
from django.apps import apps


@pytest.fixture
def app_config():
    """Фикстура для получения реальной конфигурации приложения"""
    return apps.get_app_config("django_basemodels")


def test_register_celery_handlers_with_celery_available(app_config, monkeypatch):
    """Тестируем регистрацию Celery обработчиков когда Celery доступен"""
    # Мокаем доступность Celery
    monkeypatch.setattr("django_basemodels.apps.CELERY_AVAILABLE", True)
    monkeypatch.setattr("django.apps.apps.is_installed", lambda name: name == "django_celery_beat")

    # Мокаем celery_app
    with mock.patch("django_basemodels.apps.celery_app") as mock_celery_app:
        app_config._register_celery_handlers()

        # Проверяем, что сигнал был зарегистрирован
        mock_celery_app.on_after_configure.connect.assert_called_once_with(app_config._create_periodic_task)


def test_register_celery_handlers_without_celery(app_config, monkeypatch):
    """Тестируем что обработчики не регистрируются когда Celery недоступен"""
    # Мокаем отсутствие Celery
    monkeypatch.setattr("django_basemodels.apps.CELERY_AVAILABLE", False)

    # Мокаем celery_app
    with mock.patch("django_basemodels.apps.celery_app") as mock_celery_app:
        app_config._register_celery_handlers()

        # Проверяем, что сигнал НЕ был зарегистрирован
        mock_celery_app.on_after_configure.connect.assert_not_called()


def test_register_celery_handlers_without_celery_beat(app_config, monkeypatch):
    """Тестируем что обработчики не регистрируются когда django_celery_beat не установлен"""
    # Мокаем доступность Celery но отсутствие django_celery_beat
    monkeypatch.setattr("django_basemodels.apps.CELERY_AVAILABLE", True)
    monkeypatch.setattr("django.apps.apps.is_installed", lambda name: False)

    # Мокаем celery_app
    with mock.patch("django_basemodels.apps.celery_app") as mock_celery_app:
        app_config._register_celery_handlers()

        # Проверяем, что сигнал НЕ был зарегистрирован
        mock_celery_app.on_after_configure.connect.assert_not_called()


def test_create_periodic_task_success(app_config, monkeypatch):
    """Тестируем успешное создание периодической задачи"""
    # Мокаем модели django_celery_beat
    mock_schedule = mock.MagicMock()
    mock_task = mock.MagicMock()

    mock_interval_schedule_class = mock.MagicMock()
    mock_interval_schedule_class.objects.get_or_create.return_value = (mock_schedule, True)
    mock_interval_schedule_class.MINUTES = "minutes"

    mock_periodic_task_class = mock.MagicMock()
    mock_periodic_task_class.objects.get_or_create.return_value = (mock_task, True)

    # Мокаем импорты внутри метода
    with (
        mock.patch("django_celery_beat.models.IntervalSchedule", mock_interval_schedule_class),
        mock.patch("django_celery_beat.models.PeriodicTask", mock_periodic_task_class),
    ):
        # Вызываем метод
        app_config._create_periodic_task()

        # Проверяем вызовы
        mock_interval_schedule_class.objects.get_or_create.assert_called_once_with(
            every=1,
            period="minutes",
        )
        mock_periodic_task_class.objects.get_or_create.assert_called_once_with(
            interval=mock_schedule,
            name="Models activity update",
            task="django_basemodels.update_activity_status",
            defaults={"enabled": True},
        )


def test_create_periodic_task_handles_exception(app_config, monkeypatch, caplog):
    """Тестируем обработку исключений при создании периодической задачи"""
    # Мокаем исключение при получении моделей
    with mock.patch("django_basemodels.apps.apps.get_model") as mock_get_model:
        mock_get_model.side_effect = LookupError("Model not found")

        # Вызываем метод и проверяем что исключение обработано
        app_config._create_periodic_task()

        # Проверяем что ошибка была залогирована
        assert "Failed to create periodic task in Celery signal handler" in caplog.text


def test_ready_method_registers_handlers(app_config, monkeypatch):
    """Тестируем что ready метод регистрирует обработчики"""
    with mock.patch.object(app_config, "_register_celery_handlers") as mock_register:
        app_config.ready()
        mock_register.assert_called_once()
