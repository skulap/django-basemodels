from unittest import mock

import django_basemodels.tasks as tasks_mod
import pytest
from django_basemodels.test_app.models import TestBaseModel


@pytest.mark.django_db
def test__get_models_with_activity_includes_test_model():
    models = list(tasks_mod._get_models_with_activity())
    assert any(m is TestBaseModel for m in models)


@pytest.mark.django_db
def test_update_model_activity_calls_update_activity_status(monkeypatch):
    # create objects
    TestBaseModel.objects.create(is_active=False)

    # monkeypatch apps.get_model to return our model when called with the label
    label = TestBaseModel._meta.label_lower
    monkeypatch.setattr("django_basemodels.tasks.apps.get_model", lambda lbl: TestBaseModel if lbl == label else None)

    # call the task — should run without exceptions
    tasks_mod.update_model_activity(label)


@pytest.mark.django_db
def test_update_activity_status_uses_group_and_apply_async(monkeypatch):
    # Force _get_models_with_activity to return a small list
    monkeypatch.setattr("django_basemodels.tasks._get_models_with_activity", lambda: [TestBaseModel])
    fake_group = mock.MagicMock()
    fake_group.apply_async = mock.MagicMock()

    # monkeypatch group() used in the module
    monkeypatch.setattr("django_basemodels.tasks.group", lambda tasks: fake_group)

    tasks_mod.update_activity_status()
    fake_group.apply_async.assert_called_once()
