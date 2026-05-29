#!/usr/bin/env python3
"""
Статистика: среднее количество ошибок на траекторию (ИСПРАВЛЕННАЯ ВЕРСИЯ).

count = количество locations (вхождений этой ошибки)
Нужно считать: для каждой траектории, сколько РАЗНЫХ ошибок в ней встречается.
"""

import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = PROJECT_ROOT / "work" / "data"
CATEGORIES = ["A", "B", "C", "D", "E1", "E2"]

# Для каждой траектории считаем сколько разных ошибок в ней
# traj_errors[instance_id][traj_idx] = set of (category, pattern_hash)
traj_errors = defaultdict(lambda: defaultdict(set))

for cat in CATEGORIES:
    path = DATA_DIR / f"nebius_invalid_invocation_errors_{cat}.json"
    with open(path) as f:
        errors = json.load(f)

    for error in errors:
        instance_id = error["instance_id"]
        pattern_hash = error.get("pattern_hash", "")

        # Для каждого location этой ошибки добавляем её в траекторию
        for loc in error["locations"]:
            traj_idx = loc["traj_idx"]
            key = (cat, pattern_hash)
            traj_errors[instance_id][traj_idx].add(key)

print(f"Траекторий с ошибками: {sum(len(v) for v in traj_errors.values())}")

# Считаем статистику по типам
stats = defaultdict(list)  # category -> [counts per trajectory]

for instance_id in traj_errors:
    for traj_idx in traj_errors[instance_id]:
        errors_in_traj = traj_errors[instance_id][traj_idx]
        # Группируем по категориям
        by_cat = defaultdict(int)
        for cat, _ in errors_in_traj:
            by_cat[cat] += 1

        for cat in CATEGORIES:
            stats[cat].append(by_cat[cat])

print("\n" + "="*60)
print("СТАТИСТИКА: РАЗНЫЕ ОШИБКИ НА ТРАЕКТОРИЮ")
print("="*60)
print(f"{'Тип':<6} {'Среднее':<10} {'Макс':<10} {'Сумма':<12}")
print("-" * 40)

total_errors = 0
total_trajs = sum(len(v) for v in traj_errors.values())

for cat in CATEGORIES:
    if stats[cat]:
        avg = sum(stats[cat]) / len(stats[cat])
        max_val = max(stats[cat])
        total = sum(stats[cat])
        total_errors += total
        print(f"{cat:<6} {avg:>9.2f} {max_val:>9} {total:>11}")
    else:
        print(f"{cat:<6} {'0':<9} {'0':<9} {'0':<11}")

print("-" * 40)
print(f"{'ИТОГО':<6} {total_errors/total_trajs:>9.2f} {'':<9} {total_errors:>11}")

print("\n" + "="*60)
print("ИТОГОВАЯ СВОДКА")
print("="*60)
print(f"Траекторий с ошибками: {total_trajs}")
print(f"Среднее разных ошибок на траекторию: {total_errors/total_trajs:.2f}")
