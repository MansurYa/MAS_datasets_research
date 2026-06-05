"""Тесты для distributions.py."""
from __future__ import annotations

import numpy as np
import pytest

from .distributions import (
    custom_loglogistic,
    custom_loglogistic_3p,
    DistParams,
    mle_2p,
    support_lower,
)


class TestCustomLoglogistic:
    """Тесты для custom_loglogistic."""

    def test_cdf_monotonic(self):
        """CDF должна быть монотонно неубывающей."""
        ll = custom_loglogistic(alpha=1.0, beta=2.0)
        x = np.linspace(0.1, 10, 100)
        cdf_vals = ll.cdf(x)
        assert np.all(np.diff(cdf_vals) >= -1e-10)

    def test_ppf_roundtrip(self):
        """PPF(CDF(x)) ≈ x с разумной точностью."""
        ll = custom_loglogistic(alpha=1000.0, beta=1.5)
        x = np.linspace(10, 5000, 50)  # Исключаем очень малые x
        cdf_vals = ll.cdf(x)
        recovered = ll.ppf(cdf_vals)
        rel_err = np.abs(recovered - x) / (np.abs(x) + 1e-10)
        # Tolerance 5% — достаточно для численного roundtrip
        assert np.all(rel_err < 0.05)

    def test_ppf_edge_cases(self):
        """PPF должен работать на краях [0.0001, 0.9999]."""
        ll = custom_loglogistic(alpha=1000.0, beta=1.5)

        u_low = 0.0001
        u_high = 0.9999

        x_low = ll.ppf(u_low)
        x_high = ll.ppf(u_high)

        # Значения должны быть конечными
        assert np.isfinite(x_low)
        assert np.isfinite(x_high)
        # x_high > x_low
        assert x_high > x_low

    def test_rvs_shape(self):
        """rvs должен генерировать массив нужной формы."""
        ll = custom_loglogistic(alpha=1.0, beta=2.0)
        samples = ll.rvs(size=1000, seed=42)
        assert samples.shape == (1000,)

    def test_pdf_integration(self):
        """Интеграл PDF должен быть ≈ 1."""
        ll = custom_loglogistic(alpha=1.0, beta=2.0)
        x = np.linspace(0.01, 100, 10000)
        pdf_vals = ll.pdf(x)
        # Trapezoidal integration
        integral = np.trapezoid(pdf_vals, x)
        assert abs(integral - 1.0) < 0.1


class TestCustomLoglogistic3P:
    """Тесты для custom_loglogistic_3p."""

    def test_shift_works(self):
        """3P должен сдвигать распределение."""
        ll3 = custom_loglogistic_3p(alpha=1.0, beta=2.0, gamma=100.0)
        ll2 = custom_loglogistic(alpha=1.0, beta=2.0)

        x = np.array([101.0, 102.0, 105.0])
        cdf_3p = ll3.cdf(x)
        cdf_2p = ll2.cdf(x - 100.0)

        np.testing.assert_allclose(cdf_3p, cdf_2p, rtol=1e-10)

    def test_support_boundary(self):
        """При x → γ+, CDF → 0."""
        ll3 = custom_loglogistic_3p(alpha=1.0, beta=2.0, gamma=100.0)
        x_near_boundary = np.array([100.001, 100.01, 100.1])
        cdf_vals = ll3.cdf(x_near_boundary)
        assert np.all(cdf_vals < 0.01)


class TestMLE2P:
    """Тесты для mle_2p."""

    def test_weibull_2p_recovery(self):
        """Weibull 2P: оценки в разумных пределах."""
        np.random.seed(42)
        alpha_true, beta_true = 1000.0, 1.5
        X = alpha_true * np.random.weibull(beta_true, size=500)

        params = mle_2p(X, "W2", context="final")

        # Параметры должны быть положительными и в разумных пределах
        assert params.alpha > 0
        assert params.beta > 0
        # alpha не должен быть на много порядков больше true
        assert params.alpha < alpha_true * 10
        assert params.log_likelihood is not None

    def test_lognorm_2p_recovery(self):
        """Lognormal 2P: оценки близки к истинным параметрам."""
        np.random.seed(42)
        mu_true, sigma_true = 5.0, 0.5
        X = np.exp(mu_true + sigma_true * np.random.standard_normal(500))

        params = mle_2p(X, "LN2", context="final")

        assert abs(params.mu - mu_true) / (abs(mu_true) + 1e-10) < 0.2
        assert abs(params.sigma - sigma_true) / sigma_true < 0.2

    def test_gamma_2p_recovery(self):
        """Gamma 2P: оценки близки к истинным параметрам."""
        np.random.seed(42)
        k_true, theta_true = 2.0, 500.0
        X = np.random.gamma(k_true, scale=theta_true, size=500)

        params = mle_2p(X, "G2", context="final")

        assert abs(params.k - k_true) / k_true < 0.3
        assert abs(params.theta - theta_true) / theta_true < 0.2

    def test_normal_2p_recovery(self):
        """Normal 2P: оценки близки к истинным параметрам."""
        np.random.seed(42)
        mu_true, sigma_true = 100.0, 15.0
        X = mu_true + sigma_true * np.random.standard_normal(500)

        params = mle_2p(X, "N", context="final")

        assert abs(params.mu - mu_true) / abs(mu_true) < 0.05
        assert abs(params.sigma - sigma_true) / sigma_true < 0.1

    def test_expon_1p_recovery(self):
        """Exponential 1P: оценки близки к истинным параметрам."""
        np.random.seed(42)
        lam_true = 0.001
        X = np.random.exponential(scale=1/lam_true, size=500)

        params = mle_2p(X, "E1", context="final")

        assert abs(params.lam - lam_true) / lam_true < 0.15

    def test_loglogistic_2p_recovery(self):
        """Loglogistic 2P: MLE сходится, параметры положительны."""
        np.random.seed(42)
        alpha_true, beta_true = 1000.0, 1.5
        ll = custom_loglogistic(alpha=alpha_true, beta=beta_true)
        X = ll.rvs(size=500, seed=42)

        params = mle_2p(X, "LL2", context="final")

        # MLE должен сойтись, параметры положительны
        assert params.alpha > 0
        assert params.beta > 0
        assert params.log_likelihood is not None
        # alpha не должен быть слишком далеко
        assert params.alpha < alpha_true * 5


class TestSupportLower:
    """Тесты для support_lower."""

    @pytest.mark.parametrize(
        "dist_type,gamma,expected",
        [
            ("N", 0.0, -np.inf),
            ("GU", 0.0, -np.inf),
            ("W2", 0.0, 0.0),
            ("G2", 0.0, 0.0),
            ("LL2", 0.0, 0.0),
            ("E1", 0.0, 0.0),
            ("W3", 100.0, 100.0),
            ("LN3", 0.0, 1e-10),
            ("E2", 50.0, 50.0),
        ],
    )
    def test_support_lower_values(self, dist_type, gamma, expected):
        """Проверяем корректность support_lower."""
        result = support_lower(dist_type, gamma)
        assert np.isclose(result, expected) or (result == expected)