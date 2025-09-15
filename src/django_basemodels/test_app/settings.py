from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

SECRET_KEY = "test-secret-key"
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",

    # внешние зависимости, требуемые пакетом
    "polymorphic",
    "safedelete",

    # сам пакет и тестовое тест-приложение внутри него
    "django_basemodels",
    "django_basemodels.test_app",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

MIDDLEWARE = []

USE_TZ = True
TIME_ZONE = "UTC"

# Чтобы не было проблем с auto field
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
