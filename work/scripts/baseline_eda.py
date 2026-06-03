#!/usr/bin/env python3
"""
Baseline EDA для датасета nebius/SWE-agent-trajectories (TZ_3).

Скрипт проходит 12 шардов parquet итеративно (через pyarrow.dataset),
для каждой траектории считает две длины:
  - n_steps  — количество шагов в trajectory (включая system-шаг)
  - n_chars  — суммарная длина в символах (text + system_prompt)

Параллельно классифицирует exit_status в три группы:
  - success    — 'submitted' (агент сам завершил)
  - limit_hit  — содержит exit_context / exit_cost / exit_format
  - failed     — submitted_no_patch, early_exit

Также читает поле target (bool) — реальный результат проверки патча.

Артефакты:
  - work/data/TZ_3_trajectory_lengths.csv      — плоская таблица длин
  - work/data/TZ_3_descriptive_stats.csv       — описательная статистика
  - work/data/plots/TZ_3_*.png                 — 8 графиков

Длина считается в СИМВОЛАХ, не в токенах. Это намеренное ограничение:
точный токенизатор модели агента нам недоступен, грубая аппроксимация
"len(text)/4" выбрана не была. Везде в отчёте/коде — слово "символы".
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
from scipy import stats as sstats

import matplotlib
matplotlib.use("Agg")  # без интерактивного backend
import matplotlib.pyplot as plt
import seaborn as sns

# === Пути ===
PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
PARQUET_DIR = PROJECT_ROOT / "datasets" / "nebius-SWE-agent-trajectories" / "data"
DATA_DIR = PROJECT_ROOT / "work" / "data"
PLOTS_DIR = DATA_DIR / "plots" / "trajectory_lengths"

LENGTHS_CSV = DATA_DIR / "TZ_3_trajectory_lengths.csv"
STATS_CSV = DATA_DIR / "TZ_3_descriptive_stats.csv"

# === Цвета групп (фиксированные, чтобы все графики были согласованы) ===
GROUP_COLORS = {
    "success":   "#2ca02c",  # зелёный
    "limit_hit": "#ff7f0e",  # оранжевый
    "failed":    "#d62728",  # красный
}
GROUP_ORDER = ["success", "limit_hit", "failed"]

# === Маппинг exit_status -> exit_group ===
EXIT_GROUP_MAP = {
    "submitted":                 "success",
    "submitted (exit_context)":  "limit_hit",
    "submitted (exit_cost)":     "limit_hit",
    "submitted (exit_format)":   "limit_hit",
    "exit_context":              "limit_hit",
    "exit_cost":                 "limit_hit",
    "exit_format":               "limit_hit",
    "submitted_no_patch":        "failed",
    "early_exit":                "failed",
}


# ---------------------------------------------------------------------------
# Шаг 1. Сбор длин
# ---------------------------------------------------------------------------

def compute_lengths(trajectory) -> tuple[int, int]:
    """Подсчёт длин для одной траектории.

    trajectory — список словарей со схемой
    {cutoff_date, mask, role, system_prompt, text}.
    """
    n_steps = len(trajectory)
    n_chars = 0
    for step in trajectory:
        text = step["text"] or ""
        sysp = step["system_prompt"] or ""
        n_chars += len(text) + len(sysp)
    return n_steps, n_chars


def to_exit_group(exit_status: str) -> str:
    """Маппинг exit_status в одну из трёх групп. Незнакомые значения -> failed."""
    return EXIT_GROUP_MAP.get(exit_status, "failed")


def collect_lengths(parquet_dir: Path, batch_size: int = 200) -> pd.DataFrame:
    """Итеративно читает шарды parquet и считает длины траекторий."""
    print(f"[1/4] Чтение шардов из {parquet_dir} (batch_size={batch_size})...")
    dataset = ds.dataset(str(parquet_dir), format="parquet")
    total_rows = dataset.count_rows()
    print(f"      Всего строк во всех шардах: {total_rows}")

    scanner = dataset.scanner(
        columns=["instance_id", "exit_status", "trajectory", "target"],
        batch_size=batch_size,
    )

    rows = []
    seen = 0
    t0 = time.time()
    for batch in scanner.to_batches():
        for instance_id, exit_status, trajectory, target in zip(
            batch.column("instance_id").to_pylist(),
            batch.column("exit_status").to_pylist(),
            batch.column("trajectory").to_pylist(),
            batch.column("target").to_pylist(),
        ):
            n_steps, n_chars = compute_lengths(trajectory)
            rows.append((
                instance_id,
                exit_status,
                to_exit_group(exit_status),
                n_steps,
                n_chars,
                bool(target) if target is not None else None,
            ))
        seen += batch.num_rows
        if seen % 5000 == 0 or seen == total_rows:
            dt = time.time() - t0
            print(f"      {seen}/{total_rows} ({dt:.1f}s)")

    df = pd.DataFrame(rows, columns=[
        "instance_id", "exit_status", "exit_group",
        "n_steps", "n_chars", "target",
    ])
    print(f"      Готово: {len(df)} строк, {time.time() - t0:.1f}s")
    return df


# ---------------------------------------------------------------------------
# Шаг 2. Описательная статистика
# ---------------------------------------------------------------------------

def descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Описательная статистика по трём метрикам и трём группам + всё.

    Возвращает плоскую таблицу: строки = (metric, group), колонки = статистики.
    """
    metrics = ["n_steps", "n_chars"]
    groups = ["all"] + GROUP_ORDER
    rows = []
    for metric in metrics:
        for group in groups:
            sub = df[metric] if group == "all" else df.loc[df["exit_group"] == group, metric]
            arr = sub.to_numpy()
            row = {
                "metric": metric,
                "group": group,
                "count": len(arr),
                "mean": float(np.mean(arr)),
                "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
                "min": int(np.min(arr)),
                "q01": float(np.quantile(arr, 0.01)),
                "q05": float(np.quantile(arr, 0.05)),
                "q25": float(np.quantile(arr, 0.25)),
                "q50": float(np.quantile(arr, 0.50)),
                "q75": float(np.quantile(arr, 0.75)),
                "q95": float(np.quantile(arr, 0.95)),
                "q99": float(np.quantile(arr, 0.99)),
                "max": int(np.max(arr)),
                "skew": float(sstats.skew(arr)),
                "kurtosis": float(sstats.kurtosis(arr)),
            }
            rows.append(row)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Шаг 3. Графики
