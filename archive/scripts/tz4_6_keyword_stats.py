"""ТЗ №4.6 — Полный статистический анализ ошибок из keyword search."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
import math
from collections import defaultdict
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
PLOTS_DIR.mkdir(exist_ok=True)

# ── Correct paths from tz4_5_keyword_search.py ───────────────────────────────
NEB_DIR   = ROOT / "nebius-SWE-agent-trajectories" / "data"
SWE_DIR   = ROOT / "SWE-Gym-OpenHands-Sampled-Trajectories" / "data"
TERM_DIR  = ROOT / "yoonholee-terminalbench-trajectories" / "data"
ITBENCH_DIR = ROOT / "ibm-research-ITBench-Trajectories"

# ── Надёжные пары (категория, датасет) из tz4_5_category_interpretation.md ─────
RELIABLE_PAIRS = [
    ("tool_web_failure",   "nebius"),
    ("resource_not_found",  "nebius"),
    ("tool_timeout",       "itbench"),
    ("permission_error",   "terminalbench"),
    ("memory_error",       "terminalbench"),
]

# ── Keyword categories ────────────────────────────────────────────────────────
KEYWORD_CATEGORIES = {
    "tool_timeout": [
        "timeout", "timed out", "time out", "timeouterror",
        "deadline exceeded", "request timeout", "operation timed",
    ],
    "tool_web_failure": [
        "404", "403", "500", "502", "503",
        "connection refused", "connection error", "network error",
        "failed to connect", "could not connect", "no route to host",
        "name resolution failed", "dns",
    ],
    "resource_not_found": [
        "filenotfounderror", "no such file", "not found",
        "does not exist", "cannot find", "path does not exist",
    ],
    "permission_error": [
        "permission denied", "access denied", "permissionerror",
        "not permitted", "operation not permitted",
    ],
    "memory_error": [
        "out of memory", "oom", "memoryerror",
        "memory error", "killed", "cannot allocate",
    ],
}

# ── Reused from tz4_distributions.py ─────────────────────────────────────────

def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 1.0
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


DISTRIBUTIONS_ABS = [
    ("exponential", lambda data: stats.expon.fit(data)),
    ("weibull_min", lambda data: stats.weibull_min.fit(data, floc=0)),
    ("lognorm",     lambda data: stats.lognorm.fit(data, floc=0)),
]

DISTRIBUTIONS_NORM = [
    ("exponential", lambda data: stats.expon.fit(data)),
    ("weibull_min", lambda data: stats.weibull_min.fit(data, floc=0)),
    ("lognorm",     lambda data: stats.lognorm.fit(data, floc=0)),
    ("beta",        lambda data: stats.beta.fit(data)),
    ("uniform",     lambda data: stats.uniform.fit(data)),
]

DIST_OBJECTS = {
    "exponential": stats.expon,
    "weibull_min": stats.weibull_min,
    "lognorm":     stats.lognorm,
    "beta":        stats.beta,
    "uniform":     stats.uniform,
}


def search_text(text: str) -> set:
    """Return set of categories found in text."""
    if not isinstance(text, str):
        return set()
    t = text.lower()
    found = set()
    for cat, keywords in KEYWORD_CATEGORIES.items():
        for kw in keywords:
            if kw in t:
                found.add(cat)
                break
    return found


# ── Histogram ─────────────────────────────────────────────────────────────────

def save_histogram(values, category, dataset, position_type):
    if len(values) == 0:
        return
    v = np.array(values, dtype=float)
    if position_type == "normalized":
        bins = np.linspace(0.0, 1.0, 21)
        xlabel = "Normalized Position (step / trajectory_length)"
        prefix = "hist_kw_rel"
        title = f"{category} / {dataset} — Normalized Position (n={len(v)})"
        color = "darkorange"
    else:
        binwidth = max(1, int(np.ptp(v) / 15) or 1)
        xmin = max(0, int(v.min()) - 1)
        xmax = int(v.max()) + 2
        bins = np.arange(xmin, xmax + binwidth, binwidth)
        xlabel = "Step Number (absolute)"
        prefix = "hist_kw"
        title = f"{category} / {dataset} — Absolute Position (n={len(v)})"
        color = "steelblue"

    fname = f"{prefix}_{category}_{dataset}.png"
    path = PLOTS_DIR / fname
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(v, bins=bins, edgecolor="black", alpha=0.75, color=color)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    print(f"  Saved: {path.name} ({path.stat().st_size // 1024} KB)")


# ── Distribution fitting ───────────────────────────────────────────────────────

def fit_distributions(data, dists, category, dataset, position_type):
    n = len(data)
    low_conf = n < 100
    ks_informative = n > 3000
    results = []
    for name, fit_fn in dists:
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

        note = None
        if ks_informative and ks_stat is not None and ks_pval is not None:
            if ks_pval < 0.05:
                note = "KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит."
            else:
                note = "KS-тест информативен (n>>3000): H0 не отвергнута, хорошая подгонка."
        elif n < 100:
            note = f"⚠️ n={n}<<3000. Низкая мощность KS-теста."

        results.append({
            "category": category,
            "dataset": dataset,
            "position_type": position_type,
            "distribution": name,
            "params": params_str,
            "ks_statistic": round(ks_stat, 6) if ks_stat is not None else None,
            "ks_pvalue": round(ks_pval, 6) if ks_pval is not None else None,
            "low_confidence": low_conf,
            "ks_informative": ks_informative,
            "note": note,
        })
    return results


# ── Dataset processing ─────────────────────────────────────────────────────────

def process_nebius(cat_positions, cat_totals):
    """Nebius: trajectory[step].role=='user', search in step.text."""
    shards = sorted(NEB_DIR.glob("train-*-of-*.parquet"))
    print(f"  Nebius: {len(shards)} shards")
    for si, shard in enumerate(shards):
        df = pd.read_parquet(shard)
        for _, row in df.iterrows():
            traj_id = str(row.get("instance_id", ""))
            traj = row.get("trajectory")
            if traj is None or (hasattr(traj, '__len__') and len(traj) == 0):
                traj = []
            traj_len = len(traj)
            cat_totals[("nebius", "any")] = cat_totals.get(("nebius", "any"), 0) + 1

            for cat, ds in RELIABLE_PAIRS:
                if ds != "nebius":
                    continue
                first_step = None
                for idx, step in enumerate(traj):
                    if not isinstance(step, dict) or step.get("role") != "user":
                        continue
                    text = step.get("text", "")
                    if not isinstance(text, str):
                        continue
                    if cat in search_text(text):
                        first_step = idx + 1
                        break
                if first_step is not None:
                    cat_positions[(cat, ds)].append({
                        "trajectory_id": traj_id,
                        "first_occurrence_step": first_step,
                        "trajectory_length": traj_len,
                        "normalized_position": round(first_step / traj_len, 6),
                    })
                    cat_totals[(cat, ds)] = cat_totals.get((cat, ds), 0) + 1

        if (si + 1) % 4 == 0:
            print(f"    processed {si+1}/{len(shards)} shards")

    print(f"  Nebius done. Trajectories: {cat_totals.get(('nebius','any'),0)}")


def process_terminalbench(cat_positions, cat_totals):
    """TerminalBench: steps is JSON string of [{src, msg, ...}, ...]."""
    shards = sorted(TERM_DIR.glob("*.parquet"))
    print(f"  TerminalBench: {len(shards)} shards")
    for shard in shards:
        df = pd.read_parquet(shard)
        for _, row in df.iterrows():
            traj_id = str(row.get("instance_id", row.get("task_name", "")))
            steps_str = row.get("steps", "")
            if not isinstance(steps_str, str) or not steps_str.strip() or steps_str == "null":
                continue
            try:
                steps = json.loads(steps_str)
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(steps, list):
                continue

            traj_len = len(steps)
            cat_totals[("terminalbench", "any")] = cat_totals.get(("terminalbench", "any"), 0) + 1

            for cat, ds in RELIABLE_PAIRS:
                if ds != "terminalbench":
                    continue
                first_step = None
                for idx, step in enumerate(steps):
                    if not isinstance(step, dict):
                        continue
                    msg = step.get("msg", "")
                    if not isinstance(msg, str):
                        continue
                    if cat in search_text(msg):
                        first_step = idx + 1
                        break
                if first_step is not None:
                    cat_positions[(cat, ds)].append({
                        "trajectory_id": traj_id,
                        "first_occurrence_step": first_step,
                        "trajectory_length": traj_len,
                        "normalized_position": round(first_step / traj_len, 6),
                    })
                    cat_totals[(cat, ds)] = cat_totals.get((cat, ds), 0) + 1

    print(f"  TerminalBench done. Trajectories: {cat_totals.get(('terminalbench','any'),0)}")


def process_itbench(cat_positions, cat_totals):
    """ITBench: session.jsonl — search in ALL lines (json.dumps(payload)), first occurrence = line index."""
    sessions = sorted(ITBENCH_DIR.rglob("session.jsonl"))
    print(f"  ITBench: {len(sessions)} sessions")

    for sf in sessions:
        traj_id = sf.stem
        all_lines = []
        try:
            with open(sf, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_lines.append(line)
        except OSError:
            continue

        traj_len = len(all_lines)
        cat_totals[("itbench", "any")] = cat_totals.get(("itbench", "any"), 0) + 1

        for cat, ds in RELIABLE_PAIRS:
            if ds != "itbench":
                continue
            first_step = None
            for idx, line in enumerate(all_lines):
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = obj.get("payload", {})
                text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else str(payload)
                if cat in search_text(text):
                    first_step = idx + 1
                    break

            if first_step is not None:
                cat_positions[(cat, ds)].append({
                    "trajectory_id": traj_id,
                    "first_occurrence_step": first_step,
                    "trajectory_length": traj_len,
                    "normalized_position": round(first_step / traj_len, 6),
                })
                cat_totals[(cat, ds)] = cat_totals.get((cat, ds), 0) + 1

    print(f"  ITBench done. Trajectories: {cat_totals.get(('itbench','any'),0)}")


def count_total_steps_nebius():
    total = 0
    for shard in sorted(NEB_DIR.glob("train-*-of-*.parquet")):
        df = pd.read_parquet(shard)
        for _, row in df.iterrows():
            traj = row.get("trajectory")
            if traj is None or (hasattr(traj, '__len__') and len(traj) == 0):
                continue
            if hasattr(traj, '__len__'):
                total += len(traj)
    return total


def count_total_steps_terminalbench():
    total = 0
    for fpath in sorted(TERM_DIR.glob("*.parquet")):
        df = pd.read_parquet(fpath)
        for _, row in df.iterrows():
            steps_str = row.get("steps", "")
            if not isinstance(steps_str, str) or not steps_str.strip() or steps_str == "null":
                continue
            try:
                steps = json.loads(steps_str)
                if isinstance(steps, list):
                    total += len(steps)
            except (json.JSONDecodeError, TypeError):
                continue
    return total


def count_total_steps_itbench():
    """Total lines across all sessions."""
    total = 0
    for sf in ITBENCH_DIR.rglob("session.jsonl"):
        try:
            with open(sf, encoding="utf-8") as f:
                total += sum(1 for line in f if line.strip())
        except OSError:
            continue
    return total


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ТЗ №4.6 — Полный статистический анализ ошибок из keyword search")
    print("=" * 60)

    # All known keys
    all_keys = [(cat, ds) for cat, ds in RELIABLE_PAIRS]
    all_keys += [("nebius", "any"), ("terminalbench", "any"), ("itbench", "any")]
    cat_positions = {k: [] for k in all_keys}
    cat_totals = {k: 0 for k in all_keys}

    # ── Task 1: Extract positions ───────────────────────────────────────────────
    print("\nTask 1: Extract positions from reliable pairs...")
    process_nebius(cat_positions, cat_totals)
    process_terminalbench(cat_positions, cat_totals)
    process_itbench(cat_positions, cat_totals)

    # Save keyword_positions.csv
    pos_rows = []
    for (cat, ds), items in cat_positions.items():
        if cat == "any":
            continue
        for item in items:
            pos_rows.append({
                "category": cat,
                "dataset": ds,
                "trajectory_id": item["trajectory_id"],
                "first_occurrence_step": item["first_occurrence_step"],
                "trajectory_length": item["trajectory_length"],
                "normalized_position": item["normalized_position"],
            })
    pos_df = pd.DataFrame(pos_rows)
    pos_df.to_csv(DATA_DIR / "keyword_positions.csv", index=False)
    print(f"\n  keyword_positions.csv: {len(pos_df)} rows")

    # ── Task 2 & 3: P(message) + step statistics ───────────────────────────────
    print("\nTask 2 & 3: P(message) and step statistics...")

    total_steps = {
        "nebius": count_total_steps_nebius(),
        "terminalbench": count_total_steps_terminalbench(),
        "itbench": count_total_steps_itbench(),
    }
    for ds, n in total_steps.items():
        print(f"  total_steps[{ds}]: {n}")

    # Load keyword_search_results for P(trajectory) and n_occurrences
    kw_df = pd.read_csv(DATA_DIR / "keyword_search_results.csv")

    stats_rows = []
    dist_rows = []

    for cat, ds in RELIABLE_PAIRS:
        n_with_error = len(cat_positions[(cat, ds)])
        positions_list = cat_positions[(cat, ds)]

        kw_row = kw_df[(kw_df["dataset"] == ds) & (kw_df["category"] == cat)]
        if len(kw_row) > 0:
            kw_r = kw_row.iloc[0]
            p_traj = float(kw_r["p_trajectory"])
            p_traj_lo = float(kw_r["ci_lower"])
            p_traj_hi = float(kw_r["ci_upper"])
            n_from_kw = int(kw_r["n_trajectories_with_error"])
            n_total_kw = int(kw_r["n_trajectories_total"])
            n_occurrences_total = int(kw_r["n_occurrences_total"])
        else:
            p_traj = p_traj_lo = p_traj_hi = n_from_kw = n_total_kw = n_occurrences_total = None

        ts = total_steps.get(ds, 0)
        if ts > 0 and n_occurrences_total is not None:
            p_msg = n_occurrences_total / ts
            pmsg_lo, pmsg_hi = wilson_ci(n_occurrences_total, ts)
        else:
            p_msg = pmsg_lo = pmsg_hi = None

        # Descriptive stats
        abs_steps = [p["first_occurrence_step"] for p in positions_list]
        norm_steps = [p["normalized_position"] for p in positions_list]
        s_abs = step_stats(abs_steps) if abs_steps else {}
        s_norm = step_stats(norm_steps) if norm_steps else {}

        row = {
            "category": cat,
            "dataset": ds,
            "n_trajectories_with_error": n_from_kw if n_from_kw is not None else n_with_error,
            "n_trajectories_total": n_total_kw if n_total_kw is not None else cat_totals.get((ds, "any"), 0),
            "p_trajectory": round(p_traj, 6) if p_traj is not None else None,
            "p_traj_ci_lower": round(p_traj_lo, 6) if p_traj_lo is not None else None,
            "p_traj_ci_upper": round(p_traj_hi, 6) if p_traj_hi is not None else None,
            "total_steps": ts,
            "p_message": round(p_msg, 8) if p_msg is not None else None,
            "p_msg_ci_lower": round(pmsg_lo, 8) if pmsg_lo is not None else None,
            "p_msg_ci_upper": round(pmsg_hi, 8) if pmsg_hi is not None else None,
            "step_mean": s_abs.get("mean"),
            "step_median": s_abs.get("median"),
            "step_std": s_abs.get("std"),
            "step_p25": s_abs.get("p25"),
            "step_p75": s_abs.get("p75"),
            "step_p90": s_abs.get("p90"),
            "step_p95": s_abs.get("p95"),
            "step_n": s_abs.get("n"),
        }
        stats_rows.append(row)

        # Task 4: Histograms
        if abs_steps:
            save_histogram(abs_steps, cat, ds, "absolute")
        if norm_steps:
            save_histogram(norm_steps, cat, ds, "normalized")

        # Task 5: Distribution fitting
        min_n = min(len(abs_steps), len(norm_steps)) if (abs_steps and norm_steps) else (len(abs_steps) or len(norm_steps))
        if min_n >= 20:
            abs_results = fit_distributions(abs_steps, DISTRIBUTIONS_ABS, cat, ds, "absolute")
            norm_results = fit_distributions(norm_steps, DISTRIBUTIONS_NORM, cat, ds, "normalized")
            dist_rows.extend(abs_results)
            dist_rows.extend(norm_results)
        else:
            print(f"  Warning: {cat}/{ds} has n={min_n} < 20, skipping distribution fitting.")
            if abs_steps:
                abs_results = fit_distributions(abs_steps, DISTRIBUTIONS_ABS, cat, ds, "absolute")
                dist_rows.extend(abs_results)

    # Save CSV
    stats_df = pd.DataFrame(stats_rows)
    stats_df.to_csv(DATA_DIR / "keyword_stats_full.csv", index=False)
    print(f"\n  keyword_stats_full.csv: {len(stats_df)} rows")

    dist_df = pd.DataFrame(dist_rows)
    if not dist_df.empty:
        dist_df.to_csv(DATA_DIR / "keyword_distributions.csv", index=False)
        print(f"  keyword_distributions.csv: {len(dist_df)} rows")
    else:
        pd.DataFrame(columns=[
            "category", "dataset", "position_type", "distribution", "params",
            "ks_statistic", "ks_pvalue", "low_confidence", "ks_informative", "note"
        ]).to_csv(DATA_DIR / "keyword_distributions.csv", index=False)

    # ── Task 6: Combine all errors ─────────────────────────────────────────────
    print("\nTask 6: Combine into all_errors_combined.csv...")
    combine_all_errors()

    print("\nAll done.")


def combine_all_errors():
    """Merge AgentRx+Who&When (TZ4) with keyword search (TZ4.5+4.6) into one table."""
    stats_full = pd.read_csv(DATA_DIR / "stats_full.csv")
    dist_df = pd.read_csv(DATA_DIR / "distributions.csv")
    kw_stats = pd.read_csv(DATA_DIR / "keyword_stats_full.csv")
    kw_dist_path = DATA_DIR / "keyword_distributions.csv"

    modeling_map = {
        "instruction_adherence_failure": 1,
        "guardrails_triggered": 3,
        "misinterpretation_of_tool_output": 1,
        "intent_not_supported": 1,
        "intent_plan_misalignment": 1,
        "invention_of_new_information": 1,
        "invalid_invocation": 3,
        "system_failure": 3,
        "underspecified_user_intent": 1,
        "unclassified": 1,
        "code_error": 1,
        "tool_web_failure": 3,
        "orchestration_failure": 1,
        "resource_abuse": 3,
        "hallucination": 1,
        "factual_error": 1,
        "misinterpretation": 1,
        "resource_not_found": 3,
        "tool_timeout": 2,
        "permission_error": 3,
        "memory_error": 3,
    }

    rows = []

    # AgentRx + Who&When entries
    for _, r in stats_full.iterrows():
        cat = r["category"]
        src = r["source"]
        mc = modeling_map.get(cat, 1)

        dist_rows = dist_df[
            (dist_df["category"] == cat) &
            (dist_df["source"] == src) &
            (dist_df["position_type"] == "absolute")
        ]
        if len(dist_rows) > 0:
            best_row = dist_rows.sort_values("ks_pvalue", ascending=False).iloc[0]
            best_dist = best_row["distribution"]
            best_params = best_row["params"]
            best_ks_stat = best_row["ks_statistic"]
            best_ks_p = best_row["ks_pvalue"]
        else:
            best_dist = best_params = best_ks_stat = best_ks_p = None

        rows.append({
            "error_id": cat,
            "source": src,
            "modeling_class": mc,
            "n_trajectories_with_error": int(r["n_trajectories_with_error"]),
            "n_trajectories_total": int(r["n_trajectories_total"]),
            "p_trajectory": r["p_trajectory"],
            "p_traj_ci_lower": r["p_trajectory_ci_lower"],
            "p_traj_ci_upper": r["p_trajectory_ci_upper"],
            "total_steps": int(r["total_steps"]),
            "p_message": r["p_message"],
            "p_msg_ci_lower": r["p_message_ci_lower"],
            "p_msg_ci_upper": r["p_message_ci_upper"],
            "step_mean": None, "step_median": None, "step_std": None,
            "step_p25": None, "step_p75": None, "step_n": None,
            "best_distribution": best_dist,
            "best_dist_params": best_params,
            "best_dist_ks_stat": best_ks_stat,
            "best_dist_ks_pvalue": best_ks_p,
            "data_quality": "medium",
            "insufficient_data": bool(r["insufficient_data"]),
            "notes": None,
        })

    # Keyword search entries
    kw_dist = pd.read_csv(kw_dist_path) if kw_dist_path.stat().st_size > 10 else pd.DataFrame()

    for _, r in kw_stats.iterrows():
        cat = r["category"]
        ds = r["dataset"]

        kw_d_rows = pd.DataFrame()
        if not kw_dist.empty:
            kw_d_rows = kw_dist[
                (kw_dist["category"] == cat) &
                (kw_dist["dataset"] == ds) &
                (kw_dist["position_type"] == "absolute")
            ]

        if len(kw_d_rows) > 0:
            best_row = kw_d_rows.sort_values("ks_pvalue", ascending=False).iloc[0]
            best_dist = best_row["distribution"]
            best_params = best_row["params"]
            best_ks_stat = best_row["ks_statistic"]
            best_ks_p = best_row["ks_pvalue"]
        else:
            best_dist = best_params = best_ks_stat = best_ks_p = None

        n_with = int(r["n_trajectories_with_error"]) if not math.isnan(r["n_trajectories_with_error"]) else 0

        rows.append({
            "error_id": cat,
            "source": f"keyword_search_{ds}",
            "modeling_class": modeling_map.get(cat, 3),
            "n_trajectories_with_error": n_with,
            "n_trajectories_total": int(r["n_trajectories_total"]),
            "p_trajectory": r["p_trajectory"],
            "p_traj_ci_lower": r["p_traj_ci_lower"],
            "p_traj_ci_upper": r["p_traj_ci_upper"],
            "total_steps": int(r["total_steps"]) if not math.isnan(r["total_steps"]) else 0,
            "p_message": r["p_message"],
            "p_msg_ci_lower": r["p_msg_ci_lower"],
            "p_msg_ci_upper": r["p_msg_ci_upper"],
            "step_mean": r.get("step_mean"),
            "step_median": r.get("step_median"),
            "step_std": r.get("step_std"),
            "step_p25": r.get("step_p25"),
            "step_p75": r.get("step_p75"),
            "step_n": r.get("step_n"),
            "best_distribution": best_dist,
            "best_dist_params": best_params,
            "best_dist_ks_stat": best_ks_stat,
            "best_dist_ks_pvalue": best_ks_p,
            "data_quality": "high",
            "insufficient_data": n_with < 20,
            "notes": None,
        })

    combined_df = pd.DataFrame(rows)
    combined_df.to_csv(DATA_DIR / "all_errors_combined.csv", index=False)
    print(f"  all_errors_combined.csv: {len(combined_df)} rows")
    print(f"  Sources: {sorted(combined_df['source'].unique())}")
    print(f"  modeling_class: {combined_df['modeling_class'].value_counts().sort_index().to_dict()}")


if __name__ == "__main__":
    main()