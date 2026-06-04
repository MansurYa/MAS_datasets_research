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
PARQUET_PATH = PROJECT_ROOT / "datasets" / "Kevin355-Who_and_When" / "Hand-Crafted.parquet"
OUT_BASE = Path(__file__).parent

N_TOTAL = None  # определяется из данных


def normalize_error_pattern(text: str) -> str:
    t = re.split(r"\(Open file:|\(Current directory:|bash-\$", text)[0]
    t = re.sub(r"'[^']{0,200}'", "'X'", t)
    t = re.sub(r'"[^"]{0,200}"', '"X"', t)
    t = re.sub(r"/[\w\-./]+", "/X", t)
    t = re.sub(r"\bline\s+\d+", "line N", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def process_trajectories() -> tuple[dict[str, list[ErrorRecord]], int]:
    print("Загружаю Who_and_When...")
    pf = pq.ParquetFile(str(PARQUET_PATH))
    t = pf.read().to_pydict()

    records_by_cat: dict[str, list[ErrorRecord]] = defaultdict(list)
    traj_ids: list[str] = []

    for row_idx in range(len(t["question_ID"])):
        mistake_type = t["mistake_type"][row_idx]
        if mistake_type is None:
            continue

        cat = mistake_type.strip().lower().replace(" ", "_")
        q_id = t["question_ID"][row_idx]
        traj_ids.append(q_id)

        step_idx = int(t["mistake_step"][row_idx]) if t["mistake_step"][row_idx] is not None else 0
        mistake_reason = t["mistake_reason"][row_idx] or ""

        record = ErrorRecord(
            error_id=f"ww_{q_id}",
            dataset="who_and_when",
            error_type=cat,
            error_subtype=None,
            is_dedup=False,
            instance_id=q_id,
            traj_idx=row_idx,
            step_idx=step_idx,
            chars_before_error=0,
            traj_total_chars=0,
            traj_total_steps=0,
            target=None,
            exit_group=None,
            exit_status=None,
            error_text=mistake_reason,
            normalized_pattern=normalize_error_pattern(mistake_reason),
            occurrence_in_traj=None,
        )
        records_by_cat[cat].append(record)

    n_trajectories = len(set(traj_ids))
    print(f"Загружено: {len(records_by_cat)} категорий, {n_trajectories} траекторий")
    return records_by_cat, n_trajectories


def compute_stats(df: pd.DataFrame, cat: str, is_dedup: bool, n_total: int) -> ErrorStats:
    n_errors = len(df)
    n_with = df["instance_id"].nunique()
    p_trajectory, ci_lo, ci_hi = wilson_ci(n_with, n_total)

    return ErrorStats(
        dataset="who_and_when",
        error_type=cat,
        error_subtype=None,
        is_dedup=is_dedup,
        n_errors=n_errors,
        n_trajectories_total=n_total,
        n_trajectories_with_error=n_with,
        p_trajectory=p_trajectory,
        p_trajectory_ci_lower=ci_lo,
        p_trajectory_ci_upper=ci_hi,
        p_per_step=0.0,
        step_mean=float(df["step_idx"].mean()) if len(df) > 0 else 0.0,
        step_median=float(df["step_idx"].median()) if len(df) > 0 else 0.0,
        step_std=float(df["step_idx"].std()) if len(df) > 0 else 0.0,
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


def _save(df: pd.DataFrame, cat: str, is_dedup: bool, n_total: int) -> None:
    suffix = f"{cat}" + ("_dedup" if is_dedup else "")
    out_dir = OUT_BASE / suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "errors.parquet", index=False)
    stats = compute_stats(df, cat, is_dedup, n_total)
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
        _save(df, cat, is_dedup=False, n_total=n_traj)
        _save(df, cat, is_dedup=True, n_total=n_traj)

    print("\nГотово.")
    for cat in sorted(dfs.keys()):
        print(f"  {cat}: {len(dfs[cat])} записей")


if __name__ == "__main__":
    run()