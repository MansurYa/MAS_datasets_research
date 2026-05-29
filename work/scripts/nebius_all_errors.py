#!/usr/bin/env python3
"""
Унифицированный парсер для всех категорий ошибок nebius/SWE-agent-trajectories.

Использует ds.dataset() для чтения ВСЕХ шардов сразу.
traj_idx = локальный индекс траектории в traj_list для ДАННОГО instance_id (0, 1, 2...).

Категории:
  A: FileNotFoundError, No such file or directory
  B: command not found, cannot access, cannot stat (исключая ls: cannot access)
  C: unexpected keyword argument, takes X positional arguments but Y were given
  D: missing required argument
  E1: Edit tool E999 (SyntaxError, IndentationError)
  E2: Edit tool F821 (undefined name)

Выходной JSON (унифицированный формат):
{
  "instance_id": "...",
  "category": "A",
  "count": 5,
  "locations": [
    {"traj_idx": 0, "step_idx": 9, "text": "...", "exit_status": "..."},
    {"traj_idx": 2, "step_idx": 11, "text": "...", "exit_status": "..."}
  ],
  "traj_idxs": [0, 2],
  "step_idxs": [9, 11],
  "traj_idx": 0,
  "step_idx": 9,
  "normalized_pattern": "...",
  "text": "..."
}
"""

import pyarrow.dataset as ds
from pathlib import Path
import re
import json
import hashlib
from collections import defaultdict

PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
PARQUET_DIR = PROJECT_ROOT / "datasets" / "nebius-SWE-agent-trajectories" / "data"
DATA_PATH = PROJECT_ROOT / "work" / "data"
DOCS_PATH = PROJECT_ROOT / "work" / "docs"

# === Edit tool patterns (E1, E2) ===
EDIT_HEADER = "Your proposed edit has introduced new syntax error"
ERRORS_BLOCK_RE = re.compile(r'ERRORS:\s*\n((?:- .*\n?)+)', re.MULTILINE)
ERROR_LINE_RE = re.compile(r'^- (E\d+|F\d+|W\d+)\s+(.*)$')
EDIT_BLOCK_RE = re.compile(
    r'This is how your edit would have looked if applied\s*\n[-]+\s*\n(.*?)\n[-]+',
    re.DOTALL,
)

# === User script patterns (C, D) ===
USER_SCRIPT_PATTERNS = [
    r'/reproduce\.py',
    r'/test_[\w]+\.py',
    r'/print_args\.py',
    r'/run_[\w]+\.py',
]
USER_SCRIPT_RE = re.compile('|'.join(USER_SCRIPT_PATTERNS))

# === D: интерактивный режим — отсекаем ===
INTERACTIVE_RE = re.compile(r'(bash-\$\s*$|\(Current directory:)', re.MULTILINE)


def normalize_error_pattern(text: str) -> str:
    """Нормализация ошибки для дедипликации."""
    t = text
    t = re.split(r'\(Open file:|\(Current directory:|bash-\$', t)[0]
    t = re.sub(r"'[^']{0,200}'", "'X'", t)
    t = re.sub(r'"[^"]{0,200}"', '"X"', t)
    t = re.sub(r'/[\w\-./]+', '/X', t)
    t = re.sub(r'\bline\s+\d+', 'line N', t, flags=re.IGNORECASE)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


# === Категория A: FileNotFoundError ===

def matches_A(text: str) -> bool:
    if 'FileNotFoundError' not in text and 'No such file or directory' not in text:
        return False
    if re.search(r'\bline\s+\d+', text, re.IGNORECASE):
        return False
    if 'ModuleNotFoundError' in text or 'ImportError' in text:
        return False
    if 'pytest' in text or 'fixture' in text:
        return False
    return True


# === Категория B: bash commands ===

