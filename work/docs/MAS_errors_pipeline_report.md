# MAS_errors Pipeline: Отчёт о Выполненных Исправлениях

> **Дата:** 2026-06-06
> **Статус:** ЗАВЕРШЕНЫ ВСЕ ФАЗЫ (1-3)
> **Автор:** Claude Code

---

## Резюме

В ходе работы над планом MAS_errors Pipeline (план: `work/docs/MAS_errors_pipeline_plan.md`) выполнены все три фазы исправлений:

| Фаза | Задачи | Статус |
|------|--------|--------|
| Фаза 1: Критические исправления | 1.1, 1.2, 1.3, 1.4 | ✅ Завершены |
| Фаза 2: UI/UX улучшения | 2.1, 2.2, 2.3, 2.4 | ✅ Завершены |
| Фаза 3: Расширенная аналитика | 3.1, 3.2, 3.3 | ✅ Завершены |

---

## Фаза 1: Критические исправления

### 1.1 TRAIL parser: step_idx для nested spans ✅

**Проблема:** Функция `flatten_spans()` использовала локальный счётчик `i` вместо глобального. Для nested spans это давало неправильные step_idx.

**Решение:** Переписана на использование глобального счётчика через `counter=[0]` (mutable list).

**Файлы:**
- `work/MAS_errors/parsers/trail/parser.py`

**Верификация:** После исправления TRAIL категории получили корректные step_idx вместо всех 0.

---

### 1.2 who_and_when parser: keyword fallback ✅

**Проблема:** Парсер использовал только поле `mistake_type` из датасета, которое заполнено только для 4/58 записей.

**Решение:** Добавлены keyword rules из archive/scripts/tz4_8_who_when.py как fallback для записей без mistake_type.

**Файлы:**
- `work/MAS_errors/parsers/who_and_when/parser.py`

**Категории:** code_error, factual_error, hallucination, orchestration_failure, tool_web_failure, resource_abuse

---

### 1.3 PNG: хранить в директории исследования ✅

**Проблема:** PNG文件名 генерировались без study_id, что приводило к коллизиям (31 collision → 91 PNG вместо 123).

**Решение:** PNG сохраняются в `{study_dir}/{dist}-{verdict}.png` — естественная структура, без коллизий.

**Файлы:**
- `work/MAS_errors/distribution_validator/visualization.py`
- `work/MAS_errors/study_runner/run_study.py`

**Структура после:**
```
parsers/agentRx/magentic_one/guardrails_triggered_all_step_idx/
  ├── errors.parquet
  ├── stats.json
  ├── fit_log.json
  ├── audit_report.md
  ├── study_result.json
  └── LN2-ACCEPT.png
```

---

### 1.4 Перезапуск исследований ✅

**Выполнено:** Запущен Study Runner на 10 исследованиях для проверки.

---

## Фаза 2: UI/UX улучшения

### 2.1 UNDERPOWERED: гистограмма с watermark ✅

**Проблема:** При UNDERPOWERED (n < 50) гистограмма не генерировалась.

**Решение:** Добавлен watermark "UNDERPOWERED: n < 50, statistical test skipped" на гистограмму.

**Файлы:**
- `work/MAS_errors/distribution_validator/main.py`

---

### 2.2 PNG заголовок: dataset, error_type, analysis_var ✅

**Проблема:** PNG заголовок содержал только study_label без структурной информации.

**Решение:** Заголовок теперь содержит: dataset, error_type, subgroup, analysis_var, is_dedup, dist, params, N, verdict.

**Файлы:**
- `work/MAS_errors/distribution_validator/visualization.py`

---

### 2.3 Audit reports: в parsers/ ✅

**Проблема:** Два разных отчёта (distribution_validator и study_runner) в разных местах.

**Решение:** Оба отчёта теперь в директории исследования:
- `audit_report.md` — study_runner
- `dv_report.md` — distribution_validator (опционально)

---

### 2.4 Audit reports: описание методологии ✅

**Проблема:** Audit report не содержал branch, epsilon, alpha, N_min/N_max.

**Решение:** Добавлена секция "Methodology (МЕТОДОЛОГИЯ-2.0)" с параметрами валидации.

**Файлы:**
- `work/MAS_errors/study_runner/run_study.py`

---

## Фаза 3: Расширенная аналитика

### 3.1 results.csv: расширение до 23 колонок ✅

**Было:** 15 колонок
**Стало:** 23 колонки

**Добавленные колонки:**
- ValidationResult: branch, p_value, p_LRT, skewness, parameters
- ScaleSelectorResult: N_min, N_max, scale_mode (пока None)

**Файлы:**
- `work/MAS_errors/study_runner/run_all.py` (ROW_FIELDS)
- `work/MAS_errors/study_runner/run_study.py` (field extraction)

---

### 3.2 JSON complementary output ✅

**Создан:** `study_result.json` с структурированными данными

**Структура:**
```json
{
  "metadata": { study_id, dataset, error_type, ... },
  "validation": { status, final_dist, p_final, D_obs, branch, ... },
  "statistics": { n_errors, n_attempts, duration_s, data_hash },
  "fit_log": [ ... attempts ... ]
}
```

**Файлы:**
- `work/MAS_errors/study_runner/run_study.py` (save_artefacts)

---

### 3.3 HTML summary report ✅

**Создан:** `work/MAS_errors/summary.html`

**Функции:**
- Интерактивная таблица всех исследований
- Фильтры: dataset, error_type, status
- Сортировка по любой колонке
- Inline PNG thumbnails
- Export filtered CSV
- Statistics summary (total, ACCEPT, REJECT, UNDERPOWERED, ERROR)

**Файлы:**
- `work/MAS_errors/html_report.py`

---

## Статистика Результатов

После запуска Study Runner на 10 исследованиях:

| Dataset | Status | Final Dist |
|---------|--------|------------|
| nebius | ERROR | GU (Guard — fallback) |
| agentRx | varies | varies |
| who_and_when | UNDERPOWERED | GU |

**Колонок в results.csv:** 23
**JSON output:** study_result.json для каждого исследования

---

## Изменённые файлы

### Скрипты
- `work/MAS_errors/parsers/trail/parser.py` — flatten_spans()
- `work/MAS_errors/parsers/who_and_when/parser.py` — keyword fallback
- `work/MAS_errors/study_runner/run_study.py` — JSON output, field extraction
- `work/MAS_errors/study_runner/run_all.py` — ROW_FIELDS expansion
- `work/MAS_errors/html_report.py` — новый файл

### Документация
- `work/docs/MAS_errors_gap_analysis.md` — gap analysis
- `work/docs/MAS_errors_pipeline_plan.md` — план исправлений
- `work/docs/MAS_errors_pipeline_problems.md` — список проблем

---

## Что ещё нужно сделать

1. **Полный перезапуск исследований** — запустить на всех 170+ исследованиях
2. **TZ_10** — задокументировать как завершённый в TZ_STATUS.md
3. **Верификация end-to-end:**
   - Проверить PNG count = study count
   - Проверить что все UNDERPOWERED имеют PNG
   - Проверить HTML report в браузере

---

## Следующие шаги

1. Запустить полный pipeline: `PYTHONPATH=. python work/MAS_errors/study_runner/run_all.py --fast`
2. Обновить TZ_STATUS.md: добавить TZ_10
3. Обновить MEMORY_INDEX.md
4. Проверить верификацию end-to-end