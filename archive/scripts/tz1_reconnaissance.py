#!/usr/bin/env python3
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
"""
ТЗ №1 — Разведка источников данных
Reconnaissance script for MAS_datasets_research
"""

import json
import io
import os
from pathlib import Path
from collections import defaultdict
import re

import pandas as pd
import polars as pl
from bs4 import BeautifulSoup

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO = Path("/Volumes/MansurSSD/MAS_datasets_research")
HTML_TAX = REPO / "fault_mode_analysis_and_classification_ru.html"
WHO_DIR = REPO / "Kevin355-Who_and_When"
AGENTRX_DIR = REPO / "microsoft-AgentRx"
NEBIUS_DIR = REPO / "nebius-SWE-agent-trajectories"
SWE_GYM_DIR = REPO / "SWE-Gym-OpenHands-Sampled-Trajectories"
TERMINALBENCH_DIR = REPO / "yoonholee-terminalbench-trajectories"
ITBENCH_DIR = REPO / "ibm-research-ITBench-Trajectories"
MIND2WEB_PATH = REPO / "iMeanAI-Mind2Web-Live"

OUT_REPORT = REPO / "docs" / "tz1_dataset_structure_report.md"

# ── Helpers ───────────────────────────────────────────────────────────────────
def field_check(df_columns):
    """Find error/failure/status related fields."""
    keywords = ["error", "failure", "fault", "fail", "mistake",
                "issue", "exception", "resolved", "exit_status", "category", "reason", "status"]
    return [c for c in df_columns if any(k in c.lower() for k in keywords)]

def truncate(obj, limit=600):
    s = repr(obj)
    if len(s) > limit:
        s = s[:limit] + "…"
    return s

def save_section(buf, heading, content):
    buf.write(f"\n{heading}\n\n{content}\n")

