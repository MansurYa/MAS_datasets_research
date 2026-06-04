import pytest
from work.MAS_errors.parsers.who_and_when.parser import normalize_error_pattern


class TestNormalizePattern:
    def test_hides_paths(self):
        pat = normalize_error_pattern("Error: /some/path/here.py not found")
        assert "/some/path" not in pat
        assert "/X" in pat

    def test_hides_strings(self):
        pat = normalize_error_pattern("Error: 'some long string 123'")
        assert "long string" not in pat
        assert "'X'" in pat

    def test_hides_line_numbers(self):
        pat = normalize_error_pattern("Error on line 42: something")
        assert "line 42" not in pat
        assert "line N" in pat

    def test_strips_whitespace(self):
        pat = normalize_error_pattern("  Error   multiple   spaces  ")
        assert "  " not in pat