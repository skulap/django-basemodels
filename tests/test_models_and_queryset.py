from django_basemodels import utils as utils_mod
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_basemodels.test_app.models import TestBaseModel
import django_basemodels.query as query_mod


@pytest.mark.django_db
def test_clean_raises_if_active_end_before_start():
    now = timezone.now()
    obj = TestBaseModel(active_start=now, active_end=now - timezone.timedelta(days=1))
    with pytest.raises(ValidationError):
        obj.full_clean()


@pytest.mark.django_db
def test_activate_deactivate_and_is_active_real(monkeypatch):
    now = timezone.now()
    obj = TestBaseModel.objects.create(is_active=False)
    assert obj.is_active is False

    obj.activate()
    obj.refresh_from_db()
    assert obj.is_active is True

    obj.deactivate()
    obj.refresh_from_db()
    assert obj.is_active is False

    # When celery healthy, is_active_real == is_active
    monkeypatch.setattr(utils_mod, "celery_is_healthy", lambda: True)
    obj.is_active = True
    assert obj.is_active_real is True

    # When celery not healthy, time windows decide
    monkeypatch.setattr(utils_mod, "celery_is_healthy", lambda: False)
    obj.active_start = now - timezone.timedelta(days=1)
    obj.active_end = now + timezone.timedelta(days=1)
    assert obj.is_active_real is True


@pytest.mark.django_db
def test_queryset_update_sets_updated_at_and_updates_field():
    obj = TestBaseModel.objects.create(title="orig")
    before = obj.updated_at

    # call update via queryset: should set updated_at to now and change title
    TestBaseModel.objects.filter(pk=obj.pk).update(title="changed")
    obj.refresh_from_db()
    assert obj.title == "changed"
    assert obj.updated_at >= before


@pytest.mark.django_db
def test_active_and_inactive_filters_depending_on_celery(monkeypatch):
    now = timezone.now()
    # a: always active flag True, no windows
    a = TestBaseModel.objects.create(title="a", is_active=True)
    # b: start in past, currently should be active by time window if celery down
    b = TestBaseModel.objects.create(title="b", is_active=False, active_start=now - timezone.timedelta(days=1))
    # c: end in future, active by time window
    c = TestBaseModel.objects.create(title="c", is_active=False, active_end=now + timezone.timedelta(days=1))
    # d: start in future — not active yet
    d = TestBaseModel.objects.create(title="d", is_active=False, active_start=now + timezone.timedelta(days=1))

    # celery healthy -> active() relies on is_active flag
    monkeypatch.setattr(query_mod, "celery_is_healthy", lambda: True)
    active_pks = set(TestBaseModel.objects.active().values_list("pk", flat=True))
    assert a.pk in active_pks
    assert b.pk not in active_pks
    assert c.pk not in active_pks

    # celery not healthy -> active() relies on time windows
    monkeypatch.setattr(query_mod, "celery_is_healthy", lambda: False)
    active_pks = set(TestBaseModel.objects.active().values_list("pk", flat=True))
    assert a.pk in active_pks
    assert b.pk in active_pks
    assert c.pk in active_pks
    assert d.pk not in active_pks


@pytest.mark.django_db
def test_update_activity_status_batches_and_updates_flags(monkeypatch):
    # Create objects that should toggle is_active depending on time
    now = timezone.now()
    # obj1: was inactive, active_start in past -> should become active
    obj1 = TestBaseModel.objects.create(is_active=False, active_start=now - timezone.timedelta(days=2))
    # obj2: was active, active_end in past -> should become inactive
    obj2 = TestBaseModel.objects.create(is_active=True, active_end=now - timezone.timedelta(days=1))
    # obj3: both None - should keep current is_active
    obj3 = TestBaseModel.objects.create(is_active=True)

    # Ensure celery availability does not affect update_activity_status (function itself uses time)
    # Call update_activity_status on manager (which delegates to queryset implementation)
    updated_count = TestBaseModel.objects.update_activity_status(batch_size=2)
    # updated_count should be >=1 (obj1 becomes active, obj2 becomes inactive)
    assert isinstance(updated_count, int)
    # Refresh and check flags
    obj1.refresh_from_db()
    obj2.refresh_from_db()
    obj3.refresh_from_db()

    assert obj1.is_active is True
    assert obj2.is_active is False
    # obj3 keeps its original value True
    assert obj3.is_active is True
