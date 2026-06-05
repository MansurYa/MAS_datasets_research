# TZ_8.6 — Интеграционная проверка pipeline

> **Цель:** Доказать или опровергнуть, что исследования дают реальные результаты.
>
> **Что проверяем:** Output-driven. Не код, не формулы — **файлы и числа**.
>
> **Режим:** Один раз запустить → посмотреть → verdict.

---

## 0. Структура проверки

```
Запустить 5 исследований (разные датасеты, разные ошибки)
  → Проверить что результаты разумные
  → Проверить что файлы создаются
  → Вердикт
```

**Почему 5:** Достаточно для доверия, мало для потери времени. Разные enough для охвата pipeline.

---

## 1. Выбрать 5 исследований

Выбрать из существующего `study_list.csv` или из `work/MAS_errors/results.csv`:

| # | dataset | error_type | analysis_var | Почему |
|---|---|---|---|---|
| 1 | nebius | A | step_idx | Много данных (~31k), ожидание ACCEPT |
| 2 | nebius | B | step_idx | Много данных (~69k), ожидание ACCEPT |
| 3 | nebius | ALL | step_idx | Максимум данных, ожидание ACCEPT |
| 4 | nebius | A | chars_before_error | Другая переменная, проверка что не ломается |
| 5 | AgentRx magentic_one | instruction_adherence_failure | step_idx | Мало данных (197), ожидание UNDERPOWERED |

Если любой из них не существует в study_list — выбрать следующий по списку.

---

## 2. Запустить 5 исследований

Для каждого из 5:

```bash
cd /Volumes/MansurSSD/MAS_datasets_research

# Study 1
.venv/bin/python -c "
from work.MAS_errors.study_runner.generate_study_list import scan_parsers_output
from work.MAS_errors.study_runner.run_study import run_study, save_artefacts

studies = scan_parsers_output()
target = [s for s in studies if s.dataset=='nebius' and s.error_type=='invalid_invocation' 
    and s.error_subtype=='A' and s.analysis_var=='step_idx'][0]
print(f'Study: {target.study_id}, parquet: {target.parquet_path}')
result = run_study(target)
save_artefacts(target, result)
print(f'Status: {result.status}, Dist: {result.final_dist}, p_final: {result.p_final}')
print(f'D_obs: {result.D_obs}, n_errors: {result.n_errors}')
print(f'Duration: {result.duration_s:.1f}s')
"
```

Аналогично для studies 2-5.

**Output каждого запуска:**
- study_id
- status (ACCEPT/REJECT/UNDERPOWERED/ERROR)
- final_dist
- p_final
- D_obs
- n_errors
- duration_s
- artifacts created (filepaths)

---

## 3. Проверить результаты

### 3.1. Ни одно исследование не ERROR

Если любое из 5 имеет `status = ERROR` → **FAIL**. STOP.

### 3.2. Статусы разумные

| Study | Ожидание | Проверка |
|---|---|---|
| nebius A step_idx | ACCEPT или REJECT | status ∈ {ACCEPT, REJECT} |
| nebius B step_idx | ACCEPT или REJECT | status ∈ {ACCEPT, REJECT} |
| nebius ALL step_idx | ACCEPT или REJECT | status ∈ {ACCEPT, REJECT} |
| nebius A chars | ACCEPT или REJECT | status ∈ {ACCEPT, REJECT} |
| AgentRx magent | ACCEPT или REJECT или UNDERPOWERED | status ≠ ERROR |

**FAIL если:** Все 5 — UNDERPOWERED (подозрительно, данных должно хватить). Или все 5 — ACCEPT (тоже подозрительно, должен быть разброс).

### 3.3. Файлы созданы

Проверить что для каждого исследования существуют:

```bash
# Для каждого study_id:
ls work/MAS_errors/parsers/nebius/invalid_invocation/A/nebius_invalid_invocation_A_all_step_idx/
ls work/MAS_errors/parsers/nebius/invalid_invocation/B/...
```

Проверяемые файлы:
- `fit_log.json` — существует, > 100 bytes, содержит `verdict`
- `audit_report.md` — существует, > 300 bytes, содержит вердикт + p_final

**FAIL если:** Любой файл отсутствует или < указанного размера.

---

## 4. Результат в report

Создать файл `work/report/TZ_8.6-report.md`:

```markdown
# TZ_8.6 Report

## Дата проверки: [сегодня]

## Исследования

| # | study_id | status | dist | p_final | D_obs | n_errors | dur_s |
|---|---|---|---|---|---|---|---|
| 1 | ... | ... | ... | ... | ... | ... | ... |
| 2 | ... | ... | ... | ... | ... | ... | ... |
| 3 | ... | ... | ... | ... | ... | ... | ... |
| 4 | ... | ... | ... | ... | ... | ... | ... |
| 5 | ... | ... | ... | ... | ... | ... | ... |

## Проверки

### 3.1: Ни одного ERROR
- Результат: PASS | FAIL
- Данные: [список статусов]

### 3.2: Статусы разумные
- Результат: PASS | FAIL
- Данные: [комментарий]

### 3.3: Файлы созданы
- fit_log.json: PASS | FAIL — [список]
- audit_report.md: PASS | FAIL — [список]

## Итоговый вердикт
- **PASS:** Pipeline работает. Можно запускать полный прогон.
- **FAIL:** [конкретная причина]. Детали в секции выше.
```

---

## 5. Критерии FAIL

**FAIL = конкретная ситуация, не "что-то не так":**

| FAIL | Определение |
|---|---|
| ERROR status | Любое исследование имеет `status = ERROR` |
| Все UNDERPOWERED | 5 из 5 — UNDERPOWERED (pipeline не работает с данными) |
| Все ACCEPT | 5 из 5 — ACCEPT (слишком лёгкие критерии или данные синтетические) |
| Файл не создан | `fit_log.json` или `audit_report.md` отсутствует для любого исследования |
| Файл < размера | `fit_log.json` < 100 bytes или `audit_report.md` < 300 bytes |

При FAIL: записать в report → стоп → ждать решений.

При PASS: записать в report → перейти к полному прогону.

---

## 6. Полный прогон (после PASS)

Если все проверки PASS → запустить полный прогон:

```bash
.venv/bin/python -m work.MAS_errors.study_runner.run_all
```

После завершения:
```bash
.venv/bin/python -m work.MAS_errors.summary
```

Показать `work/MAS_errors/summaries/summary_table.md`.

---

<sub-instruction>

**ВЫПОЛНЕНИЕ:**

Шаг 1: Создать директорию `work/report/`

Шаг 2: Запустить исследование 1. Показать output. Записать в report.

Шаг 3: Исследование 2. Показать output. Записать в report.

Шаг 4: Исследование 3. Показать output. Записать в report.

Шаг 5: Исследование 4. Показать output. Записать в report.

Шаг 6: Исследование 5. Показать output. Записать в report.

Шаг 7: Проверки 3.1, 3.2, 3.3. Записать результаты.

Шаг 8: Итоговый вердикт.

Если FAIL на любом шаге — СТОП, записать, ждать.

**Принцип:** Показывать конкретный output каждого запуска. Не "проверено". Показать числа.

</sub-instruction>