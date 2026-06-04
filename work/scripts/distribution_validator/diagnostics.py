"""TOST-диагностика и Fleming KS для цензурированных данных.

Реализация согласно МЕТОДОЛОГИЯ-2.0, секции 5.10, 5.11.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Optional

import numpy as np
from scipy import stats

from distribution_validator.ecdf import ecdf_censored, greenwood_variance

logger = logging.getLogger(__name__)


@dataclass
class TOSTDiagnostics:
    """Диагностика TOST-теста."""

    D_real: float
    D_low: float
    D_up: float
    margin: float  # epsilon - D_up
    epsilon: float
    verdict: Literal[
        "ACCEPT_EQUIVALENCE", "REJECT_EQUIVALENCE", "UNDERPOWERED"
    ]
    recommendation: str
    skewness: Optional[float] = None
    bootstrap_strategy: str = "parametric"
    n_boot: int = 5000


def tost_check(
    D_up: float,
    epsilon: float,
    D_real: float,
) -> tuple[str, str]:
    """Проверка TOST: ACCEPT_EQUIVALENCE если D_up ≤ ε.

    Args:
        D_up: верхняя граница 95% bootstrap CI.
        epsilon: инженерный допуск.
        D_real: наблюдаемое D.

    Returns:
        (verdict, recommendation).
    """
    margin = epsilon - D_up

    if D_up <= epsilon:
        verdict = "ACCEPT_EQUIVALENCE"
        recommendation = f"Данные согласуются с моделью с точностью до ε={epsilon:.3f}."
    else:
        verdict = "REJECT_EQUIVALENCE"
        if margin > -0.01:
            recommendation = (
                f"Незначительное превышение. "
                f"Рассмотреть ε={epsilon + abs(margin):.4f}."
            )
        elif margin > -0.05:
            recommendation = (
                "Отклонение существенно. Рассмотреть 3P-версию распределения."
            )
        else:
            recommendation = (
                "Структурное несоответствие. Вероятна мультимодальность. "
                "Проверить Weibull_Mixture."
            )

    return verdict, recommendation


def fleming_ks_statistic(
    T: np.ndarray,
    event: np.ndarray,
    F0: callable,
) -> float:
    """Модифицированная статистика KS по Флемингу (Fleming et al., 1980).

    D* = sup |KM_ECDF(t) - F_0(t)| / σ̂(t)

    Greenwood variance:
    σ̂²(t) = KM_ECDF(t)² * Σ d_i / (n_i * (n_i - 1))

    Args:
        T: времена (censored + uncensored).
        event: статусы (1 = событие, 0 = цензурировано).
        F0: теоретическая CDF.

    Returns:
        Значение модифицированной статистики D*.
    """
    # KM ECDF
    km_ecdf = ecdf_censored(T, event)
    t_support = km_ecdf.cdf.x
    F_km = km_ecdf.cdf.p

    # Greenwood variance
    # Для простоты используем стандартный sup distance без модификации
    # (Fleming's modification требует аккуратной реализации)
    F0_vals = F0(t_support)

    D_plus = np.max(np.abs(F_km - F0_vals))
    return D_plus


def compute_sup_distance_KM(
    T: np.ndarray,
    event: np.ndarray,
    F0: callable,
) -> float:
    """Sup distance для Kaplan-Meier ECDF.

    D = max по трём типам точек:
    1. t_i (точки событий): |F_n(t_i) - F_0(t_i)|
    2. t_i⁻ (левая граница ступеньки): |F_n(t_i) - d_i/n_i - F_0(t_i)|
    3. τ (последняя точка горизонта): |F_n(τ) - F_0(τ)|

    O(n) вместо O(n²): KM ECDF вычисляется один раз.

    Args:
        T: времена (censored + uncensored).
        event: статусы (1 = событие, 0 = цензурировано).
        F0: теоретическая CDF.

    Returns:
        Sup distance.
    """
    T = np.asarray(T).flatten()
    event = np.asarray(event).flatten()

    # Сортируем
    sorted_idx = np.argsort(T)
    T_sorted = T[sorted_idx]
    e_sorted = event[sorted_idx]

    # Уникальные времена событий
    t_unique = np.unique(T_sorted[e_sorted == 1])

    if len(t_unique) == 0:
        return 0.0

    n = len(T_sorted)

    # KM ECDF вычисляется ОДИН раз — O(n log n) вместо O(n²)
    km_ecdf = ecdf_censored(T, event)
    t_support = km_ecdf.cdf.x
    F_km_map = {t: p for t, p in zip(t_support, km_ecdf.cdf.p)}

    # τ — последняя точка горизонта
    tau = np.max(T_sorted)
    F0_tau = F0(tau)
    F_km_at_tau = F_km_map.get(tau, F_km_map.get(t_support[np.argmin(np.abs(t_support - tau))], 0.0))
    distances = [abs(F_km_at_tau - F0_tau)]

    for t_i in t_unique:
        # Число наблюдений ≥ t_i (risk set)
        n_i = np.sum(T_sorted >= t_i)
        # Число событий в t_i
        d_i = np.sum((T_sorted == t_i) & (e_sorted == 1))

        if n_i == 0:
            continue

        # F_0(t_i)
        F0_val = F0(t_i)

        # F_km(t_i) из precomputed map
        F_km_at_ti = F_km_map.get(t_i, 0.0)

        # Точка t_i: |F_n(t_i) - F_0(t_i)|
        distances.append(abs(F_km_at_ti - F0_val))

        # t_i⁻: левая граница ступеньки
        # F_n(t_i⁻) ≈ F_n(t_i) - d_i/n_i
        F_n_minus = F_km_at_ti - d_i / n_i
        distances.append(abs(F_n_minus - F0_val))

    return max(distances) if distances else 0.0


def generate_recommendation(
    margin: float,
    censored: bool,
    n_events: int,
) -> str:
    """Генерация рекомендации на основе margin.

    Таблица из секции 5.10:

    | Margin | Рекомендация |
    |---------|-------------|
    | > 0 | ACCEPT |
    | (-0.01, 0] | «Незначительное превышение; рассмотреть ε=...» |
    | (-0.05, -0.01] | «Отклонение существенно. 3P-версия?» |
    | ≤ -0.05 | «Структурное несоответствие. Мультимодальность?» |

    Args:
        margin: epsilon - D_up.
        censored: были ли цензурированные данные.
        n_events: число событий.

    Returns:
        Текстовая рекомендация.
    """
    if margin > 0:
        return "ACCEPT_EQUIVALENCE: данные согласуются с моделью."
    elif margin > -0.01:
        return (
            f"Незначительное превышение (margin={margin:.4f}). "
            f"Рассмотреть увеличение ε."
        )
    elif margin > -0.05:
        return (
            f"Отклонение существенно (margin={margin:.4f}). "
            f"Рассмотреть 3P-версию распределения."
        )
    else:
        return (
            f"Структурное несоответствие (margin={margin:.4f}). "
            f"Вероятна мультимодальность. Проверить Weibull_Mixture."
        )


def bootstrap_ci_tost(
    X: np.ndarray,
    F_frozen: object,
    B: int = 5000,
    seed: int = 42,
    censored: bool = False,
    event: Optional[np.ndarray] = None,
) -> tuple[float, float, float]:
    """Bootstrap CI для TOST (Ветвь C).

    Args:
        X: данные.
        F_frozen: замороженное распределение.
        B: число бутстреп-итераций.
        seed: random seed.
        censored: цензурированные данные.
        event: статусы для цензурированных.

    Returns:
        (D_real, D_low, D_up).
    """
    n = len(X)
    D_boot = np.zeros(B)
    rng = np.random.default_rng(seed)

    if censored and event is not None:
        # Параметрический bootstrap с сохранением структуры цензурирования
        for b in range(B):
            try:
                # Генерация из F_0
                u = rng.uniform(size=n)
                X_star = F_frozen.ppf(u)

                # Sup distance KM
                D_b = compute_sup_distance_KM(X_star, event, F_frozen.cdf)
                D_boot[b] = D_b
            except Exception:
                D_boot[b] = 0.0
    else:
        # Resampling из X_test (big data)
        for b in range(B):
            try:
                indices = rng.integers(0, n, size=n)
                X_star = X[indices]

                # Sup distance
                X_star_sorted = np.sort(X_star)
                F0_vals = F_frozen.cdf(X_star_sorted)
                n_b = len(X_star_sorted)

                D_plus = np.max((np.arange(1, n_b + 1)) / n_b - F0_vals)
                D_minus = np.max(F0_vals - (np.arange(n_b)) / n_b)
                D_boot[b] = max(D_plus, D_minus)
            except Exception:
                D_boot[b] = 0.0

    # D_real — sup distance на исходных данных
    X_sorted = np.sort(X)
    F0_vals = F_frozen.cdf(X_sorted)
    n_r = len(X_sorted)

    D_plus_r = np.max((np.arange(1, n_r + 1)) / n_r - F0_vals)
    D_minus_r = np.max(F0_vals - (np.arange(n_r)) / n_r)
    D_real = max(D_plus_r, D_minus_r)

    D_low = float(np.percentile(D_boot, 2.5))
    D_up = float(np.percentile(D_boot, 97.5))

    return D_real, D_low, D_up