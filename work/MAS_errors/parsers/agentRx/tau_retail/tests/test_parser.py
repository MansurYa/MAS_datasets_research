import pytest
from work.MAS_errors.parsers.agentRx.tau_retail.parser import (
    normalize_error_pattern,
    _map_category,
    CATEGORY_MAP,
)


class TestCategoryMapper:
    def test_instruction_adherence_failure(self):
        assert _map_category("Instruction Adherence Failure") == "instruction_adherence_failure"

    def test_intent_not_supported(self):
        assert _map_category("Intent Not Supported") == "intent_not_supported"

    def test_intent_plan_misalignment(self):
        assert _map_category("Intent Plan Misalignment") == "intent_plan_misalignment"

    def test_misinterpretation_of_tool_output(self):
        assert _map_category("Misinterpretation of Tool Output") == "misinterpretation_of_tool_output"

    def test_system_failure(self):
        assert _map_category("System Failure") == "system_failure"

    def test_underspecified_falls_back_to_intent_not_supported(self):
        assert _map_category("Underspecified User Intent") == "intent_not_supported"

    def test_invalid_invocation_skipped(self):
        assert _map_category("Invalid Invocation") is None


class TestNormalizePattern:
    def test_hides_paths(self):
        pat = normalize_error_pattern("Error: /some/path/here.py not found")
        assert "/some/path" not in pat
        assert "/X" in pat


class TestCATEGORY_MAP:
    def test_underspecified_user_intent_maps_to_intent_not_supported(self):
        assert CATEGORY_MAP["Underspecified User Intent"] == "intent_not_supported"

    def test_invalid_invocation_is_none(self):
        assert CATEGORY_MAP["Invalid Invocation"] is None