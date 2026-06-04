from __future__ import annotations

DATASETS = [
    "nebius",
    "trail",
    "agentRx",
    "who_and_when",
]

ERROR_TYPES: dict[str, dict[str, list[tuple[str, str | None]]]] = {
    "nebius": {
        "": [
            ("invalid_invocation_A", "A"),
            ("invalid_invocation_B", "B"),
            ("invalid_invocation_E1", "E1"),
            ("invalid_invocation_E2", "E2"),
            ("invalid_invocation_ALL", None),
        ],
    },
    "trail": {
        "": [
            ("instruction_noncompliance", None),
            ("formatting_errors", None),
            ("context_handling_failures", None),
            ("resource_abuse", None),
            ("poor_information_retrieval", None),
            ("incorrect_problem_identification", None),
            ("language_only", None),
            ("tool_related", None),
            ("task_orchestration", None),
            ("goal_deviation", None),
        ],
    },
    "agentRx": {
        "magentic_one": [
            ("instruction_adherence_failure", None),
            ("guardrails_triggered", None),
            ("misinterpretation_of_tool_output", None),
            ("intent_not_supported", None),
            ("intent_plan_misalignment", None),
            ("invention_of_new_information", None),
        ],
        "tau_retail": [
            ("instruction_adherence_failure", None),
            ("intent_not_supported", None),
            ("intent_plan_misalignment", None),
            ("misinterpretation_of_tool_output", None),
            ("system_failure", None),
        ],
    },
    "who_and_when": {
        "": [
            ("wrong_reasoning", None),
            ("processing_error", None),
            ("tool_failure", None),
        ],
    },
}
