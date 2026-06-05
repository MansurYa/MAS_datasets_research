"""Parser for code_execution errors in nebius.

This parser extracts Python runtime errors that occur when agent-written scripts
(reproduce.py, test_*.py, run_*.py) are executed.

Two outputs:
- errors.parquet: True Positives (TP) - errors from agent scripts
- errors_issue.parquet: False Positives (FP) - errors from issue descriptions
"""
from __future__ import annotations

import dataclasses
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

from work.MAS_errors.schemas import ErrorRecord
from work.MAS_errors.utils import EXIT_GROUP_MAP, data_hash, records_to_df, wilson_ci

PROJECT_ROOT = Path(__file__).parents[5]
PARQUET_DIR = PROJECT_ROOT / "datasets" / "nebius-SWE-agent-trajectories" / "data"
OUT_BASE = Path(__file__).parent

N_TOTAL = 80_036

# Patterns for Python runtime errors
# Simple pattern: matches "ErrorType: message" at the start or in traceback
PYTHON_ERROR_RE = re.compile(
    r"(?P<exc_type>"
    r"FileNotFoundError|IsADirectoryError|NotADirectoryError|"
    r"PermissionError|OSError|"
    r"TypeError|ValueError|AttributeError|NameError|KeyError|IndexError|"
    r"ImportError|ModuleNotFoundError|RuntimeError|ZeroDivisionError|"
    r"SyntaxError|UnboundLocalError|RecursionError|IndentationError|"
    r"AssertionError|ConnectionError|EOFError|"
    r"LookupError|EnvironmentError|BlockingIOError|ChildProcessError|"
    r"ConnectionRefusedError|ConnectionResetError|ConnectionAbortedError|"
    r"InterruptedError|ProcessLookupError|FileExistsError|"
    r"TabError|SystemExit|StopIteration|GeneratorExit|"
    r"BadStatusLine|MethodNotAllowed|SessionNotCreated|"
    r"NoSuchElement|StaleElementReference|TimeoutException"
    r")[:\s]+(?P<message>.+?)(?=\n\s*\n|\Z)",
    re.DOTALL | re.IGNORECASE,
)

# Patterns for agent-written scripts
AGENT_SCRIPT_PATTERNS = [
    r"/reproduce\.py",
    r"/test_[^/]+\.py",
    r"/run_[^/]+\.py",
    r"/script\.py",
    r"/debug\.py",
    r"/verify\.py",
]
AGENT_SCRIPT_RE = re.compile("|".join(AGENT_SCRIPT_PATTERNS), re.IGNORECASE)

# Exclude edit validation (these are E1/E2, not code_execution)
EDIT_VALIDATION_PATTERNS = [
    "Your proposed edit has introduced",
    "Syntax error in your proposed edit",
]
EDIT_VALIDATION_RE = re.compile("|".join(EDIT_VALIDATION_PATTERNS), re.IGNORECASE)

# Network errors (not code_execution)
NETWORK_ERROR_PATTERNS = [
    "HTTPError",
    "requests.exceptions",
    "Connection refused",
    "403 Client Error",
    "404 Client Error",
    "500 Server Error",
    "502 Bad Gateway",
    "503 Service Unavailable",
    "TimeoutError",
    "ReadTimeout",
    "ConnectTimeout",
]
NETWORK_ERROR_RE = re.compile("|".join(NETWORK_ERROR_PATTERNS), re.IGNORECASE)


def is_edit_validation(text: str) -> bool:
    """Check if text contains edit validation error (E1/E2), not code_execution."""
    return bool(EDIT_VALIDATION_RE.search(text))


def is_network_error(text: str) -> bool:
    """Check if text contains network error, not code_execution."""
    return bool(NETWORK_ERROR_RE.search(text))


def parse_error_type(text: str) -> tuple[str, str] | None:
    """Parse Python error type and message from text.

    Returns (error_type, message) or None if no Python error found.
    """
    # Find the error type and message
    match = PYTHON_ERROR_RE.search(text)
    if not match:
        return None

    exc_type = match.group("exc_type")
    message = match.group("message").strip()

    # Clean up message - take first line only for brevity
    first_line = message.split("\n")[0].strip()
    # Truncate very long messages
    if len(first_line) > 500:
        first_line = first_line[:497] + "..."

    return (exc_type, first_line)


def matches_agent_script(text: str) -> bool:
    """Check if text contains Python runtime error from agent-written script (TP)."""
    if is_edit_validation(text):
        return False

    has_py_error = parse_error_type(text) is not None
    if not has_py_error:
        return False

    has_agent_script = bool(AGENT_SCRIPT_RE.search(text))
    return has_agent_script


