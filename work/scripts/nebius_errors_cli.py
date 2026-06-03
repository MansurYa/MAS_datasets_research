#!/usr/bin/env python3
"""
CLI для анализа ошибок nebius_invalid_invocation (плоский формат).

Команды:
  list      -- топ ошибок по категории
  inspect   -- все ошибки для instance_id с пометками NEW/DUPLICATE
  show      -- шаг из parquet с контекстом
  sample    -- случайная выборка для FP-проверки
  fp-check  -- одна ошибка по (instance_id, traj_idx, step_idx)
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
PARQUET_DIR = PROJECT_ROOT / "datasets" / "nebius-SWE-agent-trajectories" / "data"
DATA_DIR = PROJECT_ROOT / "work" / "data"
CATEGORIES = ["A", "B", "E1", "E2"]


def load_errors(category=None):
    """Load errors. If category is None, load all categories."""
    path = DATA_DIR / "errors_invalid_invocation.json"
    with open(path) as f:
        data = json.load(f)
    if category:
        return data.get(category, [])
    return data


def load_trajectories(instance_id):
    dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
    table = dataset.to_table(filter=ds.field("instance_id") == instance_id)
    if len(table) == 0:
        raise ValueError(f"Не найден: {instance_id}")
    d = table.to_pydict()
    return d["trajectory"], d.get("exit_status", [])


def show_step(traj, step_idx, context=1):
    for i in range(max(0, step_idx - context), step_idx):
        print(f"[{i}] {traj[i].get('role', '?')}: {traj[i].get('text', '')[:2000]}...")
    print("-" * 50)
    print(f"[{step_idx}] {traj[step_idx].get('role', '?')}:")
    print(traj[step_idx].get("text", ""))
    if step_idx < len(traj) - 1:
        print("-" * 50)
        print(f"[{step_idx+1}] {traj[step_idx+1].get('role', '?')}: {traj[step_idx+1].get('text', '')[:2000]}...")


def cmd_list(args):
    errors = load_errors(args.category)
    if not errors:
        print(f"Нет данных для категории {args.category}")
        return
    df = pd.DataFrame(errors)
    grouped = df.groupby('normalized_pattern').size().reset_index(name='count')
    grouped = grouped[grouped['count'] >= args.min_count]
    grouped = grouped.sort_values('count', ascending=False).head(args.top)
    for _, r in grouped.iterrows():
        print(f"{r['normalized_pattern'][:70]:<70} n={r['count']:>5}")


def cmd_inspect(args):
    categories = CATEGORIES if args.category == "all" else [args.category]
    for cat in categories:
        errors = load_errors(cat)
        shown_header = False
        for r in errors:
            if r["instance_id"] != args.instance_id:
                continue
            if not shown_header:
                print(f"\n--- {args.instance_id} (категория {cat}) ---")
                shown_header = True
            if r["is_first_occurrence_in_traj"]:
                marker = "[NEW]"
            else:
                marker = f"[DUPLICATE {r['occurrence_in_traj']}]"
            print(f"{marker} traj_global={r['global_traj_idx']:>5} traj_local={r['local_traj_idx']:>3} "
                  f"chars={r['chars_up_to_error']:>7} ai_steps={r['ai_steps_up_to_error']:>3} "
                  f"step={r['step_idx']:>3}  {r['normalized_pattern'][:45]}")


def cmd_show(args):
    trajs, exits = load_trajectories(args.instance_id)
    if args.traj >= len(trajs):
        print(f"Ошибка: traj={args.traj}, всего траекторий={len(trajs)}")
        return
    traj = trajs[args.traj]
    if args.step >= len(traj):
        print(f"Ошибка: step={args.step}, шагов в траектории={len(traj)}")
        return
    print(f"instance_id={args.instance_id}  traj=local:{args.traj}  exit={exits[args.traj] if args.traj < len(exits) else '?'}")
    print("=" * 50)
    show_step(traj, args.step, context=args.context)


def cmd_sample(args):
    errors = load_errors(args.category)
    rng = random.Random(args.seed)

    # сначала уникальные (одна запись на instance_id)
    seen = set()
    unique, rest = [], []
    for r in errors:
        if r["instance_id"] not in seen:
            seen.add(r["instance_id"])
            unique.append(r)
        else:
            rest.append(r)

    rng.shuffle(unique)
    rng.shuffle(rest)
    pool = unique + rest
    sample = pool[:args.n]

    for i, r in enumerate(sample, 1):
        print(f"\n{'='*60}")
        marker = "[NEW]" if r["is_first_occurrence_in_traj"] else f"[DUP {r['occurrence_in_traj']}]"
        print(f"[{i}/{len(sample)}] {marker} instance_id={r['instance_id']}  category={r['category']}")
        print(f"pattern: {r['normalized_pattern']}")
        print(f"text:\n{r['text'][:1000]}")


def cmd_fp_check(args):
    all_errors = load_errors(args.category)
    match = [r for r in all_errors
             if r["instance_id"] == args.instance_id
             and r["global_traj_idx"] == args.traj_idx
             and r["step_idx"] == args.step_idx]
    if not match:
        print(f"Не найдено: instance_id={args.instance_id} traj={args.traj_idx} step={args.step_idx}")
        return
    r = match[0]
    print(f"instance_id={r['instance_id']}  category={r['category']}")
    print(f"traj_global={r['global_traj_idx']}  traj_local={r['local_traj_idx']}")
    print(f"chars_up_to_error={r['chars_up_to_error']}  ai_steps_up_to_error={r['ai_steps_up_to_error']}")
    print(f"pattern: {r['normalized_pattern']}")
    print(f"occurrence_in_traj={r['occurrence_in_traj']}  is_first={r['is_first_occurrence_in_traj']}")
    trajs, exits = load_trajectories(r["instance_id"])
    show_step(trajs[r["local_traj_idx"]], r["step_idx"], context=1)


def main():
    parser = argparse.ArgumentParser(description="CLI для анализа ошибок nebius_invalid_invocation (плоский формат)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="Топ ошибок по категории")
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--min-count", type=int, default=1)

    p = sub.add_parser("inspect", help="Все ошибки для instance_id с пометками NEW/DUPLICATE")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--category", default="all", choices=CATEGORIES + ["all"])

    p = sub.add_parser("show", help="Показать шаг из parquet")
    p.add_argument("--instance-id", required=True)
    p.add_argument("--traj", type=int, required=True)
    p.add_argument("--step", type=int, required=True)
    p.add_argument("--context", type=int, default=1)

    p = sub.add_parser("sample", help="Случайная выборка для FP-проверки")
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--n", type=int, default=20)
    p.add_argument("--seed", type=int, default=42)

    p = sub.add_parser("fp-check", help="Одна ошибка по (instance_id, traj_idx, step_idx)")
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--traj-idx", type=int, required=True)
    p.add_argument("--step-idx", type=int, required=True)

    args = parser.parse_args()
    {"list": cmd_list, "inspect": cmd_inspect, "show": cmd_show,
     "sample": cmd_sample, "fp-check": cmd_fp_check}[args.cmd](args)


if __name__ == "__main__":
    main()