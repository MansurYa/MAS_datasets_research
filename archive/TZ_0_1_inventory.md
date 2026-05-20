# TZ_0.1 — Инвентаризация

## Итоговая таблица файлов (не-датасетные)

| Путь | Размер | Читается скриптами | Решение |
|------|--------|-------------------|---------|
| data/aggregated_errors.csv | 7.5K | Нет | Удалить |
| data/all_errors_combined.csv | 5.8K | Да (tz4_6_report, tz4_7_heavy_tails) | Оставить |
| data/all_errors_combined_v2.csv | 5.8K | Да (tz4_7_report) | Оставить |
| data/all_errors_final.csv | 17K | Да (tz5_a_fix_data) | Оставить |
| data/all_errors_fixed.csv | 20K | Да (tz5_c_csv) | Оставить |
| data/errors_classified.csv | 120K | Нет | Оставить (архив) |
| data/nebius_by_exit_status.csv | 4K | Нет | Оставить (архив) |
| data/unified_taxonomy.json | — | Нет | Оставить (архив) |
| data/tz7_tool_web_failure_positions.csv | — | Нет | Оставить (архив) |
| report/all_errors_final.csv | 17K | Да (tz5_b_plots, tz5_d_report, tz6_*) | Оставить |
| report/tz7_distribution_comparison.csv | — | Нет | Оставить (архив) |
| report/methodology.md | — | Нет | Переместить в docs/ |
| report/methodology.docx | — | Нет | Переместить в docs/ |
| REPOSITORY_MAP.md | — | Нет | Переместить в reference/ + обновить |
| OCR Методы прикладной Статистики.txt | 655K | Нет | Переместить в reference/ |
| ТЗ №1–7.md (10 файлов) | — | Нет | Переместить в TZ/ |
| __pycache__/ | — | Нет | Удалить |
| output_opus/ | — | Нет | Уже удалён Мансуром |

## Кандидаты на удаление (подтверждено)

1. `data/aggregated_errors.csv` — не читается ни одним скриптом
2. `__pycache__/` — Python bytecode, регенерируется автоматически

## Структура после TZ_0.3

```
MAS_datasets_research/
├── CLAUDE.md
├── AGENT_TRAJECTORY_DATASETS.md
├── fault_mode_analysis_and_classification_ru.html
├── p1_fault_mode_distributions.ipynb
├── .gitignore
├── data/           ← CSV + plots/
├── docs/           ← отчёты + methodology.md (перемещён из report/)
├── report/         ← all_errors_final.csv + plots/ (читается скриптами)
├── scripts/new/    ← новые скрипты TZ_4_9+
├── TZ/             ← все TZ-файлы
├── reference/      ← REPOSITORY_MAP.md + OCR учебник + STATS_BOOK_INDEX.md
├── memory/         ← TZ_STATUS.md + MEMORY_INDEX.md
└── tz*.py          ← старые скрипты (не трогать)
```
