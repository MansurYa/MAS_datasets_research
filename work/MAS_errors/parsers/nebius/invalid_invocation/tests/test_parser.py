import pytest
from collections import defaultdict

from work.MAS_errors.parsers.nebius.invalid_invocation.parser import (
    matches_A, matches_B, matches_E,
    parse_edit_errors, normalize_error_pattern,
    _mark_dedup,
    compute_stats,
)
import pandas as pd
from work.MAS_errors.schemas import ErrorRecord


class TestClassifier:
    def test_matches_A_valid(self):
        assert matches_A("python: can't open file '/X': [Errno 2] No such file or directory") is True

    def test_matches_A_exclude_module_not_found(self):
        assert matches_A("ModuleNotFoundError: No module named 'numpy'") is False

    def test_matches_A_exclude_line_number(self):
        assert matches_A("line 42: something") is False

    def test_matches_A_exclude_pytest(self):
        assert matches_A("pytest: something") is False

    def test_matches_B_valid(self):
        assert matches_B("/bin/bash: line 309: find.: command not found") is True

    def test_matches_B_exclude_ls(self):
        assert matches_B("ls: cannot access '/X': No such file or directory") is False

    def test_matches_B_exclude_syntax_error(self):
        assert matches_B("SyntaxError: invalid syntax") is False

    def test_matches_E_true(self):
        assert matches_E("Your proposed edit has introduced new syntax error") is True

    def test_matches_E_false(self):
        assert matches_E("Some other text") is False

    def test_parse_edit_errors(self):
        text = "ERRORS:\n- E999 IndentationError: unexpected indent\n- F821 undefined name 'os'"
        errors = parse_edit_errors(text)
        assert len(errors) == 2
        assert errors[0] == ("E999", "IndentationError: unexpected indent")
        assert errors[1] == ("F821", "undefined name 'os'")

    def test_parse_edit_errors_empty(self):
        assert parse_edit_errors("No errors here") == []

    def test_normalize_pattern_hides_paths(self):
        pat = normalize_error_pattern("python: can't open file '/some/path/here.py'")
        assert "/some/path" not in pat
        assert "/X" in pat

    def test_normalize_pattern_hides_strings(self):
        pat = normalize_error_pattern("Error: 'some long string 123' not found")
        assert "long string" not in pat
        assert "'X'" in pat


class TestDedup:
    def test_mark_dedup_filters_duplicates(self):
        df = pd.DataFrame({
            "instance_id": ["r1", "r1", "r1"],
            "traj_idx":     [0,    0,    0],
            "normalized_pattern": ["A", "A", "B"],
            "step_idx":  [1, 1, 2],
        })
        result = _mark_dedup(df)
        assert len(result) == 2  # second "A" removed

    def test_mark_dedup_different_trajs(self):
        df = pd.DataFrame({
            "instance_id": ["r1", "r2"],
            "traj_idx":     [0,    1],
            "normalized_pattern": ["A", "A"],
            "step_idx":  [1, 1],
        })
        result = _mark_dedup(df)
        assert len(result) == 2  # different traj → kept


class TestStats:
    def test_compute_stats_basic(self):
        df = pd.DataFrame({
            "instance_id": ["r1", "r2", "r3"],
            "traj_idx":    [0, 1, 2],
            "step_idx":    [5, 10, 3],
            "chars_before_error": [1000, 2000, 500],
            "traj_total_chars":    [5000, 6000, 4000],
            "traj_total_steps":    [10, 12, 8],
            "target":      [True, False, None],
            "exit_group":  ["success", "limit_hit", "failed"],
        })
        stats = compute_stats(df, "A", is_dedup=False)
        assert stats.dataset == "nebius"
        assert stats.error_type == "invalid_invocation"
        assert stats.error_subtype == "A"
        assert stats.is_dedup is False
        assert stats.n_errors == 3
        assert stats.n_trajectories_with_error == 3
        assert stats.parser_version == "TZ_8.2"
        assert 0.0 <= stats.p_trajectory <= 1.0
        assert len(stats.data_hash) == 64
        assert stats.exit_success_n == 1
        assert stats.exit_limit_hit_n == 1
        assert stats.exit_failed_n == 1