
from django.core.checks import Error
from django_basemodels.apps import DjangoBaseModelsAppConfig


def test_create_models_activity_periodic_task_skips_if_no_django_celery_beat(monkeypatch):
    # Simulate django_celery_beat not installed in INSTALLED_APPS
    monkeypatch.setattr("django.apps.apps.is_installed", lambda name: False)
    # Should not raise
    DjangoBaseModelsAppConfig.create_models_activity_periodic_task(None)


def test_create_models_activity_periodic_task_handles_models(monkeypatch):
    # Simulate django_celery_beat installed
    monkeypatch.setattr("django.apps.apps.is_installed", lambda name: True)

    # Simulate importlib can import module (we just let it pass)
    # Provide fake IntervalSchedule and PeriodicTask models with get_or_create methods
    class FakeSchedule:
        MINUTES = 0

        @classmethod
        def objects(cls):  # not used
            pass

    class FakeIntervalSchedule:
        MINUTES = 0
        objects = type("O", (), {"get_or_create": staticmethod(lambda every, period: (object(), True))})

    class FakePeriodicTask:
        objects = type("O", (), {"get_or_create": staticmethod(lambda interval, name, task: (object(), True))})

    # monkeypatch importlib.import_module to return a dummy module (not strictly necessary)
    monkeypatch.setattr("importlib.import_module", lambda name: True)

    # monkeypatch apps.get_model to return our fake models
    def _get_model(label, model):
        if label == "django_celery_beat" and model == "IntervalSchedule":
            return FakeIntervalSchedule
        if label == "django_celery_beat" and model == "PeriodicTask":
            return FakePeriodicTask
        raise LookupError()

    monkeypatch.setattr("django.apps.apps.get_model", _get_model)

    # Should not raise
    DjangoBaseModelsAppConfig.create_models_activity_periodic_task(None)
