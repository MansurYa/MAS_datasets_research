# TZ_5: Data Integrity Check — Отчёт

**Дата:** 2026-05-29
**Статус:** завершён

## Цель

Проверить целостность данных в `work/data/errors_invalid_invocation.json` — аккумуляторы контекста и индексация траекторий.

## Инварианты

| # | Инвариант | Проверка |
|---|-----------|----------|
| [1] | Все обязательные ключи присутствуют | `global_traj_idx`, `local_traj_idx`, `chars_up_to_error`, `ai_steps_up_to_error` |
| [2] | Монотонность аккумуляторов | `chars_up_to_error` и `ai_steps_up_to_error` не убывают внутри траектории |
| [3] | Границы индексов | `global_traj_idx ∈ [0, 80035]`, `local_traj_idx ≥ 0` |
| [4] | Монотонность `local_traj_idx` | строго возрастает при смене траектории, неизменна внутри траектории |

## Результат

```
============================================================
TZ_5: Data Integrity Check
============================================================

  A:   31 193 записей
  B:   69 023 записей
  E1: 133 088 записей
  E2:  84 045 записей

[1] Проверка ключей...                         PASS
[2] Проверка монотонности аккумуляторов...      PASS (317 349 пар проверено)
[3] Проверка границ индексов...                PASS
[4] Проверка сброса local_traj_idx...           PASS (10 993 instance_id проверено)

============================================================
  ✓ ВСЕ ИНВАРИАНТЫ СОБЛЮДЕНЫ
============================================================
```

## Обнаруженные проблемы и исправления

### Проблема 1: Сброс счётчика между шардами parquet

**Симптом:** 337 828 нарушений инварианта [4] при первой проверке.

**Причина:** Паркет разбит на 12 шардов. Подход с `local_counters[inst]++` в однопроходном цикле даёт неправильный результат — счётчик не сбрасывается между шардами, но формула не учитывает позицию первого вхождения.

**Исправление:** Two-pass подход:
```python
# Pass 1: фиксируем first_occurrence[inst]
first_occurrence = {}
for row_idx, inst in enumerate(instance_ids):
    if inst not in first_occurrence:
        first_occurrence[inst] = row_idx

# Pass 2: вычисляем local по формуле
local_traj_idx = global_traj_idx - first_occurrence[inst]
```

### Проблема 2: Мультиошибки на одном шаге

**Симптом:** 2 нарушения дублирования:
- `PyCQA__pyflakes-668`, local=22, step=2: E999 «unexpected indent» + E999 «unexpected unindent»
- `pydantic__pydantic-2618`, local=7, step=24: E999 IndentationError + E999 SyntaxError

**Причина:** `normalize_error_pattern` убирает аргумент после `:`, поэтому «unexpected indent» и «unexpected unindent» дают одинаковый паттерн `IndentationError: unexpected X`. Верификатор считал их дубликатами.

**Исправления:**
1. В парсере (`nebius_all_errors.py`): добавлен `error_type` в ключ дедупликации
   ```python
   error_type = m.split(':')[0]
   key = (c, error_type, normalize_error_pattern(m))
   ```
2. В верификаторе (`verify_tz5.py`): ключ для E1/E2 расширен
   ```python
   key = (local, step, error_type, normalized_pattern)
   ```

## Итоговые данные

| Категория | Записей |
|-----------|---------|
| A (FileNotFoundError) | 31 193 |
| B (bash command not found) | 69 023 |
| E1 (edit tool syntax error E999) | 133 088 |
| E2 (edit tool undefined name F821) | 84 045 |
| **Итого** | **317 349** |

Файл: `work/data/errors_invalid_invocation.json` (381 MB)

## Файлы

- `work/scripts/verify_tz5.py` — скрипт верификации (4 инварианта)
- `work/scripts/nebius_all_errors.py` — парсер (обновлён с error_type)
- `work/data/errors_invalid_invocation.json` — проверенные данные