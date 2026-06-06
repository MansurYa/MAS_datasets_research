"""Главная точка входа: запуск всех исследований."""

from __future__ import annotations

import sys
import dataclasses
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2] / ".."
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from work.MAS_errors.schemas import StudySpec, StudyResult
from work.MAS_errors.study_runner.generate_study_list import scan_parsers_output
from work.MAS_errors.study_runner.run_study import run_study, save_artefacts
from work.MAS_errors.setup_logging import setup_logging


RESULTS_DIR = Path(__file__).resolve().parents[1]
RESULTS_CSV = RESULTS_DIR / "results.csv"

ROW_FIELDS = [
    "study_id", "dataset", "error_type", "error_subtype", "is_dedup",
    "subgroup", "analysis_var", "n_errors", "status", "final_dist",
    "p_final", "D_obs", "n_attempts", "duration_s", "data_hash",
    # ValidationResult fields
    "branch", "p_value", "p_LRT", "skewness", "parameters",
    # ScaleSelectorResult fields
    "N_min", "N_max", "scale_mode",
]


def _generate_html_after_run(logger: logging.Logger) -> None:
    try:
        from work.MAS_errors.html_report import generate_html_report
        html_path = generate_html_report()
        logger.info(f"HTML report: {html_path}")
    except Exception as e:
        logger.warning(f"HTML generation failed: {e}")


def _append_to_csv(result: StudyResult, path: Path) -> None:
    """Атомарная запись: writer header в новый файл, append row в существующий."""
    row = dataclasses.asdict(result)
    df_row = pd.DataFrame([row], columns=ROW_FIELDS)

    file_exists = path.exists()
    mode = 'a' if file_exists else 'w'
    header = False if file_exists else True

    with open(path, mode, newline="") as f:
        df_row.to_csv(f, header=header, index=False)


# === Parallel support ===


def _worker_init() -> None:
    """Инициализация worker-subprocess.

    Вызывается один раз при создании каждого worker process.
    ВАЖНО: dv_main (и matplotlib) импортируются лениво внутри run_study(),
    поэтому matplotlib.use('Agg') здесь гарантированно выполнится раньше.
    Если import dv_main переедет на module-level — этот init перестанет работать.
    """
    import matplotlib
    matplotlib.use('Agg')
    root = logging.getLogger()
    root.handlers = [h for h in root.handlers if not isinstance(h, logging.FileHandler)]


def _worker_fn(spec: StudySpec, fast: bool) -> StudyResult:
    """Выполнить одно исследование в subprocess."""
    result = run_study(spec, fast=fast)
    save_artefacts(spec, result)
    return result


def _run_parallel(studies: list[StudySpec], fast: bool, workers: int) -> None:
    """Параллельный запуск исследований."""
    logger = setup_logging()
    logger.info(f"=== Parallel mode: {workers} workers ===")

    studies_sorted = sorted(
        studies,
        key=lambda s: Path(s.parquet_path).stat().st_size,
        reverse=True,
    )

    results: list[StudyResult] = []
    failed: list[str] = []

    from tqdm import tqdm

    with ProcessPoolExecutor(max_workers=workers, initializer=_worker_init) as executor:
        futures = {
            executor.submit(_worker_fn, spec, fast): spec
            for spec in studies_sorted
        }
        for future in tqdm(as_completed(futures), total=len(futures),
                           desc="Studies (parallel)", unit="study"):
            spec = futures[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Study {spec.study_id} failed: {e}")
                failed.append(spec.study_id)

    # CSV — один раз, детерминированный порядок
    results.sort(key=lambda r: r.study_id)
    if RESULTS_CSV.exists():
        RESULTS_CSV.unlink()
    if results:
        df = pd.DataFrame([dataclasses.asdict(r) for r in results], columns=ROW_FIELDS)
        df.to_csv(RESULTS_CSV, index=False)

    # Summary
    if results:
        statuses = pd.Series([r.status for r in results]).value_counts()
        logger.info(f"Results: {statuses.to_dict()}")
    if failed:
        logger.warning(f"Failed studies ({len(failed)}): {failed}")
    logger.info(f"Results saved to: {RESULTS_CSV}")
    _generate_html_after_run(logger)
    logger.info("=== Study Runner finished ===")


# === Main (sequential path unchanged) ===


def main(fast: bool = False, limit: int | None = None, parallel: int = 0) -> None:
    logger = setup_logging()
    logger.info("=== Study Runner started ===")

    # Генерировать список исследований
    logger.info("Generating study list...")
    studies = scan_parsers_output()
    logger.info(f"Total studies: {len(studies)}")

    if limit:
        studies = studies[:limit]
        logger.info(f"Running only first {limit} studies")

    # Параллельный путь — полностью отдельная ветка
    if parallel > 0:
        _run_parallel(studies, fast, parallel)
        return

    # === Sequential path (оригинальный код без изменений) ===
    # Очистить старый results.csv
    if RESULTS_CSV.exists():
        RESULTS_CSV.unlink()

    results = []

    from tqdm import tqdm

    for spec in tqdm(studies, desc="Studies", unit="study"):
        result = run_study(spec, fast=fast)
        results.append(result)

        # Сохранить артефакты
        save_artefacts(spec, result)

        # Атомарная запись в results.csv
        _append_to_csv(result, RESULTS_CSV)

    # Summary
    statuses = pd.Series([r.status for r in results]).value_counts()
    logger.info(f"Results: {statuses.to_dict()}")

    logger.info(f"Results saved to: {RESULTS_CSV}")
    _generate_html_after_run(logger)
    logger.info("=== Study Runner finished ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Study Runner")
    parser.add_argument("--fast", action="store_true", help="Использовать B=500 вместо B=1000")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить число исследований")
    parser.add_argument("--parallel", type=int, default=0,
                        help="Число параллельных воркеров (0 = sequential, default)")
    args = parser.parse_args()

    main(fast=args.fast, limit=args.limit, parallel=args.parallel)
