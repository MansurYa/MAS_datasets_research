"""ТЗ №4.8 Часть A — Извлечение ошибок из TRAIL."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
TRAIL_DIR = ROOT / "TRAIL"
DATA_DIR = ROOT / "data"

TRAIL_MAPPING = {
    "Context Handling Failures":          "kv_cache_loss",
    "Context Handling Failure":           "kv_cache_loss",
    "Resource Abuse":                    "resource_abuse",
    "Timeout Issues":                   "tool_timeout",
    "Service Errors":                   "system_failure",
    "Tool-related":                     "hallucination",
    "Language-only":                    "hallucination",
    "Language-Only":                    "hallucination",
    "Poor Information Retrieval":        "misinterpretation_of_tool_output",
    "Poor Information retrieval":         "misinterpretation_of_tool_output",
    "Tool Output Misinterpretation":    "misinterpretation_of_tool_output",
    "Formatting Errors":                "code_error",
    "Formatting Error":                  "code_error",
    "Instruction Non-compliance":       "instruction_adherence_failure",
    "Instruction non complience":        "instruction_adherence_failure",
    "Instruction Non-Compliance":       "instruction_adherence_failure",
    "Tool Definition Issues":           "invalid_invocation",
    "Environment Setup Errors":          "invalid_invocation",
    "Incorrect Problem Identification":  "orchestration_failure",
    " Incorrect Problem Identification": "orchestration_failure",
    "Tool Selection Errors":             "orchestration_failure",
    "Tool Selection":                    "orchestration_failure",
    "Goal Deviation":                   "orchestration_failure",
    "Goal deviation":                    "orchestration_failure",
    "Task Orchestration":               "orchestration_failure",
    "Task Orchestration Errors":          "orchestration_failure",
    "Task Orchestration Error":           "orchestration_failure",
    "Rate Limiting":                    "tool_web_failure",
    "Authentication Errors":             "tool_web_failure",
    "Resource Not Found":               "resource_not_found",
    "Resource Exhaustion":              "resource_abuse",
    "Incorrect Memory Usage":           "kv_cache_loss",
}


def flatten_spans(spans, counter=None):
    if counter is None:
        counter = [0]
    result = {}
    for span in spans:
        counter[0] += 1
        sid = span.get("span_id")
        if sid:
            result[sid] = counter[0]
        children = span.get("child_spans", [])
        if children:
            result.update(flatten_spans(children, counter))
    return result


def main():
    rows = []
    unknown_categories = set()
    skipped = 0

    for benchmark, ann_subdir, raw_subdir in [
        ("GAIA",     "processed_annotations_gaia",         "GAIA"),
        ("SWE-bench","processed_annotations_swe_bench",    "SWE Bench"),
    ]:
        ann_dir = TRAIL_DIR / ann_subdir
        raw_dir = TRAIL_DIR / raw_subdir
        ann_files = sorted(ann_dir.glob("*.json"))
        print(f"[{benchmark}] {len(ann_files)} annotation files")

        for ann_file in ann_files:
            trace_id = ann_file.stem
            try:
                with open(ann_file, encoding="utf-8") as f:
                    ann = json.load(f)
            except (json.JSONDecodeError, OSError) as ex:
                print(f"  Skipping {trace_id}: {ex}")
                skipped += 1
                continue

            raw_file = raw_dir / f"{trace_id}.json"
            if not raw_file.exists():
                continue

            with open(raw_file, encoding="utf-8") as f:
                raw = json.load(f)

            span_map = flatten_spans(raw.get("spans", []))
            traj_len = len(span_map)
            if traj_len == 0:
                continue

            errors = ann.get("errors", [])
            if not errors:
                rows.append({
                    "trajectory_id": trace_id,
                    "trail_category": "",
                    "error_id": "no_errors",
                    "error_step": None,
                    "trajectory_length": traj_len,
                    "normalized_position": None,
                    "impact": "",
                    "benchmark": benchmark,
                })
                continue

            for err in errors:
                category = err.get("category", "")
                location = err.get("location", "")
                impact = err.get("impact", "")
                error_id = TRAIL_MAPPING.get(category, "unknown")
                if error_id == "unknown":
                    unknown_categories.add(category)

                step = span_map.get(location)
                rows.append({
                    "trajectory_id": trace_id,
                    "trail_category": category,
                    "error_id": error_id,
                    "error_step": step,
                    "trajectory_length": traj_len,
                    "normalized_position": round(step / traj_len, 6) if step else None,
                    "impact": impact,
                    "benchmark": benchmark,
                })

        df = pd.DataFrame(rows)
    n_traj = df["trajectory_id"].nunique()
    n_errors = len(df[df["error_id"] != "no_errors"])
    df.to_csv(DATA_DIR / "trail_errors_v2.csv", index=False)
    print(f"\nSaved trail_errors_v2.csv: {n_traj} trajectories, {n_errors} errors (skipped: {skipped})")
    print(f"Category distribution:")
    print(df[df["error_id"] != "no_errors"]["error_id"].value_counts())
    if unknown_categories:
        print(f"\nUnknown categories: {unknown_categories}")

    return df


if __name__ == "__main__":
    main()
