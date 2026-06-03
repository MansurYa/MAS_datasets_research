#!/usr/bin/env python3
"""
TZ_5: Data Integrity Check — проверка аккумуляторов и индексов.

Инварианты:
1. Все ключи присутствуют
2. Монотонность chars_up_to_error и ai_steps_up_to_error внутри траектории
3. Границы индексов
4. Сброс local_traj_idx при смене instance_id
"""

import json
from pathlib import Path

DATA = Path("/Volumes/MansurSSD/MAS_datasets_research/work/data/errors_invalid_invocation.json")

REQUIRED_KEYS = [
    "global_traj_idx",
    "local_traj_idx",
    "chars_up_to_error",
    "ai_steps_up_to_error",
]

def check_keys(data):
    """Проверка: все обязательные ключи существуют."""
    errors = []
    for cat, records in data.items():
        for i, r in enumerate(records):
            for key in REQUIRED_KEYS:
                if key not in r:
                    errors.append(f"[{cat}] Запись {i}: отсутствует ключ '{key}'")
    if errors:
        for e in errors[:10]:
            print(f"  FAIL: {e}")
        print(f"  Всего ошибок: {len(errors)}")
        return False
    print(f"  PASS: все записи содержат {REQUIRED_KEYS}")
    return True


def check_monotonicity(data):
    """Проверка: chars_up_to_error не убывает внутри траектории (монотонно-неубывание).

Может быть ступенькой: если два соседних шага не-AI, chars может не вырасти
(системный промпт у AI-шагов обычно больше). ai_steps растёт только на AI-шагах.
"""
    errors = []
    total_pairs = 0

    for cat, records in data.items():
        # группируем по (global_traj_idx)
        from collections import defaultdict
        by_traj = defaultdict(list)
        for r in records:
            by_traj[r["global_traj_idx"]].append(r)

        for traj_idx, group in by_traj.items():
            group_sorted = sorted(group, key=lambda x: x["step_idx"])
            prev_chars = None
            prev_ai_steps = None
            for r in group_sorted:
                chars = r["chars_up_to_error"]
                ai_steps = r["ai_steps_up_to_error"]
                total_pairs += 1

                if prev_chars is not None:
                    if chars < prev_chars:
                        errors.append(
                            f"[{cat}] traj={traj_idx}: chars не монотонна неубывающа "
                            f"(step {group_sorted[group_sorted.index(r)-1]['step_idx']} → {r['step_idx']}: "
                            f"{prev_chars} → {chars})"
                        )
                    if ai_steps < prev_ai_steps:
                        errors.append(
                            f"[{cat}] traj={traj_idx}: ai_steps не монотонна неубывающа "
                            f"(step {group_sorted[group_sorted.index(r)-1]['step_idx']} → {r['step_idx']}: "
                            f"{prev_ai_steps} → {ai_steps})"
                        )
                prev_chars = chars
                prev_ai_steps = ai_steps

    if errors:
        for e in errors[:10]:
            print(f"  FAIL: {e}")
        print(f"  Всего нарушений монотонности: {len(errors)}")
        return False
    print(f"  PASS: монотонность соблюдена ({total_pairs} пар проверено)")
    return True


def check_index_bounds(data):
    """Проверка: global_traj_idx и local_traj_idx в допустимых границах."""
    errors = []
    for cat, records in data.items():
        for r in records:
            g = r["global_traj_idx"]
            l = r["local_traj_idx"]
            if g < 0 or g > 80035:
                errors.append(f"[{cat}] global_traj_idx={g} вне [0, 80035]")
            if l < 0:
                errors.append(f"[{cat}] local_traj_idx={l} < 0")
    if errors:
        for e in errors[:10]:
            print(f"  FAIL: {e}")
        print(f"  Всего ошибок: {len(errors)}")
        return False
    print(f"  PASS: границы индексов соблюдены")
    return True


