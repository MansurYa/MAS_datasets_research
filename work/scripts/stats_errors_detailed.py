#!/usr/bin/env python3
"""
Статистика ошибок с четырьмя вариантами подсчёта.
Упрощённая версия — используем уже подсчитанные данные.
"""

import json
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = PROJECT_ROOT / "work" / "data"
CATEGORIES = ["A", "B", "C", "D", "E1", "E2"]

# Загружаем ошибки
traj_info = defaultdict(lambda: {cat: {"count": 0, "unique": 0} for cat in CATEGORIES})

for cat in CATEGORIES:
    path = DATA_DIR / f"nebius_invalid_invocation_errors_{cat}.json"
    with open(path) as f:
        errors = json.load(f)

    for error in errors:
        for loc in error["locations"]:
            key = (loc["instance_id"], loc["traj_idx"])
            traj_info[key][cat]["count"] += error["count"]
            traj_info[key][cat]["unique"] += 1

total_trajs = 80036
trajs_with_errors = len(traj_info)
trajs_without_errors = total_trajs - trajs_with_errors

print(f"Всего траекторий: {total_trajs}")
print(f"Траекторий с ошибками: {trajs_with_errors}")
print(f"Траекторий без ошибок: {trajs_without_errors}")
print()

# Вариант 1: Уникальные, все траектории
print("="*70)
print("ВАРИАНТ 1: УНИКАЛЬНЫЕ ОШИБКИ (считая все {0} траектории)".format(total_trajs))
print("="*70)
print(f"{'Тип':<6} {'Среднее':<12} {'Макс':<6} {'Сумма':<10}")
print("-" * 40)

total_unique_all = 0
for cat in CATEGORIES:
    total = sum(traj_info[key][cat]["unique"] for key in traj_info)
    max_val = max((traj_info[key][cat]["unique"] for key in traj_info), default=0)
    avg = total / total_trajs
    total_unique_all += total
    print(f"{cat:<6} {avg:>11.3f} {max_val:>5} {total:>9}")

print("-" * 40)
print(f"{'ИТОГО':<6} {total_unique_all/total_trajs:>11.3f} {'':<5} {total_unique_all:>9}")

# Вариант 2: Уникальные, только траектории с ошибками
print("\n" + "="*70)
print("ВАРИАНТ 2: УНИКАЛЬНЫЕ ОШИБКИ (только траектории с ошибками)")
print("="*70)
print(f"{'Тип':<6} {'Среднее':<12} {'Макс':<6} {'Сумма':<10}")
print("-" * 40)

total_unique_with = 0
for cat in CATEGORIES:
    counts = [traj_info[key][cat]["unique"] for key in traj_info]
    if counts:
        avg = sum(counts) / len(counts)
        max_val = max(counts)
        total = sum(counts)
        total_unique_with += total
        print(f"{cat:<6} {avg:>11.3f} {max_val:>5} {total:>9}")

print("-" * 40)
print(f"{'ИТОГО':<6} {total_unique_with/trajs_with_errors:>11.3f} {'':<5} {total_unique_with:>9}")

# Вариант 3: Все вхождения, все траектории
print("\n" + "="*70)
print("ВАРИАНТ 3: ВСЕ ВХОЖДЕНИЯ (считая все {0} траектории)".format(total_trajs))
print("="*70)
print(f"{'Тип':<6} {'Среднее':<12} {'Макс':<10} {'Сумма':<12}")
print("-" * 45)

total_all_all = 0
for cat in CATEGORIES:
    total = sum(traj_info[key][cat]["count"] for key in traj_info)
    max_val = max((traj_info[key][cat]["count"] for key in traj_info), default=0)
    avg = total / total_trajs
    total_all_all += total
    print(f"{cat:<6} {avg:>11.3f} {max_val:>9} {total:>11}")

print("-" * 45)
print(f"{'ИТОГО':<6} {total_all_all/total_trajs:>11.3f} {'':<9} {total_all_all:>11}")

# Вариант 4: Все вхождения, только траектории с ошибками
print("\n" + "="*70)
print("ВАРИАНТ 4: ВСЕ ВХОЖДЕНИЯ (только траектории с ошибками)")
print("="*70)
print(f"{'Тип':<6} {'Среднее':<12} {'Макс':<10} {'Сумма':<12}")
print("-" * 45)

total_all_with = 0
for cat in CATEGORIES:
    counts = [traj_info[key][cat]["count"] for key in traj_info]
    if counts:
        avg = sum(counts) / len(counts)
        max_val = max(counts)
        total = sum(counts)
        total_all_with += total
        print(f"{cat:<6} {avg:>11.3f} {max_val:>9} {total:>11}")

print("-" * 45)
print(f"{'ИТОГО':<6} {total_all_with/trajs_with_errors:>11.3f} {'':<9} {total_all_with:>11}")
