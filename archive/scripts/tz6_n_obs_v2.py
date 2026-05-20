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

df = pd.read_csv(ROOT + '/report/all_errors_final.csv')

step_n = df[df['step_n'].notna() & (df['step_n'] > 0)].copy()
step_n['log_n'] = step_n['step_n'].apply(lambda x: math.log10(float(x) + 1))
step_n['label'] = step_n['name_ru'] + ' (' + step_n['source'].map(SOURCE_LABEL) + ')'
step_n = step_n.sort_values('step_n', ascending=True)

fig, ax = plt.subplots(figsize=(13, max(9, len(step_n) * 0.55)))

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

x100 = math.log10(101)   # n = 100 порог
x3000 = math.log10(3001) # n = 3000 порог

ax.axvline(x100, color='#ffd700', linestyle='--', linewidth=2,
           label='порог достаточности (n=100)')
ax.axvline(x3000, color='red', linestyle='--', linewidth=2,
           label='порог надёжной подгонки (n=3000)')

unique_srcs = step_n[['source']].drop_duplicates()['source'].tolist()
legend_patches = [Patch(facecolor=SOURCE_COLOR.get(s, '#888888'), label=SOURCE_LABEL.get(s, s))
                   for s in unique_srcs if s in SOURCE_COLOR]
ax.legend(handles=legend_patches, fontsize=7, loc='lower right')

plt.tight_layout()
plt.savefig(OUT + 'summary_n_observations.png', dpi=150)
plt.close()
print("saved summary_n_observations.png")
