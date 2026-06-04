# TZ_8.5 — Агрегация и анализ результатов

> **Назначение:** Преобразовать `results.csv` в человекочитаемые summary, диаграммы, таблицы.
>
> **Вход:** `work/MAS_errors/results.csv` (заполняется по мере выполнения исследований)
>
> **Выход:** Summary, диагностика, визуализация. Быстро.

---

## 1. Структура

```
work/MAS_errors/
├── results.csv                      ← вход
├── summary.py                       ← главный скрипт
├── aggregate.py                     ← утилиты агрегации
└── summaries/
    ├── summary_table.md            ← Markdown-таблица ACCEPT/REJECT/UNDERPOWERED
    ├── distribution_breakdown.md   ← какие распределения подошли
    └── diagnostics.md              ← проблемные исследования
```

---

## 2. aggregate.py — утилиты

```python
import pandas as pd
from pathlib import Path


def load_results(path: str = "work/MAS_errors/results.csv") -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"error_subtype": str})
    df["error_subtype"] = df["error_subtype"].fillna("")
    return df


def status_counts(df: pd.DataFrame) -> pd.DataFrame:
    """ACCEPT/REJECT/UNDERPOWERED count per dataset/error_type."""
    return (
        df.groupby(["dataset", "error_type", "status"])
        .size()
        .unstack(fill_value=0)
    )


def dataset_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Сводка по датасету: total studies, ACCEPT/REJECT/UNDERPOWERED counts, ACCEPT rate."""
    g = df.groupby("dataset")["status"].value_counts().unstack(fill_value=0)
    total = g.sum(axis=1)
    accept_rate = (g.get("ACCEPT", 0) / total * 100).round(1)
    return pd.concat([g, total.rename("total"), accept_rate.rename("accept_rate%")], axis=1)


def distribution_by_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Какие распределения ACCEPT для каждого датасета."""
    accept = df[df["status"] == "ACCEPT"]
    return (
        accept.groupby(["dataset", "error_type", "final_dist"])
        .size()
        .reset_index(name="count")
        .sort_values(["dataset", "count"], ascending=[True, False])
    )


def problem_studies(df: pd.DataFrame) -> pd.DataFrame:
    """Исследования с REJECT и их p_final."""
    reject = df[df["status"] == "REJECT"].copy()
    reject = reject.sort_values("p_final")
    return reject[["study_id", "dataset", "error_type", "n_errors", "p_final", "final_dist"]]
```

---

## 3. summary.py — главный выход

```python
#!/usr/bin/env python3
"""Генерирует все summary-файлы из results.csv."""

from pathlib import Path
from aggregate import load_results, status_counts, dataset_summary, distribution_by_dataset, problem_studies


OUT = Path("work/MAS_errors/summaries")
OUT.mkdir(parents=True, exist_ok=True)


def main():
    df = load_results()
    
    if len(df) == 0:
        print("results.csv пуст. Запустите run_all.py сначала.")
        return
    
    # === 1. summary_table.md ===
    with open(OUT / "summary_table.md", "w") as f:
        f.write("# Summary: Distribution Fit Validation\n\n")
        f.write(f"Total studies: {len(df)}\n\n")
        
        # Status by dataset
        f.write("## Status by Dataset\n\n")
        g = dataset_summary(df)
        f.write(g.to_markdown() + "\n\n")
        
        # ACCEPT rate per error type
        f.write("## ACCEPT Rate by Error Type\n\n")
        accept_by_type = (
            df.groupby(["dataset", "error_type"])["status"]
            .apply(lambda x: (x == "ACCEPT").mean() * 100)
            .round(1)
            .reset_index()
            .rename(columns={"status": "accept_rate%"})
        )
        f.write(accept_by_type.to_markdown(index=False) + "\n\n")
        
        # Breakdown by analysis_var
        f.write("## ACCEPT Rate by Analysis Variable\n\n")
        by_var = (
            df.groupby(["dataset", "analysis_var"])["status"]
            .apply(lambda x: (x == "ACCEPT").mean() * 100)
            .round(1)
            .reset_index()
            .rename(columns={"status": "accept_rate%"})
        )
        f.write(by_var.to_markdown(index=False) + "\n\n")
        
        # Dedup vs full
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
        
        dist_counts = accept["final_dist"].value_counts()
        f.write("## Best-Fit Distributions\n\n")
        f.write(dist_counts.to_markdown() + "\n\n")
        
        # Distribution by dataset
        f.write("## Distribution by Dataset\n\n")
        dist_by = distribution_by_dataset(accept)
        f.write(dist_by.to_markdown(index=False) + "\n\n")
    
    # === 3. diagnostics.md ===
    with open(OUT / "diagnostics.md", "w") as f:
        f.write("# Diagnostics\n\n")
        
        underpowered = df[df["status"] == "UNDERPOWERED"]
        f.write(f"## UNDERPOWERED: {len(underpowered)} studies\n\n")
        if len(underpowered) > 0:
            up_by_dataset = underpowered.groupby("dataset").size()
            f.write(up_by_dataset.to_markdown() + "\n\n")
        
        errors = df[df["status"] == "ERROR"]
        f.write(f"## ERROR: {len(errors)} studies\n\n")
        if len(errors) > 0:
            f.write(errors[["study_id", "error"]].to_markdown() + "\n\n")
        
        reject = problem_studies(df)
        f.write(f"## REJECT (best p-values): {len(reject)} studies\n\n")
        if len(reject) > 0:
            f.write(reject.head(20).to_markdown(index=False) + "\n\n")
    
    print(f"Summary written to {OUT}/")


if __name__ == "__main__":
    main()
```

---

## 4. Визуализация (опционально, простая)

```python
# visualize.py — bar chart ACCEPT/REJECT/UNDERPOWERED per dataset
import matplotlib.pyplot as plt

def plot_status_by_dataset(df: pd.DataFrame, path: str):
    counts = df.groupby(["dataset", "status"]).size().unstack(fill_value=0)
    counts.plot(kind="bar", figsize=(10, 6))
    plt.title("Distribution Fit Status by Dataset")
    plt.ylabel("Number of Studies")
    plt.tight_layout()
    plt.savefig(path)
```

---

## 5. Запуск

```bash
# Сгенерировать summary из текущего results.csv
.venv/bin/python work/MAS_errors/summary.py

# Просмотр
cat work/MAS_errors/summaries/summary_table.md
cat work/MAS_errors/summaries/distribution_breakdown.md
cat work/MAS_errors/summaries/diagnostics.md
```

---

## 6. Ожидаемые выходы

```
summaries/
├── summary_table.md        ← ACCEPT/REJECT/UNDERPOWERED по датасетам + error types
├── distribution_breakdown.md  ← какие распределения подошли (W2/LN3/G2/etc.)
└── diagnostics.md          ← UNDERPOWERED, ERROR, REJECT (с деталями)
```

---

<sub-instruction>

**ПЛАН РЕАЛИЗАЦИИ TZ_8.5:**

1. Показать план. Ждать аппрува.
2. aggregate.py — 5 утилит. Показать код + 3 теста.
3. summary.py — генерация 3 markdown-файлов. Показать код.
4. visualize.py — bar chart (опционально, быстро).
5. Демо на текущем results.csv (5 строк из демо TZ_8.4). Показать output.
6. Запустить полный прогон всех исследований (170 studies) → показать результаты summary.

**Принцип:** Быстро. Не переусложнять. Markdown + 1 chart.

</sub-instruction>