# TZ_8.1 — Схемы данных, утилиты, логирование

> **Назначение:** Базовые модули, от которых зависят все остальные фазы. Без них невозможны ни парсеры, ни исследования.
>
> **Результат:** `work/MAS_errors/schemas.py`, `work/MAS_errors/utils.py`, `work/MAS_errors/setup_logging.py`, `tests/`

---

## 1. Структура файлов

```
work/MAS_errors/
├── __init__.py                  ← пустой (пакет)
├── schemas.py                   ← ErrorRecord, ErrorStats, StudyResult, StudySpec
├── utils.py                    ← data_hash, wilson_ci, filter_subgroup, get_subgroups
├── setup_logging.py            ← setup_logging() — настройка LOG.txt
├── tests/
│   ├── __init__.py
│   ├── test_schemas.py
│   ├── test_utils.py
│   └── test_wilson_ci.py
└── catalog.py                  ← каноническая таксономия (хардкод)
```

---

## 2. schemas.py

### 2.1. ErrorRecord

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ErrorRecord:
    """Единая запись об одной ошибке. immutable для безопасности."""
    
    # Идентификация
    error_id: str                           # f"{dataset}_{error_type}_{instance_id}_{step_idx}"
    dataset: str                            # "nebius", "trail", "agentRx", "who_and_when"
    error_type: str                        # "invalid_invocation", "orchestration_failure"
    error_subtype: Optional[str]            # "A","B","E1","E2" для nebius; None для остальных
    is_dedup: bool                         # True = дедуплицировано (nebius only)
    
    # Траектория
    instance_id: str
    traj_idx: int                          # индекс траектории
    step_idx: int                          # номер шага с ошибкой (0-based)
    chars_before_error: int                 # len(text)累积 до шага с ошибкой
    traj_total_chars: int                  # полная длина траектории в символах
    traj_total_steps: int                  # общее число шагов
    
    # nebius-специфика
    target: Optional[bool]                 # True/False (только nebius)
    exit_group: Optional[str]              # "success", "limit_hit", "failed" (только nebius)
    exit_status: Optional[str]             # точное значение exit_status
    
    # Ошибка
    error_text: str                        # оригинальный текст
    normalized_pattern: Optional[str]     # нормализованный паттерн
    occurrence_in_traj: Optional[int]     # номер вхождения (1,2,3...) для nebius
```

### 2.2. ErrorStats

```python
@dataclass(frozen=True)
class ErrorStats:
    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool
    
    # Счётчики
    n_errors: int
    n_trajectories_total: int
    n_trajectories_with_error: int         # уникальных instance_id с ошибкой
    
    # Вероятности
    p_trajectory: float
    p_trajectory_ci_lower: float            # Wilson 95% CI
    p_trajectory_ci_upper: float
    
    p_per_step: float                      # n_errors / sum(traj_total_steps)
    step_mean: float
    step_median: float
    step_std: float
    
    chars_mean: Optional[float]
    chars_median: Optional[float]
    
    # nebius subgroups
    target_true_n: Optional[int]
    target_false_n: Optional[int]
    exit_success_n: Optional[int]
    exit_limit_hit_n: Optional[int]
    exit_failed_n: Optional[int]
    
    # Meta
    data_hash: str
    parser_version: str
```

### 2.3. StudySpec и StudyResult

```python
@dataclass(frozen=True)
class StudySpec:
    """Спецификация одного исследования. frozen = immutable."""
    study_id: str
    parquet_path: str                      # путь к errors.parquet
    
    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool
    subgroup: Optional[str]                # "all", "success_targetT", etc.
    analysis_var: str                      # "step_idx" или "chars_before_error"


