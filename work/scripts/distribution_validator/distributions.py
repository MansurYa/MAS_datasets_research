"""12 распределений для distribution_validator.

10 распределений — scipy.stats wrappers.
2 распределения (Loglogistic 2P/3P) — реализованы вручную.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
from scipy import optimize
from scipy import special
from scipy import stats

# Типы распределений
DistType = Literal[
    "W2", "W3", "LN2", "LN3", "G2", "G3",
    "LL2", "LL3", "N", "GU", "E1", "E2",
]

# Контексты для MLE (，影响 точности)
MLEContext = Literal["for_grid", "for_brent", "final"]

# Маппинг 3P → 2P для MLE (используется в bootstrap.py и multi_split)
THREE_TO_TWO_MAPPING: dict[DistType, DistType] = {
    "W3": "W2",
    "LN3": "LN2",
    "G3": "G2",
    "LL3": "LL2",
    "E2": "E1",
}


@dataclass
class DistParams:
    """Параметры распределения."""

    alpha: Optional[float] = None  # scale для Weibull/LL, μ для LN
    beta: Optional[float] = None  # shape для Weibull/LL/LN, σ для LN
    gamma: Optional[float] = None  # threshold/location shift
    mu: Optional[float] = None  # mean для Normal/Gumbel
    sigma: Optional[float] = None  # std для Normal
    lam: Optional[float] = None  # rate для Exponential
    k: Optional[float] = None  # shape для Gamma
    theta: Optional[float] = None  # scale для Gamma
    median: Optional[float] = None  # для Gumbel
    log_likelihood: Optional[float] = None


def get_dist_instance(
    dist_type: DistType,
    params: DistParams,
) -> stats.rv_continuous:
    """Создать экземпляр распределения scipy с заданными параметрами.

    Args:
        dist_type: тип распределения.
        params: параметры (должны соответствовать типу).

    Returns:
        Замороженное распределение.
    """
    if dist_type == "W2":
        return stats.weibull_min(c=params.beta, scale=params.alpha)
    elif dist_type == "W3":
        return stats.weibull_min(c=params.beta, scale=params.alpha, loc=params.gamma)
    elif dist_type == "LN2":
        return stats.lognorm(s=params.sigma, scale=np.exp(params.mu))
    elif dist_type == "LN3":
        # Lognormal 3P: сдвиг applied to data before transformation
        def _ln3_cdf(x):
            z = (x - params.gamma) / np.exp(params.mu)
            return stats.lognorm(s=params.sigma).cdf(z)
        return _ln3_cdf
    elif dist_type == "G2":
        return stats.gamma(a=params.k, scale=params.theta)
    elif dist_type == "G3":
        def _g3_cdf(x):
            z = (x - params.gamma) / params.theta
            return stats.gamma(a=params.k).cdf(z)
        return _g3_cdf
    elif dist_type == "LL2":
        return custom_loglogistic(alpha=params.alpha, beta=params.beta)
    elif dist_type == "LL3":
        return custom_loglogistic_3p(alpha=params.alpha, beta=params.beta, gamma=params.gamma)
    elif dist_type == "N":
        return stats.norm(loc=params.mu, scale=params.sigma)
    elif dist_type == "GU":
        return stats.gumbel_r(loc=params.mu, scale=params.beta)
    elif dist_type == "E1":
        return stats.expon(scale=1 / params.lam)
    elif dist_type == "E2":
        return stats.expon(scale=1 / params.lam, loc=params.gamma)
    else:
        raise ValueError(f"Unknown dist_type: {dist_type}")


class custom_loglogistic:
    """Loglogistic 2P: CDF = 1 / (1 + (x/α)^(-β)).

    Реализовано вручную, т.к. scipy не имеет loglogistic.
    """

    def __init__(self, alpha: float, beta: float):
        self.alpha = alpha
        self.beta = beta

    def cdf(self, x: np.ndarray) -> np.ndarray:
        z = x / self.alpha
        return 1.0 / (1.0 + z ** (-self.beta))

    def ppf(self, u: np.ndarray) -> np.ndarray:
        # CDF: F(x) = 1 / (1 + (x/α)^(-β))
        # PPF: x = α * (u / (1-u))^(1/β)
        eps = 1e-10
        u = np.clip(u, eps, 1.0 - eps)
        return self.alpha * (u / (1.0 - u)) ** (1.0 / self.beta)

    def rvs(self, size: Optional[int] = None, seed: Optional[int] = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        u = rng.uniform(size=size)
        return self.ppf(u)

    def pdf(self, x: np.ndarray) -> np.ndarray:
        z = x / self.alpha
        return (self.beta / self.alpha) * z ** (self.beta - 1) / (1 + z ** self.beta) ** 2

    def logcdf(self, x: np.ndarray) -> np.ndarray:
        return np.log(self.cdf(x))

    def logpdf(self, x: np.ndarray) -> np.ndarray:
        return np.log(self.pdf(x))


class custom_loglogistic_3p:
    """Loglogistic 3P: CDF = 1 / (1 + ((x-γ)/α)^(-β)), x >= γ."""

    def __init__(self, alpha: float, beta: float, gamma: float):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def cdf(self, x: np.ndarray) -> np.ndarray:
        z = (x - self.gamma) / self.alpha
        return 1.0 / (1.0 + z ** (-self.beta))

    def ppf(self, u: np.ndarray) -> np.ndarray:
        # CDF: F(x) = 1 / (1 + ((x-γ)/α)^(-β))
        # PPF: x = γ + α * (u / (1-u))^(1/β)
        eps = 1e-10
        u = np.clip(u, eps, 1.0 - eps)
        return self.gamma + self.alpha * (u / (1.0 - u)) ** (1.0 / self.beta)

    def rvs(self, size: Optional[int] = None, seed: Optional[int] = None) -> np.ndarray:
        rng = np.random.default_rng(seed)
        u = rng.uniform(size=size)
        return self.ppf(u)

    def pdf(self, x: np.ndarray) -> np.ndarray:
        z = (x - self.gamma) / self.alpha
        return (self.beta / self.alpha) * z ** (self.beta - 1) / (1 + z ** self.beta) ** 2


def _neg_log_likelihood_weibull_2p(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Weibull 2P.

    scipy.stats.weibull_min(c=β, scale=α):
    CDF = 1 - exp(-(x/α)^β)
    log_pdf = log(β) - β*log(α) + (β-1)*log(x) - (x/α)^β
    """
    alpha, beta = params
    if alpha <= 0 or beta <= 0:
        return 1e10
    log_alpha = np.log(alpha)
    log_X = np.log(X)
    z = X / alpha
    ll = np.sum(
        np.log(beta) - beta * log_alpha + (beta - 1) * log_X - z**beta
    )
    return -ll


