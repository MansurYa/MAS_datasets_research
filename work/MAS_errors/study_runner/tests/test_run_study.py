"""Тесты для run_study.py."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[3].parent / "scripts"))

from work.MAS_errors.schemas import StudySpec
from work.MAS_errors.study_runner.run_study import _error_result, DISTRIBUTIONS


def test_distributions_list():
    """DISTRIBUTIONS содержит ожидаемые типы."""
    expected = ["W2", "W3", "LN2", "G2", "LL2", "E1", "E2", "N", "GU"]
    assert DISTRIBUTIONS == expected, f"Expected {expected}, got {DISTRIBUTIONS}"


def test_error_result():
    """_error_result создаёт корректный StudyResult."""
    spec = StudySpec(
        study_id="test_error",
        parquet_path="/tmp/test.parquet",
        dataset="test",
        error_type="test_error",
        error_subtype=None,
        is_dedup=False,
        subgroup="all",
        analysis_var="step_idx",
    )

    import time
    start = time.monotonic()
    result = _error_result(spec, "NO_DATA", start)

    assert result.study_id == "test_error"
    assert result.status == "NO_DATA"
    assert result.n_errors == 0
    assert result.final_dist is None
    assert result.p_final is None
    assert result.D_obs is None
    assert result.n_attempts == 0
    assert len(result.attempts_log) == 0


def test_error_result_missing_column():
    """_error_result для MISSING_COLUMN."""
    spec = StudySpec(
        study_id="test_missing",
        parquet_path="/tmp/test.parquet",
        dataset="test",
        error_type="test_error",
        error_subtype=None,
        is_dedup=False,
        subgroup="all",
        analysis_var="nonexistent_var",
    )

    import time
    start = time.monotonic()
    result = _error_result(spec, "MISSING_COLUMN", start)

    assert result.status == "MISSING_COLUMN"
    assert result.n_errors == 0


def test_studyspec_fields():
    """StudySpec имеет все необходимые поля."""
    spec = StudySpec(
        study_id="test",
        parquet_path="/tmp/test.parquet",
        dataset="test",
        error_type="test_error",
        error_subtype="subtype",
        is_dedup=True,
        subgroup="all",
        analysis_var="step_idx",
    )

    assert spec.study_id == "test"
    assert spec.parquet_path == "/tmp/test.parquet"
    assert spec.dataset == "test"
    assert spec.error_type == "test_error"
    assert spec.error_subtype == "subtype"
    assert spec.is_dedup is True
    assert spec.subgroup == "all"
    assert spec.analysis_var == "step_idx"