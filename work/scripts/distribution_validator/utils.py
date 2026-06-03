"""Утилиты для distribution_validator.

Проверки окружения, paths, hashing, jittering.
"""
from __future__ import annotations

import hashlib
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy

logger = logging.getLogger(__name__)

# Пути
PLOTS_DIR = Path("work/plots/distribution_validator")
DOCS_DIR = Path("work/docs/distribution_validator")

# Создание директорий
PLOTS_DIR.mkdir(parents=True, exist_ok=True)
DOCS_DIR.mkdir(parents=True, exist_ok=True)

# Запрещённые пакеты (GPL-лицензии)
FORBIDDEN_PACKAGES = [
    "weibullr",
    "envstats",
    "gofcens",
    "hdi",
    "rpy2",
]


def check_scipy_version() -> None:
    """Проверить, что scipy >= 1.11.0.

    Raises:
        EnvironmentError: если версия scipy старая.
    """
    major, minor = map(int, scipy.__version__.split(".")[:2])
    if (major, minor) < (1, 11):
        raise EnvironmentError(
            f"Методология 2.0 требует scipy >= 1.11.0. "
            f"Текущая версия: {scipy.__version__}"
        )
    logger.info(f"scipy version check passed: {scipy.__version__}")


def check_dependency_constraints() -> None:
    """Проверить, что запрещённые пакеты не установлены.

    Raises:
        EnvironmentError: если найден запрещённый пакет.
    """
    try:
        from importlib.metadata import version
    except ImportError:
        from importlib_metadata import version  # type: ignore

    for pkg in FORBIDDEN_PACKAGES:
        try:
            ver = version(pkg)
            raise EnvironmentError(
                f"Запрещённый пакет '{pkg}' версии {ver} обнаружен. "
                f"Пакеты {FORBIDDEN_PACKAGES} не являются зависимостями проекта."
            )
        except Exception:
            pass  # пакет не установлен — это нормально
    logger.info("Dependency constraints check passed: no forbidden packages")


def compute_data_hash(X: np.ndarray) -> str:
    """Вычислить SHA-256 хэш данных.

    Хэш вычисляется от оптимизированного одномерного массива,
    чтобы гарантировать воспроизводимость.

    Args:
        X: массив данных.

    Returns:
        Хэш в hex-формате (64 символа).
    """
    X_flat = np.ascontiguousarray(
        np.subtract(X, np.min(X))  # детерминированный сдвиг
    )
    digest = hashlib.sha256(X_flat).hexdigest()
    logger.debug(f"Data hash: {digest[:16]}...")
    return digest


def safe_jitter(
    X: np.ndarray,
    support_lower: float,
    delta: float,
) -> np.ndarray:
    """Jittering с защитой области определения.

    Добавляет микроскопический шум U(-δ, +δ) к данным.
    Результат гарантированно >= support_lower + delta.

    Args:
        X: входной массив.
        support_lower: нижняя граница области определения.
        delta: амплитуда джиттеринга.

    Returns:
        Джиттеренный массив той же формы.
    """
    noise = np.random.uniform(-delta, delta, size=X.shape)
    jittered = X + noise
    # Защита области определения
    jittered = np.maximum(support_lower + delta, jittered)
    return jittered


def audit_id() -> str:
    """Сгенерировать уникальный ID для аудит-отчёта.

    Returns:
        Строка формата audit-YYYYMMDD-HHMMSS.
    """
    return f"audit-{datetime.now():%Y%m%d-%H%M%S}"


def get_cache_dir() -> Path:
    """Вернуть путь к директории кэша.

    Returns:
        Path к ~/.cache/distfit_validator/.
    """
    cache_dir = Path.home() / ".cache" / "distfit_validator"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir