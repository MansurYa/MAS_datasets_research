#!/usr/bin/env python3
"""
Исправленный парсер для nebius/SWE-agent-trajectories.

Проблема старого подхода:
  Парсеры использовали df.iterrows() с одним шардом. trajectory_idx = локальный
  индекс внутри шарда. При фильтрации ds.dataset().to_table(filter=...)
  возвращаются строки из ВСЕХ шардов, и локальный индекс не совпадает.

Решение:
  Используем ds.dataset() для чтения ВСЕХ шардов сразу, фильтруем по instance_id,
  итерируем по отфильтрованным строкам. trajectory_idx теперь = индекс строки
  в отфильтрованном результате (0..N-1), что совпадает с traj_list[i].

Структура данных nebius:
  parquet schema: instance_id, model_name, target, trajectory, exit_status,
                  generated_patch, eval_logs
  trajectory: list[list[step_dict]]
  step_dict keys: cutoff_date, mask, role, system_prompt, text

  Для одного instance_id может быть МНОЖЕСТВО траекторий (traj_list).
  traj_list[i] — это i-я траектория (прогон) для данного instance_id.
  traj_list[i][step_idx] — это step_idx-й шаг внутри i-й траектории.

Поля в выходном JSON:
  - instance_id: идентификатор задачи (OWNER__REPO-NUMBER)
  - traj_idx: индекс траектории в traj_list (0, 1, 2, ...)
  - step_idx: индекс шага внутри траектории
  - error_code: код ошибки (E999, F821 и т.д.)
  - error_msg: текст сообщения об ошибке
  - normalized_pattern: нормализованный паттерн для дедипликации
  - text: полный текст шага
  - count: сколько раз эта ошибка встретилась (для дедипликации)
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

# Паттерны для Edit tool errors (E1 + E2)
EDIT_HEADER = "Your proposed edit has introduced new syntax error"
ERRORS_BLOCK_RE = re.compile(r'ERRORS:\s*\n((?:- .*\n?)+)', re.MULTILINE)
ERROR_LINE_RE = re.compile(r'^- (E\d+|F\d+|W\d+)\s+(.*)$')
EDIT_BLOCK_RE = re.compile(
    r'This is how your edit would have looked if applied\s*\n[-]+\s*\n(.*?)\n[-]+',
    re.DOTALL,
)
ORIGINAL_BLOCK_RE = re.compile(
    r'This is the original code before your edit\s*\n[-]+\s*\n(.*?)\n[-]+',
    re.DOTALL,
)


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


def parse_errors(text: str):
    """Извлечь список (code, message) из блока ERRORS:."""
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


def classify_errors(errors):
    """Вернуть множество категорий: {'E1', 'E2', 'OTHER'}."""
    cats = set()
    for code, _msg in errors:
        if code == 'E999':
            cats.add('E1')
        elif code == 'F821':
            cats.add('E2')
        else:
            cats.add('OTHER')
    return cats


def extract_edit_block(text: str) -> str:
    """Извлечь edit-блок агента (то, что он предложил)."""
    m = EDIT_BLOCK_RE.search(text)
    if m:
        return m.group(1)
    return ''


def has_import(edit_block: str, name: str) -> bool:
    """Грубая проверка: есть ли import name в edit-блоке."""
    if not edit_block:
        return False
    pattern_module = re.compile(rf'^\s*\d*:?\s*import\s+{re.escape(name)}\b', re.MULTILINE)
    pattern_from = re.compile(rf'^\s*\d*:?\s*from\s+\S+\s+import\s+.*\b{re.escape(name)}\b', re.MULTILINE)
    return bool(pattern_module.search(edit_block) or pattern_from.search(edit_block))


def find_edit_errors(dataset, instance_id: str = None):
    """
    Найти все Edit tool errors во всех траекториях.

    traj_idx ВСЕГДА = локальный индекс траектории в traj_list для ДАННОГО instance_id.
    (0, 1, 2... для первых N траекторий этого instance_id)

    При фильтрации по instance_id — traj_idx = позиция строки в результате.
    При чтении ВСЕГО датасета — группируем по instance_id и считаем локально.

    Args:
        dataset: pyarrow.dataset.Dataset
        instance_id: если задан — фильтруем по конкретному instance_id

    Returns:
        tuple: (e1_raw, e2_raw) — списки сырых кандидатов
            traj_idx: локальный индекс в traj_list данного instance_id
    """
    if instance_id:
        table = dataset.to_table(filter=ds.field("instance_id") == instance_id)
        d = table.to_pydict()
        instance_ids = d["instance_id"]
        trajectories = d["trajectory"]
        exit_statuses = d.get("exit_status", [None] * len(instance_ids))

        print(f"Найдено строк: {len(instance_ids)}")

        e1_raw = []
        e2_raw = []

        for traj_idx in range(len(instance_ids)):
            inst = instance_ids[traj_idx]
            traj = trajectories[traj_idx]
            exit_s = exit_statuses[traj_idx] if traj_idx < len(exit_statuses) else None

            _process_trajectory(inst, traj, traj_idx, exit_s, e1_raw, e2_raw)

    else:
        table = dataset.to_table()
        d = table.to_pydict()
        instance_ids = d["instance_id"]
        trajectories = d["trajectory"]
        exit_statuses = d.get("exit_status", [None] * len(instance_ids))

        print(f"Найдено строк (все шарды): {len(instance_ids)}")

        # Группируем по instance_id и для каждого считаем локальный traj_idx
        instance_rows = defaultdict(list)
        for row_idx in range(len(instance_ids)):
            inst = instance_ids[row_idx]
            instance_rows[inst].append(row_idx)

        print(f"Уникальных instance_id: {len(instance_rows)}")

        e1_raw = []
        e2_raw = []

        for inst, row_indices in instance_rows.items():
            for local_traj_idx, row_idx in enumerate(row_indices):
                traj = trajectories[row_idx]
                exit_s = exit_statuses[row_idx] if row_idx < len(exit_statuses) else None

                _process_trajectory(inst, traj, local_traj_idx, exit_s, e1_raw, e2_raw)

        print(f"Траекторий обработано: {sum(len(v) for v in instance_rows.values())}")

    return e1_raw, e2_raw


def _process_trajectory(inst, traj, traj_idx, exit_s, e1_raw, e2_raw):
    """Обработать одну траекторию — найти edit errors."""
    for step_idx, step in enumerate(traj):
        if not isinstance(step, dict) or 'text' not in step:
            continue

        text = step.get('text')
        if text is None:
            continue

        if EDIT_HEADER not in text:
            continue

        errors = parse_errors(text)
        if not errors:
            continue

        edit_block = extract_edit_block(text)

        base = {
            'instance_id': inst,
            'traj_idx': traj_idx,
            'step_idx': step_idx,
            'exit_status': exit_s,
            'text': text,
            'errors_parsed': [{'code': c, 'msg': m} for c, m in errors],
        }

        e999_errors = [(c, m) for c, m in errors if c == 'E999']
        if e999_errors:
            for c, m in e999_errors:
                e1_raw.append({
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
                e2_raw.append({
                    **base,
                    'error_code': c,
                    'error_msg': m,
                    'undefined_name': name,
                    'import_present_in_edit': import_present,
                })


def deduplicate(candidates, extra_keys=()):
    """
    Дедипликация по (instance_id, error_pattern_hash + extra_keys).

    Для каждой группы (одинаковая ошибка для одного instance_id):
    - pattern_hash: хэш нормализованного паттерна ошибки
    - error_msg: текст ошибки (не сжатый, а первый встреченный)
    - count: общее число вхождений
    - locations: СПИСОК всех мест где встретилась эта ошибка
      [{instance_id, traj_idx, step_idx, text, ...}, ...]
    - traj_idxs, step_idxs: списки для совместимости
    - traj_idx, step_idx: первое вхождение (для совместимости)
    """
    groups = defaultdict(list)
    for c in candidates:
        pattern_input = c.get('error_msg', c.get('text', ''))
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
            'pattern_hash': key[1],
            'count': len(items),
            'locations': locations,
            'traj_step_pairs': [list(p) for p in all_pairs],
            'traj_idx': first['traj_idx'],
            'step_idx': first['step_idx'],
            'exit_status': first['exit_status'],
            'error_code': first.get('error_code'),
            'error_msg': first.get('error_msg'),
            'normalized_pattern': normalize_error_pattern(first.get('error_msg', '')),
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
    print("nebius_edit_errors: Исправленный парсер")
    print("=" * 60)

    print("\nЗагружаю датасет (все шарды)...")
    dataset = ds.dataset(str(PARQUET_DIR), format="parquet")
    print("Датасет загружен")

    # Все instance_id с edit errors
    print("\nИщу edit tool errors...")
    e1_raw, e2_raw = find_edit_errors(dataset)

    print(f"\nE1 (E999) сырых кандидатов: {len(e1_raw)}")
    print(f"E2 (F821) сырых кандидатов: {len(e2_raw)}")

    if e2_raw:
        with_import = sum(1 for c in e2_raw if c.get('import_present_in_edit') is True)
        without_import = sum(1 for c in e2_raw if c.get('import_present_in_edit') is False)
        unknown = sum(1 for c in e2_raw if c.get('import_present_in_edit') is None)
        print(f"  E2 с import в edit-блоке: {with_import}")
        print(f"  E2 без import в edit-блоке: {without_import}")
        print(f"  E2 не удалось определить: {unknown}")

    print("\nДедипликация E1...")
    e1_unique = deduplicate(e1_raw, extra_keys=('error_code',))
    print(f"E1 уникальных событий: {len(e1_unique)}")

    print("\nДедипликация E2...")
    e2_unique = deduplicate(e2_raw, extra_keys=('undefined_name', 'import_present_in_edit'))
    print(f"E2 уникальных событий: {len(e2_unique)}")

    e1_sample = estimate_sample_size(len(e1_unique))
    e2_sample = estimate_sample_size(len(e2_unique))

    DATA_PATH.mkdir(parents=True, exist_ok=True)

    e1_file = DATA_PATH / "nebius_edit_errors_E1.json"
    with open(e1_file, 'w') as f:
        json.dump(e1_unique, f, indent=2, ensure_ascii=False)
    print(f"\nE1 сохранено: {e1_file}")

    e2_file = DATA_PATH / "nebius_edit_errors_E2.json"
    with open(e2_file, 'w') as f:
        json.dump(e2_unique, f, indent=2, ensure_ascii=False)
    print(f"E2 сохранено: {e2_file}")

    # Пример: проверим iterative__dvc-6633
    print("\n" + "=" * 60)
    print("Верификация: iterative__dvc-6633")
    print("=" * 60)

    target = [e for e in e1_raw if e['instance_id'] == 'iterative__dvc-6633']
    print(f"\nВсего E1 ошибок для iterative__dvc-6633: {len(target)}")
    print("Первые 5:")
    for e in sorted(target, key=lambda x: x['step_idx'])[:5]:
        print(f"  traj={e['traj_idx']:2d}  step={e['step_idx']:3d}  msg={e['error_msg'][:60]}")

    # Проверим deduplicate с locations
    e1_for_check = [e for e in e1_unique if e['instance_id'] == 'iterative__dvc-6633']
    if e1_for_check:
        first_group = e1_for_check[0]
        print(f"\nДедиплицированная группа: count={first_group['count']}")
        print(f"  locations: {len(first_group['locations'])} штук")
        if first_group['locations']:
            loc = first_group['locations'][0]
            print(f"  первый location: traj={loc['traj_idx']}, step={loc['step_idx']}")
            print(f"    text length: {len(loc.get('text', ''))} chars")

    print("\n" + "=" * 60)
    print("Готово")
    print("=" * 60)


if __name__ == "__main__":
    main()