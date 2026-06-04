"""Генерация списка исследований из выходов парсеров."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

# Добавляем work/ в путь для импорта schemas из MAS_errors
_WORK_DIR = Path(__file__).resolve().parents[2] / ".."
if str(_WORK_DIR) not in sys.path:
    sys.path.insert(0, str(_WORK_DIR / "scripts"))

from work.MAS_errors.schemas import StudySpec
from work.MAS_errors.utils import filter_subgroup


PARSERS_ROOT = Path(__file__).resolve().parents[1] / "parsers"
RESULTS_DIR = Path(__file__).resolve().parents[1]

ANALYSIS_VAR_MAP = {
    "nebius": ["step_idx", "chars_before_error"],
    "trail": ["step_idx"],
    "agentRx": ["step_idx"],
    "who_and_when": ["step_idx"],
}

LARGE_PARQUET_THRESHOLD = 1000
SUBGROUPS_NEBIUS = ["all", "success_targetT", "success_targetF", "limit_hit", "failed"]


def make_study_id(
    dataset: str,
    error_type: str,
    error_subtype: str,
    is_dedup: bool,
    subgroup: str,
    analysis_var: str,
) -> str:
    parts = [dataset, error_type]
    if error_subtype and error_subtype not in ("", "all"):
        parts.append(error_subtype)
    if is_dedup:
        parts.append("dedup")
    parts.extend([subgroup, analysis_var])
    return "_".join(parts)


def _determine_subgroups(df: pd.DataFrame, dataset: str) -> list[str]:
    """Определить subgroups для данного parquet.

    nebius: если данных > threshold — добавить slices по exit_group.
    Остальные: всегда ["all"].
    """
    if dataset != "nebius":
        return ["all"]

    n = len(df)
    subgroups = ["all"]

    if n > LARGE_PARQUET_THRESHOLD:
        for sg in SUBGROUPS_NEBIUS:
            if sg == "all":
                continue
            try:
                filtered = filter_subgroup(df, sg)
                if len(filtered) >= 30:
                    subgroups.append(sg)
            except ValueError:
                pass

    return subgroups


def scan_parsers_output() -> list[StudySpec]:
    """Сканирует parsers/ и генерирует список StudySpec.

    Каждый errors.parquet может породить несколько StudySpec
    (subgroup × analysis_var).
    """
    studies: list[StudySpec] = []

    for parquet_path in sorted(PARSERS_ROOT.rglob("errors.parquet")):
        rel_parts = parquet_path.relative_to(PARSERS_ROOT).parts
        if len(rel_parts) < 2:
            continue

        dataset = rel_parts[0]
        if dataset not in ANALYSIS_VAR_MAP:
            continue

        # error_subtype и is_dedup из имени папки
        # TRAIL: rel_parts = [dataset, folder_name, "errors.parquet"]  — 3 элемента
        # nebius: rel_parts = [dataset, "invalid_invocation", folder_name, "errors.parquet"]  — 4 элемента
        # agentRx: rel_parts = [dataset, subdataset, folder_name, "errors.parquet"]  — 4 элемента
        if len(rel_parts) == 3:
            # TRAIL, Who_and_When: папка прямо в dataset (trail/category/errors.parquet)
            folder_name = rel_parts[1]
            error_type = rel_parts[0]  # dataset == error_type
            is_dedup = folder_name.endswith("_dedup")
            error_subtype = folder_name.replace("_dedup", "")
        else:
            # nebius, agentRx: dataset / error_type / folder_name / errors.parquet
            folder_name = rel_parts[2]
            error_type = rel_parts[1]
            is_dedup = folder_name.endswith("_dedup")
            error_subtype = folder_name.replace("_dedup", "")

        # subgroups и analysis_var
        available_vars = ANALYSIS_VAR_MAP[dataset]
        df_full = pd.read_parquet(parquet_path)
        subgroups = _determine_subgroups(df_full, dataset)

        for subgroup in subgroups:
            for analysis_var in available_vars:
                # Проверяем что в subgroup есть данные для analysis_var
                df_sg = filter_subgroup(df_full, subgroup)
                if len(df_sg) == 0:
                    continue
                if analysis_var not in df_sg.columns:
                    continue
                X = df_sg[analysis_var].dropna()
                if len(X) == 0:
                    continue

                study_id = make_study_id(
                    dataset, error_type, error_subtype,
                    is_dedup, subgroup, analysis_var,
                )

                studies.append(StudySpec(
                    study_id=study_id,
                    parquet_path=str(parquet_path),
                    dataset=dataset,
                    error_type=error_type,
                    error_subtype=error_subtype,
                    is_dedup=is_dedup,
                    subgroup=subgroup,
                    analysis_var=analysis_var,
                ))

    return studies


if __name__ == "__main__":
    studies = scan_parsers_output()
    print(f"Total studies: {len(studies)}")
    for s in studies[:10]:
        print(f"  {s.study_id}")
    if len(studies) > 10:
        print(f"  ... and {len(studies) - 10} more")