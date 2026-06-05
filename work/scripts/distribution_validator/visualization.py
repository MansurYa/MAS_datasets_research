"""Визуализация: один PNG с ECDF + CDF + PDF.

Реализация согласно МЕТОДОЛОГИЯ-2.0, секция 12.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from scipy import stats

from .utils import PLOTS_DIR

DIST_FULL_NAME = {
    "W2": "Weibull (2P)", "W3": "Weibull (3P)",
    "LN2": "Log-Normal (2P)", "LN3": "Log-Normal (3P)",
    "G2": "Gamma (2P)", "G3": "Gamma (3P)",
    "LL2": "Log-Logistic (2P)", "LL3": "Log-Logistic (3P)",
    "E1": "Exponential (1P)", "E2": "Exponential (2P)",
    "N": "Normal", "GU": "Gumbel",
}


def plot_fit(
    report: "ValidationResult",
    F_frozen: object,
    X_test: np.ndarray,
    output_path: str | None = None,
    study_label: str | None = None,
) -> str:
    """Генерация визуализации согласия.

    Одна панель:
    - ECDF (step, синяя) + Theoretical CDF (smooth, красная) + PDF overlay
    - Shaded diff region — только если D_obs > 0.01
    - Max deviation line + annotation с цветовым кодом вердикта
    - Для 3P: вертикальная линия γ̂
    - Для TOST: ε-полоса (CDF ± ε)
    - Цветовой код: ACCEPT=зелёный, REJECT=красный,
      ACCEPT_EQUIVALENCE=жёлтый, UNDERPOWERED=голубой

    Args:
        report: ValidationResult.
        F_frozen: замороженное распределение.
        X_test: тестовые данные.
        output_path: путь для сохранения PNG.

    Returns:
        Путь к сохранённому файлу.
    """
    X_test = np.asarray(X_test).flatten()
    X_test = X_test[~np.isnan(X_test)]

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)

    # === ECDF ===
    ecdf_result = stats.ecdf(X_test)
    # scipy.stats.ecdf returns ECDFResult with .cdf being EmpiricalDistributionFunction
    # Access quantiles/probabilities via .cdf.quantiles and .cdf.probabilities
    if hasattr(ecdf_result.cdf, 'quantiles') and hasattr(ecdf_result.cdf, 'probabilities'):
        ecdf_x = ecdf_result.cdf.quantiles
        ecdf_p = ecdf_result.cdf.probabilities
    else:
        # Fallback: extract from EmpiricalDistributionFunction
        ecdf_x = np.sort(X_test)
        n = len(ecdf_x)
        ecdf_p = np.arange(1, n + 1) / n

    ax.step(
        ecdf_x, ecdf_p,
        where='post', color='tab:blue', linewidth=1.5,
        label='ECDF'
    )

    # === Theoretical CDF + PDF ===
    x_range = np.linspace(
        X_test.min() * 0.5, X_test.max() * 1.5, 1000
    )
    cdf_y = F_frozen.cdf(x_range)
    try:
        pdf_y = F_frozen.pdf(x_range)
    except Exception:
        pdf_y = np.ones_like(x_range) * 0.001

    ax.plot(
        x_range, cdf_y,
        color='tab:red', linewidth=2,
        label=f'{report.dist_type} CDF'
    )

    # PDF overlay (scaled)
    if np.isfinite(pdf_y).all() and pdf_y.max() > 0:
        pdf_scaled = pdf_y / pdf_y.max() * 0.95
        ax.fill_between(
            x_range, pdf_scaled,
            alpha=0.15, color='tab:red',
            label='Fitted PDF (scaled)'
        )

    # === Shaded deviation (если D_obs > 0.01) ===
    if report.D_obs > 0.01:
        ecdf_interp = np.interp(x_range, ecdf_x, ecdf_p)
        diff = np.abs(ecdf_interp - cdf_y)
        ax.fill_between(
            x_range, cdf_y - diff, cdf_y + diff,
            alpha=0.1, color='tab:orange',
            label=f'|ECDF–CDF|'
        )

    # === Max deviation marker ===
    ecdf_interp = np.interp(x_range, ecdf_x, ecdf_p)
    diff = np.abs(ecdf_interp - cdf_y)
    max_idx = np.argmax(diff)
    ax.axvline(
        x=x_range[max_idx], color='gray',
        linestyle='--', alpha=0.5, linewidth=1
    )

    # === Annotation с цветовым кодом ===
    verdict_colors = {
        'ACCEPT': '#d4edda',
        'REJECT': '#f8d7da',
        'ACCEPT_EQUIVALENCE': '#fff3cd',
        'REJECT_EQUIVALENCE': '#f8d7da',
        'UNDERPOWERED': '#d1ecf1'
    }
    bg = verdict_colors.get(report.verdict, '#ffffff')

    annotation_lines = [
        f"D_obs = {report.D_obs:.4f}",
        f"verdict = {report.verdict}",
    ]
    if report.p_value is not None:
        annotation_lines.append(f"p = {report.p_value:.3f}")
    if report.p_final is not None:
        annotation_lines.append(f"p_final = {report.p_final:.3f}")

    annotation = '\n'.join(annotation_lines)
    ax.text(
        0.98, 0.98, annotation,
        transform=ax.transAxes, fontsize=9,
        ha='right', va='top',
        bbox=dict(boxstyle='round', facecolor=bg, alpha=0.9)
    )

    # === 3P: threshold γ ===
    gamma = report.parameters.get('gamma', None)
    if gamma is not None and gamma > 0:
        ax.axvline(
            x=gamma, color='tab:orange', linestyle='--',
            linewidth=1.5, label=f'γ̂={gamma:.0f}'
        )

    # === TOST: ε-band ===
    if report.branch == 'C_TOST':
        from .select import compute_N_max, adaptive_xi
        xi = adaptive_xi(X_test)
        N_max = compute_N_max(xi)
        epsilon = 0.03  # Из report или по умолчанию
        ax.fill_between(
            x_range,
            np.maximum(0, cdf_y - epsilon),
            np.minimum(1, cdf_y + epsilon),
            alpha=0.1, color='tab:green',
            label=f'ε-band (ε={epsilon})'
        )

    # === Оси и легенда ===
    ax.set_xlabel('x', fontsize=11)
    ax.set_ylabel('Cumulative probability', fontsize=11)

    dist_full = DIST_FULL_NAME.get(report.dist_type, report.dist_type)
    params = report.parameters or {}
    param_str = "  ".join(
        f"{k}={v:.3g}" for k, v in params.items()
        if v is not None and k not in ("gamma",)
    )
    if params.get("gamma"):
        param_str += f"  γ={params['gamma']:.3g}"

    title_line1 = study_label if study_label else ""
    title_line2 = f"{dist_full}  [{param_str}]  ·  N={report.n_test}  ·  {report.verdict}"
    full_title = f"{title_line1}\n{title_line2}" if title_line1 else title_line2

    ax.set_title(full_title, fontsize=11, fontweight='bold', linespacing=1.5)
    ax.legend(fontsize=9, loc='upper left')

    # === Сохранение ===
    if output_path is None:
        audit_id = f"audit-{report.dist_type}-N{report.n_test}-{report.verdict}"
        output_path = PLOTS_DIR / f"{audit_id}.png"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)

    return str(output_path)