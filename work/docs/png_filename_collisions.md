# Коллизии имён PNG-плотов в distribution_validator

## Симптом

После прогона `run_all.py` на 183 исследованиях в `work/plots/distribution_validator/` лежит **91 PNG**, а не 183.

## Причины

### 1. UNDERPOWERED не рисует плот

В `scripts/distribution_validator/main.py:94-113` при режиме `selector_result.mode == MODE_UNDERPOWERED` функция возвращается **до** блока `plot_fit` (строка 173). PNG не создаётся, `plot_path = ""`.

В результатах 60 UNDERPOWERED → 60 отсутствующих PNG.

### 2. Имя файла не содержит `study_id`

`scripts/distribution_validator/visualization.py:191`:

```python
audit_id = f"audit-{report.dist_type}-N{report.n_test}-{report.verdict}"
output_path = PLOTS_DIR / f"{audit_id}.png"
```

Ключ имени: `(dist_type, n_test, verdict)` — без `study_id`. Две студии с одинаковыми итоговым распределением, числом наблюдений и вердиктом пишут в **один и тот же файл**. Последний writer выигрывает, более ранний плот перезатирается.

Пример: `LN2-N30857-REJECT` встречается 4 раза → один PNG.

### 3. Редкий сбой `plot_fit` в воркере

В параллельном режиме воркеры независимо вызывают `plot_fit`. Если внутри `matplotlib.savefig` бросает исключение (например, OOM в subprocess), ветка `try/except` в `main.py:177-179` глушит его, `plot_path = ""`. PNG не создаётся, а студия в `results.csv` остаётся со статусом ACCEPT/REJECT.

## Численная разбивка (прогон 2026-06-05)

| | Кол-во |
|---|---|
| Всего studies | 183 |
| UNDERPOWERED (плот не рисуется) | 60 |
| Студий с плотом (ACCEPT + REJECT) | 123 |
| Уникальных ключей `(dist, n, verdict)` | 92 |
| Коллизий (студии делят файл) | 31 |
| PNG на диске | 91 |
| Потеряно из-за сбоя `plot_fit` | 1 |

**123 − 31 = 92** ожидаемых файла; **91** фактически. Несовпадение в одну штуку — известная погрешность параллельного режима (не ошибка нумерации, а подавленное исключение).

## Что НЕ затронуто

- `audit_report.md` пишется через `report.py:69` с уникальным `audit_id` (содержит timestamp) — коллизий нет.
- `fit_log.json` пишется в уникальную подпапку `Path(spec.parquet_path).parent / spec.study_id` — коллизий нет.
- `results.csv` сортируется по `study_id` — детерминирован.

Коллизия затрагивает **только** PNG-плоты в общей директории `work/plots/distribution_validator/`.

## Статус

Pre-existing issue, не введено параллелизацией `--parallel`. Воспроизводится и в sequential режиме, если в разных студиях совпадают `(final_dist, n_errors, status)`.

## Возможные фиксы (не в скоупе текущего TZ)

1. **Минимальный:** добавить `study_id` в имя PNG → `audit-{dist_type}-N{n_test}-{verdict}-{study_id}.png`. Тогда 92 ключа → 92 файла, 1 потерянный плот становится виден в выводе.
2. **Правильный:** хранить плоты в подпапке студии `Path(spec.parquet_path).parent / spec.study_id /` — как `fit_log.json` и `audit_report.md`. Полная изоляция.
3. **Логирование сбоев:** в `main.py:177` поднять уровень логирования до `ERROR` и собрать отдельный `failed_plots.log` в `LOG.txt`.
