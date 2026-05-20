"""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
ТЗ №7 — Подгонка и сравнение распределений для tool_web_failure / nebius
"""

import numpy as np
import pandas as pd
import scipy.stats as stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import diptest
from scipy.optimize import minimize
from scipy.special import gammaln
import os
import warnings
warnings.filterwarnings('ignore')

BASE = "/Volumes/MansurSSD/MAS_datasets_research"
DATA = f"{BASE}/data"
REPORT = f"{BASE}/report"
PLOTS = f"{REPORT}/plots"

os.makedirs(PLOTS, exist_ok=True)

# ─────────────────────────────────────────────
# A1. Загрузка данных
# ─────────────────────────────────────────────
print("=" * 60)
print("A1. Загрузка данных")
print("=" * 60)

df = pd.read_csv(f"{DATA}/keyword_positions.csv")
mask = (df['category'] == 'tool_web_failure') & (df['dataset'] == 'nebius')
nebius_twf = df[mask].copy()
nebius_twf.to_csv(f"{DATA}/tz7_tool_web_failure_positions.csv", index=False)
print(f"Строк: {len(nebius_twf)}")

pos_abs = nebius_twf['first_occurrence_step'].values.astype(float)
pos_norm = nebius_twf['normalized_position'].values.astype(float)
traj_len = nebius_twf['trajectory_length'].values.astype(float)

# ─────────────────────────────────────────────
# A2. Базовые статистики
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("A2. Базовые статистики")
print("=" * 60)

def basic_stats(arr, name=""):
    n = len(arr)
    p = np.percentile(arr, [10, 25, 50, 75, 90, 95, 99])
    s = stats.skew(arr)
    k = stats.kurtosis(arr)
    print(f"\n  {name}")
    print(f"  n={n}, mean={arr.mean():.4f}, median={np.median(arr):.4f}, std={arr.std():.4f}")
    print(f"  min={arr.min():.4f}, max={arr.max():.4f}")
    print(f"  p10={p[0]:.4f}, p25={p[1]:.4f}, p50={p[2]:.4f}, p75={p[3]:.4f}, p90={p[4]:.4f}, p95={p[5]:.4f}, p99={p[6]:.4f}")
    print(f"  IQR={p[3]-p[1]:.4f}, skewness={s:.4f}, kurtosis={k:.4f}")
    return {
        'n': n, 'mean': arr.mean(), 'median': np.median(arr), 'std': arr.std(),
        'min': arr.min(), 'max': arr.max(),
        'p10': p[0], 'p25': p[1], 'p50': p[2], 'p75': p[3], 'p90': p[4], 'p95': p[5], 'p99': p[6],
        'IQR': p[3]-p[1], 'skewness': s, 'kurtosis': k
    }

stats_abs = basic_stats(pos_abs, "Абсолютные позиции [шаги]")
stats_norm = basic_stats(pos_norm, "Нормализованные позиции [0,1]")

# Histogram bins for normalized
bins_norm = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
bin_counts = np.histogram(pos_norm, bins=bins_norm)[0]
bin_pcts = bin_counts / len(pos_norm) * 100
print("\n  Распределение нормализованных по бинам:")
for i in range(len(bin_counts)):
    print(f"  [{bins_norm[i]:.1f}, {bins_norm[i+1]:.1f}]: {bin_counts[i]:6d} ({bin_pcts[i]:.1f}%)")

# ─────────────────────────────────────────────
# B1-B3. MLE для всех кандидатов
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("B. Подгонка распределений (MLE)")
print("=" * 60)

n = len(pos_abs)
n_norm = len(pos_norm)
ln_n = np.log(n)

quantile_points = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]

def emp_quantiles(data, q):
    return np.percentile(data, np.array(q) * 100)

def quantile_error(data, fitted_dist, q_points):
    eq = emp_quantiles(data, q_points)
    tq = np.array([fitted_dist.ppf(p) for p in q_points])
    rmse = np.sqrt(np.mean((eq - tq) ** 2))
    max_ae = np.max(np.abs(eq - tq))
    mape = np.mean(np.abs((eq - tq) / eq)) * 100
    return rmse, max_ae, mape, eq, tq

def ks_to_empirical(data, fitted_dist):
    sorted_data = np.sort(data)
    ecdf = np.arange(1, len(sorted_data) + 1) / (len(sorted_data) + 1)
    tcdf = fitted_dist.cdf(sorted_data)
    return np.max(np.abs(ecdf - tcdf))

def aic_bic(log_lik, k, n):
    aic = 2 * k - 2 * log_lik
    bic = k * np.log(n) - 2 * log_lik
    return aic, bic

