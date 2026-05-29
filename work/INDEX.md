# Индекс файлов проекта MAS Datasets Research (work/)

## Спецификации (work/specs/)

| Файл | Статус | Описание |
|------|--------|----------|
| `TZ_1.md` | ✓ Завершено | Анализ типов ошибок tool call по TRAIL/AgentRx |
| `TZ_2.md` | ✓ Завершено (v2) | Извлечение invalid_invocation из nebius/SWE-agent |

## Отчёты (work/reports/)

| Файл | Статус | Описание |
|------|--------|----------|
| `TZ_1_report.md` | ✓ Завершено | Анализ типов ошибок (TRAIL, AgentRx) |
| `TZ_2_report.md` | ✓ Завершено (v1) | Первая итерация парсера invalid_invocation. A 100%, B 63%, C 40%, D 29% |
| `TZ_2_v2_report.md` | ✓ Завершено (v2) | Финальный отчёт. A 100%, B 84%, C/D отброшены, E1 100%, E2 пограничная |

## Скрипты (work/scripts/)

| Файл | Описание |
|------|----------|
| `nebius_all_errors.py` | Унифицированный парсер A/B/E1/E2 (C/D отключены — FP) |
| `nebius_errors_cli.py` | CLI-интерфейс к nebius_all_errors.py |
| `nebius_edit_errors.py` | Парсер ошибок edit-инструмента |
| `nebius_invalid_invocation_errors_view.ipynb` | Jupyter-ноутбук для просмотра результатов |
| `gen_notebook.py` | Генератор ноутбука |
| `stats_errors_detailed.py` | Детальная статистика ошибок (4 варианта подсчёта) |
| `stats_errors_per_trajectory.py` | Статистика ошибок по траекториям |

## Документация (work/docs/)

| Файл | Описание |
|------|----------|
| `invalid_invocation_concept.md` | Концепция invalid_invocation: что это, где границы, анализ парсера |
| `subagent_fp_analysis_methodology.md` | Методология FP-анализа категорий C и D |
| `структура_датасетов_ошибок.md` | Структура датасетов ошибок |
| `nebius_error_statistics.md` | Статистика ошибок (4 варианта подсчёта) |

## Данные (work/data/)

| Файл | Описание |
|------|----------|
| `nebius_invalid_invocation_errors_A.json` | Финальные данные: категория A (FileNotFoundError, 100% TP) |
| `nebius_invalid_invocation_errors_B.json` | Финальные данные: категория B (bash errors, 84% TP) |
| `nebius_invalid_invocation_errors_C.json` | Данные категории C (TypeError) — отключена, 100% FP |
| `nebius_invalid_invocation_errors_D.json` | Данные категории D (missing args) — отключена, 95% FP |
| `nebius_invalid_invocation_errors_E1.json` | Финальные данные: категория E1 (edit syntax, 100% TP) |
| `nebius_invalid_invocation_errors_E2.json` | Финальные данные: категория E2 (edit undefined name, 50% TP) |
| `nebius_edit_errors_E1.json` | Edit-ошибки E1 |
| `nebius_edit_errors_E2.json` | Edit-ошибки E2 |
| `TZ_2_v2_metrics.json` | Сводные метрики TZ_2 v2 |
| `who_when_hc_classification.csv` | Who&When HC классификация (TZ_1) |

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

Подробный статус: `memory/TZ_STATUS.md`.
