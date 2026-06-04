"""Параметрический bootstrap и multi-split валидация.

Реализация согласно МЕТОДОЛОГИЯ-2.0, секции 5.8, 5.9.
"""
from __future__ import annotations

import logging
from typing import Optional

import numpy as np
from scipy import stats

from distribution_validator.distributions import (
    DistParams,
    DistType,
    THREE_TO_TWO_MAPPING,
    custom_loglogistic,
    custom_loglogistic_3p,
    get_dist_instance,
    mle_2p,
)

logger = logging.getLogger(__name__)


def generate_ppf_samples(
    F_frozen: object,
    n: int,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Генерация псевдовыборок через PPF (inverse CDF transform).

    КРИТИЧНО: НЕ использует scipy.stats.fit() в цикле.
    Это основное требование для производительности.

    Args:
        F_frozen: замороженное распределение с методами .ppf().
        n: размер выборки.
        seed: random seed.

    Returns:
        Массив из n псевдовыборок.
    """
    rng = np.random.default_rng(seed)
    u = rng.uniform(size=n)
    return F_frozen.ppf(u)


def parametric_bootstrap(
    X_test: np.ndarray,
    F_frozen: object,
    theta: DistParams,
    gamma: float,
    dist_type: DistType,
    B: int = 10000,
    seed: Optional[int] = None,
) -> tuple[float, float, np.ndarray]:
    """Параметрический bootstrap для сложной гипотезы (Ветвь A).

    Реализация:
    1. D_obs = sup|ECDF(X_j) - F_0|
    2. B итераций: генерация X* ~ F_0(theta), быстрый MLE, расчёт D*
    3. p-value = доля D* >= D_obs

    Args:
        X_test: тестовые данные (джиттеренные).
        F_frozen: замороженное распределение.
        theta: финальные параметры.
        gamma: параметр сдвига.
        dist_type: тип распределения.
        B: число бутстреп-итераций.
        seed: random seed.

    Returns:
        (D_obs, p_value, D_boot_array).
    """
    # D_obs
    X_sorted = np.sort(X_test)
    n = len(X_sorted)

    def F0(x):
        return F_frozen.cdf(x)

    i_over_n = (np.arange(1, n + 1)) / n
    F0_vals = F0(X_sorted)
    D_plus = np.max(i_over_n - F0_vals)
    D_minus = np.max(F0_vals - (np.arange(n)) / n)
    D_obs = max(D_plus, D_minus)

    # Bootstrap loop
    D_boot = np.zeros(B)
    rng = np.random.default_rng(seed)

    for b in range(B):
        # Генерация через PPF
        u = rng.uniform(size=n)
        X_star = F_frozen.ppf(u)

        try:
            # Быстрый MLE с γ фиксированным
            X_star_shifted = X_star - gamma
            X_star_positive = X_star_shifted[X_star_shifted > 0]

            if len(X_star_positive) < 10:
                D_boot[b] = 0.0
                continue

            # Определяем 2P-тип для MLE (3P → соответствующий 2P)
            dist_2p = THREE_TO_TWO_MAPPING.get(dist_type, dist_type)
            params_star = mle_2p(X_star_positive, dist_2p, context="for_grid")
            params_star.gamma = gamma

            # Создаём распределение для X_star
            if dist_type in ("W2", "W3"):
                F_star = stats.weibull_min(c=params_star.beta, scale=params_star.alpha, loc=gamma)
            elif dist_type in ("LN2", "LN3"):
                F_star = stats.lognorm(s=params_star.sigma, scale=np.exp(params_star.mu), loc=gamma)
            elif dist_type in ("G2", "G3"):
                F_star = stats.gamma(a=params_star.k, scale=params_star.theta, loc=gamma)
            elif dist_type == "N":
                F_star = stats.norm(loc=params_star.mu, scale=params_star.sigma)
            elif dist_type == "GU":
                F_star = stats.gumbel_r(loc=params_star.mu, scale=params_star.beta)
            elif dist_type in ("E1", "E2"):
                F_star = stats.expon(scale=1 / params_star.lam, loc=gamma)
            elif dist_type in ("LL2", "LL3"):
                ll = custom_loglogistic_3p(alpha=params_star.alpha, beta=params_star.beta, gamma=gamma)
                X_star_sorted = np.sort(X_star)
                F0_star_vals = ll.cdf(X_star_sorted)
                D_plus_star = np.max((np.arange(1, n + 1)) / n - F0_star_vals)
                D_minus_star = np.max(F0_star_vals - (np.arange(n)) / n)
                D_boot[b] = max(D_plus_star, D_minus_star)
                continue
            else:
                D_boot[b] = 0.0
                continue

            # D* для X_star
            X_star_sorted = np.sort(X_star)
            F0_star_vals = F_star.cdf(X_star_sorted)
            D_plus_star = np.max((np.arange(1, n + 1)) / n - F0_star_vals)
            D_minus_star = np.max(F0_star_vals - (np.arange(n)) / n)
            D_boot[b] = max(D_plus_star, D_minus_star)

        except Exception:
            D_boot[b] = 0.0

    # p-value
    p_value = np.mean(D_boot >= D_obs)

    return D_obs, p_value, D_boot


def multi_split_K100(
    X: np.ndarray,
    F_frozen: object,
    dist_type: DistType,
    theta: DistParams,
    K: int = 100,
    seed: int = 42,
) -> tuple[float, float, list[float]]:
    """Multi-split валидация (Ветвь B).

    K=100 независимых сплитов 50/50.
    p_k = 1 - K(D_k * sqrt(N_test/2))
    p_final = min(1, 2 * median(p_1..p_K)) — Meinshausen correction

    Args:
        X: тестовые данные.
        F_frozen: замороженное распределение.
        dist_type: тип распределения.
        theta: параметры.
        K: число сплитов.
        seed: random seed.

    Returns:
        (D_median, p_final, p_values).
    """
    n = len(X)
    n_split = n // 2

    D_values = []
    p_values = []

    rng = np.random.default_rng(seed)

    for k in range(K):
        # Сплит
        indices = rng.permutation(n)
        idx_fit = indices[:n_split]
        idx_test = indices[n_split:]

        X_fit = X[idx_fit]
        X_test_split = X[idx_test]

        try:
            # MLE на fit-части
            dist_2p = THREE_TO_TWO_MAPPING.get(dist_type, dist_type)
            params_k = mle_2p(X_fit, dist_2p, context="final")

            # Создаём распределение
            if dist_type in ("W2", "W3"):
                F_k = stats.weibull_min(c=params_k.beta, scale=params_k.alpha, loc=params_k.gamma or 0.0)
            elif dist_type in ("LN2", "LN3"):
                F_k = stats.lognorm(s=params_k.sigma, scale=np.exp(params_k.mu), loc=params_k.gamma or 0.0)
            elif dist_type in ("G2", "G3"):
                F_k = stats.gamma(a=params_k.k, scale=params_k.theta, loc=params_k.gamma or 0.0)
            elif dist_type == "N":
                F_k = stats.norm(loc=params_k.mu, scale=params_k.sigma)
            elif dist_type == "GU":
                F_k = stats.gumbel_r(loc=params_k.mu, scale=params_k.beta)
            elif dist_type in ("E1", "E2"):
                F_k = stats.expon(scale=1 / params_k.lam, loc=params_k.gamma or 0.0)
            elif dist_type in ("LL2", "LL3"):
                F_k = custom_loglogistic_3p(alpha=params_k.alpha, beta=params_k.beta, gamma=params_k.gamma or 0.0)
            else:
                continue

            # D_k
            X_test_sorted = np.sort(X_test_split)
            F0_k_vals = F_k.cdf(X_test_sorted)
            n_k = len(X_test_sorted)

            D_plus_k = np.max((np.arange(1, n_k + 1)) / n_k - F0_k_vals)
            D_minus_k = np.max(F0_k_vals - (np.arange(n_k)) / n_k)
            D_k = max(D_plus_k, D_minus_k)

            D_values.append(D_k)

            # p_k для простой гипотезы
            z = D_k * np.sqrt(n_k)
            p_k = stats.kstwobign.sf(z)
            p_values.append(p_k)

        except Exception:
            continue

    if len(p_values) == 0:
        return 0.0, 1.0, []

    D_median = float(np.median(D_values))
    p_final = meinshausen_correction(p_values)

    return D_median, p_final, p_values


def meinshausen_correction(p_values: list[float]) -> float:
    """Коррекция Мейнсхаузена (Meinshausen & Bühlmann, 2009).

    p_final = min(1, 2 * median(p))

    Это поправка Бонферрони для порядковых статистик.
    Медиана — это ⌈K/2⌉-я порядковая статистика.
    При K=100 медиана — 50-я.
    Поправка Бонферрони для 50-й статистики: 2 * median(p).

    Args:
        p_values: список p-values от K сплитов.

    Returns:
        Скорректированный p-value.
    """
    if len(p_values) == 0:
        return 1.0

    median_p = np.median(p_values)
    return min(1.0, 2.0 * median_p)


def skewness_bootstrap(D_boot: np.ndarray) -> float:
    """Перцентильная асимметрия бутстреп-распределения.

    skew = (Q_75 + Q_25 - 2*Q_50) / (Q_75 - Q_25 + 1e-10)

    Порог |skew| > 0.5 → предупреждение.

    Args:
        D_boot: массив бутстреп-статистик D*.

    Returns:
        Значение асимметрии.
    """
    Q_25 = np.percentile(D_boot, 25)
    Q_50 = np.percentile(D_boot, 50)
    Q_75 = np.percentile(D_boot, 75)

    skew = (Q_75 + Q_25 - 2 * Q_50) / (Q_75 - Q_25 + 1e-10)
    return skew