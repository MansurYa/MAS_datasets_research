"""Tests for code_execution parser."""
import pytest

from work.MAS_errors.parsers.nebius.code_execution.parser import (
    matches_agent_script,
    matches_issue_description,
    parse_error_type,
    normalize_error_pattern,
    is_edit_validation,
    is_network_error,
)


class TestIsEditValidation:
    def test_edit_validation_detected(self):
        text = "Your proposed edit has introduced new syntax error: E999"
        assert is_edit_validation(text) is True

    def test_normal_error_not_edit_validation(self):
        text = "TypeError: string indices must be integers"
        assert is_edit_validation(text) is False


class TestIsNetworkError:
    def test_http_error_detected(self):
        text = "requests.exceptions.HTTPError: 403 Client Error"
        assert is_network_error(text) is True

    def test_connection_refused(self):
        text = "ConnectionRefusedError: [Errno 111] Connection refused"
        assert is_network_error(text) is True

    def test_normal_error_not_network(self):
        text = "TypeError: unsupported operand type(s) for +: 'int' and 'str'"
        assert is_network_error(text) is False


class TestParseErrorType:
    def test_type_error(self):
        text = "TypeError: string indices must be integers"
        result = parse_error_type(text)
        assert result == ("TypeError", "string indices must be integers")

    def test_import_error(self):
        text = "ImportError: cannot import name 'Config' from 'lexicon.config'"
        result = parse_error_type(text)
        assert result == ("ImportError", "cannot import name 'Config' from 'lexicon.config'")

    def test_no_error(self):
        text = "This is normal output without errors"
        result = parse_error_type(text)
        assert result is None


class TestMatchesAgentScript:
    def test_reproduce_py_detected(self):
        text = """
        Traceback (most recent call last):
          File "/lexicon/reproduce.py", line 5, in <module>
            from lexicon.providers.example import Provider
        AttributeError: 'NoneType' object has no attribute 'get'
        """
        assert matches_agent_script(text) is True

    def test_test_py_detected(self):
        text = """
        Traceback (most recent call last):
          File "/lexicon/test_example.py", line 10, in test_basic
            result = obj.method()
        KeyError: 'missing_key'
        """
        assert matches_agent_script(text) is True

    def test_edit_validation_excluded(self):
        text = "Your proposed edit has introduced new syntax error: E999"
        assert matches_agent_script(text) is False

    def test_issue_description_excluded(self):
        text = """
        The issue is:

        Traceback (most recent call last):
          File "/opt/conda/envs/lexicon/lib/python3.9/site-packages/requests/api.py", line 78, in get
            response = request.get(url)
        ConnectionError: Connection refused
        """
        assert matches_agent_script(text) is False

    def test_other_error_excluded(self):
        text = "Some random output without Python error"
        assert matches_agent_script(text) is False


class TestMatchesIssueDescription:
    def test_issue_with_error_no_script(self):
        text = """
        From the issue description:

        Traceback (most recent call last):
          File "/opt/conda/envs/lexicon/lib/python3.9/site-packages/requests/api.py", line 78
            response = request.get(url)
        AttributeError: 'NoneType' object has no attribute 'request'
        """
        assert matches_issue_description(text) is True

    def test_agent_script_excluded(self):
        text = """
        Traceback (most recent call last):
          File "/lexicon/reproduce.py", line 5
            from lexicon.providers.example import Provider
        TypeError: 'NoneType' object has no attribute 'get'
        """
        # This is agent script, not issue description
        assert matches_issue_description(text) is False

    def test_edit_validation_excluded(self):
        text = "Your proposed edit has introduced new syntax error"
        assert matches_issue_description(text) is False

    def test_network_error_excluded(self):
        text = "requests.exceptions.HTTPError: 403 Client Error"
        assert matches_issue_description(text) is False


class TestNormalizeErrorPattern:
    def test_normalizes_file_paths(self):
        result = normalize_error_pattern("TypeError", "string indices must be integers in /some/path/file.py at line 5")
        assert "/some/path/file.py" not in result
        assert "line 5" not in result

    def test_normalizes_line_numbers(self):
        result = normalize_error_pattern("ImportError", "cannot import name 'X' from 'module' in line 123")
        assert "line 123" not in result

    def test_normalizes_strings(self):
        result = normalize_error_pattern("ValueError", "invalid literal 'abc123' for base 10 in 'some_long_string_here'")
        assert "'abc123'" in result  # Short strings kept
        # Long strings truncated