def matches_B(text: str) -> bool:
    if not ('command not found' in text or 'cannot access' in text or 'cannot stat' in text):
        return False
    if 'ls: cannot access' in text:
        return False
    if 'SyntaxError' in text or 'syntax error' in text:
        return False
    if 'grep' in text and ('pattern' in text or 'search' in text):
        return False
    if 'python' in text.lower() and 'not found' in text:
        return False
    # --- НОВЫЙ ФИЛЬТР (2026-05-29) ---
    # FP: markdown-блок из рассуждений агента (``` невозможен в реальном bash stderr)
    if '```' in text:
        return False
    return True


# === Категория C: TypeError (ОТКЛЮЧЕНА 2026-05-29) ===
# Категория C отключена, так как она ловит рантайм-ошибки кодогенерации (100% FP rate),
# а не отказы pre-execution валидации инструментов.
# Код сохранён для будущих задач по анализу Категории 1 (runtime errors).
#
# def matches_C(text: str) -> bool:
#     if not ('unexpected keyword argument' in text or
#             ('takes' in text and 'positional argument' in text)):
#         return False
#     if text.lstrip().startswith('[File:'):
#         return False
#     if 'FutureWarning' in text and 'TypeError' not in text:
#         return False
#     if 'unsupported operand' in text:
#         return False
#     if 'NoneType' in text and 'object' in text:
#         return False
#     if 'Traceback' in text and USER_SCRIPT_RE.search(text):
#         return False
#     return True


# === Категория D: missing arguments (ОТКЛЮЧЕНА 2026-05-29) ===
# Категория D отключена, так как после добавления Traceback-фильтра выяснилось,
# что паттерн "missing"+"required"+"argument" ловит ТОЛЬКО CoT-рассуждения агента
# о недостающих параметрах (100% INVALID). Фраза не является маркером
# invalid_invocation — она означает либо рантайм (argparse), либо рассуждения LLM.
# Код сохранён для истории.
#
# def matches_D(text: str) -> bool:
#     if not ('missing' in text and 'required' in text and 'argument' in text):
#         return False
#     if text.lstrip().startswith('[File:'):
#         return False
#     if '__init__()' in text:
#         return False
#     if "'self'" in text:
#         return False
#     if 'config' in text.lower() and 'parameter' in text.lower():
#         return False
#     if 'dependency' in text or 'dependencies' in text:
#         return False
#     if 'Traceback' in text:
#         return False
#     if INTERACTIVE_RE.search(text):
#         return False
#     return True


# === Категории E1, E2: Edit tool ===

def parse_edit_errors(text: str):
    m = ERRORS_BLOCK_RE.search(text)
    if not m:
        return []
    block = m.group(1)
    out = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith('-'):
            continue
        em = ERROR_LINE_RE.match(line)
        if em:
            out.append((em.group(1), em.group(2)))
    return out


def extract_edit_block(text: str) -> str:
    m = EDIT_BLOCK_RE.search(text)
    if m:
        return m.group(1)
    return ''


def has_import(edit_block: str, name: str) -> bool:
    if not edit_block:
        return False
    pattern_module = re.compile(rf'^\s*\d*:?\s*import\s+{re.escape(name)}\b', re.MULTILINE)
    pattern_from = re.compile(rf'^\s*\d*:?\s*from\s+\S+\s+import\s+.*\b{re.escape(name)}\b', re.MULTILINE)
    return bool(pattern_module.search(edit_block) or pattern_from.search(edit_block))


def matches_E(text: str) -> bool:
    return EDIT_HEADER in text


