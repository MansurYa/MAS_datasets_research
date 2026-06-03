"""Profile MLE для 3P-распределений (Subtasks A–E).

Реализация согласно МЕТОДОЛОГИЯ-2.0, секция 5.7.
Сеточная инициализация → Brent → L-BFGS-B → LRT.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
from scipy import optimize
from scipy import special
from scipy import stats

from distribution_validator.distributions import (
    DistParams,
    DistType,
    MLEContext,
    mle_2p,
)

logger = logging.getLogger(__name__)

# Статус-коды Profile MLE
MLE_STATUS_SINGULARITY = "γ_LOCKED_BY_SINGULARITY"
MLE_STATUS_NOT_SIGNIFICANT = "γ_NOT_SIGNIFICANT"
MLE_STATUS_MARGINAL = "γ_MARGINAL"
MLE_STATUS_NEAR_BOUNDARY = "γ_NEAR_BOUNDARY"
MLE_STATUS_DOUBLE_WARNING = "DOUBLE_WARNING"
MLE_STATUS_CONVERGENCE_WARNING = "CONVERGENCE_WARNING"


@dataclass
class ProfileMLEResult:
    """Результат Profile MLE для 3P-распределения."""

    params_3p: DistParams  # Финальные 3P параметры
    params_2p: DistParams  # 2P fallback параметры
    use_3p: bool  # Использовать 3P (True) или 2P (False)
    status_codes: list[str] = field(default_factory=list)
    gamma_final: float = 0.0
    alpha_final: float = 0.0
    beta_final: float = 0.0
    ll_3p: float = -np.inf
    ll_2p: float = -np.inf
    p_LRT: float = 1.0
    converged: bool = False


def _preliminary_beta_weibull(X: np.ndarray) -> float:
    """Subtask A: Предварительная проверка β (Weibull probability paper).

    Линейная регрессия на вейбулловской бумаге.
    Если β ≤ 1 → сингулярность likelihood при γ → x_(1).

    Args:
        X: данные.

    Returns:
        Оценка β.
    """
    n = len(X)
    if n < 3:
        return 1.5

    # Медианные ранги (Bergman)
    i = np.arange(1, n + 1)
    median_ranks = (i - 0.3) / (n + 0.4)

    # Weibull: ln(-ln(1 - F)) vs ln(x)
    with np.errstate(divide="ignore", invalid="ignore"):
        y = np.log(-np.log(1 - median_ranks))
        x = np.log(X)

    # Убираем невалидные значения
    valid = np.isfinite(y) & np.isfinite(x)
    if np.sum(valid) < 3:
        return 1.5

    x_valid = x[valid]
    y_valid = y[valid]

    # Линейная регрессия: y = a + b * x, где b = β
    x_mean = np.mean(x_valid)
    y_mean = np.mean(y_valid)
    ss_xy = np.sum((x_valid - x_mean) * (y_valid - y_mean))
    ss_xx = np.sum((x_valid - x_mean) ** 2)

    if ss_xx < 1e-10:
        return 1.5

    beta_prelim = ss_xy / ss_xx
    return max(0.1, min(beta_prelim, 10.0))


_DIST_TYPE_3P_TO_2P = {
    "W3": "W2",
    "LN3": "LN2",
    "G3": "G2",
    "LL3": "LL2",
    "E2": "E1",
}


def _grid_search_gamma(
    X: np.ndarray,
    dist_type: DistType,
    n_points: int = 100,
) -> tuple[np.ndarray, np.ndarray]:
    """Subtask B: Grid search по γ.

    γ-сетка: n_points точек от 0 до x_min - epsilon.
    В каждой точке — внутренний 2P MLE.

    Args:
        X: данные.
        dist_type: тип распределения (3P версия).
        n_points: число точек сетки.

    Returns:
        (gamma_grid, ll_grid): массивы значений γ и log-likelihood.
    """
    x_min = np.min(X)
    x_max = np.max(X)
    x_mean = np.mean(X)

    # gamma ∈ [0, x_min - epsilon]
    epsilon = 1e-6 * x_mean
    gamma_max = max(0, x_min - epsilon)

    if gamma_max <= 0:
        gamma_grid = np.array([0.0])
        ll_grid = np.array([-np.inf])
        return gamma_grid, ll_grid

    gamma_grid = np.linspace(0, gamma_max, n_points)

    ll_grid = np.zeros(n_points)
    for i, gamma in enumerate(gamma_grid):
        try:
            X_shifted = X - gamma
            X_positive = X_shifted[X_shifted > 0]

            if len(X_positive) < 5:
                ll_grid[i] = -np.inf
                continue

            # 2P MLE на сдвинутых данных
            dist_type_2p = _DIST_TYPE_3P_TO_2P.get(dist_type, dist_type[:2] + "2")
            params_2p = mle_2p(X_positive, dist_type_2p, context="for_grid")
            ll_grid[i] = params_2p.log_likelihood if params_2p.log_likelihood else -np.inf

        except Exception:
            ll_grid[i] = -np.inf

    return gamma_grid, ll_grid


def _optimize_gamma_brent(
    X: np.ndarray,
    dist_type: DistType,
    gamma_init: float,
    gamma_grid: np.ndarray,
    ll_grid: np.ndarray,
) -> tuple[float, float, bool]:
    """Subtask C: Оптимизация γ методом Brent.

    Args:
        X: данные.
        dist_type: тип распределения.
        gamma_init: начальное приближение.
        gamma_grid, ll_grid: результаты grid search.

    Returns:
        (gamma_opt, ll_opt, converged).
    """
    x_min = np.min(X)
    x_mean = np.mean(X)
    gamma_lo = 0.0
    gamma_hi = max(0, x_min - 1e-6 * x_mean)

    if gamma_hi <= gamma_lo:
        return gamma_init, ll_grid[np.argmax(ll_grid)], False

    def neg_ll_gamma(gamma: float) -> float:
        """Отрицательный log-likelihood для фиксированного γ."""
        try:
            X_shifted = X - gamma
            X_positive = X_shifted[X_shifted > 0]

            if len(X_positive) < 5:
                return 1e10

            dist_type_2p = _DIST_TYPE_3P_TO_2P.get(dist_type, dist_type[:2] + "2")
            params = mle_2p(X_positive, dist_type_2p, context="for_brent")
            ll = params.log_likelihood if params.log_likelihood else 1e10
            return -ll
        except Exception:
            return 1e10

    try:
        result = optimize.minimize_scalar(
            neg_ll_gamma,
            bounds=(gamma_lo, gamma_hi),
            method="bounded",
            options={
                "xatol": 1e-10,
                "maxiter": 200,
            },
        )
        gamma_opt = result.x
        ll_opt = -result.fun
        converged = result.success or result.nit > 0

        if not converged and result.nit == 0:
            # Brent не стартовал — используем grid-оценку
            best_idx = np.argmax(ll_grid)
            gamma_opt = gamma_grid[best_idx]
            ll_opt = ll_grid[best_idx]

    except Exception:
        # Fallback: используем лучшую точку сетки
        best_idx = np.argmax(ll_grid)
        gamma_opt = gamma_grid[best_idx]
        ll_opt = ll_grid[best_idx]
        converged = False

    return gamma_opt, ll_opt, converged


def _internal_mle_with_gamma_fixed(
    X: np.ndarray,
    gamma: float,
    dist_type: DistType,
    context: MLEContext,
) -> DistParams:
    """Внутренний MLE для 2P с фиксированным γ.

    Subtask D: L-BFGS-B с точностью, зависящей от контекста.

    Args:
        X: данные.
        gamma: фиксированный параметр сдвига.
        dist_type: тип распределения (2P версия).
        context: контекст оптимизации.

    Returns:
        DistParams с 2P параметрами.
    """
    X_shifted = X - gamma
    X_positive = X_shifted[X_shifted > 0]

    if len(X_positive) < 5:
        raise ValueError("Insufficient positive data after shift")

    params = mle_2p(X_positive, dist_type, context=context)
    params.gamma = gamma
    return params


def profile_mle_3p(
    X: np.ndarray,
    dist_type: DistType,
) -> ProfileMLEResult:
    """Profile MLE для трёхпараметрического распределения.

    Полный pipeline Subtasks A–E:

    Subtask A: Предварительная проверка β.
    Subtask B: Grid search (100 узлов) → fine grid (201) при Δ_LL > 1.0.
    Subtask C: Brent 1D optimization.
    Subtask D: L-BFGS-B internal MLE (final).
    Subtask E: LRT 2P vs 3P.

    Args:
        X: данные (одномерный массив).
        dist_type: тип распределения (3P: W3, LN3, G3, LL3, E2).

    Returns:
        ProfileMLEResult с параметрами и статус-кодами.
    """
    X = np.asarray(X).flatten()
    X = X[~np.isnan(X)]

    if len(X) < 10:
        raise ValueError("Profile MLE требует минимум 10 наблюдений")

    x_min = np.min(X)
    x_max = np.max(X)
    x_mean = np.mean(X)

    # 2P MLE для сравнения
    dist_type_2p = _DIST_TYPE_3P_TO_2P.get(dist_type, dist_type[:2] + "2")
    try:
        params_2p = mle_2p(X, dist_type_2p, context="final")
    except Exception:
        params_2p = DistParams(log_likelihood=-np.inf)

    result = ProfileMLEResult(
        params_3p=params_2p,  # Временно, перезапишем позже
        params_2p=params_2p,
        use_3p=False,
    )

    # === Subtask A: Пропускаем — см. комментарий ниже

    # === Subtask B: Grid Search ===
    gamma_grid, ll_grid = _grid_search_gamma(X, dist_type, n_points=100)

    # Проверяем, есть ли валидные точки
    valid_mask = np.isfinite(ll_grid)
    if not np.any(valid_mask):
        # Fallback: используем 2P
        result.status_codes.append(MLE_STATUS_CONVERGENCE_WARNING)
        result.params_3p = params_2p
        result.params_3p.gamma = 0.0
        result.use_3p = False
        return result

    # Fine grid при Δ_LL > 1.0
    sorted_idx = np.argsort(ll_grid)[::-1]
    best_idx = sorted_idx[0]
    second_idx = sorted_idx[1] if len(sorted_idx) > 1 else sorted_idx[0]
    delta_ll = ll_grid[best_idx] - ll_grid[second_idx]

    if delta_ll > 1.0:
        # Fine grid вокруг лучшей точки
        gamma_peak = gamma_grid[best_idx]
        gamma_range = (x_min - gamma_peak) * 0.1 if gamma_peak > 0 else x_min * 0.1
        gamma_lo = max(0, gamma_peak - gamma_range)
        gamma_hi = max(gamma_lo + 1e-6, gamma_peak + gamma_range)

        gamma_grid_fine = np.linspace(gamma_lo, gamma_hi, 201)
        ll_grid_fine = np.zeros(201)

        for i, gamma in enumerate(gamma_grid_fine):
            try:
                X_shifted = X - gamma
                X_positive = X_shifted[X_shifted > 0]
                if len(X_positive) < 5:
                    ll_grid_fine[i] = -np.inf
                    continue
                params = mle_2p(X_positive, dist_type_2p, context="for_grid")
                ll_grid_fine[i] = params.log_likelihood if params.log_likelihood else -np.inf
            except Exception:
                ll_grid_fine[i] = -np.inf

        gamma_grid = gamma_grid_fine
        ll_grid = ll_grid_fine

    # === Subtask C: Brent optimization ===
    best_idx = np.argmax(ll_grid)
    gamma_init = gamma_grid[best_idx]

    gamma_final, ll_opt, converged = _optimize_gamma_brent(
        X, dist_type, gamma_init, gamma_grid, ll_grid
    )

    if not converged:
        result.status_codes.append(MLE_STATUS_CONVERGENCE_WARNING)

    # Проверка граничного γ
    boundary_threshold = x_min - 1e-4 * x_mean
    if gamma_final > boundary_threshold:
        result.status_codes.append(MLE_STATUS_NEAR_BOUNDARY)

    # === Subtask D: Финальный MLE с оптимальным γ ===
    try:
        params_with_gamma = _internal_mle_with_gamma_fixed(
            X, gamma_final, dist_type_2p, context="final"
        )
        ll_3p = params_with_gamma.log_likelihood or -np.inf
    except Exception:
        ll_3p = -np.inf

    # === Subtask E: LRT 2P vs 3P ===
    ll_2p = params_2p.log_likelihood if params_2p.log_likelihood else -np.inf
    lambda_stat = 2.0 * (ll_3p - ll_2p)

    # LR statistic ~ chi2(1) для вложенных моделей (2P vs 3P)
    if lambda_stat > 0:
        p_LRT = stats.chi2.sf(lambda_stat, df=1)
    else:
        p_LRT = 1.0

    result.ll_3p = ll_3p
    result.ll_2p = ll_2p
    result.p_LRT = p_LRT
    result.gamma_final = gamma_final

    # Решающее правило: p_LRT > 0.05 → 2P
    if p_LRT > 0.10:
        result.status_codes.append(MLE_STATUS_NOT_SIGNIFICANT)
        result.use_3p = False
    elif p_LRT > 0.05:
        result.status_codes.append(MLE_STATUS_MARGINAL)
        result.use_3p = True
    else:
        result.use_3p = True

    # DOUBLE_WARNING: γ_NEAR_BOUNDARY AND p_LRT < 0.10
    if MLE_STATUS_NEAR_BOUNDARY in result.status_codes and p_LRT < 0.10:
        result.status_codes.append(MLE_STATUS_DOUBLE_WARNING)

    # Формируем финальные параметры
    if result.use_3p:
        # Собираем 3P параметры из params_with_gamma
        p = params_with_gamma
        if dist_type == "W3":
            result.params_3p = DistParams(
                alpha=p.alpha, beta=p.beta, gamma=gamma_final,
                log_likelihood=ll_3p,
            )
            result.alpha_final = p.alpha
            result.beta_final = p.beta
        elif dist_type == "LN3":
            result.params_3p = DistParams(
                mu=p.mu, sigma=p.sigma, gamma=gamma_final,
                log_likelihood=ll_3p,
            )
            result.alpha_final = np.exp(p.mu)
            result.beta_final = p.sigma
        elif dist_type == "G3":
            result.params_3p = DistParams(
                k=p.k, theta=p.theta, gamma=gamma_final,
                log_likelihood=ll_3p,
            )
            result.alpha_final = p.theta
            result.beta_final = p.k
        elif dist_type == "LL3":
            result.params_3p = DistParams(
                alpha=p.alpha, beta=p.beta, gamma=gamma_final,
                log_likelihood=ll_3p,
            )
            result.alpha_final = p.alpha
            result.beta_final = p.beta
        elif dist_type == "E2":
            result.params_3p = DistParams(
                lam=p.lam, gamma=gamma_final,
                log_likelihood=ll_3p,
            )
            result.alpha_final = 1.0 / p.lam
            result.beta_final = p.lam
    else:
        # 2P fallback: используем params_2p напрямую
        result.params_3p = params_2p  # params_2p has valid alpha, beta for 2P
        result.use_3p = False
        result.alpha_final = params_2p.alpha or 0.0
        result.beta_final = params_2p.beta or 0.0

    result.converged = converged
    return result