from __future__ import annotations

import dataclasses
import json
import re
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
import pandas as pd

from work.MAS_errors.schemas import ErrorRecord, ErrorStats
from work.MAS_errors.utils import data_hash, records_to_df, wilson_ci

PROJECT_ROOT = Path(__file__).parents[4]
PARQUET_PATH = PROJECT_ROOT / "datasets" / "TRAIL" / "data" / "gaia-00000-of-00001-33a2e72d362d688a.parquet"
OUT_BASE = Path(__file__).parent

N_TOTAL = None  # определяется из данных: df["instance_id"].nunique()

CATEGORY_MAP = {
    "Instruction Non-compliance": "instruction_noncompliance",
    "Formatting Errors": "formatting_errors",
    "Context Handling Failure": "context_handling_failures",
    "Context Handling Failures": "context_handling_failures",
    "Resource Abuse": "resource_abuse",
    "Poor Information Retrieval": "poor_information_retrieval",
    "Incorrect Problem Identification": "incorrect_problem_identification",
    "Language-only": "language_only",
    "Language-only ": "language_only",
    "Tool-related": "tool_related",
    "Tool-related ": "tool_related",
    "Tool Output Misinterpretation": "tool_related",
    "Task Orchestration": "task_orchestration",
    "Goal Deviation": "goal_deviation",
}


