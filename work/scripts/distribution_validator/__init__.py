"""distribution_validator: проверка согласия данных с теоретическим распределением.

МЕТОДОЛОГИЯ-2.0.
"""
from distribution_validator import (
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
from distribution_validator.report import AuditReport
from distribution_validator.select import ScaleSelectorResult
from distribution_validator.validate import ValidationResult

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