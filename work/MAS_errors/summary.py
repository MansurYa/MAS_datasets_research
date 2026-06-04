#!/usr/bin/env python3
"""Генерирует все summary-файлы из results.csv."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggregate import load_results, dataset_summary, distribution_by_dataset, problem_studies

OUT = Path(__file__).resolve().parent / "summaries"
OUT.mkdir(parents=True, exist_ok=True)


def main():
    df = load_results(str(Path(__file__).resolve().parent / "results.csv"))

    if len(df) == 0:
        print("results.csv пуст. Запустите run_all.py сначала.")
        return

    # === 1. summary_table.md ===
    with open(OUT / "summary_table.md", "w") as f:
        f.write("# Summary: Distribution Fit Validation\n\n")
        f.write(f"Total studies: {len(df)}\n\n")

        f.write("## Status by Dataset\n\n")
        f.write(dataset_summary(df).to_markdown() + "\n\n")

        f.write("## ACCEPT Rate by Error Type\n\n")
        accept_by_type = (
            df.groupby(["dataset", "error_type"])["status"]
            .apply(lambda x: (x == "ACCEPT").mean() * 100)
            .round(1)
            .reset_index()
            .rename(columns={"status": "accept_rate%"})
        )
        f.write(accept_by_type.to_markdown(index=False) + "\n\n")

        f.write("## ACCEPT Rate by Analysis Variable\n\n")
        by_var = (
            df.groupby(["dataset", "analysis_var"])["status"]
            .apply(lambda x: (x == "ACCEPT").mean() * 100)
            .round(1)
            .reset_index()
            .rename(columns={"status": "accept_rate%"})
        )
        f.write(by_var.to_markdown(index=False) + "\n\n")

        f.write("## Dedup vs Full\n\n")
        dedup = df[df["is_dedup"] == True]
        full = df[df["is_dedup"] == False]
        f.write(f"- Full: {len(full)} studies, {(full['status']=='ACCEPT').mean()*100:.1f}% ACCEPT\n")
        f.write(f"- Dedup: {len(dedup)} studies, {(dedup['status']=='ACCEPT').mean()*100:.1f}% ACCEPT\n\n")

    # === 2. distribution_breakdown.md ===
    with open(OUT / "distribution_breakdown.md", "w") as f:
        f.write("# Distribution Breakdown\n\n")

        accept = df[df["status"] == "ACCEPT"]
        f.write(f"ACCEPT: {len(accept)} / {len(df)} ({len(accept)/len(df)*100:.1f}%)\n\n")

        f.write("## Best-Fit Distributions\n\n")
        f.write(accept["final_dist"].value_counts().to_markdown() + "\n\n")

        f.write("## Distribution by Dataset\n\n")
        f.write(distribution_by_dataset(df).to_markdown(index=False) + "\n\n")

    # === 3. diagnostics.md ===
    with open(OUT / "diagnostics.md", "w") as f:
        f.write("# Diagnostics\n\n")

        underpowered = df[df["status"] == "UNDERPOWERED"]
        f.write(f"## UNDERPOWERED: {len(underpowered)} studies\n\n")
        if len(underpowered) > 0:
            f.write(underpowered.groupby("dataset").size().to_markdown() + "\n\n")

        errors = df[df["status"] == "ERROR"]
        f.write(f"## ERROR: {len(errors)} studies\n\n")
        if len(errors) > 0:
            f.write(errors[["study_id", "dataset"]].to_markdown(index=False) + "\n\n")

        reject = problem_studies(df)
        f.write(f"## REJECT: {len(reject)} studies\n\n")
        if len(reject) > 0:
            f.write(reject.head(20).to_markdown(index=False) + "\n\n")

    print(f"Summary written to {OUT}/")


if __name__ == "__main__":
    main()
