import typing as tp

from django.db import models
from polymorphic.managers import PolymorphicManager
from safedelete.config import DELETED_INVISIBLE
from safedelete.managers import SafeDeleteManager

from .query import BaseModelQuerySet


class BaseModelManager(SafeDeleteManager, PolymorphicManager):
    queryset_class = BaseModelQuerySet
    _queryset_class = BaseModelQuerySet

    def __init__(
            self,
            queryset_class: tp.Optional[tp.Type[BaseModelQuerySet]] = None,
            safedelete_visibility: int = DELETED_INVISIBLE
    ):
        super().__init__(queryset_class)

        if safedelete_visibility:
            self._safedelete_visibility = safedelete_visibility

    @classmethod
    def from_queryset(cls, queryset_class, class_name=None):
        manager = models.Manager.from_queryset(queryset_class, class_name=class_name)
        manager.queryset_class = queryset_class
        return manager

    def get_queryset(self):
        queryset = self._queryset_class(self.model, using=self._db, hints=self._hints)
        queryset.query._safedelete_visibility = self._safedelete_visibility
        queryset.query._safedelete_visibility_field = self._safedelete_visibility_field

        if self.model._meta.proxy:
            queryset = queryset.instance_of(self.model)

        return queryset

    def __str__(self):
        return (
            f"{self.__class__.__name__} (BaseModelManager) using {self.queryset_class.__name__}"
        )

    def activate(self):
        return self.get_queryset().activate()

    def deactivate(self):
        return self.get_queryset().deactivate()

    def active(self):
        return self.get_queryset().active()

    def inactive(self):
        return self.get_queryset().inactive()

    def update_activity_status(self, batch_size=1000):
        return self.get_queryset().update_activity_status(batch_size=batch_size)
