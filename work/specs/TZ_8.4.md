

# TZ_8.4 — Study Runner: запуск исследований

> **Назначение:** Сгенерировать список всех исследований из выхода парсеров → запустить `distribution_validator` на каждом → собрать результаты в `results.csv`.
>
> **Зависимость:** TZ_7 (distribution_validator) должен быть реализован.
>
> **Принцип:** Один study → один вызов `distribution_validator` → одна строка в results.csv.

---

## 1. Структура

```
work/MAS_errors/
├── LOG.txt
├── results.csv                    ← единый CSV со всеми результатами
├── study_list.csv                ← все исследования (data-driven)
│
├── studies/
│   ├── run_all.py                ← главная точка входа (Command 2)
│   ├── generate_study_list.py    ← сканирует parsers/ → список StudySpec
│   ├── run_study.py              ← одно исследование
│   ├── tests/
│   │   ├── test_study_list.py
│   │   └── test_run_study.py
│   ├── nebius/
│   │   ├── invalid_invocation/
│   │   │   ├── A/
│   │   │   │   ├── step_idx/     ← результат: fit_log.json, audit_report.md
│   │   │   │   └── chars_before_error/
│   │   │   ├── A_dedup/
│   │   │   │   ├── step_idx/
│   │   │   │   └── chars_before_error/
│   │   │   └── ...
│   │   └── ... (все ошибки nebius)
│   └── trail/
│       └── instruction_noncompliance/
│           └── step_idx/
```

---

## 2. generate_study_list.py

### 2.1. Логика

```python
def scan_parsers_output() -> list[StudySpec]:
    """
    Сканирует work/MAS_errors/parsers/.
    Для каждого {dataset}/{error_type}/errors.parquet:
      1. Читает parquet → определяет доступные subgroups
      2. Определяет доступные analysis_var (шаг 0)
      3. Определяет is_dedup из пути (A_dedup → True, A → False)
      4. Создаёт StudySpec на каждый subgroup × analysis_var
    """
```

**Шаг 0 — какие переменные анализа доступны:**

| Датасет | step_idx | chars_before_error |
|---|---|---|
| nebius | ✅ | ✅ |
| TRAIL | ⚠️ все = 0 | ❌ |
| AgentRx | ✅ | ❌ |
| Who_and_When | ✅ | ❌ |

TRAIL: `step_idx=0` для всех записей → распределение вырождено. Но мы всё равно запускаем — пусть `distribution_validator` вернёт свой вердикт (скорее всего UNDERPOWERED).

**Шаг 1 — subgroups:**

```python
# nebius: из данных (success_targetT, success_targetF, limit_hit, failed, all)
# TRAIL: ["all"]
# AgentRx: ["all"]
# Who_and_When: ["all"]
```

**Шаг 2 — is_dedup:**

```python
# Из пути: "A/" → is_dedup=False, "A_dedup/" → is_dedup=True
# Остальные датасеты: всегда False
```

**Шаг 3 — StudySpec:**

```python
def make_spec(
    dataset: str,
    error_type: str,
    error_subtype: str | None,
    is_dedup: bool,
    subgroup: str,
    analysis_var: str,
    parquet_path: str,
) -> StudySpec:
    study_id = (
        f"{dataset}"
        f"_{error_type}"
        f"{'_' + error_subtype if error_subtype else ''}"
        f"{'_dedup' if is_dedup else ''}"
        f"_{subgroup}"
        f"_{analysis_var}"
    )
    return StudySpec(
        study_id=study_id,
        parquet_path=parquet_path,
        dataset=dataset,
        error_type=error_type,
        error_subtype=error_subtype,
        is_dedup=is_dedup,
        subgroup=subgroup,
        analysis_var=analysis_var,
    )
```

**Подсчёт ожидаемого числа исследований:**

| Датасет | error_types | subgroups | vars | dedup | Studies |
|---|---|---|---|---|---|
| nebius invalid_invocation | 5 (A/B/E1/E2/ALL) | 5 | 2 | 2 | **100** |
| TRAIL | 20 | 1 | 1 | 1 | 20 |
| AgentRx magentic_one | 7 | 1 | 1 | 1 | 7 |
| AgentRx tau_retail | 5 | 1 | 1 | 1 | 5 |
| Who_and_When | 3 | 1 | 1 | 1 | 3 |
| **Итого** | | | | | **~135** |