def matches_issue_description(text: str) -> bool:
    """Check if text contains Python error from issue description (FP).

    This is Python error WITHOUT agent script - likely copied from issue.
    """
    if is_edit_validation(text):
        return False

    has_py_error = parse_error_type(text) is not None
    if not has_py_error:
        return False

    has_agent_script = bool(AGENT_SCRIPT_RE.search(text))
    return not has_agent_script


def normalize_error_pattern(error_type: str, message: str) -> str:
    """Normalize error pattern for deduplication."""
    t = f"{error_type}: {message}"
    # Normalize file paths
    t = re.sub(r"/[\w\-./\\]+/", "/PATH/", t)
    t = re.sub(r"'[^']{0,100}'", "'X'", t)
    t = re.sub(r'"[^"]{0,100}"', '"X"', t)
    # Normalize line numbers
    t = re.sub(r"\bline\s+\d+", "line N", t, flags=re.IGNORECASE)
    # Normalize numbers
    t = re.sub(r"\b\d+\b", "N", t)
    # Collapse whitespace
    return re.sub(r"\s+", " ", t).strip()


def process_trajectories() -> tuple[list[ErrorRecord], list[ErrorRecord]]:
    """Process all trajectories and extract code_execution errors.

    Returns:
        Tuple of (TP_records, FP_records) where TP = agent script errors,
        FP = issue description errors.
    """
    print("Загружаю датасет...")
    dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
    d = dataset.to_table().to_pydict()

    instance_ids = d["instance_id"]
    trajectories = d["trajectory"]
    exit_statuses = d["exit_status"]
    targets = d["target"]

    print(f"Загружено траекторий: {len(instance_ids)}")

    # Counters for occurrence tracking
    occ_counters: dict[tuple, int] = defaultdict(int)

    tp_records: list[ErrorRecord] = []
    fp_records: list[ErrorRecord] = []

    total = len(instance_ids)
    for row_idx in range(total):
        inst = instance_ids[row_idx]
        traj = trajectories[row_idx]
        exit_s = exit_statuses[row_idx]
        target = targets[row_idx]
        exit_group = EXIT_GROUP_MAP.get(exit_s)

        global_traj_idx = row_idx

        traj_total_chars = sum(
            len(s.get("text") or "") + len(s.get("system_prompt") or "")
            for s in traj
        )
        traj_total_steps = len(traj)
        running_chars = 0

        for step_idx, step in enumerate(traj):
            if not isinstance(step, dict):
                continue
            text = step.get("text")
            if not text:
                running_chars += len(step.get("system_prompt") or "")
                continue

            base = dict(
                dataset="nebius",
                error_type="code_execution",
                is_dedup=False,
                instance_id=inst,
                traj_idx=global_traj_idx,
                step_idx=step_idx,
                chars_before_error=running_chars,
                traj_total_chars=traj_total_chars,
                traj_total_steps=traj_total_steps,
                target=bool(target) if target is not None else None,
                exit_group=exit_group,
                exit_status=exit_s,
            )

            # Check for TP (agent script) errors
            if matches_agent_script(text):
                error_info = parse_error_type(text)
                if error_info:
                    error_type, error_msg = error_info
                    pat = normalize_error_pattern(error_type, error_msg)

                    occ_counters[(inst, global_traj_idx, pat)] += 1
                    occ = occ_counters[(inst, global_traj_idx, pat)]

                    tp_records.append(ErrorRecord(
                        **base,
                        error_subtype=error_type,
                        error_id=f"nebius_ce_tp_{global_traj_idx}_{step_idx}_{occ}",
                        error_text=text[:2000],  # Truncate long texts
                        normalized_pattern=pat,
                        occurrence_in_traj=occ,
                    ))

            # Check for FP (issue description) errors
            elif matches_issue_description(text):
                # Only if not a network error
                if not is_network_error(text):
                    error_info = parse_error_type(text)
                    if error_info:
                        error_type, error_msg = error_info

                        fp_records.append(ErrorRecord(
                            **base,
                            error_subtype=error_type,
                            error_id=f"nebius_ce_fp_{global_traj_idx}_{step_idx}_{len(fp_records)}",
                            error_text=text[:2000],
                            normalized_pattern=None,  # Not used for FP
                            occurrence_in_traj=None,
                        ))

            running_chars += len(text) + len(step.get("system_prompt") or "")

        if (row_idx + 1) % 10_000 == 0:
            print(f"  {row_idx + 1}/{total}")

    return tp_records, fp_records


def _mark_dedup(df: pd.DataFrame) -> pd.DataFrame:
    """Mark duplicate errors based on (instance_id, traj_idx, normalized_pattern)."""
    seen: set = set()
    mask = []
    for _, row in df.iterrows():
        key = (row["instance_id"], row["traj_idx"], row["normalized_pattern"])
        mask.append(key not in seen)
        seen.add(key)
    df = df[mask].copy()
    df["is_dedup"] = True
    return df