@dataclass
class StudyResult:
    study_id: str
    dataset: str
    error_type: str
    error_subtype: Optional[str]
    is_dedup: bool
    subgroup: Optional[str]
    analysis_var: str
    n_errors: int
    
    status: str                            # "ACCEPT" / "REJECT" / "UNDERPOWERED" / "ERROR"
    final_dist: Optional[str]
    p_final: Optional[float]
    D_obs: Optional[float]
    
    n_attempts: int
    attempts_log: list = field(default_factory=list)
    
    duration_s: float
    data_hash: str
```

---

## 3. utils.py

### 3.1. data_hash — SHA-256 от массива

```python
import hashlib
import numpy as np


def data_hash(arr: np.ndarray | list) -> str:
    """SHA-256 хэш массива. Для проверки изменились ли данные."""
    if isinstance(arr, list):
        arr = np.array(arr, dtype=np.float64)
    arr = np.asarray(arr, dtype=np.float64)
    return hashlib.sha256(arr.tobytes()).hexdigest()
```

### 3.2. wilson_ci — Wilson confidence interval

```python
from typing import Tuple
import math


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float, float]:
    """
    Wilson confidence interval для доли.
    
    k = число успехов (траекторий с ошибкой)
    n = общее число траекторий
    alpha = уровень значимости (0.05 = 95% CI)
    
    Returns: (p_hat, lower, upper)
    
    Формула:
        z²/2n
        center = (k + z²/2n) / (n + z²)
        half_width = z * sqrt(k*(n-k)/n³ + z²/4n²)
        adjusted_n = n + z²
    """
    if n == 0:
        return 0.0, 0.0, 0.0
    
    z = 1.960  # ~1.95996 для 95%
    p_hat = k / n
    
    adjusted_n = n + z**2
    center = (k + z**2 / 2) / adjusted_n
    half_width = z * math.sqrt((k * (n - k)) / (n**3) + (z**2) / (4 * n**2))
    
    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)
    
    return p_hat, lower, upper
```

### 3.3. filter_subgroup — фильтрация по nebius subgroup

```python
import pandas as pd


# nebius exit_status → exit_group mapping
EXIT_GROUP_MAP = {
    "submitted": "success",
    "submitted (exit_context)": "limit_hit",
    "exit_context": "limit_hit",
    "early_exit": "failed",
    "submitted_no_patch": "failed",
    "exit_format": "failed",
}


def filter_subgroup(df: pd.DataFrame, subgroup: str) -> pd.DataFrame:
    """
    Фильтрует errors.parquet по subgroup.
    
    subgroup variants:
      "all"                    → все строки
      "success_targetT"        → exit_group=success AND target=True
      "success_targetF"        → exit_group=success AND target=False
      "limit_hit"              → exit_group=limit_hit
      "failed"                 → exit_group=failed
    """
    if subgroup == "all":
        return df
    
    if subgroup == "success_targetT":
        return df[(df["exit_group"] == "success") & (df["target"] == True)]
    if subgroup == "success_targetF":
        return df[(df["exit_group"] == "success") & (df["target"] == False)]
    if subgroup == "limit_hit":
        return df[df["exit_group"] == "limit_hit"]
    if subgroup == "failed":
        return df[df["exit_group"] == "failed"]
    
    raise ValueError(f"Unknown subgroup: {subgroup}")


def get_subgroups(df: pd.DataFrame) -> list[str]:
    """
    Возвращает список доступных subgroups в parquet.
    Для nebius — из данных. Для остальных — только ['all'].
    """
    if "exit_group" not in df.columns:
        return ["all"]
    
    subgroups = []
    if len(df[df["exit_group"] == "success"]) > 0:
        subgroups.append("success_targetT")
        subgroups.append("success_targetF")
    if len(df[df["exit_group"] == "limit_hit"]) > 0:
        subgroups.append("limit_hit")
    if len(df[df["exit_group"] == "failed"]) > 0:
        subgroups.append("failed")
    
    if not subgroups:
        return ["all"]
    
    return subgroups
```

### 3.4. to_parquet / from_parquet

```python
import pandas as pd
from typing import List
from .schemas import ErrorRecord


