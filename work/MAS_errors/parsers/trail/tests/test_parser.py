import pytest
from work.MAS_errors.parsers.trail.parser import (
    normalize_error_pattern,
    _map_category,
    CATEGORY_MAP,
)


class TestCategoryMapper:
    def test_instruction_noncompliance(self):
        assert _map_category("Instruction Non-compliance") == "instruction_noncompliance"

    def test_formatting_errors(self):
        assert _map_category("Formatting Errors") == "formatting_errors"

    def test_context_handling_failure(self):
        assert _map_category("Context Handling Failure") == "context_handling_failures"

    def test_resource_abuse(self):
        assert _map_category("Resource Abuse") == "resource_abuse"

    def test_poor_information_retrieval(self):
        assert _map_category("Poor Information Retrieval") == "poor_information_retrieval"

    def test_incorrect_problem_identification(self):
        assert _map_category("Incorrect Problem Identification") == "incorrect_problem_identification"

    def test_language_only(self):
        assert _map_category("Language-only") == "language_only"
        assert _map_category("Language-only ") == "language_only"

    def test_tool_related(self):
        assert _map_category("Tool-related") == "tool_related"
        assert _map_category("Tool-related ") == "tool_related"
        assert _map_category("Tool Output Misinterpretation") == "tool_related"

    def test_task_orchestration(self):
        assert _map_category("Task Orchestration") == "task_orchestration"

    def test_goal_deviation(self):
        assert _map_category("Goal Deviation") == "goal_deviation"

    def test_unknown_category(self):
        result = _map_category("Some Unknown Category")
        assert result == "some_unknown_category"


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


class TestCATEGORY_MAP:
    def test_all_mapped_categories_exist(self):
        assert "Instruction Non-compliance" in CATEGORY_MAP
        assert "Formatting Errors" in CATEGORY_MAP
        assert "Context Handling Failure" in CATEGORY_MAP
        assert "Resource Abuse" in CATEGORY_MAP
        assert "Tool-related" in CATEGORY_MAP
        assert "Tool-related " in CATEGORY_MAP
        assert "Goal Deviation" in CATEGORY_MAP