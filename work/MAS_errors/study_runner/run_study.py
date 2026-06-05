"""Запуск одного исследования: Fit_Everything → validate."""

from __future__ import annotations

import sys
import time
import json
from pathlib import Path

import numpy as np
import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2] / ".."
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from work.MAS_errors.schemas import StudySpec, StudyResult
from work.MAS_errors.utils import filter_subgroup, data_hash
from work.MAS_errors.setup_logging import setup_logging


# Типы распределений для Fit_Everything
DISTRIBUTIONS = ["W2", "W3", "LN2", "G2", "LL2", "E1", "E2", "N", "GU"]

# Параметры валидации
EPSILON = 0.03
ALPHA = 0.05
POWER = 0.80
B_DEFAULT = 1000


def run_study(spec: StudySpec, fast: bool = False, B: int | None = None) -> StudyResult:
    """Запустить одно исследование: Fit_Everything → validate для каждого dist."""

    logger = setup_logging()
    start = time.monotonic()

    # 1. Загрузить parquet
    df = pd.read_parquet(spec.parquet_path)
    df = filter_subgroup(df, spec.subgroup)

    # 2. Извлечь анализируемую переменную
    if spec.analysis_var not in df.columns:
        return _error_result(spec, "MISSING_COLUMN", start)

    X = df[spec.analysis_var].dropna().values
    N = len(X)

    if N == 0:
        return _error_result(spec, "NO_DATA", start)

    # 3. Fit_Everything цикл
    B = B if B is not None else (500 if fast else B_DEFAULT)

    # Импорт здесь — избегаем circular imports
    import work.scripts.distribution_validator.main as dv_main
    from work.scripts.distribution_validator import validate as validate_module

    attempts_log: list[dict] = []
    final_result: validate_module.ValidationResult | None = None
    final_dist_type: str | None = None

    for dist_type in DISTRIBUTIONS:
        try:
            val_result, _, _ = dv_main.main(
                X=X,
                dist_type=dist_type,
                epsilon=EPSILON,
                alpha=ALPHA,
                power=POWER,
                do_split=True,
                B=B,
                seed=42,
                data_hash=None,
                save_artefacts=False,
            )

            attempt = {
                "dist": dist_type,
                "verdict": val_result.verdict,
                "p": val_result.p_final,
                "D_obs": val_result.D_obs,
                "branch": val_result.branch,
            }
            attempts_log.append(attempt)

            if val_result.verdict == "ACCEPT":
                final_result = val_result
                final_dist_type = dist_type
                break
            elif val_result.verdict == "UNDERPOWERED":
                continue
        except Exception as e:
            logger.error(f"Distribution {dist_type} failed: {e}")
            attempts_log.append({
                "dist": dist_type,
                "verdict": "ERROR",
                "error": str(e),
            })

    # 4. Определить финальный результат
    if final_result:
        verdict = "ACCEPT"
        best_dist = final_result.dist_type
        p_final = final_result.p_final
        D_obs = final_result.D_obs
    else:
        valid = [a for a in attempts_log if a.get("verdict") in ("REJECT", "REJECT_EQUIVALENCE")]
        if valid:
            best = max(valid, key=lambda a: a.get("p") or 0)
            verdict = best["verdict"]
            best_dist = best["dist"]
            p_final = best.get("p")
            D_obs = best.get("D_obs")
            final_dist_type = best_dist
        elif attempts_log:
            verdict = attempts_log[-1]["verdict"]
            best_dist = attempts_log[-1].get("dist")
            p_final = attempts_log[-1].get("p")
            D_obs = attempts_log[-1].get("D_obs")
            final_dist_type = best_dist
        else:
            verdict = "ERROR"
            best_dist = None
            p_final = None
            D_obs = None
            final_dist_type = None

    # 5. Один финальный вызов с save_artefacts=True для победителя
    if final_dist_type and verdict not in ("ERROR", "NO_DATA", "MISSING_COLUMN"):
        parts = [spec.dataset, spec.error_type]
        if spec.error_subtype:
            parts.append(spec.error_subtype)
        if spec.is_dedup:
            parts.append("dedup")
        if spec.subgroup and spec.subgroup != "all":
            parts.append(spec.subgroup)
        parts.append(spec.analysis_var)
        study_label = " · ".join(parts)
        try:
            dv_main.main(
                X=X,
                dist_type=final_dist_type,
                epsilon=EPSILON,
                alpha=ALPHA,
                power=POWER,
                do_split=True,
                B=B,
                seed=42,
                data_hash=None,
                save_artefacts=True,
                study_label=study_label,
            )
        except Exception as e:
            logger.warning(f"Final artefact save failed for {final_dist_type}: {e}")

    return StudyResult(
        study_id=spec.study_id,
        dataset=spec.dataset,
        error_type=spec.error_type,
        error_subtype=spec.error_subtype,
        is_dedup=spec.is_dedup,
        subgroup=spec.subgroup,
        analysis_var=spec.analysis_var,
        n_errors=N,
        status=verdict,
        final_dist=best_dist,
        p_final=p_final,
        D_obs=D_obs,
        n_attempts=len(attempts_log),
        attempts_log=attempts_log,
        duration_s=time.monotonic() - start,
        data_hash=data_hash(X),
    )


