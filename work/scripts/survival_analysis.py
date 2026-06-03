#!/usr/bin/env python3
"""
TZ_6: Анализ выживаемости и математическое моделирование отказов.

Артефакты:
  - work/data/reliability_plots/TZ_6_exp{1,2,3}_*.png  — Probability Plots
  - work/data/TZ_6_fit_params.csv                   — параметры фитов (CSV)
  - work/reports/TZ_6_survival_analysis_report.md   — отчёт (пишется вручную)

Входные данные:
  - work/data/TZ_3_trajectory_lengths.csv (80 036 строк, индекс = global_traj_idx)
  - work/data/errors_invalid_invocation.json (317 349 записей A/B/E1/E2)

Методология: Survival Analysis с right-censored данными.
Библиотека: reliability.Fitters (Fit_Everything, Fit_Weibull_Mixture, Fit_Weibull_CR).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sstats

from reliability.Fitters import (
    Fit_Everything,
    Fit_Weibull_Mixture,
    Fit_Weibull_CR,
)

# === Пути ===
PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = PROJECT_ROOT / "work" / "data"
ERRORS_JSON = DATA_DIR / "errors_invalid_invocation.json"
LENGTHS_CSV = DATA_DIR / "TZ_3_trajectory_lengths.csv"
PLOTS_DIR = DATA_DIR / "reliability_plots"
PARAMS_CSV = DATA_DIR / "TZ_6_fit_params.csv"

CATEGORIES = ["A", "B", "E1", "E2"]
SAMPLE_SIZE = 10_000
RANDOM_STATE = 42


# ---------------------------------------------------------------------------
# Утилиты
# ---------------------------------------------------------------------------

def extract_weibull_beta_and_ad(fe) -> tuple[float | None, float | None]:
    """Извлекает β (shape) и AD-статистику из Fit_Everything.

    Работает даже если лучшее распределение — не Вейбулл.
    Ищет Weibull_2P или Weibull_3P в results DataFrame.
    Возвращает (beta, AD). Если Weibull недоступен — (None, None).
    """
    beta, ad = None, None
    try:
        results_df = fe.results
        for dist_name in ["Weibull_2P", "Weibull_3P"]:
            wrow = results_df[results_df["Distribution"] == dist_name]
            if len(wrow) > 0:
                beta = float(wrow["Beta"].values[0])
                ad = float(wrow["AD"].values[0])
                break
    except Exception:
        pass
    return beta, ad


def extract_mixture_alpha12(fe) -> tuple[float | None, float | None]:
    """Извлекает alpha_1 и alpha_2 из Weibull_Mixture в results DataFrame.

    Внимание: в results DataFrame колонки называются 'Alpha 1' и 'Alpha 2' (с пробелом).
    """
    alpha_1, alpha_2 = None, None
    try:
        results_df = fe.results
        wrow = results_df[results_df["Distribution"] == "Weibull_Mixture"]
        if len(wrow) > 0:
            row = wrow.iloc[0]
            if "Alpha 1" in results_df.columns:
                a1_val = row.get("Alpha 1")
                a2_val = row.get("Alpha 2")
                if a1_val is not None and not np.isnan(float(a1_val)):
                    alpha_1 = float(a1_val)
                if a2_val is not None and not np.isnan(float(a2_val)):
                    alpha_2 = float(a2_val)
    except Exception:
        pass
    return alpha_1, alpha_2


def extract_best_params(fe) -> dict:
    """Извлекает параметры лучшего распределения из Fit_Everything.

    Fit_Everything не имеет атрибута .BIC напрямую.
    BIC лучшего берём из fe.results (колонка 'BIC', строка best_distribution_name).
    """
    dist_name = fe.best_distribution_name  # строка, например 'weibull_2p'

    result = {
        "best_distribution": dist_name,
        "alpha": None,
        "beta": None,
        "AD": None,
        "BIC": None,
        "alpha_1": None,
        "alpha_2": None,
    }

    # BIC лучшего — из results DataFrame
    try:
        results_df = fe.results
        best_row = results_df[results_df["Distribution"] == dist_name]
        if len(best_row) > 0:
            result["BIC"] = float(best_row["BIC"].values[0])
            result["AD"] = float(best_row["AD"].values[0])
            # alpha из строки лучшего распределения
            for col in ["Alpha", "Alpha 1", "Mu"]:
                if col in best_row.columns:
                    val = best_row[col].values[0]
                    if val is not None and not isinstance(val, str) and not np.isnan(float(val)):
                        result["alpha"] = float(val)
                        break
    except Exception:
        pass

    # β и AD из Weibull_2P (даже если лучшее другое)
    beta_wb, ad_wb = extract_weibull_beta_and_ad(fe)
    if beta_wb is not None:
        result["beta"] = beta_wb
        result["AD"] = ad_wb

    return result


def stratified_sample(df: pd.DataFrame, n: int, stratify_by: str,
                     random_state: int = 42) -> pd.DataFrame:
    """Стратифицированный downsampling.

    Сохраняет пропорции групп `stratify_by` из df в выборке размером n.
    """
    rng = np.random.default_rng(random_state)
    groups = df.groupby(stratify_by).groups
    n_groups = {g: len(idx) for g, idx in groups.items()}

    sampled_indices = []
    for group, group_indices in groups.items():
        proportion = n_groups[group] / len(df)
        n_from_group = int(round(n * proportion))
        # Минимум 1, если группа непуста
        n_from_group = max(1, min(n_from_group, len(group_indices)))
        chosen = rng.choice(list(group_indices), size=n_from_group, replace=False)
        sampled_indices.extend(chosen)

    return df.loc[sampled_indices].copy()


# ---------------------------------------------------------------------------
# Задача 1: Загрузка и downsampling
# ---------------------------------------------------------------------------

def load_and_sample() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Загружает данные и делает стратифицированный downsampling.

    Returns:
        df_sample: 10 000 траекторий с global_traj_idx как index
        df_err_sample: ошибки только для траекторий в df_sample
    """
    print("[1/5] Загрузка данных...")
    t0 = time.time()

    # CSV: индекс = global_traj_idx
    df_traj = pd.read_csv(LENGTHS_CSV)
    df_traj.index = pd.RangeIndex(start=0, stop=len(df_traj), step=1, name="global_traj_idx")
    print(f"      Траектории загружены: {len(df_traj)} ({time.time()-t0:.1f}s)")

    # JSON: объединить все 4 категории
    with open(ERRORS_JSON) as f:
        data = json.load(f)
    frames = []
    for cat, items in data.items():
        df_cat = pd.DataFrame(items)
        frames.append(df_cat)
    df_err = pd.concat(frames, ignore_index=True)
    print(f"      Ошибки загружены: {len(df_err)} ({time.time()-t0:.1f}s)")

    # Стратифицированный downsampling
    print(f"[1/5] Стратифицированный downsampling (N={SAMPLE_SIZE}, seed={RANDOM_STATE})...")
    df_sample = stratified_sample(df_traj, n=SAMPLE_SIZE, stratify_by="exit_group",
                                  random_state=RANDOM_STATE)
    sample_indices = set(df_sample.index)

    # Ошибки только для траекторий в сэмпле (БЕЗ inner join!)
    df_err_sample = df_err[df_err["global_traj_idx"].isin(sample_indices)].copy()
    print(f"      Сэмпл траекторий: {len(df_sample)}")
    print(f"      Ошибки в сэмпле: {len(df_err_sample)}")
    print(f"      Группы в сэмпле:")
    for g, n in df_sample["exit_group"].value_counts().items():
        print(f"        {g}: {n} ({n/len(df_sample)*100:.1f}%)")

    return df_sample, df_err_sample


