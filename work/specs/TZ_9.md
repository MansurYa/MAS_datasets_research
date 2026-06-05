# TZ_9. Спецификация: Claude Code Usage — KV Cache Loss

**Дата:** 2026-06-05
**Статус:** Завершено

---

## 1. Контекст

Исследование KV cache loss (утрата кеша на GPU) на основе анонимизированного датасета API-логов Claude Code.

### Источник данных

`datasets/claude_code_usage_kv_cache_loss.csv`
- 7561 запрос
- 86 сессий (интервал > 30 минут)
- Столбцы: Time, Input Tokens, Output Tokens, Cache Read Tokens, Cache Creation Tokens
- Временной диапазон: ~35 дней (февраль-апрель 2026)

### Особенность

TZ_9 **не имеет разделения на траектории** — сессии выделяются из данных самостоятельно.

---

## 2. Определения

### 2.1. Сессия (trajectory)

Интервал между запросами > **30 минут (1800 секунд)** = новая сессия.
Каждый запрос принадлежит одной сессии, сессии нумеруются от 0.

### 2.2. Тёплые vs холодные сессии

**Тёплая сессия:** хотя бы один запрос имеет Cache Read Tokens > 0.
**Холодная сессия:** все запросы имеют Cache Read Tokens = 0.

Холодные сессии (18 штук, 849 запросов) не используют cache — для них cache_loss не применим.
Статистика считается только для тёплых сессий.

### 2.3. KV Cache Loss (ошибка)

Событие, при котором GPU сбрасывает KV cache из-за вытеснения.

**Критерии:**
1. Интервал с предыдущего запроса > 30 минут
2. Cache Read Tokens = 0 (нет попаданий в кеш)
3. Предыдущий шаг в сессии имел Cache Read Tokens > 100

**Обоснование:** Если до перерыва модель активно использовала кеш (>100 токенов чтения), значит кеш был горячим. После перерыва кеш = 0 указывает на вытеснение.

---

## 3. Статистика

| Метрика | Значение |
|---------|----------|
| Сессий (всего) | 86 |
| Тёплых сессий (используют cache) | 68 |
| Запросов в тёплых сессиях | 6712 |
| KV cache loss событий | 23 |
| P(loss | request) | 0.34% |
| P(loss | after_gap, тёплые сессии) | 34.3% |

### P(loss | after_gap) — ключевой показатель

Из 67 запросов после перерыва в тёплых сессиях — 23 вызвали KV cache loss.
34.3% — вероятность потери cache после 30-минутного перерыва в сессиях, которые используют cache.

---

## 4. Архитектура парсера

### Структура файлов

```
work/MAS_errors/parsers/
  claude_code_usage/
    __init__.py
    parser.py
    run_all.py
    tests/
      test_parser.py
    kv_cache_loss/
      errors.parquet
      stats.json
```

### parser.py — функции

| Функция | Описание |
|---------|----------|
| `load_and_process_csv()` | Загрузка CSV, добавление time_diff, cache_hit_ratio |
| `assign_sessions()` | Определение сессий по time_diff > 1800 сек |
| `detect_kv_cache_loss()` | Определение событий по критериям выше |
| `build_records()` | Создание DataFrame для parquet |
| `compute_stats()` | Вычисление статистики (только тёплые сессии) |

### Выходной parquet

| Поле | Описание |
|------|----------|
| traj_idx | Номер сессии (0-85) |
| step_idx | Номер шага в сессии |
| chars_before_error | time_diff (секунды с предыдущего) |
| cache_read_tokens | Cache Read Tokens |
| cache_creation_tokens | Cache Creation Tokens |
| input_tokens | Input Tokens |
| output_tokens | Output Tokens |
| cache_loss | 0/1 — событие KV cache loss |
| cache_hit_ratio | Cache Read / Input Tokens (0-1) |
| time_diff | Секунды с предыдущего запроса |
| request_time | Время запроса (строка) |
| step_in_session | Номер шага в сессии |

### stats.json

```json
{
  "dataset": "claude_code_usage",
  "error_type": "kv_cache_loss",
  "n_total_requests": 6712,
  "n_sessions": 68,
  "n_kv_cache_loss_events": 23,
  "p_loss_per_request": 0.0034,
  "p_loss_per_session_after_gap": 0.3433,
  "parser_version": "TZ_9.1"
}
```

---

## 5. Интеграция в study_runner

В `work/MAS_errors/study_runner/generate_study_list.py`:

```python
ANALYSIS_VAR_MAP = {
    # ...
    "claude_code_usage": ["time_diff", "cache_hit_ratio", "cache_read_tokens"],
}
```

**Автоматически генерируемые исследования:**

| Study ID | Analysis Var | Описание |
|----------|--------------|----------|
| claude_code_usage_claude_code_usage_kv_cache_loss_all_time_diff | time_diff | Распределение интервалов |
| claude_code_usage_claude_code_usage_kv_cache_loss_all_cache_hit_ratio | cache_hit_ratio | Cache hit ratio |
| claude_code_usage_claude_code_usage_kv_cache_loss_all_cache_read_tokens | cache_read_tokens | Объём чтения из кеша |

---

## 6. Верификация

```bash
# Запуск парсера
PYTHONPATH=. python work/MAS_errors/parsers/claude_code_usage/parser.py

# Проверка выходов
ls -la work/MAS_errors/parsers/claude_code_usage/kv_cache_loss/

# Проверка study_runner
PYTHONPATH=. python -c "
from work.MAS_errors.study_runner.generate_study_list import scan_parsers_output
studies = scan_parsers_output()
cc_usage = [s for s in studies if s.dataset == 'claude_code_usage']
print(f'Claude Code Usage studies: {len(cc_usage)}')
"
```

---

## 7. Результаты

```
Тёплых сессий: 68
Запросов: 6712
KV cache loss событий: 23
P(loss|request): 0.0034
P(loss|after_gap): 0.3433
```

Парсер работает корректно. Статистика считается только для тёплых сессий.

---

## 8. Документация

- `work/docs/kv_cache_loss_concept.md` — концепция KV cache loss
- `work/docs/claude_code_usage_dataset.md` — описание датасета