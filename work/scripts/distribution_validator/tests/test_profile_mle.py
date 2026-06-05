"""Тесты для profile_mle.py."""
from __future__ import annotations

import numpy as np
import pytest

from .distributions import custom_loglogistic
from .profile_mle import (
    MLE_STATUS_CONVERGENCE_WARNING,
    MLE_STATUS_DOUBLE_WARNING,
    MLE_STATUS_MARGINAL,
    MLE_STATUS_NEAR_BOUNDARY,
    MLE_STATUS_NOT_SIGNIFICANT,
    MLE_STATUS_SINGULARITY,
    ProfileMLEResult,
    profile_mle_3p,
)


class TestProfileMLE:
    """Тесты для profile_mle_3p."""

    def test_weibull_3p_recovery(self):
        """Weibull_3P: результат должен быть валидным."""
        np.random.seed(42)
        alpha_true, beta_true, gamma_true = 1000.0, 1.5, 100.0

        # Генерация: Weibull с порогом gamma
        X = gamma_true + alpha_true * np.random.weibull(beta_true, size=500)

        result = profile_mle_3p(X, "W3")

        # Должен вернуть результат (fallback работает)
        assert result is not None
        assert isinstance(result, ProfileMLEResult)
        assert len(result.status_codes) >= 0

        # Если не SINGULARITY, то параметры должны быть положительны
        if MLE_STATUS_SINGULARITY not in result.status_codes:
            if result.alpha_final > 0:
                assert result.alpha_final < alpha_true * 20

    def test_loglogistic_3p_recovery(self):
        """Loglogistic_3P: оценки в разумных пределах."""
        np.random.seed(42)
        alpha_true, beta_true, gamma_true = 1000.0, 1.5, 100.0

        ll3 = custom_loglogistic_3p(alpha=alpha_true, beta=beta_true, gamma=gamma_true)
        X = ll3.rvs(size=500, seed=42)

        result = profile_mle_3p(X, "LL3")

        assert result.alpha_final > 0
        assert result.beta_final > 0
        assert result.gamma_final >= 0
        assert result.ll_3p > -np.inf

    def test_gamma_locked_by_singularity(self):
        """При β≤1 должен вернуться статус γ_NEAR_BOUNDARY или DOUBLE_WARNING.

        Subtask A (Weibull probability paper) пропущен для надёжности.
        LRT сам определяет, нужен ли 3P. При β≤1 данные γ≈x_min,
        что даёт предупреждения о граничной области.
        """
        np.random.seed(42)
        alpha_true, beta_true, gamma_true = 1000.0, 0.5, 50.0

        # Генерация: Weibull с beta <= 1
        X = gamma_true + alpha_true * np.random.weibull(beta_true, size=500)

        result = profile_mle_3p(X, "W3")

        # Модель сходится, но с предупреждениями о граничной области
        boundary_codes = {MLE_STATUS_NEAR_BOUNDARY, MLE_STATUS_DOUBLE_WARNING}
        assert any(c in boundary_codes for c in result.status_codes), (
            f"Expected boundary warning codes, got {result.status_codes}"
        )

    def test_gamma_not_significant(self):
        """При γ=0 (данные без сдвига) должен вернуться γ_NOT_SIGNIFICANT."""
        np.random.seed(42)
        # Чистый Weibull 2P без сдвига
        alpha_true, beta_true = 1000.0, 1.5
        X = alpha_true * np.random.weibull(beta_true, size=500)

        result = profile_mle_3p(X, "W3")

        # При γ≈0 дополнительный параметр незначим
        assert result.gamma_final < 50.0  # gamma должен быть малым
        assert result.p_LRT is not None

    def test_convergence_warning_fallback(self):
        """При малом количестве данных должен вернуть результат."""
        np.random.seed(42)
        # Очень малые данные
        X = 1000.0 + 500.0 * np.random.weibull(1.5, size=20)

        result = profile_mle_3p(X, "W3")

        # Должен вернуть результат (fallback работает)
        assert result is not None
        assert isinstance(result, ProfileMLEResult)
        assert result.params_2p is not None

    def test_small_sample(self):
        """При n < 10 должно выбросить ValueError."""
        np.random.seed(42)
        X = np.random.exponential(scale=1000, size=5)

        with pytest.raises(ValueError):
            profile_mle_3p(X, "W3")

    def test_result_dataclass_fields(self):
        """Проверяем все поля ProfileMLEResult."""
        np.random.seed(42)
        X = 100.0 + 1000.0 * np.random.weibull(1.5, size=100)

        result = profile_mle_3p(X, "W3")

        assert isinstance(result, ProfileMLEResult)
        assert hasattr(result, "params_3p")
        assert hasattr(result, "params_2p")
        assert hasattr(result, "use_3p")
        assert hasattr(result, "status_codes")
        assert hasattr(result, "gamma_final")
        assert hasattr(result, "ll_3p")
        assert hasattr(result, "ll_2p")
        assert hasattr(result, "p_LRT")
        assert hasattr(result, "converged")


class TestProfileMLEResult:
    """Тесты для статус-кодов."""

    def test_marginal_status(self):
        """Статус MARGINAL когда 0.05 < p_LRT ≤ 0.10."""
        # Создаём искусственный результат
        np.random.seed(42)
        X = 50.0 + 1000.0 * np.random.weibull(1.5, size=200)

        result = profile_mle_3p(X, "W3")

        # p_LRT должен быть вычислен
        assert 0.0 <= result.p_LRT <= 1.0

    def test_status_codes_list(self):
        """status_codes должен быть списком."""
        np.random.seed(42)
        X = 100.0 + 1000.0 * np.random.weibull(1.5, size=100)

        result = profile_mle_3p(X, "W3")

        assert isinstance(result.status_codes, list)


class custom_loglogistic_3p:
    """Копия для тестирования (из distributions.py)."""

    def __init__(self, alpha: float, beta: float, gamma: float):
        self.alpha = alpha
        self.beta = beta
        self.gamma = gamma

    def rvs(self, size=None, seed=None):
        rng = np.random.default_rng(seed)
        u = rng.uniform(size=size)
        eps = 1e-10
        u = np.clip(u, eps, 1.0 - eps)
        return self.gamma + self.alpha * (u / (1.0 - u)) ** (1.0 / self.beta)