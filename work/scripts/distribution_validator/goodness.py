"""Статистические расстояния: KS-статистика и p-value.

Реализация согласно Буре, Парилина (2018), §2.2.2.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def ks_distance(
    X_sorted: np.ndarray,
    F0: callable,
) -> float:
    """Расстояние Колмогорова (практическая формула 2.2.2).

    D* = max(max|i/n - F0(x_i)|, max|F0(x_i) - (i-1)/n|)

    Args:
        X_sorted: отсортированные данные (x_{(1)} ≤ ... ≤ x_{(n)}).
        F0: теоретическая CDF (callable: x → F(x)).

    Returns:
        Значение статистики D*.
    """
    n = len(X_sorted)
    if n == 0:
        return 0.0

    # F0(x_i) для каждой точки
    F0_vals = F0(X_sorted)

    # D+ = max_i (i/n - F0(x_i))
    i_over_n = (np.arange(1, n + 1)) / n
    D_plus = np.max(i_over_n - F0_vals)

    # D- = max_i (F0(x_i) - (i-1)/n)
    i_minus_1_over_n = (np.arange(n)) / n
    D_minus = np.max(F0_vals - i_minus_1_over_n)

    return max(D_plus, D_minus)


def kolmogorov_pvalue(
    D: float,
    n: int,
    simple_hypothesis: bool = True,
) -> float:
    """P-value для статистики Колмогорова.

    Для простой гипотезы (параметры известны):
    P(D_n* ≤ x) → K(x) = 1 + 2Σ(-1)^m exp(-2m²x²)

    Для сложной гипотезы (параметры оценены по выборке):
    Используется приближение kstwobign (менее точное, но консервативное).

    Args:
        D: значение статистики D*.
        n: размер выборки.
        simple_hypothesis: True = параметры заданы априори.

    Returns:
        Односторонний p-value = P(D ≥ D_obs).
    """
    if n <= 0:
        return 1.0

    # kstwobign — предельное распределение для больших n
    # p-value = P(Kolmogorov distribution > D * sqrt(n))
    z = D * np.sqrt(n)
    return stats.kstwobign.sf(z)


def anderson_darling_distance(
    X_sorted: np.ndarray,
    F0: callable,
) -> float:
    """Расстояние Андерсона-Дарлинга (практическая формула 2.2.5).

    ω² = 1/(12n) + Σ(F0(x_i) - (2i-1)/(2n))²

    Args:
        X_sorted: отсортированные данные.
        F0: теоретическая CDF.

    Returns:
        Значение статистики ω².
    """
    n = len(X_sorted)
    if n == 0:
        return 0.0

    F0_vals = F0(X_sorted)
    # (2i-1)/(2n) для i=1..n
    i_minus_half = (2 * np.arange(1, n + 1) - 1) / (2 * n)
    diff = F0_vals - i_minus_half

    omega_sq = 1 / (12 * n) + np.sum(diff**2)
    return omega_sq


def cramervon_mises_distance(
    X_sorted: np.ndarray,
    F0: callable,
) -> float:
    """Расстояние Крамера — фон Мизеса.

    T = Σ (F0(x_i) - (i-0.5)/n)² + 1/(12n)

    Args:
        X_sorted: отсортированные данные.
        F0: теоретическая CDF.

    Returns:
        Значение статистики T.
    """
    n = len(X_sorted)
    if n == 0:
        return 0.0

    F0_vals = F0(X_sorted)
    i_half = (np.arange(n) + 0.5) / n
    diff = F0_vals - i_half

    T = np.sum(diff**2) + 1 / (12 * n)
    return T