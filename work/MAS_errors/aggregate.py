"""Утилиты агрегации results.csv."""

from __future__ import annotations

import pandas as pd


def load_results(path: str = "work/MAS_errors/results.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"error_subtype": str})
    df["error_subtype"] = df["error_subtype"].fillna("")
    return df


def status_counts(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["dataset", "error_type", "status"])
        .size()
        .unstack(fill_value=0)
    )


def dataset_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("dataset")["status"].value_counts().unstack(fill_value=0)
    total = g.sum(axis=1)
    accept_rate = (g.get("ACCEPT", 0) / total * 100).round(1)
    return pd.concat([g, total.rename("total"), accept_rate.rename("accept_rate%")], axis=1)


def distribution_by_dataset(df: pd.DataFrame) -> pd.DataFrame:
    accept = df[df["status"] == "ACCEPT"]
    return (
        accept.groupby(["dataset", "error_type", "final_dist"])
        .size()
        .reset_index(name="count")
        .sort_values(["dataset", "count"], ascending=[True, False])
    )


def problem_studies(df: pd.DataFrame) -> pd.DataFrame:
    reject = df[df["status"] == "REJECT"].copy()
    reject = reject.sort_values("p_final")
    return reject[["study_id", "dataset", "error_type", "n_errors", "p_final", "final_dist"]]
