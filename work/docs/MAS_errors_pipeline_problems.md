# MAS_errors Pipeline: Проблемы и Пути Решения

> **Дата:** 2026-06-06
> **Статус:** ИСПРАВЛЕНО (Проблема 0 решена)
> **Основание:** Пользователь запросил документирование до имплементации

---

## Проблема 0 (ИСПРАВЛЕНО): TRAIL Parser не извлекал step_idx

### Описание
TRAIL parser (`work/MAS_errors/parsers/trail/parser.py`, строка 89) жестко задавал `step_idx=0` для ВСЕХ записей. Это приводило к:

### Последствия (до исправления)
1. **data_hash коллизии:** 52 из 183 исследований (28%) имели одинаковый хеш из-за идентичных данных
2. **Бессмысленные UNDERPOWERED вердикты:** При step_idx=0 для всех записей, анализ не имел статистического смысла
3. **Искажение baseline:** TRAIL записи составляли ~25% от общего числа ошибок в системе

### Исправление (2026-06-06)
Добавлена функция `flatten_spans()` для создания маппинга `span_id → step_idx`:

```python
def flatten_spans(spans, step_idx_start=0):
    """Recursively flatten spans including nested child_spans.

    Returns list of (step_idx, span_id) tuples in depth-first order.
    """
    flat = []
    for i, span in enumerate(spans):
        flat.append((step_idx_start + i, span.get("span_id")))
        if "child_spans" in span and span["child_spans"]:
            child_flat = flatten_spans(span["child_spans"], step_idx_start + len(spans))
            flat.extend(child_flat)
    return flat
```

В цикле по errors теперь:
```python
flat_spans = flatten_spans(trace.get("spans", []) if isinstance(trace, dict) else [])
span_id_to_step = {span_id: idx for idx, span_id in flat_spans}
...
step_idx = span_id_to_step.get(err.get("location"), 0)
```

### Результат
- **До:** step_idx range = 0-0, unique = 1
- **После:** step_idx range = 7-46, unique = 18-28 (зависит от категории)

### Следующие шаги
1. Перезапустить TRAIL-исследования
2. Проверить исчезновение коллизий через data_hash

---

## Проблема 1: Миграция ошибок из TRAIL/archive неполная

### Описание
- В `archive/data/errors_stats.csv` — **47 строк** (45 уникальных комбинаций ошибок)
- В `work/MAS_errors/results.csv` — **183 исследования**, но многие типы ошибок отсутствуют
- Количество исследований выросло за счёт дублей (коллизий), а не новых типов

### Корневая причина
TRAIL parser не извлекает данные корректно → часть исследований не генерируется

### Путь решения
1. Сравнить список error_type × error_subtype из archive с текущим results.csv
2. Определить недостающие комбинации
3. Зафиксить TRAIL parser (Проблема 0)
4. Запустить заново исследования для недостающих типов

---

## Проблема 2: UNDERPOWERED исследования не генерируют гистограммы

### Описание
Правило "один study = один график" нарушено. UNDERPOWERED исследования:
- Имеют статус UNDERPOWERED (недостаточно данных для KS-теста)
- НЕ генерируют PNG с гистограммой
- Пользователь не может визуально оценить данные

### Пример
```
agentRx_magentic_one_guardrails_triggered_all_step_idx:
- Status: UNDERPOWERED
- Best Distribution: GU
- Errors: 24, Attempts: 9
- PNG: НЕТ
```

### Путь решения
**Вариант A (рекомендуется):** Всегда генерировать гистограмму, добавлять watermark "UNDERPOWERED: insufficient data for statistical test"

**Вариант B:** В audit_report.md добавить ссылку на данные (n_errors, range), чтобы пользователь мог сам оценить

---

## Проблема 3: results.csv слишком мало информации

### Описание
Текущий `work/MAS_errors/results.csv` содержит:
- study_id, status, best_dist, p_value, D_statistic, errors, attempts, duration

Оригинальный `archive/data/errors_stats.csv` содержал:
- Все поля выше +
- error_type, error_subtype, dataset, analysis_variable, de_duplicated
- Статистика по каждому error_type (count, mean, std, min, max)

### Корневая причина
При миграции на новую архитектуру (StudyRunner) расширенная статистика была утеряна

### Путь решения
**Вариант A:** Добавить расширенные поля в results.csv:
- dataset, error_type, error_subtype, analysis_variable, de_duplicated
- percentiles (p25, p50, p75, p90, p95, p99)
- distribution_params (params для каждой попытки)

**Вариант B:** Создать дополнительный файл `study_metadata.csv` с расширенной информацией

---

## Проблема 4: Нет минимального чека для забытых ошибок

### Описание
Пользователь не имеет автоматического способа проверить:
- Какие типы ошибок из archive/data/errors_stats.csv ещё не мигрированы
- Какие исследования содержат данные, но не прошли fit pipeline

