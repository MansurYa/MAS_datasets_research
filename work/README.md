# work/ — Текущая работа

Новый цикл исследования (после отклонения старого отчёта Huawei).

| Папка | Содержимое |
|-------|-----------|
| `specs/` | TZ-спецификации: TZ_1.md, TZ_2.md, TZ_3.md |
| `scripts/` | Скрипты парсинга и анализа |
| `reports/` | Отчёты: TZ_1_report.md, TZ_2_v2_report.md, TZ_3_baseline_eda_report.md |
| `data/` | Выходные JSON, CSV и графики |

---

## Ноутбук для просмотра ошибок nebius

**Файл:** `nebius_review.ipynb`

### Быстрый старт

```bash
cd /Volumes/MansurSSD/MAS_datasets_research
jupyter notebook work/nebius_review.ipynb
```

### Порядок действий

1. **Cell 1** — задай пути (PARQUET_DIR, JSON_FILE)
2. **Cell 2** — выполни, увидишь список ошибок
3. **Cell 3** — задай INSTANCE_ID (например `iterative__dvc-6633`), выполни
4. **Cell 4** — увидишь все ошибки для INSTANCE_ID с `traj_idxs` и `step_idxs`
5. **Cell 3b** — задай TRAJ_IDX и STEP_IDX, выполни, увидишь текст шага

### Файлы данных (унифицированный формат)

| Файл | Категория | Записей |
|------|-----------|---------|
| `nebius_invalid_invocation_errors_A.json` | FileNotFoundError | 10,226 |
| `nebius_invalid_invocation_errors_B.json` | bash command errors | 7,731 |
| `nebius_invalid_invocation_errors_C.json` | TypeError | 1,886 |
| `nebius_invalid_invocation_errors_D.json` | missing arguments | 1,550 |
| `nebius_invalid_invocation_errors_E1.json` | E999 SyntaxError | 12,573 |
| `nebius_invalid_invocation_errors_E2.json` | F821 undefined name | 35,662 |

### Структура JSON (унифицированный формат)

```json
{
  "instance_id": "iterative__dvc-6633",
  "category": "E1",
  "count": 251,
  "locations": [
    {"traj_idx": 0, "step_idx": 9, "text": "...", "exit_status": "..."},
    {"traj_idx": 2, "step_idx": 11, "text": "...", "exit_status": "..."}
  ],
  "traj_idxs": [0, 2, 3, 5],
  "step_idxs": [9, 11, 13],
  "traj_idx": 0,
  "step_idx": 9,
  "normalized_pattern": "...",
  "text": "..."
}
```

### Как менять данные

- В Cell 1 измени `CATEGORY = "A"` (доступны: A, B, C, D, E1, E2)
- Файл автоматически меняется на `nebius_invalid_invocation_errors_{CATEGORY}.json`
- INSTANCE_ID бери из Cell 2 (список instance_id)
- TRAJ_IDX бери из Cell 4 (traj_idxs)

### Подробная инструкция

См. `docs/NOTEBOOK_GUIDE.md`