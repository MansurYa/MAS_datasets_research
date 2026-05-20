import pandas as pd
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats

df = pd.read_csv('/Volumes/MansurSSD/MAS_datasets_research/report/all_errors_final.csv')

CLASS_COLORS = {
    'Категория 1': '#808080',
    'Категория 2': '#1f77b4',
    'Категория 3': '#2ca02c',
    'Категория 4': '#d62728',
}
OUT = '/Volumes/MansurSSD/MAS_datasets_research/report/plots/'

# ---- График 1: P(trajectory) по всем ошибкам ----
fig, ax = plt.subplots(figsize=(14, 14))
rows = []
for _, r in df.iterrows():
    if pd.notna(r['p_trajectory']) and r['p_trajectory'] != '':
        rows.append(r)
rows.sort(key=lambda r: r['p_trajectory'], reverse=True)

labels = []
colors = []
values = []
ci_lower = []
ci_upper = []
for r in rows:
    src = str(r.get('source', ''))
    eid = str(r.get('error_id', ''))
    lbl = f"{r['name_ru']} ({src})"
    labels.append(lbl)
    colors.append(CLASS_COLORS.get(str(r['modeling_class']), '#999999'))
    values.append(r['p_trajectory'])
    ci_lower.append(r['p_trajectory'] - r['p_traj_ci_lower'])
    ci_upper.append(r['p_traj_ci_upper'] - r['p_trajectory'])

y = range(len(labels))
ax.barh(list(y), values, xerr=[ci_lower, ci_upper], color=colors, height=0.6,
        error_kw={'linewidth': 1.2, 'ecolor': 'black', 'capsize': 3})
ax.set_yticks(list(y))
ax.set_yticklabels(labels, fontsize=8)
ax.set_xlabel('P(trajectory)', fontsize=10)
ax.set_title('P(trajectory) по всем ошибкам\n(цвет — класс моделирования)', fontsize=12)
ax.set_xlim(0, 1)
patches = [mpatches.Patch(color=v, label=k.replace('Категория', 'Класс')) for k, v in CLASS_COLORS.items()]
ax.legend(handles=patches, loc='lower right', fontsize=8)
plt.tight_layout()
plt.savefig(OUT + 'summary_p_trajectory.png', dpi=150)
plt.close()
print("saved summary_p_trajectory.png")

# ---- График 2: Pie chart по классам ----
cat_counts = df['modeling_class'].value_counts().sort_index()
cat_labels = ['Класс 1:\nневозможно\n({})'.format(cat_counts.get('Категория 1', 0)),
              'Класс 2:\nнапрямую\n({})'.format(cat_counts.get('Категория 2', 0)),
              'Класс 3:\nстатистически\n({})'.format(cat_counts.get('Категория 3', 0)),
              'Класс 4:\nнецелесообразно\n({})'.format(cat_counts.get('Категория 4', 0))]
cat_colors = [CLASS_COLORS.get(c, '#999999') for c in ['Категория 1','Категория 2','Категория 3','Категория 4']]
vals = [cat_counts.get(c, 0) for c in ['Категория 1','Категория 2','Категория 3','Категория 4']]
fig, ax = plt.subplots(figsize=(8, 8))
ax.pie(vals, labels=cat_labels, colors=cat_colors, startangle=90,
       textprops={'fontsize': 10})
ax.set_title('Распределение ошибок по классам моделирования', fontsize=12)
plt.tight_layout()
plt.savefig(OUT + 'summary_by_class.png', dpi=150)
plt.close()
print("saved summary_by_class.png")

# ---- График 3: log10(n) шкала ----
step_n = df[df['step_n'].notna() & (df['step_n'] > 0)].copy()
step_n['log_n'] = np.log10(step_n['step_n'] + 1)
step_n['label'] = step_n['name_ru'] + ' (' + step_n['source'].astype(str) + ')'
fig, ax = plt.subplots(figsize=(12, 10))
colors3 = [CLASS_COLORS.get(str(r['modeling_class']), '#999999') for _, r in step_n.iterrows()]
ax.scatter(step_n['log_n'], range(len(step_n)), c=colors3, s=50, zorder=3)
ax.set_yticks(range(len(step_n)))
ax.set_yticklabels(step_n['label'], fontsize=7)
ax.set_xlabel('log₁₀(n + 1)', fontsize=10)
ax.set_title('Объём наблюдений (log₁₀ шкала)\nцвет — класс моделирования', fontsize=12)
x20 = np.log10(20 + 1)
x100 = np.log10(100 + 1)
ax.axvline(x20, color='orange', linestyle='--', linewidth=1.5, label='порог достаточности (n=20)')
ax.axvline(x100, color='red', linestyle='--', linewidth=1.5, label='порог надёжной подгонки (n=100)')
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(OUT + 'summary_n_observations.png', dpi=150)
plt.close()
print("saved summary_n_observations.png")

# ---- График 4: Box plot нормализованных позиций ----
# Для TRAIL: есть trajectory_length из total_steps/n_trajectories_total
# normalized position = step / trajectory_length
norm_rows = []
for _, r in df.iterrows():
    if pd.notna(r.get('step_n')) and r.get('step_n', 0) >= 20:
        if pd.notna(r.get('total_steps')) and pd.notna(r.get('n_trajectories_with_error')):
            avg_len = r['total_steps'] / max(r['n_trajectories_with_error'], 1)
            if avg_len > 0 and pd.notna(r.get('step_mean')):
                norm_rows.append({
                    'name': r['name_ru'] + ' (' + str(r['source']) + ')',
                    'modeling_class': str(r['modeling_class']),
                    'norm_mean': r['step_mean'] / avg_len,
                })
norm_df = pd.DataFrame(norm_rows)
if len(norm_df) > 0:
    classes = ['Категория 1', 'Категория 2', 'Категория 3', 'Категория 4']
    fig, ax = plt.subplots(figsize=(12, 6))
    positions = {}
    cur = 1
    for c in classes:
        subset = norm_df[norm_df['modeling_class'] == c]
        if len(subset) == 0:
            continue
        for _, row in subset.iterrows():
            ax.bar(cur, row['norm_mean'], color=CLASS_COLORS.get(c, '#999999'), width=0.6)
            ax.text(cur, row['norm_mean'] + 0.02, row['name'], fontsize=6, ha='center', va='bottom', rotation=30)
            cur += 1
        cur += 1
    ax.axhline(1.0, color='red', linestyle='--', linewidth=1, label='конец траектории')
    ax.set_ylabel('Нормализованная позиция (шаг / длина траектории)', fontsize=9)
    ax.set_title('Нормализованные позиции ошибок по классам\n(step_mean / avg_trajectory_length)', fontsize=11)
    patches = [mpatches.Patch(color=v, label=k.replace('Категория', 'Класс')) for k, v in CLASS_COLORS.items()]
    ax.legend(handles=patches, fontsize=8)
    plt.tight_layout()
    plt.savefig(OUT + 'summary_step_position.png', dpi=150)
    plt.close()
    print("saved summary_step_position.png")

print("Summary plots done.")