---

## 3. run_study.py

### 3.1. Константы

```python
EPSILON = 0.05       # инженерный допуск на отклонение CDF
ALPHA = 0.05         # уровень значимости
POWER = 0.80         # целевая мощность
```

### 3.2. Алгоритм

```python
import time
from work.MAS_errors.schemas import StudySpec, StudyResult
from work.MAS_errors.utils import filter_subgroup, records_to_df, data_hash
from work.MAS_errors.study_runner.distribution_validator import validate


def run_study(spec: StudySpec) -> StudyResult:
    start = time.monotonic()
    
    # 1. Загрузить parquet
    df = pd.read_parquet(spec.parquet_path)
    
    # 2. Фильтровать subgroup
    df = filter_subgroup(df, spec.subgroup)
    
    # 3. Извлечь анализируемую переменную
    X = df[spec.analysis_var].values
    N = len(X)
    
    if N == 0:
        return StudyResult(
            study_id=spec.study_id, dataset=spec.dataset,
            error_type=spec.error_type, error_subtype=spec.error_subtype,
            is_dedup=spec.is_dedup, subgroup=spec.subgroup,
            analysis_var=spec.analysis_var, n_errors=0,
            status="ERROR", final_dist=None, p_final=None, D_obs=None,
            n_attempts=0, attempts_log=[],
            duration_s=time.monotonic() - start,
            data_hash="",
        )
    
    # 4. Вызов distribution_validator (TZ_7)
    #    API: validate(X, dist_type, params, epsilon=EPSILON, alpha=ALPHA, power=POWER)
    #    Возвращает: (verdict, best_dist, p_final, D_obs, attempts_log)
    
    result = distribution_validator.validate_full(
        X=X,
        epsilon=EPSILON,
        alpha=ALPHA,
        power=POWER,
    )
    
    return StudyResult(
        study_id=spec.study_id,
        dataset=spec.dataset,
        error_type=spec.error_type,
        error_subtype=spec.error_subtype,
        is_dedup=spec.is_dedup,
        subgroup=spec.subgroup,
        analysis_var=spec.analysis_var,
        n_errors=N,
        status=result.verdict,
        final_dist=result.best_dist,
        p_final=result.p_final,
        D_obs=result.D_obs,
        n_attempts=result.n_attempts,
        attempts_log=result.attempts_log,
        duration_s=time.monotonic() - start,
        data_hash=data_hash(X),
    )
```

### 3.3. Добавление подпапки для сохранения артефактов

Каждый study сохраняет артефакты в свою папку:

```
{study_id}/
├── fit_log.json     ← Fit_Everything лог (JSON)
├── audit_report.md  ← markdown-отчёт с вердиктом
└── stats.png        ← CDF plot (опционально)
```

```python
def save_artefacts(spec: StudySpec, result: StudyResult) -> None:
    artefact_dir = Path(spec.parquet_path).parent / spec.study_id
    artefact_dir.mkdir(parents=True, exist_ok=True)
    
    # fit_log.json
    with open(artefact_dir / "fit_log.json", "w") as f:
        json.dump({
            "study_id": result.study_id,
            "verdict": result.status,
            "best_dist": result.final_dist,
            "p_final": result.p_final,
            "D_obs": result.D_obs,
            "n_attempts": result.n_attempts,
            "attempts": result.attempts_log,
        }, f, indent=2)
    
    # audit_report.md
    with open(artefact_dir / "audit_report.md", "w") as f:
        f.write(f"# Audit Report: {result.study_id}\n\n")
        f.write(f"**Status:** {result.status}\n\n")
        if result.final_dist:
            f.write(f"**Best Distribution:** {result.final_dist}\n\n")
            f.write(f"**p-value:** {result.p_final:.4f}\n\n")
            f.write(f"**D-statistic:** {result.D_obs:.4f}\n\n")
        f.write(f"**Errors:** {result.n_errors}\n\n")
        f.write(f"**Duration:** {result.duration_s:.1f}s\n\n")
        if result.attempts_log:
            f.write("## Attempts\n\n")
            for attempt in result.attempts_log:
                f.write(f"- {attempt['dist']}: {attempt['verdict']} "
                        f"(p={attempt.get('p', 'N/A')})\n")
```