def records_to_df(records: List[ErrorRecord]) -> pd.DataFrame:
    """Конвертирует список ErrorRecord в DataFrame для сохранения в parquet."""
    rows = []
    for r in records:
        rows.append({
            "error_id": r.error_id,
            "dataset": r.dataset,
            "error_type": r.error_type,
            "error_subtype": r.error_subtype,
            "is_dedup": r.is_dedup,
            "instance_id": r.instance_id,
            "traj_idx": r.traj_idx,
            "step_idx": r.step_idx,
            "chars_before_error": r.chars_before_error,
            "traj_total_chars": r.traj_total_chars,
            "traj_total_steps": r.traj_total_steps,
            "target": r.target,
            "exit_group": r.exit_group,
            "exit_status": r.exit_status,
            "error_text": r.error_text,
            "normalized_pattern": r.normalized_pattern,
            "occurrence_in_traj": r.occurrence_in_traj,
        })
    return pd.DataFrame(rows)


def df_to_records(df: pd.DataFrame) -> List[ErrorRecord]:
    """Конвертирует DataFrame обратно в список ErrorRecord."""
    records = []
    for _, row in df.iterrows():
        records.append(ErrorRecord(
            error_id=str(row["error_id"]),
            dataset=str(row["dataset"]),
            error_type=str(row["error_type"]),
            error_subtype=str(row["error_subtype"]) if pd.notna(row["error_subtype"]) else None,
            is_dedup=bool(row["is_dedup"]),
            instance_id=str(row["instance_id"]),
            traj_idx=int(row["traj_idx"]),
            step_idx=int(row["step_idx"]),
            chars_before_error=int(row["chars_before_error"]),
            traj_total_chars=int(row["traj_total_chars"]),
            traj_total_steps=int(row["traj_total_steps"]),
            target=bool(row["target"]) if pd.notna(row["target"]) else None,
            exit_group=str(row["exit_group"]) if pd.notna(row["exit_group"]) else None,
            exit_status=str(row["exit_status"]) if pd.notna(row["exit_status"]) else None,
            error_text=str(row["error_text"]),
            normalized_pattern=str(row["normalized_pattern"]) if pd.notna(row["normalized_pattern"]) else None,
            occurrence_in_traj=int(row["occurrence_in_traj"]) if pd.notna(row["occurrence_in_traj"]) else None,
        ))
    return records
```

---

## 4. setup_logging.py

```python
import logging
import os
from pathlib import Path


def setup_logging(log_path: str = "work/MAS_errors/LOG.txt") -> logging.Logger:
    """
    Настраивает логирование в LOG.txt.
    Каждая запись: timestamp PID [study_id] message
    """
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    
    # File handler — все уровни
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s PID%(process)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    
    # Root logger
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(file_handler)
    
    logger = logging.getLogger("MAS_errors")
    return logger
```

---

## 5. catalog.py — каноническая таксономия

```python
"""
Каноническая таксономия ошибок. Хардкодится в коде, не выводится из данных.
Формат: {dataset}: {error_type} → {error_subtypes}
"""

DATASETS = [
    "nebius",
    "trail",
    "agentRx",
    "who_and_when",
]

