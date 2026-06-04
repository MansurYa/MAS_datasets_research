"""Главная точка входа: запуск всех исследований."""

from __future__ import annotations

import sys
import dataclasses
import logging
from pathlib import Path

import pandas as pd

_PROJECT_ROOT = Path(__file__).resolve().parents[2] / ".."
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT / "scripts"))

from work.MAS_errors.schemas import StudyResult
from work.MAS_errors.study_runner.generate_study_list import scan_parsers_output
from work.MAS_errors.study_runner.run_study import run_study, save_artefacts
from work.MAS_errors.setup_logging import setup_logging


RESULTS_DIR = Path(__file__).resolve().parents[1]
RESULTS_CSV = RESULTS_DIR / "results.csv"

ROW_FIELDS = [
    "study_id", "dataset", "error_type", "error_subtype", "is_dedup",
    "subgroup", "analysis_var", "n_errors", "status", "final_dist",
    "p_final", "D_obs", "n_attempts", "duration_s", "data_hash",
]


def _append_to_csv(result: StudyResult, path: Path) -> None:
    """Атомарная запись: writer header в новый файл, append row в существующий."""
    row = dataclasses.asdict(result)
    df_row = pd.DataFrame([row], columns=ROW_FIELDS)

    file_exists = path.exists()
    mode = 'a' if file_exists else 'w'
    header = False if file_exists else True

    with open(path, mode, newline="") as f:
        df_row.to_csv(f, header=header, index=False)


def main(fast: bool = False, limit: int | None = None) -> None:
    logger = setup_logging()
    logger.info("=== Study Runner started ===")

    # Генерировать список исследований
    logger.info("Generating study list...")
    studies = scan_parsers_output()
    logger.info(f"Total studies: {len(studies)}")

    if limit:
        studies = studies[:limit]
        logger.info(f"Running only first {limit} studies")

    # Очистить старый results.csv
    if RESULTS_CSV.exists():
        RESULTS_CSV.unlink()

    results = []

    # tqdm уже импортирован в setup_logging
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
    logger.info("=== Study Runner finished ===")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Study Runner")
    parser.add_argument("--fast", action="store_true", help="Использовать B=500 вместо B=1000")
    parser.add_argument("--limit", type=int, default=None, help="Ограничить число исследований")
    args = parser.parse_args()

    main(fast=args.fast, limit=args.limit)