---

## 4. run_all.py

```python
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd
import dataclasses
import logging
from tqdm import tqdm

from work.MAS_errors.schemas import StudyResult
from work.MAS_errors.study_runner.generate_study_list import scan_parsers_output
from work.MAS_errors.study_runner.run_study import run_study, save_artefacts
from work.MAS_errors.setup_logging import setup_logging


RESULTS_PATH = Path("work/MAS_errors/results.csv")
N_WORKERS = 12


def main():
    logger = setup_logging()
    logger.info("=== Study Runner started ===")
    
    # Очистить старый results.csv
    if RESULTS_PATH.exists():
        RESULTS_PATH.unlink()
    
    # 1. Сгенерировать список исследований
    logger.info("Generating study list...")
    studies = scan_parsers_output()
    logger.info(f"Total studies: {len(studies)}")
    
    # 2. Запустить все исследования
    results = []
    with ProcessPoolExecutor(max_workers=N_WORKERS) as executor:
        futures = {executor.submit(run_study, s): s for s in studies}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="Studies"):
            spec = futures[future]
            try:
                result = future.result()
            except Exception as e:
                logger.error(f"STUDY ERROR: {spec.study_id}: {e}", exc_info=True)
                result = StudyResult(
                    study_id=spec.study_id, dataset=spec.dataset,
                    error_type=spec.error_type, error_subtype=spec.error_subtype,
                    is_dedup=spec.is_dedup, subgroup=spec.subgroup,
                    analysis_var=spec.analysis_var, n_errors=0,
                    status="ERROR", final_dist=None, p_final=None, D_obs=None,
                    n_attempts=0, attempts_log=[],
                    duration_s=0.0, data_hash="",
                )
            
            results.append(result)
            save_artefacts(spec, result)
            
            # Атомарная запись в results.csv
            _append_to_csv(result, RESULTS_PATH)
    
    # 3. Summary
    statuses = pd.Series([r.status for r in results]).value_counts()
    logger.info(f"Results: {statuses.to_dict()}")
    
    logger.info("=== Study Runner finished ===")


def _append_to_csv(result: StudyResult, path: Path) -> None:
    """Атомарная запись: писать во временный файл, потом rename."""
    tmp_path = path.with_suffix(".tmp")
    row = dataclasses.asdict(result)
    
    import csv
    file_exists = path.exists()
    
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ROW_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)
    
    tmp_path.rename(path)  # atomic on POSIX


ROW_FIELDS = [
    "study_id", "dataset", "error_type", "error_subtype", "is_dedup",
    "subgroup", "analysis_var", "n_errors", "status", "final_dist",
    "p_final", "D_obs", "n_attempts", "duration_s", "data_hash",
]
```

---

## 5. distribution_validator API (интерфейс TZ_7)

TZ_8.4 вызывает `distribution_validator` из `TZ_7`. Необходимый API:

```python
@dataclass
class ValidationResult:
    verdict: str              # "ACCEPT" / "REJECT" / "UNDERPOWERED" / "ERROR"
    best_dist: str | None    # "W2", "LN3" etc.
    p_final: float | None
    D_obs: float | None
    n_attempts: int
    attempts_log: list[dict]  # [{"dist": str, "verdict": str, "p": float}, ...]


def validate_full(
    X: np.ndarray,
    epsilon: float = 0.05,
    alpha: float = 0.05,
    power: float = 0.80,
) -> ValidationResult:
    """
    Полный цикл: Fit_Everything → scale_selector → validate для каждого dist.
    Возвращает результат первого ACCEPT или финальный REJECT/UNDERPOWERED.
    """
```

**Если API TZ_7 отличается** — адаптировать вызов в `run_study.py`.

