import os
import sys
from pathlib import Path

# 1) Путь к корню проекта (где лежат pyproject.toml и pytest.ini)
ROOT = Path(__file__).resolve().parents[1]

# 2) Добавляем src/ в sys.path (poetry src layout)
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# 3) Добавим корень проекта в sys.path, чтобы можно было импортировать tests.test_settings
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 4) Устанавливаем DJANGO_SETTINGS_MODULE ранним (если ещё не установлен)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.test_settings")

# 5) Выполняем django.setup() чтобы настройки были доступны до импорта моделей
#    Это безопасно: pytest-django обычно делает setup, но ранний вызов в conftest
#    решает проблемы при топ-левел импортaх в тестах/модулях.
import django

django.setup()
