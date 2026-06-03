# Индекс файлов проекта MAS Datasets Research (work/)

## Спецификации (work/specs/)

| Файл | Статус | Описание |
|------|--------|----------|
| `TZ_1.md` | ✓ Завершено | Анализ типов ошибок tool call по TRAIL/AgentRx |
| `TZ_2.md` | ✓ Завершено (v2) | Извлечение invalid_invocation из nebius/SWE-agent |
| `TZ_3.md` | ✓ Завершено | Baseline EDA по nebius/SWE-agent-trajectories |
| `TZ_4.md` | ✓ Завершено | Реформа дедупликации: плоский формат вместо вложенного |
| `TZ_5.md` | ✓ Завершено | Data Integrity Check: аккумуляторы и индексация |
| `TZ_6.md` | ✓ Завершено | Survival Analysis: Weibull Mixture, Context Rot |

## Отчёты (work/reports/)

| Файл | Статус | Описание |
|------|--------|----------|
| `TZ_1_report.md` | ✓ Завершено | Анализ типов ошибок (TRAIL, AgentRx) |
| `TZ_2_report.md` | ✓ Завершено (v1) | Первая итерация парсера invalid_invocation |
| `TZ_2_v2_report.md` | ✓ Завершено (v2) | Финальный отчёт. A 100%, B 84%, E1 100%, E2 пограничная |
| `TZ_3_baseline_eda_report.md` | ✓ Завершено | Baseline EDA: стенка контекста ~100k символов |
| `TZ_5_report.md` | ✓ Завершено | Data Integrity Check: 4 инварианта, все PASS |
| `TZ_6_survival_analysis_report.md` | ✓ Завершено | Survival Analysis: Context Rot (E1 β>1), Weibull Mixture |

## Скрипты (work/scripts/)

| Файл | Описание |
|------|----------|
| `nebius_all_errors.py` | Унифицированный парсер A/B/E1/E2. Выход: плоский `errors_invalid_invocation.json` |
| `nebius_errors_cli.py` | CLI-интерфейс к nebius_all_errors.py |
| `verify_tz5.py` | Верификатор 4 инвариантов целостности данных |
| `baseline_eda.py` | TZ_3: Baseline EDA (длины, контекстная стенка) |
| `survival_analysis.py` | TZ_6: Survival Analysis (Weibull Mixture, Context Rot, BIC) |

## Документация (work/docs/)

| Файл | Описание |
|------|----------|
| `invalid_invocation_concept.md` | Концепция invalid_invocation: что это, где границы, FP-анализ |
| `baseline_trajectory_physics.md` | TZ_3: 7 аксиом о физике среды (стенка контекста, состав популяции) |
| `структура_датасетов_ошибок.md` | Структура датасетов ошибок |

## Данные (work/data/)

| Файл | Описание |
|------|----------|
| `errors_invalid_invocation.json` | Плоский список ошибок: A/B/E1/E2. 317 349 записей, 381 MB |
| `TZ_3_trajectory_lengths.csv` | 80 036 × 6: instance_id, exit_status, exit_group, n_steps, n_chars, target |
| `TZ_3_descriptive_stats.csv` | Описательная статистика по группам |
| `TZ_6_fit_params.csv` | TZ_6: параметры всех фиттеров (Weibull Mixture, Lognormal_3P, BIC) |
| `reliability_plots/TZ_6_exp*.png` | TZ_6: 7 Probability Plots |
| `plots/TZ_3_*.png` | TZ_3: 8 графиков |

---

## Ключевые результаты

### TZ_1: Анализ типов ошибок (TRAIL, AgentRx)

4 типа ошибок tool call:
- invalid_invocation, tool_timeout, tool_web_failure, misinterpretation_of_tool_output

"Incorrect tool call" Huawei соответствует **invalid_invocation**.

### TZ_2 v2: Извлечение invalid_invocation из nebius

**Надёжные категории (A + B + E1):** 4 137 истинных событий на первом шарде.
- P_step ≈ 0.0116
- P_traj ≈ 0.297

**Расширенный набор (с E2):** 5 450 истинных событий.
- P_step ≈ 0.0153
- P_traj ≈ 0.383

**Экстраполяция на 80 036 траекторий:** ≈ 30 622 траекторий с ошибкой, ≈ 65 397 истинных событий.

| Категория | TP rate | n_unique | n_true | Надёжность |
|-----------|---------|----------|--------|------------|
| A: Пути | 100% | 2 666 | 2 666 | ✓ |
| B: Bash | 84% | 560 | 470 | ✓ |
| C: TypeError | 0% | 107 | 0 | ✗ |
| D: Missing args | 5% | 148 | 7 | ✗ |
| E1: Edit syntax | 100% | 1 001 | 1 001 | ✓ |
| E2: Edit undefined | 50%* | 2 613 | 1 306 | ⚠ |

---

## Статус проекта

| Компонент | Статус |
|-----------|--------|
| TZ_1 — анализ типов ошибок | ✓ |
| TZ_2 v1 — первый парсер | ✓ (отброшен) |
| TZ_2 v2 — улучшенный парсер | ✓ |
| TZ_3 — Baseline EDA | ✓ |
| TZ_4 — Реформа дедупликации | ✓ |
| TZ_5 — Data Integrity Check | ✓ |
| TZ_6 — Survival Analysis | ✓ |

Подробный статус: `memory/TZ_STATUS.md`.
