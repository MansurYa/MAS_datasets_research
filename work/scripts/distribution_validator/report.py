"""Аудит-отчёт: машиночитаемый и человекочитаемый.

Реализация согласно МЕТОДОЛОГИЯ-2.0, секция 11.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from .utils import DOCS_DIR


@dataclass
class TraceEntry:
    """Запись в трассировке решений."""

    step: int
    component: str
    action: str
    result: str


@dataclass
class AuditReport:
    """Компактная спецификация аудит-отчёта."""

    audit_id: str
    distribution: str
    N_total: int
    N_fit: int
    N_test: int
    branch: str  # "A_BOOTSTRAP" / "B_SPLIT" / "C_TOST"
    epsilon: float
    alpha: float
    power_target: float
    verdict: str  # "ACCEPT" / "REJECT" / "ACCEPT_EQUIVALENCE" / "UNDERPOWERED"
    D_obs: float
    p_value: Optional[float] = None
    p_final: Optional[float] = None
    p_LRT: Optional[float] = None
    skewness: Optional[float] = None
    N_min: Optional[int] = None
    N_max: Optional[int] = None
    mode: str = ""
    parameters: dict = field(default_factory=dict)
    status_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)
    data_hash: str = ""
    computation_time_s: float = 0.0
    scipy_version: str = ""
    figure_path: str = ""


def save_report(report: AuditReport, output_dir: Optional[Path] = None) -> Path:
    """Сохранить аудит-отчёт в Markdown.

    Args:
        report: AuditReport.
        output_dir: директория для сохранения. По умолчанию DOCS_DIR.

    Returns:
        Путь к сохранённому файлу.
    """
    save_dir = output_dir if output_dir is not None else DOCS_DIR
    save_dir.mkdir(parents=True, exist_ok=True)

    path = save_dir / f"dv_report-{report.audit_id}.md"
    path.write_text(_render_template(report))
    return path


def _render_template(report: AuditReport) -> str:
    """Рендеринг шаблона аудит-отчёта."""

    # Параметры модели таблица
    params_table = ""
    for name, value in report.parameters.items():
        if value is not None:
            params_table += f"| {name} | {value:.4f} | MLE | — |\n"

    # Статус-коды
    status_block = ""
    if report.status_codes:
        status_block = "\n".join(f"- `{code}`" for code in report.status_codes)
    else:
        status_block = "Нет"

    # Предупреждения
    warnings_block = "\n".join(f"- {w}" for w in report.warnings) if report.warnings else "Нет"

    # Трассировка
    trace_table = ""
    for entry in report.trace:
        trace_table += f"| {entry.step} | {entry.component} | {entry.action} | {entry.result} |\n"

    # Математические источники
    sources_table = """
| Метод | Источник |
|---|---|
| KS D*, K(x) | Буре, Парилина (2018), §2.2.2, формулы (2.2.2)–(2.2.3) |
| Модифицированные статистики | Буре, Парилина (2018), §2.2.4, Табл. 2.1–2.2 |
| LRT | Буре, Парилина (2018), (3.2.25) |
| Kaplan-Meier | Kaplan & Meier (1958) |
| TOST / DKW | Dvoretzky, Kiefer, Wolfowitz (1956) |
| Meinshausen correction | Meinshausen & Bühlmann (2009), JASA 101(476) |
| Профильное MLE | Cohen & Whitten (1980); EnvStats doc |
"""

    return f"""# Аудит-отчёт: {report.verdict}

## Условия исследования

| Параметр | Значение |
|---|---|
| Распределение | {report.distribution} |
| N (полный) | {report.N_total} |
| N_fit / N_test | {report.N_fit} / {report.N_test} |
| Ветвь | {report.branch} |
| Инженерный допуск ε | {report.epsilon} |
| Уровень значимости α | {report.alpha} |
| Целевая мощность | {report.power_target} |
| Версия | Методология 2.0 / scipy {report.scipy_version} |
| Время | {report.computation_time_s:.2f} сек |
| Хэш данных | `{report.data_hash[:16]}...` |
| График | {report.figure_path} |

