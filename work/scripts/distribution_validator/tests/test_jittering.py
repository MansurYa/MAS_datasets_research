"""Тесты для safe_jitter (utils.py)."""
import numpy as np
import pytest

from .utils import safe_jitter


class TestSafeJitter:
    """Тесты для функции safe_jitter."""

    def test_jittering_preserves_shape(self):
        """Проверяем, что shape сохраняется."""
        X = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = safe_jitter(X, support_lower=0.0, delta=0.01)
        assert result.shape == X.shape

    def test_jittering_within_bounds(self):
        """Проверяем, что все значения >= support_lower + delta."""
        np.random.seed(42)
        X = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        support_lower = 0.0
        delta = 0.01

        for _ in range(10):
            result = safe_jitter(X, support_lower, delta)
            assert np.all(result >= support_lower + delta)

    def test_jittering_shifts_values(self):
        """Проверяем, что джиттеринг реально меняет значения."""
        np.random.seed(42)
        X = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        delta = 0.1

        result = safe_jitter(X, support_lower=0.0, delta=delta)
        # Хотя бы одно значение должно измениться
        assert not np.allclose(result, X)

    def test_jittering_large_n(self):
        """Проверяем на большом массиве."""
        np.random.seed(42)
        X = np.random.uniform(1, 100, size=1000)
        support_lower = 0.0
        delta = 0.01

        result = safe_jitter(X, support_lower, delta)
        assert result.shape == X.shape
        assert np.all(result >= support_lower + delta)

    def test_jittering_support_lower_positive(self):
        """Проверяем защиту при положительном support_lower."""
        np.random.seed(42)
        X = np.array([0.1, 0.2, 0.5, 1.0])
        support_lower = 0.5
        delta = 0.01

        result = safe_jitter(X, support_lower, delta)
        # Все значения должны быть >= 0.51
        assert np.all(result >= support_lower + delta)

    def test_jittering_negative_to_positive_boundary(self):
        """Проверяем защиту при переходе через ноль."""
        np.random.seed(42)
        X = np.array([-0.5, -0.1, 0.0, 0.1])
        support_lower = 0.0
        delta = 0.05

        result = safe_jitter(X, support_lower, delta)
        # Даже если джиттеринг сдвинет -0.5 вниз, защита поднимет
        assert np.all(result >= support_lower + delta)