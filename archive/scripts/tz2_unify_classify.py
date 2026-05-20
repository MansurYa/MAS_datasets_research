"""ТЗ №2 — Унификация таксономии, классификация ошибок, базовая статистика."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

AGENTRX_DIR = ROOT / "microsoft-AgentRx"
WW_DIR = ROOT / "Kevin355-Who_and_When"

# ── Taxonomy unification map ──────────────────────────────────────────────────
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

# ── Keyword rules (priority = order) ─────────────────────────────────────────
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


def classify_text(text: str) -> str:
    if not isinstance(text, str):
        return "unclassified"
    t = text.lower()
    for category, keywords in KEYWORD_RULES:
        if any(kw in t for kw in keywords):
            return category
    return "unclassified"


# ── Load AgentRx ──────────────────────────────────────────────────────────────
def load_agentrx(fname: str) -> pd.DataFrame:
    rows = []
    with open(AGENTRX_DIR / fname) as f:
        for line in f:
            obj = json.loads(line)
            traj_id = obj["trajectory_id"]
            for fail in obj.get("failures", []):
                rows.append({
                    "source": fname.replace(".jsonl", ""),
                    "trajectory_id": traj_id,
                    "category_original": fail.get("failure_category", ""),
                    "category_unified": UNIFICATION_MAP.get(fail.get("failure_category", ""), "unknown"),
                    "step_number": fail.get("step_number"),
                    "text_snippet": (fail.get("step_reason") or "")[:100],
                })
    return pd.DataFrame(rows)


# ── Load Who&When ─────────────────────────────────────────────────────────────
def load_who_and_when() -> pd.DataFrame:
    dfs = []
    for fname in ["Algorithm-Generated.parquet", "Hand-Crafted.parquet"]:
        df = pd.read_parquet(WW_DIR / fname)
        df["_source_file"] = fname
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)

    rows = []
    for _, row in df.iterrows():
        reason = row.get("mistake_reason")
        step_raw = row.get("mistake_step")
        try:
            step = int(step_raw) if step_raw is not None else None
        except (ValueError, TypeError):
            step = None
        rows.append({
            "source": "who_and_when",
            "trajectory_id": row.get("question_ID", ""),
            "category_original": reason if isinstance(reason, str) else "",
            "category_unified": classify_text(reason),
            "step_number": step,
            "text_snippet": (reason[:100] if isinstance(reason, str) else ""),
        })
    return pd.DataFrame(rows)


# ── Wilson CI ─────────────────────────────────────────────────────────────────
def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 0.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


# ── Stats per (category, source) ─────────────────────────────────────────────
TOTAL_TRAJECTORIES = {
    "magentic_one": 44,
    "tau_retail": 29,
    "who_and_when": 184,
}


def compute_stats(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (cat, src), grp in df.groupby(["category_unified", "source"]):
        n_fail = len(grp)
        n_traj = grp["trajectory_id"].nunique()
        n_total = TOTAL_TRAJECTORIES.get(src, n_traj)
        p = n_traj / n_total if n_total else 0.0
        ci_lo, ci_hi = wilson_ci(n_traj, n_total)

        steps = grp["step_number"].dropna().astype(float)
        step_stats = {}
        if len(steps) > 0:
            step_stats = {
                "step_mean": round(steps.mean(), 2),
                "step_median": round(steps.median(), 2),
                "step_std": round(steps.std(), 2) if len(steps) > 1 else 0.0,
                "step_p25": round(steps.quantile(0.25), 2),
                "step_p75": round(steps.quantile(0.75), 2),
                "step_min": int(steps.min()),
                "step_max": int(steps.max()),
                "step_n": len(steps),
            }
        else:
            step_stats = {k: None for k in
                          ["step_mean", "step_median", "step_std", "step_p25", "step_p75",
                           "step_min", "step_max", "step_n"]}

        rows.append({
            "category": cat,
            "source": src,
            "n_failures": n_fail,
            "n_trajectories_with_error": n_traj,
            "n_trajectories_total": n_total,
            "p_trajectory": round(p, 4),
            "ci_lower": round(ci_lo, 4),
            "ci_upper": round(ci_hi, 4),
            "insufficient_data": n_traj < 20,
            **step_stats,
        })
    return pd.DataFrame(rows).sort_values(["source", "n_failures"], ascending=[True, False])


# ── Report generation ─────────────────────────────────────────────────────────
def df_to_md_table(df: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(df.columns)) + "|")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(v) if v is not None else "" for v in row) + " |")
    return "\n".join(lines)


def generate_report(unified_taxonomy: dict, all_df: pd.DataFrame, stats_df: pd.DataFrame) -> str:
    lines = ["# ТЗ №2 — Унификация таксономии и классификация ошибок", "",
             f"**Дата:** 2026-05-04", ""]

    # Section 1: Unified taxonomy
    lines += ["## 1. Унифицированная таксономия AgentRx", ""]
    tax_rows = []
    for orig, unified in sorted(unified_taxonomy.items()):
        # count occurrences
        n = len(all_df[(all_df["source"].isin(["magentic_one", "tau_retail"])) &
                       (all_df["category_original"] == orig)])
        tax_rows.append({"Оригинал": orig, "Унифицированное": unified, "Вхождений": n})
    lines.append(df_to_md_table(pd.DataFrame(tax_rows)))
    lines.append("")

    # Section 2: Who&When classification
    ww = all_df[all_df["source"] == "who_and_when"]
    lines += ["## 2. Результаты классификации Who&When", ""]
    ww_freq = ww["category_unified"].value_counts().reset_index()
    ww_freq.columns = ["Категория", "Кол-во"]
    ww_freq["% от 184"] = (ww_freq["Кол-во"] / 184 * 100).round(1).astype(str) + "%"
    lines.append(df_to_md_table(ww_freq))
    lines.append("")
    n_unclassified = (ww["category_unified"] == "unclassified").sum()
    lines.append(f"**Неклассифицировано:** {n_unclassified} из 184 ({n_unclassified/184*100:.1f}%)")
    lines.append("")

    # Examples per category
    lines += ["### 2.1 Примеры по категориям", ""]
    for cat in ww["category_unified"].unique():
        sample = ww[ww["category_unified"] == cat]["text_snippet"].dropna().head(2).tolist()
        lines.append(f"**{cat}:**")
        for s in sample:
            lines.append(f"- `{s}`")
    lines.append("")

    # Section 3: Stats
    lines += ["## 3. Статистика по категориям", ""]
    stat_cols = ["category", "source", "n_failures", "n_trajectories_with_error",
                 "n_trajectories_total", "p_trajectory", "ci_lower", "ci_upper", "insufficient_data"]
    lines.append(df_to_md_table(stats_df[stat_cols]))
    lines.append("")

    # Section 4: Step distribution
    lines += ["## 4. Распределение ошибок по шагам", ""]
    step_cols = ["category", "source", "step_mean", "step_median", "step_std",
                 "step_p25", "step_p75", "step_min", "step_max", "step_n"]
    step_df = stats_df[step_cols].dropna(subset=["step_mean"])
    lines.append(df_to_md_table(step_df))
    lines.append("")

    # Section 5: Conclusions
    lines += ["## 5. Выводы", ""]
    sufficient = stats_df[~stats_df["insufficient_data"]][["category", "source", "n_trajectories_with_error"]]
    insufficient = stats_df[stats_df["insufficient_data"]][["category", "source", "n_trajectories_with_error"]]

    lines.append("### Категории с достаточным числом данных (n ≥ 20):")
    lines.append("")
    if len(sufficient):
        lines.append(df_to_md_table(sufficient))
    else:
        lines.append("_Нет категорий с n ≥ 20 траекторий_")
    lines.append("")

    lines.append("### Категории с недостаточным числом данных (n < 20):")
    lines.append("")
    if len(insufficient):
        lines.append(df_to_md_table(insufficient))
    lines.append("")

    lines.append("### Рекомендации:")
    lines.append("")
    top_cats = stats_df[~stats_df["insufficient_data"]]["category"].unique().tolist()
    if top_cats:
        lines.append(f"- Для ТЗ №3/4 использовать: {', '.join(f'`{c}`' for c in top_cats)}")
    lines.append(f"- Who&When: {n_unclassified/184*100:.1f}% записей не классифицировано — "
                 "рекомендуется расширить keyword-правила или добавить ручную разметку")
    lines.append("- AgentRx: `instruction_adherence_failure` доминирует (>60% failures в magentic_one) — "
                 "основной источник для статистики по этой категории")

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    DATA_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)

    print("Loading AgentRx...")
    mag_df = load_agentrx("magentic_one.jsonl")
    tau_df = load_agentrx("tau_retail.jsonl")

    print("Loading Who&When...")
    ww_df = load_who_and_when()

    all_df = pd.concat([mag_df, tau_df, ww_df], ignore_index=True)
    print(f"Total errors: {len(all_df)} (AgentRx: {len(mag_df)+len(tau_df)}, Who&When: {len(ww_df)})")

    # Save unified taxonomy
    (DATA_DIR / "unified_taxonomy.json").write_text(
        json.dumps(UNIFICATION_MAP, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Saved data/unified_taxonomy.json")

    # Save classified errors
    all_df.to_csv(DATA_DIR / "errors_classified.csv", index=False)
    print(f"Saved data/errors_classified.csv ({len(all_df)} rows)")

    # Compute stats
    stats_df = compute_stats(all_df)
    stats_df.to_csv(DATA_DIR / "stats_by_category.csv", index=False)
    print(f"Saved data/stats_by_category.csv ({len(stats_df)} rows)")

    # Generate report
    report = generate_report(UNIFICATION_MAP, all_df, stats_df)
    report_path = DOCS_DIR / "tz2_classification_report.md"
    report_path.write_text(report, encoding="utf-8")
    size = report_path.stat().st_size
    print(f"Saved docs/tz2_classification_report.md ({size:,} bytes)")


if __name__ == "__main__":
    main()
