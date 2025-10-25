from unittest import mock

import pytest
from django_basemodels.celery import get_models_with_activity, update_activity_status_task, update_model_activity_task
from django_basemodels.test_app.models import TestBaseModel


@pytest.mark.django_db
def test_get_models_with_activity_includes_test_model():
    """Тестируем что функция возвращает тестовую модель"""
    models = list(get_models_with_activity())
    assert any(m is TestBaseModel for m in models)


@pytest.mark.django_db
def test_update_model_activity_task_calls_update_activity_status(monkeypatch):
    """Тестируем задачу обновления активности для конкретной модели"""
    # Создаем объект
    obj = TestBaseModel.objects.create(is_active=False)

    # Мокаем apps.get_model чтобы возвращала нашу тестовую модель
    monkeypatch.setattr("django_basemodels.celery.apps.get_model", lambda model_label: TestBaseModel)

    # Мокаем update_activity_status чтобы проверить вызов
    with mock.patch.object(TestBaseModel.objects, "update_activity_status") as mock_update:
        mock_update.return_value = 1
        result = update_model_activity_task(TestBaseModel._meta.label_lower)

        # Проверяем что метод был вызван
        mock_update.assert_called_once()
        # Проверяем что возвращается количество обновленных объектов
        assert result == 1


@pytest.mark.django_db
def test_update_model_activity_task_handles_exception(monkeypatch, caplog):
    """Тестируем обработку исключений в задаче"""
    # Мокаем исключение при получении модели
    monkeypatch.setattr(
        "django_basemodels.celery.apps.get_model", lambda model_label: (_ for _ in ()).throw(Exception("Model error"))
    )

    # Вызываем задачу и проверяем что исключение пробрасывается
    with pytest.raises(Exception, match="Model error"):
        update_model_activity_task("nonexistent.Model")


@pytest.mark.django_db
def test_update_activity_status_task_creates_group():
    """Тестируем основную задачу обновления активности"""
    # Мокаем get_models_with_activity чтобы возвращала тестовую модель
    with mock.patch("django_basemodels.celery.get_models_with_activity") as mock_get_models:
        mock_get_models.return_value = [TestBaseModel]

        # Мокаем group и apply_async
        with mock.patch("django_basemodels.celery.group") as mock_group:
            mock_group_instance = mock.MagicMock()
            mock_group.return_value = mock_group_instance

            # Вызываем задачу
            result = update_activity_status_task()

            # Проверяем что group был создан с правильными параметрами
            mock_group.assert_called_once()

            # Проверяем что apply_async был вызван
            mock_group_instance.apply_async.assert_called_once()

            # Проверяем возвращаемое значение
            assert "Started update for 1 models" in result


@pytest.mark.django_db
def test_update_activity_status_task_no_models():
    """Тестируем задачу когда нет моделей для обновления"""
    # Мокаем пустой список моделей
    with mock.patch("django_basemodels.celery.get_models_with_activity") as mock_get_models:
        mock_get_models.return_value = []

        # Вызываем задачу
        result = update_activity_status_task()

        # Проверяем возвращаемое значение
        assert result == "No models to update"
