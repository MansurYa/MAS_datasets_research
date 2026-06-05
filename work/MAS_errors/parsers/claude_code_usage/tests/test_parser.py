"""Тесты для парсера claude_code_usage."""

import pytest
from pathlib import Path
import pandas as pd
import sys

# Добавляем корень проекта в путь
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from work.MAS_errors.parsers.claude_code_usage.parser import (
    load_and_process_csv,
    assign_sessions,
    detect_kv_cache_loss,
    build_records,
    compute_stats,
    SESSION_GAP_SECONDS,
)


class TestLoadAndProcessCsv:
    def test_loads_data(self):
        df = load_and_process_csv()
        assert len(df) == 7561
        assert "Time" in df.columns
        assert "Cache Read Tokens" in df.columns

    def test_has_time_diff(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        assert "time_diff" in df.columns

    def test_cache_hit_ratio_bounds(self):
        df = load_and_process_csv()
        assert df["cache_hit_ratio"].min() >= 0
        assert df["cache_hit_ratio"].max() <= 1.0


class TestSessionAssignment:
    def test_assigns_sessions(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        assert "session_id" in df.columns
        assert df["session_id"].nunique() >= 1

    def test_step_in_session(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        assert "step_in_session" in df.columns
        assert df["step_in_session"].min() == 0

    def test_session_gap_threshold(self):
        """Проверяем что сессии разделяются по порогу 30 минут."""
        df = load_and_process_csv()
        df = assign_sessions(df)

        # Находим переходы между сессиями
        transitions = df[df["is_new_session"]]
        assert len(transitions) > 0

        # Все переходы должны иметь time_diff > SESSION_GAP_SECONDS
        for _, row in transitions.iterrows():
            if pd.notna(row["time_diff"]):
                assert row["time_diff"] > SESSION_GAP_SECONDS


class TestKVCacheLossDetection:
    def test_detects_kv_cache_loss(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        df = detect_kv_cache_loss(df)

        assert "is_kv_cache_loss" in df.columns
        assert df["is_kv_cache_loss"].dtype == bool

    def test_kv_cache_loss_count(self):
        """Проверяем что найдено ~27 событий."""
        df = load_and_process_csv()
        df = assign_sessions(df)
        df = detect_kv_cache_loss(df)

        n_loss = df["is_kv_cache_loss"].sum()
        # Допускаем погрешность ±5
        assert 20 <= n_loss <= 35, f"Expected ~27 events, got {n_loss}"

    def test_kv_cache_loss_after_gap_only(self):
        """KV cache loss может быть только после перерыва."""
        df = load_and_process_csv()
        df = assign_sessions(df)
        df = detect_kv_cache_loss(df)

        loss_events = df[df["is_kv_cache_loss"]]
        for _, row in loss_events.iterrows():
            assert row["time_diff"] > SESSION_GAP_SECONDS


class TestBuildRecords:
    def test_builds_records(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        df = detect_kv_cache_loss(df)
        records = build_records(df)

        assert len(records) == len(df)
        assert "traj_idx" in records.columns
        assert "step_idx" in records.columns
        assert "cache_loss" in records.columns

    def test_cache_loss_values(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        df = detect_kv_cache_loss(df)
        records = build_records(df)

        assert set(records["cache_loss"].unique()).issubset({0, 1})


class TestComputeStats:
    def test_computes_stats(self):
        df = load_and_process_csv()
        df = assign_sessions(df)
        df = detect_kv_cache_loss(df)
        stats = compute_stats(df)

        assert stats.dataset == "claude_code_usage"
        assert stats.error_type == "kv_cache_loss"
        assert stats.n_total_requests == 7561
        assert 20 <= stats.n_kv_cache_loss_events <= 35


if __name__ == "__main__":
    pytest.main([__file__, "-v"])