from __future__ import annotations

import dataclasses
import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

from work.MAS_errors.schemas import ErrorRecord, ErrorStats
from work.MAS_errors.utils import EXIT_GROUP_MAP, data_hash, records_to_df, wilson_ci

PROJECT_ROOT = Path(__file__).parents[5]
PARQUET_DIR = PROJECT_ROOT / "datasets" / "nebius-SWE-agent-trajectories" / "data"
OUT_BASE = Path(__file__).parent

N_TOTAL = 80_036

EDIT_HEADER = "Your proposed edit has introduced new syntax error"
ERRORS_BLOCK_RE = re.compile(r"ERRORS:\s*\n((?:- .*\n?)+)", re.MULTILINE)
ERROR_LINE_RE = re.compile(r"^- (E\d+|F\d+|W\d+)\s+(.*)$")
EDIT_BLOCK_RE = re.compile(
    r"This is how your edit would have looked if applied\s*\n[-]+\s*\n(.*?)\n[-]+",
    re.DOTALL,
)


def normalize_error_pattern(text: str) -> str:
    t = re.split(r"\(Open file:|\(Current directory:|bash-\$", text)[0]
    t = re.sub(r"'[^']{0,200}'", "'X'", t)
    t = re.sub(r'"[^"]{0,200}"', '"X"', t)
    t = re.sub(r"/[\w\-./]+", "/X", t)
    t = re.sub(r"\bline\s+\d+", "line N", t, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", t).strip()


def matches_A(text: str) -> bool:
    if "FileNotFoundError" not in text and "No such file or directory" not in text:
        return False
    if re.search(r"\bline\s+\d+", text, re.IGNORECASE):
        return False
    if "ModuleNotFoundError" in text or "ImportError" in text:
        return False
    if "pytest" in text or "fixture" in text:
        return False
    return True


def matches_B(text: str) -> bool:
    if not ("command not found" in text or "cannot access" in text or "cannot stat" in text):
        return False
    if "ls: cannot access" in text:
        return False
    if "SyntaxError" in text or "syntax error" in text:
        return False
    if "grep" in text and ("pattern" in text or "search" in text):
        return False
    if "python" in text.lower() and "not found" in text:
        return False
    if "```" in text:
        return False
    return True


def matches_E(text: str) -> bool:
    return EDIT_HEADER in text


def parse_edit_errors(text: str) -> list[tuple[str, str]]:
    m = ERRORS_BLOCK_RE.search(text)
    if not m:
        return []
    out = []
    for line in m.group(1).splitlines():
        em = ERROR_LINE_RE.match(line.strip())
        if em:
            out.append((em.group(1), em.group(2)))
    return out


def _extract_edit_block(text: str) -> str:
    m = EDIT_BLOCK_RE.search(text)
    return m.group(1) if m else ""


def _has_import(edit_block: str, name: str) -> bool:
    if not edit_block:
        return False
    pat_mod = re.compile(rf"^\s*\d*:?\s*import\s+{re.escape(name)}\b", re.MULTILINE)
    pat_from = re.compile(rf"^\s*\d*:?\s*from\s+\S+\s+import\s+.*\b{re.escape(name)}\b", re.MULTILINE)
    return bool(pat_mod.search(edit_block) or pat_from.search(edit_block))


def process_trajectories() -> dict[str, list[ErrorRecord]]:
    print("Загружаю датасет...")
    dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
    d = dataset.to_table().to_pydict()

    instance_ids = d["instance_id"]
    trajectories = d["trajectory"]
    exit_statuses = d["exit_status"]
    targets = d["target"]

    print(f"Загружено траекторий: {len(instance_ids)}")

    first_occurrence: dict[str, int] = {}
    for row_idx, inst in enumerate(instance_ids):
        if inst not in first_occurrence:
            first_occurrence[inst] = row_idx

    A_records: list[ErrorRecord] = []
    B_records: list[ErrorRecord] = []
    E1_records: list[ErrorRecord] = []
    E2_records: list[ErrorRecord] = []

    occ_counters: dict[tuple, int] = defaultdict(int)

    total = len(instance_ids)
    for row_idx in range(total):
        inst = instance_ids[row_idx]
        traj = trajectories[row_idx]
        exit_s = exit_statuses[row_idx]
        target = targets[row_idx]
        exit_group = EXIT_GROUP_MAP.get(exit_s)

        global_traj_idx = row_idx

        traj_total_chars = sum(
            len(s.get("text") or "") + len(s.get("system_prompt") or "")
            for s in traj
        )
        traj_total_steps = len(traj)
        running_chars = 0

        step_seen: set = set()

        for step_idx, step in enumerate(traj):
            if not isinstance(step, dict):
                continue
            text = step.get("text")
            if not text:
                running_chars += len(step.get("system_prompt") or "")
                continue

            base = dict(
                dataset="nebius",
                error_type="invalid_invocation",
                is_dedup=False,
                instance_id=inst,
                traj_idx=global_traj_idx,
                step_idx=step_idx,
                chars_before_error=running_chars,
                traj_total_chars=traj_total_chars,
                traj_total_steps=traj_total_steps,
                target=bool(target) if target is not None else None,
                exit_group=exit_group,
                exit_status=exit_s,
            )

            if matches_A(text):
                pat = normalize_error_pattern(text)
                key = (inst, global_traj_idx, pat)
                occ_counters[key] += 1
                occ = occ_counters[key]
                A_records.append(ErrorRecord(
                    **base,
                    error_subtype="A",
                    error_id=f"nebius_A_{global_traj_idx}_{step_idx}_{occ}",
                    error_text=text,
                    normalized_pattern=pat,
                    occurrence_in_traj=occ,
                ))

            if matches_B(text):
                pat = normalize_error_pattern(text)
                key = (inst, global_traj_idx, pat)
                occ_counters[key] += 1
                occ = occ_counters[key]
                B_records.append(ErrorRecord(
                    **base,
                    error_subtype="B",
                    error_id=f"nebius_B_{global_traj_idx}_{step_idx}_{occ}",
                    error_text=text,
                    normalized_pattern=pat,
                    occurrence_in_traj=occ,
                ))

            if matches_E(text):
                errors = parse_edit_errors(text)
                if errors:
                    edit_block = _extract_edit_block(text)
                    e_base = {**base, "exit_status": None, "exit_group": EXIT_GROUP_MAP.get(exit_s)}

                    for code, msg in errors:
                        if code == "E999":
                            pat = normalize_error_pattern(msg)
                            step_key = ("E999", pat)
                            if step_key in step_seen:
                                continue
                            step_seen.add(step_key)
                            key = (inst, global_traj_idx, pat)
                            occ_counters[key] += 1
                            occ = occ_counters[key]
                            E1_records.append(ErrorRecord(
                                **e_base,
                                error_subtype="E1",
                                error_id=f"nebius_E1_{global_traj_idx}_{step_idx}_{occ}",
                                error_text="",
                                normalized_pattern=pat,
                                occurrence_in_traj=occ,
                                error_code=code,
                                error_msg=msg,
                            ))

                        elif code == "F821":
                            pat = normalize_error_pattern(msg)
                            step_key = ("F821", pat)
                            if step_key in step_seen:
                                continue
                            step_seen.add(step_key)
                            key = (inst, global_traj_idx, pat)
                            occ_counters[key] += 1
                            occ = occ_counters[key]
                            nm = re.search(r"undefined name '([^']+)'", msg)
                            name = nm.group(1) if nm else None
                            imp = _has_import(edit_block, name) if name else None
                            E2_records.append(ErrorRecord(
                                **e_base,
                                error_subtype="E2",
                                error_id=f"nebius_E2_{global_traj_idx}_{step_idx}_{occ}",
                                error_text="",
                                normalized_pattern=pat,
                                occurrence_in_traj=occ,
                                error_code=code,
                                error_msg=msg,
                                undefined_name=name,
                                import_present_in_edit=imp,
                            ))

            running_chars += len(text) + len(step.get("system_prompt") or "")

        if (row_idx + 1) % 10_000 == 0:
            print(f"  {row_idx + 1}/{total}")

    return {"A": A_records, "B": B_records, "E1": E1_records, "E2": E2_records}


def _mark_dedup(df: pd.DataFrame) -> pd.DataFrame:
    seen: set = set()
    mask = []
    for _, row in df.iterrows():
        key = (row["instance_id"], row["traj_idx"], row["normalized_pattern"])
        mask.append(key not in seen)
        seen.add(key)
    df = df[mask].copy()
    df["is_dedup"] = True
    return df


def compute_stats(df: pd.DataFrame, subtype: str | None, is_dedup: bool) -> ErrorStats:
    n_errors = len(df)
    n_with = df["instance_id"].nunique()
    p_traj, ci_lo, ci_hi = wilson_ci(n_with, N_TOTAL)
    total_steps = int(df["traj_total_steps"].sum())
    p_step = n_errors / total_steps if total_steps > 0 else 0.0

    return ErrorStats(
        dataset="nebius",
        error_type="invalid_invocation",
        error_subtype=subtype,
        is_dedup=is_dedup,
        n_errors=n_errors,
        n_trajectories_total=N_TOTAL,
        n_trajectories_with_error=n_with,
        p_trajectory=p_traj,
        p_trajectory_ci_lower=ci_lo,
        p_trajectory_ci_upper=ci_hi,
        p_per_step=p_step,
        step_mean=float(df["step_idx"].mean()),
        step_median=float(df["step_idx"].median()),
        step_std=float(df["step_idx"].std()),
        chars_mean=float(df["chars_before_error"].mean()),
        chars_median=float(df["chars_before_error"].median()),
        target_true_n=int(df["target"].eq(True).sum()),
        target_false_n=int(df["target"].eq(False).sum()),
        exit_success_n=int((df["exit_group"] == "success").sum()),
        exit_limit_hit_n=int((df["exit_group"] == "limit_hit").sum()),
        exit_failed_n=int((df["exit_group"] == "failed").sum()),
        data_hash=data_hash(df["step_idx"].values),
        parser_version="TZ_8.2",
    )


def _save(df: pd.DataFrame, subtype: str | None, is_dedup: bool) -> None:
    suffix = f"{subtype or 'ALL'}" + ("_dedup" if is_dedup else "")
    out_dir = OUT_BASE / suffix
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "errors.parquet", index=False)
    stats = compute_stats(df, subtype, is_dedup)
    (out_dir / "stats.json").write_text(
        json.dumps(dataclasses.asdict(stats), indent=2), encoding="utf-8"
    )
    print(f"  {suffix}: {len(df)} записей → {out_dir}")


def run() -> None:
    by_cat = process_trajectories()

    dfs: dict[str, pd.DataFrame] = {}
    for cat, records in by_cat.items():
        dfs[cat] = records_to_df(records)

    df_ALL = pd.concat(list(dfs.values()), ignore_index=True)

    dedup: dict[str, pd.DataFrame] = {cat: _mark_dedup(df) for cat, df in dfs.items()}
    df_ALL_dedup = pd.concat(list(dedup.values()), ignore_index=True)

    print("\nСохраняю...")
    for cat, df in dfs.items():
        _save(df, cat, is_dedup=False)
        _save(dedup[cat], cat, is_dedup=True)

    _save(df_ALL, None, is_dedup=False)
    _save(df_ALL_dedup, None, is_dedup=True)

    print("\nГотово.")
    for cat in ["A", "B", "E1", "E2"]:
        print(f"  {cat}: full={len(dfs[cat])}, dedup={len(dedup[cat])}")
    print(f"  ALL: full={len(df_ALL)}, dedup={len(df_ALL_dedup)}")


if __name__ == "__main__":
    run()
