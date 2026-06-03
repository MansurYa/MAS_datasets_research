"""Function 2: validate — проверка согласия данных с распределением.

Реализация согласно МЕТОДОЛОГИЯ-2.0, секции 4.3, 5.6–5.11.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
from scipy import stats

from distribution_validator.bootstrap import (
    meinshausen_correction,
    multi_split_K100,
    parametric_bootstrap,
    skewness_bootstrap,
)
from distribution_validator.diagnostics import (
    TOSTDiagnostics,
    bootstrap_ci_tost,
    compute_sup_distance_KM,
    tost_check,
)
from distribution_validator.distributions import (
    DistParams,
    DistType,
    custom_loglogistic,
    custom_loglogistic_3p,
    get_dist_instance,
    mle_2p,
    support_lower,
)
from distribution_validator.ecdf import ecdf_full, ecdf_censored
from distribution_validator.goodness import kolmogorov_pvalue, ks_distance
from distribution_validator.profile_mle import profile_mle_3p

logger = logging.getLogger(__name__)

# Вердикты
VERDICT_ACCEPT = "ACCEPT"
VERDICT_REJECT = "REJECT"
VERDICT_ACCEPT_EQUIVALENCE = "ACCEPT_EQUIVALENCE"
VERDICT_REJECT_EQUIVALENCE = "REJECT_EQUIVALENCE"
VERDICT_UNDERPOWERED = "UNDERPOWERED"


@dataclass
class ValidationResult:
    """Результат validate()."""

    verdict: str
    dist_type: DistType
    n_fit: int
    n_test: int
    branch: str  # "A_BOOTSTRAP" / "B_SPLIT" / "C_TOST"
    D_obs: float
    p_value: Optional[float] = None
    p_final: Optional[float] = None
    p_LRT: Optional[float] = None
    skewness: Optional[float] = None
    parameters: dict = field(default_factory=dict)
    status_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    event_mask_provided: bool = False
    censorship_detected: bool = False
    trained_on_same: bool = False
    computation_time_s: float = 0.0


def _jitter_X(
    X: np.ndarray,
    dist_type: DistType,
    gamma: float = 0.0,
    seed: Optional[int] = None,
) -> np.ndarray:
    """Jittering с защитой области определения (секция 5.6).

    δ = max(10^-4 * mean(X), 1e-10)
    X_j = max(support_lower + δ, X + U(-δ, +δ))

    Args:
        X: входные данные.
        dist_type: тип распределения.
        gamma: параметр сдвига.

    Returns:
        Джиттеренный массив.
    """
    delta = max(1e-4 * np.mean(np.abs(X)), 1e-10)
    support_lower_bound = support_lower(dist_type, gamma)
    rng = np.random.default_rng(seed)

    if np.isinf(support_lower_bound):
        jittered = X + rng.uniform(-delta, delta, size=X.shape)
    else:
        noise = rng.uniform(-delta, delta, size=X.shape)
        jittered = X + noise
        jittered = np.maximum(support_lower_bound + delta, jittered)

    return jittered


def _get_frozen_dist(
    dist_type: DistType,
    params: DistParams,
    is_3p: bool,
) -> object:
    """Создать замороженное распределение.

    Args:
        dist_type: тип распределения.
        params: параметры.
        is_3p: True если 3P.

    Returns:
        Объект с методами .cdf(), .ppf(), .rvs().
    """
    if dist_type in ("W2",):
        return stats.weibull_min(c=params.beta, scale=params.alpha)
    elif dist_type in ("W3",):
        return stats.weibull_min(c=params.beta, scale=params.alpha, loc=params.gamma)
    elif dist_type in ("LN2",):
        return stats.lognorm(s=params.sigma, scale=np.exp(params.mu))
    elif dist_type == "N":
        return stats.norm(loc=params.mu, scale=params.sigma)
    elif dist_type == "G2":
        return stats.gamma(a=params.k, scale=params.theta)
    elif dist_type == "GU":
        return stats.gumbel_r(loc=params.mu, scale=params.beta)
    elif dist_type == "E1":
        return stats.expon(scale=1 / params.lam)
    elif dist_type == "E2":
        return stats.expon(scale=1 / params.lam, loc=params.gamma)
    elif dist_type in ("LL2",):
        return custom_loglogistic(alpha=params.alpha, beta=params.beta)
    elif dist_type in ("LL3",):
        return custom_loglogistic_3p(alpha=params.alpha, beta=params.beta, gamma=params.gamma)
    else:
        raise ValueError(f"Unsupported dist_type: {dist_type}")


def validate(
    X_test: np.ndarray,
    F_frozen: object,
    trained_on_same: bool,
    N_max: int,
    event_mask: Optional[np.ndarray] = None,
    epsilon: float = 0.03,
    alpha: float = 0.05,
    dist_type: Optional[DistType] = None,
    params: Optional[DistParams] = None,
    gamma: float = 0.0,
    is_3p: bool = False,
    B: int = 10000,
    seed: int = 42,
) -> ValidationResult:
    """Function 2: Проверка согласия данных с теоретическим распределением.

    Внутреннее ветвление:
    event_mask → Branch C (TOST)
    trained_on_same=True → Branch A (Param Bootstrap)
    trained_on_same=False, N_test ≤ N_max/2 → Branch B (Multi-split)
    trained_on_same=False, N_test > N_max/2 → Branch C (TOST)

    Args:
        X_test: тестовые данные.
        F_frozen: замороженное распределение.
        trained_on_same: параметры оценены по X_test.
        N_max: верхний барьер (из Function 1).
        event_mask: None или массив 0/1 (1 = событие).
        epsilon: инженерный допуск.
        alpha: уровень значимости.
        dist_type: тип распределения.
        params: параметры.
        gamma: параметр сдвига.
        is_3p: True если 3P.
        B: число бутстреп-итераций.
        seed: random seed.

    Returns:
        ValidationResult.
    """
    import time
    t0 = time.time()

    X_test = np.asarray(X_test).flatten()
    X_test = X_test[~np.isnan(X_test)]
    n_test = len(X_test)

    # Jittering
    X_j = _jitter_X(X_test, dist_type or "W2", gamma, seed=seed)

    result = ValidationResult(
        verdict="",
        dist_type=dist_type or "W2",
        n_fit=0,
        n_test=n_test,
        branch="UNKNOWN",
        D_obs=0.0,
        event_mask_provided=event_mask is not None,
    )

    if params:
        result.parameters = {
            k: v for k, v in {
                "alpha": params.alpha,
                "beta": params.beta,
                "gamma": params.gamma,
                "mu": params.mu,
                "sigma": params.sigma,
                "lam": params.lam,
                "k": params.k,
                "theta": params.theta,
            }.items() if v is not None
        }

    # === Определяем ветвь ===
    censored = False
    if event_mask is not None:
        event_mask = np.asarray(event_mask).flatten()
        if not np.all(np.isin(event_mask, [0, 1])):
            raise ValueError("event_mask должен содержать только 0 и 1")
        censored = np.any(event_mask == 0)
        result.censorship_detected = censored
        branch = "C_TOST"
    elif trained_on_same:
        branch = "A_BOOTSTRAP"
    elif n_test <= N_max / 2:
        branch = "B_SPLIT"
    else:
        branch = "C_TOST"

    result.branch = branch
    result.trained_on_same = trained_on_same

    # === D_obs ===
    if censored:
        D_obs = compute_sup_distance_KM(X_test, event_mask, F_frozen.cdf)
    else:
        D_obs = ks_distance(np.sort(X_j), F_frozen.cdf)

    result.D_obs = D_obs

    # === Branch A: Complex Hypothesis ===
    if branch == "A_BOOTSTRAP":
        logger.info(f"Branch A: Parametric Bootstrap, B={B}")
        D_obs_b, p_value, D_boot = parametric_bootstrap(
            X_j, F_frozen, params or DistParams(), gamma,
            dist_type or "W2", B=B, seed=seed,
        )
        result.D_obs = D_obs_b
        result.p_value = p_value

        # Skewness
        skew = skewness_bootstrap(D_boot)
        result.skewness = skew
        if abs(skew) > 0.5:
            result.warnings.append(
                f"Bootstrap distribution skewed (skewness={skew:.3f}). "
                "Consider TOST as alternative."
            )

        # Вердикт
        if p_value >= alpha:
            result.verdict = VERDICT_ACCEPT
        else:
            result.verdict = VERDICT_REJECT

    # === Branch B: Simple Hypothesis ===
    elif branch == "B_SPLIT":
        logger.info("Branch B: Multi-split K=100")
        D_median, p_final, p_values = multi_split_K100(
            X_j, F_frozen, dist_type or "W2",
            params or DistParams(), K=100, seed=seed,
        )
        result.D_obs = D_median
        result.p_final = p_final

        # Meinshausen correction
        if p_final >= alpha:
            result.verdict = VERDICT_ACCEPT
        else:
            result.verdict = VERDICT_REJECT

    # === Branch C: TOST ===
    elif branch == "C_TOST":
        logger.info("Branch C: TOST (Bootstrap CI Equivalence)")

        D_real, D_low, D_up = bootstrap_ci_tost(
            X_j, F_frozen, B=min(B, 5000), seed=seed,
            censored=censored, event=event_mask,
        )

        result.D_obs = D_real
        verdict, recommendation = tost_check(D_up, epsilon, D_real)
        result.verdict = verdict

        if verdict == VERDICT_ACCEPT_EQUIVALENCE:
            result.warnings.append(
                f"ACCEPT_EQUIVALENCE: D_up={D_up:.4f} ≤ ε={epsilon:.3f}"
            )
        else:
            result.warnings.append(
                f"REJECT_EQUIVALENCE: D_up={D_up:.4f} > ε={epsilon:.3f}. "
                + recommendation
            )

    result.computation_time_s = time.time() - t0
    return result