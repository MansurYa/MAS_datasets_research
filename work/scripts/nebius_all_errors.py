#!/usr/bin/env python3
"""
Унифицированный парсер для всех категорий ошибок nebius/SWE-agent-trajectories.

Выходной формат — плоский список (одна запись = один факт ошибки):
{
  "A": [{...}, ...],
  "B": [{...}, ...],
  "E1": [{...}, ...],
  "E2": [{...}, ...]
}

traj_idx — абсолютный индекс траектории в датасете (0–80035).

Поля для анализа Time-to-First-Failure и Thrashing:
- occurrence_in_traj: порядковый номер ошибки в траектории
- is_first_occurrence_in_traj: True для первого вхождения
"""

import pyarrow.dataset as ds
from pathlib import Path
import re
import json
from collections import defaultdict

PROJECT_ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
PARQUET_DIR = PROJECT_ROOT / "datasets" / "nebius-SWE-agent-trajectories" / "data"
DATA_PATH = PROJECT_ROOT / "work" / "data"

# === Edit tool patterns (E1, E2) ===
EDIT_HEADER = "Your proposed edit has introduced new syntax error"
ERRORS_BLOCK_RE = re.compile(r'ERRORS:\s*\n((?:- .*\n?)+)', re.MULTILINE)
ERROR_LINE_RE = re.compile(r'^- (E\d+|F\d+|W\d+)\s+(.*)$')
EDIT_BLOCK_RE = re.compile(
    r'This is how your edit would have looked if applied\s*\n[-]+\s*\n(.*?)\n[-]+',
    re.DOTALL,
)


def normalize_error_pattern(text: str) -> str:
    """Нормализация ошибки для дедупликации."""
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
    if '```' in text:
        return False
    return True


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


def annotate_occurrences(candidates: list) -> list:
    """Добавить occurrence_in_traj и is_first_occurrence_in_traj."""
    seen = defaultdict(int)
    for c in candidates:
        key = (c['instance_id'], c['global_traj_idx'], c['normalized_pattern'])
        seen[key] += 1
        c['occurrence_in_traj'] = seen[key]
        c['is_first_occurrence_in_traj'] = (seen[key] == 1)
    return candidates


def process_trajectories():
    """
    Обработать все траектории, собрать ошибки по категориям.

    traj_idx = абсолютный индекс строки в parquet (0–80035).
    """
    print("Загружаю датасет (все шарды)...")
    dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
    table = dataset.to_table()
    d = table.to_pydict()

    instance_ids = d["instance_id"]
    trajectories = d["trajectory"]
    exit_statuses = d.get("exit_status", [None] * len(instance_ids))

    print(f"Найдено строк (все шарды): {len(instance_ids)}")

    # Паркет разбит на 12 шардов — local_counters сбрасывается между шардами.
    # Правильная формула: local = global - first_occurrence_global[instance_id]
    # Строим one-pass: first_occurrence[inst] фиксируется при первом виде instance_id
    # Первый проход: фиксируем first_occurrence[inst] и local_counters[inst].
    first_occurrence = {}
    local_counts = {}

    for row_idx, inst in enumerate(instance_ids):
        if inst not in first_occurrence:
            first_occurrence[inst] = row_idx
            local_counts[inst] = 0
        else:
            local_counts[inst] += 1

    # Второй проход: обработка траекторий с правильным local_traj_idx.
    # Формула: local = global - first_occurrence[inst]

    A_candidates = []
    B_candidates = []
    E1_candidates = []
    E2_candidates = []

    total_trajs = len(instance_ids)

    for row_idx in range(len(instance_ids)):
        inst = instance_ids[row_idx]
        traj = trajectories[row_idx]
        exit_s = exit_statuses[row_idx] if row_idx < len(exit_statuses) else None

        global_traj_idx = row_idx
        local_traj_idx = global_traj_idx - first_occurrence[inst]

        running_chars = 0
        running_ai_steps = 0

        for step_idx, step in enumerate(traj):
            step_seen = set()

            if not isinstance(step, dict) or 'text' not in step:
                continue

            text = step.get('text')
            if text is None:
                continue

            base = {
                'instance_id': inst,
                'global_traj_idx': global_traj_idx,
                'local_traj_idx': local_traj_idx,
                'step_idx': step_idx,
                'exit_status': exit_s,
                'text': text,
                'chars_up_to_error': running_chars,
                'ai_steps_up_to_error': running_ai_steps,
            }

            # === A: FileNotFoundError ===
            if matches_A(text):
                A_candidates.append({**base})

            # === B: bash commands ===
            if matches_B(text):
                B_candidates.append({**base})

            # === E: Edit tool errors ===
            if matches_E(text):
                errors = parse_edit_errors(text)
                if errors:
                    edit_block = extract_edit_block(text)

                    e999_errors = [(c, m) for c, m in errors if c == 'E999']
                    if e999_errors:
                        for c, m in e999_errors:
                            # Ключ дедупликации включает тип ошибки: "IndentationError: unexpected indent"
                            # и "IndentationError: unexpected unindent" — разные ошибки, нормализация
                            # убирает аргумент после ":", поэтому различаем через error_type.
                            error_type = m.split(':')[0]
                            key = (c, error_type, normalize_error_pattern(m))
                            if key not in step_seen:
                                step_seen.add(key)
                                E1_candidates.append({
                                    **base,
                                    'error_code': c,
                                    'error_msg': m,
                                    'error_type': error_type,
                                })

                    f821_errors = [(c, m) for c, m in errors if c == 'F821']
                    if f821_errors:
                        for c, m in f821_errors:
                            key = (c, normalize_error_pattern(m))
                            if key not in step_seen:
                                step_seen.add(key)
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

            running_chars += len(step.get('text') or '') + len(step.get('system_prompt') or '')
            if step.get('role') == 'ai':
                running_ai_steps += 1

        if (row_idx + 1) % 10000 == 0:
            print(f"  Обработано траекторий: {row_idx + 1}/{total_trajs}")

    print(f"Траекторий обработано: {total_trajs}")

    return {
        'A': A_candidates,
        'B': B_candidates,
        'E1': E1_candidates,
        'E2': E2_candidates,
    }


