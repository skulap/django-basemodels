from unittest import mock

from django_basemodels import utils


def test_celery_is_healthy_when_celery_not_available(monkeypatch):
    """Тестируем celery_is_healthy когда Celery недоступен"""
    monkeypatch.setattr(utils, "CELERY_AVAILABLE", False)
    assert utils.celery_is_healthy() is False


def test_celery_is_healthy_when_checker_returns_healthy(monkeypatch):
    """Тестируем celery_is_healthy когда checker возвращает здоровый статус"""
    monkeypatch.setattr(utils, "CELERY_AVAILABLE", True)

    mock_checker = mock.MagicMock()
    mock_checker.is_healthy = True
    mock_checker.get_instance.return_value = mock_checker

    monkeypatch.setattr("django_basemodels.utils.celery_hchecker", mock.MagicMock())
    monkeypatch.setattr("django_basemodels.utils.celery_hchecker.CeleryHealthChecker", mock_checker)

    assert utils.celery_is_healthy() is True


def test_celery_is_healthy_when_checker_returns_unhealthy(monkeypatch):
    """Тестируем celery_is_healthy когда checker возвращает нездоровый статус"""
    monkeypatch.setattr(utils, "CELERY_AVAILABLE", True)

    mock_checker = mock.MagicMock()
    mock_checker.is_healthy = False
    mock_checker.get_instance.return_value = mock_checker

    monkeypatch.setattr("django_basemodels.utils.celery_hchecker", mock.MagicMock())
    monkeypatch.setattr("django_basemodels.utils.celery_hchecker.CeleryHealthChecker", mock_checker)

    assert utils.celery_is_healthy() is False


def test_celery_is_healthy_handles_exception(monkeypatch):
    """Тестируем обработку исключений в celery_is_healthy"""
    monkeypatch.setattr(utils, "CELERY_AVAILABLE", True)
    monkeypatch.setattr(
        "django_basemodels.utils.celery_hchecker.CeleryHealthChecker.get_instance",
        lambda: (_ for _ in ()).throw(Exception("Checker error")),
    )

    assert utils.celery_is_healthy() is False