def compute_stats(df: pd.DataFrame, n_total: int = N_TOTAL) -> dict:
    """Compute statistics for error records."""
    n_errors = len(df)
    n_with = df["instance_id"].nunique() if len(df) > 0 else 0
    p_traj, ci_lo, ci_hi = wilson_ci(n_with, n_total)
    total_steps = int(df["traj_total_steps"].sum()) if len(df) > 0 else 0
    p_step = n_errors / total_steps if total_steps > 0 else 0.0

    # Subtype counts
    subtype_counts = {}
    if len(df) > 0:
        for st in df["error_subtype"].dropna().unique():
            subtype_counts[st] = int((df["error_subtype"] == st).sum())

    return {
        "n_errors": n_errors,
        "n_trajectories_with_error": n_with,
        "p_trajectory": p_traj,
        "p_trajectory_ci_lower": ci_lo,
        "p_trajectory_ci_upper": ci_hi,
        "p_per_step": p_step,
        "subtype_counts": subtype_counts,
        "step_mean": float(df["step_idx"].mean()) if len(df) > 0 else 0.0,
        "step_median": float(df["step_idx"].median()) if len(df) > 0 else 0.0,
        "data_hash": data_hash(df["step_idx"].values) if len(df) > 0 else "",
    }


def save_outputs(tp_records: list[ErrorRecord], fp_records: list[ErrorRecord]) -> None:
    """Save TP and FP records to parquet files with stats."""
    out_dir = OUT_BASE / "code_execution"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Convert to DataFrames
    df_tp = records_to_df(tp_records)
    df_fp = records_to_df(fp_records)

    # Save full versions
    df_tp.to_parquet(out_dir / "errors.parquet", index=False)
    df_fp.to_parquet(out_dir / "errors_issue.parquet", index=False)

    # Compute dedup version for TP
    df_tp_dedup = _mark_dedup(df_tp.copy())
    df_tp_dedup.to_parquet(out_dir / "errors_dedup.parquet", index=False)

    # Compute FP rate
    total_classified = len(df_tp) + len(df_fp)
    fp_rate = len(df_fp) / total_classified if total_classified > 0 else 0.0

    # Stats for TP (full)
    stats_tp = compute_stats(df_tp)
    # Stats for TP (dedup)
    stats_tp_dedup = compute_stats(df_tp_dedup)

    # Save stats.json
    stats = {
        "dataset": "nebius",
        "error_type": "code_execution",
        "parser_version": "TZ_10",
        "n_trajectories_total": N_TOTAL,
        "n_errors": len(df_tp),  # TP count
        "n_errors_dedup": len(df_tp_dedup),
        "n_trajectories_with_error": stats_tp["n_trajectories_with_error"],
        "n_trajectories_with_error_dedup": stats_tp_dedup["n_trajectories_with_error"],
        "n_issue_errors": len(df_fp),  # FP count
        "fp_rate": fp_rate,
        "p_per_step": stats_tp["p_per_step"],
        "p_per_step_dedup": stats_tp_dedup["p_per_step"],
        "subtypes": stats_tp["subtype_counts"],
        "subtypes_dedup": stats_tp_dedup["subtype_counts"],
        "issue_subtypes": df_fp["error_subtype"].value_counts().to_dict() if len(df_fp) > 0 else {},
        "step_mean": stats_tp["step_mean"],
        "step_median": stats_tp["step_median"],
        "data_hash": stats_tp["data_hash"],
    }

    with open(out_dir / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"  TP (agent script): {len(df_tp)} records, {stats_tp['n_trajectories_with_error']} trajectories")
    print(f"  TP dedup: {len(df_tp_dedup)} records, {stats_tp_dedup['n_trajectories_with_error']} trajectories")
    print(f"  FP (issue desc): {len(df_fp)} records")
    print(f"  FP rate: {fp_rate:.1%}")

    # Print subtype breakdown
    print("\n  TP subtypes:")
    for st, cnt in sorted(stats_tp["subtype_counts"].items(), key=lambda x: -x[1]):
        print(f"    {st}: {cnt}")

    if stats["issue_subtypes"]:
        print("\n  FP subtypes:")
        for st, cnt in sorted(stats["issue_subtypes"].items(), key=lambda x: -x[1]):
            print(f"    {st}: {cnt}")


def run() -> None:
    """Main entry point."""
    print("=" * 60)
    print("Parser: code_execution errors in nebius")
    print("=" * 60)

    tp_records, fp_records = process_trajectories()

    print("\nСохраняю результаты...")
    save_outputs(tp_records, fp_records)

    print("\nГотово.")


if __name__ == "__main__":
    run()