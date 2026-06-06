"""Main entry point для distribution_validator.

CLI и полный pipeline: scale_selector → validate → plot → report.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import scipy

from . import (
    distributions,
    ecdf,
    goodness,
    profile_mle,
    select,
    utils,
    validate as validate_module,
    visualization,
    report as report_module,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main(
    X: np.ndarray,
    dist_type: str,
    event_mask: Optional[np.ndarray] = None,
    epsilon: float = 0.03,
    alpha: float = 0.05,
    power: float = 0.80,
    do_split: bool = True,
    B: int = 10000,
    seed: int = 42,
    data_hash: Optional[str] = None,
    save_artefacts: bool = True,
    study_label: Optional[str] = None,
    is_dedup: bool = False,
    study_dir: Optional[str] = None,
) -> tuple[validate_module.ValidationResult, str, str]:
    """Основной pipeline.

    1. check_scipy_version()
    2. check_dependency_constraints()
    3. compute_data_hash(X)
    4. scale_selector(X, epsilon, alpha, power) → mode
    5. Сплит если нужно → X_fit, X_test
    6. F_frozen = profile_mle(X_fit) если 3P иначе mle_2p(X_fit)
    7. validate(X_test, F_frozen, trained_on_same, N_max, event_mask, epsilon)
    8. plot_fit(report, F_frozen, X_test)
    9. generate_report(report, figure_path)
    10. Вернуть (ValidationResult, plot_path, md_path)

    Args:
        X: данные.
        dist_type: тип распределения (W2, W3, LN2, ...).
        event_mask: None или массив 0/1.
        epsilon: инженерный допуск.
        alpha: уровень значимости.
        power: целевая мощность.
        do_split: делать ли сплит 50/50.
        B: число бутстреп-итераций.
        seed: random seed.
        data_hash: хэш (опционально).

    Returns:
        (ValidationResult, plot_path, md_path).
    """
    # 1. Проверка scipy
    utils.check_scipy_version()
    logger.info(f"scipy version: {scipy.__version__}")

    # 2. Проверка зависимостей
    utils.check_dependency_constraints()

    # 3. Хэш
    if data_hash is None:
        data_hash = utils.compute_data_hash(X)
    logger.info(f"Data hash: {data_hash[:16]}...")

    # 4. scale_selector
    selector_result = select.scale_selector(X, epsilon, alpha, power)
    logger.info(f"Scale selector: mode={selector_result.mode}, N_min={selector_result.N_min}, N_max={selector_result.N_max}")

    # Режим UNDERPOWERED — останавливаемся, но генерируем PNG
    if selector_result.mode == select.MODE_UNDERPOWERED:
        result = validate_module.ValidationResult(
            verdict=validate_module.VERDICT_UNDERPOWERED,
            dist_type=dist_type,
            n_fit=0,
            n_test=len(X),
            branch="UNDERPOWERED",
            D_obs=0.0,
            warnings=selector_result.recommendations,
        )
        # Генерируем PNG даже для UNDERPOWERED (с watermark)
        plot_path = ""
        if save_artefacts and study_dir:
            try:
                params = distributions.mle_2p(X, dist_type, context="final")
                F_frozen = distributions.get_dist_instance(dist_type, params)
                output_path = Path(study_dir) / f"{dist_type}-{result.verdict}.png"
                plot_path = visualization.plot_fit(
                    result, F_frozen, X,
                    output_path=output_path,
                    study_label=study_label,
                    is_dedup=is_dedup,
                )
                logger.info(f"UNDERPOWERED plot saved: {plot_path}")
            except Exception as e:
                logger.warning(f"UNDERPOWERED plot failed: {e}")

        # Создаём минимальный отчёт
        from .report import AuditReport, create_report_from_validation
        report_obj = create_report_from_validation(
            result, data_hash, scipy.__version__,
            selector_result.N_min, selector_result.N_max,
            selector_result.mode, plot_path
        )
        if save_artefacts:
            report_module.save_report(report_obj, output_dir=Path(study_dir) if study_dir else None)
        dv_report_path = str(Path(study_dir) / f"dv_report-{report_obj.audit_id}.md") if study_dir else str(report_module.DOCS_DIR / f"dv_report-{report_obj.audit_id}.md")
        return result, plot_path, dv_report_path

    # 5. Сплит если нужно
    n = len(X)
    if do_split and selector_result.mode in (select.MODE_SPLIT_EXACT, select.MODE_BOOTSTRAP):
        rng = np.random.default_rng(seed)
        indices = rng.permutation(n)
        n_split = n // 2
        X_fit = X[indices[:n_split]]
        X_test = X[indices[n_split:]]
        trained_on_same = False
    else:
        X_fit = X
        X_test = X
        trained_on_same = True

    logger.info(f"Split: X_fit={len(X_fit)}, X_test={len(X_test)}, trained_on_same={trained_on_same}")

    # 6. Оценка параметров
    is_3p = dist_type in ("W3", "LN3", "G3", "LL3", "E2")

    if is_3p:
        profile_result = profile_mle.profile_mle_3p(X_fit, dist_type)
        params = profile_result.params_3p
        status_codes = profile_result.status_codes
        p_LRT = profile_result.p_LRT
        gamma = profile_result.gamma_final
    else:
        params = distributions.mle_2p(X_fit, dist_type, context="final")
        status_codes = []
        p_LRT = None
        gamma = params.gamma or 0.0

    # Создаём замороженное распределение
    F_frozen = distributions.get_dist_instance(dist_type, params)

    logger.info(f"Parameters: {params}")

    # 7. validate
    result = validate_module.validate(
        X_test, F_frozen, trained_on_same,
        selector_result.N_max,
        event_mask=event_mask,
        epsilon=epsilon,
        alpha=alpha,
        dist_type=dist_type,
        params=params,
        gamma=gamma,
        is_3p=is_3p,
        B=B,
        seed=seed,
    )
    result.status_codes = status_codes + result.status_codes
    if p_LRT is not None:
        result.p_LRT = p_LRT
    result.n_fit = len(X_fit)

    logger.info(f"Validation: verdict={result.verdict}, D_obs={result.D_obs:.4f}")

    # 8. plot
    if save_artefacts:
        try:
            # PNG сохраняется в директории исследования
            if study_dir:
                output_path = Path(study_dir) / f"{dist_type}-{result.verdict}.png"
            else:
                output_path = None
            plot_path = visualization.plot_fit(result, F_frozen, X_test, output_path=output_path, study_label=study_label, is_dedup=is_dedup)
            logger.info(f"Plot saved: {plot_path}")
        except Exception as e:
            logger.warning(f"Plot failed: {e}")
            plot_path = ""
    else:
        plot_path = ""

    # 9. report
    from .report import create_report_from_validation
    report_obj = create_report_from_validation(
        result, data_hash, scipy.__version__,
        selector_result.N_min, selector_result.N_max,
        selector_result.mode, plot_path,
    )
    if save_artefacts:
        md_path = report_module.save_report(report_obj, output_dir=Path(study_dir) if study_dir else None)
        logger.info(f"Report saved: {md_path}")
    else:
        md_path = ""

    return result, plot_path, str(md_path)


def run_cli():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Distribution Validator")
    parser.add_argument("--data", required=True, help="Path to CSV/Parquet file")
    parser.add_argument("--dist", required=True, help="Distribution type: W2, W3, LN2, ...")
    parser.add_argument("--epsilon", type=float, default=0.03, help="Engineering tolerance")
    parser.add_argument("--alpha", type=float, default=0.05, help="Significance level")
    parser.add_argument("--power", type=float, default=0.80, help="Target power")
    parser.add_argument("--fast", action="store_true", help="Fast mode (B=1000)")
    parser.add_argument("--event-col", type=str, help="Column name for event status")
    parser.add_argument("--time-col", type=str, help="Column name for time")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")

    args = parser.parse_args()

    # Загрузка данных
    path = Path(args.data)
    if path.suffix == ".csv":
        import pandas as pd
        df = pd.read_csv(path)
    elif path.suffix == ".parquet":
        import pandas as pd
        df = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    # Определяем X
    if args.time_col:
        X = df[args.time_col].values
        if args.event_col:
            event_mask = df[args.event_col].values
        else:
            event_mask = None
    else:
        # Первая колонка
        X = df.iloc[:, 0].values
        event_mask = None

    # Убираем NaN
    valid = ~np.isnan(X)
    X = X[valid]
    if event_mask is not None:
        event_mask = event_mask[valid]

    # Параметры
    B = 1000 if args.fast else 10000

    # Запуск
    result, plot_path, md_path = main(
        X, args.dist,
        event_mask=event_mask,
        epsilon=args.epsilon,
        alpha=args.alpha,
        power=args.power,
        do_split=True,
        B=B,
        seed=args.seed,
    )

    print(f"\n{'='*50}")
    print(f"Verdict: {result.verdict}")
    print(f"D_obs: {result.D_obs:.4f}")
    if result.p_value is not None:
        print(f"p_value: {result.p_value:.4f}")
    if result.p_final is not None:
        print(f"p_final: {result.p_final:.4f}")
    print(f"Report: {md_path}")
    if plot_path:
        print(f"Plot: {plot_path}")
    print(f"{'='*50}")


if __name__ == "__main__":
    run_cli()