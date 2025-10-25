import logging

from . import CELERY_AVAILABLE

if CELERY_AVAILABLE:
    import celery_hchecker
else:
    celery_hchecker = None

logger = logging.getLogger(__name__)


def celery_is_healthy() -> bool:
    """
    Возвращает True, если Celery доступен и воркеры запущены.
    Если Celery не установлен, возвращает False.
    """
    try:
        if not CELERY_AVAILABLE:
            return False

        checker: celery_hchecker.CeleryHealthChecker = celery_hchecker.CeleryHealthChecker.get_instance()
    except Exception as exc:
        logger.error("Error checking Celery health", exc_info=exc)
        return False

    if checker is None:
        logger.warning(
            "Warning: Celery health checker is not initialized. "
            "Please create celery health checker instance if you use celery.",
            stacklevel=2,
        )
        return False

    try:
        return checker.is_healthy
    except Exception as exc:
        logger.error("Error checking Celery health", exc_info=exc)
        return False