def main():
    print("=" * 60)
    print("nebius_invalid_invocation_errors: Парсер (плоский формат)")
    print("=" * 60)

    candidates_by_cat = process_trajectories()

    DATA_PATH.mkdir(parents=True, exist_ok=True)

    # Добавить normalized_pattern и annotate_occurrences для каждой категории
    for cat in ['A', 'B']:
        for c in candidates_by_cat[cat]:
            c['normalized_pattern'] = normalize_error_pattern(c['text'])
            c['category'] = cat

    for c in candidates_by_cat['E1']:
        c['normalized_pattern'] = normalize_error_pattern(c['error_msg'])
        c['category'] = 'E1'

    for c in candidates_by_cat['E2']:
        c['normalized_pattern'] = normalize_error_pattern(c['error_msg'])
        c['category'] = 'E2'

    # Annotate occurrences
    for cat in ['A', 'B', 'E1', 'E2']:
        candidates_by_cat[cat] = annotate_occurrences(candidates_by_cat[cat])

    # Удалить поле text из E1/E2 (слишком длинное, уже есть в error_msg)
    for c in candidates_by_cat['E1'] + candidates_by_cat['E2']:
        c.pop('text', None)
        c.pop('exit_status', None)

    # Сохранить в один файл
    output_path = DATA_PATH / "errors_invalid_invocation.json"
    with open(output_path, 'w') as f:
        json.dump(candidates_by_cat, f, indent=2, ensure_ascii=False)
    print(f"\nСохранено: {output_path}")

    # Удалить старые файлы
    old_files = [
        "nebius_invalid_invocation_errors_A.json",
        "nebius_invalid_invocation_errors_B.json",
        "nebius_invalid_invocation_errors_E1.json",
        "nebius_invalid_invocation_errors_E2.json",
    ]
    for fname in old_files:
        old_path = DATA_PATH / fname
        if old_path.exists():
            old_path.unlink()
            print(f"Удалён старый файл: {old_path}")

    # Сводка
    print("\n" + "=" * 60)
    print("СВОДКА")
    print("=" * 60)
    print(f"{'Категория':<12} {'Записей':>10}")
    print("-" * 26)
    for cat in ['A', 'B', 'E1', 'E2']:
        print(f"{cat:<12} {len(candidates_by_cat[cat]):>10}")
    print("-" * 26)

    print("\n" + "=" * 60)
    print("Готово")
    print("=" * 60)


if __name__ == "__main__":
    main()