import typing as tp

from django.db import models
from django.utils import timezone
from polymorphic.query import PolymorphicModelIterable, PolymorphicQuerySet
from safedelete.query import SafeDeleteQuery
from safedelete.queryset import SafeDeleteQueryset

from .utils import celery_is_healthy


class BaseModelQuerySet(SafeDeleteQueryset, PolymorphicQuerySet):
    def __init__(self,
                 model: tp.Optional[tp.Type[models.Model]] = None,
                 query: tp.Optional[SafeDeleteQuery] = None,
                 using: tp.Optional[str] = None,
                 hints: tp.Optional[tp.Dict[str, models.Model]] = None):
        # safedelete
        super(BaseModelQuerySet, self).__init__(model=model, query=query, using=using, hints=hints)
        self.query: SafeDeleteQuery = query or SafeDeleteQuery(self.model)

        # polymorphic
        self._iterable_class = PolymorphicModelIterable

        self.polymorphic_disabled = False
        self.polymorphic_deferred_loading = (set(), True)

    @classmethod
    def as_manager(cls):
        from .managers import BaseModelManager

        manager = BaseModelManager.from_queryset(cls)()
        manager._built_with_as_manager = True
        return manager

    as_manager.queryset_only = True

    def update(self, **kwargs):
        """
        При любом обновлении автоматически ставим updated_at = timezone.now().
        """
        kwargs['updated_at'] = timezone.now()
        return super().update(**kwargs)

    def activate(self):
        """
        Массово установить is_active=True → обновится updated_at.
        """
        return super().update(is_active=True)

    def deactivate(self):
        """
        Массово установить is_active=False → обновится updated_at.
        """
        return super().update(is_active=False)

    def _active_q(self):
        """Условие для определения реальной активности элемента (по времени)."""
        now = timezone.now()
        always = models.Q(is_active=True, active_start__isnull=True, active_end__isnull=True)

        timed_both = models.Q(
            active_start__isnull=False,
            active_end__isnull=False,
            active_start__lte=now,
            active_end__gte=now
        )
        timed_start_only = models.Q(
            active_start__isnull=False,
            active_end__isnull=True,
            active_start__lte=now
        )
        timed_end_only = models.Q(
            active_start__isnull=True,
            active_end__isnull=False,
            active_end__gte=now
        )

        return always | timed_both | timed_start_only | timed_end_only

    def active(self):
        """
        Возвращает только активные элементы
        Если celery доступен, то возвращает элементы с фильтрацией по полю is_active=True.
        Если celery недоступен, возвращает элементы с фильтрацией по условию определения реальной активности.
        """
        if celery_is_healthy():
            return self.filter(is_active=True)
        return self.filter(self._active_q())

    def inactive(self):
        """
        Возвращает только неактивные элементы
        Если celery доступен, то возвращает элементы с фильтрацией по полю is_active=False.
        Если celery недоступен, возвращает элементы с фильтрацией по условию определения реальной активности.
        """
        if celery_is_healthy():
            return self.filter(is_active=False)

        return self.filter(~self._active_q())

    def update_activity_status(self, batch_size=1000):
        """
        Обновляет is_active для всех объектов в queryset по правилам:
          - Если задан active_start: active_start <= now
          - Если задан active_end: active_end >= now
          - Если оба не заданы: сохраняем текущее is_active
        """
        now = timezone.now()

        is_active_condition = models.Case(
            models.When(
                models.Q(active_start__isnull=False, active_end__isnull=False),
                then=models.Q(active_start__lte=now, active_end__gte=now)
            ),
            models.When(
                models.Q(active_start__isnull=False, active_end__isnull=True),
                then=models.Q(active_start__lte=now)
            ),
            models.When(
                models.Q(active_start__isnull=True, active_end__isnull=False),
                then=models.Q(active_end__gte=now)
            ),
            models.When(
                models.Q(active_start__isnull=True, active_end__isnull=True),
                then=models.F('is_active')
            ),
            default=models.Value(True),
            output_field=models.BooleanField()
        )

        # Обходим BaseModelQuerySet.update(), чтобы не обновлять updated_at
        return models.QuerySet.update(self, is_active=is_active_condition)