def make_results_row(name, scale, k, log_lik, params, dist_obj, rmse, max_ae, mape, ks, eq, tq, note=""):
    aic, bic = aic_bic(log_lik, k, n if scale == 'absolute' else n_norm)
    return {
        'distribution': name, 'scale': scale, 'k': k, 'log_lik': log_lik,
        'AIC': aic, 'BIC': bic, 'DeltaAIC': np.nan,
        'RMSE_quantiles': rmse, 'MaxAE': max_ae, 'MAPE': mape,
        'KS_to_empirical': ks, 'note': note,
        '_params': params, '_dist': dist_obj, '_eq': eq, '_tq': tq
    }

results = []

# ─── НОРМАЛИЗОВАННЫЕ [0,1] ───────────────────────

print("\n  === Нормализованные позиции ===")

# 1. Beta(a, b, loc=0, scale=1)  k=2
beta_params = stats.beta.fit(pos_norm, floc=0, fscale=1)
a_beta, b_beta = beta_params[0], beta_params[1]
beta_dist_norm = stats.beta(a_beta, b_beta, loc=0, scale=1)
log_lik_beta = np.sum(beta_dist_norm.logpdf(pos_norm))
rmse_b, mae_b, mape_b, eq_b, tq_b = quantile_error(pos_norm, beta_dist_norm, quantile_points)
ks_b = ks_to_empirical(pos_norm, beta_dist_norm)
print(f"  Beta: a={a_beta:.4f}, b={b_beta:.4f}, log_lik={log_lik_beta:.2f}, AIC={2*2-2*log_lik_beta:.2f}")
results.append(make_results_row('Beta', 'normalized', 2, log_lik_beta,
    {'a': a_beta, 'b': b_beta}, beta_dist_norm, rmse_b, mae_b, mape_b, ks_b, eq_b, tq_b))

# 2. Truncated Normal  k=2
lo, hi = 0.0, 1.0
tnorm_a = (lo - pos_norm.mean()) / pos_norm.std()
tnorm_b = (hi - pos_norm.mean()) / pos_norm.std()
tloc, tscale = pos_norm.mean(), pos_norm.std()
tnorm_params = stats.truncnorm.fit(pos_norm, lo, hi)
tloc2, tscale2 = tnorm_params[0] * tnorm_params[2] + tnorm_params[1], tnorm_params[2]
tloc2 = tnorm_params[1]
tscale2 = tnorm_params[2]
# Re-fit properly
tloc2 = tnorm_params[1]
tscale2 = tnorm_params[2]
tnorm_dist = stats.truncnorm(tnorm_a, tnorm_b, loc=tloc2, scale=tscale2)
# actually use scipy fit output properly
tnorm_dist2 = stats.truncnorm(*tnorm_params)
log_lik_tn = np.sum(tnorm_dist2.logpdf(pos_norm))
rmse_tn, mae_tn, mape_tn, eq_tn, tq_tn = quantile_error(pos_norm, tnorm_dist2, quantile_points)
ks_tn = ks_to_empirical(pos_norm, tnorm_dist2)
print(f"  TruncNorm: loc={tloc2:.4f}, scale={tscale2:.4f}, log_lik={log_lik_tn:.2f}")
results.append(make_results_row('TruncNorm', 'normalized', 2, log_lik_tn,
    {'loc': tloc2, 'scale': tscale2}, tnorm_dist2, rmse_tn, mae_tn, mape_tn, ks_tn, eq_tn, tq_tn))

# 3. Shifted Beta (вручную: loc/scale не фиксированы)  k=4
# Beta с произвольным loc и scale на [0,1] эквивалентна Beta(a,b) на loc=0, scale=1
# поэтому Shifted Beta = Beta с ненулевым shift — но на [0,1] shift невозможен
# Используем Beta(a,b) но k=4 (a,b,loc,scale)
shift_beta_params = stats.beta.fit(pos_norm)
a_sb, b_sb, loc_sb, scale_sb = shift_beta_params
sb_dist = stats.beta(a_sb, b_sb, loc=loc_sb, scale=scale_sb)
log_lik_sb = np.sum(sb_dist.logpdf(pos_norm))
rmse_sb, mae_sb, mape_sb, eq_sb, tq_sb = quantile_error(pos_norm, sb_dist, quantile_points)
ks_sb = ks_to_empirical(pos_norm, sb_dist)
print(f"  ShiftedBeta: a={a_sb:.4f}, b={b_sb:.4f}, loc={loc_sb:.4f}, scale={scale_sb:.4f}")
results.append(make_results_row('ShiftedBeta', 'normalized', 4, log_lik_sb,
    {'a': a_sb, 'b': b_sb, 'loc': loc_sb, 'scale': scale_sb}, sb_dist, rmse_sb, mae_sb, mape_sb, ks_sb, eq_sb, tq_sb))

# ─── АБСОЛЮТНЫЕ [2, 594] ─────────────────────────

print("\n  === Абсолютные позиции ===")