def _neg_log_likelihood_lognorm_2p(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Lognormal 2P."""
    mu, sigma = params
    if sigma <= 0:
        return 1e10
    ll = np.sum(stats.norm.logpdf(np.log(X), loc=mu, scale=sigma))
    return -ll


def _neg_log_likelihood_gamma_2p(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Gamma 2P."""
    k, theta = params
    if k <= 0 or theta <= 0:
        return 1e10
    ll = np.sum(stats.gamma.logpdf(X, a=k, scale=theta))
    return -ll


def _neg_log_likelihood_normal(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Normal 2P."""
    mu, sigma = params
    if sigma <= 0:
        return 1e10
    ll = np.sum(stats.norm.logpdf(X, loc=mu, scale=sigma))
    return -ll


def _neg_log_likelihood_gumbel(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Gumbel 2P."""
    mu, beta = params
    if beta <= 0:
        return 1e10
    ll = np.sum(stats.gumbel_r.logpdf(X, loc=mu, scale=beta))
    return -ll


def _neg_log_likelihood_expon_1p(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Exponential 1P."""
    lam, = params
    if lam <= 0:
        return 1e10
    ll = np.sum(stats.expon(scale=1/lam).logpdf(X))
    return -ll


def _neg_log_likelihood_expon_2p(params: np.ndarray, X: np.ndarray, x_min: float) -> float:
    """Отрицательный лог-L для Exponential 2P с фиксированным γ."""
    lam, = params
    if lam <= 0:
        return 1e10
    # Shift: работаем с (X - gamma)
    gamma = x_min  # gamma фиксирован
    X_shifted = X - gamma
    if np.any(X_shifted <= 0):
        return 1e10
    ll = np.sum(stats.expon(scale=1/lam).logpdf(X_shifted))
    return -ll


def _neg_log_likelihood_loglogistic_2p(params: np.ndarray, X: np.ndarray) -> float:
    """Отрицательный лог-L для Loglogistic 2P."""
    alpha, beta = params
    if alpha <= 0 or beta <= 0:
        return 1e10
    z = X / alpha
    # log-CDF и log-Survival
    log_cdf = -np.log1p(z**(-beta))
    log_survival = -np.log1p(z**beta)
    # PDF: beta/alpha * z^(beta-1) / (1 + z^beta)^2
    log_pdf = np.log(beta) - np.log(alpha) + (beta - 1) * np.log(z) - 2 * np.log1p(z**beta)
    ll = np.sum(log_pdf)
    return -ll


def mle_2p(
    X: np.ndarray,
    dist_type: DistType,
    context: MLEContext = "final",
    gamma_fixed: Optional[float] = None,
) -> DistParams:
    """MLE-оценка параметров 2P-распределения.

    Args:
        X: данные (одномерный массив, >= 0 для most distributions).
        dist_type: тип распределения.
        context: контекст оптимизации (affects tolerance).
        gamma_fixed: для 2P с опциональным сдвигом — зафиксированный γ.

    Returns:
        DistParams с оценёнными параметрами и log_likelihood.
    """
    X = np.asarray(X).flatten()
    X = X[~np.isnan(X)]

    # Начальное приближение (method of moments)
    n = len(X)
    x_mean = np.mean(X)
    x_std = np.std(X, ddof=1)
    x_min = np.min(X)

    # Параметры tolerance в зависимости от контекста
    if context == "for_grid":
        gtol, max_iter = 1e-6, 50
    elif context == "for_brent":
        gtol, max_iter = 1e-8, 100
    else:  # final
        gtol, max_iter = 1e-9, 200

    options = {"maxiter": max_iter}

    if dist_type == "W2":
        # Weibull 2P: α, β
        beta0 = 1.5 if x_mean == 0 else np.log(x_mean) / np.log(
            (x_mean**2 + x_std**2) / x_mean**2
        )
        beta0 = max(0.1, min(beta0, 10))
        alpha0 = max(x_mean / special.gamma(1 + 1/beta0), 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_weibull_2p(p, X)

        res = optimize.minimize(
            neg_ll, [alpha0, beta0], method="L-BFGS-B",
            bounds=[(1e-10, None), (1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            alpha=res.x[0], beta=res.x[1],
            log_likelihood=-res.fun,
        )

    elif dist_type == "LN2":
        # Lognormal 2P: μ, σ
        ln_X = np.log(X)
        mu0 = float(np.mean(ln_X))
        sigma0 = max(float(np.std(ln_X, ddof=1)), 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_lognorm_2p(p, X)

        res = optimize.minimize(
            neg_ll, [mu0, sigma0], method="L-BFGS-B",
            bounds=[(None, None), (1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            mu=res.x[0], sigma=res.x[1],
            log_likelihood=-res.fun,
        )

    elif dist_type == "G2":
        # Gamma 2P: k, θ
        k0 = max(x_mean**2 / (x_std**2 + 1e-10), 0.01)
        theta0 = max(x_std**2 / (x_mean + 1e-10), 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_gamma_2p(p, X)

        res = optimize.minimize(
            neg_ll, [k0, theta0], method="L-BFGS-B",
            bounds=[(1e-10, None), (1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            k=res.x[0], theta=res.x[1],
            log_likelihood=-res.fun,
        )

    elif dist_type == "N":
        # Normal 2P: μ, σ
        mu0, sigma0 = x_mean, max(x_std, 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_normal(p, X)

        res = optimize.minimize(
            neg_ll, [mu0, sigma0], method="L-BFGS-B",
            bounds=[(None, None), (1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            mu=res.x[0], sigma=res.x[1],
            log_likelihood=-res.fun,
        )

    elif dist_type == "GU":
        # Gumbel 2P: μ, β
        # Приближение: μ ≈ mean - 0.45*std, β ≈ std / 1.282
        mu0 = x_mean - 0.45 * x_std
        beta0 = max(x_std / 1.282, 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_gumbel(p, X)

        res = optimize.minimize(
            neg_ll, [mu0, beta0], method="L-BFGS-B",
            bounds=[(None, None), (1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            mu=res.x[0], beta=res.x[1],
            log_likelihood=-res.fun,
        )

    elif dist_type == "E1":
        # Exponential 1P: λ
        lam0 = max(1 / x_mean, 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_expon_1p(p, X)

        res = optimize.minimize(
            neg_ll, [lam0], method="L-BFGS-B",
            bounds=[(1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            lam=res.x[0],
            log_likelihood=-res.fun,
        )

    elif dist_type == "E2":
        # Exponential 2P: λ, γ (зафиксирован)
        if gamma_fixed is None:
            gamma_fixed = x_min

        # X_shifted = X - gamma_fixed
        X_shifted = X - gamma_fixed
        X_shifted = X_shifted[X_shifted > 0]
        if len(X_shifted) < 2:
            raise ValueError("E2: insufficient data after shift")

        lam0 = max(1 / np.mean(X_shifted), 1e-6)

        def neg_ll(p):
            return _neg_log_likelihood_expon_2p(p, X, gamma_fixed)

        res = optimize.minimize(
            neg_ll, [lam0], method="L-BFGS-B",
            bounds=[(1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            lam=res.x[0], gamma=gamma_fixed,
            log_likelihood=-res.fun,
        )

    elif dist_type == "LL2":
        # Loglogistic 2P: α, β
        alpha0 = max(x_mean, 1.0)
        beta0 = 1.0

        def neg_ll(p):
            return _neg_log_likelihood_loglogistic_2p(p, X)

        res = optimize.minimize(
            neg_ll, [alpha0, beta0], method="L-BFGS-B",
            bounds=[(1e-10, None), (1e-10, None)],
            options={"gtol": gtol, "maxiter": max_iter},
        )
        return DistParams(
            alpha=res.x[0], beta=res.x[1],
            log_likelihood=-res.fun,
        )

    else:
        raise ValueError(f"mle_2p: unsupported dist_type {dist_type}")


def support_lower(dist_type: DistType, gamma: float = 0.0) -> float:
    """Нижняя граница области определения распределения.

    Args:
        dist_type: тип распределения.
        gamma: параметр сдвига (для 3P).

    Returns:
        Нижняя граница.
    """
    if dist_type in ("N", "GU"):
        return -np.inf
    elif dist_type in ("W2", "G2", "LL2", "E1"):
        return 0.0
    elif dist_type in ("W3", "G3", "LL3", "E2"):
        return gamma
    elif dist_type in ("LN2", "LN3"):
        return max(gamma, 1e-10)
    else:
        return 0.0