# ── 1. HTML Taxonomy ─────────────────────────────────────────────────────────
def parse_html_taxonomy():
    """Returns (trail_rows, ww_rows, ww_ideas_rows)"""
    with open(HTML_TAX, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    # Find all tables
    all_tables = soup.find_all("table")

    # Print raw tables for debugging
    lines = []
    lines.append(f"=== HTML: found {len(all_tables)} <table> elements ===")

    trail_rows = []
    ww_rows = []
    ww_ideas_rows = []

    for i, tbl in enumerate(all_tables):
        lines.append(f"\n--- Table {i} ---")
        rows_data = []
        for j, row in enumerate(tbl.find_all("tr")):
            cells = [c.get_text(strip=True) for c in row.find_all(["th", "td"])]
            rows_data.append(cells)
            if cells:
                lines.append(f"  Row {j}: {cells}")

        # Identify by column count / content
        if not rows_data:
            continue
        headers = rows_data[0] if rows_data else []

        # TRAIL table: has "Category" or "Тип" in headers, 4-6 columns
        if len(headers) >= 4 and any("Category" in h or "Тип" in h or "Последствия" in h for h in headers):
            trail_rows = rows_data[1:]  # skip header
            lines.append(f"  -> TRAIL table detected ({len(trail_rows)} rows)")

        # Who&When patterns table: has "Count" or "Частота" or W&W pattern text
        elif any("Count" in h or "Частота" in h or "retrieval" in str(headers).lower()
                 for h in headers):
            ww_rows = rows_data[1:]
            lines.append(f"  -> W&W patterns table detected ({len(ww_rows)} rows)")

        # Ideas table (Section B): has "Idea" or "ID"
        elif any("Idea" in h or "ID" in h and len(headers) >= 4 for h in headers):
            ww_ideas_rows = rows_data[1:]
            lines.append(f"  -> W&W Ideas table detected ({len(ww_ideas_rows)} rows)")

    return trail_rows, ww_rows, ww_ideas_rows, "\n".join(lines)

# ── 2. Who&When ───────────────────────────────────────────────────────────────
def analyze_who_and_when():
    buf = io.StringIO()

    gen = pd.read_parquet(WHO_DIR / "Algorithm-Generated.parquet")
    craft = pd.read_parquet(WHO_DIR / "Hand-Crafted.parquet")

    # Normalize columns
    gen = gen.rename(columns={"ground_truth": "groundtruth", "is_correct": "is_corrected"})
    craft = craft.rename(columns={"is_corrected": "is_corrected"})  # already correct name

    # Ensure same column order for concat
    shared = list(set(gen.columns) & set(craft.columns))
    gen = gen[shared]
    craft = craft[shared]
    df = pd.concat([gen, craft], ignore_index=True)

    # ── Schema ──
    save_section(buf, "## 2. Who&When — Детальный анализ",
                 f"**Всего записей:** {len(df)}  "
                 f"(Algorithm-Generated: {len(gen)}, Hand-Crafted: {len(craft)})\n\n"
                 "### 2.1 Схема (Algorithm-Generated)\n\n"
                 f"| Поле | Тип |\n|------|------|\n" +
                 "\n".join(f"| `{c}` | `{str(gen.dtypes[c])}` |" for c in gen.columns))

    # ── is_correct distribution ──
    ic_col = "is_corrected" if "is_corrected" in df.columns else "is_correct"
    ic_dist = df[ic_col].value_counts()
    save_section(buf, "### 2.2 Распределение is_correct",
                 ic_dist.to_string())

    # ── mistake_agent frequencies ──
    agent_freq = df["mistake_agent"].value_counts().head(15)
    lines = [f"| Агент | Кол-во |", "|------|------|"]
    for agent, cnt in agent_freq.items():
        lines.append(f"| `{agent}` | {cnt} |")
    save_section(buf, "### 2.3 Частоты: mistake_agent (топ-15)", "\n".join(lines))

    # ── mistake_reason frequencies ──
    reason_freq = df["mistake_reason"].dropna().value_counts()
    # Check for duplicates
    dupes = reason_freq[reason_freq > 1]
    lines = [f"**Всего уникальных:** {df['mistake_reason'].nunique()} "
             f"(из {df['mistake_reason'].notna().sum()} non-null)\n"]
    if len(dupes) > 0:
        lines.append("**Повторяющиеся mistake_reason:**\n")
        for reason, cnt in dupes.items():
            lines.append(f"- ({cnt}x) `{reason}`")
    lines.append("\n**Частотная таблица (все значения):**\n")
    lines.append(f"| mistake_reason | Кол-во |")
    lines.append(f"|------|------|")
    for reason, cnt in reason_freq.items():
        lines.append(f"| `{reason[:120]}` | {cnt} |")
    save_section(buf, "### 2.4 Все уникальные mistake_reason", "\n".join(lines))

    # ── mistake_step frequencies ──
    step_freq = df["mistake_step"].dropna().value_counts().head(20)
    lines = [f"| mistake_step | Кол-во |", "|------|------|"]
    for step, cnt in step_freq.items():
        lines.append(f"| `{step}` | {cnt} |")
    save_section(buf, "### 2.5 Частоты: mistake_step (топ-20)", "\n".join(lines))

    # ── Example records ──
    # Pick two with short-ish history
    examples = []
    for idx, row in df.head(20).iterrows():
        hist_len = len(row.get("history", [])) if isinstance(row.get("history"), list) else 0
        if hist_len >= 3 and len(examples) < 2:
            examples.append(row)

    for i, row in enumerate(examples, 1):
        hist = row.get("history", [])
        rec = {
            "is_corrected": row.get("is_corrected"),
            "question": row.get("question", "")[:200],
            "mistake_agent": row.get("mistake_agent"),
            "mistake_step": row.get("mistake_step"),
            "mistake_reason": row.get("mistake_reason"),
            "history_len": len(hist),
            "history_sample": hist[:3] if hist else [],
        }
        save_section(buf, f"### 2.6 Пример записи #{i} (Who&When)",
                     f"```json\n{json.dumps(rec, ensure_ascii=False, indent=2)}\n```")

    return buf.getvalue()

# ── 3. AgentRx ────────────────────────────────────────────────────────────────
def analyze_agentrx():
    buf = io.StringIO()

    annotated_files = ["magentic_one.jsonl", "tau_retail.jsonl"]
    traj_only_files = ["magentic_dataset.jsonl", "tau_retail_dataset.jsonl"]

    all_failures = []
    file_stats = {}

    # Annotated files
    for fname in annotated_files:
        fpath = AGENTRX_DIR / fname
        if not fpath.exists():
            buf.write(f"\n⚠️  Файл не найден: {fpath}\n")
            continue

        failures_this_file = []
        records = []
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                records.append(obj)
                failures_this_file.extend(obj.get("failures", []))

        file_stats[fname] = {
            "records": len(records),
            "failures": len(failures_this_file),
        }
        all_failures.extend(failures_this_file)

        # Frequency tables
        if failures_this_file:
            df_f = pd.DataFrame(failures_this_file)
            cat_freq = df_f["failure_category"].value_counts()
            agent_freq = df_f["failed_agent"].value_counts()

            lines = [f"**Записей:** {len(records)}  **Всего failures:** {len(failures_this_file)}\n"]
            lines.append("\n**Схема failures:**\n")
            lines.append(f"| Поле | Тип |")
            lines.append(f"|------|------|")
            for col in df_f.columns:
                lines.append(f"| `{col}` | `{df_f.dtypes[col]}` |")

            lines.append("\n**failure_category частоты:**\n")
            lines.append(f"| failure_category | Кол-во |")
            lines.append(f"|------|------|")
            for cat, cnt in cat_freq.items():
                lines.append(f"| `{cat}` | {cnt} |")

            lines.append("\n**failed_agent частоты:**\n")
            lines.append(f"| failed_agent | Кол-во |")
            lines.append(f"|------|------|")
            for ag, cnt in agent_freq.items():
                lines.append(f"| `{ag}` | {cnt} |")

            # root_cause reasons
            root_causes = [r.get("root_cause_reason") for r in records if r.get("root_cause_reason")]
            lines.append(f"\n**root_cause_reason (уникальных):** {len(set(root_causes))}")
            lines.append("\n**Примеры root_cause_reason:**")
            for rc in root_causes[:3]:
                if rc:
                    lines.append(f"- `{rc[:200]}`")

            # Example record
            example = records[0] if records else {}
            ex_fail = example.get("failures", [])[:2]
            ex_root = {k: v for k, v in example.items()
                       if k in ["trajectory_id", "num_failures", "root_cause_reason"]}
            lines.append(f"\n**Пример записи ({fname}):**\n```json")
            lines.append(json.dumps({**ex_root, "failures_sample": ex_fail},
                                     ensure_ascii=False, indent=2))
            lines.append("```")

            save_section(buf, f"### 3.1 Аннотированный: {fname}", "\n".join(lines))

    # Trajectory-only files
    for fname in traj_only_files:
        fpath = AGENTRX_DIR / fname
        if not fpath.exists():
            buf.write(f"\n⚠️  Файл не найден: {fpath}\n")
            continue

        records = []
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                records.append(json.loads(line))

        if records:
            first = records[0]
            keys = list(first.keys())
            # schema-like
            lines = [f"**Записей:** {len(records)}\n"]
            lines.append(f"**Ключи верхнего уровня:** {keys}\n")
            lines.append(f"\n**Типы значений:**\n")
            for k in keys:
                v = first[k]
                t = type(v).__name__
                lines.append(f"- `{k}`: `{t}`")
            # nested step example
            steps = first.get("steps", [])
            if steps:
                lines.append(f"\n**Пример первого шага (len(steps)={len(steps)}):**\n")
                lines.append(f"```json\n{json.dumps(steps[0], ensure_ascii=False, indent=2)[:600]}\n```")

            lines.append("\n**Статус:** типизация ошибок отсутствует — только траектории\n")

            save_section(buf, f"### 3.2 Только траектории: {fname}", "\n".join(lines))

    # Combined summary
    if all_failures:
        df_all = pd.DataFrame(all_failures)
        lines = [f"**Всего failures (оба файла):** {len(all_failures)}\n"]
        cat_all = df_all["failure_category"].value_counts()
        lines.append("\n**Combined failure_category (оба файла):**\n")
        lines.append(f"| failure_category | Кол-во |")
        lines.append(f"|------|------|")
        for cat, cnt in cat_all.items():
            lines.append(f"| `{cat}` | {cnt} |")
        save_section(buf, "### 3.3 Combined: failure_category across all annotated files",
                     "\n".join(lines))

    return buf.getvalue()

# ── 4. Nebius ─────────────────────────────────────────────────────────────────
def quick_check_nebius():
    buf = io.StringIO()

    parquet_files = list(NEBIUS_DIR.glob("data/*.parquet"))
    if not parquet_files:
        buf.write("⚠️  No parquet files found in nebius-SWE-agent-trajectories/data/\n")
        return buf.getvalue()

    # Lazy count
    df_lazy = pl.scan_parquet(str(NEBIUS_DIR / "data" / "*.parquet"))
    total = df_lazy.select(pl.len()).collect().item()
    schema = dict(df_lazy.collect_schema())

    # Sample 5 rows
    df_sample = df_lazy.head(5).collect()

    lines = [
        f"**Паркет-файлов:** {len(parquet_files)}",
        f"**Всего строк:** ~{total:,}",
        f"\n**Схема (top-level columns):**\n",
    ]
    for col, dtype in schema.items():
        lines.append(f"- `{col}`: `{dtype}`")

    # Error fields
    err_fields = field_check(list(schema.keys()))
    if err_fields:
        # Get actual values from sample
        for ef in err_fields:
            vals = df_sample[ef].to_list()
            lines.append(f"\n**Поле `{ef}` — уникальные значения в выборке:** {set(vals)}")

    # exit_status distribution from sample
    if "exit_status" in df_sample.columns:
        es_dist = df_sample["exit_status"].value_counts().sort("count", descending=True)
        lines.append(f"\n**exit_status (5 rows):**\n{es_dist}")

    # Trajectory structure
    if "trajectory" in df_sample.columns:
        first_traj_raw = df_sample["trajectory"][0].to_list()
        if first_traj_raw and len(first_traj_raw) > 0:
            lines.append(f"\n**Пример шага траектории (len={len(first_traj_raw)}):**\n"
                         f"`{truncate(first_traj_raw[0])}`")

    buf.write("\n".join(lines))
    return buf.getvalue()

# ── 5. SWE-Gym ─────────────────────────────────────────────────────────────────
def quick_check_swe_gym():
    buf = io.StringIO()

    pq_files = list(SWE_GYM_DIR.glob("data/*.parquet"))
    if not pq_files:
        buf.write("⚠️  No parquet files found\n")
        return buf.getvalue()

    # Try each file individually — some may be corrupted
    df = None
    last_err = None
    for pf in pq_files:
        try:
            df = pl.read_parquet(pf).head(5)
            break
        except Exception as e:
            last_err = e
            continue

    if df is None:
        buf.write(f"⚠️  All parquet files failed to read: {last_err}\n")
        return buf.getvalue()

    total = 0
    for pf in pq_files:
        try:
            total += len(pl.read_parquet(pf))
        except Exception:
            pass

    lines = [
        f"**Паркет-файлов:** {len(pq_files)}",
        f"**Всего строк:** {total:,}",
        f"\n**Схема:**\n",
    ]
    col_names = df.columns
    lines.append(f"\n**Схема:**\n")
    for col in col_names:
        dtype = str(df[col].dtype)
        lines.append(f"- `{col}`: `{dtype}`")

    err_fields = field_check(list(col_names))
    if err_fields:
        lines.append(f"\n**Error-related fields:** {err_fields}")
        for ef in err_fields:
            lines.append(f"  `{ef}`: {df[ef].to_list()}")

    # Nested example
    if "messages" in col_names:
        first_msgs = df["messages"][0].to_list()
        if first_msgs and len(first_msgs) > 0:
            lines.append(f"\n**Пример первого сообщения (len={len(first_msgs)}):**\n"
                         f"`{truncate(first_msgs[0])}`")

    buf.write("\n".join(lines))
    return buf.getvalue()

# ── 6. Terminalbench ─────────────────────────────────────────────────────────
def quick_check_terminalbench():
    buf = io.StringIO()

    pq_files = list(TERMINALBENCH_DIR.glob("data/*.parquet"))
    if not pq_files:
        buf.write("⚠️  No parquet files found\n")
        return buf.getvalue()

    df = pl.scan_parquet(str(TERMINALBENCH_DIR / "data" / "*.parquet")).head(5).collect()
    total = pl.scan_parquet(str(TERMINALBENCH_DIR / "data" / "*.parquet")).select(pl.len()).collect().item()

    lines = [
        f"**Паркет-файлов:** {len(pq_files)}",
        f"**Всего строк:** {total:,}",
        f"\n**Схема:**\n",
    ]
    for col in df.columns:
        dtype = str(df[col].dtype)
        lines.append(f"- `{col}`: `{dtype}`")

    col_names = [c for c in df.columns]
    err_fields = field_check(col_names)
    if err_fields:
        lines.append(f"\n**Error-related fields:** {err_fields}")

    if "steps" in col_names:
        first_steps_raw = df["steps"][0]
        first_steps = first_steps_raw
        if isinstance(first_steps_raw, str) and first_steps_raw != "null":
            lines.append(f"\n**steps sample (type=JSON string, len={len(first_steps_raw)}):**\n"
                         f"`{truncate(first_steps_raw)[:500]}`")
        elif first_steps_raw is not None:
            lines.append(f"\n**steps sample (type={type(first_steps_raw).__name__}):**\n"
                         f"`{truncate(first_steps_raw) if first_steps_raw else 'null'}`")

    buf.write("\n".join(lines))
    return buf.getvalue()

# ── 7. ITBench ────────────────────────────────────────────────────────────────
def quick_check_itbench():
    buf = io.StringIO()

    # Find session.jsonl files
    session_files = list(ITBENCH_DIR.rglob("session.jsonl"))
    if not session_files:
        buf.write("⚠️  No session.jsonl found\n")
        return buf.getvalue()

    first_file = session_files[0]
    records = []
    with open(first_file, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            records.append(json.loads(line))

    lines = [
        f"**session.jsonl файлов:** {len(session_files)}",
        f"**Прочитано записей из первого файла:** {len(records)}",
        f"\n**Ключи верхнего уровня (первая запись):**\n",
    ]

    if records:
        first = records[0]
        for k, v in first.items():
            t = type(v).__name__
            lines.append(f"- `{k}`: `{t}`")

        # Check for type:error
        if "type" in first:
            lines.append(f"\n**type field values in 5 records:**")
            types_seen = set(r.get("type") for r in records)
            lines.append(f"  {types_seen}")

        # payload example
        if "payload" in first:
            lines.append(f"\n**Пример payload:**\n`{truncate(first['payload'])}`")

    buf.write("\n".join(lines))
    return buf.getvalue()

# ── 8. Mind2Web ──────────────────────────────────────────────────────────────
def quick_check_mind2web():
    buf = io.StringIO()

    json_files = list(MIND2WEB_PATH.glob("*.json")) + list(MIND2WEB_PATH.glob("*.jsonl"))
    if not json_files:
        buf.write("⚠️  No JSON files found\n")
        return buf.getvalue()

    first_file = json_files[0]
    # Mind2Web files are JSON arrays, not NDJSON
    if first_file.suffix == ".jsonl":
        df = pd.read_json(first_file, nrows=5, lines=True)
    else:
        # JSON array — read as text and take first few lines manually
        with open(first_file, encoding="utf-8") as f:
            content = f.read()
        try:
            data = json.loads(content)
            if isinstance(data, list):
                df = pd.DataFrame(data[:5])
            else:
                df = pd.DataFrame([data])
        except Exception:
            buf.write(f"⚠️  Failed to parse JSON: {first_file}\n")
            return buf.getvalue()

    lines = [
        f"**Файл:** {first_file.name}",
        f"**Прочитано строк:** {len(df)}",
        f"\n**Схема:**\n",
    ]
    for col in df.columns:
        lines.append(f"- `{col}`: `{df[col].dtype}`")

    err_fields = field_check(list(df.columns))
    if err_fields:
        lines.append(f"\n**Error-related fields:** {err_fields}")

    # evaluation example
    if "evaluation" in df.columns and len(df) > 0:
        ev = df["evaluation"].iloc[0]
        lines.append(f"\n**Пример evaluation:**\n`{truncate(ev)}`")

    buf.write("\n".join(lines))
    return buf.getvalue()

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("Starting ТЗ №1 reconnaissance…", flush=True)

    # 1. HTML Taxonomy
    print("  [1/8] Parsing HTML taxonomy…", flush=True)
    trail_rows, ww_rows, ww_ideas, html_debug = parse_html_taxonomy()

    # 2. Who&When
    print("  [2/8] Analyzing Who&When…", flush=True)
    ww_section = analyze_who_and_when()

    # 3. AgentRx
    print("  [3/8] Analyzing AgentRx…", flush=True)
    rx_section = analyze_agentrx()

    # 4. Nebius
    print("  [4/8] Checking nebius…", flush=True)
    nebius_section = quick_check_nebius()

    # 5. SWE-Gym
    print("  [5/8] Checking SWE-Gym…", flush=True)
    swe_gym_section = quick_check_swe_gym()

    # 6. Terminalbench
    print("  [6/8] Checking terminalbench…", flush=True)
    terminalbench_section = quick_check_terminalbench()

    # 7. ITBench
    print("  [7/8] Checking ITBench…", flush=True)
    itbench_section = quick_check_itbench()

    # 8. Mind2Web
    print("  [8/8] Checking Mind2Web…", flush=True)
    mind2web_section = quick_check_mind2web()

    # ── Build report ──
    print("  Building report…", flush=True)

    report = io.StringIO()
    report.write("# ТЗ №1 — Разведка источников данных\n\n")
    report.write("**Дата:** 2026-05-04\n")
    report.write("**Репозиторий:** MAS_datasets_research\n\n")

    # Executive Summary Table
    report.write("## Резюме\n\n")
    report.write("| Датасет | HF ID | Записей | Типизация ошибок | Что можно извлечь |\n")
    report.write("|---------|-------|---------|------------------|-------------------|\n")
    summary = [
        ("Who&When", "Kevin355/Who_and_When", "~184", "✅ Да",
         "`mistake_reason` (free-text, 182 уник.), `mistake_agent`, `mistake_step`"),
        ("AgentRx", "microsoft/AgentRx", "159 (73 аннот.)",
         "✅ Частично",
         "`failure_category` (8+ типов), `failed_agent`, `step_number`"),
        ("nebius/SWE-agent", "nebius/SWE-agent-trajectories", "~80 036",
         "❌ Нет",
         "`exit_status` (3 кат.), длина траектории"),
        ("SWE-Gym/OpenHands", "SWE-Gym/OpenHands-Sampled-Trajectories", "~6 055",
         "❌ Нет",
         "`resolved` (bool), длина траектории"),
        ("Terminalbench", "yoonholee/terminalbench-trajectories", "~52 104",
         "❌ Нет",
         "`reward` (binary), `duration_seconds`"),
        ("ITBench", "ibm-research/ITBench-Trajectories", "105",
         "⚠️ Частично",
         "`type:error` (operational, нет таксономии)"),
        ("Mind2Web-Live", "iMeanAI/Mind2Web-Live", "~500",
         "❌ Нет",
         "Только описания задач, траектории отсутствуют"),
    ]
    for row in summary:
        report.write(f"| {' | '.join(row)} |\n")
    report.write("\n")

    # Section 1: Existing taxonomy
    report.write("## 1. Существующая таксономия ошибок\n\n")
    report.write("Источник: `fault_mode_analysis_and_classification_ru.html`\n\n")

    if trail_rows:
        report.write("### 1.1 TRAIL — таблица ошибок\n\n")
        report.write("| Класс ошибок | Подгруппа | Категория | Последствия | Моделир. |\n")
        report.write("|-------------|-----------|-----------|-------------|----------|\n")
        for row in trail_rows[:15]:  # cap for readability
            report.write("| " + " | ".join(str(c)[:60] for c in row) + " |\n")
        report.write("\n")

    if ww_rows:
        report.write("### 1.2 Who&When fault patterns\n\n")
        report.write("| Паттерн | Count | TRAIL Category | Моделир. |\n")
        report.write("|---------|-------|-----------------|----------|\n")
        for row in ww_rows[:12]:
            report.write("| " + " | ".join(str(c)[:50] for c in row) + " |\n")
        report.write("\n")

    if ww_ideas:
        report.write("### 1.3 Идеи симулятора (TRAIL mapping)\n\n")
        report.write("| ID | Идея | TRAIL | Категория |\n")
        report.write("|----|------|-------|-----------|\n")
        for row in ww_ideas[:14]:
            report.write("| " + " | ".join(str(c)[:50] for c in row) + " |\n")
        report.write("\n")

    # Section 2: Who&When
    report.write(ww_section)
    report.write("\n")

    # Section 3: AgentRx
    report.write(rx_section)
    report.write("\n")

    # Section 4: 5 datasets
    report.write("## 4. Пять дополнительных датасетов\n\n")

    report.write("### 4.1 nebius/SWE-agent-trajectories\n\n")
    report.write(nebius_section)
    report.write("\n\n")

    report.write("### 4.2 SWE-Gym/OpenHands-Sampled-Trajectories\n\n")
    report.write(swe_gym_section)
    report.write("\n\n")

    report.write("### 4.3 yoonholee/terminalbench-trajectories\n\n")
    report.write(terminalbench_section)
    report.write("\n\n")

    report.write("### 4.4 ibm-research/ITBench-Trajectories\n\n")
    report.write(itbench_section)
    report.write("\n\n")

    report.write("### 4.5 iMeanAI/Mind2Web-Live\n\n")
    report.write(mind2web_section)
    report.write("\n\n")

    # Section 5: Выводы
    report.write("## 5. Вывод\n\n")
    conclusions = [
        "**Who&When** — ✅ Есть явная типизация. Поля: `mistake_agent`, `mistake_step`, `mistake_reason` "
        "(182 уникальных free-text значений). 184 записи — все неуспешные. mistake_reason свободный текст, "
        "не фиксированная таксономия.",
        "**AgentRx** — ⚠️ Частичная типизация. 73 из 159 записей аннотированы. "
        "`failure_category` имеет 8+ категорий, но таксономия НЕ унифицирована между файлами "
        "(magentic_one ≠ tau_retail). `failed_agent` доминирует WebSurfer.",
        "**nebius/SWE-agent** — ❌ Нет типизации. Только `exit_status` (3 категории: "
        "exit_context/exit_format/early_exit). Можно извлечь: частоту успех/провал, "
        "длину траектории, модель.",
        "**SWE-Gym/OpenHands** — ❌ Нет типизации. Только `resolved` (bool) и "
        "`test_result` (bool flags без таксономии). Можно извлечь: success rate, "
        "длину сообщений.",
        "**yoonholee/terminalbench** — ❌ Нет типизации. Только `reward` (binary 0/1) "
        "и `duration_seconds`. Можно извлечь: success rate, время выполнения, стоимость.",
        "**ibm-research/ITBench** — ⚠️ Частично. session.jsonl содержит `type: error` "
        "но это operational message type, не структурированная таксономия. "
        "Можно извлечь: оценки качества из judge_output, типы операций.",
        "**iMeanAI/Mind2Web-Live** — ❌ Нет типизации. Нет траекторий, только описания "
        "задач и критерии оценки. Можно извлечь: число задач, complexity.",
        "",
        "**Итого:** из 7 датасетов только Who&When и AgentRx имеют структурированную "
        "типизацию ошибок. Остальные 5 — только агрегированные метрики (exit_status, "
        "resolved, reward). Для ТЗ №2 основной фокус — на парсерах Who&When и AgentRx.",
    ]
    report.write("\n\n".join(conclusions))

    # Save
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        f.write(report.getvalue())

    size = OUT_REPORT.stat().st_size
    print(f"\n✅ Done! Report written to: {OUT_REPORT}")
    print(f"   Size: {size:,} bytes ({size//1024} KB)")


if __name__ == "__main__":
    main()