# 4. Shifted Exponential (вручную)  k=2
# F(x) = 1 - exp(-(x - loc_min) / scale), x >= loc_min
# loc_min фиксирован = 2 (min наблюдаемый)
loc_min_exp = 2.0
x_shifted = pos_abs - loc_min_exp
scale_exp_mle = x_shifted.mean()
log_lik_exp = np.sum(stats.expon(loc=loc_min_exp, scale=scale_exp_mle).logpdf(pos_abs))
exp_dist = stats.expon(loc=loc_min_exp, scale=scale_exp_mle)
rmse_exp, mae_exp, mape_exp, eq_exp, tq_exp = quantile_error(pos_abs, exp_dist, quantile_points)
ks_exp = ks_to_empirical(pos_abs, exp_dist)
print(f"  ShiftedExp: loc_min={loc_min_exp}, scale={scale_exp_mle:.4f}, log_lik={log_lik_exp:.2f}")
results.append(make_results_row('ShiftedExp', 'absolute', 2, log_lik_exp,
    {'loc_min': loc_min_exp, 'scale': scale_exp_mle}, exp_dist, rmse_exp, mae_exp, mape_exp, ks_exp, eq_exp, tq_exp))

# 5. Weibull_min (c, loc, scale)  k=3
# Фиксируем loc = 2 (min наблюдаемый)
wb_loc_fixed = 2.0
weibull_params = stats.weibull_min.fit(pos_abs, floc=wb_loc_fixed)
c_wb, scale_wb = weibull_params[0], weibull_params[2]
wb_dist = stats.weibull_min(c_wb, loc=wb_loc_fixed, scale=scale_wb)
log_lik_wb = np.sum(wb_dist.logpdf(pos_abs))
rmse_wb, mae_wb, mape_wb, eq_wb, tq_wb = quantile_error(pos_abs, wb_dist, quantile_points)
ks_wb = ks_to_empirical(pos_abs, wb_dist)
print(f"  Weibull: c={c_wb:.4f}, loc={wb_loc_fixed}, scale={scale_wb:.4f}")
results.append(make_results_row('Weibull', 'absolute', 3, log_lik_wb,
    {'c': c_wb, 'loc': wb_loc_fixed, 'scale': scale_wb}, wb_dist, rmse_wb, mae_wb, mape_wb, ks_wb, eq_wb, tq_wb))

# 6. Gamma(a, loc, scale)  k=3
gamma_params = stats.gamma.fit(pos_abs)
a_gamma, loc_gamma, scale_gamma = gamma_params
gamma_dist = stats.gamma(a_gamma, loc=loc_gamma, scale=scale_gamma)
log_lik_gamma = np.sum(gamma_dist.logpdf(pos_abs))
rmse_ga, mae_ga, mape_ga, eq_ga, tq_ga = quantile_error(pos_abs, gamma_dist, quantile_points)
ks_ga = ks_to_empirical(pos_abs, gamma_dist)
print(f"  Gamma: a={a_gamma:.4f}, loc={loc_gamma:.4f}, scale={scale_gamma:.4f}")
results.append(make_results_row('Gamma', 'absolute', 3, log_lik_gamma,
    {'a': a_gamma, 'loc': loc_gamma, 'scale': scale_gamma}, gamma_dist, rmse_ga, mae_ga, mape_ga, ks_ga, eq_ga, tq_ga))

# 7. LogNormal(s, loc, scale)  k=3
lognorm_params = stats.lognorm.fit(pos_abs)
s_ln, loc_ln, scale_ln = lognorm_params
ln_dist = stats.lognorm(s_ln, loc=loc_ln, scale=scale_ln)
log_lik_ln = np.sum(ln_dist.logpdf(pos_abs))
rmse_ln, mae_ln, mape_ln, eq_ln, tq_ln = quantile_error(pos_abs, ln_dist, quantile_points)
ks_ln = ks_to_empirical(pos_abs, ln_dist)
print(f"  LogNormal: s={s_ln:.4f}, loc={loc_ln:.4f}, scale={scale_ln:.4f}")
results.append(make_results_row('LogNormal', 'absolute', 3, log_lik_ln,
    {'s': s_ln, 'loc': loc_ln, 'scale': scale_ln}, ln_dist, rmse_ln, mae_ln, mape_ln, ks_ln, eq_ln, tq_ln))

# 8. Shifted LogNormal (вручную)  k=3
# Сдвинутое: x' = x - loc_min, логарифм, потом обратно
loc_min_ln = 2.0
x_sh = pos_abs - loc_min_ln
log_data = np.log(x_sh[x_sh > 0])
mu_sh = log_data.mean()
sigma_sh = log_data.std(ddof=1)
shift_ln_dist = stats.lognorm(s=sigma_sh, loc=0, scale=np.exp(mu_sh))
# сдвиг: f(x) = lognorm.pdf(x - loc_min) для x >= loc_min
def shifted_lognorm_pdf(x, s, loc_min, scale_param):
    x_sh = x - loc_min
    x_sh = np.maximum(x_sh, 1e-10)
    return stats.lognorm(s=s, loc=0, scale=scale_param).pdf(x_sh)

