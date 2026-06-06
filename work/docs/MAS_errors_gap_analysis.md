# MAS_errors Pipeline: Анализ Расхождений

> **Дата:** 2026-06-06
> **Тип:** Gap Analysis (не план имплементации)
> **Цель:** Задокументировать ЧТО ХОЧЕТСЯ vs ЧТО ИМЕЕТСЯ

---

## Обзор Источников Данных

### Архив (reference)
- `archive/data/errors_stats.csv` — **46 типизированных ошибок**
- Источники: trail, magentic_one, tau_retail, who_and_when_hc, keyword_search_nebius, keyword_search_itbench, keyword_search_terminalbench, теоретическая

### Текущий пайплайн
- `work/MAS_errors/results.csv` — **183 исследования**
- Datasets: agentRx (magentic_one, tau_retail), nebius (code_execution, invalid_invocation), who_and_when, trail, claude_code_usage

---

## G1: Покрытие Типов Ошибок

### TRAIL — наибольший разрыв

**В archive (trail):**
```
code_error, hallucination, instruction_adherence_failure, invalid_invocation,
kv_cache_loss, misinterpretation_of_tool_output, orchestration_failure,
resource_abuse, resource_not_found, system_failure, tool_timeout, tool_web_failure
```

**В текущем пайплайне (trail categories из parsers/):**
```
authentication_errors, context_handling_failures, environment_setup_errors,
formatting_errors, goal_deviation, incorrect_problem_identification,
instruction_noncompliance, language_only, poor_information_retrieval,
resource_abuse*, resource_exhaustion, resource_not_found*, service_errors,
task_orchestration, task_orchestration_errors, timeout_issues,
tool_definition_issues, tool_related, tool_selection, tool_selection_errors
```
*совпадают с archive

**Отсутствуют в текущем (из archive):**
- `code_error` — 74 траектории в archive, есть в who_and_when_hc, НЕТ в TRAIL
- `hallucination` — 83 траектории, НЕТ
- `instruction_adherence_failure` — 77 траекторий, НЕТ (но есть `instruction_noncompliance` — возможно маппинг?)
- `invalid_invocation` — 10 траекторий, НЕТ
- `kv_cache_loss` — 44 траектории, НЕТ
- `misinterpretation_of_tool_output` — 40 траекторий, НЕТ
- `orchestration_failure` — 92 траектории, НЕТ (но есть `task_orchestration` — возможно маппинг?)
- `system_failure` — 2 траектории, НЕТ
- `tool_timeout` — 2 траектории, НЕТ
- `tool_web_failure` — 5 траекторий, НЕТ

**Причина:** TRAIL парсер извлекает категории из поля `category` в аннотациях. Эти категории НЕ совпадают с именами из archive. Парсер правильно читает TRAIL датасет, но имена категорий в TRAIL другие (например, "Language-only" → `language_only`, "Task Orchestration" → `task_orchestration`).

### MAGENTIC_ONE — почти полное покрытие

**В archive:** guardrails_triggered ✅, instruction_adherence_failure ✅, intent_not_supported ✅, intent_plan_misalignment ✅, **invalid_invocation ❌**, invention_of_new_information ✅, misinterpretation_of_tool_output ✅, system_failure ✅

**Отсутствует:** `invalid_invocation` (1 траектория в archive)

### TAU_RETAIL — частичное покрытие

**В archive:** instruction_adherence_failure ✅, intent_not_supported ✅, intent_plan_misalignment ✅, **invalid_invocation ❌**, misinterpretation_of_tool_output ✅, system_failure ✅, **underspecified_user_intent ❌**

**Отсутствует:** `invalid_invocation` (2 траектории), `underspecified_user_intent` (10 траекторий)

### WHO_AND_WHEN — ПОЛНОСТЬЮ ОТСУТСТВУЕТ

**В archive (who_and_when_hc):** code_error, factual_error, hallucination, orchestration_failure, resource_abuse, tool_web_failure

