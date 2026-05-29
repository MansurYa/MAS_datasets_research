#!/usr/bin/env python3
"""
CLI для анализа ошибок nebius_invalid_invocation.

Команды:
  list      -- топ ошибок по категории
  inspect   -- все ошибки для instance_id
  show      -- шаг из parquet с контекстом
  sample    -- случайная выборка для FP-проверки
  fp-check  -- одна ошибка по pattern_hash с контекстом из parquet
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


def load_errors(category):
    path = DATA_DIR / f"nebius_invalid_invocation_errors_{category}.json"
    with open(path) as f:
        return json.load(f)


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
    df = pd.DataFrame(errors)
    df["num_trajs"] = df["locations"].apply(lambda locs: len(set(l["traj_idx"] for l in locs)))
    df = df[df["count"] >= args.min_count].sort_values("count", ascending=False).head(args.top)
    for _, r in df.iterrows():
        print(f"{r['instance_id']:<45} count={r['count']:>4}  trajs={r['num_trajs']:>3}  {r['normalized_pattern'][:60]}")


def cmd_inspect(args):
    categories = CATEGORIES if args.category == "all" else [args.category]
    for cat in categories:
        errors = load_errors(cat)
        for r in errors:
            if r["instance_id"] != args.instance_id:
                continue
            for traj, step in r["traj_step_pairs"]:
                print(f"[{r['category']}] traj={traj:>3}  step={step:>3}  count={r['count']:>4}  {r['normalized_pattern'][:60]}")


def cmd_show(args):
    trajs, exits = load_trajectories(args.instance_id)
    if args.traj >= len(trajs):
        print(f"Ошибка: traj={args.traj}, всего траекторий={len(trajs)}")
        return
    traj = trajs[args.traj]
    if args.step >= len(traj):
        print(f"Ошибка: step={args.step}, шагов в траектории={len(traj)}")
        return
    print(f"instance_id={args.instance_id}  traj={args.traj}  exit={exits[args.traj] if args.traj < len(exits) else '?'}")
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
        print(f"[{i}/{len(sample)}] instance_id={r['instance_id']}  category={r['category']}  count={r['count']}")
        print(f"pattern: {r['normalized_pattern']}")
        print(f"text:\n{r['text'][:1000]}")


def cmd_fp_check(args):
    errors = load_errors(args.category)
    match = [r for r in errors if r["instance_id"] == args.instance_id and r.get("pattern_hash") == args.pattern_hash]
    if not match:
        print(f"Не найдено: instance_id={args.instance_id} pattern_hash={args.pattern_hash}")
        return
    r = match[0]
    print(f"instance_id={r['instance_id']}  category={r['category']}  count={r['count']}")
    print(f"pattern: {r['normalized_pattern']}")
    print(f"\nПервое вхождение: traj={r['traj_idx']} step={r['step_idx']}")
    print("=" * 50)
    trajs, exits = load_trajectories(r["instance_id"])
    show_step(trajs[r["traj_idx"]], r["step_idx"], context=1)


def main():
    parser = argparse.ArgumentParser(description="CLI для анализа ошибок nebius_invalid_invocation")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list", help="Топ ошибок по категории")
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--top", type=int, default=20)
    p.add_argument("--min-count", type=int, default=1)

    p = sub.add_parser("inspect", help="Все ошибки для instance_id")
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

    p = sub.add_parser("fp-check", help="Одна ошибка с контекстом для FP-оценки")
    p.add_argument("--category", required=True, choices=CATEGORIES)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--pattern-hash", required=True)

    args = parser.parse_args()
    {"list": cmd_list, "inspect": cmd_inspect, "show": cmd_show,
     "sample": cmd_sample, "fp-check": cmd_fp_check}[args.cmd](args)


if __name__ == "__main__":
    main()