def process_trajectories():
    """
    Обработать все траектории, собрать ошибки по категориям.

    traj_idx = локальный индекс в traj_list для данного instance_id.
    """
    print("Загружаю датасет (все шарды)...")
    dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
    table = dataset.to_table()
    d = table.to_pydict()

    instance_ids = d["instance_id"]
    trajectories = d["trajectory"]
    exit_statuses = d.get("exit_status", [None] * len(instance_ids))

    print(f"Найдено строк (все шарды): {len(instance_ids)}")

    # Группируем по instance_id
    instance_rows = defaultdict(list)
    for row_idx in range(len(instance_ids)):
        inst = instance_ids[row_idx]
        instance_rows[inst].append(row_idx)

    print(f"Уникальных instance_id: {len(instance_rows)}")

    # Инициализация
    A_candidates = []
    B_candidates = []
    # C_candidates = []  # ОТКЛЮЧЕНА 2026-05-29 (100% FP)
    # D_candidates = []  # ОТКЛЮЧЕНА 2026-05-29 (100% INVALID)
    E1_candidates = []
    E2_candidates = []

    total_trajs = sum(len(v) for v in instance_rows.values())
    processed = 0

    for inst, row_indices in instance_rows.items():
        for local_traj_idx, row_idx in enumerate(row_indices):
            traj = trajectories[row_idx]
            exit_s = exit_statuses[row_idx] if row_idx < len(exit_statuses) else None
            traj_idx = local_traj_idx  # локальный индекс

            for step_idx, step in enumerate(traj):
                if not isinstance(step, dict) or 'text' not in step:
                    continue

                text = step.get('text')
                if text is None:
                    continue

                base = {
                    'instance_id': inst,
                    'traj_idx': traj_idx,
                    'step_idx': step_idx,
                    'exit_status': exit_s,
                    'text': text,
                }

                # === A: FileNotFoundError ===
                if matches_A(text):
                    A_candidates.append({**base})

                # === B: bash commands ===
                if matches_B(text):
                    B_candidates.append({**base})

                # # === C: TypeError (ОТКЛЮЧЕНА 2026-05-29) ===
                # if matches_C(text):
                #     C_candidates.append({**base})

                # # === D: missing args (ОТКЛЮЧЕНА 2026-05-29: 100% INVALID) ===
                # # after Traceback filter, the only remaining "missing"+"required"+"argument"
                # # were agent CoT reasoning — NOT pre-execution validator rejections
                # if matches_D(text):
                #     D_candidates.append({**base})

                # === E: Edit tool errors ===
                if matches_E(text):
                    errors = parse_edit_errors(text)
                    if errors:
                        edit_block = extract_edit_block(text)

                        e999_errors = [(c, m) for c, m in errors if c == 'E999']
                        if e999_errors:
                            for c, m in e999_errors:
                                E1_candidates.append({
                                    **base,
                                    'error_code': c,
                                    'error_msg': m,
                                })

                        f821_errors = [(c, m) for c, m in errors if c == 'F821']
                        if f821_errors:
                            for c, m in f821_errors:
                                name_match = re.search(r"undefined name '([^']+)'", m)
                                name = name_match.group(1) if name_match else None
                                import_present = has_import(edit_block, name) if name else None
                                E2_candidates.append({
                                    **base,
                                    'error_code': c,
                                    'error_msg': m,
                                    'undefined_name': name,
                                    'import_present_in_edit': import_present,
                                })

            processed += 1
            if processed % 10000 == 0:
                print(f"  Обработано траекторий: {processed}/{total_trajs}")

    print(f"Траекторий обработано: {processed}")

    return {
        'A': A_candidates,
        'B': B_candidates,
        # 'C': C_candidates,  # ОТКЛЮЧЕНА 2026-05-29 (100% FP)
        # 'D': D_candidates,  # ОТКЛЮЧЕНА 2026-05-29 (100% INVALID)
        'E1': E1_candidates,
        'E2': E2_candidates,
    }


