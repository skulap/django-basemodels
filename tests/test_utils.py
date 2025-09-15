import logging

import django_basemodels.utils as utils


class DummyChecker:
    def __init__(self, healthy=True):
        self.is_healthy = healthy


def test_celery_is_healthy_when_not_initialized(monkeypatch, caplog):
    monkeypatch.setattr("celery_hchecker.CeleryHealthChecker.get_instance", lambda: None)
    caplog.set_level(logging.WARNING)
    assert utils.celery_is_healthy() is False
    assert "Celery health checker is not initialized" in caplog.text


def test_celery_is_healthy_when_true(monkeypatch):
    monkeypatch.setattr("celery_hchecker.CeleryHealthChecker.get_instance", lambda: DummyChecker(True))
    assert utils.celery_is_healthy() is True


def test_celery_is_healthy_when_false(monkeypatch):
    monkeypatch.setattr("celery_hchecker.CeleryHealthChecker.get_instance", lambda: DummyChecker(False))
    assert utils.celery_is_healthy() is False


def test_celery_is_healthy_handles_exception(monkeypatch, caplog):
    def _bad():
        raise RuntimeError("boom")

    monkeypatch.setattr("celery_hchecker.CeleryHealthChecker.get_instance", _bad)
    caplog.set_level(logging.ERROR)
    assert utils.celery_is_healthy() is False
    assert "Error checking Celery health" in caplog.text