def _error_result(spec: StudySpec, status: str, start: float) -> StudyResult:
    """Результат при ошибке выполнения."""
    return StudyResult(
        study_id=spec.study_id,
        dataset=spec.dataset,
        error_type=spec.error_type,
        error_subtype=spec.error_subtype,
        is_dedup=spec.is_dedup,
        subgroup=spec.subgroup,
        analysis_var=spec.analysis_var,
        n_errors=0,
        status=status,
        final_dist=None,
        p_final=None,
        D_obs=None,
        n_attempts=0,
        attempts_log=[],
        duration_s=time.monotonic() - start,
        data_hash="",
    )


def save_artefacts(spec: StudySpec, result: StudyResult) -> None:
    """Сохранить артефакты исследования."""

    artefact_dir = Path(spec.parquet_path).parent / spec.study_id
    artefact_dir.mkdir(parents=True, exist_ok=True)

    # fit_log.json
    fit_log = {
        "study_id": result.study_id,
        "verdict": result.status,
        "best_dist": result.final_dist,
        "p_final": result.p_final,
        "D_obs": result.D_obs,
        "n_errors": result.n_errors,
        "n_attempts": result.n_attempts,
        "attempts": result.attempts_log,
        "duration_s": result.duration_s,
        "data_hash": result.data_hash,
    }
    with open(artefact_dir / "fit_log.json", "w") as f:
        json.dump(fit_log, f, indent=2)

    # audit_report.md
    md_content = f"""# Audit Report: {result.study_id}

**Dataset:** {result.dataset}
**Error Type:** {result.error_type}
**Error Subtype:** {result.error_subtype or 'N/A'}
**Subgroup:** {result.subgroup}
**Analysis Variable:** {result.analysis_var}
**De-duplicated:** {result.is_dedup}

---

**Status:** {result.status}
**Best Distribution:** {result.final_dist or 'N/A'}
**p-value:** {f'{result.p_final:.4f}' if result.p_final is not None else 'N/A'}
**D-statistic:** {f'{result.D_obs:.4f}' if result.D_obs is not None else 'N/A'}
**Errors:** {result.n_errors}
**Attempts:** {result.n_attempts}
**Duration:** {result.duration_s:.1f}s

---

## Attempts Log

"""
    for attempt in result.attempts_log:
        verdict = attempt.get("verdict", "UNKNOWN")
        dist = attempt.get("dist", "N/A")
        p = attempt.get("p")
        D = attempt.get("D_obs")
        branch = attempt.get("branch", "")

        p_str = f"p={p:.4f}" if p is not None else "p=N/A"
        D_str = f"D={D:.4f}" if D is not None else "D=N/A"

        if "error" in attempt:
            md_content += f"- **{dist}:** ERROR — {attempt['error']}\n"
        else:
            md_content += f"- **{dist}:** {verdict} ({p_str}, {D_str}) [{branch}]\n"

    with open(artefact_dir / "audit_report.md", "w") as f:
        f.write(md_content)