def normalize_error_pattern(text: str) -> str:
    t = re.split(r"\(Open file:|\(Current directory:|bash-\$", text)[0]
    t = re.sub(r"'[^']{0,200}'", "'X'", t)
    t = re.sub(r'"[^"]{0,200}"', '"X"', t)
    t = re.sub(r"/[\w\-./]+", "/X", t)
    t = re.sub(r"\bline\s+\d+", "line N", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def _map_category(raw_cat: str) -> str:
    mapped = CATEGORY_MAP.get(raw_cat.strip())
    if mapped:
        return mapped
    return raw_cat.strip().lower().replace(" ", "_")


def flatten_spans(spans, counter=None, depth=0, max_depth=1000):
    """Recursively flatten spans including nested child_spans.

    Returns dict: {span_id: step_idx} in depth-first order.
    Uses global counter for correct step_idx across all spans.
    """
    if depth > max_depth:
        raise ValueError(f"max_depth={max_depth} exceeded in flatten_spans")
    if counter is None:
        counter = [0]
    result = {}
    for span in spans:
        counter[0] += 1
        sid = span.get("span_id")
        if sid:
            result[sid] = counter[0]
        children = span.get("child_spans", [])
        if children:
            child_result = flatten_spans(children, counter, depth + 1, max_depth)
            result.update(child_result)
    return result


def process_trajectories() -> tuple[dict[str, list[ErrorRecord]], int]:
    print("Загружаю TRAIL...")
    pf = pq.ParquetFile(str(PARQUET_PATH))
    t = pf.read().to_pydict()

    records_by_cat: dict[str, list[ErrorRecord]] = defaultdict(list)

    for row_idx, (trace_str, labels_str) in enumerate(zip(t["trace"], t["labels"])):
        trace_id = None
        trace_str_len = len(trace_str)

        try:
            trace = json.loads(trace_str)
            trace_id = trace.get("trace_id") or f"row_{row_idx}"
        except json.JSONDecodeError:
            trace_id = f"row_{row_idx}"

        try:
            labels = json.loads(labels_str)
        except json.JSONDecodeError:
            continue

        # Build span_id → step_idx mapping for this trace
        span_id_to_step = flatten_spans(trace.get("spans", []) if isinstance(trace, dict) else [])

        for err in labels.get("errors", []):
            raw_cat = err.get("category", "")
            cat = _map_category(raw_cat)
            err_location = err.get("location", "")
            step_idx = span_id_to_step.get(err_location, 0)

            record = ErrorRecord(
                error_id=f"trail_{trace_id}_{row_idx}_{len(records_by_cat.get(cat, []))}",
                dataset="trail",
                error_type=cat,
                error_subtype=None,
                is_dedup=False,
                instance_id=trace_id,
                traj_idx=row_idx,
                step_idx=step_idx,
                chars_before_error=0,
                traj_total_chars=trace_str_len,
                traj_total_steps=len(span_id_to_step),
                target=None,
                exit_group=None,
                exit_status=None,
                error_text=err.get("evidence", ""),
                normalized_pattern=normalize_error_pattern(err.get("evidence", "")),
                occurrence_in_traj=None,
            )
            records_by_cat[cat].append(record)

    # Count unique trace_ids from successfully parsed traces
    unique_trace_ids = set()
    for row_idx, trace_str in enumerate(t["trace"]):
        try:
            trace = json.loads(trace_str)
            tid = trace.get("trace_id")
            if tid:
                unique_trace_ids.add(tid)
            else:
                unique_trace_ids.add(f"row_{row_idx}")
        except json.JSONDecodeError:
            unique_trace_ids.add(f"row_{row_idx}")
    n_trajectories = len(unique_trace_ids)
    print(f"Загружено: {len(records_by_cat)} категорий, {n_trajectories} траекторий")
    return records_by_cat, n_trajectories


def compute_stats(df: pd.DataFrame, cat: str | None, is_dedup: bool, n_trajectories_total: int) -> ErrorStats:
    n_errors = len(df)
    n_with = df["instance_id"].nunique()

    p_raw = n_errors / n_with if n_with > 0 else 0.0

    if p_raw > 1.0:
        p_trajectory = 1.0
        ci_lo = None
        ci_hi = None
    else:
        p_trajectory, ci_lo, ci_hi = wilson_ci(n_errors, n_with)

    return ErrorStats(
        dataset="trail",
        error_type=cat,
        error_subtype=None,
        is_dedup=is_dedup,
        n_errors=n_errors,
        n_trajectories_total=n_with,
        n_trajectories_with_error=n_with,
        p_trajectory=p_trajectory,
        p_trajectory_ci_lower=ci_lo if ci_lo is not None else 0.0,
        p_trajectory_ci_upper=ci_hi if ci_hi is not None else 1.0,
        p_per_step=0.0,
        step_mean=0.0,
        step_median=0.0,
        step_std=0.0,
        chars_mean=None,
        chars_median=None,
        target_true_n=None,
        target_false_n=None,
        exit_success_n=None,
        exit_limit_hit_n=None,
        exit_failed_n=None,
        data_hash=data_hash(df["step_idx"].values),
        parser_version="TZ_8.3",
    )


def _save(df: pd.DataFrame, cat: str | None, is_dedup: bool, n_trajectories_total: int) -> None:
    suffix = f"{cat or 'ALL'}" + ("_dedup" if is_dedup else "")
    out_dir = OUT_BASE / suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "errors.parquet", index=False)
    stats = compute_stats(df, cat, is_dedup, n_trajectories_total)
    (out_dir / "stats.json").write_text(
        json.dumps(dataclasses.asdict(stats), indent=2), encoding="utf-8"
    )
    print(f"  {suffix}: {len(df)} записей → {out_dir}")


def run() -> None:
    by_cat, n_traj = process_trajectories()

    dfs: dict[str, pd.DataFrame] = {}
    for cat, records in by_cat.items():
        dfs[cat] = records_to_df(records)

    print("\nСохраняю...")
    for cat, df in dfs.items():
        n_with = df["instance_id"].nunique()
        _save(df, cat, is_dedup=False, n_trajectories_total=n_with)
        _save(df, cat, is_dedup=True, n_trajectories_total=n_with)  # no dedup для TRAIL

    print("\nГотово.")
    for cat in sorted(dfs.keys()):
        print(f"  {cat}: {len(dfs[cat])} записей")


if __name__ == "__main__":
    run()