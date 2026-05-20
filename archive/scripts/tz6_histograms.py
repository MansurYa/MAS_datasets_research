import pandas as pd
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import json
import os
from scipy.stats import beta, gamma, lognorm, weibull_min, expon

OUT = '/Volumes/MansurSSD/MAS_datasets_research/report/plots/'
SRC = '/Volumes/MansurSSD/MAS_datasets_research/data/'

CLASS_COLORS = {
    'Категория 1': '#808080',
    'Категория 2': '#1f77b4',
    'Категория 3': '#2ca02c',
    'Категория 4': '#d62728',
}

# ── Mapping from AgentRx failure_category to unified error_id ─────────────────
CATEGORY_MAP = {
    'Instruction Adherence Failure': 'instruction_adherence_failure',
    'Instruction/Plan Adherence Failure': 'instruction_adherence_failure',
    'Misinterpretation of Tool Output': 'misinterpretation_of_tool_output',
    'Intent Not Supported': 'intent_not_supported',
    'Intent/Plan Mismatch': 'intent_plan_misalignment',
    'Guardrails Triggered': 'guardrails_triggered',
    'System Failure': 'system_failure',
    'Invalid Tool Invocation': 'invalid_invocation',
    'Invention of New Information': 'invention_of_new_information',
    'Underspecified User Intent': 'underspecified_user_intent',
    'Code Generation Error': 'code_error',
    'Hallucination': 'hallucination',
    'Factual Error': 'factual_error',
    'Resource Not Found': 'resource_not_found',
    'Resource Exhaustion': 'resource_abuse',
    'Orchestration Failure': 'orchestration_failure',
    'Tool Timeout': 'tool_timeout',
    'Web Failure': 'tool_web_failure',
}

def parse_params(s):
    if not s or pd.isna(s) or str(s).strip() == '':
        return None
    try:
        parts = {}
        for p in str(s).replace('"', '').split(','):
            if '=' in p:
                k, v = p.split('=', 1)
                parts[k.strip()] = float(v.strip())
        return parts
    except:
        return None

def draw_pdf(ax, dist, params, x_min, x_max, color='#d62728', label=''):
    x = np.linspace(x_min, x_max, 300)
    try:
        if dist == 'beta':
            y = beta.pdf(x, params['a'], params['b'], loc=params.get('loc', 0), scale=params.get('scale', 1))
        elif dist == 'gamma':
            y = gamma.pdf(x, params['shape'], loc=params.get('loc', 0), scale=params.get('scale', 1))
        elif dist == 'lognorm':
            y = lognorm.pdf(x, params['s'], loc=params.get('loc', 0), scale=params.get('scale', 1))
        elif dist == 'weibull_min':
            y = weibull_min.pdf(x, params['shape'], loc=params.get('loc', 0), scale=params.get('scale', 1))
        elif dist == 'exponential':
            y = expon.pdf(x, loc=params.get('loc', 0), scale=params.get('scale', 1))
        elif dist == 'lomax':
            from scipy.stats import lomax
            y = lomax.pdf(x, params.get('c', 1), loc=params.get('loc', 0), scale=params.get('scale', 1))
        ax.plot(x, y, color=color, linewidth=2, label=label)
    except Exception:
        pass

# ── Load raw positions from all four sources ──────────────────────────────────

# 1. TRAIL from trail_errors_v2.csv (error_id → steps)
trail_positions = {}
trail_df = pd.read_csv(SRC + 'trail_errors_v2.csv')
for eid, grp in trail_df.groupby('error_id'):
    vals = grp['error_step'].dropna().values
    if len(vals) > 0 and str(eid) not in ('no_errors', ''):
        trail_positions[('trail', str(eid))] = vals.astype(float)

# 2. Keyword search from keyword_positions.csv
kw_positions = {}
kw_df = pd.read_csv(SRC + 'keyword_positions.csv')
for cat, grp in kw_df.groupby('category'):
    vals = grp['first_occurrence_step'].dropna().values
    if len(vals) > 0:
        src_label = grp['dataset'].iloc[0]
        kw_positions[(f'keyword_search_{src_label}', str(cat))] = vals.astype(float)

AGENTRX_DIR = '/Volumes/MansurSSD/MAS_datasets_research/microsoft-AgentRx/'

