"""ECDF: полные и цензурированные данные.

ecdf_full — стандартная ECDF из scipy.stats.
ecdf_censored — Kaplan-Meier через scipy.stats.CensoredData.
dkw_confidence_interval — DKW доверительные полосы.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

# Типы для цензурированных данных
EventMask = np.ndarray  # 1 = событие, 0 = цензурирование


def ecdf_full(X: np.ndarray) -> stats.ECDF:
    """Эмпирическая функция распределения (полные данные).

    Args:
        X: одномерный массив данных.

    Returns:
        Объект scipy.stats.ECDF с методами .cdf(x) и .support.
    """
    X = np.asarray(X).flatten()
    X = X[~np.isnan(X)]
    return stats.ecdf(X)


def ecdf_censored(
    times: np.ndarray,
    event: np.ndarray,
) -> stats.ECDF:
    """ECDF для цензурированных данных (оценка Каплана-Майера).

    scipy.stats.CensoredData автоматически вычисляет KM-ECDF.

    Args:
        times: массив времени (censored + uncensored).
        event: массив статуса (1 = событие, 0 = цензурировано).

    Returns:
        Объект ECDF с Kaplan-Meier оценкой.
    """
    times = np.asarray(times).flatten()
    event = np.asarray(event).flatten()

    if not np.all(np.isin(event, [0, 1])):
        raise ValueError("event_mask должен содержать только 0 и 1")

    uncensored = times[event == 1]
    censored = times[event == 0]

    censored_data = stats.CensoredData(uncensored=uncensored, censored_right=censored)
    return censored_data.ecdf()


def dkw_confidence_interval(
    ecdf_result: stats.ECDF,
    alpha: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    """Доверительные полосы Дворецкого-Кифера-Волфовица.

    Неравенство DKW даёт равномерные границы:
    P(sup|F_n(x) - F(x)| ≤ ε) ≥ 1 - α
    где ε = sqrt(ln(2/α) / (2n))

    Args:
        ecdf_result: результат ecdf_full() или ecdf_censored().
        alpha: уровень значимости (0.05 = 95% CI).

    Returns:
        (lower_bound, upper_bound) — массивы той же длины, что ecdf.cdf.x.
    """
    ci = ecdf_result.confidence_interval(method="dkw")
    return ci.low, ci.high


def km_survival_function(
    times: np.ndarray,
    event: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Каплан-Майер: S(t) и F(t) = 1 - S(t).

    Returns:
        t_unique: уникальные времена событий.
        S: оценка выживаемости.
        d: числа событий в каждой точке.
    """
    times = np.asarray(times).flatten()
    event = np.asarray(event).flatten()

    # Сортируем по времени
    sorted_idx = np.argsort(times)
    t_sorted = times[sorted_idx]
    e_sorted = event[sorted_idx]

    # Уникальные времена событий (event=1)
    t_event, d = np.unique(t_sorted[e_sorted == 1], return_counts=True)
    n = len(t_sorted)

    # Kaplan-Meier S(t)
    S = np.ones(len(t_event) + 1)
    S[0] = 1.0
    risk_set = n

    for i, (t_i, d_i) in enumerate(zip(t_event, d)):
        risk_set_i = np.sum(t_sorted >= t_i)
        S[i + 1] = S[i] * (1 - d_i / risk_set_i)

    # S(t) constant between event times
    # F(t) = 1 - S(t)

    return t_event, S[:-1], d


def greenwood_variance(
    times: np.ndarray,
    event: np.ndarray,
    S: np.ndarray,
    d: np.ndarray,
) -> np.ndarray:
    """Оценка дисперсии Гринвуда для KM-ECDF.

    Var[S(t)] = S(t)^2 * Σ d_i / (n_i * (n_i - 1))

    Args:
        times: времена (отсортированные).
        event: статусы (отсортированные).
        S: оценка выживаемости.
        d: числа событий в каждой точке.

    Returns:
        Массив дисперсий для каждого t_event.
    """
    n = len(times)
    t_event = np.unique(times[event == 1])

    var = np.zeros(len(t_event))
    for i, t_i in enumerate(t_event):
        risk_i = np.sum(times >= t_i)
        if risk_i > 1:
            var[i] = S[i] ** 2 * d[i] / (risk_i * (risk_i - 1))

    return var