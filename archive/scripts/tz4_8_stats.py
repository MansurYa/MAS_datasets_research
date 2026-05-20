"""ТЗ №4.8 Часть C — Полный пересчёт статистики (TRAIL + AgentRx + Who&When HC)."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
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
AGENTRX_DIR = ROOT / "microsoft-AgentRx"
WW_DIR = ROOT / "Kevin355-Who_and_When"
PLOTS_DIR.mkdir(exist_ok=True)

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

DISTRIBUTIONS = [
    ("exponential", lambda d: stats.expon.fit(d)),
    ("weibull_min", lambda d: stats.weibull_min.fit(d, floc=0)),
    ("lognorm",     lambda d: stats.lognorm.fit(d, floc=0)),
    ("beta",        lambda d: stats.beta.fit(d)),
    ("uniform",     lambda d: stats.uniform.fit(d)),
    ("pareto",      lambda d: stats.pareto.fit(d, floc=0)),
    ("gamma",       lambda d: stats.gamma.fit(d, floc=0)),
    ("lomax",       lambda d: stats.lomax.fit(d, floc=0)),
]

DIST_OBJECTS = {
    "exponential": stats.expon, "weibull_min": stats.weibull_min,
    "lognorm": stats.lognorm, "beta": stats.beta, "uniform": stats.uniform,
    "pareto": stats.pareto, "gamma": stats.gamma, "lomax": stats.lomax,
}


def wilson_ci(n_success, n_total, z=1.96):
    if n_total == 0:
        return 0.0, 1.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def step_stats(arr):
    a = np.array(arr, dtype=float)
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return {}
    return dict(n=len(a), mean=round(float(a.mean()), 2), median=float(np.median(a)),
                std=round(float(a.std()), 2) if len(a) > 1 else 0.0,
                min=int(a.min()), max=int(a.max()),
                p25=float(np.percentile(a, 25)), p75=float(np.percentile(a, 75)),
                p90=float(np.percentile(a, 90)), p95=float(np.percentile(a, 95)))


def save_histogram(values, error_id, source, pos_type):
    v = np.array(values, dtype=float)
    prefix = f"hist48_{pos_type}_{error_id}_{source}"
    path = PLOTS_DIR / f"{prefix}.png"
    if pos_type == "normalized":
        bins = np.linspace(0.0, 1.0, 21)
        xlabel = "Normalized Position"
    else:
        bw = max(1, int(np.ptp(v) / 15) or 1)
        bins = np.arange(max(0, int(v.min()) - 1), int(v.max()) + 2 + bw, bw)
        xlabel = "Step Number"
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(v, bins=bins, edgecolor="black", alpha=0.75, color="steelblue")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.set_title(f"{error_id} / {source} — {pos_type} (n={len(v)})")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def fit_distributions(data, error_id, source, pos_type):
    n = len(data)
    results = []
    for name, fit_fn in DISTRIBUTIONS:
        if pos_type == "absolute" and name in ("beta", "uniform"):
            continue
        try:
            params = fit_fn(data)
            dist_obj = DIST_OBJECTS.get(name)
            ks_stat, ks_pval = stats.kstest(data, dist_obj.cdf, args=params)
            params_str = ", ".join(f"{p:.4f}" for p in params)
        except Exception as ex:
            params_str = f"fit_failed: {ex}"
            ks_stat = ks_pval = None
        results.append({
            "error_id": error_id, "source": source, "position_type": pos_type,
            "distribution": name, "params": params_str,
            "ks_statistic": round(ks_stat, 6) if ks_stat is not None else None,
            "ks_pvalue": round(ks_pval, 6) if ks_pval is not None else None,
            "low_confidence": n < 100, "ks_informative": n > 3000,
        })
    return results


def best_fit(dist_rows):
    valid = [r for r in dist_rows if r["ks_pvalue"] is not None]
    if not valid:
        return None, None, None
    best = max(valid, key=lambda r: r["ks_pvalue"])
    return best["distribution"], best["params"], best["ks_pvalue"]


def compute_source_stats(error_df, n_total_traj, total_steps, source_name, traj_lens=None, step_col="step_number"):
    stats_rows = []
    dist_rows = []

    for error_id, grp in error_df.groupby("error_id"):
        n_traj = grp["trajectory_id"].nunique()
        n_occ = len(grp)
        p_traj = n_traj / n_total_traj if n_total_traj else 0
        ci_lo, ci_hi = wilson_ci(n_traj, n_total_traj)
        p_msg = n_occ / total_steps if total_steps else None
        pmsg_lo, pmsg_hi = wilson_ci(n_occ, total_steps) if total_steps else (None, None)

        # Step positions from specified column
        steps = grp[step_col].dropna().astype(int).tolist()

        # Normalized positions
        norm_vals = []
        if traj_lens is not None:
            for _, r in grp.iterrows():
                step = r.get(step_col)
                tid = r.get("trajectory_id")
                tl = traj_lens.get(tid)
                if step is not None and tl and tl > 0:
                    norm_vals.append(step / tl)
        elif "trajectory_length" in grp.columns:
            for _, r in grp.iterrows():
                step = r.get(step_col)
                tl = r.get("trajectory_length")
                if step is not None and tl and tl > 0:
                    norm_vals.append(step / tl)

        s_abs = step_stats(steps) if len(steps) >= 5 else {}
        s_norm = step_stats(norm_vals) if len(norm_vals) >= 5 else {}

        row = {
            "error_id": error_id, "source": source_name,
            "n_trajectories_with_error": n_traj, "n_trajectories_total": n_total_traj,
            "p_trajectory": round(p_traj, 6), "p_traj_ci_lower": round(ci_lo, 6),
            "p_traj_ci_upper": round(ci_hi, 6), "total_steps": total_steps,
            "p_message": round(p_msg, 8) if p_msg else None,
            "p_msg_ci_lower": round(pmsg_lo, 8) if pmsg_lo else None,
            "p_msg_ci_upper": round(pmsg_hi, 8) if pmsg_hi else None,
            "step_mean": s_abs.get("mean"), "step_median": s_abs.get("median"),
            "step_std": s_abs.get("std"), "step_n": s_abs.get("n"),
            "step_p25": s_abs.get("p25"), "step_p75": s_abs.get("p75"),
            "step_p90": s_abs.get("p90"), "step_p95": s_abs.get("p95"),
            "norm_mean": s_norm.get("mean"), "norm_median": s_norm.get("median"),
            "norm_std": s_norm.get("std"), "norm_n": s_norm.get("n"),
            "insufficient_data": n_traj < 20,
        }
        stats_rows.append(row)

        # Histograms + distributions for n >= 20
        if len(steps) >= 20:
            save_histogram(steps, error_id, source_name, "absolute")
            dr = fit_distributions(steps, error_id, source_name, "absolute")
            dist_rows.extend(dr)
        if len(norm_vals) >= 20:
            save_histogram(norm_vals, error_id, source_name, "normalized")
            dr = fit_distributions(norm_vals, error_id, source_name, "normalized")
            dist_rows.extend(dr)

    return stats_rows, dist_rows


def main():
    print("=" * 60)
    print("ТЗ №4.8 Часть C — Пересчёт статистики")
    print("=" * 60)

    all_stats = []
    all_dists = []

    # ── TRAIL ─────────────────────────────────────────────────────────────────
    print("\n[TRAIL]")
    trail_df = pd.read_csv(DATA_DIR / "trail_errors_v2.csv")
    trail_df = trail_df[trail_df["error_id"] != "no_errors"]
    n_trail_traj = trail_df["trajectory_id"].nunique()
    traj_steps_trail = trail_df.groupby("trajectory_id")["trajectory_length"].first().sum()
    print(f"  Trajectories: {n_trail_traj}, total steps: {traj_steps_trail}")
    print(f"  Errors per trajectory: {len(trail_df) / n_trail_traj:.1f}")

    s, d = compute_source_stats(trail_df, n_trail_traj, int(traj_steps_trail), "trail", step_col="error_step")
    all_stats.extend(s)
    all_dists.extend(d)

    # AgentRx: no total_steps data, so p_message = None
    print("\n[AgentRx]")
    rx_rows = []
    rx_lens = {}
    for fname, src in [("magentic_one.jsonl", "magentic_one"), ("tau_retail.jsonl", "tau_retail")]:
        with open(AGENTRX_DIR / fname) as f:
            for line in f:
                obj = json.loads(line)
                traj_id = obj["trajectory_id"]
                rx_lens[traj_id] = None  # unknown
                for fail in obj.get("failures", []):
                    cat = UNIFICATION_MAP.get(fail.get("failure_category", ""), "unknown")
                    if cat == "unknown":
                        continue
                    step = fail.get("step_number")
                    rx_rows.append({"source": src, "trajectory_id": traj_id,
                                    "error_id": cat, "step_number": step})
    rx_df = pd.DataFrame(rx_rows)

    for src, n_traj in [("magentic_one", 44), ("tau_retail", 29)]:
        sub = rx_df[rx_df["source"] == src]
        # p_message undefined — AgentRx has no trajectory step counts
        print(f"  {src}: {sub['trajectory_id'].nunique()} error trajs / {n_traj} total")
        s, d = compute_source_stats(sub, n_traj, None, src, traj_lens=None)
        all_stats.extend(s)
        all_dists.extend(d)

    # ── Who&When Hand-Crafted ─────────────────────────────────────────────────
    print("\n[Who&When Hand-Crafted]")
    ww_df = pd.read_csv(DATA_DIR / "who_and_when_handcrafted_classified.csv")
    ww_df = ww_df[ww_df["category_unified"] != "unclassified"].rename(
        columns={"category_unified": "error_id"})

    # Get actual trajectory lengths from HC parquet
    hc = pd.read_parquet(WW_DIR / "Hand-Crafted.parquet")
    hc_lens = hc.set_index("question_ID")["history"].apply(len).to_dict()

    n_ww_traj = ww_df["trajectory_id"].nunique()
    total_steps_ww = sum(hc_lens.get(tid, 0) for tid in ww_df["trajectory_id"].unique())
    print(f"  Trajectories: {n_ww_traj}, total steps: {total_steps_ww}")
    print(f"  Classification distribution:")
    print(ww_df["error_id"].value_counts())

    s, d = compute_source_stats(ww_df, n_ww_traj, total_steps_ww, "who_and_when_hc",
                                 traj_lens=hc_lens)
    all_stats.extend(s)
    all_dists.extend(d)

    # ── Keyword search (unchanged) ─────────────────────────────────────────────
    print("\n[Keyword search]")
    kw_stats = pd.read_csv(DATA_DIR / "keyword_stats_full.csv")
    for _, r in kw_stats.iterrows():
        row = {
            "error_id": r["category"], "source": f"keyword_search_{r['dataset']}",
            "n_trajectories_with_error": int(r["n_trajectories_with_error"]),
            "n_trajectories_total": int(r["n_trajectories_total"]),
            "p_trajectory": round(r["p_trajectory"], 6),
            "p_traj_ci_lower": round(r["p_traj_ci_lower"], 6),
            "p_traj_ci_upper": round(r["p_traj_ci_upper"], 6),
            "total_steps": int(r["total_steps"]),
            "p_message": round(r["p_message"], 8) if not math.isnan(r["p_message"]) else None,
            "p_msg_ci_lower": round(r["p_msg_ci_lower"], 8) if not math.isnan(r["p_msg_ci_lower"]) else None,
            "p_msg_ci_upper": round(r["p_msg_ci_upper"], 8) if not math.isnan(r["p_msg_ci_upper"]) else None,
            "step_mean": r.get("step_mean"), "step_median": r.get("step_median"),
            "step_std": r.get("step_std"), "step_n": r.get("step_n"),
            "step_p25": r.get("step_p25"), "step_p75": r.get("step_p75"),
            "step_p90": r.get("step_p90"), "step_p95": r.get("step_p95"),
            "norm_mean": r.get("norm_mean"), "norm_median": r.get("norm_median"),
            "norm_std": r.get("norm_std"), "norm_n": r.get("norm_n"),
            "insufficient_data": r["n_trajectories_with_error"] < 20,
        }
        all_stats.append(row)
    print(f"  Keyword search sources: {kw_stats['dataset'].nunique()} datasets")

    # ── Save ──────────────────────────────────────────────────────────────────
    stats_df = pd.DataFrame(all_stats)
    stats_df.to_csv(DATA_DIR / "stats_full_v2.csv", index=False)
    print(f"\nSaved stats_full_v2.csv: {len(stats_df)} rows")
    print(f"Sources: {stats_df['source'].unique()}")

    dist_df = pd.DataFrame(all_dists)
    dist_df.to_csv(DATA_DIR / "distributions_v2.csv", index=False)
    print(f"Saved distributions_v2.csv: {len(dist_df)} rows")

    return stats_df, dist_df


if __name__ == "__main__":
    main()