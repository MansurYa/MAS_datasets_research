"""Generate TZ 4.6 report."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
PLOTS_DIR = DATA_DIR / "plots"

def fmt(v, digits=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)

def df_to_md(df, drop_null_cols=True):
    if df.empty:
        return "_Нет данных_"
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(df.columns)) + "|")
    for _, row in df.iterrows():
        vals = [fmt(v) for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)

def main():
    kw_stats = pd.read_csv(DATA_DIR / "keyword_stats_full.csv")
    kw_dist = pd.read_csv(DATA_DIR / "keyword_distributions.csv")
    combined = pd.read_csv(DATA_DIR / "all_errors_combined.csv")

    lines = [
        "# ТЗ №4.6 — Полный статистический анализ ошибок из keyword search",
        "",
        "**Дата:** 2026-05-05",
        "",
    ]

    # ── Section 1: Keyword search statistics ───────────────────────────────────
    lines += ["## 1. Статистика keyword search — надёжные пары", ""]
    lines += [
        "Надёжные пары определены в `docs/tz4_5_category_interpretation.md`.",
        "**Примечание:** KS-тест при n >> 3000 (nebius) имеет высокую мощность — "
        "отвержение H0 (p < 0.05) информативно и означает, что стандартное распределение "
        "не подходит для фактических данных.",
        "",
    ]

    tbl_rows = []
    for _, r in kw_stats.iterrows():
        cat = r["category"]
        ds = r["dataset"]
        n = int(r["n_trajectories_with_error"])
        n_total = int(r["n_trajectories_total"])
        p_traj = fmt(r["p_trajectory"])
        ci_lo = fmt(r["p_traj_ci_lower"])
        ci_hi = fmt(r["p_traj_ci_upper"])
        ts = int(r["total_steps"])
        p_msg = fmt(r["p_message"], 6)
        pmsg_lo = fmt(r["p_msg_ci_lower"], 6)
        pmsg_hi = fmt(r["p_msg_ci_upper"], 6)
        insufficient = n < 20

        # Best distribution
        d_rows = kw_dist[(kw_dist["category"] == cat) & (kw_dist["dataset"] == ds) & (kw_dist["position_type"] == "absolute")]
        if len(d_rows) > 0:
            best = d_rows.sort_values("ks_pvalue", ascending=False).iloc[0]
            best_dist = best["distribution"]
            best_ks = fmt(best["ks_statistic"])
            best_p = fmt(best["ks_pvalue"])
            best_params = best["params"]
        else:
            best_dist = best_ks = best_p = best_params = "—"

        tbl_rows.append({
            "category": cat, "dataset": ds,
            "n_trajectories_with_error": n, "n_trajectories_total": n_total,
            "p_trajectory": p_traj, "P(traj)_CI95": f"[{ci_lo}, {ci_hi}]",
            "total_steps": ts,
            "p_message": p_msg, "P(msg)_CI95": f"[{pmsg_lo}, {pmsg_hi}]",
            "insufficient": "⚠️" if insufficient else "",
            "best_dist": best_dist, "best_KS": best_ks, "best_p": best_p,
        })

    display_cols = ["category", "dataset", "n_trajectories_with_error", "n_trajectories_total",
                    "p_trajectory", "P(traj)_CI95", "total_steps", "p_message", "P(msg)_CI95",
                    "insufficient", "best_dist", "best_KS", "best_p"]
    disp_df = pd.DataFrame(tbl_rows)[display_cols]
    lines.append(df_to_md(disp_df))
    lines.append("")
    lines.append("_P(traj) = n_trajectories_with_error / n_trajectories_total;_ "
                 "_P(msg) = n_occurrences_total / total_steps._")
    lines.append("")

    # ── Section 2: Descriptive statistics per pair ───────────────────────────────
    lines += ["## 2. Описательная статистика позиций ошибок", ""]
    lines += [
        "Две версии: абсолютная (номер шага) и нормализованная (step / trajectory_length).",
        "",
    ]

    for _, r in kw_stats.iterrows():
        cat = r["category"]
        ds = r["dataset"]
        n = int(r["step_n"]) if not math.isnan(r["step_n"]) else 0

        lines.append(f"### 2.{list(kw_stats['category']).index(cat)+1} `{cat}` / `{ds}` (n={n})")
        lines.append("")

        for pos_type in ["absolute", "normalized"]:
            d_rows = kw_dist[(kw_dist["category"] == cat) & (kw_dist["dataset"] == ds) & (kw_dist["position_type"] == pos_type)]

            stats_vals = {
                "mean": r["step_mean"] if pos_type == "absolute" else None,
                "median": r["step_median"] if pos_type == "absolute" else None,
                "std": r["step_std"] if pos_type == "absolute" else None,
                "p25": r["step_p25"] if pos_type == "absolute" else None,
                "p75": r["step_p75"] if pos_type == "absolute" else None,
                "p90": r["step_p90"] if pos_type == "absolute" else None,
                "p95": r["step_p95"] if pos_type == "absolute" else None,
            }
            norm_stats = {"mean": None, "median": None, "std": None, "p25": None, "p75": None}

            # For histogram, use the positions CSV
            pos_df = pd.read_csv(DATA_DIR / "keyword_positions.csv")
            pos_subset = pos_df[(pos_df["category"] == cat) & (pos_df["dataset"] == ds)]
            if pos_type == "normalized":
                vals = pos_subset["normalized_position"].tolist()
                stat_col = "normalized_position"
            else:
                vals = pos_subset["first_occurrence_step"].tolist()
                stat_col = "first_occurrence_step"

            # Histogram plot
            suffix = "rel" if pos_type == "normalized" else ""
            plot_fname = f"hist_kw_{suffix}{cat}_{ds}.png"
            plot_path = PLOTS_DIR / plot_fname

            srows = []
            srows.append({"Метрика": "n", "Значение": fmt(len(vals))})
            srows.append({"Метрика": "mean", "Значение": fmt(pd.Series(vals).mean())})
            srows.append({"Метрика": "median", "Значение": fmt(pd.Series(vals).median())})
            srows.append({"Метрика": "std", "Значение": fmt(pd.Series(vals).std())})
            srows.append({"Метрика": "min", "Значение": fmt(min(vals))})
            srows.append({"Метрика": "max", "Значение": fmt(max(vals))})
            srows.append({"Метрика": "p25", "Значение": fmt(pd.Series(vals).quantile(0.25))})
            srows.append({"Метрика": "p75", "Значение": fmt(pd.Series(vals).quantile(0.75))})
            srows.append({"Метрика": "p90", "Значение": fmt(pd.Series(vals).quantile(0.90))})
            srows.append({"Метрика": "p95", "Значение": fmt(pd.Series(vals).quantile(0.95))})
            stat_disp_df = pd.DataFrame(srows)
            lines.append(f"**{pos_type} позиция:**")
            lines.append(df_to_md(stat_disp_df))
            lines.append("")

            if plot_path.exists():
                lines.append(f"![{cat}/{ds} {pos_type}]({plot_path.relative_to(ROOT)})")
                lines.append("")

            # Distribution fitting
            if len(d_rows) > 0:
                lines.append("**Подгонка распределений:**")
                lines.append("")
                d_disp_rows = []
                for _, dr in d_rows.iterrows():
                    row = {
                        "distribution": dr["distribution"],
                        "params": dr["params"],
                        "KS_stat": fmt(dr["ks_statistic"]),
                        "KS_p": fmt(dr["ks_pvalue"]),
                    }
                    if dr.get("note"):
                        row["note"] = "⚠️" if "H0 отвергнута" in str(dr["note"]) else "⚡" if "H0 не отвергнута" in str(dr["note"]) else "⚠️ n<100"
                    else:
                        row["note"] = ""
                    d_disp_rows.append(row)
                d_disp_df = pd.DataFrame(d_disp_rows)
                lines.append(df_to_md(d_disp_df))
                lines.append("")

                # Per-row notes
                for _, dr in d_rows.iterrows():
                    note = dr.get("note")
                    if note and isinstance(note, str) and len(note) > 5:
                        lines.append(f"**{dr['distribution']}:** {note}")
                        lines.append("")
            lines.append("")

    # ── Section 3: Combined table ───────────────────────────────────────────────
    lines += ["## 3. Сводная таблица всех ошибок", ""]
    lines += [
        "Объединены: AgentRx (magentic_one, tau_retail), Who&When (who_and_when), "
        "keyword search (keyword_search_nebius, keyword_search_itbench, keyword_search_terminalbench).",
        "",
    ]

    # Group by modeling_class
    for mc in sorted(combined["modeling_class"].unique()):
        subset = combined[combined["modeling_class"] == mc].copy()
        if mc == 1:
            label = "Класс 1 — Невозможно моделировать (требует LLM)"
        elif mc == 2:
            label = "Класс 2 — Моделируется напрямую"
        elif mc == 3:
            label = "Класс 3 — Моделируется статистически"
        else:
            label = f"Класс {mc}"

        lines.append(f"### {label}")
        lines.append("")

        cols_show = ["error_id", "source", "n_trajectories_with_error", "n_trajectories_total",
                     "p_trajectory", "total_steps", "p_message", "best_distribution",
                     "data_quality", "insufficient_data"]
        disp = subset[cols_show].copy()
        disp["p_trajectory"] = disp["p_trajectory"].apply(lambda x: fmt(x))
        disp["p_message"] = disp["p_message"].apply(lambda x: fmt(x, 6))
        lines.append(df_to_md(disp))
        lines.append("")

    # ── Section 4: Limitations ──────────────────────────────────────────────────
    lines += [
        "## 4. Ограничения",
        "",
        "1. **Ложные срабатывания:** для nebius `tool_web_failure` и `resource_not_found` — "
        "ошибки могут появляться в коде задачи (решаемая проблема), а не как инфраструктурный сбой.",
        "2. **Кластерная структура:** шаги внутри одной траектории не независимы. "
        "Wilson CI для P(message) занижен, так как не учитывает корреляцию.",
        "3. **KS-тест при n >> 3000:** при большом n мощность теста высока — "
        "любое отклонение от модели отвергается. Это не означает, что данные "
        "«плохие»; это означает, что простые аналитические распределения не подходят.",
        "4. **KS-тест при n < 100 (ITBench):** низкая мощность, результаты носят "
        "иллюстративный характер.",
        "5. **n_occurrences_total** для keyword search использует данные из "
        "`keyword_search_results.csv` (ТЗ 4.5), где подсчёт вёлся по всем категориям. "
        "Для надёжных пар это соответствует реальному числу вхождений.",
    ]

    report = "\n".join(lines)
    path = DOCS_DIR / "tz4_6_report.md"
    path.write_text(report, encoding="utf-8")
    size = path.stat().st_size
    print(f"Saved: {path} ({size:,} bytes)")


if __name__ == "__main__":
    main()