### Путь решения
Создать скрипт `check_migration_coverage.py`:
```python
# Входные данные:
# - archive/data/errors_stats.csv (reference)
# - work/MAS_errors/results.csv (current)

# Алгоритм:
# 1. Извлечь все уникальные (dataset, error_type, error_subtype) из archive
# 2. Извлечь все уникальные (dataset, error_type, error_subtype) из current
# 3. Вычислить: missing = archive - current
# 4. Вывести отчёт: какие типы ещё не мигрированы
```

---

## Проблема 5: PNG файлы без контекста

### Описание
Текущие PNG имеют заголовок (например "agentRx_magentic_one_guardrails_triggered_all_step_idx"), но не объясняют:
- Какой это датасет
- Какой тип ошибки
- Какая аналитическая переменная (step_idx vs chars_before_error)
- Был ли de-duplicated

### Путь решения
Включить в заголовок PNG полную информацию:
```
agentRx / magentic_one / guardrails_triggered
Variable: step_idx | Dedup: No
Status: ACCEPT | Distribution: LL2
n_errors=24 | D=0.1134
```

---

## Проблема 6: Audit Reports неполные

### Описание
Текущий audit_report.md содержит:
- Status, Best Distribution, p-value, D-statistic
- Errors, Attempts, Duration
- Attempts Log

Отсутствует:
- Описание эксперимента (что измеряем)
- Dataset source
- Error type и subtype
- Методология (какой KS-тест, какие параметры)
- Аналитическая переменная (steps vs chars "before")

### Пример текущего audit_report.md
```markdown
# Audit Report: agentRx_magentic_one_guardrails_triggered_all_step_idx

**Status:** UNDERPOWERED
**Best Distribution:** GU
...
```

### Путь решения
Расширить шаблон audit_report.md:
```markdown
# Audit Report: {study_id}

## Metadata
- **Dataset:** agentRx
- **Error Type:** magentic_one
- **Error Subtype:** guardrails_triggered
- **Analysis Variable:** step_idx
- **De-duplicated:** False
- **Methodology:** Fit_Everything v2.0 (KS-test, bootstrap, 9 distributions)

## Results
- **Status:** UNDERPOWERED
- **Best Distribution:** GU
- **p-value:** N/A (insufficient data)
- **D-statistic:** 0.0000
- **Errors:** 24
- **Attempts:** 9
- **Duration:** 0.0s

## Data Summary
- Min: {min}, Max: {max}
- Mean: {mean}, Std: {std}
- Percentiles: p25={p25}, p50={p50}, p75={p75}

## Attempts Log
...
```

---

## Сводная таблица

| # | Проблема | Критичность | Путь решения | Приоритет |
|---|----------|-------------|--------------|-----------|
| 0 | TRAIL parser step_idx=0 | **КРИТИЧЕСКИЙ** | Исправить parser.py | 1 |
| 1 | Неполная миграция TRAIL | Высокая | Фикс 0 + перезапуск | 2 |
| 2 | UNDERPOWERED без гистограмм | Средняя | Всегда генерировать PNG | 3 |
| 3 | results.csv мало полей | Средняя | Добавить metadata | 4 |
| 4 | Нет чека миграции | Средняя | Скрипт check_coverage | 5 |
| 5 | PNG без контекста | Низкая | Расширить заголовок | 6 |
| 6 | Audit reports неполные | Низкая | Расширить шаблон | 7 |

---

## Предлагаемый порядок работ

### Фаза 1: Критический фикс
1. Исправить TRAIL parser (Проблема 0)
2. Перезапустить все TRAIL-исследования
3. Проверить исчезновение коллизий

### Фаза 2: Миграция
4. Создать check_migration_coverage.py (Проблема 4)
5. Запустить, определить недостающие типы
6. Доработать парсеры для недостающих типов

### Фаза 3: UI/UX улучшения
7. Все UNDERPOWERED генерируют гистограммы (Проблема 2)
8. Расширить audit_report.md (Проблема 6)
9. Расширить заголовки PNG (Проблема 5)

### Фаза 4: Расширенная аналитика
10. Добавить metadata в results.csv (Проблема 3)
11. Добавить percentile-статистику

---

## Ресурсы для решения

### Архивные данные (reference)
- `archive/data/errors_stats.csv` — 47 строк типизированных ошибок
- `archive/data/plots/` — PNG файлы для сравнения
- `archive/docs/fault_analysis_report.md` — полный анализ

### Текущие данные (для миграции)
- `work/MAS_errors/results.csv` — 183 исследования
- `work/MAS_errors/parsers/` — парсеры для всех датасетов
- `work/MAS_errors/schemas.py` — схемы данных

### Ключевые файлы для понимания
- `work/MAS_errors/study_runner/run_study.py` — генерация fit_log.json и audit_report.md
- `work/MAS_errors/utils.py` — data_hash() функция
- `memory/project_code_execution_parser.md` — документация по парсерам