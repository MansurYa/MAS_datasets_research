"""Generate TZ 4.7 report."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
PLOTS_DIR = DATA_DIR / "plots"
DOCS_DIR = ROOT / "docs"

RELIABLE_PAIRS = [
    ("tool_web_failure",   "nebius"),
    ("resource_not_found",  "nebius"),
    ("tool_timeout",       "itbench"),
    ("permission_error",   "terminalbench"),
    ("memory_error",       "terminalbench"),
]

MODELING_MAP = {
    "tool_web_failure":   3,
    "resource_not_found":  3,
    "tool_timeout":       2,
    "permission_error":   3,
    "memory_error":       3,
}

MODELING_NAMES = {
    2: "Класс 2 — Моделируется напрямую",
    3: "Класс 3 — Моделируется статистически",
}


def fmt(v, digits=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)


def df_to_md(df):
    if df.empty:
        return "_Нет данных_"
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |"]
    lines.append("|" + "|".join(["---"] * len(df.columns)) + "|")
    for _, row in df.iterrows():
        vals = [fmt(v) for v in row]
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def main():
    dist_ext = pd.read_csv(DATA_DIR / "distributions_extended.csv")
    combined = pd.read_csv(DATA_DIR / "all_errors_combined_v2.csv")
    kw_stats = pd.read_csv(DATA_DIR / "keyword_stats_full.csv")

    lines = [
        "# ТЗ №4.7 — Подгонка тяжёлых хвостов и финальная сводная таблица",
        "",
        "**Дата:** 2026-05-06",
        "",
    ]

    # ── Section 1: Extended distribution fitting table ──────────────────────────
    lines += ["## 1. Результаты подгонки всех распределений", ""]

    # Full table per pair
    for cat, ds in RELIABLE_PAIRS:
        n = kw_stats[(kw_stats["category"] == cat) & (kw_stats["dataset"] == ds)]["step_n"].values
        n_val = int(n[0]) if len(n) else 0
        ks_info = "KS-тест информативен (n>>3000)" if n_val >= 3000 else "⚠️ низкая мощность KS-теста" if n_val < 100 else "⚠️ умеренная мощность"

        lines.append(f"### 1.{list(RELIABLE_PAIRS).index((cat, ds))+1} `{cat}` / `{ds}` (n={n_val}, {ks_info})")
        lines.append("")

        for pos_type in ["absolute", "normalized"]:
            subset = dist_ext[
                (dist_ext["category"] == cat) &
                (dist_ext["dataset"] == ds) &
                (dist_ext["position_type"] == pos_type)
            ]
            if subset.empty:
                continue

            subset = subset.sort_values("ks_pvalue", ascending=False).reset_index(drop=True)

            tbl = []
            for _, r in subset.iterrows():
                ks_p = r["ks_pvalue"]
                flag = ""
                if ks_p is not None:
                    if not math.isnan(ks_p):
                        if ks_p >= 0.05:
                            flag = "✓"
                        elif n_val >= 3000:
                            flag = "✗"
                        elif n_val < 100:
                            flag = "⚠"
                tbl.append({
                    "distribution": r["distribution"],
                    "params": r["params"],
                    "KS_stat": fmt(r["ks_statistic"]),
                    "KS_p": fmt(ks_p),
                    "ok": flag,
                })

            lines.append(f"**{pos_type}:**")
            lines.append(df_to_md(pd.DataFrame(tbl)))
            lines.append("")

    # ── Section 2: Q-Q plots ────────────────────────────────────────────────────
    lines += ["## 2. Q-Q plots для лучшего распределения", ""]
    lines += [
        "Q-Q plot сравнивает эмпирические квантили с теоретическими. "
        "Точки на диагонали — хорошая подгонка.",
        "",
    ]

    for cat, ds in RELIABLE_PAIRS:
        n = kw_stats[(kw_stats["category"] == cat) & (kw_stats["dataset"] == ds)]["step_n"].values
        n_val = int(n[0]) if len(n) else 0

        for pos_type in ["absolute", "normalized"]:
            fname = f"qq_{cat}_{ds}_{pos_type}.png"
            path = PLOTS_DIR / fname
            if path.exists():
                lines.append(f"**{cat} / {ds} — {pos_type}**")
                lines.append(f"![{cat}/{ds}/{pos_type}]({path.relative_to(ROOT)})")
                lines.append("")

    # ── Section 3: Final fit conclusions ──────────────────────────────────────
    lines += ["## 3. Финальные выводы по распределениям", ""]

    final_rows = []
    for cat, ds in RELIABLE_PAIRS:
        n = kw_stats[(kw_stats["category"] == cat) & (kw_stats["dataset"] == ds)]["step_n"].values
        n_val = int(n[0]) if len(n) else 0

        for pos_type in ["absolute", "normalized"]:
            subset = dist_ext[
                (dist_ext["category"] == cat) &
                (dist_ext["dataset"] == ds) &
                (dist_ext["position_type"] == pos_type)
            ]
            if subset.empty:
                continue

            ks_pvalues = [r["ks_pvalue"] for r in subset.to_dict("records")]

            if n_val >= 3000:
                non_rejected = [p for p in ks_pvalues if p is not None and not math.isnan(p) and p >= 0.05]
                if non_rejected:
                    best = max(subset.to_dict("records"), key=lambda r: r["ks_pvalue"] or 0)
                    conclusion = f"best_fit: {best['distribution']} (p={best['ks_pvalue']:.4f})"
                    fit_type = "пригодно" if best['ks_pvalue'] >= 0.05 else "непригодно"
                else:
                    conclusion = "no_parametric_fit: эмпирическое распределение"
                    fit_type = "непригодно"
            elif n_val >= 100:
                non_rejected = [p for p in ks_pvalues if p is not None and not math.isnan(p) and p >= 0.05]
                if non_rejected:
                    best = max(subset.to_dict("records"), key=lambda r: r["ks_pvalue"] or 0)
                    conclusion = f"best_fit: {best['distribution']} (p={best['ks_pvalue']:.4f})"
                    fit_type = "пригодно (с оговоркой)"
                else:
                    conclusion = "inconclusive: формальное отвержение"
                    fit_type = "неопределённо"
            else:
                non_rejected = [p for p in ks_pvalues if p is not None and not math.isnan(p) and p >= 0.05]
                if non_rejected:
                    best = max(subset.to_dict("records"), key=lambda r: r["ks_pvalue"] or 0)
                    conclusion = f"best_fit: {best['distribution']} (p={best['ks_pvalue']:.4f}, ⚠️ низкая мощность)"
                    fit_type = "ориентировочно"
                else:
                    conclusion = "inconclusive: низкая мощность, данных недостаточно"
                    fit_type = "неопределённо"

            final_rows.append({
                "error": cat,
                "dataset": ds,
                "n": n_val,
                "position": pos_type,
                "conclusion": conclusion,
                "fit_type": fit_type,
            })

    final_df = pd.DataFrame(final_rows)
    lines.append(df_to_md(final_df))
    lines.append("")
    lines.append("**fit_type:** пригодно = KS p ≥ 0.05, информативный тест (n ≥ 3000).")
    lines.append("")

    # ── Section 4: Recommendations for simulator ────────────────────────────────
    lines += ["## 4. Рекомендации для симулятора (ошибки классов 2–3)", ""]

    for mc in [2, 3]:
        rows_mc = combined[combined["modeling_class"] == mc]
        if rows_mc.empty:
            continue

        lines.append(f"### {MODELING_NAMES[mc]}")
        lines.append("")

        for _, row in rows_mc.iterrows():
            error_id = row["error_id"]
            source = row["source"]
            p_traj = fmt(row["p_trajectory"])
            p_msg = fmt(row["p_message"], 6)
            fit_conc = row.get("fit_conclusion", "—")

            # Determine recommendation
            if mc == 2:
                if "tool_timeout" in error_id:
                    rec = ("Использовать эмпирическое распределение нормализованной позиции. "
                           "P(traj)=0.76 высока, ошибка систематически происходит. "
                           "Weibull(1.42, 0, 0.26) даёт приемлемую аппроксимацию при n=80.")
                else:
                    rec = "См. спецификацию."
            elif mc == 3:
                # Use fit conclusions from final_df
                fc_rows = final_df[(final_df["error"] == error_id)]
                if not fc_rows.empty:
                    norm_row = fc_rows[fc_rows["position"] == "normalized"]
                    if len(norm_row):
                        cr = norm_row.iloc[0]["conclusion"]
                        ft = norm_row.iloc[0]["fit_type"]
                        if ft == "непригодно" or "empirical" in cr:
                            rec = (f"Эмпирическое распределение (все параметрические отвергнуты). "
                                   f"P(traj)={p_traj}, P(msg)={p_msg}.")
                        elif ft == "ориентировочно" or ft == "неопределённо":
                            rec = (f"Приближённо {cr.split('(')[0].strip()} "
                                   f"(⚠️ малая выборка). P(traj)={p_traj}, P(msg)={p_msg}.")
                        else:
                            rec = f"{cr}. P(traj)={p_traj}, P(msg)={p_msg}."
                    else:
                        rec = f"P(traj)={p_traj}, P(msg)={p_msg}."
                else:
                    rec = f"P(traj)={p_traj}, P(msg)={p_msg}."
            else:
                rec = "—"

            lines.append(f"**`{error_id}`** ({source}):")
            lines.append(f"- P(traj)={p_traj}, P(msg)={p_msg}")
            lines.append(f"- Распределение: {fit_conc}")
            lines.append(f"- Рекомендация: {rec}")
            lines.append("")

    # ── Section 5: Limitations ──────────────────────────────────────────────────
    lines += [
        "## 5. Ограничения",
        "",
        "1. **Тяжёлые хвосты:** nebius-категории имеют длинные хвосты (max=594 при median=14). "
        "Pareto и Lomax дают физически нереалистичные параметры (scale~10^13), что указывает "
        "на нестабильность MLE при данных значениях.",
        "2. **KS-тест при n>>3000:** отвержение H0 для всех 8 распределений означает, что "
        "простые аналитические формы не описывают данные. Это не недостаток данных, а "
        "ограничение параметрического подхода — рекомендуется эмпирическое CDF.",
        "3. **KS-тест при n<100:** для ITBench (n=80) и TerminalBench (n=267) мощность "
        "теста ограничена. Результаты носят ориентировочный характер.",
        "4. **Все fit-функции используют floc=0** (фиксированный сдвиг loc=0). "
        "Для данных, начинающихся не с 0, это может давать смещённые оценки.",
    ]

    report = "\n".join(lines)
    path = DOCS_DIR / "tz4_7_report.md"
    path.write_text(report, encoding="utf-8")
    size = path.stat().st_size
    print(f"Saved: {path} ({size:,} bytes)")


if __name__ == "__main__":
    main()