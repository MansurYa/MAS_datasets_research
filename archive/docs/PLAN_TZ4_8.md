# План ТЗ №4.8

## Контекст: что исправляется

Два источника данных были обработаны неправильно:
1. **TRAIL** — ошибочно исключён (нужно вернуть)
2. **Who&When** — использовались все 184 записи вместо 58 Hand-Crafted

Критический баг: `resource_abuse` для Who&When HC показывает n=1 вместо 5.
- Причина: HC parquet обновлён, keyword matching даёт другие результаты
- Решение: использовать оригинальную классификацию из `errors_classified.csv` (фильтровать по HC IDs)

---

## Часть A. Извлечение TRAIL

**A1. Изучить структуру TRAIL**
- Файлы: `processed_annotations_gaia/*.json`, `processed_annotations_swe_bench/*.json`
- Поля в JSON: `errors[].category`, `errors[].location`, `errors[].impact`
- Span mapping: рекурсивно обойти `spans[]` → `span_id: step_number`
- Benchmark: GAIA или SWE-bench определяется по подпапке

**A2. Извлечь ошибки** (tz4_8_trail_extract.py)
- Для каждого `.json` в аннотациях: загрузить, получить span_map,提取 errors
- TRAIL category → наш error_id (по маппингу из ТЗ)
- trajectory_length = len(span_map)
- normalized_position = step / trajectory_length
- Сохранить `data/trail_errors.csv`

**A3. Проверить результат**
- Число траекторий: ~143 (GAIA + SWE-bench)
- Число ошибок: 816 (TRAIL имеет много ошибок на траекторию)
- Неизвестные категории: проверить какие не маппятся

---

## Часть B. Чистка Who&When

**B1. Загрузить Hand-Crafted** (58 записей)
- `Kevin355-Who_and_When/Hand-Crafted.parquet`

**B2. Классификация**
- Использовать `classify_text()` из `tz2_unify_classify.py` (те же keyword rules)
- Сохранить `data/who_and_when_handcrafted_classified.csv`

**B3. БАГ-ФИКС: Использовать оригинальную классификацию**
- Оригинальный `errors_classified.csv` имел классификацию всех 184 записей
- После фильтрации по HC IDs (58 trajectories): 103 rows, 5 resource_abuse
- Эти 103 rows из errors_classified.csv = правильная классификация
- Перезаписать `who_and_when_handcrafted_classified.csv` данными из errors_classified.csv (фильтрованными по HC IDs)
- Структура: source, trajectory_id, category_unified, category_original, step_number, text_snippet

**B4. Проверить результат**
- Total: 103 rows, 58 unique trajectories
- resource_abuse: 5 trajectories
- Не должно быть колонки trajectory_length (она была добавлена в tz4_8_who_when.py, но не нужна)

---

## Часть C. Полный пересчёт статистики

**C1. TRAIL stats** (tz4_8_stats.py)
- n_total_traj = 143
- total_steps = sum of all trajectory lengths (или лучше: unique trajectory lengths)
- Для каждого error_id: P(traj), P(msg), Wilson CI, step stats
- Гистограммы: абсолютные + нормализованные (n >= 20)
- Подгонка 8 распределений (n >= 20)

**C2. AgentRx stats** (без изменений — уже корректно)
- magentic_one: 44 trajectories
- tau_retail: 29 trajectories

**C3. Who&When HC stats** (ИСПРАВЛЕНО)
- n_total_traj = 58
- total_steps = сумма длин всех 58 траекторий
  - Извлечь из `history` полей HC parquet
  - Или: подсчитать из errors_classified filtered
- Использовать 103 rows из errors_classified (фильтрованных по HC IDs)
- P(traj) = n_trajectories_with_error / 58
- P(msg) = n_occurrences / total_steps

**C4. Keyword search** (без изменений)

**C5. Сохранить**
- `data/stats_full_v2.csv` — TRAIL + AgentRx + Who&When HC
- `data/distributions_v2.csv` — подгонки распределений

---

## Часть D. Финальная таблица + отчёт

**D1. all_errors_final.csv** (tz4_8_final.py)
- Объединить: stats_full_v2.csv + keyword_stats_full.csv
- Добавить: name_ru, description_ru, modeling_class, DATA_QUALITY
- TRAIL → data_quality = "high"
- AgentRx → "medium"
- Who&When HC → "medium"
- Keyword search → "high"

**D2. docs/tz4_8_report.md**
- Секция 1: что исправлено (таблица было/стало)
- Секция 2: TRAIL категории с частотами
- Секция 3: Who&When HC классификация (58 HC, resource_abuse = 5)
- Секция 4: обновлённая статистика P(traj), P(msg), Wilson CI
- Секция 5: распределения для n >= 20
- Секция 6: финальная сводная таблица

---

## Скрипты для запуска

1. **tz4_8_trail_extract.py** — извлечь TRAIL
2. **tz4_8_stats.py** (исправленный) — пересчитать статистику
3. **tz4_8_final.py** — финальная таблица
4. **tz4_8_report.py** (новый) — отчёт

---

## Ожидаемые результаты

| error_id | source | n_traj | n_total | P(traj) |
|---|---|---|---|---|
| kv_cache_loss | trail | ~15 | 143 | ~0.10 |
| resource_abuse | trail | ~45 | 143 | ~0.31 |
| resource_abuse | who_and_when_hc | **5** | 58 | ~0.086 |
| tool_web_failure | who_and_when_hc | 24 | 58 | ~0.41 |
| orchestration_failure | who_and_when_hc | 16 | 58 | ~0.28 |
| ... | ... | ... | ... | ... |

---

## Ключевые файлы

- `data/trail_errors.csv` — TRAIL ошибки
- `data/who_and_when_handcrafted_classified.csv` — 103 rows (фильтр из errors_classified.csv)
- `data/stats_full_v2.csv` — статистика всех источников
- `data/distributions_v2.csv` — подгонки распределений
- `data/all_errors_final.csv` — финальная таблица
- `docs/tz4_8_report.md` — отчёт

---

## Известные ограничения

- TRAIL: категория "unknown" не маппится (нужно проверить какие именно)
- Who&When HC: 41% записей остаются "unclassified" (keyword matching недостаточно)
- p_message для Who&When HC: total_steps может быть неточным (нужно проверить как извлекать)