# 3. AgentRx from JSONL (failures array, failure_category → unified error_id)
agentrx_positions = {}
for fname, src_label in [
    ('magentic_one.jsonl', 'magentic_one'),
    ('tau_retail.jsonl', 'tau_retail'),
]:
    try:
        with open(AGENTRX_DIR + fname) as f:
            for line in f:
                rec = json.loads(line)
                for failure in rec.get('failures', []):
                    cat_raw = failure.get('failure_category', '')
                    if not cat_raw:
                        continue
                    eid = CATEGORY_MAP.get(cat_raw, cat_raw.lower().replace(' ', '_'))
                    step_num = failure.get('step_number', 0)
                    if step_num > 0:
                        key = (src_label, eid)
                        if key not in agentrx_positions:
                            agentrx_positions[key] = []
                        agentrx_positions[key].append(float(step_num))
    except Exception as e:
        print(f"AgentRx load error ({fname}): {e}")

for k in agentrx_positions:
    if isinstance(agentrx_positions[k], list):
        agentrx_positions[k] = np.array(agentrx_positions[k])

# 4. Who&When HC from hand-crafted CSV
ww_positions = {}
ww_df = pd.read_csv(SRC + 'who_and_when_handcrafted_classified.csv')
for cat, grp in ww_df.groupby('category_unified'):
    vals = grp['step_number'].dropna().values
    if len(vals) > 0:
        ww_positions[('who_and_when_hc', str(cat))] = vals.astype(float)

print("Data sources loaded:")
print(f"  TRAIL: {sorted(trail_positions.keys())}")
print(f"  Keyword: {sorted(kw_positions.keys())}")
print(f"  AgentRx: {sorted(agentrx_positions.keys())}")
print(f"  Who&When HC: {sorted(ww_positions.keys())}")

# Merge all into one dict
ALL_POSITIONS = {}
for d in [trail_positions, kw_positions, agentrx_positions, ww_positions]:
    ALL_POSITIONS.update(d)

# ── Load CSV and generate histograms ─────────────────────────────────────────
df = pd.read_csv('/Volumes/MansurSSD/MAS_datasets_research/report/all_errors_final.csv')

os.makedirs(OUT, exist_ok=True)

def make_hist(eid, src, positions, modeling_class, name_ru, fit_conclusion,
              best_dist, best_params, step_n):
    color = CLASS_COLORS.get(modeling_class, '#999999')
    fit_conc = str(fit_conclusion)

    # Show fitted curve only if "подгонка найдена" (strict: n>=100 AND p>=0.05)
    show_curve = 'подгонка найдена' in fit_conc and 'низкая мощность' not in fit_conc
    bimodal = 'бимодальное' in fit_conc

    fig, ax = plt.subplots(figsize=(8, 5))
    n_bins = min(30, max(10, int(np.sqrt(len(positions)))))
    ax.hist(positions, bins=n_bins, color=color, edgecolor='white', alpha=0.8, density=True)

    if show_curve and best_dist and best_params:
        x_min = max(0, positions.min() - 2)
        x_max = positions.max() + 5
        params = parse_params(best_params)
        if params:
            draw_pdf(ax, best_dist, params, x_min, x_max, '#d62728', f'{best_dist} fit')

    src_lbl = src
    bimodal_note = ' (возможно бимодальное)' if bimodal else ''
    ax.set_title(f'{name_ru} — {src_lbl}{bimodal_note}\nn={len(positions)}, класс={modeling_class}', fontsize=10)
    ax.set_xlabel('Номер шага', fontsize=9)
    ax.set_ylabel('Плотность', fontsize=9)
    if show_curve:
        ax.legend(fontsize=8)

    plt.tight_layout()
    safe_src = src.replace('/', '_').replace(' ', '_')
    plt.savefig(OUT + f'hist_{eid}_{safe_src}.png', dpi=150)
    plt.close()

processed = 0
for _, row in df.iterrows():
    eid = str(row['error_id'])
    src = str(row.get('source', ''))
    step_n = row.get('step_n', 0)
    if pd.isna(step_n) or int(step_n) < 20:
        continue

    key = (src, eid)
    positions = ALL_POSITIONS.get(key)

    if positions is None or len(positions) == 0:
        print(f"  no raw positions for {eid}/{src} (step_n={step_n})")
        continue

    mc = str(row.get('modeling_class', 'Категория 3'))
    make_hist(eid, src, positions, mc,
              row['name_ru'],
              row.get('fit_conclusion_ru', ''),
              row.get('best_distribution', ''),
              row.get('best_dist_params', ''),
              step_n)
    print(f"  saved hist_{eid}_{src}.png")
    processed += 1

print(f"\nDone: {processed} histograms saved to {OUT}")