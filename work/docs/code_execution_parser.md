# Code Execution Errors Parser — описание реализации

**Дата:** 2026-06-05
**TZ:** 10
**Статус:** Реализован, не запущен (требует оптимизации)

---

## Что сделано

Создан парсер для извлечения **runtime errors** (ошибок выполнения) из nebius/SWE-agent-trajectories.

### Отличие от invalid_invocation

| Тип | Когда возникает | Пример |
|-----|-----------------|--------|
| `invalid_invocation` | Pre-execution (edit tool) | SyntaxError, undefined name |
| `code_execution` | Runtime (выполнение кода) | TypeError, AttributeError |

### Два выходных файла

1. **errors.parquet** (TP) — ошибки из скриптов агента
2. **errors_issue.parquet** (FP) — ошибки из описания issue

---

## Логика работы

### 1. Agent-written scripts (TP)

Скрипты, созданные агентом:
- `/reproduce.py` — основной скрипт воспроизведения
- `/test_*.py` — unit tests
- `/run_*.py` — runner scripts

Если traceback указывает на эти файлы → TP (истинная ошибка агента).

### 2. Issue description (FP)

Если в тексте есть Python error, но нет пути к скрипту агента →
вероятно скопировано из описания issue → FP.

### 3. Исключения

- **Edit validation** (`Your proposed edit has introduced`) → это E1/E2, не code_execution
- **Network errors** (HTTPError, Connection refused) → не code_execution

---

## Структура файлов

```
work/MAS_errors/parsers/nebius/code_execution/
  __init__.py
  parser.py
  code_execution/
    errors.parquet        # TP (full)
    errors_dedup.parquet  # TP (deduped)
    errors_issue.parquet  # FP
    stats.json
  tests/
    test_parser.py
```

---

## Ключевые функции

| Функция | Назначение |
|---------|------------|
| `matches_agent_script()` | TP: Python error + agent script path |
| `matches_issue_description()` | FP: Python error без agent script |
| `parse_error_type()` | Извлечение типа ошибки |
| `normalize_error_pattern()` | Нормализация для дедупликации |
| `is_edit_validation()` | Исключить E1/E2 |
| `is_network_error()` | Исключить HTTP errors |

---

## Subtypes (предварительная статистика из 5000 траекторий)

| Subtype | Доля |
|---------|------|
| TypeError | 32.0% |
| AttributeError | 24.8% |
| ImportError | 14.9% |
| ModuleNotFoundError | 9.9% |
| ValueError | 9.1% |
| Other | 9.3% |

---

## Проблема: производительность

Парсер работает на 80 036 траекториях и слишком медленный.

**Причина:** Итерация по всем шагам всех траекторий с подсчётом `running_chars` на каждом шаге.

**Решение:** Использовать sampling (5000 траекторий как в TZ_2 v2) или joblib parallelization.

---

## Запуск

```bash
# Тесты
PYTHONPATH=. python -c "
from work.MAS_errors.parsers.nebius.code_execution.parser import (
    matches_agent_script, matches_issue_description, parse_error_type
)
# unit tests passed
"

# Полный запуск (медленно)
PYTHONPATH=. python work/MAS_errors/parsers/nebius/code_execution/parser.py
```

---

## Связанные документы

- `work/specs/TZ_10.md` — спецификация
- `work/reports/TZ_2_v2_report.md` — документация по invalid_invocation