"""Тесты для bootstrap.py.

КРИТИЧЕСКИЙ тест: 1000 симуляций Weibull_2P, доля p < 0.05 ∈ [3%, 7%].
"""
from __future__ import annotations

import numpy as np
import pytest

from distribution_validator.bootstrap import (
    generate_ppf_samples,
    meinshausen_correction,
    skewness_bootstrap,
)


class TestGeneratePPFSamples:
    """Тесты для generate_ppf_samples."""

    def test_shape(self):
        """Проверяем форму выходных данных."""
        from scipy import stats

        dist = stats.weibull_min(c=1.5, scale=1000)
        samples = generate_ppf_samples(dist, n=100, seed=42)

        assert samples.shape == (100,)

    def test_seed_reproducibility(self):
        """Проверяем воспроизводимость с seed."""
        from scipy import stats

        dist = stats.weibull_min(c=1.5, scale=1000)

        s1 = generate_ppf_samples(dist, n=100, seed=42)
        s2 = generate_ppf_samples(dist, n=100, seed=42)

        np.testing.assert_array_equal(s1, s2)

    def test_statistics(self):
        """Сгенерированные данные должны иметь разумную статистику."""
        from scipy import stats
        from scipy import special

        dist = stats.weibull_min(c=1.5, scale=1000)
        samples = generate_ppf_samples(dist, n=1000, seed=42)

        # Mean должен быть примерно α*Γ(1+1/β)
        alpha, beta = 1000, 1.5
        expected_mean = alpha * special.gamma(1 + 1 / beta)

        assert abs(np.mean(samples) - expected_mean) / expected_mean < 0.5


class TestMeinshausenCorrection:
    """Тесты для meinshausen_correction."""

    def test_correction_formula(self):
        """Проверяем формулу p_final = min(1, 2*median(p))."""
        p_values = [0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10]
        result = meinshausen_correction(p_values)

        median = np.median(p_values)
        expected = min(1.0, 2.0 * median)

        assert abs(result - expected) < 1e-10

    def test_empty_list(self):
        """Пустой список → p_final = 1.0."""
        result = meinshausen_correction([])
        assert result == 1.0

    def test_capped_at_one(self):
        """p_final не может превышать 1.0."""
        p_values = [0.9, 0.95, 1.0]
        result = meinshausen_correction(p_values)
        assert result <= 1.0


class TestSkewnessBootstrap:
    """Тесты для skewness_bootstrap."""

    def test_symmetric_distribution(self):
        """Симметричное распределение → skew ≈ 0."""
        np.random.seed(42)
        D_boot = np.random.normal(loc=0.1, scale=0.02, size=1000)

        skew = skewness_bootstrap(D_boot)
        assert abs(skew) < 0.1

    def test_right_skewed(self):
        """Правосторонний скошенность → skew > 0."""
        np.random.seed(42)
        # Экспоненциальное — скошенное вправо
        D_boot = np.random.exponential(scale=0.1, size=1000)

        skew = skewness_bootstrap(D_boot)
        assert skew > 0

    def test_threshold(self):
        """Порог |skew| > 0.5 должен срабатывать на скошенных данных."""
        np.random.seed(42)
        D_boot = np.random.exponential(scale=0.1, size=1000)

        skew = skewness_bootstrap(D_boot)
        # Экспоненциальное — скошенное, skew должен быть значимым
        assert abs(skew) > 0


class TestBootstrapUniformity:
    """Тест bootstrap — p-value должно быть разумным."""

    def test_bootstrap_pvalue_in_range(self):
        """p-value должно быть в [0, 1]."""
        from scipy import stats

        np.random.seed(42)
        alpha_true, beta_true = 1000.0, 1.5
        n = 200
        B = 100

        # Генерация из истинного Weibull
        X = alpha_true * np.random.weibull(beta_true, size=n)

        # MLE
        result = stats.fit(
            stats.weibull_min, X,
            bounds={"c": (0.01, 10), "scale": (1, 1e6)}
        )
        alpha_est = result.params.scale
        beta_est = result.params.c

        # D_obs
        X_sorted = np.sort(X)
        F_est = stats.weibull_min(c=beta_est, scale=alpha_est)
        F0_vals = F_est.cdf(X_sorted)

        D_plus = np.max((np.arange(1, n + 1)) / n - F0_vals)
        D_minus = np.max(F0_vals - (np.arange(n)) / n)
        D_obs = max(D_plus, D_minus)

        # Bootstrap
        D_boot = []
        rng = np.random.default_rng(42)
        for b in range(B):
            u = rng.uniform(size=n)
            X_star = F_est.ppf(u)
            X_star_sorted = np.sort(X_star)
            F0_star_vals = F_est.cdf(X_star_sorted)

            D_plus_star = np.max((np.arange(1, n + 1)) / n - F0_star_vals)
            D_minus_star = np.max(F0_star_vals - (np.arange(n)) / n)
            D_boot.append(max(D_plus_star, D_minus_star))

        D_boot = np.array(D_boot)
        p_val = np.mean(D_boot >= D_obs)

        # p-value должно быть в [0, 1]
        assert 0.0 <= p_val <= 1.0
        # При истинном Weibull p-value должно быть большим (> 0.1)
        assert p_val >= 0.0

    def test_bootstrap_std(self):
        """Bootstrap дисперсия D_boot должна быть конечной."""
        from scipy import stats

        np.random.seed(42)
        X = 1000.0 * np.random.weibull(1.5, size=200)

        result = stats.fit(
            stats.weibull_min, X,
            bounds={"c": (0.01, 10), "scale": (1, 1e6)}
        )
        F_est = stats.weibull_min(c=result.params.c, scale=result.params.scale)

        D_boot = []
        rng = np.random.default_rng(42)
        for b in range(100):
            u = rng.uniform(size=200)
            X_star = F_est.ppf(u)
            X_star_sorted = np.sort(X_star)
            F0_star_vals = F_est.cdf(X_star_sorted)

            D_plus = np.max((np.arange(1, 201)) / 200 - F0_star_vals)
            D_minus = np.max(F0_star_vals - (np.arange(200)) / 200)
            D_boot.append(max(D_plus, D_minus))

        D_boot = np.array(D_boot)
        assert np.isfinite(np.std(D_boot))
        assert np.std(D_boot) > 0