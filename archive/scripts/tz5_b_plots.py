"""ТЗ №5 Часть B (v2) — Генерация графиков с улучшенным кодированием."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
PLOTS_DIR = ROOT / "report" / "plots"
PLOTS_DIR.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({"font.size": 11, "axes.titlesize": 12, "axes.labelsize": 11})

DIST_OBJECTS = {
    "exponential": stats.expon, "weibull_min": stats.weibull_min,
    "lognorm": stats.lognorm, "beta": stats.beta, "uniform": stats.uniform,
    "pareto": stats.pareto, "gamma": stats.gamma, "lomax": stats.lomax,
}

# Цвет = источник / качество данных (научная визуализация)
SOURCE_COLOR = {
    "trail":                        "#1f77b4",  # синий — экспертная разметка
    "magentic_one":                 "#2ca02c",  # зелёный — аннотация на уровне шагов
    "tau_retail":                   "#228b22",  # тёмно-зелёный — аннотация на уровне шагов
    "who_and_when_hc":             "#ff7f0e",  # оранжевый — keyword matching
    "keyword_search_nebius":        "#9467bd",  # фиолетовый — keyword search
    "keyword_search_itbench":       "#8c564b",  # коричневый — keyword search
    "keyword_search_terminalbench": "#e377c2",  # розовый — keyword search
    "теоретическая":                "#7f7f7f",  # серый — нет данных
}

SOURCE_LABEL = {
    "trail":                        "TRAIL (экспертная)",
    "magentic_one":                 "AgentRx / MagenticOne",
    "tau_retail":                  "AgentRx / TauRetail",
    "who_and_when_hc":             "Who&When HC (keyword)",
    "keyword_search_nebius":        "Nebius (keyword)",
    "keyword_search_itbench":       "ITBench (keyword)",
    "keyword_search_terminalbench":"TerminalBench (keyword)",
    "теоретическая":               "Теоретическая (нет данных)",
}

CLASS_COLORS = {1: "#888888", 2: "#4472C4", 3: "#70AD47", 4: "#FF4444"}
CLASS_LABEL = {1: "Класс 1: невозможно", 2: "Класс 2: напрямую",
               3: "Класс 3: статистически", 4: "Класс 4: нецелесообразно"}

NAME_RU = {
    "code_error": "Ошибка в коде", "hallucination": "Галлюцинация",
    "instruction_adherence_failure": "Несоблюдение инструкций",
    "kv_cache_loss": "Потеря KV-кэша", "orchestration_failure": "Сбой оркестрации",
    "resource_abuse": "Избыточное потребление ресурсов",
    "misinterpretation_of_tool_output": "Неверная интерпретация результата",
    "guardrails_triggered": "Срабатывание защитных ограничений",
    "intent_not_supported": "Неподдерживаемое намерение",
    "tool_web_failure": "Сбой доступа к веб-ресурсу",
    "resource_not_found": "Ресурс не найден",
    "tool_timeout": "Таймаут вызова инструмента",
    "permission_error": "Ошибка доступа",
    "memory_error": "Ошибка памяти (OOM)",
    "invalid_invocation": "Некорректный вызов инструмента",
    "system_failure": "Системный сбой",
    "intent_plan_misalignment": "Несоответствие намерения и плана",
    "invention_of_new_information": "Изобретение информации",
    "underspecified_user_intent": "Недоопределённое намерение",
    "misinterpretation": "Неверная интерпретация",
    "factual_error": "Фактическая ошибка",
    "hardware_degradation": "Деградация оборудования",
    "gpu_throttling": "Троттлинг GPU",
    "correlated_ssd_failure": "Коррелированные сбои SSD",
    "network_power_failure": "Сетевые и power-сбои",
    "bad_retry_policy": "Неверная политика повторов",
    "kv_transfer_failure": "Сбой передачи KV-кэша",
    "memory_bandwidth_bottleneck": "Узкое место пропускной способности памяти",
}


def parse_params(params_str):
    if not isinstance(params_str, str) or "fit_failed" in params_str:
        return None
    try:
        parts = [p.strip() for p in params_str.split(",")]
        vals = []
        for p in parts:
            if "=" in p:
                vals.append(float(p.split("=")[1]))
            else:
                vals.append(float(p))
        return tuple(vals)
    except Exception:
        return None


def load_all_positions():
    """Load all position data for each (error_id, source)."""
    import json
    agentrx_dir = ROOT / "microsoft-AgentRx"
    trail_df = pd.read_csv(DATA_DIR / "trail_errors.csv")
    trail_df = trail_df[trail_df["error_id"].notna() &
                        ~trail_df["error_id"].isin(["unknown", "no_errors"])]
    ww_df = pd.read_csv(DATA_DIR / "who_and_when_handcrafted_classified.csv")
    kw_pos = pd.read_csv(DATA_DIR / "keyword_positions.csv")

    unif_map = {
        "Instruction/Plan Adherence Failure": "instruction_adherence_failure",
        "Instruction Adherence Failure": "instruction_adherence_failure",
        "Intent not supported": "intent_not_supported",
        "Intent Not Supported": "intent_not_supported",
        "Intent Plan Misalignment": "intent_plan_misalignment",
        "Misinterpretation of Tool Output": "misinterpretation_of_tool_output",
        "Invention of new information": "invention_of_new_information",
        "Underspecified User Intent": "underspecified_user_intent",
        "Guardrails Triggered": "guardrails_triggered",
        "Invalid Invocation": "invalid_invocation",
        "System Failure": "system_failure",
    }

    rx_lens = {}
    for fname in ["magentic_dataset.jsonl", "tau_retail_dataset.jsonl"]:
        with open(agentrx_dir / fname) as f:
            for line in f:
                obj = json.loads(line)
                rx_lens[obj["trajectory_id"]] = len(obj.get("steps", []))

    rx_positions = {}
    for fname, src in [("magentic_one.jsonl", "magentic_one"), ("tau_retail.jsonl", "tau_retail")]:
        with open(agentrx_dir / fname) as f:
            for line in f:
                obj = json.loads(line)
                tid = obj["trajectory_id"]
                tl = rx_lens.get(tid, 0)
                for fail in obj.get("failures", []):
                    cat = unif_map.get(fail.get("failure_category", ""), "unknown")
                    step = fail.get("step_number")
                    if cat != "unknown" and step is not None:
                        rx_positions.setdefault((cat, src), []).append(int(step))

    ww_positions = {}
    for _, row in ww_df.iterrows():
        cat = row.get("category_unified")
        step = row.get("step_number")
        if cat and cat != "unclassified" and step is not None:
            try:
                ww_positions.setdefault((cat, "who_and_when_hc"), []).append(int(step))
            except (ValueError, TypeError):
                pass

    kw_positions = {}
    for _, r in kw_pos.iterrows():
        kw_positions.setdefault((r["category"], f"keyword_search_{r['dataset']}"), []).append(
            r["first_occurrence_step"])

    # TRAIL normalized
    trail_norm = {}
    for _, r in trail_df.iterrows():
        trail_norm.setdefault((r["error_id"], "trail"), []).append(r["normalized_position"])

    return {
        "trail_norm": trail_norm,
        "rx": rx_positions,
        "ww": ww_positions,
        "kw": kw_positions,
    }


# ── B1: Индивидуальные графики ───────────────────────────────────────────────

def b1_histograms(df, all_pos):
    saved = []
    for _, row in df.iterrows():
        eid = row["error_id"]
        src = row["source"]
        n = row.get("step_n")
        try:
            n = int(float(n))
        except (ValueError, TypeError):
            n = 0
        if n < 20:
            continue

        # Get positions
        values = []
        if src == "trail":
            key = (eid, "trail")
            # normalized positions
            values = all_pos["trail_norm"].get(key, [])
        elif src in ("magentic_one", "tau_retail"):
            values = all_pos["rx"].get((eid, src), [])
        elif src == "who_and_when_hc":
            values = all_pos["ww"].get((eid, src), [])
        elif "keyword_search" in src:
            values = all_pos["kw"].get((eid, src), [])

        if len(values) < 20:
            continue

        v = np.array(values, dtype=float)
        color = SOURCE_COLOR.get(src, "#888888")
        name_ru = NAME_RU.get(eid, eid)
        label = f"{name_ru}\n{eid}"
        src_ru = SOURCE_LABEL.get(src, src)

        # Histogram
        bw = max(1, int(np.ptp(v) / 20) or 1)
        bins = np.arange(max(0, int(v.min()) - 1), int(v.max()) + 2 + bw, bw)

        fig, ax = plt.subplots(figsize=(9, 4))
        ax.hist(v, bins=bins, edgecolor="black", alpha=0.7, color=color)

        # Overlay fitted distribution if KS p > 0.05
        dist_name = row.get("best_distribution")
        ks_p = row.get("best_dist_ks_p")
        params_str = row.get("best_dist_params")
        if (isinstance(dist_name, str) and dist_name.strip() and
            isinstance(ks_p, float) and ks_p > 0.05):
            dist_obj = DIST_OBJECTS.get(dist_name)
            params = parse_params(str(params_str))
            if params and dist_obj:
                x = np.linspace(v.min(), v.max(), 300)
                try:
                    bin_width = bins[1] - bins[0]
                    scale = len(v) * bin_width
                    ax.plot(x, dist_obj.pdf(x, *params) * scale, color="#d62728", lw=2.5,
                            label=f"{dist_name} (KS p={ks_p:.3f})")
                    ax.legend(fontsize=9, loc="upper right")
                except Exception:
                    pass

        ax.set_xlabel("Номер шага / Step number")
        ax.set_ylabel("Число вхождений / Count")
        ax.set_title(f"{name_ru} / {eid}\n{src_ru}, n={n}")
        ax.grid(axis="y", alpha=0.3)
        fig.tight_layout()
        fname = f"hist_{eid}_{src}.png"
        fig.savefig(PLOTS_DIR / fname, dpi=150)
        plt.close(fig)
        saved.append(fname)

        # Q-Q plot if KS p > 0.05
        if isinstance(dist_name, str) and dist_name.strip() and isinstance(ks_p, float) and ks_p > 0.05:
            dist_obj = DIST_OBJECTS.get(dist_name)
            params = parse_params(str(params_str))
            if params and dist_obj:
                fig, ax = plt.subplots(figsize=(6, 5))
                try:
                    stats.probplot(v, dist=dist_obj, sparams=params, plot=ax)
                except Exception as e:
                    ax.text(0.5, 0.5, str(e), transform=ax.transAxes, ha="center")
                ax.set_title(f"Q-Q: {name_ru} / {eid}\n{dist_name}")
                ax.grid(alpha=0.3)
                fig.tight_layout()
                qname = f"qq_{eid}_{src}.png"
                fig.savefig(PLOTS_DIR / qname, dpi=150)
                plt.close(fig)
                saved.append(qname)

    print(f"B1: {len(saved)} графиков")
    return saved


# ── B2: Сводные графики ────────────────────────────────────────────────────────

def b2_p_trajectory_with_ci(df):
    """Горизонтальный барплот с error bars (Wilson CI). Цвет = источник."""
    plot_df = df[df["p_trajectory"].notna()].copy()
    plot_df["name_en"] = plot_df["error_id"]
    plot_df["name_ru"] = plot_df["error_id"].map(NAME_RU).fillna(plot_df["error_id"])
    plot_df["color"] = plot_df["source"].map(SOURCE_COLOR).fillna("#888888")
    plot_df = plot_df.sort_values("p_trajectory", ascending=True)

    fig, ax = plt.subplots(figsize=(14, max(7, len(plot_df) * 0.42)))

    y_pos = list(range(len(plot_df)))
    p_vals = plot_df["p_trajectory"].astype(float).values
    ci_lo = plot_df["p_traj_ci_lower"].astype(float).values
    ci_hi = plot_df["p_traj_ci_upper"].astype(float).values
    colors = plot_df["color"].values

    bars = ax.barh(y_pos, p_vals, xerr=[p_vals - ci_lo, ci_hi - p_vals],
                   color=colors, edgecolor="white", height=0.65,
                   error_kw={"elinewidth": 1.2, "capsize": 3, "ecolor": "#333333"},
                   alpha=0.85)
    ax.set_yticks(y_pos)
    labels = [f"{r['name_ru']}  ({r['error_id']})" for _, r in plot_df.iterrows()]
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("P(trajectory) / Вероятность в траектории")
    ax.set_title("Вероятность ошибки в траектории с 95% доверительным интервалом\n"
                 "P(trajectory) with 95% Wilson CI — цвет = источник данных / color = data source")

    # Value labels
    for bar, p in zip(bars, p_vals):
        ax.text(p + 0.005, bar.get_y() + bar.get_height() / 2,
                f"{p:.3f}", va="center", fontsize=6.5)

    # Source legend
    from matplotlib.patches import Patch
    unique_srcs = plot_df[["source", "color"]].drop_duplicates()
    legend_src = [Patch(facecolor=c, label=SOURCE_LABEL.get(s, s))
                  for _, (s, c) in unique_srcs.iterrows()]
    ax.legend(handles=legend_src, loc="lower right", fontsize=8,
               title="Источник / Source", title_fontsize=9)
    ax.set_xlim(0, min(1.05, plot_df["p_trajectory"].astype(float).max() * 1.25))
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "summary_p_trajectory.png", dpi=150)
    plt.close(fig)
    print("B2: summary_p_trajectory.png")


def b2_by_class(df):
    """Круговая диаграмма — ошибки по классам."""
    import re
    unique = df.drop_duplicates("error_id").copy()
    unique["_cls_int"] = unique["modeling_class"].apply(
        lambda x: int(m.group()) if (m := re.search(r"\d+", str(x))) else x)
    counts = unique["_cls_int"].value_counts().sort_index()
    labels = [f"{CLASS_LABEL.get(k, str(k))}\n({v})" for k, v in counts.items()]
    colors = [CLASS_COLORS.get(k, "#888888") for k in counts.index]

    fig, ax = plt.subplots(figsize=(9, 7))
    wedges, texts, autotexts = ax.pie(
        counts.values, labels=labels, colors=colors,
        autopct="%1.0f%%", startangle=90,
        textprops={"fontsize": 10})
    for at in autotexts:
        at.set_fontsize(10)
        at.set_fontweight("bold")
    ax.set_title("Распределение ошибок по классам моделируемости\n"
                 "Error distribution by modeling class")
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "summary_by_class.png", dpi=150)
    plt.close(fig)
    print("B2: summary_by_class.png")


def b2_n_observations(df):
    """log10(n) — цвет = источник."""
    plot_df = df[df["n_trajectories_with_error"].notna()].copy()
    plot_df["n"] = plot_df["n_trajectories_with_error"].astype(float)
    plot_df["log_n"] = np.log10(plot_df["n"] + 1)
    plot_df["color"] = plot_df["source"].map(SOURCE_COLOR).fillna("#888888")
    plot_df["label"] = plot_df.apply(
        lambda r: f"{NAME_RU.get(r['error_id'], r['error_id'])} / {r['error_id']}", axis=1)
    plot_df = plot_df.sort_values("log_n", ascending=True)

    fig, ax = plt.subplots(figsize=(13, max(7, len(plot_df) * 0.32)))
    y_pos = list(range(len(plot_df)))
    ax.barh(y_pos, plot_df["log_n"], color=plot_df["color"], edgecolor="white",
            height=0.65, alpha=0.85)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(plot_df["label"], fontsize=7.5)
    ax.set_xlabel("log₁₀(n + 1)  /  Объём данных")
    ax.set_title("Объём данных по ошибкам (log scale) — цвет = источник\n"
                 "Data volume per error — color = data source")
    ax.axvline(math.log10(20), color="orange", linestyle="--", lw=1.5,
               label="порог достаточности / sufficiency (n=20)")
    ax.axvline(math.log10(3000), color="red", linestyle="--", lw=1.5,
               label="порог надёжной подгонки / reliable fit (n=3000)")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "summary_n_observations.png", dpi=150)
    plt.close(fig)
    print("B2: summary_n_observations.png")


def b2_step_position(df, all_pos):
    """Box plot нормализованных позиций — цвет = источник."""
    series = {}
    for (eid, src), vals in all_pos["trail_norm"].items():
        if len(vals) >= 20:
            series[f"{NAME_RU.get(eid, eid)}/{eid}\n({SOURCE_LABEL.get(src, src)})"] = vals
    for (eid, src), vals in all_pos["rx"].items():
        if len(vals) >= 20:
            series[f"{NAME_RU.get(eid, eid)}/{eid}\n({SOURCE_LABEL.get(src, src)})"] = vals
    for (eid, src), vals in all_pos["ww"].items():
        if len(vals) >= 20:
            series[f"{NAME_RU.get(eid, eid)}/{eid}\n({SOURCE_LABEL.get(src, src)})"] = vals

    if not series:
        print("B2: нет данных для box plot")
        return

    sorted_items = sorted(series.items(), key=lambda x: float(np.median(x[1])))
    labels = [k for k, _ in sorted_items]
    data = [v for _, v in sorted_items]

    fig, ax = plt.subplots(figsize=(11, max(5, len(labels) * 0.52)))
    bp = ax.boxplot(data, vert=False, patch_artist=True,
                    boxprops=dict(facecolor="#AED6F1", color="#2E86C1", lw=1.2),
                    medianprops=dict(color="#d62728", lw=2),
                    whiskerprops=dict(color="#2E86C1"),
                    capprops=dict(color="#2E86C1"),
                    flierprops=dict(marker="o", markersize=4, alpha=0.5))
    ax.set_yticks(range(1, len(labels) + 1))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel("Нормализованная позиция (шаг / длина) / Normalized position")
    ax.set_title("Распределение позиций ошибок в траектории\n"
                 "Error position distribution — цвет = источник / color = data source")
    ax.set_xlim(0, 1)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(PLOTS_DIR / "summary_step_position.png", dpi=150)
    plt.close(fig)
    print("B2: summary_step_position.png")


def main():
    df = pd.read_csv(ROOT / "report" / "all_errors_final.csv")
    all_pos = load_all_positions()

    b1_histograms(df, all_pos)
    b2_p_trajectory_with_ci(df)
    b2_by_class(df)
    b2_n_observations(df)
    b2_step_position(df, all_pos)
    print("\nВсе графики сохранены.")


if __name__ == "__main__":
    main()