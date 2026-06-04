"""Тесты для generate_study_list.py."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3].parent / "scripts"))

from work.MAS_errors.study_runner.generate_study_list import scan_parsers_output, make_study_id


def test_scan_finds_nebius():
    """scan_parsers_output возвращает исследования для nebius."""
    studies = scan_parsers_output()
    nebius = [s for s in studies if s.dataset == "nebius"]
    assert len(nebius) > 0, "nebius studies not found"


def test_scan_finds_trail():
    """scan_parsers_output возвращает исследования для TRAIL."""
    studies = scan_parsers_output()
    trail = [s for s in studies if s.dataset == "trail"]
    assert len(trail) > 0, "TRAIL studies not found"


def test_scan_finds_agentRx():
    """scan_parsers_output возвращает исследования для AgentRx."""
    studies = scan_parsers_output()
    agentrx = [s for s in studies if s.dataset == "agentRx"]
    assert len(agentrx) > 0, "AgentRx studies not found"


def test_scan_finds_who_and_when():
    """scan_parsers_output возвращает исследования для Who_and_When."""
    studies = scan_parsers_output()
    ww = [s for s in studies if s.dataset == "who_and_when"]
    assert len(ww) > 0, "Who_and_When studies not found"


def test_study_id_unique():
    """Все study_id уникальны."""
    studies = scan_parsers_output()
    ids = [s.study_id for s in studies]
    assert len(ids) == len(set(ids)), "Duplicate study_id found"


def test_nebius_has_step_idx_and_chars():
    """nebius имеет оба analysis_var."""
    studies = scan_parsers_output()
    nebius = [s for s in studies if s.dataset == "nebius"]
    step_idx = [s for s in nebius if s.analysis_var == "step_idx"]
    chars = [s for s in nebius if s.analysis_var == "chars_before_error"]
    assert len(step_idx) > 0, "nebius step_idx studies not found"
    assert len(chars) > 0, "nebius chars_before_error studies not found"


def test_dedup_is_detected_from_path():
    """A_dedup → is_dedup=True."""
    studies = scan_parsers_output()
    nebius = [s for s in studies if s.dataset == "nebius"]
    dedup = [s for s in nebius if s.is_dedup]
    non_dedup = [s for s in nebius if not s.is_dedup]
    assert len(dedup) > 0, "nebius dedup studies not found"
    assert len(non_dedup) > 0, "nebius non-dedup studies not found"


def test_other_datasets_have_dedup():
    """TRAIL/AgentRx/Who_and_When тоже имеют dedup-варианты."""
    studies = scan_parsers_output()
    others = [s for s in studies if s.dataset != "nebius"]
    # TRAIL и AgentRx парсеры генерируют _dedup папки
    assert any(s.is_dedup for s in others), "Other datasets should have dedup variants"


def test_make_study_id():
    """make_study_id генерирует правильные ID."""
    sid = make_study_id("nebius", "invalid_invocation", "A", False, "all", "step_idx")
    assert sid == "nebius_invalid_invocation_A_all_step_idx"

    sid_dedup = make_study_id("nebius", "invalid_invocation", "A", True, "all", "step_idx")
    assert sid_dedup == "nebius_invalid_invocation_A_dedup_all_step_idx"

    sid_no_subtype = make_study_id("trail", "instruction_noncompliance", None, False, "all", "step_idx")
    assert sid_no_subtype == "trail_instruction_noncompliance_all_step_idx"


def test_study_has_required_fields():
    """Каждый StudySpec имеет все обязательные поля."""
    studies = scan_parsers_output()
    for s in studies:
        assert hasattr(s, "study_id")
        assert hasattr(s, "parquet_path")
        assert hasattr(s, "dataset")
        assert hasattr(s, "error_type")
        assert hasattr(s, "error_subtype")
        assert hasattr(s, "is_dedup")
        assert hasattr(s, "subgroup")
        assert hasattr(s, "analysis_var")
        assert s.study_id  # не пустой
        assert s.parquet_path  # не пустой
        assert s.dataset  # не пустой
        assert s.error_type  # не пустой