def shifted_lognorm_cdf(x, s, loc_min, scale_param):
    x_sh = x - loc_min
    x_sh = np.maximum(x_sh, 1e-10)
    return stats.lognorm(s=s, loc=0, scale=scale_param).cdf(x_sh)

# Оцениваем параметры MLE для сдвинутого lognormal
def neg_log_lik_shln(params, x, loc_min):
    s, scale_param = params
    if s <= 0 or scale_param <= 0:
        return 1e10
    x_sh = x - loc_min
    x_sh = np.maximum(x_sh, 1e-10)
    ll = np.sum(stats.lognorm(s=s, loc=0, scale=scale_param).logpdf(x_sh))
    return -ll

from scipy.optimize import minimize_scalar
res_sl = minimize(neg_log_lik_shln, [sigma_sh, np.exp(mu_sh)], args=(pos_abs, loc_min_ln),
                 bounds=[(0.1, 5.0), (1.0, 100.0)], method='L-BFGS-B')
s_sl, scale_sl = res_sl.x
log_lik_sl = -res_sl.fun
sl_dist = {'s': s_sl, 'loc_min': loc_min_ln, 'scale': scale_sl}
rmse_sl, mae_sl, mape_sl, eq_sl, tq_sl = np.nan, np.nan, np.nan, np.nan, np.nan
# approximate quantile error
class ShiftedLN:
    def __init__(self, s, loc_min, scale):
        self.s = s; self.loc_min = loc_min; self.scale = scale
        self.base = stats.lognorm(s=s, loc=0, scale=scale)
    def ppf(self, p):
        return self.base.ppf(p) + self.loc_min
    def cdf(self, x):
        return self.base.cdf(x - self.loc_min)
    def pdf(self, x):
        return self.base.pdf(x - self.loc_min)
sln_dist = ShiftedLN(s_sl, loc_min_ln, scale_sl)
rmse_sl, mae_sl, mape_sl, eq_sl, tq_sl = quantile_error(pos_abs, sln_dist, quantile_points)
ks_sl = ks_to_empirical(pos_abs, sln_dist)
print(f"  ShiftedLogNormal: s={s_sl:.4f}, loc_min={loc_min_ln}, scale={scale_sl:.4f}")
results.append(make_results_row('ShiftedLogNormal', 'absolute', 3, log_lik_sl,
    {'s': s_sl, 'loc_min': loc_min_ln, 'scale': scale_sl}, sln_dist, rmse_sl, mae_sl, mape_sl, ks_sl, eq_sl, tq_sl))

# ─────────────────────────────────────────────
# E1. Hartigan's dip test
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("E. Проверка на бимодальность")
print("=" * 60)

dip_norm, p_dip_norm = diptest.diptest(pos_norm)
print(f"  Нормализованные: dip={dip_norm:.4f}, p={p_dip_norm:.4f}  → {'БИМОДАЛЬНЫ' if p_dip_norm < 0.05 else 'унимодально'}")

dip_abs, p_dip_abs = diptest.diptest(pos_abs)
print(f"  Абсолютные: dip={dip_abs:.4f}, p={p_dip_abs:.4f}  → {'БИМОДАЛЬНЫ' if p_dip_abs < 0.05 else 'унимодально'}")

run_mixture = p_dip_abs < 0.05
print(f"\n  Mixture of 2 Exponentials: {'ЗАПУСК' if run_mixture else 'ПРОПУСК'}")