---

## 6. Тесты

### test_study_list.py

```python
def test_scan_parsers_finds_nebius():
    """scan_parsers_output возвращает исследования для nebius."""
    studies = scan_parsers_output()
    nebius = [s for s in studies if s.dataset == "nebius"]
    assert len(nebius) > 0

def test_study_id_unique():
    """Все study_id уникальны."""
    studies = scan_parsers_output()
    ids = [s.study_id for s in studies]
    assert len(ids) == len(set(ids))

def test_nebius_has_step_idx_and_chars():
    """nebius имеет оба analysis_var."""
    studies = scan_parsers_output()
    nebius = [s for s in studies if s.dataset == "nebius"]
    step_idx = [s for s in nebius if s.analysis_var == "step_idx"]
    chars = [s for s in nebius if s.analysis_var == "chars_before_error"]
    assert len(step_idx) > 0
    assert len(chars) > 0

def test_dedup_is_detected_from_path():
    """A_dedup → is_dedup=True."""
    studies = scan_parsers_output()
    nebius = [s for s in studies if s.dataset == "nebius"]
    dedup = [s for s in nebius if s.is_dedup]
    assert len(dedup) > 0

def test_other_datasets_no_dedup():
    """TRAIL/AgentRx/Who_and_When не имеют dedup."""
    studies = scan_parsers_output()
    others = [s for s in studies if s.dataset != "nebius"]
    assert all(not s.is_dedup for s in others)
```

### test_run_study.py

```python
def test_run_study_with_synthetic_data():
    """Синтетические данные из Weibull(10, 2) → ACCEPT."""
    from scipy.stats import weibull_min
    X = weibull_min(c=2, scale=10, loc=0).rvs(size=200)
    
    spec = StudySpec(
        study_id="test_weibull",
        parquet_path="",  # не используется, X передаётся напрямую
        dataset="test", error_type="test",
        error_subtype=None, is_dedup=False,
        subgroup="all", analysis_var="step_idx",
    )
    
    # Мок: перехватываем вызов distribution_validator
    # result = run_study_with_X(spec, X)
    # assert result.status in ("ACCEPT", "REJECT")  # не UNDERPOWERED при N=200
    pass  # требует мока distribution_validator

def test_run_study_empty_dataframe():
    """Пустой DataFrame → ERROR."""
    pass
```

---

## 7. Ожидаемые результаты

| Статус | Ожидание |
|---|---|
| nebius step_idx (full) | 50 studies: ~30–40% ACCEPT |
| nebius chars | 50 studies: ~30–40% ACCEPT |
| nebius dedup | 50 studies: аналогично |
| TRAIL | 20 studies: большинство UNDERPOWERED или ERROR (step_idx=0, мало данных) |
| AgentRx | 12 studies: UNDERPOWERED (мало данных, 44 и 29 траекторий) |
| Who_and_When | 3 studies: UNDERPOWERED (4 ошибки на 58 траекторий) |

**Оценка времени:** 135 исследований × 12 воркеров ≈ ~11 исследований одновременно. Каждое исследование: Fit_Everything (10 dist × 100 MC = 1000 операций) + 1–10 валидаций. Ожидаемое время: **10–30 минут** на полном прогоне.

---

<sub-instruction>

**ПЛАН РЕАЛИЗАЦИИ TZ_8.4:**

**Шаг 1:** Показать план. Ждать аппрува.

**Шаг 2:** Проверить API distribution_validator (прочитать TZ_7 или work/scripts/distribution_validator/). Показать мне точный интерфейс функции, которую нужно вызывать.

**Шаг 3:** generate_study_list.py — сканирование парсеров. Показать код + тесты.

**Шаг 4:** run_study.py — одно исследование. Показать код.

**Шаг 5:** run_all.py — оркестрация. Показать код.

**Шаг 6:** Тесты. Показать результат.

**Шаг 7:** Демо на 5 исследованиях nebius A → показать results.csv (5 строк) + 5 артефактов.

**Принцип:** Один этап → его тесты → следующий. Не писать всё сразу.

</sub-instruction>