# ---------------------------------------------------------------------------
# Задача 2: Эксперимент 1 — Right-Wall (Гильотина Среды)
# ---------------------------------------------------------------------------

def run_experiment_1(df_sample: pd.DataFrame) -> dict:
    """Right-Wall Analysis: распределение лимита контекста."""
    print("\n[2/5] Эксперимент 1: Right-Wall Analysis...")

    failures = df_sample[df_sample["exit_group"] == "limit_hit"]["n_chars"].values
    censored = df_sample[df_sample["exit_group"].isin(["success", "failed"])]["n_chars"].values
    print(f"      Failures (limit_hit): {len(failures)}")
    print(f"      Right-Censored (success+failed): {len(censored)}")

    fe = Fit_Everything(
        failures=failures,
        right_censored=censored,
        sort_by="BIC",
        print_results=False,
        show_histogram_plot=False,
        show_PP_plot=False,
        show_probability_plot=True,
        show_best_distribution_probability_plot=False,
    )

    # Сохраняем график
    fig = plt.gcf()
    fig.savefig(PLOTS_DIR / "TZ_6_exp1_right_wall_prob.png", dpi=140)
    plt.close(fig)
    print(f"      → сохранено: TZ_6_exp1_right_wall_prob.png")

    params = extract_best_params(fe)

    # Для Weibull_Mixture: извлечь alpha_1, alpha_2 из results
    if params["best_distribution"] == "Weibull_Mixture":
        a1, a2 = extract_mixture_alpha12(fe)
        params["alpha_1"] = a1
        params["alpha_2"] = a2

    print(f"      Лучшее распределение: {params['best_distribution']}")
    alpha_str = f"{params['alpha']:.1f}" if params["alpha"] is not None else "N/A"
    beta_str = f"{params['beta']:.3f}" if params["beta"] is not None else "N/A"
    ad_str = f"{params['AD']:.3f}" if params["AD"] is not None else "N/A"
    bic_str = f"{params['BIC']:.2f}" if params["BIC"] is not None else "N/A"
    print(f"      α={alpha_str}, β={beta_str}, AD={ad_str}, BIC={bic_str}")

    return {
        "experiment": "exp1_right_wall",
        "n_failures": len(failures),
        "n_censored": len(censored),
        **params,
    }


