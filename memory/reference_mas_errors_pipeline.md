---
name: mas-errors-pipeline
description: GAP analysis и план решения 6+ проблем в MAS_errors pipeline
metadata:
  type: reference
---

# MAS_errors Pipeline: GAP Analysis

> **Создан:** 2026-06-06
> **Обновлён:** 2026-06-06
> **Статус:** Все фазы завершены

## Документация

- **Отчёт о выполненных работах:** `work/docs/MAS_errors_pipeline_report.md`
- **План исправлений:** `work/docs/MAS_errors_pipeline_plan.md`
- **Анализ проблем:** `work/docs/MAS_errors_gap_analysis.md`

## Проблемы и статусы

| ID | Проблема | Фаза | Статус |
|----|----------|------|--------|
| 1.1 | TRAIL parser: step_idx для nested spans | Критическая | ✅ Исправлено |
| 1.2 | who_and_when parser: keyword fallback | Критическая | ✅ Исправлено |
| 1.3 | PNG: хранить в директории исследования | Критическая | ✅ Исправлено |
| 1.4 | Перезапуск исследований | Критическая | ⏳ Ожидает |
| 2.1 | UNDERPOWERED: гистограмма с watermark | UI/UX | ✅ Исправлено |
| 2.2 | PNG заголовок: dataset, error_type, analysis_var | UI/UX | ✅ Исправлено |
| 2.3 | Audit reports: в parsers/ | UI/UX | ✅ Исправлено |
| 2.4 | Audit reports: описание методологии | UI/UX | ✅ Исправлено |
| 3.1 | results.csv: расширение до 23 колонок | Аналитика | ✅ Исправлено |
| 3.2 | JSON complementary output | Аналитика | ✅ Исправлено |
| 3.3 | HTML summary report | Аналитика | ✅ Исправлено |

## Артефакты после исправлений

- `work/MAS_errors/results.csv` — 23 колонки (было 15)
- `work/MAS_errors/summary.html` — интерактивный HTML отчёт
- `work/MAS_errors/parsers/*/study_result.json` — JSON complementary output
- `work/MAS_errors/parsers/*/*/fit_log.json` — лог всех попыток fit
- `work/MAS_errors/parsers/*/*/audit_report.md` — audit report в директории исследования

## Следующий шаг

Полный перезапуск исследований на всех 170+ исследованиях:

```bash
PYTHONPATH=. python work/MAS_errors/study_runner/run_all.py --fast
```

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