def deduplicate(candidates, extra_keys=(), error_msg_field='text', category=''):
    """
    Дедипликация по (instance_id, error_pattern_hash + extra_keys).

    Формат выхода:
    {
      "instance_id": "...",
      "category": "A",
      "count": 5,
      "locations": [
        {"traj_idx": 0, "step_idx": 9, "text": "...", "exit_status": "..."},
        ...
      ],
      "traj_step_pairs": [[0, 9], [2, 11]],
      "traj_idx": 0,
      "step_idx": 9,
      "normalized_pattern": "...",
      "text": "..."
    }
    """
    groups = defaultdict(list)
    for c in candidates:
        pattern_input = c.get('error_msg', c.get(error_msg_field, ''))
        pattern = normalize_error_pattern(pattern_input)
        h = hashlib.md5(pattern.encode()).hexdigest()[:12]
        extra = tuple(c.get(k) for k in extra_keys)
        key = (c['instance_id'], h, extra)
        groups[key].append(c)

    unique = []
    for key, items in groups.items():
        first = items[0]

        locations = []
        for c in items:
            loc = {
                'instance_id': c['instance_id'],
                'traj_idx': c['traj_idx'],
                'step_idx': c['step_idx'],
                'exit_status': c.get('exit_status'),
                'text': c.get('text'),
            }
            for k in extra_keys:
                loc[k] = c.get(k)
            locations.append(loc)

        all_pairs = sorted(set((c['traj_idx'], c['step_idx']) for c in items))

        record = {
            'instance_id': first['instance_id'],
            'category': category,
            'count': len(items),
            'locations': locations,
            'traj_step_pairs': [list(p) for p in all_pairs],
            'traj_idx': first['traj_idx'],
            'step_idx': first['step_idx'],
            'exit_status': first.get('exit_status'),
            'normalized_pattern': normalize_error_pattern(
                first.get('error_msg', first.get(error_msg_field, ''))
            ),
            'text': first['text'],
        }
        for k in extra_keys:
            record[k] = first.get(k)
        unique.append(record)

    unique.sort(key=lambda x: -x['count'])
    return unique


def estimate_sample_size(n_candidates):
    if n_candidates < 20:
        return n_candidates
    elif n_candidates < 200:
        return 20
    elif n_candidates < 1000:
        return 50
    elif n_candidates < 5000:
        return 100
    else:
        return 150


