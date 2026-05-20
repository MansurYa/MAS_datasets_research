"""ТЗ №3 — Агрегированная таблица ошибок с классификацией."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

# ── Master error list ─────────────────────────────────────────────────────────
# Fields: error_id, name_en, name_ru, description, trail_category, agentRx_category,
#         modeling_class, modeling_class_reason
# Sources encoded separately via stats merge

ERRORS = [
    # ── TRAIL errors ──────────────────────────────────────────────────────────
    {
        "error_id": "kv_cache_loss",
        "name_en": "KV-Cache Loss",
        "name_ru": "Потеря KV-кэша",
        "description": "Loss of local KV-cache state after module restart or state-transfer failure. Causes incorrect continuation or repeated steps.",
        "trail_category": "Context Handling Failures",
        "agentRx_category": None,
        "modeling_class": 2,
        "modeling_class_reason": "Directly modeled by removing cached state in IR-graph block; no LLM required.",
    },
    {
        "error_id": "resource_abuse",
        "name_en": "Resource Abuse",
        "name_ru": "Избыточное потребление ресурсов",
        "description": "Agent exhausts step budget or repeatedly calls tools without progress, consuming excessive resources.",
        "trail_category": "Resource Abuse",
        "agentRx_category": "resource_abuse",
        "modeling_class": 3,
        "modeling_class_reason": "Cannot reproduce without LLM reasoning, but frequency and step distribution can be estimated statistically.",
    },
    {
        "error_id": "tool_timeout",
        "name_en": "Tool Call Timeout",
        "name_ru": "Таймаут вызова инструмента",
        "description": "External tool or API call exceeds time limit, causing step failure or retry.",
        "trail_category": "Timeout Issues",
        "agentRx_category": None,
        "modeling_class": 2,
        "modeling_class_reason": "Modeled directly as a probabilistic delay/failure on tool-call blocks in IR-graph.",
    },
    {
        "error_id": "hardware_degradation",
        "name_en": "Hardware Degradation",
        "name_ru": "Деградация оборудования",
        "description": "Long-horizon hardware wear causing latency growth, queue buildup, and service failures.",
        "trail_category": "Timeout Issues; Resource Exhaustion; Service Errors",
        "agentRx_category": None,
        "modeling_class": 4,
        "modeling_class_reason": "Technically feasible but simulator is not designed for long-horizon hardware degradation scenarios.",
    },
    {
        "error_id": "gpu_throttling",
        "name_en": "GPU Throttling",
        "name_ru": "Троттлинг GPU",
        "description": "GPU frequency drop under thermal/power limits causing throughput reduction and queue growth.",
        "trail_category": "Timeout Issues; Resource Exhaustion",
        "agentRx_category": None,
        "modeling_class": 4,
        "modeling_class_reason": "Rarely occurs in large clusters; out of scope for the simulator's target scenarios.",
    },
    {
        "error_id": "correlated_ssd_failure",
        "name_en": "Correlated SSD Failure",
        "name_ru": "Коррелированные сбои SSD",
        "description": "Simultaneous SSD failures causing data unavailability or service errors.",
        "trail_category": "Resource Not Found; Service Errors; Timeout Issues",
        "agentRx_category": None,
        "modeling_class": 4,
        "modeling_class_reason": "Infrastructure-level failure outside the scope of agent trajectory simulation.",
    },
    {
        "error_id": "network_power_failure",
        "name_en": "Network/Power Failure",
        "name_ru": "Сетевые и power-сбои",
        "description": "Correlated infrastructure failures above compute module level causing cascading retries.",
        "trail_category": "Service Errors; Timeout Issues; Resource Not Found",
        "agentRx_category": None,
        "modeling_class": 4,
        "modeling_class_reason": "Infrastructure-level failure outside the scope of agent trajectory simulation.",
    },
    {
        "error_id": "memory_bandwidth_bottleneck",
        "name_en": "Memory Bandwidth Bottleneck",
        "name_ru": "Узкое место по memory bandwidth",
        "description": "KV-heavy inference saturates memory bandwidth, reducing throughput and causing retry amplification.",
        "trail_category": "Timeout Issues; Resource Exhaustion; Resource Abuse",
        "agentRx_category": None,
        "modeling_class": 2,
        "modeling_class_reason": "Modeled directly as throughput reduction parameter on inference blocks in IR-graph.",
    },
    {
        "error_id": "bad_retry_policy",
        "name_en": "Bad Retry Policy",
        "name_ru": "Неверная политика ретраев",
        "description": "Misconfigured backoff/retry parameters causing retry storms or excessive delays.",
        "trail_category": "Resource Abuse; Timeout Issues; Task Orchestration",
        "agentRx_category": None,
        "modeling_class": 2,
        "modeling_class_reason": "Directly modeled by setting retry policy parameters in IR-graph blocks.",
    },
    {
        "error_id": "kv_transfer_failure",
        "name_en": "KV-Transfer Failure",
        "name_ru": "Сбой KV-transfer",
        "description": "Loss or corruption of KV-state during transfer between decode stages, breaking continuation.",
        "trail_category": "Context Handling Failures",
        "agentRx_category": None,
        "modeling_class": 2,
        "modeling_class_reason": "Directly modeled as state-transfer failure block in IR-graph.",
    },
    # ── AgentRx errors ────────────────────────────────────────────────────────
    {
        "error_id": "instruction_adherence_failure",
        "name_en": "Instruction Adherence Failure",
        "name_ru": "Несоблюдение инструкций",
        "description": "Agent deviates from given instructions or plan, producing outputs that violate explicit constraints.",
        "trail_category": "Instruction Non-compliance",
        "agentRx_category": "instruction_adherence_failure",
        "modeling_class": 1,
        "modeling_class_reason": "Requires full LLM reasoning to reproduce; cannot be injected as a structural IR-graph event.",
    },
    {
        "error_id": "guardrails_triggered",
        "name_en": "Guardrails Triggered",
        "name_ru": "Срабатывание защитных ограничений",
        "description": "Agent action blocked by safety or policy guardrails, halting task progress.",
        "trail_category": None,
        "agentRx_category": "guardrails_triggered",
        "modeling_class": 3,
        "modeling_class_reason": "Frequency can be estimated statistically; effect modeled as a step-level failure event.",
    },
    {
        "error_id": "misinterpretation_of_tool_output",
        "name_en": "Misinterpretation of Tool Output",
        "name_ru": "Неверная интерпретация вывода инструмента",
        "description": "Agent incorrectly reads or parses tool output, leading to wrong downstream actions.",
        "trail_category": "Tool Output Misinterpretation",
        "agentRx_category": "misinterpretation_of_tool_output",
        "modeling_class": 1,
        "modeling_class_reason": "Semantic misinterpretation requires LLM reasoning; cannot be structurally injected.",
    },
    {
        "error_id": "intent_not_supported",
        "name_en": "Intent Not Supported",
        "name_ru": "Неподдерживаемое намерение",
        "description": "User intent falls outside the agent's capabilities or available tools.",
        "trail_category": None,
        "agentRx_category": "intent_not_supported",
        "modeling_class": 1,
        "modeling_class_reason": "Depends on LLM capability assessment; not reproducible without full model execution.",
    },
    {
        "error_id": "intent_plan_misalignment",
        "name_en": "Intent-Plan Misalignment",
        "name_ru": "Несоответствие намерения и плана",
        "description": "Agent's execution plan diverges from the user's actual intent, solving the wrong problem.",
        "trail_category": "Goal Deviation",
        "agentRx_category": "intent_plan_misalignment",
        "modeling_class": 1,
        "modeling_class_reason": "Goal deviation requires LLM-level understanding of intent; not injectable structurally.",
    },
    {
        "error_id": "invention_of_new_information",
        "name_en": "Invention of New Information",
        "name_ru": "Изобретение новой информации",
        "description": "Agent fabricates facts, IDs, or data not present in context or tool outputs (hallucination variant).",
        "trail_category": "Language-only Hallucination; Tool-related Hallucination",
        "agentRx_category": "invention_of_new_information",
        "modeling_class": 1,
        "modeling_class_reason": "Hallucination requires full LLM execution; cannot be reproduced structurally.",
    },
    {
        "error_id": "underspecified_user_intent",
        "name_en": "Underspecified User Intent",
        "name_ru": "Недостаточно конкретное намерение пользователя",
        "description": "User request is ambiguous or incomplete, causing agent to make incorrect assumptions.",
        "trail_category": None,
        "agentRx_category": "underspecified_user_intent",
        "modeling_class": 1,
        "modeling_class_reason": "Ambiguity resolution depends on LLM reasoning; not injectable as a structural event.",
    },
    {
        "error_id": "invalid_invocation",
        "name_en": "Invalid Tool Invocation",
        "name_ru": "Некорректный вызов инструмента",
        "description": "Agent calls a tool with wrong parameters, missing arguments, or in an invalid state.",
        "trail_category": "Tool Definition Issues",
        "agentRx_category": "invalid_invocation",
        "modeling_class": 3,
        "modeling_class_reason": "Can be modeled as a probabilistic tool-call failure event with estimated frequency.",
    },
    {
        "error_id": "system_failure",
        "name_en": "System Failure",
        "name_ru": "Системный сбой",
        "description": "Unexpected system-level error (crash, OOM, unhandled exception) terminating agent execution.",
        "trail_category": "Service Errors",
        "agentRx_category": "system_failure",
        "modeling_class": 3,
        "modeling_class_reason": "Modeled as a probabilistic hard-failure event on execution blocks.",
    },
    # ── Who&When-only errors ──────────────────────────────────────────────────
    {
        "error_id": "code_error",
        "name_en": "Code Error",
        "name_ru": "Ошибка в коде",
        "description": "Agent generates syntactically or semantically incorrect code that fails to execute or produces wrong output.",
        "trail_category": "Formatting Errors; Environment Setup Errors",
        "agentRx_category": None,
        "modeling_class": 1,
        "modeling_class_reason": "Code correctness depends on LLM generation quality; cannot be injected structurally.",
    },
    {
        "error_id": "tool_web_failure",
        "name_en": "Tool/Web Access Failure",
        "name_ru": "Сбой доступа к инструменту/веб",
        "description": "Agent fails to access a URL, file, or external resource (404, blocked, not found).",
        "trail_category": "Resource Not Found; Service Errors",
        "agentRx_category": None,
        "modeling_class": 3,
        "modeling_class_reason": "Modeled as probabilistic tool-call failure; frequency and step distribution available from data.",
    },
    {
        "error_id": "orchestration_failure",
        "name_en": "Orchestration Failure",
        "name_ru": "Сбой оркестрации",
        "description": "Orchestrator routes task incorrectly, fails to delegate, or enters a coordination loop.",
        "trail_category": "Task Orchestration",
        "agentRx_category": None,
        "modeling_class": 1,
        "modeling_class_reason": "Routing and delegation decisions require LLM reasoning; not injectable structurally.",
    },
    {
        "error_id": "hallucination",
        "name_en": "Hallucination",
        "name_ru": "Галлюцинация",
        "description": "Agent assumes existence of files, IDs, or facts not present in context, acting on fabricated data.",
        "trail_category": "Language-only Hallucination; Tool-related Hallucination",
        "agentRx_category": "invention_of_new_information",
        "modeling_class": 1,
        "modeling_class_reason": "Hallucination requires full LLM execution; cannot be reproduced structurally.",
    },
    {
        "error_id": "factual_error",
        "name_en": "Factual Error",
        "name_ru": "Фактическая ошибка",
        "description": "Agent states incorrect facts or makes wrong assumptions about the world or task context.",
        "trail_category": "Incorrect Problem Identification",
        "agentRx_category": None,
        "modeling_class": 1,
        "modeling_class_reason": "Factual correctness depends on LLM knowledge; not injectable structurally.",
    },
    {
        "error_id": "misinterpretation",
        "name_en": "Misinterpretation",
        "name_ru": "Неверная интерпретация",
        "description": "Agent misreads OCR output, extracted values, or task context, leading to wrong conclusions.",
        "trail_category": "Tool Output Misinterpretation",
        "agentRx_category": "misinterpretation_of_tool_output",
        "modeling_class": 1,
        "modeling_class_reason": "Semantic misinterpretation requires LLM reasoning; not injectable structurally.",
    },
]


# ── TRAIL statistics (from p1_fault_mode_distributions.ipynb outputs) ─────────
# Using trace-level (n=148 traces) Wilson CI values from notebook
TRAIL_STATS = {
    "kv_cache_loss":  {"n": 44, "p": 0.2973, "ci_lower": 0.2295, "ci_upper": 0.3753},
    "resource_abuse": {"n": 42, "p": 0.2838, "ci_lower": 0.2173, "ci_upper": 0.3612},
    "tool_timeout":   {"n": 4,  "p": 0.0270, "ci_lower": 0.0106, "ci_upper": 0.0674},
}


def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 0.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2)) / denom
    return round(max(0.0, center - margin), 4), round(min(1.0, center + margin), 4)


def build_aggregated(errors: list, stats_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for e in errors:
        row = dict(e)

        # TRAIL stats
        ts = TRAIL_STATS.get(e["error_id"])
        if ts:
            row["trail_n"] = ts["n"]
            row["trail_p"] = round(ts["p"], 4)
            row["trail_ci_lower"] = ts["ci_lower"]
            row["trail_ci_upper"] = ts["ci_upper"]
        else:
            row["trail_n"] = 0
            row["trail_p"] = None
            row["trail_ci_lower"] = None
            row["trail_ci_upper"] = None

        # AgentRx stats (magentic_one + tau_retail combined)
        rx = stats_df[
            (stats_df["category"] == e["error_id"]) &
            (stats_df["source"].isin(["magentic_one", "tau_retail"]))
        ]
        if len(rx):
            rx_n = rx["n_trajectories_with_error"].sum()
            rx_total = rx["n_trajectories_total"].sum()
            rx_p = round(rx_n / rx_total, 4) if rx_total else None
            ci_lo, ci_hi = wilson_ci(rx_n, rx_total) if rx_total else (None, None)
            row["agentRx_n"] = int(rx_n)
            row["agentRx_p"] = rx_p
            row["agentRx_ci_lower"] = ci_lo
            row["agentRx_ci_upper"] = ci_hi
        else:
            row["agentRx_n"] = 0
            row["agentRx_p"] = None
            row["agentRx_ci_lower"] = None
            row["agentRx_ci_upper"] = None

        # Who&When stats
        ww = stats_df[
            (stats_df["category"] == e["error_id"]) &
            (stats_df["source"] == "who_and_when")
        ]
        if len(ww):
            ww_row = ww.iloc[0]
            row["who_and_when_n"] = int(ww_row["n_trajectories_with_error"])
            row["who_and_when_p"] = ww_row["p_trajectory"]
            row["who_and_when_ci_lower"] = ww_row["ci_lower"]
            row["who_and_when_ci_upper"] = ww_row["ci_upper"]
        else:
            row["who_and_when_n"] = 0
            row["who_and_when_p"] = None
            row["who_and_when_ci_lower"] = None
            row["who_and_when_ci_upper"] = None

        # Totals
        total_n = (row["trail_n"] or 0) + (row["agentRx_n"] or 0) + (row["who_and_when_n"] or 0)
        row["total_n"] = total_n
        row["sufficient_data"] = total_n >= 20

        # Sources list
        srcs = []
        if row["trail_n"]: srcs.append("trail")
        if row["agentRx_n"]: srcs.append("agentRx")
        if row["who_and_when_n"]: srcs.append("who_and_when")
        row["sources"] = ", ".join(srcs) if srcs else "none"

        rows.append(row)

    return pd.DataFrame(rows)


# ── Report generation ─────────────────────────────────────────────────────────
def df_to_md(df: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(df.columns)) + "|")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join("" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v) for v in row) + " |")
    return "\n".join(lines)


def generate_report(agg: pd.DataFrame) -> str:
    lines = [
        "# ТЗ №3 — Агрегированная таблица ошибок с классификацией",
        "",
        f"**Дата:** 2026-05-04",
        f"**Всего ошибок:** {len(agg)}",
        "",
    ]

    # Section 1: Summary table
    lines += ["## 1. Сводная таблица", ""]
    summary_cols = ["error_id", "name_en", "modeling_class", "total_n", "sufficient_data", "sources"]
    lines.append(df_to_md(agg[summary_cols].sort_values(["modeling_class", "total_n"], ascending=[True, False])))
    lines.append("")

    # Section 2: By modeling class
    lines += ["## 2. Таблица по классам моделирования", ""]
    for cls in [1, 2, 3, 4]:
        subset = agg[agg["modeling_class"] == cls][["error_id", "name_en", "name_ru", "modeling_class_reason"]]
        label = {
            1: "Класс 1 — Невозможно моделировать",
            2: "Класс 2 — Моделируется напрямую",
            3: "Класс 3 — Моделируется статистически",
            4: "Класс 4 — Нецелесообразно моделировать",
        }[cls]
        lines += [f"### {label}", ""]
        lines.append(df_to_md(subset))
        lines.append("")

    # Section 3: Statistics by source
    lines += ["## 3. Статистика по источникам", ""]
    stat_cols = [
        "error_id", "name_en",
        "trail_n", "trail_p", "trail_ci_lower", "trail_ci_upper",
        "agentRx_n", "agentRx_p", "agentRx_ci_lower", "agentRx_ci_upper",
        "who_and_when_n", "who_and_when_p", "who_and_when_ci_lower", "who_and_when_ci_upper",
        "total_n", "sufficient_data",
    ]
    lines.append(df_to_md(agg[stat_cols].sort_values("total_n", ascending=False)))
    lines.append("")

    # Section 4: Conclusions
    lines += ["## 4. Выводы", ""]
    ready = agg[(agg["sufficient_data"]) & (agg["modeling_class"].isin([2, 3]))]
    lines.append("### Ошибки классов 2–3 с sufficient_data=True (готовы к анализу распределений в ТЗ №4):")
    lines.append("")
    if len(ready):
        lines.append(df_to_md(ready[["error_id", "name_en", "modeling_class", "total_n", "sources"]]))
    else:
        lines.append("_Нет ошибок с достаточным числом данных в классах 2–3_")
    lines.append("")

    class_counts = agg["modeling_class"].value_counts().sort_index()
    lines.append("### Распределение по классам:")
    lines.append("")
    for cls, cnt in class_counts.items():
        lines.append(f"- Класс {cls}: {cnt} ошибок")
    lines.append("")

    lines.append("### Источники данных:")
    lines.append("")
    lines.append(f"- TRAIL: {len(TRAIL_STATS)} ошибки с данными (n=148 траекторий)")
    lines.append(f"- AgentRx: {len(agg[agg['agentRx_n'] > 0])} ошибок с данными (magentic_one=44 + tau_retail=29 траекторий)")
    lines.append(f"- Who&When: {len(agg[agg['who_and_when_n'] > 0])} ошибок с данными (n=184 случая)")
    lines.append("")
    lines.append(f"**Итого с sufficient_data=True:** {agg['sufficient_data'].sum()} из {len(agg)}")

    return "\n".join(lines)


def main():
    DATA_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)

    stats_df = pd.read_csv(DATA_DIR / "stats_by_category.csv")

    agg = build_aggregated(ERRORS, stats_df)

    out_csv = DATA_DIR / "aggregated_errors.csv"
    agg.to_csv(out_csv, index=False)
    print(f"Saved {out_csv} ({len(agg)} rows)")

    report = generate_report(agg)
    out_md = DOCS_DIR / "tz3_aggregated_table_report.md"
    out_md.write_text(report, encoding="utf-8")
    print(f"Saved {out_md} ({out_md.stat().st_size:,} bytes)")

    # Quick summary
    print(f"\nModeling class distribution:")
    print(agg["modeling_class"].value_counts().sort_index().to_string())
    print(f"\nSufficient data (n≥20): {agg['sufficient_data'].sum()} errors")
    ready = agg[(agg["sufficient_data"]) & (agg["modeling_class"].isin([2, 3]))]
    print(f"Ready for ТЗ №4 (class 2-3, sufficient): {len(ready)}")
    if len(ready):
        print(ready[["error_id", "modeling_class", "total_n"]].to_string(index=False))


if __name__ == "__main__":
    main()
