import math
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

ROOT = "/Volumes/MansurSSD/MAS_datasets_research"
OUT = ROOT + "/report/plots/"

SOURCE_COLOR = {
    "trail":                        "#1f77b4",
    "magentic_one":                 "#2ca02c",
    "tau_retail":                   "#228b22",
    "who_and_when_hc":             "#ff7f0e",
    "keyword_search_nebius":        "#9467bd",
    "keyword_search_itbench":       "#8c564b",
    "keyword_search_terminalbench": "#e377c2",
    "теоретическая":                "#7f7f7f",
}

SOURCE_LABEL = {
    "trail":                        "TRAIL (экспертная)",
    "magentic_one":                 "AgentRx / MagenticOne",
    "tau_retail":                   "AgentRx / TauRetail",
    "who_and_when_hc":             "Who&When HC (keyword)",
    "keyword_search_nebius":        "Nebius (keyword)",
    "keyword_search_itbench":       "ITBench (keyword)",
    "keyword_search_terminalbench": "TerminalBench (keyword)",
    "теоретическая":                "Теоретическая (нет данных)",
}

# ── P(trajectory) ─────────────────────────────────────────────────────────────
def plot_p_trajectory(df):
    rows = []
    for _, r in df.iterrows():
        if pd.notna(r.get('p_trajectory')) and r['p_trajectory'] != '':
            rows.append(r)
    rows.sort(key=lambda r: float(r['p_trajectory']), reverse=True)

    labels, colors, values, ci_lo, ci_hi = [], [], [], [], []
    for r in rows:
        src = str(r.get('source', ''))
        eid = str(r.get('error_id', ''))
        name_ru = str(r.get('name_ru', ''))
        lbl = f"{name_ru} [{eid}] ({SOURCE_LABEL.get(src, src)})"
        labels.append(lbl)
        colors.append(SOURCE_COLOR.get(src, '#888888'))
        p = float(r['p_trajectory'])
        values.append(p)
        ci_lo.append(p - float(r['p_traj_ci_lower']))
        ci_hi.append(float(r['p_traj_ci_upper']) - p)

    fig, ax = plt.subplots(figsize=(16, max(8, len(labels) * 0.45)))
    y = range(len(labels))
    ax.barh(list(y), values, xerr=[ci_lo, ci_hi], color=colors, height=0.6,
            error_kw={'linewidth': 1.2, 'ecolor': 'black', 'capsize': 3})
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=7.5)
    ax.set_xlabel('P(trajectory)', fontsize=10)
    ax.set_title('P(trajectory) по всем ошибкам\nцвет = источник / color = data source', fontsize=12)
    ax.set_xlim(0, 1)
    unique_srcs = list(dict.fromkeys([str(r.get('source', '')) for r in rows]))
    legend_patches = [Patch(facecolor=SOURCE_COLOR.get(s, '#888888'), label=SOURCE_LABEL.get(s, s))
                     for s in unique_srcs if s in SOURCE_COLOR]
    ax.legend(handles=legend_patches, loc='lower right', fontsize=7, ncol=2)
    plt.tight_layout()
    plt.savefig(OUT + 'summary_p_trajectory.png', dpi=150)
    plt.close()
    print("saved summary_p_trajectory.png")

# ── N observations (log scale + n labels) ────────────────────────────────────
def plot_n_observations(df):
    step_n = df[df['step_n'].notna() & (df['step_n'] > 0)].copy()
    step_n['log_n'] = step_n['step_n'].apply(lambda x: math.log10(float(x) + 1))
    # Label: name_ru [error_id] (source_label)
    step_n['label'] = (
        step_n['name_ru'].astype(str) + ' [' + step_n['error_id'].astype(str) + '] (' +
        step_n['source'].map(SOURCE_LABEL) + ')'
    )
    # Sort ascending (so highest n at top)
    step_n = step_n.sort_values('step_n', ascending=True)

    fig, ax = plt.subplots(figsize=(13, max(9, len(step_n) * 0.55)))
    ax.set_xlim(0, 5.5)
    colors = [SOURCE_COLOR.get(str(s), '#888888') for s in step_n['source']]
    y = range(len(step_n))
    bars = ax.barh(list(y), step_n['log_n'].values, color=colors, height=0.65, edgecolor='white')

    for i, (bar, n_val) in enumerate(zip(bars, step_n['step_n'].values)):
        ax.text(bar.get_width() + 0.04, bar.get_y() + bar.get_height() / 2,
                f'{int(n_val):,}', va='center', fontsize=6.5, color='black')

    ax.set_yticks(list(y))
    ax.set_yticklabels(step_n['label'].tolist(), fontsize=7)
    ax.set_xlabel('log₁₀(n + 1)', fontsize=10)
    ax.set_title('Объём наблюдений (log₁₀ шкала)\nцвет = источник / color = data source', fontsize=12)

    x100 = math.log10(101)
    x3000 = math.log10(3001)
    ax.axvline(x100, color='#ffd700', linestyle='--', linewidth=2)
    ax.axvline(x3000, color='red', linestyle='--', linewidth=2)

    y_max = len(step_n) - 1

    # Colored zone bands across full plot height (reliable visibility)
    ax.axvspan(0, x100, alpha=0.08, color='#ffd700', zorder=0)
    ax.axvspan(x100, x3000, alpha=0.05, color='gray', zorder=0)
    ax.axvspan(x3000, 5.5, alpha=0.08, color='red', zorder=0)

    # Zone labels at top of plot area
    ax.text(x100 / 2, y_max + 0.6, 'недостаточно', fontsize=9, color='#ffd700',
            ha='center', va='bottom', fontweight='bold')
    ax.text((x100 + x3000) / 2, y_max + 0.6, 'частично', fontsize=9, color='gray',
            ha='center', va='bottom', fontweight='bold')
    ax.text((x3000 + 5.5) / 2, y_max + 0.6, 'достаточно', fontsize=9, color='red',
            ha='center', va='bottom', fontweight='bold')

    unique_srcs = step_n[['source']].drop_duplicates()['source'].tolist()
    legend_patches = [Patch(facecolor=SOURCE_COLOR.get(s, '#888888'), label=SOURCE_LABEL.get(s, s))
                     for s in unique_srcs if s in SOURCE_COLOR]
    # Add threshold line legend entries (simple, honest)
    from matplotlib.lines import Line2D
    legend_patches += [
        Line2D([0], [0], color='#ffd700', linestyle='--', linewidth=2,
               label='n = 100'),
        Line2D([0], [0], color='red', linestyle='--', linewidth=2,
               label='n = 3000'),
    ]
    ax.legend(handles=legend_patches, fontsize=7, loc='lower right')
    ax.set_ylim(-0.8, len(step_n) + 1.5)
    plt.tight_layout()
    plt.savefig(OUT + 'summary_n_observations.png', dpi=150)
    plt.close()
    print("saved summary_n_observations.png")

# ── MAIN ──────────────────────────────────────────────────────────────────────
df = pd.read_csv(ROOT + '/report/all_errors_final.csv')
plot_p_trajectory(df)
plot_n_observations(df)

# remove summary_step_position.png if exists
import os
step_pos_path = OUT + 'summary_step_position.png'
if os.path.exists(step_pos_path):
    os.remove(step_pos_path)
    print("removed summary_step_position.png")