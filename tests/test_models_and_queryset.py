import django_basemodels.query as query_mod
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_basemodels import utils as utils_mod
from django_basemodels.test_app.models import TestBaseModel


@pytest.mark.django_db
def test_clean_raises_if_active_end_before_start():
    """Тестируем валидацию временных интервалов активности"""
    now = timezone.now()
    obj = TestBaseModel(active_start=now, active_end=now - timezone.timedelta(days=1))
    with pytest.raises(ValidationError):
        obj.full_clean()


@pytest.mark.django_db
def test_activate_deactivate_and_is_active_real(monkeypatch):
    """Тестируем методы активации/деактивации и свойство is_active_real"""
    now = timezone.now()
    obj = TestBaseModel.objects.create(is_active=False)
    assert obj.is_active is False

    obj.activate()
    obj.refresh_from_db()
    assert obj.is_active is True

    obj.deactivate()
    obj.refresh_from_db()
    assert obj.is_active is False

    # Когда Celery доступен, is_active_real == is_active
    monkeypatch.setattr(utils_mod, "celery_is_healthy", lambda: True)
    obj.is_active = True
    assert obj.is_active_real is True

    # Когда Celery недоступен, решают временные окна
    monkeypatch.setattr(utils_mod, "celery_is_healthy", lambda: False)
    obj.active_start = now - timezone.timedelta(days=1)
    obj.active_end = now + timezone.timedelta(days=1)
    assert obj.is_active_real is True


@pytest.mark.django_db
def test_queryset_update_sets_updated_at_and_updates_field():
    """Тестируем что queryset.update обновляет updated_at"""
    obj = TestBaseModel.objects.create(title="orig")
    before = obj.updated_at

    # Вызываем update через queryset: должен установить updated_at и изменить title
    TestBaseModel.objects.filter(pk=obj.pk).update(title="changed")
    obj.refresh_from_db()
    assert obj.title == "changed"
    assert obj.updated_at >= before


@pytest.mark.django_db
def test_active_and_inactive_filters_depending_on_celery(monkeypatch):
    """Тестируем фильтры active/inactive в зависимости от доступности Celery"""
    now = timezone.now()
    # a: всегда активен, флаг True, нет окон
    a = TestBaseModel.objects.create(title="a", is_active=True)
    # b: начало в прошлом, должен быть активен по временному окну если Celery недоступен
    b = TestBaseModel.objects.create(title="b", is_active=False, active_start=now - timezone.timedelta(days=1))
    # c: конец в будущем, активен по временному окну
    c = TestBaseModel.objects.create(title="c", is_active=False, active_end=now + timezone.timedelta(days=1))
    # d: начало в будущем — еще не активен
    d = TestBaseModel.objects.create(title="d", is_active=False, active_start=now + timezone.timedelta(days=1))

    # Celery доступен -> active() полагается на флаг is_active
    monkeypatch.setattr(query_mod, "celery_is_healthy", lambda: True)
    active_pks = set(TestBaseModel.objects.active().values_list("pk", flat=True))
    assert a.pk in active_pks
    assert b.pk not in active_pks
    assert c.pk not in active_pks

    # Celery недоступен -> active() полагается на временные окна
    monkeypatch.setattr(query_mod, "celery_is_healthy", lambda: False)
    active_pks = set(TestBaseModel.objects.active().values_list("pk", flat=True))
    assert a.pk in active_pks
    assert b.pk in active_pks
    assert c.pk in active_pks
    assert d.pk not in active_pks


@pytest.mark.django_db
def test_update_activity_status_batches_and_updates_flags(monkeypatch):
    """Тестируем массовое обновление статусов активности"""
    # Создаем объекты которые должны изменить is_active в зависимости от времени
    now = timezone.now()
    # obj1: был неактивен, начало активности в прошлом -> должен стать активным
    obj1 = TestBaseModel.objects.create(is_active=False, active_start=now - timezone.timedelta(days=2))
    # obj2: был активен, конец активности в прошлом -> должен стать неактивным
    obj2 = TestBaseModel.objects.create(is_active=True, active_end=now - timezone.timedelta(days=1))
    # obj3: оба None - должен сохранить текущий is_active
    obj3 = TestBaseModel.objects.create(is_active=True)

    # Вызываем update_activity_status на менеджере
    updated_count = TestBaseModel.objects.update_activity_status(batch_size=2)

    # Проверяем что возвращается число
    assert isinstance(updated_count, int)

    # Обновляем и проверяем флаги
    obj1.refresh_from_db()
    obj2.refresh_from_db()
    obj3.refresh_from_db()

    assert obj1.is_active is True
    assert obj2.is_active is False
    # obj3 сохраняет оригинальное значение True
    assert obj3.is_active is True