**В текущем пайплайне:** парсер `who_and_when` генерирует categories: `processing_error`, `tool_failure`, `wrong_reasoning`

**Проблема:** Имена категорий НЕ совпадают. Парсер не использует архивные имена. Аннотации who_and_when_hc извлекаются некорректно или не извлекаются вообще.

### NEBIIUS — новые типы без архива

**В archive:** tool_web_failure (26379 вхождений), resource_not_found (33565 вхождений)

**В текущем:** `code_execution`, `invalid_invocation` — этих типов нет в archive

### TERMINALBENCH и ITBENCH — отсутствуют полностью

- `keyword_search_terminalbench`: permission_error (267), memory_error (1750) — НЕТ
- `keyword_search_itbench`: tool_timeout (80) — НЕТ

### Итого по покрытию

| Источник | В archive | В current | Покрытие |
|----------|-----------|-----------|----------|
| trail | 12 типов | 20 типов (другие имена) | ~60% семантически |
| magentic_one | 8 типов | 7 типов | 87.5% |
| tau_retail | 7 типов | 5 типов | 71.4% |
| who_and_when_hc | 6 типов | 0 типов | **0%** |
| nebius keyword | 2 типа | 0 типов (новые типы) | 0% |
| terminalbench | 2 типа | 0 типов | 0% |
| itbench | 1 тип | 0 типов | 0% |

---

## G2: Правило "Одно Исследование = Один График"

### Ожидание
Каждое исследование (study) генерирует ровно один PNG.

### Реальность

**UNDERPOWERED (n < 50): PNG не генерируется**
- Порог: `select.py:226` — `if n < 50: mode = MODE_UNDERPOWERED`
- При UNDERPOWERED: `main.py:94` возвращает `ValidationResult(verdict="UNDERPOWERED")` ДО вызова `plot_fit()`
- Из 183 исследований: 60 UNDERPOWERED → 60 исследований БЕЗ PNG

**PNG collision: одно имя на несколько исследований**
- `visualization.py:191`: `audit_id = f"audit-{dist_type}-N{n_test}-{verdict}"`
- Имя файла НЕ содержит `study_id`
- 123 исследования с графиком (ACCEPT + REJECT) → 92 уникальных ключа → **31 коллизия**
- Итог: 91 PNG на диске вместо 123

**Математика:**
```
183 studies
- 60 UNDERPOWERED (нет графика) = 123 с графиком
- 31 collision (перезапись)     = 92 уникальных
- 1 сбой plot_fit               = 91 на диске
```

### Две разные проблемы
1. **UNDERPOWERED без графика** — дизайн: при недостатке данных график не имеет смысла
2. **PNG collision** — баг: имена файлов не уникальны

---

## G3: Глубинная Причина Коллизий data_hash

### Ожидание
Каждый dataset × error_type × error_subtype × subgroup × analysis_var даёт уникальный data_hash.

### Реальность: Три уровня коллизий

**Уровень 1: TRAIL step_idx=0 (ИСПРАВЛЕН)**
- TRAIL parser до исправления ставил `step_idx=0` для всех записей
- Все TRAIL категории с <50 ошибками давали `data_hash = SHA256([0.0, 0.0, ...])`
- Это приводило к коллизиям ВНУТРИ TRAIL

**Уровень 2: data_hash слишком "тонкий"**
```python
# run_study.py:174
data_hash = data_hash(df["step_idx"].values)
```
Хэшируется ТОЛЬКО массив значений анализируемой переменной. НЕ включаются:
- dataset
- error_type
- error_subtype
- subgroup
- analysis_var

**Пример коллизии (уже после исправления TRAIL):**
```
agentRx_magentic_one_system_failure (n=1, step_idx=[0])  → edf70214...
trail_trail_task_orchestration_errors (n=1, step_idx=[0]) → edf70214...
```
Это НЕ баг TRAIL. Оба имеют n=1, step_idx=0. Хэш идентичен по дизайну.

