"""ТЗ №4.8 Часть B — Who&When только Hand-Crafted."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
from pathlib import Path
import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
WW_DIR = ROOT / "Kevin355-Who_and_When"
DATA_DIR = ROOT / "data"

KEYWORD_RULES = [
    ("hallucination",         ["hallucinate", "fabricat", "made up", "assumes the existence", "placeholder"]),
    ("resource_abuse",        ["exhaustion of the step limits", "step limit", "too many steps", "repeatedly"]),
    ("orchestration_failure", ["orchestrator", "replan", "wrong direction", "should not decide", "should instruct"]),
    ("tool_web_failure",      ["failed to access", "404", " retrieve", "websurfer", "filesurfer",
                               "could not access", "not found", "url", "cloudflare"]),
    ("code_error",            ["code is incorrect", "code is wrong", "python code", "incorrect code",
                               "code provided", " bug ", "syntax", "the code is"]),
    ("factual_error",         ["factual error", "incorrect information", "incorrect assumption",
                               "incorrect fact", "wrong answer"]),
    ("misinterpretation",     ["misinterpret", "misidentif", "incorrect interpretation", "wrong interpretation"]),
]


def classify_text(text: str) -> str:
    if not isinstance(text, str):
        return "unclassified"
    t = text.lower()
    for cat, kws in KEYWORD_RULES:
        if any(kw in t for kw in kws):
            return cat
    return "unclassified"


def main():
    df = pd.read_parquet(WW_DIR / "Hand-Crafted.parquet")
    print(f"Hand-Crafted records: {len(df)}")
    print(f"Columns: {list(df.columns)}")

    rows = []
    for _, row in df.iterrows():
        reason = row.get("mistake_reason")
        step_raw = row.get("mistake_step")
        try:
            step = int(step_raw) if step_raw is not None else None
        except (ValueError, TypeError):
            step = None
        hist = row.get("history")
        traj_len = len(hist) if hist is not None else 0
        rows.append({
            "source": "who_and_when_hc",
            "trajectory_id": row.get("question_ID", ""),
            "category_original": reason if isinstance(reason, str) else "",
            "category_unified": classify_text(reason),
            "step_number": step,
            "trajectory_length": traj_len,
            "text_snippet": (reason[:100] if isinstance(reason, str) else ""),
        })

    out = pd.DataFrame(rows)
    out.to_csv(DATA_DIR / "who_and_when_handcrafted_classified.csv", index=False)
    print(f"Saved who_and_when_handcrafted_classified.csv: {len(out)} rows")
    print(f"Category distribution:\n{out['category_unified'].value_counts()}")
    print(f"Total steps: {out['trajectory_length'].sum()}")


if __name__ == "__main__":
    main()