# ---------------------------------------------------------------------------

def _setup_style() -> None:
    sns.set_theme(style="whitegrid")
    plt.rcParams["figure.dpi"] = 110
    plt.rcParams["savefig.dpi"] = 140
    plt.rcParams["font.family"] = "DejaVu Sans"  # поддерживает кириллицу


def _save(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"      сохранено: {path.name}")


def plot_hist_overlay(df: pd.DataFrame, metric: str, path: Path,
                      bins: int = 60, log_x: bool = False) -> None:
    """Гистограмма метрики, наложение трёх групп. Без обрезки хвостов."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    series_all = df[metric]
    if log_x:
        lower = max(1, int(series_all[series_all > 0].min()))
        upper = int(series_all.max())
        edges = np.logspace(np.log10(lower), np.log10(upper), bins)
        ax.set_xscale("log")
    else:
        edges = np.linspace(0, int(series_all.max()), bins)

    for group in GROUP_ORDER:
        sub = df.loc[df["exit_group"] == group, metric]
        ax.hist(
            sub,
            bins=edges,
            color=GROUP_COLORS[group],
            alpha=0.55,
            label=f"{group} (n={len(sub)})",
            edgecolor="none",
        )
    ax.set_xlabel(metric)
    ax.set_ylabel("Количество траекторий")
    ax.set_title(f"Распределение {metric} по группам exit_group")
    ax.legend()
    _save(fig, path)


def plot_box_by_exit_status(df: pd.DataFrame, metric: str, path: Path,
                            clip_q: float = 0.99) -> None:
    """Boxplot: слева — по трём группам, справа — по полному exit_status."""
    upper = float(df[metric].quantile(clip_q))

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # (a) по exit_group
    ax = axes[0]
    sns.boxplot(
        data=df, x="exit_group", y=metric,
        order=GROUP_ORDER,
        palette=[GROUP_COLORS[g] for g in GROUP_ORDER],
        showfliers=False,
        ax=ax,
    )
    ax.set_ylim(0, upper)
    ax.set_title(f"{metric} по exit_group (выбросы > q{int(clip_q*100)} скрыты)")

    # (b) по полному exit_status, цвет наследуется от группы
    status_order = (
        df.groupby("exit_status").size().sort_values(ascending=False).index.tolist()
    )
    palette = {
        st: GROUP_COLORS[to_exit_group(st)] for st in status_order
    }
    ax = axes[1]
    sns.boxplot(
        data=df, x="exit_status", y=metric,
        order=status_order, palette=palette,
        showfliers=False,
        ax=ax,
    )
    ax.set_ylim(0, upper)
    ax.set_title(f"{metric} по полному exit_status")
    ax.tick_params(axis="x", labelrotation=35)
    for label in ax.get_xticklabels():
        label.set_horizontalalignment("right")

    _save(fig, path)


def plot_ecdf(df: pd.DataFrame, metric: str, path: Path,
              clip_q: float = 0.995) -> None:
    """ECDF трёх групп. Жёсткие лимиты бенчмарка видны как вертикальные стенки."""
    fig, ax = plt.subplots(figsize=(10, 5.5))
    upper = float(df[metric].quantile(clip_q))
    for group in GROUP_ORDER:
        sub = df.loc[df["exit_group"] == group, metric].sort_values().to_numpy()
        if len(sub) == 0:
            continue
        ys = np.arange(1, len(sub) + 1) / len(sub)
        ax.plot(sub, ys, color=GROUP_COLORS[group], lw=1.6,
                label=f"{group} (n={len(sub)})")
    ax.set_xlim(0, upper)
    ax.set_xlabel(metric)
    ax.set_ylabel("ECDF")
    ax.set_title(f"ECDF {metric} по группам exit_group")
    ax.legend()
    _save(fig, path)


def plot_exit_status_bar(df: pd.DataFrame, path: Path) -> None:
    """Bar-chart распределения exit_status и exit_group."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # (a) по exit_status (9 значений)
    s = df["exit_status"].value_counts().sort_values(ascending=False)
    colors = [GROUP_COLORS[to_exit_group(st)] for st in s.index]
    axes[0].bar(range(len(s)), s.values, color=colors)
    axes[0].set_xticks(range(len(s)))
    axes[0].set_xticklabels(s.index, rotation=35, ha="right")
    axes[0].set_ylabel("Количество траекторий")
    axes[0].set_title("Распределение exit_status (9 значений)")
    for i, v in enumerate(s.values):
        axes[0].text(i, v, f"{v}", ha="center", va="bottom", fontsize=9)

    # (b) по exit_group (3 значения)
    g = df["exit_group"].value_counts().reindex(GROUP_ORDER)
    axes[1].bar(GROUP_ORDER, g.values,
                color=[GROUP_COLORS[k] for k in GROUP_ORDER])
    axes[1].set_ylabel("Количество траекторий")
    axes[1].set_title("Распределение exit_group (3 группы)")
    total = int(g.sum())
    for i, v in enumerate(g.values):
        share = v / total * 100
        axes[1].text(i, v, f"{v}\n{share:.1f}%",
                     ha="center", va="bottom", fontsize=10)
    _save(fig, path)


