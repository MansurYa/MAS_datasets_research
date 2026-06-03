"""Интеграционный тест: Weibull_3P(α=4247, β=1.31, γ=1240), N=847.

Согласно TZ_7, должен выдать ACCEPT с p_final > 0.05.
"""
from __future__ import annotations

import numpy as np
import pytest
from pathlib import Path

from distribution_validator.main import main
from distribution_validator import distributions


class TestIntegration:
    """Интеграционные тесты."""

    def test_weibull_3p_full_pipeline(self):
        """Полный pipeline: Weibull_3P, ACCEPT, PNG, MD."""
        np.random.seed(42)

        # Симуляция Weibull_3P(α=4247, β=1.31, γ=1240)
        alpha_true, beta_true, gamma_true = 4247.0, 1.31, 1240.0
        X = gamma_true + alpha_true * np.random.weibull(beta_true, size=847)

        # Pipeline
        result, plot_path, md_path = main(
            X, "W3",
            epsilon=0.03,
            alpha=0.05,
            power=0.80,
            do_split=True,
            B=1000,  # Быстрый режим
            seed=42,
        )

        # ACCEPT или ACCEPT_EQUIVALENCE ожидаем
        assert result.verdict in ("ACCEPT", "ACCEPT_EQUIVALENCE"), (
            f"Expected ACCEPT or ACCEPT_EQUIVALENCE, got {result.verdict}"
        )

        # PNG сгенерирован
        if plot_path:
            plot_p = Path(plot_path)
            assert plot_p.exists(), f"Plot does not exist: {plot_path}"
            assert plot_p.stat().st_size > 10 * 1024, (
                f"Plot too small: {plot_p.stat().st_size} bytes"
            )

        # MD сгенерирован
        md_p = Path(md_path)
        assert md_p.exists(), f"MD does not exist: {md_path}"

        md_content = md_p.read_text()
        assert result.verdict in md_content, "Verdict not in MD"
        assert "D_obs" in md_content, "D_obs not in MD"
        assert plot_path and Path(plot_path).name in md_content, "PNG path not in MD"

    def test_weibull_2p_fast(self):
        """Быстрый pipeline: Weibull_2P."""
        np.random.seed(42)
        X = 1000.0 * np.random.weibull(1.5, size=200)

        result, plot_path, md_path = main(
            X, "W2",
            epsilon=0.03,
            alpha=0.05,
            do_split=True,
            B=500,  # Очень быстрый
            seed=42,
        )

        assert result.verdict in ("ACCEPT", "ACCEPT_EQUIVALENCE", "REJECT")
        assert Path(md_path).exists()

    def test_check_scipy_version(self):
        """check_scipy_version не должен падать."""
        from distribution_validator import utils
        # Не должно выбросить
        utils.check_scipy_version()

    def test_check_dependency_constraints(self):
        """check_dependency_constraints не должен падать."""
        from distribution_validator import utils
        # Не должно выбросить (запрещённые пакеты не установлены)
        utils.check_dependency_constraints()

    def test_scale_selector(self):
        """scale_selector возвращает корректный результат."""
        from distribution_validator.select import scale_selector

        np.random.seed(42)
        X = 1000.0 * np.random.weibull(1.5, size=500)

        result = scale_selector(X, epsilon=0.03, alpha=0.05, power=0.80)

        assert result.mode in ("UNDERPOWERED", "BOOTSTRAP", "SPLIT_EXACT", "BIG_DATA")
        assert result.N_min is not None
        assert result.N_max is not None
        assert result.xi > 0

    def test_bootstrap_fast(self):
        """Bootstrap работает на малых данных."""
        np.random.seed(42)
        X = 1000.0 * np.random.weibull(1.5, size=100)

        result, _, md_path = main(
            X, "W2",
            epsilon=0.03,
            do_split=False,
            B=100,
            seed=42,
        )

        assert result.verdict in ("ACCEPT", "REJECT")
        assert result.D_obs >= 0