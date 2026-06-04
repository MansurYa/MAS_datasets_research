# TZ_8.2 — Парсер nebius invalid_invocation (из raw parquet)

> **Назначение:** Читать raw nebius parquet → парсить ошибки напрямую (логика из `nebius_all_errors.py`) → создавать ErrorRecord → 10 `.parquet` + 10 `.stats.json`.
>
> **Вход:** 12 шардов nebius parquet (80 036 траекторий)
>
> **Ключевое:** `errors_invalid_invocation.json` — это **выход** старого парсера. Новый парсер читает raw parquet напрямую, логика классификации переносится из `nebius_all_errors.py`.

---

## 1. Алгоритм (из nebius_all_errors.py)

### 1.1. Error classification functions

Копируются один-в-один из `nebius_all_errors.py`:

```python
# === Категория A: FileNotFoundError ===
def matches_A(text: str) -> bool:
    if 'FileNotFoundError' not in text and 'No such file or directory' not in text:
        return False
    if re.search(r'\bline\s+\d+', text, re.IGNORECASE):
        return False
    if 'ModuleNotFoundError' in text or 'ImportError' in text:
        return False
    if 'pytest' in text or 'fixture' in text:
        return False
    return True

# === Категория B: bash commands ===
def matches_B(text: str) -> bool:
    if not ('command not found' in text or 'cannot access' in text or 'cannot stat' in text):
        return False
    if 'ls: cannot access' in text:
        return False
    if 'SyntaxError' in text or 'syntax error' in text:
        return False
    if 'grep' in text and ('pattern' in text or 'search' in text):
        return False
    if 'python' in text.lower() and 'not found' in text:
        return False
    if '```' in text:
        return False
    return True

# === Edit tool patterns ===
EDIT_HEADER = "Your proposed edit has introduced new syntax error"
ERRORS_BLOCK_RE = re.compile(r'ERRORS:\s*\n((?:- .*\n?)+)', re.MULTILINE)
ERROR_LINE_RE = re.compile(r'^- (E\d+|F\d+|W\d+)\s+(.*)$')

def parse_edit_errors(text: str) -> list[tuple[str, str]]:
    m = ERRORS_BLOCK_RE.search(text)
    if not m:
        return []
    return [(em.group(1), em.group(2))
            for line in m.group(1).splitlines()
            if (em := ERROR_LINE_RE.match(line.strip()))]

def matches_E(text: str) -> bool:
    return EDIT_HEADER in text
```

### 1.2. Главный цикл по траекториям

```python
# Читаем все 12 шардов через pyarrow.dataset (один проход)
dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
table = dataset.to_table()
instance_ids = table["instance_id"].to_pylist()
trajectories = table["trajectory"].to_pylist()
exit_statuses = table["exit_status"].to_pylist()
targets = table["target"].to_pylist()

# Фиксируем first_occurrence[inst] → local_traj_idx вычисляется корректно
# (формула: global - first_occurrence[inst])
first_occurrence = {}
for row_idx, inst in enumerate(instance_ids):
    if inst not in first_occurrence:
        first_occurrence[inst] = row_idx
