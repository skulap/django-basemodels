import logging

import celery_hchecker

logger = logging.getLogger(__name__)


def celery_is_healthy() -> bool:
    """
    Возвращает True, если Celery доступен и воркеры запущены.
    Бросает RuntimeError, если CeleryHealthChecker не инициализирован.
    """
    try:
        checker: celery_hchecker.CeleryHealthChecker = celery_hchecker.CeleryHealthChecker.get_instance()
    except Exception as exc:
        logger.error("Error checking Celery health", exc_info=exc)
        return False

    if checker is None:
        logger.warning(
            'Warning: Celery health checker is not initialized. '
            'Please create celery health checker instance if you use celery.',
            stacklevel=2
        )
        return False
    try:
        return checker.is_healthy
    except Exception as exc:
        logger.error("Error checking Celery health", exc_info=exc)
        return False