ERROR_TYPES = {
    "nebius": [
        ("invalid_invocation_A",        "A"),
        ("invalid_invocation_B",        "B"),
        ("invalid_invocation_E1",       "E1"),
        ("invalid_invocation_E2",        "E2"),
        ("invalid_invocation_ALL",        None),  # None = все подтипы
    ],
    "trail": [
        ("instruction_noncompliance",     None),
        ("formatting_errors",            None),
        ("context_handling_failures",    None),
        ("resource_abuse",              None),
        ("poor_information_retrieval",   None),
        ("incorrect_problem_identification", None),
        ("language_only",               None),
        ("tool_related",                None),
        ("task_orchestration",          None),
        ("goal_deviation",              None),
    ],
    "agentRx": {
        "magentic_one": [
            ("instruction_adherence_failure",  None),
            ("guardrails_triggered",           None),
            ("misinterpretation_of_tool_output", None),
            ("intent_not_supported",            None),
            ("intent_plan_misalignment",        None),
            ("invention_of_new_information",    None),
        ],
        "tau_retail": [
            ("instruction_adherence_failure",   None),
            ("intent_not_supported",           None),
            ("intent_plan_misalignment",       None),
            ("misinterpretation_of_tool_output", None),
            ("system_failure",                 None),
        ],
    },
    "who_and_when": [
        ("wrong_reasoning",             None),
        ("processing_error",            None),
        ("tool_failure",                None),
    ],
}
```

---

## 6. tests/

### test_schemas.py

```python
import pytest
import pandas as pd
from work.MAS_errors.schemas import ErrorRecord
from work.MAS_errors.utils import records_to_df, df_to_records, data_hash
import numpy as np


def test_error_record_immutable():
    """ErrorRecord должен быть frozen (immutable)."""
    r = ErrorRecord(
        error_id="nebius_inv_001", dataset="nebius",
        error_type="invalid_invocation", error_subtype="A",
        is_dedup=False, instance_id="repo-1", traj_idx=0,
        step_idx=5, chars_before_error=1000, traj_total_chars=5000,
        traj_total_steps=10, target=True, exit_group="success",
        exit_status="submitted", error_text="FileNotFoundError",
        normalized_pattern="FileNotFoundError", occurrence_in_traj=1,
    )
    with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
        r.step_idx = 99


def test_records_to_df_roundtrip():
    """ErrorRecord → DataFrame → ErrorRecord: все поля совпадают."""
    records = [
        ErrorRecord(
            error_id="test_1", dataset="nebius",
            error_type="invalid_invocation", error_subtype="A",
            is_dedup=False, instance_id="r1", traj_idx=0,
            step_idx=5, chars_before_error=1000, traj_total_chars=5000,
            traj_total_steps=10, target=True, exit_group="success",
            exit_status="submitted", error_text="err", normalized_pattern="p",
            occurrence_in_traj=1,
        ),
        ErrorRecord(
            error_id="test_2", dataset="nebius",
            error_type="invalid_invocation", error_subtype="A",
            is_dedup=True, instance_id="r1", traj_idx=0,
            step_idx=5, chars_before_error=1000, traj_total_chars=5000,
            traj_total_steps=10, target=True, exit_group="success",
            exit_status="submitted", error_text="err", normalized_pattern="p",
            occurrence_in_traj=1,
        ),
    ]
    
    df = records_to_df(records)
    back = df_to_records(df)
    
    assert len(back) == 2
    assert back[0].error_id == "test_1"
    assert back[0].is_dedup == False
    assert back[1].is_dedup == True
    assert back[0].error_subtype == "A"
    assert back[1].error_subtype == "A"


def test_data_hash_deterministic():
    """data_hash должен быть детерминирован — одинаковый массив → одинаковый хэш."""
    arr = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    h1 = data_hash(arr)
    h2 = data_hash(arr)
    h3 = data_hash([1.0, 2.0, 3.0, 4.0, 5.0])  # list input
    
    assert h1 == h2 == h3
    assert len(h1) == 64  # SHA-256 = 64 hex chars
```

### test_wilson_ci.py

```python
import pytest
from work.MAS_errors.utils import wilson_ci


def test_wilson_ci_basic():
    """k=50, n=100 → p≈0.5, CI не выходит за [0,1]."""
    p, lo, hi = wilson_ci(50, 100)
    assert 0.0 <= lo < p < hi <= 1.0
    assert lo < 0.5 < hi


def test_wilson_ci_edge_zero():
    """k=0, n=100 → lower=0, upper>0."""
    p, lo, hi = wilson_ci(0, 100)
    assert p == 0.0
    assert lo == 0.0
    assert hi > 0.0
    assert hi < 0.1


