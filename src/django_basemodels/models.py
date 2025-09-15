from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _lazy
from polymorphic.models import PolymorphicModel
from safedelete.config import DELETED_ONLY_VISIBLE, DELETED_VISIBLE, HARD_DELETE
from safedelete.config import FIELD_NAME as SAFEDELETE_FIELD_NAME
from safedelete.models import SafeDeleteModel

from .managers import BaseModelManager
from .utils import celery_is_healthy


class BaseModel(SafeDeleteModel, PolymorphicModel):
    _safedelete_policy = HARD_DELETE

    class Meta:
        abstract = True
        ordering = ['-updated_at']
        indexes = [
            # Для запросов типа .filter(is_active=True)
            models.Index(fields=['is_active']),

            # Для временных диапазонов
            models.Index(fields=['active_start', 'active_end']),

            # Для часто используемых комбинаций
            models.Index(fields=['is_active', 'active_start']),
            models.Index(fields=['is_active', 'active_end']),

            models.Index(fields=['is_active', 'active_start', 'active_end']),
            models.Index(fields=['active_start']),
            models.Index(fields=['active_end']),
            models.Index(fields=['polymorphic_ctype']),
            models.Index(fields=[SAFEDELETE_FIELD_NAME]),
        ]

    created_at = models.DateTimeField(
        name="created_at", auto_now_add=True, null=False, blank=True, editable=False,
        verbose_name=_lazy("Дата создания")
    )
    updated_at = models.DateTimeField(
        name="updated_at", auto_now=True, null=False, blank=True, editable=False,
        verbose_name=_lazy("Время последнего обновления")
    )
    is_active = models.BooleanField(
        default=True,
        null=False, blank=True,
        verbose_name=_lazy("Активность")
    )
    active_start = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_lazy("Начало активности")
    )
    active_end = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_lazy("Конец активности")
    )

    objects = BaseModelManager()
    all_objects = BaseModelManager(safedelete_visibility=DELETED_VISIBLE)
    deleted_objects = BaseModelManager(safedelete_visibility=DELETED_ONLY_VISIBLE)

    def clean(self):
        if self.active_start and self.active_end and self.active_end < self.active_start:
            raise ValidationError(_lazy("Конец активности не может быть раньше начала"))

        super().clean()

    def activate(self):
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    def deactivate(self):
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    @property
    def is_active_real(self):
        if celery_is_healthy():
            return self.is_active

        if not self.active_start and not self.active_end:
            return self.is_active

        now = timezone.now()
        active_start = self.active_start or now
        return (active_start <= now) and (self.active_end >= now if self.active_end else True)
