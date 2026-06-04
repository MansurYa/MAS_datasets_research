TZ_8.2 завершён. Переходим к TZ_8.3.

---

# TZ_8.3 — Парсеры TRAIL, AgentRx, Who_and_When

> **Назначение:** Создать парсеры для остальных датасетов.
> **Принцип:** Один парсер на датасет. Discovery → код → тесты → output.

---

## TRAIL

### Discovery (перед написанием кода)

Просканировать `datasets/TRAIL/` — показать:
- Точные пути к parquet
- Структуру колонок (trace, labels, ...)
- Как определить тип ошибки из `labels → errors[].category`

### Структура выхода

```
work/MAS_errors/parsers/trail/
├── run_all.py
├── parser.py
└── instruction_noncompliance/
    ├── errors.parquet
    └── stats.json
├── formatting_errors/
│   └── ...
├── context_handling_failures/
│   └── ...
├── resource_abuse/
│   └── ...
├── poor_information_retrieval/
│   └── ...
├── incorrect_problem_identification/
│   └── ...
├── language_only/
│   └── ...
├── tool_related/
│   └── ...
├── task_orchestration/
│   └── ...
└── goal_deviation/
    └── ...
```

**10 типов × 1 вариант** (без dedup) = **10 папок**.

###TRAIL parser — ключевая логика

```python
# Читать: datasets/TRAIL/data/*.parquet
# Колонки: instance_id, trace, labels (JSON-строка)

# labels = json.loads(row["labels"])
# labels["errors"] = [{"category": str, "location": str, "evidence": str}, ...]

# Для каждого errors:
#   step_idx =  из location (парсить номер шага)
#   chars_before_error = 0  ← TRAIL не имеет chars_before_error (или: рассчитать из trace)
#   error_text = evidence
#   normalized_pattern = normalize_error_pattern(evidence)
#   TRAIL не имеет: exit_status, target, exit_group
```

---

## AgentRx

### Discovery (перед написанием кода)

Просканировать `datasets/microsoft-AgentRx/` — показать:
- Формат JSONL (magentic_one.jsonl, tau_retail.jsonl)
- `failures[].failure_category`, `failures[].step_number`
- Какой агент (WebSurfer, Orchestrator, ...) и нужен ли он

### Структура выхода

```
work/MAS_errors/parsers/agentRx/
├── run_all.py
├── magentic_one/
│   ├── parser.py
│   ├── instruction_adherence_failure/
│   │   ├── errors.parquet
│   │   └── stats.json
│   ├── guardrails_triggered/
│   ├── misinterpretation_of_tool_output/
│   ├── intent_not_supported/
│   ├── intent_plan_misalignment/
│   └── invention_of_new_information/
└── tau_retail/
    ├── parser.py
    ├── instruction_adherence_failure/
    ├── intent_not_supported/
    ├── intent_plan_misalignment/
    ├── misinterpretation_of_tool_output/
    └── system_failure/
```

**magentic_one: 6 типов, tau_retail: 5 типов. Без dedup. = 11 папок.**

---

## Who_and_When

### Discovery (перед написанием кода)

Просканировать `datasets/Kevin355-Who_and_When/Hand-Crafted.parquet` — показать:
- Колонки: history, question, mistake_agent, mistake_step, mistake_reason, mistake_type
- Что такое `mistake_type=NULL` (нет ошибки? пропускать?)
- `mistake_step` — это step_idx?

### Структура выхода

```
work/MAS_errors/parsers/who_and_when/
├── run_all.py
├── parser.py
├── wrong_reasoning/
│   ├── errors.parquet
│   └── stats.json
├── processing_error/
│   └── ...
└── tool_failure/
    └── ...
```

**3 типа × 1 вариант = 3 папки.** (mistake_type=NULL пропускаем — это отсутствие ошибки.)

---

## Реализация

### Шаг 1: Discovery (выполнить самостоятельно)

Перед написанием кода — просканировать три директории и показать мне формат данных. Я не знаю точной структуры.

### Шаг 2: TRAIL parser → показать код + тесты

### Шаг 3: AgentRx parser (magentic_one + tau_retail) → показать код + тесты

### Шаг 4: Who_and_When parser → показать код + тесты

### Шаг 5: Интеграция в `work/MAS_errors/parsers/run_all.py`

```python
"""Запускает ВСЕ парсеры всех датасетов."""
from work.MAS_errors.parsers.nebius.invalid_invocation.parser import run as run_nebius
from work.MAS_errors.parsers.trail.parser import run as run_trail
from work.MAS_errors.parsers.agentRx.magentic_one.parser import run as run_arx_m1
from work.MAS_errors.parsers.agentRx.tau_retail.parser import run as run_arx_tr
from work.MAS_errors.parsers.who_and_when.parser import run as run_ww

def run_all():
    run_nebius()
    run_trail()
    run_arx_m1()
    run_arx_tr()
    run_ww()
```

---