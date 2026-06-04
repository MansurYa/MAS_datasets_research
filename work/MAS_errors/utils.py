from __future__ import annotations

import hashlib
import math
from typing import Tuple

import numpy as np
import pandas as pd

from .schemas import ErrorRecord


EXIT_GROUP_MAP = {
    "submitted": "success",
    "submitted (exit_context)": "limit_hit",
    "exit_context": "limit_hit",
    "early_exit": "failed",
    "submitted_no_patch": "failed",
    "exit_format": "failed",
}


def data_hash(arr: np.ndarray | list) -> str:
    if isinstance(arr, list):
        arr = np.array(arr, dtype=np.float64)
    arr = np.asarray(arr, dtype=np.float64)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def wilson_ci(k: int, n: int, alpha: float = 0.05) -> Tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 0.0

    z = 1.960
    p_hat = k / n

    adjusted_n = n + z**2
    center = (k + z**2 / 2) / adjusted_n
    half_width = z * math.sqrt((k * (n - k)) / (n**3) + (z**2) / (4 * n**2))

    lower = max(0.0, center - half_width)
    upper = min(1.0, center + half_width)

    return p_hat, lower, upper


def filter_subgroup(df: pd.DataFrame, subgroup: str) -> pd.DataFrame:
    if subgroup == "all":
        return df

    if subgroup == "success_targetT":
        return df[(df["exit_group"] == "success") & df["target"].eq(True)]
    if subgroup == "success_targetF":
        return df[(df["exit_group"] == "success") & df["target"].eq(False)]
    if subgroup == "limit_hit":
        return df[df["exit_group"] == "limit_hit"]
    if subgroup == "failed":
        return df[df["exit_group"] == "failed"]

    raise ValueError(f"Unknown subgroup: {subgroup}")


def get_subgroups(df: pd.DataFrame) -> list[str]:
    if "exit_group" not in df.columns:
        return ["all"]

    subgroups = []
    if (df["exit_group"] == "success").any():
        subgroups.append("success_targetT")
        subgroups.append("success_targetF")
    if (df["exit_group"] == "limit_hit").any():
        subgroups.append("limit_hit")
    if (df["exit_group"] == "failed").any():
        subgroups.append("failed")

    if not subgroups:
        return ["all"]

    return subgroups


def records_to_df(records: list[ErrorRecord]) -> pd.DataFrame:
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
            "error_code": r.error_code,
            "error_msg": r.error_msg,
            "undefined_name": r.undefined_name,
            "import_present_in_edit": r.import_present_in_edit,
        })
    return pd.DataFrame(rows)


def df_to_records(df: pd.DataFrame) -> list[ErrorRecord]:
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
            target=None if not pd.notna(row["target"]) else bool(row["target"]),
            exit_group=str(row["exit_group"]) if pd.notna(row["exit_group"]) else None,
            exit_status=str(row["exit_status"]) if pd.notna(row["exit_status"]) else None,
            error_text=str(row["error_text"]),
            normalized_pattern=str(row["normalized_pattern"]) if pd.notna(row["normalized_pattern"]) else None,
            occurrence_in_traj=int(row["occurrence_in_traj"]) if pd.notna(row["occurrence_in_traj"]) else None,
            error_code=str(row["error_code"]) if pd.notna(row.get("error_code")) else None,
            error_msg=str(row["error_msg"]) if pd.notna(row.get("error_msg")) else None,
            undefined_name=str(row["undefined_name"]) if pd.notna(row.get("undefined_name")) else None,
            import_present_in_edit=bool(row["import_present_in_edit"]) if pd.notna(row.get("import_present_in_edit")) else None,
        ))
    return records