# ─────────────────────────────────────────────
# B2. Mixture of 2 Shifted Exponentials (EM)
# ─────────────────────────────────────────────
if run_mixture:
    print("\n  === Mixture of 2 Shifted Exponentials (EM) ===")

    class Mix2Exp:
        def __init__(self, pi, loc1, scale1, loc2, scale2):
            self.pi = pi
            self.loc1 = loc1; self.scale1 = scale1
            self.loc2 = loc2; self.scale2 = scale2
            self.d1 = stats.expon(loc=loc1, scale=scale1)
            self.d2 = stats.expon(loc=loc2, scale=scale2)

        def pdf(self, x):
            return self.pi * self.d1.pdf(x) + (1 - self.pi) * self.d2.pdf(x)

        def logpdf(self, x):
            p1 = self.pi * self.d1.pdf(x)
            p2 = (1 - self.pi) * self.d2.pdf(x)
            p = np.maximum(p1 + p2, 1e-300)
            return np.log(p)

        def cdf(self, x):
            return self.pi * self.d1.cdf(x) + (1 - self.pi) * self.d2.cdf(x)

        def ppf(self, q):
            # inverse CDF — brute force
            x_grid = np.linspace(1, 600, 10000)
            cdf_vals = self.cdf(x_grid)
            return np.interp(q, cdf_vals, x_grid)

        def quantile(self, p):
            return self.ppf(p)

    def em_mixture(x, max_iter=200, tol=1e-6):
        # init
        pi = 0.5
        loc1 = 2.0
        scale1 = x.mean() / 2
        loc2 = 10.0
        scale2 = x.mean()
        ll_prev = -np.inf

        for it in range(max_iter):
            # E-step
            p1 = pi * stats.expon(loc=loc1, scale=scale1).pdf(x)
            p2 = (1 - pi) * stats.expon(loc=loc2, scale=scale2).pdf(x)
            denom = np.maximum(p1 + p2, 1e-300)
            gamma = p1 / denom

            # M-step
            n1 = np.sum(gamma)
            n2 = len(x) - n1
            pi = n1 / len(x)
            if n1 > 1:
                x_g1 = x[gamma > 0.01]
                g1_g = gamma[gamma > 0.01]
                loc1 = x_g1.min() - 1e-3
                scale1 = np.sum(g1_g * (x_g1 - loc1)) / np.sum(g1_g) if np.sum(g1_g) > 0 else x_g1.mean()
            if n2 > 1:
                x_g2 = x[gamma < 0.99]
                g2_g = 1 - gamma[gamma < 0.99]
                loc2 = x_g2.min() - 1e-3
                scale2 = np.sum(g2_g * (x_g2 - loc2)) / np.sum(g2_g) if np.sum(g2_g) > 0 else x_g2.mean()

            scale1 = max(scale1, 0.1)
            scale2 = max(scale2, 0.1)
            loc1 = max(loc1, 0.0)
            loc2 = max(loc2, 0.0)

            ll = np.sum(np.log(np.maximum(pi * stats.expon(loc=loc1, scale=scale1).pdf(x) +
                                          (1-pi) * stats.expon(loc=loc2, scale=scale2).pdf(x), 1e-300)))
            if abs(ll - ll_prev) < tol:
                break
            ll_prev = ll

        mix = Mix2Exp(pi, loc1, scale1, loc2, scale2)
        return pi, loc1, scale1, loc2, scale2, ll, mix

    pi_m, loc1_m, sc1_m, loc2_m, sc2_m, ll_mix, mix_dist = em_mixture(pos_abs)
    print(f"  pi={pi_m:.4f}, loc1={loc1_m:.4f}, scale1={sc1_m:.4f}")
    print(f"  loc2={loc2_m:.4f}, scale2={sc2_m:.4f}, log_lik={ll_mix:.2f}")
    results.append(make_results_row('Mix2Exp', 'absolute', 5, ll_mix,
        {'pi': pi_m, 'loc1': loc1_m, 'scale1': sc1_m, 'loc2': loc2_m, 'scale2': sc2_m},
        mix_dist, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, note='смесь'))

# ─────────────────────────────────────────────
# C. Сравнение моделей: вычисление DeltaAIC
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("C. Сравнение моделей")
print("=" * 60)

df_res = pd.DataFrame(results)
best_aic_norm = df_res[df_res['scale'] == 'normalized']['AIC'].min()
best_aic_abs = df_res[df_res['scale'] == 'absolute']['AIC'].min()
df_res['DeltaAIC'] = df_res.apply(
    lambda r: r['AIC'] - best_aic_norm if r['scale'] == 'normalized' else r['AIC'] - best_aic_abs, axis=1)

# Финальная сортировка
df_res = df_res.sort_values('DeltaAIC').reset_index(drop=True)

print("\n  НОРМАЛИЗОВАННЫЕ:")
print(df_res[df_res['scale']=='normalized'][['distribution','k','log_lik','AIC','BIC','DeltaAIC','RMSE_quantiles','MaxAE','KS_to_empirical']].to_string(index=False))
print("\n  АБСОЛЮТНЫЕ:")
print(df_res[df_res['scale']=='absolute'][['distribution','k','log_lik','AIC','BIC','DeltaAIC','RMSE_quantiles','MaxAE','KS_to_empirical']].to_string(index=False))

# ─────────────────────────────────────────────
# D1. Q-Q графики
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("D. Визуализация")
print("=" * 60)

