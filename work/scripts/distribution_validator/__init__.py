"""distribution_validator: проверка согласия данных с теоретическим распределением.

МЕТОДОЛОГИЯ-2.0.
"""
from . import (
    bootstrap,
    diagnostics,
    distributions,
    ecdf,
    goodness,
    profile_mle,
    report,
    select,
    utils,
    validate,
    visualization,
)
from .report import AuditReport
from .select import ScaleSelectorResult
from .validate import ValidationResult

__all__ = [
    "bootstrap",
    "diagnostics",
    "distributions",
    "ecdf",
    "goodness",
    "profile_mle",
    "report",
    "select",
    "utils",
    "validate",
    "visualization",
    "AuditReport",
    "ScaleSelectorResult",
    "ValidationResult",
]