**Уровень 3: nebius dedup/non-dedup**
```
nebius_invalid_invocation_E2_dedup_limit_hit_chars_before_error → af7ebcd3...
nebius_invalid_invocation_E2_limit_hit_chars_before_error       → af7ebcd3...
```
dedup не меняет chars_before_error array → идентичный хэш. Это ожидаемо.

### Корневая причина
`data_hash` предназначен для traceability (воспроизводимость данных), но используется как quasi-уникальный идентификатор. Для уникальности нужен хэш от: `dataset + error_type + error_subtype + subgroup + analysis_var + values`.

### Реальные коллизии после исправления TRAIL
```
dbc736bcdf28... : trail_resource_exhaustion (n=2) + trail_timeout_issues (n=2)
edf70214d121... : agentRx_magentic_one_system_failure (n=1) + trail_task_orchestration_errors (n=1)
51b40f351662... : agentRx_magentic_one_guardrails_triggered (n=24) + dedup version
```
До исправления: 52 коллизии. После исправления: ~5-10 (ожидаемо меньше, но не 0).

---

## G4: Недостаток Информации в results.csv

### Ожидание
results.csv содержит всю существенную информацию об исследовании.

### Реальность

**Текущие колонки (15):**
```
study_id, dataset, error_type, error_subtype, is_dedup, subgroup,
analysis_var, n_errors, status, final_dist, p_final, D_obs,
n_attempts, duration_s, data_hash
```

**Архивные колонки (26, в archive/data/errors_stats.csv):**
```
error_id, name_ru, description_ru, source, modeling_class,
modeling_class_reason_ru, n_trajectories_with_error, n_trajectories_total,
p_trajectory, p_traj_ci_lower, p_traj_ci_upper, total_steps,
p_message, p_msg_ci_lower, p_msg_ci_upper, step_mean, step_median,
step_std, step_n, best_distribution, best_dist_params, best_dist_ks_p,
fit_conclusion_ru, data_quality_ru, insufficient_data, plots
```

**Отсутствуют в results.csv:**
- `description_ru` — русское описание ошибки
- `source` — источник (trail, magentic_one, etc.) — частично есть (dataset)
- `modeling_class` — категория 1-4
- `modeling_class_reason_ru` — почему моделируется/не моделируется
- `n_trajectories_total` — общее число траекторий
- `p_trajectory, p_traj_ci_lower, p_traj_ci_upper` — вероятность появления
- `total_steps` — всего шагов во всех траекториях
- `p_message, p_msg_ci_lower, p_msg_ci_upper` — вероятность на уровне шага
- `step_mean, step_median, step_std` — статистика по шагам (НЕТ в results.csv!)
- `best_dist_params` — параметры распределения
- `best_dist_ks_p` — p-value KS-теста
- `fit_conclusion_ru` — русский вердикт ("подгонка формально не отклонена")
- `data_quality_ru` — качество данных ("достаточно", "частично", "недостаточно")
- `insufficient_data` — флаг недостаточности
- `plots` — ссылки на графики

**Важно:** `step_mean`, `step_median`, `step_std` — это статистика по архивным данным, а не по текущему исследованию. Для текущего пайплайна нужны свои percentile-статистики (p25, p50, p75, p90, p95, p99).

**Наблюдение:** results.csv и errors_stats.csv — это РАЗНЫЕ файлы с РАЗНЫМИ целями. errors_stats.csv агрегирует данные из РАЗНЫХ источников в ЕДИНУЮ таблицу. results.csv описывает результаты независимых исследований. Нельзя просто "добавить все колонки" — нужно решить, какие метрики действительно нужны для simulator parameters.

---

## G5: PNG Без Контекста

### Ожидание
Заголовок PNG содержит: dataset, error_type, error_subtype, analysis_variable, status, distribution, n_errors, D-statistic.

### Реальность

**Текущий формат (visualization.py:182-186):**
```python
title = f"{study_label}\n{dist_full} [{params}] · N={n_test} · {verdict}"
```

**Что понятно из заголовка:**
- Название исследования (например, `agentRx_magentic_one_guardrails_triggered` — но это одно слово, непонятно где dataset, где error_type)
- Distribution type (LN2, W2, etc.)
- Parameters в скобках
- N (размер тестовой выборки)
- Verdict (ACCEPT/REJECT/UNDERPOWERED)

**Что НЕпонятно:**
- Какой dataset (agentRx vs nebius vs trail)
- Какой error_type (guardrails_triggered vs instruction_adherence_failure)
- Какая analysis_variable (step_idx vs chars_before_error vs cache_hit_ratio)
- Был ли de-duplicated
- Полный D-statistic
- data_hash

### Пример: что видит пользователь
```
agentRx_magentic_one_guardrails_triggered
LL2 [shape=0.8879, loc=0.0000, scale=28.1013] · N=24 · ACCEPT
```
Непонятно: Это dataset=agentRx? error_type=magentic_one? error_subtype=guardrails_triggered? analysis_var=step_idx? dedup=False?

---

## G6: Audit Reports Неполные

### Ожидание
audit_report.md содержит: описание эксперимента, методологию (branch, epsilon, alpha), статистику, data_hash, путь к графику.

### Реальность: Два разных отчёта

**Отчёт distribution_validator (work/docs/distribution_validator/audit-*.md):**
- Содержит: study conditions, verdict, D_obs, p-values, parameters, status codes, warnings, trace, figure_path
- НО: пишется в `work/docs/distribution_validator/`, а НЕ рядом с исследованием
- Путь: `work/docs/distribution_validator/audit-LN2-N3471-ACCEPT.md`

**Отчёт study_runner (рядом с исследованием, например `parsers/agentRx/magentic_one/guardrails_triggered/`):**
- Содержит: Status, Best Distribution, p-value, D-statistic, Errors, Attempts, Duration, Attempts Log
- НЕ содержит:
  - `N_total` — общий размер выборки
  - `N_fit / N_test` — размеры train/test
  - `epsilon` — инженерный допуск (default 0.03)
  - `alpha` — уровень значимости (default 0.05)
  - `branch` — A_BOOTSTRAP / B_SPLIT / C_TOST
  - `figure_path` — путь к PNG
  - `data_hash` — SHA-256
  - `parameters` — параметры распределения
  - `skewness` — бутстрепная асимметрия
  - `warnings` — список предупреждений
  - Описание ошибки (что измеряем, зачем)
  - dataset, error_type, error_subtype (дублируется в study_id, но не структурировано)

**N/A вместо значений:**
- `p_final` для UNDERPOWERED = пусто (правильно)
- `D_obs` для UNDERPOWERED = 0.0 (вводит в заблуждение — не "не измерено", а "ноль")
- `final_dist` для UNDERPOWERED = GU (Guard — fallback, не real fit)

### Организация файлов

**Ожидание:** структура `parsers/{dataset}/{error_type}/{subgroup}/audit_report.md`

**Реальность:** audit_report.md лежит рядом с parquet в `parsers/.../{study_id}/`, но:
- PNG лежит в `work/plots/distribution_validator/audit-{dist}-{n}-{verdict}.png` (не рядом с audit_report!)
- distribution_validator report лежит в `work/docs/distribution_validator/audit-*.md` (отдельная директория)

---

## G7: Методология 2.0 Не Описана в Отчётах

### Ожидание
Каждый audit_report объясняет, КАК именно проводилось исследование (branch, параметры, почему именно этот branch выбран).

### Реальность