def test_wilson_ci_edge_full():
    """k=100, n=100 → p=1.0, lower<1.0, upper=1.0."""
    p, lo, hi = wilson_ci(100, 100)
    assert p == 1.0
    assert lo < 1.0
    assert hi == 1.0


def test_wilson_ci_n_zero():
    """n=0 → все нули."""
    p, lo, hi = wilson_ci(0, 0)
    assert p == lo == hi == 0.0
```

### test_utils.py

```python
import pytest
import pandas as pd
from work.MAS_errors.utils import filter_subgroup, get_subgroups


@pytest.fixture
def nebius_df():
    """Симулированный parquet для nebius."""
    return pd.DataFrame({
        "exit_group": ["success", "success", "success", "limit_hit", "failed", "success"],
        "target":     [True,       False,      True,       None,        None,      None],
        "step_idx":   [5,          10,        3,         15,         20,        8],
    })


def test_filter_all(nebius_df):
    df = filter_subgroup(nebius_df, "all")
    assert len(df) == 6


def test_filter_success_targetT(nebius_df):
    df = filter_subgroup(nebius_df, "success_targetT")
    assert len(df) == 2  # строки 0 и 2


def test_filter_success_targetF(nebius_df):
    df = filter_subgroup(nebius_df, "success_targetF")
    assert len(df) == 1  # строка 1


def test_filter_limit_hit(nebius_df):
    df = filter_subgroup(nebius_df, "limit_hit")
    assert len(df) == 1  # строка 3


def test_filter_failed(nebius_df):
    df = filter_subgroup(nebius_df, "failed")
    assert len(df) == 1  # строка 4


def test_filter_unknown_raises(nebius_df):
    with pytest.raises(ValueError, match="Unknown subgroup"):
        filter_subgroup(nebius_df, "unknown_subgroup")


def test_get_subgroups_nebius(nebius_df):
    subs = get_subgroups(nebius_df)
    assert "success_targetT" in subs
    assert "success_targetF" in subs
    assert "limit_hit" in subs
    assert "failed" in subs


def test_get_subgroups_other_dataset():
    """Для датасетов без exit_group — только 'all'."""
    df = pd.DataFrame({"step_idx": [1, 2, 3]})
    subs = get_subgroups(df)
    assert subs == ["all"]
```

---

<sub-instruction>

**ПЛАН РЕАЛИЗАЦИИ TZ_8.1:**

**Шаг 1:** Показать мне план файлов:
```
work/MAS_errors/
├── __init__.py
├── schemas.py
├── utils.py
├── setup_logging.py
├── catalog.py
└── tests/
    ├── __init__.py
    ├── test_schemas.py
    ├── test_wilson_ci.py
    └── test_utils.py