```

### 1.3. Подсчёт chars_before_error

```python
# ВАЖНО: chars считаются как в оригинале:
running_chars += len(step.get('text') or '') + len(step.get('system_prompt') or '')
```

Это значит: `chars_before_error` = сумма `len(text) + len(system_prompt)` по шагам **ДО** шага с ошибкой (НЕ включая шаг ошибки). `system_prompt` учитывается в каждом шаге, где он есть.

### 1.4. deduplication key

```python
key = (instance_id, global_traj_idx, normalized_pattern)
occurrence_in_traj = счётчик[key]
is_first_occurrence_in_traj = (счётчик[key] == 1)
```

---

## 2. Структура выхода

```
work/MAS_errors/parsers/nebius/
├── parser.py                   ← единый парсер для всех 10 вариаций
├── invalid_invocation_A/
│   ├── errors.parquet
│   └── stats.json
├── invalid_invocation_A_dedup/
│   ├── errors.parquet
│   └── stats.json
├── invalid_invocation_B/          ... (10 директорий)
├── invalid_invocation_B_dedup/
├── invalid_invocation_E1/
├── invalid_invocation_E1_dedup/
├── invalid_invocation_E2/
├── invalid_invocation_E2_dedup/
├── invalid_invocation_ALL/
└── invalid_invocation_ALL_dedup/
```

**ALL** = объединение A + B + E1 + E2. Перед сохранением:

```python
# ALL: объединяем все ErrorRecord из всех категорий
df_A = records_to_df(A_records)
df_B = records_to_df(B_records)
df_E1 = records_to_df(E1_records)
df_E2 = records_to_df(E2_records)
df_ALL = pd.concat([df_A, df_B, df_E1, df_E2], ignore_index=True)
```

---

## 3. ErrorRecord — уточнённые поля

Из `nebius_all_errors.py` E1/E2 **не содержат** `text` и `exit_status`. Но **содержат** `error_code`, `error_msg`, `error_type` (для E1) и `undefined_name`, `import_present_in_edit` (для E2).

```python
# Для E1/E2 — дополнительные поля:
error_code: str | None        # "E999", "F821"
error_msg: str | None         # оригинальное сообщение
error_type: str | None        # для E1: тип ошибки (IndentationError etc.)
undefined_name: str | None    # для E2: какое имя не определено
import_present_in_edit: bool | None  # для E2: импорт есть в edit block
```

**Решение:** Добавить эти поля в `ErrorRecord`. Для A/B оставляем None.

---

## 4. compute_stats — N_trajectories_total

Из `nebius_all_errors.py`: всего траекторий = `len(instance_ids)` = 80 036.

Это константа. Хардкодим в парсере:

```python
N_TOTAL_TRAJECTORIES = 80_036
```

---

## 5. Тесты

```python
# tests/test_nebius_parser.py (5 тестов, synthetic)

def test_matches_A():
    assert matches_A("ls: cannot access 'X': No such file or directory") == True
    assert matches_A("ModuleNotFoundError: No module named 'numpy'") == False
    assert matches_A("line 42: SyntaxError") == False

def test_matches_B():
    assert matches_B("/X: line N: find.: command not found") == True
    assert matches_B("ls: cannot access 'X': No such file or directory") == False
    assert matches_B("SyntaxError: invalid syntax") == False

def test_matches_E():
    assert matches_E("Your proposed edit has introduced new syntax error") == True
    assert matches_E("Some other text") == False

def test_parse_edit_errors():
    text = "ERRORS:\n- E999 IndentationError: unexpected indent\n- F821 undefined name 'os'"
    errors = parse_edit_errors(text)
    assert len(errors) == 2
    assert errors[0] == ("E999", "IndentationError: unexpected indent")
    assert errors[1] == ("F821", "undefined name 'os'")

def test_dedup_key():
    """Ключ = (instance_id, global_traj_idx, normalized_pattern)."""
    seen = defaultdict(int)
    c = {"instance_id": "r1", "global_traj_idx": 5, "normalized_pattern": "X"}
    seen[(c["instance_id"], c["global_traj_idx"], c["normalized_pattern"])] += 1
    assert seen[("r1", 5, "X")] == 1
```

---

## 6. Ожидаемые результаты

| subtype | full | dedup | Notes |
|---|---|---|---|
| A | ~31 193 | <31 193 | |
| B | ~69 023 | <69 023 | |
| E1 | ~133 088 | <133 088 | без exit_status |
| E2 | ~84 045 | <84 045 | без exit_status |
| ALL | ~317 349 | <317 349 | объединение |

---

<sub-instruction>

**ПЛАН РЕАЛИЗАЦИИ TZ_8.2:**

**Шаг 1:** Показать план. Ждать аппрува.

**Шаг 2:** Скопировать error classification functions + написать 4 теста на matches_A/B/E. Показать код + тесты.

**Шаг 3:** parser.py — главный цикл по траекториям. Показать код.

**Шаг 4:** Добавить compute_stats + сохранение 10 вариаций. Показать код.

**Шаг 5:** Тесты (5 тестов). Показать результат.

**Шаг 6:** Демо на 1000 траекторий (shard 0, subtype A) → показать stats.json.

**Шаг 7:** Полный запуск на всех 80 036 траекториях → показать сводку.

**Принцип:** Один этап → его тесты → следующий. Не писать всё сразу.

</sub-instruction>