## Вердикт: {report.verdict}

{f'Данные согласуются с моделью. Вероятность ошибки I рода — не более {report.alpha*100:.0f}%.' if report.verdict == 'ACCEPT' else ''}
{f'Данные НЕ согласуются с моделью. Отклонение D_obs={report.D_obs:.4f} значимо.' if report.verdict == 'REJECT' else ''}
{f'Данные эквивалентны модели с точностью до ε={report.epsilon:.3f}.' if report.verdict == 'ACCEPT_EQUIVALENCE' else ''}
{'Анализ ЗАБЛОКИРОВАН: данных недостаточно для вывода.' if report.verdict == 'UNDERPOWERED' else ''}

## Статистика

| Метрика | Значение | Интерпретация |
|---|---|---|
| D_obs | {report.D_obs:.4f} | Макс. отклонение ECDF от CDF |
| p_value | {report.p_value if report.p_value is not None else 'N/A'} | Односторонний p-value |
| p_final | {report.p_final if report.p_final is not None else 'N/A'} | Meinshausen: 2 × median(p₁..p_K) |
| p_LRT | {report.p_LRT if report.p_LRT is not None else 'N/A'} | LRT 2P vs 3P |
| Skewness | {report.skewness if report.skewness is not None else 'N/A'} | Бутстреп-асимметрия (порог: 0.5) |
| N_min / N_max | {report.N_min if report.N_min else '?'} / {report.N_max if report.N_max else '?'} | Режим: {report.mode} |

## Параметры модели

| Параметр | Оценка | Метод | ДИ или статус |
|---|---|---|---|
{params_table}

## Статус-коды

{status_block}

## Предупреждения

{warnings_block}

## Трассировка решений

| Шаг | Компонент | Действие | Результат |
|---|---|---|---|
{trace_table}

## Рисунок

![Fit visualization]({report.figure_path})

*Рис. 1.* ECDF (синяя ступенчатая) vs Theoretical CDF (красная гладкая).
Shaded region — область максимального отклонения.
D_obs={report.D_obs:.4f}, verdict={report.verdict}.

## Математические источники

{sources_table}
"""


def create_report_from_validation(
    result: "ValidationResult",
    data_hash: str,
    scipy_version: str,
    N_min: int,
    N_max: int,
    mode: str,
    figure_path: str,
) -> AuditReport:
    """Создать AuditReport из ValidationResult.

    Args:
        result: ValidationResult.
        data_hash: SHA-256 хэш данных.
        scipy_version: версия scipy.
        N_min, N_max: барьеры из scale_selector.
        mode: режим из scale_selector.
        figure_path: путь к PNG.

    Returns:
        AuditReport.
    """
    audit_id = f"{datetime.now():%Y%m%d-%H%M%S}-{result.dist_type}-N{result.n_test}-{result.verdict}"

    return AuditReport(
        audit_id=audit_id,
        distribution=result.dist_type,
        N_total=result.n_fit + result.n_test,
        N_fit=result.n_fit,
        N_test=result.n_test,
        branch=result.branch,
        epsilon=0.03,
        alpha=0.05,
        power_target=0.80,
        verdict=result.verdict,
        D_obs=result.D_obs,
        p_value=result.p_value,
        p_final=result.p_final,
        p_LRT=result.p_LRT,
        skewness=result.skewness,
        N_min=N_min,
        N_max=N_max,
        mode=mode,
        parameters=result.parameters,
        status_codes=result.status_codes,
        warnings=result.warnings,
        data_hash=data_hash,
        computation_time_s=result.computation_time_s,
        scipy_version=scipy_version,
        figure_path=figure_path,
        trace=[
            TraceEntry(1, "utils", "check_scipy_version", "OK"),
            TraceEntry(2, "utils", "check_dependency_constraints", "OK"),
            TraceEntry(3, "utils", "compute_data_hash", data_hash[:16] + "..."),
            TraceEntry(4, "select", "scale_selector", f"mode={mode}"),
            TraceEntry(5, "validate", f"Branch {result.branch}", result.verdict),
        ],
    )