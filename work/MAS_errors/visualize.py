"""Визуализация результатов."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aggregate import load_results


def plot_status_by_dataset(df, path: str):
    counts = df.groupby(["dataset", "status"]).size().unstack(fill_value=0)
    counts.plot(kind="bar", figsize=(10, 6))
    plt.title("Distribution Fit Status by Dataset")
    plt.ylabel("Number of Studies")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path)
    plt.close()


def main():
    df = load_results(str(Path(__file__).resolve().parent / "results.csv"))
    out = Path(__file__).resolve().parent / "summaries"
    out.mkdir(parents=True, exist_ok=True)
    plot_status_by_dataset(df, str(out / "status_by_dataset.png"))
    print(f"Chart saved to {out}/status_by_dataset.png")


if __name__ == "__main__":
    main()