# Q-Q для нормализованных
for _, row in df_res[df_res['scale'] == 'normalized'].iterrows():
    name = row['distribution']
    dist_obj = row['_dist']
    fig, ax = plt.subplots(figsize=(6, 5))
    emp_q = row['_eq']
    theor_q = row['_tq']
    q_labels = [f'p{int(q*100)}' for q in quantile_points]
    ax.scatter(emp_q, theor_q, s=30, alpha=0.8, zorder=3)
    lims = [min(emp_q.min(), theor_q.min()) - 0.02, max(emp_q.max(), theor_q.max()) + 0.02]
    ax.plot(lims, lims, 'k--', lw=1, label='y=x', zorder=2)
    ax.set_xlabel('Эмпирические квантили')
    ax.set_ylabel('Теоретические квантили')
    ax.set_title(f'Q-Q: {name} (нормализованные)\nΔAIC={row["DeltaAIC"]:.2f}, KS={row["KS_to_empirical"]:.4f}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fname = f"{PLOTS}/qq_tool_web_failure_nebius_{name.lower()}.png"
    plt.savefig(fname, dpi=120)
    plt.close()
    print(f"  Сохранён: qq_tool_web_failure_nebius_{name.lower()}.png")

# Q-Q для абсолютных
for _, row in df_res[df_res['scale'] == 'absolute'].iterrows():
    name = row['distribution']
    dist_obj = row['_dist']
    fig, ax = plt.subplots(figsize=(6, 5))
    emp_q = row['_eq']
    theor_q = row['_tq']
    if np.any(np.isnan(emp_q)):
        continue
    ax.scatter(emp_q, theor_q, s=30, alpha=0.8, zorder=3)
    lims = [min(emp_q.min(), theor_q.min()) - 5, max(emp_q.max(), theor_q.max()) + 5]
    ax.plot(lims, lims, 'k--', lw=1, label='y=x', zorder=2)
    ax.set_xlabel('Эмпирические квантили (шаг)')
    ax.set_ylabel('Теоретические квантили (шаг)')
    ax.set_title(f'Q-Q: {name} (абсолютные)\nΔAIC={row["DeltaAIC"]:.2f}, KS={row["KS_to_empirical"]:.4f}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fname = f"{PLOTS}/qq_tool_web_failure_nebius_{name.lower()}.png"
    plt.savefig(fname, dpi=120)
    plt.close()
    print(f"  Сохранён: qq_tool_web_failure_nebius_{name.lower()}.png")

# ─────────────────────────────────────────────
# D2. Heatmap Beta на нормализованных
# ─────────────────────────────────────────────
print("  Построение heatmap Beta...")
alpha_grid = np.linspace(0.5, 3.0, 50)
beta_grid = np.linspace(0.5, 3.0, 50)
rmse_grid = np.zeros((50, 50))
quantile_points_hm = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
emp_q_hm = emp_quantiles(pos_norm, quantile_points_hm)

for i, a in enumerate(alpha_grid):
    for j, b in enumerate(beta_grid):
        d = stats.beta(a, b, loc=0, scale=1)
        tq = np.array([d.ppf(p) for p in quantile_points_hm])
        rmse_grid[j, i] = np.sqrt(np.mean((emp_q_hm - tq) ** 2))

fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(rmse_grid, extent=[0.5, 3.0, 3.0, 0.5], origin='upper',
               aspect='auto', cmap='viridis_r')
plt.colorbar(im, ax=ax, label='RMSE квантилей')
ax.set_xlabel(r'$\alpha$')
ax.set_ylabel(r'$\beta$')
ax.set_title(r'Heatmap Beta($\alpha$,$\beta$) — RMSE квантилей')
# Оптимум
idx_min = np.unravel_index(np.argmin(rmse_grid), rmse_grid.shape)
ax.scatter(alpha_grid[idx_min[1]], beta_grid[idx_min[0]], color='red', s=80, marker='*',
           label=f'Оптимум: α={alpha_grid[idx_min[1]]:.2f}, β={beta_grid[idx_min[0]]:.2f}', zorder=5)
ax.legend()
plt.tight_layout()
plt.savefig(f"{PLOTS}/heatmap_beta_quantiles.png", dpi=120)
plt.close()
print(f"  Сохранён: heatmap_beta_quantiles.png")

# ─────────────────────────────────────────────
# D3. Heatmap Weibull на абсолютных
# ─────────────────────────────────────────────
print("  Построение heatmap Weibull...")
c_grid = np.linspace(0.5, 3.0, 50)
scale_grid = np.linspace(5, 50, 50)
rmse_grid_w = np.zeros((50, 50))
emp_q_w = emp_quantiles(pos_abs, quantile_points_hm)

for i, c in enumerate(c_grid):
    for j, sc in enumerate(scale_grid):
        d = stats.weibull_min(c, loc=2, scale=sc)
        tq = np.array([d.ppf(p) for p in quantile_points_hm])
        rmse_grid_w[j, i] = np.sqrt(np.mean((emp_q_w - tq) ** 2))

fig, ax = plt.subplots(figsize=(8, 6))
im2 = ax.imshow(rmse_grid_w, extent=[0.5, 3.0, 50, 5], origin='upper',
                aspect='auto', cmap='viridis_r')
plt.colorbar(im2, ax=ax, label='RMSE квантилей')
ax.set_xlabel('c (shape)')
ax.set_ylabel('scale')
ax.set_title('Heatmap Weibull_min(c, loc=2, scale) — RMSE квантилей')
idx_min_w = np.unravel_index(np.argmin(rmse_grid_w), rmse_grid_w.shape)
ax.scatter(c_grid[idx_min_w[1]], scale_grid[idx_min_w[0]], color='red', s=80, marker='*',
           label=f'Оптимум: c={c_grid[idx_min_w[1]]:.2f}, scale={scale_grid[idx_min_w[0]]:.2f}', zorder=5)
ax.legend()
plt.tight_layout()
plt.savefig(f"{PLOTS}/heatmap_weibull_quantiles.png", dpi=120)
plt.close()
print(f"  Сохранён: heatmap_weibull_quantiles.png")

# ─────────────────────────────────────────────
# D4. Лучшее распределение — гистограмма + кривая
# ─────────────────────────────────────────────
best_norm = df_res[df_res['scale'] == 'normalized'].iloc[0]
best_abs = df_res[df_res['scale'] == 'absolute'].iloc[0]

# Нормализованные
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(pos_norm, bins=60, density=True, alpha=0.6, color='steelblue', label='Данные')
x_g = np.linspace(0, 1, 500)
ax.plot(x_g, best_norm['_dist'].pdf(x_g), 'r-', lw=2,
        label=f'{best_norm["distribution"]} (ΔAIC={best_norm["DeltaAIC"]:.2f})')
ax.set_xlabel('Нормализованная позиция')
ax.set_ylabel('Плотность')
ax.set_title(f'{best_norm["distribution"]} — лучшее на нормализованных')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{PLOTS}/best_fit_normalized.png", dpi=120)
plt.close()
print(f"  Сохранён: best_fit_normalized.png")

# Абсолютные
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(pos_abs, bins=60, density=True, alpha=0.6, color='steelblue', label='Данные')
x_g = np.linspace(2, 600, 500)
ax.plot(x_g, best_abs['_dist'].pdf(x_g), 'r-', lw=2,
        label=f'{best_abs["distribution"]} (ΔAIC={best_abs["DeltaAIC"]:.2f})')
ax.set_xlabel('Шаг в траектории')
ax.set_ylabel('Плотность')
ax.set_title(f'{best_abs["distribution"]} — лучшее на абсолютных')
ax.legend()
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(f"{PLOTS}/best_fit_absolute.png", dpi=120)
plt.close()
print(f"  Сохранён: best_fit_absolute.png")

# ─────────────────────────────────────────────
# D5. Сравнительный Q-Q (все кандидаты на одном)
# ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

colors = plt.cm.tab10.colors
# Нормализованные
ax = axes[0]
emp_q_norm_all = emp_quantiles(pos_norm, quantile_points)
for idx, (_, row) in enumerate(df_res[df_res['scale'] == 'normalized'].iterrows()):
    if np.any(np.isnan(row['_eq'])):
        continue
    ax.plot(range(len(quantile_points)), row['_eq'] - row['_tq'],
            marker='o', label=row['distribution'], color=colors[idx % 10], lw=1.5)
ax.axhline(0, color='black', ls='--', lw=0.8)
ax.set_xticks(range(len(quantile_points)))
ax.set_xticklabels([f'p{int(q*100)}' for q in quantile_points])
ax.set_xlabel('Квантиль')
ax.set_ylabel('Ошибка (эмпир. − теорет.)')
ax.set_title('Нормализованные: ошибка квантилей')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Абсолютные
ax = axes[1]
emp_q_abs_all = emp_quantiles(pos_abs, quantile_points)
for idx, (_, row) in enumerate(df_res[df_res['scale'] == 'absolute'].iterrows()):
    if np.any(np.isnan(row['_eq'])):
        continue
    ax.plot(range(len(quantile_points)), row['_eq'] - row['_tq'],
            marker='o', label=row['distribution'], color=colors[idx % 10], lw=1.5)
ax.axhline(0, color='black', ls='--', lw=0.8)
ax.set_xticks(range(len(quantile_points)))
ax.set_xticklabels([f'p{int(q*100)}' for q in quantile_points])
ax.set_xlabel('Квантиль')
ax.set_ylabel('Ошибка (эмпир. − теорет.)')
ax.set_title('Абсолютные: ошибка квантилей')
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

plt.suptitle('Q-Q ошибки: все кандидаты', fontsize=12)
plt.tight_layout()
plt.savefig(f"{PLOTS}/qq_all_candidates.png", dpi=120)
plt.close()
print(f"  Сохранён: qq_all_candidates.png")

# ─────────────────────────────────────────────
# E2. KDE для визуальной проверки бимодальности
# ─────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Нормализованные
ax = axes[0]
kde_norm = stats.gaussian_kde(pos_norm, bw_method=0.05)
x_kn = np.linspace(0, 1, 500)
ax.plot(x_kn, kde_norm(x_kn), 'b-', lw=2, label='KDE (bw=0.05)')
ax.hist(pos_norm, bins=60, density=True, alpha=0.3, color='gray', label='Гистограмма')
ax.set_xlabel('Нормализованная позиция')
ax.set_ylabel('Плотность')
ax.set_title(f'KDE нормализованных\ndip={dip_norm:.4f}, p={p_dip_norm:.4f}')
ax.legend()
ax.grid(True, alpha=0.3)

# Абсолютные
ax = axes[1]
kde_abs = stats.gaussian_kde(pos_abs, bw_method=0.02)
x_ka = np.linspace(2, 600, 500)
ax.plot(x_ka, kde_abs(x_ka), 'b-', lw=2, label='KDE (bw=0.02)')
ax.hist(pos_abs, bins=60, density=True, alpha=0.3, color='gray', label='Гистограмма')
ax.set_xlabel('Шаг')
ax.set_ylabel('Плотность')
ax.set_title(f'KDE абсолютных\ndip={dip_abs:.4f}, p={p_dip_abs:.4f}')
ax.legend()
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(f"{PLOTS}/kde_bimodality_check.png", dpi=120)
plt.close()
print(f"  Сохранён: kde_bimodality_check.png")

# ─────────────────────────────────────────────
# F. Финальная таблица
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("F. Сохранение таблиц")
print("=" * 60)

cols = ['distribution','scale','k','log_lik','AIC','BIC','DeltaAIC',
        'RMSE_quantiles','MaxAE','MAPE','KS_to_empirical','note']
df_final = df_res[cols].copy()
df_final['RMSE_quantiles'] = df_final['RMSE_quantiles'].round(6)
df_final['MaxAE'] = df_final['MaxAE'].round(4)
df_final['MAPE'] = df_final['MAPE'].round(4)
df_final['KS_to_empirical'] = df_final['KS_to_empirical'].round(6)
df_final['log_lik'] = df_final['log_lik'].round(2)
df_final['AIC'] = df_final['AIC'].round(2)
df_final['BIC'] = df_final['BIC'].round(2)
df_final['DeltaAIC'] = df_final['DeltaAIC'].round(2)

df_final.to_csv(f"{REPORT}/tz7_distribution_comparison.csv", index=False)
print(f"  Сохранён: tz7_distribution_comparison.csv")
print(df_final.to_string(index=False))

# ─────────────────────────────────────────────
# G. Финальные параметры
# ─────────────────────────────────────────────
print("\n" + "=" * 60)
print("G. Финальные параметры")
print("=" * 60)

print(f"\n  === Лучшее на нормализованных: {best_norm['distribution']} ===")
print(f"  Параметры: {best_norm['_params']}")
print(f"  k={best_norm['k']}, AIC={best_norm['AIC']:.2f}, BIC={best_norm['BIC']:.2f}")
print(f"  ΔAIC={best_norm['DeltaAIC']:.2f}, RMSE_quantiles={best_norm['RMSE_quantiles']:.6f}")
print(f"  KS_to_empirical={best_norm['KS_to_empirical']:.6f}")
print(f"  Квантили (эмпир. vs теорет.):")
eqn = best_norm['_eq']
tqn = best_norm['_tq']
for i, q in enumerate(quantile_points):
    print(f"    p{int(q*100):02d}: эмпир={eqn[i]:.4f}, теорет={tqn[i]:.4f}, ошибка={eqn[i]-tqn[i]:.4f}")

print(f"\n  === Лучшее на абсолютных: {best_abs['distribution']} ===")
print(f"  Параметры: {best_abs['_params']}")
print(f"  k={best_abs['k']}, AIC={best_abs['AIC']:.2f}, BIC={best_abs['BIC']:.2f}")
print(f"  ΔAIC={best_abs['DeltaAIC']:.2f}, RMSE_quantiles={best_abs['RMSE_quantiles']:.6f}")
print(f"  KS_to_empirical={best_abs['KS_to_empirical']:.6f}")

if not np.any(np.isnan(best_abs['_eq'])):
    eqa = best_abs['_eq']
    tqa = best_abs['_tq']
    print(f"  Квантили (эмпир. vs теорет.):")
    for i, q in enumerate(quantile_points):
        print(f"    p{int(q*100):02d}: эмпир={eqa[i]:.2f}, теорет={tqa[i]:.2f}, ошибка={eqa[i]-tqa[i]:.2f}")

print("\n  ГОТОВО!")
