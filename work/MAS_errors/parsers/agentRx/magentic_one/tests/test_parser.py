import pytest
from work.MAS_errors.parsers.agentRx.magentic_one.parser import (
    normalize_error_pattern,
    _map_category,
    CATEGORY_MAP,
)


class TestCategoryMapper:
    def test_instruction_adherence_failure(self):
        assert _map_category("Instruction/Plan Adherence Failure") == "instruction_adherence_failure"

    def test_guardrails_triggered(self):
        assert _map_category("Guardrails Triggered") == "guardrails_triggered"

    def test_misinterpretation_of_tool_output(self):
        assert _map_category("Misinterpretation of Tool Output") == "misinterpretation_of_tool_output"

    def test_intent_not_supported(self):
        assert _map_category("Intent not supported") == "intent_not_supported"

    def test_intent_plan_misalignment(self):
        assert _map_category("Intent Plan Misalignment") == "intent_plan_misalignment"

    def test_invention_of_new_information(self):
        assert _map_category("Invention of new information") == "invention_of_new_information"

    def test_system_failure(self):
        assert _map_category("System Failure") == "system_failure"

    def test_invalid_invocation_skipped(self):
        assert _map_category("Invalid Invocation") is None

    def test_unknown_category_returns_none(self):
        assert _map_category("Unknown Category") is None


class TestNormalizePattern:
    def test_hides_paths(self):
        pat = normalize_error_pattern("Error: /some/path/here.py not found")
        assert "/some/path" not in pat
        assert "/X" in pat

    def test_hides_strings(self):
        pat = normalize_error_pattern("Error: 'some long string 123'")
        assert "long string" not in pat
        assert "'X'" in pat


class TestCATEGORY_MAP:
    def test_invalid_invocation_is_none(self):
        assert CATEGORY_MAP["Invalid Invocation"] is None

    def test_system_failure_mapped(self):
        assert CATEGORY_MAP["System Failure"] == "system_failure"