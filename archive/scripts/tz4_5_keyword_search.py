"""ТЗ №4.5 — Keyword search в текстах траекторий."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
import math
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
NEB_DIR = ROOT / "nebius-SWE-agent-trajectories" / "data"
SWE_DIR = ROOT / "SWE-Gym-OpenHands-Sampled-Trajectories" / "data"
TERM_DIR = ROOT / "yoonholee-terminalbench-trajectories" / "data"
ITBENCH_DIR = ROOT / "ibm-research-ITBench-Trajectories"

KEYWORD_CATEGORIES = {
    "tool_timeout": [
        "timeout", "timed out", "time out", "timeouterror",
        "deadline exceeded", "request timeout", "operation timed",
    ],
    "tool_web_failure": [
        "404", "403", "500", "502", "503",
        "connection refused", "connection error", "network error",
        "failed to connect", "could not connect", "no route to host",
        "name resolution failed", "dns",
    ],
    "resource_not_found": [
        "filenotfounderror", "no such file", "not found",
        "does not exist", "cannot find", "path does not exist",
    ],
    "permission_error": [
        "permission denied", "access denied", "permissionerror",
        "not permitted", "operation not permitted",
    ],
    "memory_error": [
        "out of memory", "oom", "memoryerror",
        "memory error", "killed", "cannot allocate",
    ],
    "code_execution_error": [
        "traceback (most recent call last)",
        "syntaxerror", "nameerror", "typeerror",
        "valueerror", "indexerror", "keyerror",
        "attributeerror", "importerror", "modulenotfounderror",
    ],
    "tool_execution_error": [
        "command not found", "no such command",
        "bash: ", "sh: ", "error:", "failed:", "exception:",
    ],
}

CATEGORIES = list(KEYWORD_CATEGORIES.keys())


def wilson_ci(n_success: int, n_total: int, z: float = 1.96):
    if n_total == 0:
        return 0.0, 0.0
    p = n_success / n_total
    denom = 1 + z**2 / n_total
    center = (p + z**2 / (2 * n_total)) / denom
    margin = z * math.sqrt(p * (1 - p) / n_total + z**2 / (4 * n_total**2)) / denom
    return max(0.0, center - margin), min(1.0, center + margin)


def search_text(text: str) -> dict[str, int]:
    """Return {category: n_steps_with_match} for a single text block."""
    if not isinstance(text, str) or not text:
        return {}
    t = text.lower()
    return {cat: 1 for cat, kws in KEYWORD_CATEGORIES.items() if any(kw in t for kw in kws)}


def find_snippet(text: str, cat: str) -> str:
    """Return first 100 chars around the first matching keyword."""
    if not isinstance(text, str):
        return ""
    t = text.lower()
    for kw in KEYWORD_CATEGORIES[cat]:
        idx = t.find(kw)
        if idx >= 0:
            start = max(0, idx - 20)
            return text[start: start + 100].replace("\n", " ")
    return ""


# ── Counters ──────────────────────────────────────────────────────────────────

def empty_counters():
    return {cat: {"with_error": 0, "occurrences": 0} for cat in CATEGORIES}


# ── Dataset 1: Nebius ─────────────────────────────────────────────────────────

def process_nebius(examples: dict) -> tuple[dict, dict, int]:
    """Returns (counters, exit_status_counters, n_total)."""
    counters = empty_counters()
    # exit_status -> category -> {with_error, total}
    es_counters: dict[str, dict] = defaultdict(lambda: {cat: {"with_error": 0} for cat in CATEGORIES})
    es_totals: dict[str, int] = defaultdict(int)
    n_total = 0

    shards = sorted(NEB_DIR.glob("train-*-of-*.parquet"))
    for shard_idx, shard in enumerate(shards):
        print(f"  nebius shard {shard_idx+1}/{len(shards)}: {shard.name}")
        df = pd.read_parquet(shard)
        for _, row in df.iterrows():
            n_total += 1
            exit_status = str(row.get("exit_status", "unknown") or "unknown")
            es_totals[exit_status] += 1
            trajectory = row.get("trajectory")
            if trajectory is None or (hasattr(trajectory, '__len__') and len(trajectory) == 0):
                trajectory = []

            traj_cats: set[str] = set()
            for step in trajectory:
                if not isinstance(step, dict) or step.get("role") != "user":
                    continue
                text = step.get("text", "")
                matches = search_text(text)
                for cat in matches:
                    counters[cat]["occurrences"] += 1
                    if cat not in traj_cats:
                        traj_cats.add(cat)
                        # collect example
                        key = ("nebius", cat)
                        if len(examples[key]) < 5:
                            examples[key].append(find_snippet(text, cat))

            for cat in traj_cats:
                counters[cat]["with_error"] += 1
                es_counters[exit_status][cat]["with_error"] += 1

    return counters, dict(es_counters), dict(es_totals), n_total


# ── Dataset 2: SWE-Gym ────────────────────────────────────────────────────────

def process_swegym(examples: dict) -> tuple[dict, int]:
    counters = empty_counters()
    n_total = 0

    for shard in sorted(p for p in SWE_DIR.glob("*.parquet") if not p.name.startswith(".")):
        print(f"  swegym shard: {shard.name}")
        df = pd.read_parquet(shard)
        for _, row in df.iterrows():
            n_total += 1
            messages = row.get("messages")
            if messages is None or not hasattr(messages, '__iter__'):
                messages = []
            traj_cats: set[str] = set()
            for msg in messages:
                if not isinstance(msg, dict) or msg.get("role") != "tool":
                    continue
                content = msg.get("content", "")
                if isinstance(content, list):
                    content = " ".join(str(c) for c in content)
                matches = search_text(content)
                for cat in matches:
                    counters[cat]["occurrences"] += 1
                    if cat not in traj_cats:
                        traj_cats.add(cat)
                        key = ("swegym", cat)
                        if len(examples[key]) < 5:
                            examples[key].append(find_snippet(content, cat))

            for cat in traj_cats:
                counters[cat]["with_error"] += 1

    return counters, n_total


# ── Dataset 3: TerminalBench ──────────────────────────────────────────────────

def process_terminalbench(examples: dict) -> tuple[dict, int]:
    counters = empty_counters()
    n_total = 0

    for shard in sorted(TERM_DIR.glob("*.parquet")):
        print(f"  terminalbench shard: {shard.name}")
        df = pd.read_parquet(shard)
        for _, row in df.iterrows():
            n_total += 1
            steps_str = row.get("steps", "")
            if not isinstance(steps_str, str) or not steps_str.strip() or steps_str == "null":
                continue
            try:
                steps = json.loads(steps_str)
            except (json.JSONDecodeError, ValueError):
                continue
            if not isinstance(steps, list):
                continue

            traj_cats: set[str] = set()
            for step in steps:
                if not isinstance(step, dict):
                    continue
                text = str(step.get("msg", ""))
                matches = search_text(text)
                for cat in matches:
                    counters[cat]["occurrences"] += 1
                    if cat not in traj_cats:
                        traj_cats.add(cat)
                        key = ("terminalbench", cat)
                        if len(examples[key]) < 5:
                            examples[key].append(find_snippet(text, cat))

            for cat in traj_cats:
                counters[cat]["with_error"] += 1

    return counters, n_total


# ── Dataset 4: ITBench ────────────────────────────────────────────────────────

def process_itbench(examples: dict) -> tuple[dict, int]:
    counters = empty_counters()
    session_files = sorted(ITBENCH_DIR.rglob("session.jsonl"))
    n_total = len(session_files)
    print(f"  itbench: {n_total} session files")

    for session_file in session_files:
        traj_cats: set[str] = set()
        try:
            with open(session_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    t = obj.get("type", "")
                    if t not in ("error", "event_msg", "response_item"):
                        continue
                    payload = obj.get("payload", {})
                    text = json.dumps(payload, ensure_ascii=False) if isinstance(payload, dict) else str(payload)
                    matches = search_text(text)
                    for cat in matches:
                        counters[cat]["occurrences"] += 1
                        if cat not in traj_cats:
                            traj_cats.add(cat)
                            key = ("itbench", cat)
                            if len(examples[key]) < 5:
                                examples[key].append(find_snippet(text, cat))
        except OSError:
            pass

        for cat in traj_cats:
            counters[cat]["with_error"] += 1

    return counters, n_total


# ── Build CSVs ────────────────────────────────────────────────────────────────

def build_results_csv(all_counters: dict) -> pd.DataFrame:
    rows = []
    for dataset, (counters, n_total) in all_counters.items():
        for cat in CATEGORIES:
            n_with = counters[cat]["with_error"]
            n_occ = counters[cat]["occurrences"]
            p = n_with / n_total if n_total else 0.0
            lo, hi = wilson_ci(n_with, n_total)
            rows.append({
                "dataset": dataset,
                "category": cat,
                "n_trajectories_with_error": n_with,
                "n_trajectories_total": n_total,
                "n_occurrences_total": n_occ,
                "p_trajectory": round(p, 6),
                "ci_lower": round(lo, 6),
                "ci_upper": round(hi, 6),
            })
    return pd.DataFrame(rows)


def build_nebius_exit_status_csv(es_counters: dict, es_totals: dict) -> pd.DataFrame:
    rows = []
    for es, cat_dict in es_counters.items():
        n_total = es_totals.get(es, 0)
        for cat in CATEGORIES:
            n_with = cat_dict[cat]["with_error"]
            p = n_with / n_total if n_total else 0.0
            rows.append({
                "exit_status": es,
                "category": cat,
                "n_trajectories_with_error": n_with,
                "n_trajectories_total": n_total,
                "p_trajectory": round(p, 6),
            })
    return pd.DataFrame(rows)


# ── Report ────────────────────────────────────────────────────────────────────

def df_to_md(df: pd.DataFrame) -> str:
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |",
             "|" + "|".join(["---"] * len(df.columns)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join("—" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v) for v in row) + " |")
    return "\n".join(lines)


def generate_report(results_df: pd.DataFrame, es_df: pd.DataFrame, examples: dict) -> str:
    lines = [
        "# ТЗ №4.5 — Keyword Search в текстах траекторий",
        "",
        "**Дата:** 2026-05-05",
        "",
        "## 1. Сводная таблица",
        "",
        "p_trajectory = n_trajectories_with_error / n_trajectories_total; Wilson 95% CI.",
        "",
    ]

    # Pivot: rows = category, cols = dataset
    datasets = results_df["dataset"].unique().tolist()
    pivot_rows = []
    for cat in CATEGORIES:
        row = {"category": cat}
        for ds in datasets:
            sub = results_df[(results_df["dataset"] == ds) & (results_df["category"] == cat)]
            if sub.empty:
                row[f"{ds}_p"] = "—"
                row[f"{ds}_ci"] = "—"
            else:
                r = sub.iloc[0]
                row[f"{ds}_p"] = f"{r['p_trajectory']:.4f}"
                row[f"{ds}_ci"] = f"[{r['ci_lower']:.4f}, {r['ci_upper']:.4f}]"
        pivot_rows.append(row)
    lines.append(df_to_md(pd.DataFrame(pivot_rows)))
    lines.append("")

    # Section 2: Nebius exit_status
    lines += ["## 2. Nebius: разбивка по exit_status", ""]
    for es in sorted(es_df["exit_status"].unique()):
        sub = es_df[es_df["exit_status"] == es][["category", "n_trajectories_with_error", "n_trajectories_total", "p_trajectory"]]
        n_total = sub["n_trajectories_total"].iloc[0] if len(sub) else 0
        lines.append(f"### {es} (n={n_total})")
        lines.append("")
        lines.append(df_to_md(sub))
        lines.append("")

    # Section 3: Top-5 examples
    lines += ["## 3. Топ-5 примеров по категориям", ""]
    lines.append("Первые 100 символов текста где найдено ключевое слово. Нужно для оценки качества поиска.")
    lines.append("")
    for ds in datasets:
        lines.append(f"### {ds}")
        lines.append("")
        for cat in CATEGORIES:
            key = (ds, cat)
            exs = examples.get(key, [])
            if not exs:
                continue
            lines.append(f"**{cat}:**")
            for ex in exs:
                lines.append(f"- `{ex}`")
        lines.append("")

    # Section 4: Quality assessment
    lines += [
        "## 4. Оценка качества",
        "",
        "| Категория | Датасет | Оценка | Примечание |",
        "|---|---|---|---|",
        "| code_execution_error | nebius | Завышено | Traceback — часть SWE-задачи, не инфраструктурная ошибка |",
        "| code_execution_error | swegym | Завышено | Аналогично nebius |",
        "| resource_not_found | nebius | Умеренно | 'not found' встречается в выводе тестов |",
        "| tool_timeout | nebius | Точно | Timeout — инфраструктурная ошибка |",
        "| tool_web_failure | nebius | Точно | HTTP-коды — инфраструктурная ошибка |",
        "| permission_error | все | Точно | Permission denied — инфраструктурная ошибка |",
        "| memory_error | все | Точно | OOM — инфраструктурная ошибка |",
        "",
    ]

    # Section 5: Comparison with TZ2-4
    lines += [
        "## 5. Сравнение с ТЗ №2-4",
        "",
        "ТЗ №2-4 работали только с AgentRx (73 траектории) и Who&When (184 траектории).",
        "Keyword search добавляет данные из 4 новых датасетов.",
        "",
    ]
    comparison_cats = ["tool_timeout", "tool_web_failure", "resource_not_found",
                       "permission_error", "memory_error", "code_execution_error", "tool_execution_error"]
    comp_rows = []
    for cat in comparison_cats:
        sub = results_df[results_df["category"] == cat]
        total_new = sub["n_trajectories_with_error"].sum()
        comp_rows.append({"category": cat, "n_new (keyword search)": total_new,
                          "n_prev (TZ2-4)": "0 (не было данных)"})
    lines.append(df_to_md(pd.DataFrame(comp_rows)))
    lines.append("")

    lines += [
        "## 6. Ограничения",
        "",
        "1. **Ложные срабатывания code_execution_error** — для nebius/SWE-Gym завышено: "
        "traceback встречается как часть SWE-задачи, а не как инфраструктурная ошибка.",
        "2. **Контекст поиска** — ищем в ответах среды (role=user/tool), не в рассуждениях агента. "
        "Снижает ложные срабатывания, но не устраняет их.",
        "3. **tool_execution_error** — ключевые слова 'error:', 'failed:' очень широкие, "
        "высокая вероятность ложных срабатываний.",
        "4. **TerminalBench** — ~17k из 52k траекторий имеют непустые steps; остальные steps=null.",
    ]

    return "\n".join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("ТЗ №4.5 — Keyword Search в текстах траекторий")
    print("=" * 60)

    examples: dict = defaultdict(list)

    print("\n[1/4] Nebius SWE-agent-trajectories...")
    neb_counters, es_counters, es_totals, neb_total = process_nebius(examples)
    print(f"  total: {neb_total}")

    print("\n[2/4] SWE-Gym OpenHands...")
    swe_counters, swe_total = process_swegym(examples)
    print(f"  total: {swe_total}")

    print("\n[3/4] TerminalBench...")
    term_counters, term_total = process_terminalbench(examples)
    print(f"  total: {term_total}")

    print("\n[4/4] ITBench...")
    itb_counters, itb_total = process_itbench(examples)
    print(f"  total: {itb_total}")

    all_counters = {
        "nebius": (neb_counters, neb_total),
        "swegym": (swe_counters, swe_total),
        "terminalbench": (term_counters, term_total),
        "itbench": (itb_counters, itb_total),
    }

    results_df = build_results_csv(all_counters)
    results_df.to_csv(DATA_DIR / "keyword_search_results.csv", index=False)
    print(f"\nSaved data/keyword_search_results.csv ({len(results_df)} rows)")

    es_df = build_nebius_exit_status_csv(es_counters, es_totals)
    es_df.to_csv(DATA_DIR / "nebius_by_exit_status.csv", index=False)
    print(f"Saved data/nebius_by_exit_status.csv ({len(es_df)} rows)")

    report = generate_report(results_df, es_df, dict(examples))
    report_path = DOCS_DIR / "tz4_5_keyword_search_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Saved docs/tz4_5_keyword_search_report.md ({report_path.stat().st_size:,} bytes)")

    print("\nDone.")


if __name__ == "__main__":
    main()
