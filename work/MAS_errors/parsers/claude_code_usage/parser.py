#!/usr/bin/env python3
"""Парсер Claude Code Usage для исследования KV Cache Loss.

Выделяет сессии из API-логов и определяет события утраты KV cache.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parents[4]
CSV_PATH = PROJECT_ROOT / "datasets" / "claude_code_usage_kv_cache_loss.csv"
OUT_BASE = Path(__file__).parent

# Порог для определения новой сессии (секунды)
SESSION_GAP_SECONDS = 1800  # 30 минут

# Порог для определения KV cache loss
CACHE_READ_ZERO = 0
CACHE_READ_PREV_THRESHOLD = 100


@dataclasses.dataclass
class ClaudeCodeUsageStats:
    dataset: str
    error_type: str
    n_total_requests: int
    n_sessions: int
    n_kv_cache_loss_events: int
    p_loss_per_request: float
    p_loss_per_session_after_gap: float
    parser_version: str


def load_and_process_csv() -> pd.DataFrame:
    """Загрузить CSV и добавить вычисляемые поля."""
    df = pd.read_csv(CSV_PATH)
    df["Time"] = pd.to_datetime(df["Time"])
    df = df.sort_values("Time").reset_index(drop=True)

    # Время с предыдущего запроса
    df["time_diff"] = df["Time"].diff().dt.total_seconds()

    # Cache hit ratio (ограничиваем до 1.0)
    df["cache_hit_ratio"] = np.minimum(
        np.where(df["Input Tokens"] > 0,
                 df["Cache Read Tokens"] / df["Input Tokens"], 0),
        1.0
    )

    return df


def assign_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """Assign session IDs based on time gaps."""
    df = df.copy()
    df["is_new_session"] = df["time_diff"].isna() | (df["time_diff"] > SESSION_GAP_SECONDS)
    df["session_id"] = df["is_new_session"].cumsum()
    df["session_id"] = df["session_id"] - 1  # Начинаем с 0

    # Номер шага в сессии
    df["step_in_session"] = df.groupby("session_id").cumcount()

    return df


def detect_kv_cache_loss(df: pd.DataFrame) -> pd.DataFrame:
    """Определить события KV cache loss."""
    df = df.copy()

    # Cache Read Tokens предыдущего запроса
    df["prev_cache_read"] = df["Cache Read Tokens"].shift(1)

    # Предыдущий запрос в той же сессии?
    df["prev_in_same_session"] = (df["session_id"] == df["session_id"].shift(1))

    # KV cache loss = после перерыва, Cache Read = 0, предыдущий шаг имел > 100
    df["is_kv_cache_loss"] = (
        (df["time_diff"] > SESSION_GAP_SECONDS) &
        (df["prev_in_same_session"] == False) &  # Первый запрос новой сессии
        (df["Cache Read Tokens"] == CACHE_READ_ZERO) &
        (df["prev_cache_read"] > CACHE_READ_PREV_THRESHOLD)
    )

    return df


def build_records(df: pd.DataFrame) -> pd.DataFrame:
    """Построить DataFrame записей для сохранения в parquet."""
    records = pd.DataFrame({
        "traj_idx": df["session_id"],
        "step_idx": df["step_in_session"],
        "chars_before_error": df["time_diff"].fillna(0),  # time_diff как proxy для интервала
        "cache_read_tokens": df["Cache Read Tokens"],
        "cache_creation_tokens": df["Cache Creation Tokens"],
        "input_tokens": df["Input Tokens"],
        "output_tokens": df["Output Tokens"],
        "cache_loss": df["is_kv_cache_loss"].astype(int),
        "cache_hit_ratio": df["cache_hit_ratio"],
        "time_diff": df["time_diff"].fillna(0),
        "request_time": df["Time"].astype(str),
        "step_in_session": df["step_in_session"],
    })

    return records


def compute_stats(df: pd.DataFrame) -> ClaudeCodeUsageStats:
    """Вычислить статистику для ТЁПЛЫХ сессий (использующих cache хотя бы раз)."""
    # Тёплая сессия: максимальный Cache Read Tokens в сессии > 0
    session_max = df.groupby("session_id")["Cache Read Tokens"].max()
    warm_sessions = set(session_max[session_max > 0].index)
    df["is_warm_session"] = df["session_id"].isin(warm_sessions)

    df_warm = df[df["is_warm_session"]]
    after_gap_warm = df_warm[df_warm["time_diff"] > SESSION_GAP_SECONDS]

    n_requests: int = int(len(df_warm))
    n_sessions: int = int(df_warm["session_id"].nunique())
    n_kv_cache_loss: int = int(df_warm["is_kv_cache_loss"].sum())
    n_after_gap: int = int(len(after_gap_warm))

    p_per_request: float = float(n_kv_cache_loss / n_requests if n_requests > 0 else 0)
    p_after_gap: float = float(n_kv_cache_loss / n_after_gap if n_after_gap > 0 else 0)

    return ClaudeCodeUsageStats(
        dataset="claude_code_usage",
        error_type="kv_cache_loss",
        n_total_requests=n_requests,
        n_sessions=n_sessions,
        n_kv_cache_loss_events=n_kv_cache_loss,
        p_loss_per_request=p_per_request,
        p_loss_per_session_after_gap=p_after_gap,
        parser_version="TZ_9.1",
    )


def run() -> None:
    print("Загружаю Claude Code Usage data...")
    df = load_and_process_csv()
    print(f"Загружено: {len(df)} запросов")

    print("Выделяю сессии...")
    df = assign_sessions(df)
    n_sessions = df["session_id"].nunique()
    print(f"Сессий: {n_sessions}")

    print("Определяю KV cache loss...")
    df = detect_kv_cache_loss(df)
    n_loss = df["is_kv_cache_loss"].sum()
    print(f"Событий KV cache loss: {n_loss}")

    print("Создаю записи...")
    records = build_records(df)
    stats = compute_stats(df)

    # Сохраняем
    out_dir = OUT_BASE / "kv_cache_loss"
    out_dir.mkdir(parents=True, exist_ok=True)

    records.to_parquet(out_dir / "errors.parquet", index=False)
    print(f"  errors.parquet: {len(records)} записей → {out_dir}")

    with open(out_dir / "stats.json", "w") as f:
        json.dump(dataclasses.asdict(stats), f, indent=2)
    print(f"  stats.json → {out_dir}")

    print("\nГотово.")
    print(f"  Всего запросов: {stats.n_total_requests}")
    print(f"  Сессий: {stats.n_sessions}")
    print(f"  KV cache loss событий: {stats.n_kv_cache_loss_events}")
    print(f"  P(loss|request): {stats.p_loss_per_request:.4f}")
    print(f"  P(loss|after_gap): {stats.p_loss_per_session_after_gap:.4f}")


if __name__ == "__main__":
    run()