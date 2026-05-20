"""ТЗ №4 — Статистический анализ распределений ошибок."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
import math
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
AGENTRX_DIR = ROOT / "microsoft-AgentRx"
WW_DIR = ROOT / "Kevin355-Who_and_When"
DATA_DIR = ROOT / "data"
PLOTS_DIR = DATA_DIR / "plots"
DOCS_DIR = ROOT / "docs"
PLOTS_DIR.mkdir(exist_ok=True)

# ── ERRORS list (from tz3_aggregate.py) ──────────────────────────────────────
ERRORS = [
    {"error_id": "kv_cache_loss",            "name_en": "KV-Cache Loss",                  "name_ru": "Потеря KV-кэша",                     "description": "Loss of local KV-cache state after module restart or state-transfer failure.",                     "trail_category": "Context Handling Failures",             "agentRx_category": None,                                           "modeling_class": 2, "modeling_class_reason": "Directly modeled by removing cached state in IR-graph block."},
    {"error_id": "resource_abuse",           "name_en": "Resource Abuse",                  "name_ru": "Избыточное потребление ресурсов",     "description": "Agent exhausts step budget or repeatedly calls tools without progress.",                           "trail_category": "Resource Abuse",                       "agentRx_category": "resource_abuse",                            "modeling_class": 3, "modeling_class_reason": "Frequency and step distribution estimated statistically."},
    {"error_id": "tool_timeout",             "name_en": "Tool Call Timeout",               "name_ru": "Таймаут вызова инструмента",           "description": "External tool or API call exceeds time limit, causing step failure.",                             "trail_category": "Timeout Issues",                        "agentRx_category": None,                                           "modeling_class": 2, "modeling_class_reason": "Modeled as probabilistic delay/failure on tool-call blocks."},
    {"error_id": "hardware_degradation",     "name_en": "Hardware Degradation",           "name_ru": "Деградация оборудования",               "description": "Long-horizon hardware wear causing latency growth and service failures.",                         "trail_category": "Timeout Issues; Resource Exhaustion",     "agentRx_category": None,                                           "modeling_class": 4, "modeling_class_reason": "Simulator not designed for long-horizon hardware degradation."},
    {"error_id": "gpu_throttling",            "name_en": "GPU Throttling",                  "name_ru": "Троттлинг GPU",                         "description": "GPU frequency drop under thermal/power limits.",                                                 "trail_category": "Timeout Issues; Resource Exhaustion",     "agentRx_category": None,                                           "modeling_class": 4, "modeling_class_reason": "Rare in large clusters; out of scope."},
    {"error_id": "correlated_ssd_failure",    "name_en": "Correlated SSD Failure",          "name_ru": "Коррелированные сбои SSD",              "description": "Simultaneous SSD failures causing data unavailability.",                                         "trail_category": "Resource Not Found; Service Errors",      "agentRx_category": None,                                           "modeling_class": 4, "modeling_class_reason": "Infrastructure-level; out of agent trajectory scope."},
    {"error_id": "network_power_failure",     "name_en": "Network/Power Failure",           "name_ru": "Сетевые и power-сбои",                 "description": "Correlated infrastructure failures causing cascading retries.",                                   "trail_category": "Service Errors; Timeout Issues",           "agentRx_category": None,                                           "modeling_class": 4, "modeling_class_reason": "Infrastructure-level; out of agent trajectory scope."},
    {"error_id": "memory_bandwidth_bottleneck","name_en": "Memory Bandwidth Bottleneck",    "name_ru": "Узкое место по memory bandwidth",        "description": "KV-heavy inference saturates memory bandwidth, reducing throughput.",                             "trail_category": "Timeout Issues; Resource Exhaustion",     "agentRx_category": None,                                           "modeling_class": 2, "modeling_class_reason": "Modeled as throughput reduction parameter on inference blocks."},
    {"error_id": "bad_retry_policy",          "name_en": "Bad Retry Policy",                "name_ru": "Неверная политика ретраев",             "description": "Misconfigured backoff/retry parameters causing retry storms.",                                    "trail_category": "Resource Abuse; Timeout Issues",           "agentRx_category": None,                                           "modeling_class": 2, "modeling_class_reason": "Modeled by setting retry policy parameters in IR-graph blocks."},
    {"error_id": "kv_transfer_failure",       "name_en": "KV-Transfer Failure",             "name_ru": "Сбой KV-transfer",                     "description": "Loss or corruption of KV-state during transfer between decode stages.",                          "trail_category": "Context Handling Failures",               "agentRx_category": None,                                           "modeling_class": 2, "modeling_class_reason": "Modeled as state-transfer failure block in IR-graph."},
    {"error_id": "instruction_adherence_failure", "name_en": "Instruction Adherence Failure","name_ru": "Несоблюдение инструкций",               "description": "Agent deviates from given instructions or plan.",                                                   "trail_category": "Instruction Non-compliance",             "agentRx_category": "instruction_adherence_failure",               "modeling_class": 1, "modeling_class_reason": "Requires full LLM reasoning; cannot be injected structurally."},
    {"error_id": "guardrails_triggered",       "name_en": "Guardrails Triggered",            "name_ru": "Срабатывание защитных ограничений",     "description": "Agent action blocked by safety or policy guardrails.",                                            "trail_category": None,                                       "agentRx_category": "guardrails_triggered",                         "modeling_class": 3, "modeling_class_reason": "Frequency estimated statistically; effect modeled as step-level failure."},
    {"error_id": "misinterpretation_of_tool_output", "name_en": "Misinterpretation of Tool Output", "name_ru": "Неверная интерпретация вывода инструмента","description": "Agent incorrectly reads or parses tool output.",                                                     "trail_category": "Tool Output Misinterpretation",          "agentRx_category": "misinterpretation_of_tool_output",            "modeling_class": 1, "modeling_class_reason": "Semantic misinterpretation requires LLM reasoning."},
    {"error_id": "intent_not_supported",      "name_en": "Intent Not Supported",           "name_ru": "Неподдерживаемое намерение пользователя", "description": "User intent falls outside the agent's capabilities.",                                              "trail_category": None,                                       "agentRx_category": "intent_not_supported",                         "modeling_class": 1, "modeling_class_reason": "Depends on LLM capability assessment."},
    {"error_id": "intent_plan_misalignment",  "name_en": "Intent-Plan Misalignment",        "name_ru": "Несоответствие намерения и плана",       "description": "Agent's execution plan diverges from user's actual intent.",                                       "trail_category": "Goal Deviation",                          "agentRx_category": "intent_plan_misalignment",                     "modeling_class": 1, "modeling_class_reason": "Goal deviation requires LLM-level understanding."},
    {"error_id": "invention_of_new_information", "name_en": "Invention of New Information",  "name_ru": "Изобретение новой информации",           "description": "Agent fabricates facts, IDs, or data not present in context.",                                     "trail_category": "Language-only Hallucination",             "agentRx_category": "invention_of_new_information",                 "modeling_class": 1, "modeling_class_reason": "Hallucination requires full LLM execution."},
    {"error_id": "underspecified_user_intent","name_en": "Underspecified User Intent",       "name_ru": "Недостаточно конкретное намерение",       "description": "User request is ambiguous or incomplete.",                                                         "trail_category": None,                                       "agentRx_category": "underspecified_user_intent",                    "modeling_class": 1, "modeling_class_reason": "Ambiguity resolution depends on LLM reasoning."},
    {"error_id": "invalid_invocation",        "name_en": "Invalid Tool Invocation",         "name_ru": "Некорректный вызов инструмента",          "description": "Agent calls a tool with wrong parameters or in invalid state.",                                   "trail_category": "Tool Definition Issues",                  "agentRx_category": "invalid_invocation",                           "modeling_class": 3, "modeling_class_reason": "Modeled as probabilistic tool-call failure event."},
    {"error_id": "system_failure",            "name_en": "System Failure",                  "name_ru": "Системный сбой",                         "description": "Unexpected system-level error terminating agent execution.",                                     "trail_category": "Service Errors",                           "agentRx_category": "system_failure",                               "modeling_class": 3, "modeling_class_reason": "Modeled as probabilistic hard-failure event."},
    {"error_id": "code_error",                "name_en": "Code Error",                       "name_ru": "Ошибка в коде",                          "description": "Agent generates syntactically or semantically incorrect code.",                                  "trail_category": "Formatting Errors",                       "agentRx_category": None,                                           "modeling_class": 1, "modeling_class_reason": "Code correctness depends on LLM generation."},
    {"error_id": "tool_web_failure",          "name_en": "Tool/Web Access Failure",         "name_ru": "Сбой доступа к инструменту/веб",         "description": "Agent fails to access a URL, file, or external resource.",                                       "trail_category": "Resource Not Found",                       "agentRx_category": None,                                           "modeling_class": 3, "modeling_class_reason": "Modeled as probabilistic tool-call failure."},
    {"error_id": "orchestration_failure",     "name_en": "Orchestration Failure",           "name_ru": "Сбой оркестрации",                       "description": "Orchestrator routes task incorrectly or enters coordination loop.",                             "trail_category": "Task Orchestration",                       "agentRx_category": None,                                           "modeling_class": 1, "modeling_class_reason": "Routing decisions require LLM reasoning."},
    {"error_id": "hallucination",             "name_en": "Hallucination",                   "name_ru": "Галлюцинация",                           "description": "Agent assumes existence of files, IDs, or facts not present.",                                   "trail_category": "Language-only Hallucination",             "agentRx_category": "invention_of_new_information",                 "modeling_class": 1, "modeling_class_reason": "Hallucination requires full LLM execution."},
    {"error_id": "factual_error",             "name_en": "Factual Error",                   "name_ru": "Фактическая ошибка",                     "description": "Agent states incorrect facts or makes wrong assumptions.",                                      "trail_category": "Incorrect Problem Identification",        "agentRx_category": None,                                           "modeling_class": 1, "modeling_class_reason": "Factual correctness depends on LLM knowledge."},
    {"error_id": "misinterpretation",         "name_en": "Misinterpretation",               "name_ru": "Неверная интерпретация",                  "description": "Agent misreads OCR output or extracted values.",                                                "trail_category": "Tool Output Misinterpretation",          "agentRx_category": "misinterpretation_of_tool_output",              "modeling_class": 1, "modeling_class_reason": "Semantic misinterpretation requires LLM reasoning."},
]

UNIFICATION_MAP = {
    "Instruction/Plan Adherence Failure": "instruction_adherence_failure",
    "Instruction Adherence Failure":      "instruction_adherence_failure",
    "Intent not supported":               "intent_not_supported",
    "Intent Not Supported":               "intent_not_supported",
    "Intent Plan Misalignment":           "intent_plan_misalignment",
    "Misinterpretation of Tool Output":   "misinterpretation_of_tool_output",
    "Invention of new information":       "invention_of_new_information",
    "Underspecified User Intent":         "underspecified_user_intent",
    "Guardrails Triggered":               "guardrails_triggered",
    "Invalid Invocation":                 "invalid_invocation",
    "System Failure":                     "system_failure",
}

KEYWORD_RULES = [
    ("hallucination",         ["hallucinate", "fabricat", "made up", "assumes the existence", "placeholder"]),
    ("resource_abuse",        ["exhaustion of the step limits", "step limit", "too many steps", "repeatedly"]),
    ("orchestration_failure", ["orchestrator", "replan", "wrong direction", "should not decide", "should instruct"]),
    ("tool_web_failure",      ["failed to access", "404", " retrieve", "websurfer", "filesurfer",
                               "could not access", "not found", "url", "cloudflare"]),
    ("code_error",            ["code is incorrect", "code is wrong", "python code", "incorrect code",
                               "code provided", " bug ", "syntax", "the code is"]),
    ("factual_error",         ["factual error", "incorrect information", "incorrect assumption",
                               "incorrect fact", "wrong answer"]),
    ("misinterpretation",     ["misinterpret", "misidentif", "incorrect interpretation", "wrong interpretation"]),
]

# ── Helpers ─────────────────────────────────────────────────────────────────────

def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 0.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)

def step_stats(arr):
    a = np.array(arr, dtype=float)
    return dict(
        n=len(a),
        mean=round(float(a.mean()), 2),
        median=float(np.median(a)),
        std=round(float(a.std()), 2),
        min=int(a.min()),
        max=int(a.max()),
        p25=float(np.percentile(a, 25)),
        p75=float(np.percentile(a, 75)),
        p90=float(np.percentile(a, 90)),
        p95=float(np.percentile(a, 95)),
    )

def classify_text(text: str) -> str:
    if not isinstance(text, str):
        return "unclassified"
    t = text.lower()
    for cat, kws in KEYWORD_RULES:
        if any(kw in t for kw in kws):
            return cat
    return "unclassified"

# ── Data loading ───────────────────────────────────────────────────────────────

def load_agentrx_positions():
    """Return {category: [(step, trajectory_id), ...]} for magentic_one + tau_retail."""
    cat_data = {}
    for fname in ["magentic_one.jsonl", "tau_retail.jsonl"]:
        with open(AGENTRX_DIR / fname) as f:
            for line in f:
                obj = json.loads(line)
                traj_id = obj["trajectory_id"]
                for fail in obj.get("failures", []):
                    cat = UNIFICATION_MAP.get(fail.get("failure_category", ""), "unknown")
                    if cat == "unknown":
                        continue
                    step = fail.get("step_number")
                    if step is not None:
                        cat_data.setdefault(cat, []).append((int(step), traj_id))
    return cat_data

def load_agentrx_traj_lens():
    """Return {trajectory_id: len(steps)} from dataset files."""
    lens = {}
    for fname in ["magentic_dataset.jsonl", "tau_retail_dataset.jsonl"]:
        with open(AGENTRX_DIR / fname) as f:
            for line in f:
                obj = json.loads(line)
                lens[obj["trajectory_id"]] = len(obj.get("steps", []))
    return lens

def load_who_when_positions():
    """Return {category: [(step, traj_len), ...]} for both parquets."""
    cat_data = {}
    for fname in ["Algorithm-Generated.parquet", "Hand-Crafted.parquet"]:
        df = pd.read_parquet(WW_DIR / fname)
        for _, row in df.iterrows():
            reason = row.get("mistake_reason", "")
            cat = classify_text(reason) if isinstance(reason, str) else "unclassified"
            step_raw = row.get("mistake_step")
            try:
                step = int(step_raw)
            except (ValueError, TypeError):
                step = None
            hist = row.get("history")
            traj_len = int(len(hist)) if hist is not None else 0
            if step is not None:
                cat_data.setdefault(cat, []).append((step, traj_len))
    return cat_data

def load_dataset_steps():
    """Return {source: total_steps} for AgentRx."""
    total = {}
    for ds_fname, src_name in [
        ("magentic_dataset.jsonl", "magentic_one"),
        ("tau_retail_dataset.jsonl", "tau_retail"),
    ]:
        n_steps = 0
        with open(AGENTRX_DIR / ds_fname) as f:
            for line in f:
                obj = json.loads(line)
                n_steps += len(obj.get("steps", []))
        total[src_name] = n_steps
    return total

def load_ww_steps():
    """Return total_steps for Who&When."""
    total = 0
    for fname in ["Algorithm-Generated.parquet", "Hand-Crafted.parquet"]:
        df = pd.read_parquet(WW_DIR / fname)
        total += sum(len(h) for h in df["history"] if h is not None)
    return total

def load_ww_context_lengths():
    """Return {question_ID: total_chars} for Who&When."""
    result = {}
    for fname in ["Algorithm-Generated.parquet", "Hand-Crafted.parquet"]:
        df = pd.read_parquet(WW_DIR / fname)
        for _, row in df.iterrows():
            hist = row.get("history")
            if hist is not None:
                total_chars = sum(len(str(msg.get("content", "") or "")) for msg in hist)
                result[row["question_ID"]] = total_chars
    return result

# ── Task 1 ─────────────────────────────────────────────────────────────────────

def task1_update_aggregated():
    stats_df = pd.read_csv(DATA_DIR / "stats_by_category.csv")
    rows = []
    for e in ERRORS:
        row = dict(e)
        row["trail_n"] = 0
        row["trail_p"] = None
        row["trail_ci_lower"] = None
        row["trail_ci_upper"] = None

        rx = stats_df[
            (stats_df["category"] == e["error_id"]) &
            (stats_df["source"].isin(["magentic_one", "tau_retail"]))
        ]
        if len(rx):
            rx_n = int(rx["n_trajectories_with_error"].sum())
            rx_total = int(rx["n_trajectories_total"].sum())
            rx_p = round(rx_n / rx_total, 4) if rx_total else None
            lo, hi = wilson_ci(rx_n, rx_total) if rx_total else (None, None)
            row.update(agentRx_n=rx_n, agentRx_p=rx_p,
                       agentRx_ci_lower=lo, agentRx_ci_upper=hi)
        else:
            row.update(agentRx_n=0, agentRx_p=None,
                       agentRx_ci_lower=None, agentRx_ci_upper=None)

        ww = stats_df[
            (stats_df["category"] == e["error_id"]) &
            (stats_df["source"] == "who_and_when")
        ]
        if len(ww):
            ww_r = ww.iloc[0]
            row.update(who_and_when_n=int(ww_r["n_trajectories_with_error"]),
                       who_and_when_p=ww_r["p_trajectory"],
                       who_and_when_ci_lower=ww_r["ci_lower"],
                       who_and_when_ci_upper=ww_r["ci_upper"])
        else:
            row.update(who_and_when_n=0, who_and_when_p=None,
                       who_and_when_ci_lower=None, who_and_when_ci_upper=None)

        total_n = (row["agentRx_n"] or 0) + (row["who_and_when_n"] or 0)
        row["total_n"] = total_n
        row["sufficient_data"] = total_n >= 20
        srcs = []
        if row["agentRx_n"]: srcs.append("agentRx")
        if row["who_and_when_n"]: srcs.append("who_and_when")
        row["sources"] = ", ".join(srcs) if srcs else "none"
        rows.append(row)

    agg = pd.DataFrame(rows)
    agg.to_csv(DATA_DIR / "aggregated_errors.csv", index=False)
    print(f"Task 1: updated aggregated_errors.csv ({len(agg)} rows)")
    print(f"  TRAIL columns zeroed. sufficient_data (n≥20) recalculated.")
    return agg

# ── Task 2 ─────────────────────────────────────────────────────────────────────

def task2_pmessage():
    stats_df = pd.read_csv(DATA_DIR / "stats_by_category.csv")
    agentrx_steps = load_dataset_steps()
    ww_steps_total = load_ww_steps()

    rows = []
    for _, r in stats_df.iterrows():
        src = r["source"]
        n_fail = int(r["n_failures"])
        n_traj = int(r["n_trajectories_with_error"])
        n_total = int(r["n_trajectories_total"])

        if src in ("magentic_one", "tau_retail"):
            total_steps = agentrx_steps.get(src, 0)
        else:
            total_steps = ww_steps_total

        if total_steps > 0:
            p_msg = n_fail / total_steps
            ci_lo, ci_hi = wilson_ci(n_fail, total_steps)
        else:
            p_msg = None
            ci_lo = ci_hi = None

        rows.append({
            "category": r["category"],
            "source": src,
            "n_failures": n_fail,
            "n_trajectories_with_error": n_traj,
            "n_trajectories_total": n_total,
            "p_trajectory": round(float(r["p_trajectory"]), 6) if r["p_trajectory"] is not None else None,
            "p_trajectory_ci_lower": round(float(r["ci_lower"]), 6) if r["ci_lower"] is not None else None,
            "p_trajectory_ci_upper": round(float(r["ci_upper"]), 6) if r["ci_upper"] is not None else None,
            "total_steps": total_steps,
            "p_message": round(p_msg, 8) if p_msg is not None else None,
            "p_message_ci_lower": round(ci_lo, 8) if ci_lo is not None else None,
            "p_message_ci_upper": round(ci_hi, 8) if ci_hi is not None else None,
            "insufficient_data": bool(r["insufficient_data"]),
        })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "stats_full.csv", index=False)
    print(f"Task 2: stats_full.csv ({len(df)} rows)")
    print(f"  AgentRx total_steps: {agentrx_steps}")
    print(f"  Who&When total_steps: {ww_steps_total}")
    return df

# ── Task 3a/3b/3c ──────────────────────────────────────────────────────────────

def save_histogram(values, error_id, position_type):
    """Save histogram PNG."""
    if len(values) == 0:
        return
    v = np.array(values, dtype=float)
    suffix = "rel" if position_type == "normalized" else ""
    fname = f"hist_{suffix}{error_id}.png"
    path = PLOTS_DIR / fname

    if position_type == "normalized":
        bins = np.linspace(0.0, 1.0, 21)
        xlabel = "Normalized Position (step / trajectory_length)"
        title = f"{error_id} — Normalized Position Distribution (n={len(v)})"
    else:
        binwidth = max(1, int(np.ptp(v) / 15) or 1)
        xmin = max(0, int(v.min()) - 1)
        xmax = int(v.max()) + 2
        bins = np.arange(xmin, xmax + binwidth, binwidth)
        xlabel = "Step Number"
        title = f"{error_id} — Absolute Position Distribution (n={len(v)})"

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(v, bins=bins, edgecolor="black", alpha=0.75, color="steelblue")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"  Saved: {path.name} ({path.stat().st_size // 1024} KB)")


DISTRIBUTIONS_ABS = [
    ("exponential", lambda data: stats.expon.fit(data)),
    ("weibull_min", lambda data: stats.weibull_min.fit(data, floc=0)),
    ("lognorm",    lambda data: stats.lognorm.fit(data, floc=0)),
]

DISTRIBUTIONS_NORM = [
    ("exponential", lambda data: stats.expon.fit(data)),
    ("weibull_min", lambda data: stats.weibull_min.fit(data, floc=0)),
    ("lognorm",    lambda data: stats.lognorm.fit(data, floc=0)),
    ("beta",        lambda data: stats.beta.fit(data)),
    ("uniform",     lambda data: stats.uniform.fit(data)),
]

# Mapping name → scipy distribution object for kstest
DIST_OBJECTS = {
    "exponential": stats.expon,
    "weibull_min": stats.weibull_min,
    "lognorm":     stats.lognorm,
    "beta":        stats.beta,
    "uniform":     stats.uniform,
}

KS_WARNING = ("параметры оценены по тем же данным → p-value KS-теста завышен "
              "(сложная гипотеза, §2.2.4 Буре). "
              "Результат теста не является строгим подтверждением подгонки.")


def fit_distributions(data, dists, cat, src, pos_type):
    """Fit distributions, return list of dicts for distributions.csv."""
    n = len(data)
    low_conf = n < 100
    results = []
    for name, fit_fn in dists:
        try:
            params = fit_fn(data)
            # KS test — use the distribution object from DIST_OBJECTS
            dist_obj = DIST_OBJECTS.get(name)
            if dist_obj is not None:
                ks_stat, ks_pval = stats.kstest(data, dist_obj.cdf, args=params)
            else:
                ks_stat, ks_pval = None, None
            params_str = ", ".join(f"{p:.4f}" for p in params)
        except Exception as ex:
            params_str = f"fit_failed: {ex}"
            ks_stat = ks_pval = None

        results.append({
            "category": cat,
            "source": src,
            "position_type": pos_type,
            "distribution": name,
            "params": params_str,
            "ks_statistic": round(ks_stat, 6) if ks_stat is not None else None,
            "ks_pvalue": round(ks_pval, 6) if ks_pval is not None else None,
            "low_confidence": low_conf,
            "ks_warning": KS_WARNING if ks_stat is not None and ks_pval is not None else None,
            "mm_lambda": None,  # filled below for exponential
        })
    return results


def fit_exponential_mm(arr):
    """Return λ̂_MLE and λ̂_MM for exponential distribution."""
    n = len(arr)
    mle_lambda = n / sum(arr)
    mm_lambda = 1.0 / np.mean(arr)
    return round(mle_lambda, 6), round(mm_lambda, 6)


def chi_squared_test(arr):
    """Sturges k, merge bins < 5, need ≥ 3 remaining bins."""
    n = len(arr)
    if n < 5:
        return None

    k = max(2, int(1 + math.log2(n)))
    observed, bin_edges = np.histogram(arr, bins=k)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Merge bins with n_i < 5
    merged_obs = []
    merged_edges = [bin_edges[0]]
    i = 0
    while i < len(observed):
        if observed[i] < 5 and len(merged_obs) < len(observed) - 1:
            # merge with next
            merged = observed[i]
            j = i + 1
            while j < len(observed) and merged < 5 and j < len(observed) - 1:
                merged += observed[j]
                j += 1
            merged_obs.append(merged)
            merged_edges.append(bin_edges[j])
            i = j
        else:
            merged_obs.append(observed[i])
            merged_edges.append(bin_edges[i + 1])
            i += 1

    # If < 3 bins remain, chi-squared not applicable
    if len(merged_obs) < 3:
        return {"note": "chi-squared неприменим при данном n (менее 3 бинов после объединения)"}

    # Expected frequencies (uniform)
    total = sum(merged_obs)
    expected = [total / len(merged_obs)] * len(merged_obs)

    try:
        chi2_stat, chi2_pval = stats.chisquare(merged_obs, f_exp=expected)
        return {
            "k_bins": len(merged_obs),
            "chi2_statistic": round(chi2_stat, 4),
            "chi2_pvalue": round(chi2_pval, 6),
            "note": None,
        }
    except Exception as ex:
        return {"note": f"chi-squared error: {ex}"}


def task3(step_stats_rows, dist_rows, chi2_rows):
    rx_positions = load_agentrx_positions()
    ww_positions = load_who_when_positions()
    rx_traj_lens = load_agentrx_traj_lens()

    # Determine which errors have n ≥ 20
    eligible = {cat for cat, vals in {**rx_positions, **ww_positions}.items() if len(vals) >= 20}
    print(f"Task 3: eligible errors (n≥20): {eligible}")

    for cat in eligible:
        src = "agentRx" if cat in rx_positions else "who_and_when"

        # Collect absolute positions and normalized positions
        if cat in rx_positions:
            steps = [s for s, _ in rx_positions[cat]]
            traj_ids = [tid for _, tid in rx_positions[cat]]
            traj_lens = [rx_traj_lens.get(tid, None) for tid in traj_ids]
        else:
            steps = [s for s, _ in ww_positions[cat]]
            traj_lens = [tl for _, tl in ww_positions[cat]]

        # Absolute positions
        s_abs = step_stats(steps)
        step_stats_rows.append({"category": cat, "source": src,
                                 "position_type": "absolute", **s_abs})
        save_histogram(steps, cat, "absolute")

        # Normalized positions
        norm_vals = []
        for i, step in enumerate(steps):
            if src == "agentRx":
                tl = traj_lens[i]
            else:
                tl = traj_lens[i]
            if tl and tl > 0:
                norm_vals.append(step / tl)

        if len(norm_vals) >= 20:
            s_norm = step_stats(norm_vals)
            step_stats_rows.append({"category": cat, "source": src,
                                     "position_type": "normalized", **s_norm})
            save_histogram(norm_vals, cat, "normalized")

            # Fit distributions
            dists = DISTRIBUTIONS_ABS if cat not in eligible else DISTRIBUTIONS_ABS
            abs_results = fit_distributions(steps, DISTRIBUTIONS_ABS, cat, src, "absolute")
            norm_results = fit_distributions(norm_vals, DISTRIBUTIONS_NORM, cat, src, "normalized")

            # Exponential MM for absolute
            if len(steps) >= 5:
                mle_l, mm_l = fit_exponential_mm(np.array(steps, dtype=float))
                for res in abs_results:
                    if res["distribution"] == "exponential":
                        res["mm_lambda"] = mm_l
                        res["ks_warning"] = (
                            f"{KS_WARNING} "
                            f"λ̂_MLE={mle_l:.6f}, λ̂_MM={mm_l:.6f}. "
                            f"{'Близки, дополнительное подтверждение.' if abs(mle_l-mm_l)/mle_l < 0.1 else 'Различаются >10%.'}"
                        )

            dist_rows.extend(abs_results)
            dist_rows.extend(norm_results)

            # Chi-squared
            chi2_abs = chi_squared_test(steps)
            if chi2_abs:
                chi2_abs.update(category=cat, source=src, position_type="absolute")
                chi2_rows.append(chi2_abs)
            chi2_norm = chi_squared_test(norm_vals)
            if chi2_norm:
                chi2_norm.update(category=cat, source=src, position_type="normalized")
                chi2_rows.append(chi2_norm)

# ── Task 4 ─────────────────────────────────────────────────────────────────────

def task4():
    """Context length analysis for Who&When."""
    ww_positions = load_who_when_positions()
    ww_context = load_ww_context_lengths()

    eligible = {cat for cat, vals in ww_positions.items() if len(vals) >= 20}
    print(f"Task 4: eligible errors for context analysis: {eligible}")

    if not eligible:
        print("Task 4: No errors with n≥20 in Who&When for context analysis.")
        return

    for cat in eligible:
        cat_vals = ww_positions[cat]
        context_vals = []
        for step, traj_len in cat_vals:
            # Map to question_ID — we don't have it directly from positions
            # For Who&When, context at mistake_step = sum of chars of history up to mistake_step
            # Since we only have total_chars, use total_chars as proxy
            pass

        # Use question_ID from the full who_when loading — collect all question_IDs per category
        # Reload to get question_IDs
        context_data = {}
        for fname in ["Algorithm-Generated.parquet", "Hand-Crafted.parquet"]:
            df = pd.read_parquet(WW_DIR / fname)
            for _, row in df.iterrows():
                reason = row.get("mistake_reason", "")
                cat2 = classify_text(reason) if isinstance(reason, str) else "unclassified"
                step_raw = row.get("mistake_step")
                try:
                    step = int(step_raw)
                except:
                    step = None
                hist = row.get("history")
                traj_len = len(hist) if hist is not None else 0
                if step is not None and cat2 == cat:
                    # total chars as proxy for context length
                    total_chars = sum(len(str(msg.get("content", "") or "")) for msg in hist)
                    context_data.setdefault(cat, []).append(total_chars)

        if cat in context_data:
            vals = context_data[cat]
            if len(vals) >= 20:
                save_histogram(vals, cat, "context_length")
                print(f"  Saved context histogram for {cat} (n={len(vals)})")


# ── Report ─────────────────────────────────────────────────────────────────────

def df_to_md_table(df):
    if df.empty:
        return "_Нет данных_"
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(df.columns)) + "|")
    for _, row in df.iterrows():
        vals = []
        for v in row:
            if v is None or (isinstance(v, float) and (math.isnan(v) or v == 0)):
                vals.append("—")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def generate_report():
    stats_full = pd.read_csv(DATA_DIR / "stats_full.csv")
    step_stats_df = pd.read_csv(DATA_DIR / "step_stats.csv")
    dist_df = pd.read_csv(DATA_DIR / "distributions.csv")
    chi2_df = pd.read_csv(DATA_DIR / "chi2_tests.csv")

    lines = [
        "# ТЗ №4 — Статистический анализ распределений ошибок",
        "",
        f"**Дата:** 2026-05-04",
        "**Примечание:** Датасет TRAIL исключён (синтетический). "
        "Все расчёты выполнены заново с нуля.",
        "",
    ]

    # ── Section 1: Full statistics ──────────────────────────────────────────
    lines += ["## 1. Обновлённая базовая статистика", ""]

    # P(trajectory) table
    traj_cols = ["category", "source", "n_trajectories_with_error", "n_trajectories_total",
                 "p_trajectory", "p_trajectory_ci_lower", "p_trajectory_ci_upper",
                 "total_steps", "p_message", "p_message_ci_lower", "p_message_ci_upper",
                 "insufficient_data"]
    sf = stats_full[traj_cols].copy()
    sf["p_trajectory"] = sf["p_trajectory"].apply(
        lambda x: f"{x:.4f}" if x is not None and not (isinstance(x, float) and math.isnan(x)) else "—")
    sf["ci"] = sf.apply(lambda r: f"[{r['p_trajectory_ci_lower']:.4f}, {r['p_trajectory_ci_upper']:.4f}]"
                        if r['p_trajectory_ci_lower'] is not None else "—", axis=1)
    sf["p_message_disp"] = sf["p_message"].apply(
        lambda x: f"{x:.6f}" if x is not None and not (isinstance(x, float) and math.isnan(x)) else "—")
    sf["pmsg_ci"] = sf.apply(lambda r: f"[{r['p_message_ci_lower']:.6f}, {r['p_message_ci_upper']:.6f}]"
                             if r['p_message_ci_lower'] is not None else "—", axis=1)

    display_df = sf[["category", "source", "n_trajectories_with_error", "n_trajectories_total",
                     "p_trajectory", "ci", "total_steps", "p_message_disp", "pmsg_ci", "insufficient_data"]].rename(
        columns={"ci": "P(traj)_CI95", "p_message_disp": "P(msg)", "pmsg_ci": "P(msg)_CI95"}
    )
    lines.append(df_to_md_table(display_df))
    lines.append("")
    lines.append(f"_P(traj) = n_trajectories_with_error / n_trajectories_total;_ "
                 f"_P(msg) = n_failures / total_steps._")
    lines.append("")

    # Errors with no data
    class23 = [
        "kv_cache_loss", "tool_timeout", "memory_bandwidth_bottleneck",
        "bad_retry_policy", "kv_transfer_failure", "hardware_degradation",
        "gpu_throttling", "correlated_ssd_failure", "network_power_failure",
    ]
    no_data = [
        ("kv_cache_loss", "Class 2", "Эмпирических данных нет. Параметры требуют экспертной оценки."),
        ("tool_timeout", "Class 2", "Эмпирических данных нет. Параметры требуют экспертной оценки."),
        ("memory_bandwidth_bottleneck", "Class 2", "Эмпирических данных нет. Параметры требуют экспертной оценки."),
        ("bad_retry_policy", "Class 2", "Эмпирических данных нет. Параметры требуют экспертной оценки."),
        ("kv_transfer_failure", "Class 2", "Эмпирических данных нет. Параметры требуют экспертной оценки."),
        ("hardware_degradation", "Class 4", "Класс 4. Нецелесообразно моделировать."),
        ("gpu_throttling", "Class 4", "Класс 4. Нецелесообразно моделировать."),
        ("correlated_ssd_failure", "Class 4", "Класс 4. Нецелесообразно моделировать."),
        ("network_power_failure", "Class 4", "Класс 4. Нецелесообразно моделировать."),
    ]
    if no_data:
        lines += ["### 1.1 Ошибки без эмпирических данных (классы 2, 3, 4)", ""]
        nd_df = pd.DataFrame(no_data, columns=["error_id", "класс", "примечание"])
        lines.append(df_to_md_table(nd_df))
        lines.append("")

    # ── Section 2: Distribution analysis ─────────────────────────────────────
    lines += ["## 2. Анализ распределений", ""]

    # Only for errors with n >= 20
    dist_errors = step_stats_df["category"].unique()
    for cat in dist_errors:
        for pos_type in ["absolute", "normalized"]:
            srow = step_stats_df[
                (step_stats_df["category"] == cat) &
                (step_stats_df["position_type"] == pos_type)
            ]
            if srow.empty:
                continue
            sr = srow.iloc[0]
            n = int(sr["n"])
            src = sr["source"]

            lines.append(f"### 2.{1 if cat=='guardrails_triggered' and pos_type=='absolute' else 'X'} "
                         f"`{cat}` — {pos_type}")
            lines.append("")

            # Descriptive stats
            stat_vals = {
                "n": int(sr["n"]),
                "mean": sr["mean"],
                "median": sr["median"],
                "std": sr["std"],
                "min": int(sr["min"]),
                "max": int(sr["max"]),
                "p25": sr["p25"],
                "p75": sr["p75"],
                "p90": sr["p90"],
                "p95": sr["p95"],
            }
            stat_df = pd.DataFrame([stat_vals]).T.reset_index()
            stat_df.columns = ["Метрика", "Значение"]
            lines.append(df_to_md_table(stat_df))
            lines.append("")

            # Histogram
            suffix = "rel" if pos_type == "normalized" else ""
            fname = f"hist_{suffix}{cat}.png"
            plot_path = PLOTS_DIR / fname
            if plot_path.exists():
                lines.append(f"![{cat} {pos_type}]({plot_path.relative_to(ROOT)})")
            lines.append("")

            # Distribution fitting
            dist_rows = dist_df[
                (dist_df["category"] == cat) &
                (dist_df["position_type"] == pos_type)
            ]
            if len(dist_rows):
                lines.append("**Подгонка распределений:**")
                lines.append("")
                d_disp = dist_rows[["distribution", "params", "ks_statistic", "ks_pvalue", "mm_lambda"]].copy()
                d_disp["ks_warning"] = dist_rows["ks_warning"].apply(
                    lambda x: "⚠️" if isinstance(x, str) and len(x) > 10 else "")
                d_disp["low_confidence"] = dist_rows["low_confidence"].apply(lambda x: "⚠️ n<100" if x else "")
                lines.append(df_to_md_table(d_disp))
                lines.append("")

                # KS warning + MLE vs MM comparison
                for _, dr in dist_rows.iterrows():
                    if dr["ks_warning"] and isinstance(dr["ks_warning"], str) and len(dr["ks_warning"]) > 10:
                        lines.append(f"⚠️ {dr['ks_warning']}")
                        lines.append("")
                if n < 100:
                    lines.append(f"⚠️ n={n}, n<<3000. Результаты носят иллюстративный характер. "
                                  "Нельзя делать уверенных выводов о виде распределения.")
                    lines.append("")

            # Chi-squared
            c2rows = chi2_df[
                (chi2_df["category"] == cat) &
                (chi2_df["position_type"] == pos_type)
            ]
            if len(c2rows):
                c2r = c2rows.iloc[0]
                note = c2r.get("note")
                if note:
                    lines.append(f"**Chi-squared:** {note}")
                else:
                    lines.append(f"**Chi-squared:** k={int(c2r['k_bins'])} bins, "
                                 f"χ²={c2r['chi2_statistic']:.4f}, p={c2r['chi2_pvalue']:.4f}")
                lines.append("")

    # ── Section 3: Context length ─────────────────────────────────────────────
    lines += ["## 3. Анализ контекстной длины", ""]
    context_plots = list(PLOTS_DIR.glob("hist_*context_length*.png"))
    if context_plots:
        lines.append("Распределение длины контекста (total_chars) для ошибок Who&When с n≥20:")
        lines.append("")
        for p in context_plots:
            lines.append(f"![{p.stem}]({p.relative_to(ROOT)})")
            lines.append("")
    else:
        lines.append("Данные о длине контекста доступны для Who&When (total_chars из history), "
                     "но ни одна категория не имеет n≥20 ошибок с привязкой к question_ID "
                     "для надёжного анализа.")
        lines.append("")

    # ── Section 4: Limitations ────────────────────────────────────────────────
    lines += [
        "## 4. Ограничения",
        "",
        "1. **TRAIL исключён** — синтетический источник, параметры не подтверждены экспериментально.",
        "2. **n<<3000 для всех ошибок** — нельзя делать уверенных выводов о виде распределения.",
        "3. **Keyword matching для Who&When** — покрытие ~54% (85/184 записей не классифицировано).",
        "4. **KS-тест** — параметры оценены по тем же данным, что и тестируются "
           "(сложная гипотеза, §2.2.4 Буре), p-value завышено.",
        "5. **P(message)** — использует фактическое число шагов в траекториях, "
           "но не учитывает вариативность длины контекста.",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ТЗ №4 — Статистический анализ распределений ошибок")
    print("=" * 60)

    task1_update_aggregated()
    task2_pmessage()

    # Initialise output lists
    step_stats_rows = []
    dist_rows = []
    chi2_rows = []

    task3(step_stats_rows, dist_rows, chi2_rows)

    # Save step_stats.csv
    step_stats_df = pd.DataFrame(step_stats_rows)
    if not step_stats_df.empty:
        step_stats_df.to_csv(DATA_DIR / "step_stats.csv", index=False)
        print(f"  step_stats.csv: {len(step_stats_df)} rows")
    else:
        # Create empty with correct columns
        pd.DataFrame(columns=[
            "category", "source", "position_type", "n", "mean", "median",
            "std", "min", "max", "p25", "p75", "p90", "p95"
        ]).to_csv(DATA_DIR / "step_stats.csv", index=False)
        print("  step_stats.csv: empty (no errors with n≥20)")

    # Save distributions.csv
    dist_df = pd.DataFrame(dist_rows)
    if not dist_df.empty:
        dist_df.to_csv(DATA_DIR / "distributions.csv", index=False)
        print(f"  distributions.csv: {len(dist_df)} rows")
    else:
        pd.DataFrame(columns=[
            "category", "source", "position_type", "distribution", "params",
            "ks_statistic", "ks_pvalue", "low_confidence", "ks_warning", "mm_lambda"
        ]).to_csv(DATA_DIR / "distributions.csv", index=False)

    # Save chi2_tests.csv
    chi2_df = pd.DataFrame(chi2_rows)
    if not chi2_df.empty:
        chi2_df.to_csv(DATA_DIR / "chi2_tests.csv", index=False)
        print(f"  chi2_tests.csv: {len(chi2_df)} rows")
    else:
        pd.DataFrame(columns=[
            "category", "source", "position_type", "k_bins",
            "chi2_statistic", "chi2_pvalue", "note"
        ]).to_csv(DATA_DIR / "chi2_tests.csv", index=False)

    task4()

    print("\nGenerating report...")
    report = generate_report()
    report_path = DOCS_DIR / "tz4_distributions_report.md"
    report_path.write_text(report, encoding="utf-8")
    size = report_path.stat().st_size
    print(f"  Report saved: docs/tz4_distributions_report.md ({size:,} bytes)")

    print("\nDone.")


if __name__ == "__main__":
    main()