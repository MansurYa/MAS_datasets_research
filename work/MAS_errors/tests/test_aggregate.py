"""Тесты для aggregate.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aggregate import load_results, dataset_summary, problem_studies


def test_load_results():
    df = load_results(str(Path(__file__).resolve().parents[1] / "results.csv"))
    assert len(df) > 0


def test_dataset_summary_has_accept_rate():
    df = load_results(str(Path(__file__).resolve().parents[1] / "results.csv"))
    summary = dataset_summary(df)
    assert "accept_rate%" in summary.columns


def test_problem_studies_sorted():
    df = load_results(str(Path(__file__).resolve().parents[1] / "results.csv"))
    reject = problem_studies(df)
    if len(reject) > 1:
        assert reject["p_final"].is_monotonic_increasing