TARGET_COLORS = {
    True:  "#1f77b4",  # синий — задача решена
    False: "#7f7f7f",  # серый  — задача не решена
}


def plot_hist_by_target(df: pd.DataFrame, metric: str, path: Path,
                        bins: int = 60, log_x: bool = False) -> None:
    """Гистограмма метрики по всем траекториям, разбивка по target (bool). Без обрезки хвостов."""
    sub_df = df[df["target"].notna()].copy()

    fig, ax = plt.subplots(figsize=(10, 5.5))
    series_all = sub_df[metric]
    if log_x:
        lower = max(1, int(series_all[series_all > 0].min()))
        upper = int(series_all.max())
        edges = np.logspace(np.log10(lower), np.log10(upper), bins)
        ax.set_xscale("log")
    else:
        edges = np.linspace(0, int(series_all.max()), bins)

    for val, label in [(True, "решено (target=True)"), (False, "не решено (target=False)")]:
        sub = sub_df.loc[sub_df["target"] == val, metric]
        ax.hist(
            sub,
            bins=edges,
            color=TARGET_COLORS[val],
            alpha=0.55,
            label=f"{label} (n={len(sub)})",
            edgecolor="none",
        )
    ax.set_xlabel(metric)
    ax.set_ylabel("Количество траекторий")
    ax.set_title(f"Распределение {metric} — все траектории, разбивка по target")
    ax.legend()
    _save(fig, path)


