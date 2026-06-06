# Параллелизация study_runner

## Использование

```bash
# Последовательный (как раньше)
python -m work.MAS_errors.study_runner.run_all --fast

# Параллельный (6 воркеров)
python -m work.MAS_errors.study_runner.run_all --fast --parallel 6
```

Флаг `--parallel 0` (или отсутствие) — последовательное выполнение. Sequential path не затронут.

## Что реализовано

`ProcessPoolExecutor` на уровне исследований в `run_all.py`. Каждый study полностью независим — свой parquet, свой seed, свои артефакты.

Ключевые решения:
- `_worker_init()` ставит `matplotlib.use('Agg')` до импорта pyplot (избегает crash macOS GUI backend в subprocess)
- FileHandler отключается в воркерах (нет гонки на LOG.txt)
- CSV пишется один раз в конце, отсортирован по study_id (детерминированный порядок)
- Studies сортируются по размеру parquet (тяжёлые первыми) для балансировки нагрузки
- Без per-task timeout (stdlib не умеет убивать отдельный subprocess)

## Бенчмарки

| Режим | 5 trail studies | Ускорение |
|-------|----------------|-----------|
| Sequential | ~18 сек | — |
| Parallel (2 workers) | ~8 сек | ×2.2 |

Ожидаемое ускорение на полном прогоне (183 studies, 8 ядер, 6 workers): ×4–5.

## Ограничения

- Ctrl+C ждёт завершения текущих workers (до ~2 мин)
- Ленивый import `dv_main` внутри `run_study()` — если переедет на module-level, parallel сломается
- PLOTS_DIR filename collision (pre-existing, не введено параллелизацией)
