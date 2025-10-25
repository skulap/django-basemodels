# django-basemodels

`django-basemodels` — небольшой, но гибкий пакет для Django, который предоставляет абстрактную базовую модель с:
- поддержкой полиморфизма (через `django-polymorphic`);
- безопасного удаления (soft-delete) через `django-safedelete`;
- полями и утилитами для управления активности записей (`is_active`, `active_start`, `active_end`);
- массовыми операциями и менеджером/QuerySet с полезными методами (`active()`, `inactive()`, `activate()`, `deactivate()`, `update_activity_status()`);
- интеграцией с Celery для периодического обновления статуса активности.

Проект спроектирован как drop-in база для ваших моделей: вы наследуете BaseModel, и получаете все возможности готовой логики управления состоянием и удаления.

## Особенности
- Абстрактная `BaseModel` — готовые поля: `created_at`, `updated_at`, `is_active`, `active_start`, `active_end`.
- Менеджер `objects` поддерживает soft-delete через `django-safedelete`.
- Полиморфизм через `django-polymorphic`.
- Удобные массовые методы: `activate()`, `deactivate()`, `active()`, `inactive()`.
- Задача celery для периодического обновления is_active у моделей: `django_basemodels.update_activity_status`
- Поддержка конфигурации `django_celery_beat` — при наличии создаётся периодическая задача.

## Требования
- Python >=3.12
- Django >=5.0
- `django-polymorphic`
- `django-safedelete`
- (опционально) `celery` и `django_celery_beat` для автоматического обновления активности
- (опционально) `celery_hchecker` — для проверки состояния Celery в рантайме (если используется)

## Установка
### Базовая установка (без Celery)
```bash
pip install django-basemodels
```

### С поддержкой Celery
```bash
pip install django-basemodels[celery]
```

### Функции, доступные только в Celery:
- Автоматическое обновление статуса активности
- Периодические задачи через django-celery-beat
- Проверка здоровья celery

### Добавьте в INSTALLED_APPS в settings.py:
```python
INSTALLED_APPS = [
    # ...
    "polymorphic",
    "safedelete",
    "django_basemodels",
    # ...
]
```



## Быстрый старт
### Определение модели:
```python
from django.db import models
from django_basemodels.models import BaseModel

class Article(BaseModel):
    title = models.CharField(max_length=255)
    body = models.TextField()
```

### Использование менеджера и методов:
```python
# получение активных записей (в зависимости от состояния Celery — по флагу is_active или по временным полям)
Article.objects.active()

# массовая деактивация
Article.objects.deactivate()

# массовая активация
Article.objects.activate()

# вручную обновить is_active для всех записей по правилам active_start/active_end
Article.objects.update_activity_status(batch_size=500)
```

### Доступ ко всем (включая удаленные) объектам:
```python
Article.all_objects.all()        # видимы даже soft-deleted при DELETED_VISIBLE
Article.deleted_objects.all() 
```

## Краткое API

**BaseModel (абстрактный)**
- `created_at`, `updated_at` — авто-поля времени.
- `is_active`, `active_start`, `active_end` — управление активности.
- `activate()` / `deactivate()` — изменения с сохранением `updated_at`.
- `is_active_real` — вычисление активности (учитывает состояние Celery).

**BaseModelQuerySet / BaseModelManager**
- `update(**kwargs)` — при массовом обновлении ставит `updated_at = now()`.
- `active()` / `inactive()` — возвращает элементы в зависимости от доступности Celery (по флагу или по временным полям).
- `update_activity_status(batch_size=1000)` — пересчитывает `is_active` батчами, использует `bulk_update`.

## Celery и `django_celery_beat`

- Задачи: `django_basemodels.update_model_activity(model_label)` и `django_basemodels.update_activity_status()`.
- При наличии `django_celery_beat` пакет попытается создать периодическую задачу после миграций.
- Для проверки состояния Celery используется `celery_hchecker`. Если он не инициализирован, `active()` будет полагаться на временные поля.

## Тестирование (pytest)

Рекомендуемая структура проекта: `src/` + `tests/` (poetry default). Установите `pytest` и `pytest-django` и запустите:

```bash
poetry add --dev pytest pytest-django
poetry run pytest -q
```

Примеры важных замечаний при тестировании:
- Если `query.py` использует `from .utils import celery_is_healthy`, то в тестах патчить нужно `django_basemodels.query.celery_is_healthy`.
- Альтернативно, поменяйте импорт в `query.py` на `from . import utils` и патчьте `django_basemodels.utils.celery_is_healthy`.


## Практические советы

- `update_activity_status` рассчитан на большую нагрузку (батчи + `bulk_update`). Настройте `batch_size` под вашу БД.
- Добавьте логирование в задачи Celery в продакшене для мониторинга числа обновлённых записей.
- Для крупных таблиц рассмотрите частичные индексы (Postgres) по условию активности.


## Лицензия
MIT