# ---------------------------------------------------------------------------
# Шаг 4. main
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Сбор длин
    if LENGTHS_CSV.exists():
        print(f"[1/4] Найден кэш {LENGTHS_CSV.name}, загружаем...")
        df = pd.read_csv(LENGTHS_CSV)
    else:
        df = collect_lengths(PARQUET_DIR)
        df.to_csv(LENGTHS_CSV, index=False)
        print(f"      Сохранено: {LENGTHS_CSV}")

    # Бюджетные проверки
    print(f"[2/4] Проверки целостности...")
    assert len(df) == 80036, f"Ожидалось 80036 строк, получено {len(df)}"
    counts = df["exit_group"].value_counts().to_dict()
    expected = {"success": 51087, "limit_hit": 24707, "failed": 4242}
    assert counts == expected, f"exit_group: ожидалось {expected}, получено {counts}"
    assert (df["n_steps"] >= 2).all(), "Есть траектории с n_steps < 2"
    print("      ok: 80 036 строк, exit_group распределение совпадает.")

    # Описательная статистика
    print(f"[3/4] Описательная статистика...")
    stats_df = descriptive_stats(df)
    stats_df.to_csv(STATS_CSV, index=False)
    print(f"      Сохранено: {STATS_CSV}")

    # Графики
    print(f"[4/4] Графики...")
    _setup_style()
    plot_exit_status_bar(df, PLOTS_DIR / "TZ_3_exit_status_bar.png")
    plot_hist_overlay(df, "n_steps", PLOTS_DIR / "TZ_3_hist_n_steps.png")
    plot_hist_overlay(df, "n_chars", PLOTS_DIR / "TZ_3_hist_n_chars.png", log_x=True)
    plot_box_by_exit_status(df, "n_steps", PLOTS_DIR / "TZ_3_box_n_steps_by_exit.png")
    plot_box_by_exit_status(df, "n_chars", PLOTS_DIR / "TZ_3_box_n_chars_by_exit.png")
    plot_ecdf(df, "n_steps", PLOTS_DIR / "TZ_3_ecdf_n_steps.png")
    plot_hist_by_target(df, "n_steps", PLOTS_DIR / "TZ_3_hist_n_steps_by_target.png")
    plot_hist_by_target(df, "n_chars", PLOTS_DIR / "TZ_3_hist_n_chars_by_target.png", log_x=True)
    print("\nГотово. Артефакты:")
    print(f"  {LENGTHS_CSV}")
    print(f"  {STATS_CSV}")
    print(f"  {PLOTS_DIR}/TZ_3_*.png")


if __name__ == "__main__":
    main()