```
Ждать аппрува.

**Шаг 2:** Написать файлы по одному. После каждого файла — показать diff / листинг. Не переходить к следующему, пока не показан текущий.

**Шаг 3:** Запустить тесты:
```bash
cd work/MAS_errors && python -m pytest tests/ -v
```
Показать output. Если есть FAIL — исправить.

**Шаг 4:** Показать summary: "TZ_8.1 реализован. 3 файла, 3 теста, N passed."

**Принципы:**
- Один файл → его тесты → следующий
- Не писать всё сразу
- Каждый тест проверяет ОДНО конкретное поведение
- Ошибка в тесте = остановиться и исправить
</sub-instruction>




# TZ_8.1 — Addendum: исправления

## 1. catalog.py — единая структура

Заменить секцию `ERROR_TYPES` на:

```python
ERROR_TYPES: dict[str, dict[str, list[tuple[str, str | None]]]] = {
    # dataset → variant → list of (error_type, error_subtype)
    # variant="" для datasets без вариантов
    "nebius": {
        "": [
            ("invalid_invocation_A",   "A"),
            ("invalid_invocation_B",    "B"),
            ("invalid_invocation_E1",   "E1"),
            ("invalid_invocation_E2",  "E2"),
            ("invalid_invocation_ALL",   None),
        ],
    },
    "trail": {
        "": [
            ("instruction_noncompliance",          None),
            ("formatting_errors",                  None),
            ("context_handling_failures",          None),
            ("resource_abuse",                    None),
            ("poor_information_retrieval",        None),
            ("incorrect_problem_identification",  None),
            ("language_only",                     None),
            ("tool_related",                      None),
            ("task_orchestration",                 None),
            ("goal_deviation",                    None),
        ],
    },
    "agentRx": {
        "magentic_one": [
            ("instruction_adherence_failure",            None),
            ("guardrails_triggered",                       None),
            ("misinterpretation_of_tool_output",          None),
            ("intent_not_supported",                       None),
            ("intent_plan_misalignment",                  None),
            ("invention_of_new_information",              None),
        ],
        "tau_retail": [
            ("instruction_adherence_failure",             None),
            ("intent_not_supported",                       None),
            ("intent_plan_misalignment",                  None),
            ("misinterpretation_of_tool_output",           None),
            ("system_failure",                            None),
        ],
    },
    "who_and_when": {
        "": [
            ("wrong_reasoning",   None),
            ("processing_error",  None),
            ("tool_failure",      None),
        ],
    },
}
```

## 2. Добавить тест `wilson_ci` с малым n

В `test_wilson_ci.py`:

```python
def test_wilson_ci_small_n():
    """k=5, n=10 — малые выборки, Wilson должен давать разумные CI."""
    p, lo, hi = wilson_ci(5, 10)
    assert 0.0 <= lo < p < hi <= 1.0
    # CI должен быть шире чем при большом n
    assert (hi - lo) > 0.3  # ~0.38 для 95% CI при n=10


def test_wilson_ci_unequal():
    """k=1, n=20 — сильно несбалансированная выборка."""
    p, lo, hi = wilson_ci(1, 20)
    assert 0.0 <= lo < p < hi <= 1.0
    assert p == 0.05  # 1/20
    assert lo < 0.05 < hi  # CI содержит истинную долю
```

## 3. Добавить тест `get_subgroups` для пустого df

В `test_utils.py`:

```python
def test_get_subgroups_empty():
    """Пустой DataFrame → только 'all'."""
    df = pd.DataFrame({"exit_group": [], "target": []})
    subs = get_subgroups(df)
    assert subs == ["all"]


def test_get_subgroups_partial_target():
    """success + target=False, но нет target=True → empty study."""
    df = pd.DataFrame({
        "exit_group": ["success", "success"],
        "target":     [False, False],
        "step_idx":   [1, 2],
    })
    subs = get_subgroups(df)
    # get_subgroups вернёт оба, но filter_subgroup для targetT даст пустой df
    assert "success_targetT" in subs
    assert "success_targetF" in subs
    # Исследование будет пустым → scale_selector вернёт UNDERPOWERED
```

## 4. Добавить тест `data_hash` — разные входы

В `test_schemas.py`:

```python
def test_data_hash_different_arrays():
    """Разные массивы → разные хэши."""
    h1 = data_hash([1.0, 2.0, 3.0])
    h2 = data_hash([1.0, 2.0, 4.0])
    h3 = data_hash([1.0, 2.0])
    
    assert h1 != h2 != h3
    assert h1 != data_hash([3.0, 2.0, 1.0])  # порядок важен


def test_data_hash_empty():
    """Пустой массив → валидный хэш."""
    h = data_hash([])
    assert len(h) == 64
```

---

<sub-instruction>

**ПЛАН: реализация TZ_8.1**

Показать дерево файлов → ждать аппрува → написать файлы по одному → тесты → summary.

</sub-instruction>