def main():
    print("=" * 60)
    print("nebius_invalid_invocation_errors: Унифицированный парсер")
    print("=" * 60)

    candidates_by_cat = process_trajectories()

    DATA_PATH.mkdir(parents=True, exist_ok=True)

    # Категория A
    print("\n--- Категория A (FileNotFoundError) ---")
    print(f"Сырых кандидатов: {len(candidates_by_cat['A'])}")
    A_unique = deduplicate(candidates_by_cat['A'], category='A')
    print(f"Уникальных событий: {len(A_unique)}")

    with open(DATA_PATH / "nebius_invalid_invocation_errors_A.json", 'w') as f:
        json.dump(A_unique, f, indent=2, ensure_ascii=False)
    print(f"Сохранено: {DATA_PATH / 'nebius_invalid_invocation_errors_A.json'}")

    # Категория B
    print("\n--- Категория B (bash commands) ---")
    print(f"Сырых кандидатов: {len(candidates_by_cat['B'])}")
    B_unique = deduplicate(candidates_by_cat['B'], category='B')
    print(f"Уникальных событий: {len(B_unique)}")

    with open(DATA_PATH / "nebius_invalid_invocation_errors_B.json", 'w') as f:
        json.dump(B_unique, f, indent=2, ensure_ascii=False)
    print(f"Сохранено: {DATA_PATH / 'nebius_invalid_invocation_errors_B.json'}")

    # === Категория C (ОТКЛЮЧЕНА 2026-05-29) ===
    # print("\n--- Категория C (TypeError) ---")
    # print(f"Сырых кандидатов: {len(candidates_by_cat['C'])}")
    # C_unique = deduplicate(candidates_by_cat['C'], category='C')
    # print(f"Уникальных событий: {len(C_unique)}")
    # with open(DATA_PATH / "nebius_invalid_invocation_errors_C.json", 'w') as f:
    #     json.dump(C_unique, f, indent=2, ensure_ascii=False)
    # print(f"Сохранено: {DATA_PATH / 'nebius_invalid_invocation_errors_C.json'}")

    # # Категория D (ОТКЛЮЧЕНА 2026-05-29: 100% INVALID)
    # # паттерн "missing"+"required"+"argument" ловит CoT-рассуждения агента, не invalid_invocation
    # print("\n--- Категория D (missing args) ---")
    # print(f"Сырых кандидатов: {len(candidates_by_cat['D'])}")
    # D_unique = deduplicate(candidates_by_cat['D'], category='D')
    # print(f"Уникальных событий: {len(D_unique)}")
    # with open(DATA_PATH / "nebius_invalid_invocation_errors_D.json", 'w') as f:
    #     json.dump(D_unique, f, indent=2, ensure_ascii=False)
    # print(f"Сохранено: {DATA_PATH / 'nebius_invalid_invocation_errors_D.json'}")

    # Категория E1
    print("\n--- Категория E1 (Edit E999) ---")
    print(f"Сырых кандидатов: {len(candidates_by_cat['E1'])}")
    E1_unique = deduplicate(candidates_by_cat['E1'], extra_keys=('error_code',), category='E1')
    print(f"Уникальных событий: {len(E1_unique)}")

    with open(DATA_PATH / "nebius_invalid_invocation_errors_E1.json", 'w') as f:
        json.dump(E1_unique, f, indent=2, ensure_ascii=False)
    print(f"Сохранено: {DATA_PATH / 'nebius_invalid_invocation_errors_E1.json'}")

    # Категория E2
    print("\n--- Категория E2 (Edit F821) ---")
    print(f"Сырых кандидатов: {len(candidates_by_cat['E2'])}")
    if candidates_by_cat['E2']:
        with_import = sum(1 for c in candidates_by_cat['E2']
                         if c.get('import_present_in_edit') is True)
        without_import = sum(1 for c in candidates_by_cat['E2']
                           if c.get('import_present_in_edit') is False)
        unknown = sum(1 for c in candidates_by_cat['E2']
                     if c.get('import_present_in_edit') is None)
        print(f"  с import в edit-блоке: {with_import}")
        print(f"  без import в edit-блоке: {without_import}")
        print(f"  не удалось определить: {unknown}")

    E2_unique = deduplicate(
        candidates_by_cat['E2'],
        extra_keys=('undefined_name', 'import_present_in_edit'),
        category='E2'
    )
    print(f"Уникальных событий: {len(E2_unique)}")

    with open(DATA_PATH / "nebius_invalid_invocation_errors_E2.json", 'w') as f:
        json.dump(E2_unique, f, indent=2, ensure_ascii=False)
    print(f"Сохранено: {DATA_PATH / 'nebius_invalid_invocation_errors_E2.json'}")

    # Сводка
    print("\n" + "=" * 60)
    print("СВОДКА")
    print("=" * 60)
    print(f"{'Категория':<12} {'Сырых':>10} {'Уникальных':>12}")
    print("-" * 36)
    for cat, raw_key, uniq_var in [
        ('A', 'A', A_unique), ('B', 'B', B_unique),
        ('E1', 'E1', E1_unique), ('E2', 'E2', E2_unique)
    ]:
        raw = len(candidates_by_cat[raw_key])
        uniq = len(uniq_var)
        print(f"{cat:<12} {raw:>10} {uniq:>12}")
    print("-" * 36)
    print("C (TypeError)  ОТКЛЮЧЕНА 2026-05-29: 100% FP rate (runtime errors, not tool invocation)")
    print("D (missing args) ОТКЛЮЧЕНА 2026-05-29: 100% INVALID (CoT reasoning text)")

    print("\n" + "=" * 60)
    print("Готово")
    print("=" * 60)


if __name__ == "__main__":
    main()