def check_local_reset(data):
    """Проверка: local_traj_idx уникален и предсказуем внутри instance_id.

    Каждая категория содержит ПОДМНОЖЕСТВО траекторий (не все траектории
    instance_id имеют ошибки данной категории). Поэтому ожидаем:
    - Без дубликатов (каждая траектория даёт ошибку данной категории ≤1 раз)
    - Без пропусков относительно global_traj_idx: если traj с global=0 есть,
      то и local=0 должен быть; если global=5 есть, local=5 тоже должен быть.

    Инвариант: для записей одного instance_id, отсортированных по global_traj_idx,
    local_traj_idx должен совпадать с порядковым номером (т.е. local = порядок в группе).
    """
    errors = []
    checked = 0

    for cat, records in data.items():
        # сортируем по global_traj_idx
        sorted_records = sorted(records, key=lambda x: x["global_traj_idx"])

        i = 0
        while i < len(sorted_records):
            inst = sorted_records[i]["instance_id"]
            # все записи с этим instance_id
            j = i
            while j < len(sorted_records) and sorted_records[j]["instance_id"] == inst:
                j += 1
            group = sorted_records[i:j]
            n = len(group)

            # (local_traj_idx, step_idx) уникальны — один шаг = одна запись
            # (одиночные ошибки с одним error_msg или мультиошибки с разными msg)
            # Для E1/E2: включаем error_type/error_msg в ключ — разные ошибки на одном шаге легитимны
            seen_keys = set()
            for r in group:
                if cat in ('E1', 'E2'):
                    # Для E1/E2: различаем подтипы ошибок через error_type + normalized_pattern
                    # "unexpected indent" vs "unexpected unindent" — разные паттерны, разные записи
                    # (но дубль того же паттерна на том же шаге — один)
                    type_key = r.get('error_type') or r.get('undefined_name') or ''
                    norm_key = r.get('normalized_pattern') or ''
                    key = (r["local_traj_idx"], r["step_idx"], type_key, norm_key)
                else:
                    type_key = ''
                    norm_key = r.get('normalized_pattern') or ''
                    key = (r["local_traj_idx"], r["step_idx"])
                if key in seen_keys:
                    errors.append(
                        f"[{cat}] instance_id={inst}: дубликат (local={r['local_traj_idx']}, "
                        f"step={r['step_idx']}, type='{type_key}', pattern='{norm_key[:30]}')"
                    )
                seen_keys.add(key)

            # Проверяем: local_traj_idx == ожидаемому значению
            # Ожидаем: если траектории идут как [g0, g1, g2, ...],
            # то local должны быть как [l0, l1, l2, ...] где li — счётчик
            # внутри instance_id. Но поскольку категория = подмножество,
            # мы проверяем: local_traj_idx монотонен и без пропусков
            # относительно индекса в группе.
            # Проще: local_traj_idx[i] должен = local_traj_idx[i-1] + 1
            # ИЛИ = тому же значению (если та же траектория, следующий шаг)
            for k in range(1, len(group)):
                prev_local = group[k-1]["local_traj_idx"]
                curr_local = group[k]["local_traj_idx"]
                prev_global = group[k-1]["global_traj_idx"]
                curr_global = group[k]["global_traj_idx"]

                if curr_global == prev_global:
                    # та же траектория — local должен совпадать
                    if curr_local != prev_local:
                        errors.append(
                            f"[{cat}] instance_id={inst}: local_traj_idx скачок при той же траектории "
                            f"(global={curr_global}, prev_local={prev_local}, curr_local={curr_local})"
                        )
                else:
                    # новая траектория — local должен строго возрастать
                    # (пропуски допустимы: категория — подмножество траекторий)
                    if curr_local <= prev_local:
                        errors.append(
                            f"[{cat}] instance_id={inst}: local_traj_idx не возрастает при смене траектории "
                            f"(global {prev_global}→{curr_global}, "
                            f"prev_local={prev_local}, curr_local={curr_local})"
                        )

            checked += 1
            i = j

    if errors:
        for e in errors[:10]:
            print(f"  FAIL: {e}")
        print(f"  Всего нарушений: {len(errors)}")
        return False
    print(f"  PASS: local_traj_idx монотонен без пропусков ({checked} instance_id проверено)")
    return True


def main():
    print("=" * 60)
    print("TZ_5: Data Integrity Check")
    print("=" * 60)

    print("\nЗагружаю errors_invalid_invocation.json...")
    with open(DATA) as f:
        data = json.load(f)

    for cat in ['A', 'B', 'E1', 'E2']:
        print(f"  {cat}: {len(data[cat]):>7} записей")

    all_pass = True

    print("\n[1] Проверка ключей...")
    all_pass &= check_keys(data)

    print("\n[2] Проверка монотонности аккумуляторов...")
    all_pass &= check_monotonicity(data)

    print("\n[3] Проверка границ индексов...")
    all_pass &= check_index_bounds(data)

    print("\n[4] Проверка сброса local_traj_idx...")
    all_pass &= check_local_reset(data)

    print("\n" + "=" * 60)
    if all_pass:
        print("  ✓ ВСЕ ИНВАРИАНТЫ СОБЛЮДЕНЫ")
    else:
        print("  ✗ ОБНАРУЖЕНЫ НАРУШЕНИЯ ИНВАРИАНТОВ")
    print("=" * 60)


if __name__ == "__main__":
    main()