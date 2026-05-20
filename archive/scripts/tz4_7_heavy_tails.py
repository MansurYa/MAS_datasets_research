"""ТЗ №4.7 — Подгонка тяжёлых хвостов и финальная сводная таблица."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
PLOTS_DIR = DATA_DIR / "plots"
DOCS_DIR = ROOT / "docs"

# ── Reused helpers ──────────────────────────────────────────────────────────────

def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 1.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)

def fmt(v, digits=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.{digits}f}"
    return str(v)

# ── Reliable pairs from TZ 4.6 ─────────────────────────────────────────────────

RELIABLE_PAIRS = [
    ("tool_web_failure",   "nebius"),
    ("resource_not_found",  "nebius"),
    ("tool_timeout",       "itbench"),
    ("permission_error",   "terminalbench"),
    ("memory_error",       "terminalbench"),
]

# ── New distributions ───────────────────────────────────────────────────────────

DISTRIBUTIONS_NEW = [
    ("pareto",  lambda data: stats.pareto.fit(data, floc=0)),
    ("gamma",   lambda data: stats.gamma.fit(data, floc=0)),
    ("lomax",   lambda data: stats.lomax.fit(data, floc=0)),
]

DIST_OBJECTS = {
    "exponential": stats.expon,
    "weibull_min": stats.weibull_min,
    "lognorm":     stats.lognorm,
    "beta":        stats.beta,
    "uniform":     stats.uniform,
    "pareto":      stats.pareto,
    "gamma":       stats.gamma,
    "lomax":       stats.lomax,
}


def fit_distribution(data, name, fit_fn):
    """Fit one distribution, return dict with KS-test result."""
    n = len(data)
    try:
        params = fit_fn(data)
        dist_obj = DIST_OBJECTS.get(name)
        if dist_obj is not None:
            ks_stat, ks_pval = stats.kstest(data, dist_obj.cdf, args=params)
        else:
            ks_stat = ks_pval = None
        params_str = ", ".join(f"{p:.4f}" for p in params)
    except Exception as ex:
        params_str = f"fit_failed: {ex}"
        ks_stat = ks_pval = None
    return params_str, ks_stat, ks_pval


def fit_conclusion(n, ks_pvalues):
    """Return one-line conclusion based on n and KS p-values."""
    if n >= 3000:
        non_rejected = [p for p in ks_pvalues if p is not None and p >= 0.05]
        if non_rejected:
            return f"best_fit_available: {len(non_rejected)}/{len(ks_pvalues)} not rejected"
        return "no_parametric_fit: рекомендуется эмпирическое распределение"
    elif n >= 100:
        non_rejected = [p for p in ks_pvalues if p is not None and p >= 0.05]
        if non_rejected:
            return f"best_fit_available: {len(non_rejected)}/{len(ks_pvalues)} not rejected"
        return "inconclusive: формальное отвержение при умеренной мощности"
    else:
        return "inconclusive: низкая мощность теста, данных недостаточно"


def best_fit_row(results):
    """Return row with highest KS p-value."""
    valid = [r for r in results if r["ks_pvalue"] is not None]
    if not valid:
        return None
    return max(valid, key=lambda r: r["ks_pvalue"])


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ТЗ №4.7 — Подгонка тяжёлых хвостов и финальная сводка")
    print("=" * 60)

    pos_df = pd.read_csv(DATA_DIR / "keyword_positions.csv")
    kw_stats = pd.read_csv(DATA_DIR / "keyword_stats_full.csv")
    kw_dist_old = pd.read_csv(DATA_DIR / "keyword_distributions.csv")

    # ── Task 1: Fit new distributions ─────────────────────────────────────────
    print("\nTask 1: Fit Pareto, Gamma, Lomax for reliable pairs...")

    all_dist_results = []  # will hold combined old + new

    # Include old results
    for _, r in kw_dist_old.iterrows():
        all_dist_results.append({
            "category": r["category"],
            "dataset": r["dataset"],
            "position_type": r["position_type"],
            "distribution": r["distribution"],
            "params": r["params"],
            "ks_statistic": r["ks_statistic"],
            "ks_pvalue": r["ks_pvalue"],
            "low_confidence": r["low_confidence"],
        })

    # Fit new distributions
    for cat, ds in RELIABLE_PAIRS:
        pos_subset = pos_df[(pos_df["category"] == cat) & (pos_df["dataset"] == ds)]
        abs_vals = pos_subset["first_occurrence_step"].tolist()
        norm_vals = pos_subset["normalized_position"].tolist()
        n = len(abs_vals)

        for pos_type, vals in [("absolute", abs_vals), ("normalized", norm_vals)]:
            if len(vals) < 5:
                continue

            for dist_name, fit_fn in DISTRIBUTIONS_NEW:
                params_str, ks_stat, ks_pval = fit_distribution(vals, dist_name, fit_fn)
                ks_info = n > 3000
                note = None
                if ks_info and ks_stat is not None and ks_pval is not None:
                    if ks_pval < 0.05:
                        note = "KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит."
                    else:
                        note = "KS-тест информативен (n>>3000): H0 не отвергнута."
                elif n < 100:
                    note = f"⚠️ n={n}<<3000. Низкая мощность KS-теста."

                all_dist_results.append({
                    "category": cat,
                    "dataset": ds,
                    "position_type": pos_type,
                    "distribution": dist_name,
                    "params": params_str,
                    "ks_statistic": round(ks_stat, 6) if ks_stat is not None else None,
                    "ks_pvalue": round(ks_pval, 6) if ks_pval is not None else None,
                    "low_confidence": n < 100,
                    "note": note,
                })

    # Save extended distributions CSV
    dist_ext_df = pd.DataFrame(all_dist_results)
    dist_ext_df.to_csv(DATA_DIR / "distributions_extended.csv", index=False)
    print(f"  distributions_extended.csv: {len(dist_ext_df)} rows")

    # ── Task 2: Q-Q plots ──────────────────────────────────────────────────────
    print("\nTask 2: Q-Q plots...")

    for cat, ds in RELIABLE_PAIRS:
        pos_subset = pos_df[(pos_df["category"] == cat) & (pos_df["dataset"] == ds)]
        n = len(pos_subset)

        for pos_type in ["absolute", "normalized"]:
            dist_subset = dist_ext_df[
                (dist_ext_df["category"] == cat) &
                (dist_ext_df["dataset"] == ds) &
                (dist_ext_df["position_type"] == pos_type)
            ]
            best = best_fit_row(dist_subset.to_dict("records"))

            if best is None:
                continue

            vals = pos_subset["first_occurrence_step"].tolist() if pos_type == "absolute" else pos_subset["normalized_position"].tolist()

            dist_name = best["distribution"]
            params_str = best["params"]
            dist_obj = DIST_OBJECTS.get(dist_name)

            if dist_obj is None:
                continue

            # Parse params
            try:
                params = tuple(float(p) for p in params_str.split(", "))
            except:
                continue

            fname = f"qq_{cat}_{ds}_{pos_type}.png"
            path = PLOTS_DIR / fname

            fig, ax = plt.subplots(figsize=(7, 5))
            try:
                stats.probplot(vals, dist=dist_obj, sparams=params, plot=ax)
            except Exception as e:
                ax.text(0.5, 0.5, f"probplot failed: {e}", transform=ax.transAxes, ha="center")
            ax.set_title(f"{cat} / {ds} — {pos_type} — Q-Q ({dist_name})")
            ax.grid(alpha=0.3)
            fig.tight_layout()
            fig.savefig(path, dpi=120)
            plt.close(fig)
            print(f"  Saved: {fname} ({path.stat().st_size // 1024} KB)")

    # ── Task 3: Fit conclusions ───────────────────────────────────────────────
    print("\nTask 3: Fit conclusions...")

    conclusions = {}
    for cat, ds in RELIABLE_PAIRS:
        pos_subset = pos_df[(pos_df["category"] == cat) & (pos_df["dataset"] == ds)]
        n = len(pos_subset)

        for pos_type in ["absolute", "normalized"]:
            dist_subset = dist_ext_df[
                (dist_ext_df["category"] == cat) &
                (dist_ext_df["dataset"] == ds) &
                (dist_ext_df["position_type"] == pos_type)
            ]
            ks_pvalues = [r["ks_pvalue"] for r in dist_subset.to_dict("records")]
            conclusion = fit_conclusion(n, ks_pvalues)
            conclusions[(cat, ds, pos_type)] = conclusion

    # ── Task 4: Update all_errors_combined ────────────────────────────────────
    print("\nTask 4: Update all_errors_combined...")

    combined = pd.read_csv(DATA_DIR / "all_errors_combined.csv")

    # Determine best fit per (error_id, source) from all distributions
    updated_rows = []
    for _, row in combined.iterrows():
        error_id = row["error_id"]
        source = row["source"]

        # Check if this is a keyword search row
        if "keyword_search" in source:
            cat = error_id
            # Infer dataset from source
            ds_map = {
                "keyword_search_nebius": "nebius",
                "keyword_search_itbench": "itbench",
                "keyword_search_terminalbench": "terminalbench",
            }
            ds = ds_map.get(source)
            if ds:
                # Find best fit across all distributions for this pair
                pair_dist = dist_ext_df[
                    (dist_ext_df["category"] == cat) &
                    (dist_ext_df["dataset"] == ds)
                ]
                best = best_fit_row(pair_dist.to_dict("records"))
                if best:
                    conc_abs = conclusions.get((cat, ds, "absolute"), "inconclusive")
                    conc_norm = conclusions.get((cat, ds, "normalized"), "inconclusive")
                    best_conclusion = f"{conc_abs} | {conc_norm}"
                    row = row.copy()
                    row["best_distribution"] = best["distribution"]
                    row["best_dist_params"] = best["params"]
                    row["best_dist_ks_pvalue"] = best["ks_pvalue"]
                    row["fit_conclusion"] = best_conclusion
            updated_rows.append(row)
        else:
            # Keep as-is from TZ 4.6
            row = row.copy()
            if pd.isna(row.get("fit_conclusion", None)):
                row["fit_conclusion"] = "from AgentRx/Who&When"
            updated_rows.append(row)

    combined_v2 = pd.DataFrame(updated_rows)
    combined_v2.to_csv(DATA_DIR / "all_errors_combined_v2.csv", index=False)
    print(f"  all_errors_combined_v2.csv: {len(combined_v2)} rows")

    # Print conclusions
    print("\n  Fit conclusions:")
    for cat, ds in RELIABLE_PAIRS:
        conc_abs = conclusions.get((cat, ds, "absolute"), "—")
        conc_norm = conclusions.get((cat, ds, "normalized"), "—")
        print(f"  {cat}/{ds}:")
        print(f"    absolute: {conc_abs}")
        print(f"    normalized: {conc_norm}")

    print("\nDone Tasks 1–4.")


if __name__ == "__main__":
    main()