# ---------------------------------------------------------------------------
# Задача 3: Эксперимент 2 — Context Rot для A, B, E1, E2
# ---------------------------------------------------------------------------

def run_experiment_2(df_sample: pd.DataFrame, df_err_sample: pd.DataFrame) -> list[dict]:
    """Context Rot Analysis: 4 категории ошибок, описательная статистика + фитинг."""
    print("\n[3/5] Эксперимент 2: Context Rot Analysis (A, B, E1, E2)...")

    results = []
    sample_idx = set(df_sample.index)

    for cat in CATEGORIES:
        print(f"\n      === Категория {cat} ===")
        t0 = time.time()

        # First occurrence ошибок из сэмпла
        first_err = df_err_sample[
            (df_err_sample["category"] == cat) &
            df_err_sample["is_first_occurrence_in_traj"]
        ]
        failures_arr = first_err["chars_up_to_error"].values

        # Цензурированные: траектории из сэмпла БЕЗ ошибок этой категории
        traj_with_cat = set(first_err["global_traj_idx"])
        censored_arr = df_sample[~df_sample.index.isin(traj_with_cat)]["n_chars"].values

        print(f"      Failures: {len(failures_arr)}, Right-Censored: {len(censored_arr)}")

        # Описательная статистика (до фитинга)
        if len(failures_arr) > 1:
            desc = {
                "n": len(failures_arr),
                "mean": float(np.mean(failures_arr)),
                "std": float(np.std(failures_arr, ddof=1)),
                "skew": float(sstats.skew(failures_arr)),
                "kurtosis": float(sstats.kurtosis(failures_arr)),
                "min": int(np.min(failures_arr)),
                "q50": float(np.median(failures_arr)),
                "max": int(np.max(failures_arr)),
            }
        else:
            desc = {k: None for k in ["n", "mean", "std", "skew", "kurtosis", "min", "q50", "max"]}

        print(f"      skew={desc['skew']:.3f}, kurtosis={desc['kurtosis']:.3f} "
              f"({time.time()-t0:.1f}s)")

        # Фитинг (только если достаточно данных)
        if len(failures_arr) < 4:
            print(f"      ⚠ Недостаточно данных для фитинга (n={len(failures_arr)})")
            fit_result = {k: None for k in
                          ["best_distribution", "alpha", "beta", "AD", "BIC", "beta_source"]}
        else:
            try:
                fe = Fit_Everything(
                    failures=failures_arr,
                    right_censored=censored_arr,
                    sort_by="BIC",
                    print_results=False,
                    show_histogram_plot=False,
                    show_PP_plot=False,
                    show_probability_plot=True,
                    show_best_distribution_probability_plot=False,
                )
                fit_result = extract_best_params(fe)

                # Сохраняем график
                fig = plt.gcf()
                fig.savefig(PLOTS_DIR / f"TZ_6_exp2_{cat}_prob.png", dpi=140)
                plt.close(fig)
                print(f"      → сохранено: TZ_6_exp2_{cat}_prob.png")

                bd = fit_result["best_distribution"]
                a = f"{fit_result['alpha']}" if fit_result["alpha"] else "N/A"
                b = f"{fit_result['beta']}" if fit_result["beta"] else "N/A"
                ad = f"{fit_result['AD']}" if fit_result["AD"] else "N/A"
                bic = f"{fit_result['BIC']}" if fit_result["BIC"] else "N/A"
                print(f"      best={bd}, α={a}, β={b}, AD={ad}, BIC={bic}")

            except Exception as e:
                print(f"      ⚠ Фитинг не удался: {e}")
                fit_result = {k: None for k in
                             ["best_distribution", "alpha", "beta", "AD", "BIC", "beta_source"]}

        results.append({
            "experiment": "exp2_context_rot",
            "category": cat,
            **desc,
            **fit_result,
        })

    return results


# ---------------------------------------------------------------------------
# Задача 4: Эксперимент 3 — Mixture vs Competing Risks
# ---------------------------------------------------------------------------