**study_runner audit_report НЕ содержит:**
- Какой branch использовался (A_BOOTSTRAP / B_SPLIT / C_TOST)
- Почему выбран именно этот branch
- Значения epsilon, alpha, power_target
- N_min / N_max — барьеры из scale_selector
- Сколько итераций bootstrap (B=1000)
- Сколько split-итераций (K=100)
- TOST tolerance (ε)

**distribution_validator report содержит эту информацию**, но:
- Он в отдельной директории `work/docs/distribution_validator/`
- Он не связан с конкретным исследованием по пути
- Имя файла: `audit-LN2-N3471-ACCEPT.md` — без study_id
- При параллельном запуске — коллизии имён (как у PNG)

**Результат:** Пользователь, читая audit_report.md в папке исследования, не понимает, как именно был проведён KS-тест. Он видит "ACCEPT" но не понимает, через какой branch и с какими параметрами.

---

## Сводная Таблица Расхождений

| # | Область | Ожидание | Реальность | Приоритет |
|---|---------|----------|------------|-----------|
| G1a | TRAIL categories | 12 типов из archive | 20 типов с ДРУГИМИ именами | Высокий |
| G1b | who_and_when | 6 типов из archive | 0 типов (другие имена) | **Критический** |
| G1c | terminalbench/itbench | keyword search ошибки | Полностью отсутствуют | Средний |
| G2a | UNDERPOWERED PNG | Всегда генерируется | n<50 — без графика | Средний |
| G2b | PNG collision | 1 study = 1 PNG | 31 коллизия → 91 вместо 123 | **Критический** |
| G3a | data_hash uniqueness | Уникален per study | Коллизии при одинаковых values | Средний |
| G3b | data_hash scope | Хэширует dataset+type+values | Только values | Средний |
| G4a | results.csv fields | Все ключевые метрики | Нет: p_trajectory, CI, percentiles | Средний |
| G4b | percentile stats | p25, p50, p75, p90, p95, p99 | Не вычисляются | Низкий |
| G5 | PNG заголовок | Полный контекст | Только study_label + dist | Низкий |
| G6a | audit_report fields | Всё: methodology + stats | Только: status, dist, attempts | Средний |
| G6b | N/A значения | Осмысленные значения | D_obs=0.0 для UNDERPOWERED | Низкий |
| G6c | file organization | audit_report рядом с PNG | PNG в отдельной директории | Низкий |
| G7 | methodology description | Branch + params explained | Нет информации о branch | Средний |

---

## Наблюдения по Методологии

1. **distribution_validator и study_runner — две разные системы отчётности**, которые плохо интегрированы. distribution_validator генерирует подробные отчёты в `work/docs/`, но они не связаны с исследованиями в `parsers/`.

2. **"Исследования" ≠ "Исследования из archive":** 183 исследования в results.csv — это НЕ те же 46 ошибок из archive/errors_stats.csv. Это новые категории (TRAIL) плюс nebius subgroups. Нельзя сказать "миграция неполная" — миграция была частичной, но текущий пайплайн генерирует ДРУГИЕ исследования.

3. **TZ_8.* — текущая методология:** МЕТОДОЛОГИЯ-2.0 (KS-test, bootstrap, TOST) применяется, но в audit_report не описана. TZ_8.3 исправил TRAIL parser, TZ_8.6-8.10 добавили AgentRx, TRAIL, Who_and_When парсеры.

---

## Что Нужно для Симулятора (Практический Аспект)

Пайплайн должен предоставить для симулятора:

1. **P_err** — вероятность ошибки = n_trajectories_with_error / n_trajectories_total
2. **P(step)** — распределение момента ошибки = fit distribution параметры
3. **D** — штраф по времени = ??? (НЕТ в текущем пайплайне)

**Чего не хватает для симулятора:**
- P_err для каждого error_type (нужно: n_with_error, n_total)
- Distribution parameters (есть в distribution_validator, но не в results.csv)
- Штраф по времени D (нужно определить методологию)

---

*Документ готов для обсуждения. Следующий шаг: приоритизация и план имплементации.*