def run_experiment_3(df_sample: pd.DataFrame) -> list[dict]:
    """Сложные модели провала: Weibull Mixture vs Competing Risks."""
    print("\n[4/5] Эксперимент 3: Mixture vs Competing Risks...")

    failures = df_sample[df_sample["exit_group"].isin(["failed", "limit_hit"])]["n_chars"].values
    censored_arr = df_sample[df_sample["exit_group"] == "success"]["n_chars"].values
    print(f"      Failures (failed+limit_hit): {len(failures)}")
    print(f"      Right-Censored (success): {len(censored_arr)}")

    results = []

    # Модель A: Weibull Mixture
    print("      Fit_Weibull_Mixture...")
    t0 = time.time()
    try:
        wm = Fit_Weibull_Mixture(
            failures=failures,
            right_censored=censored_arr,
            print_results=False,
            show_probability_plot=True,
            optimizer="best",
        )
        fig = plt.gcf()
        fig.savefig(PLOTS_DIR / "TZ_6_exp3_mixture_prob.png", dpi=140)
        plt.close(fig)
        print(f"      → сохранено: TZ_6_exp3_mixture_prob.png ({time.time()-t0:.1f}s)")
        print(f"      BIC={wm.BIC:.2f}, proportion_1={wm.proportion_1:.3f}")

        wm_params = {
            "alpha_1": float(wm.alpha_1),
            "beta_1": float(wm.beta_1),
            "alpha_2": float(wm.alpha_2),
            "beta_2": float(wm.beta_2),
            "proportion_1": float(wm.proportion_1),
            "BIC": float(wm.BIC),
        }
    except Exception as e:
        print(f"      ⚠ Weibull Mixture не удался: {e}")
        wm_params = {k: None for k in
                     ["alpha_1", "beta_1", "alpha_2", "beta_2", "proportion_1", "BIC"]}

    results.append({"experiment": "exp3_mixture", **wm_params})

    # Модель B: Competing Risks
    print("      Fit_Weibull_CR...")
    t0 = time.time()
    try:
        cr = Fit_Weibull_CR(
            failures=failures,
            right_censored=censored_arr,
            print_results=False,
            show_probability_plot=True,
            optimizer="best",
        )
        fig = plt.gcf()
        fig.savefig(PLOTS_DIR / "TZ_6_exp3_competing_risks_prob.png", dpi=140)
        plt.close(fig)
        print(f"      → сохранено: TZ_6_exp3_competing_risks_prob.png ({time.time()-t0:.1f}s)")
        print(f"      BIC={cr.BIC:.2f}")

        cr_params = {
            "alpha_1": float(cr.alpha_1),
            "beta_1": float(cr.beta_1),
            "alpha_2": float(cr.alpha_2),
            "beta_2": float(cr.beta_2),
            "BIC": float(cr.BIC),
        }
    except Exception as e:
        print(f"      ⚠ Weibull CR не удался: {e}")
        cr_params = {k: None for k in ["alpha_1", "beta_1", "alpha_2", "beta_2", "BIC"]}

    results.append({"experiment": "exp3_competing_risks", **cr_params})

    # Итоговый вывод
    winner = "mixture" if wm_params["BIC"] < cr_params["BIC"] else "competing_risks"
    winner_bic = wm_params["BIC"] if winner == "mixture" else cr_params["BIC"]
    print(f"\n      ✓ Победитель: {winner} (BIC={winner_bic:.2f})")

    return results


# ---------------------------------------------------------------------------
# Задача 5: Сохранение параметров
# ---------------------------------------------------------------------------

def save_params(all_results: list[dict]) -> None:
    """Сохраняет все параметры фитов в CSV."""
    rows = []
    for r in all_results:
        row = {}
        for k, v in r.items():
            if v is None:
                row[k] = ""
            elif isinstance(v, float) and np.isnan(v):
                row[k] = ""
            else:
                row[k] = v
        rows.append(row)

    df_out = pd.DataFrame(rows)
    df_out.to_csv(PARAMS_CSV, index=False)
    print(f"\n[5/5] Параметры сохранены: {PARAMS_CSV}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    t0 = time.time()
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Задача 1
    df_sample, df_err_sample = load_and_sample()

    # Задача 2
    all_results = [run_experiment_1(df_sample)]

    # Задача 3
    all_results += run_experiment_2(df_sample, df_err_sample)

    # Задача 4
    all_results += run_experiment_3(df_sample)

    # Задача 5
    save_params(all_results)

    print(f"\n{'='*60}")
    print(f"TZ_6 завершён за {time.time()-t0:.1f}s")
    print(f"  Графики: {PLOTS_DIR}/TZ_6_exp*.png")
    print(f"  Параметры: {PARAMS_CSV}")
    print(f"  Отчёт: work/reports/TZ_6_survival_analysis_report.md (вписать вручную)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()