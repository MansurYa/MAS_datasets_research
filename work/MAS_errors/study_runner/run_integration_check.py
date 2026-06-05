"""TZ_8.6 — Интеграционная проверка pipeline (5 целевых исследований)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _ROOT / "work" / "scripts"
for _p in [str(_ROOT), str(_SCRIPTS)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from work.MAS_errors.schemas import StudySpec
from work.MAS_errors.study_runner.run_study import run_study, save_artefacts

PARSERS = Path(__file__).resolve().parents[1] / "parsers"

TARGETS = [
    ("nebius/invalid_invocation/A/errors.parquet",      "step_idx",           "nebius_A_step"),
    ("nebius/invalid_invocation/B/errors.parquet",      "step_idx",           "nebius_B_step"),
    ("nebius/invalid_invocation/ALL/errors.parquet",    "step_idx",           "nebius_ALL_step"),
    ("nebius/invalid_invocation/A/errors.parquet",      "chars_before_error", "nebius_A_chars"),
    ("agentRx/magentic_one/instruction_adherence_failure/errors.parquet", "step_idx", "agentRx_iah"),
]


def _spec_from_target(rel_path: str, analysis_var: str, label: str) -> StudySpec:
    p = PARSERS / rel_path
    parts = Path(rel_path).parts
    if len(parts) == 3:
        dataset, error_type, folder = parts[0], parts[1], parts[2].replace("/errors.parquet", "")
        error_subtype = parts[2].replace("_dedup", "").replace("/errors.parquet", "")
        folder_name = parts[2].replace("/errors.parquet", "")
    else:
        dataset = parts[0]
        error_type = parts[1] if len(parts) > 2 else parts[0]
        folder_name = parts[-2]
        error_subtype = folder_name.replace("_dedup", "")

    is_dedup = folder_name.endswith("_dedup")

    return StudySpec(
        study_id=label,
        parquet_path=str(p),
        dataset=dataset,
        error_type=error_type,
        error_subtype=error_subtype,
        is_dedup=is_dedup,
        subgroup="all",
        analysis_var=analysis_var,
    )


def main() -> None:
    rows = []
    for rel_path, analysis_var, label in TARGETS:
        spec = _spec_from_target(rel_path, analysis_var, label)
        print(f"  Running {label}...", flush=True)
        result = run_study(spec, B=100)
        save_artefacts(spec, result)

        artefact_dir = Path(spec.parquet_path).parent / spec.study_id
        fit_log = artefact_dir / "fit_log.json"
        audit_md = artefact_dir / "audit_report.md"

        fit_ok = fit_log.exists() and fit_log.stat().st_size > 100
        audit_ok = audit_md.exists() and audit_md.stat().st_size > 300

        rows.append({
            "label": label,
            "n": result.n_errors,
            "status": result.status,
            "dist": result.final_dist or "—",
            "p": f"{result.p_final:.4f}" if result.p_final is not None else "—",
            "fit_ok": fit_ok,
            "audit_ok": audit_ok,
        })
        print(f"    → {result.status} | {result.final_dist} | n={result.n_errors}")

    # Проверки
    errors = [r for r in rows if r["status"] == "ERROR"]
    files_missing = [r for r in rows if not r["fit_ok"] or not r["audit_ok"]]
    statuses = {r["status"] for r in rows}
    all_same = len(statuses) == 1

    passed = not errors and not files_missing and not all_same

    # Таблица
    print("\n" + "=" * 70)
    print(f"{'Label':<25} {'n':>6} {'Status':<15} {'Dist':<6} {'p':>7}  files")
    print("-" * 70)
    for r in rows:
        files = "OK" if r["fit_ok"] and r["audit_ok"] else "FAIL"
        print(f"{r['label']:<25} {r['n']:>6} {r['status']:<15} {r['dist']:<6} {r['p']:>7}  {files}")
    print("=" * 70)
    print(f"\nРезультат: {'PASS' if passed else 'FAIL'}")
    if errors:
        print(f"  ERROR статусы: {[r['label'] for r in errors]}")
    if files_missing:
        print(f"  Отсутствуют файлы: {[r['label'] for r in files_missing]}")
    if all_same:
        print(f"  Все статусы одинаковые ({statuses}) — неинформативно")

    # Отчёт
    _write_report(rows, passed, errors, files_missing, all_same)


def _write_report(rows, passed, errors, files_missing, all_same):
    lines = ["# Отчёт TZ_8.6 — Интеграционная проверка pipeline\n",
             "**Дата:** 2026-06-04\n",
             f"**Итог: {'PASS' if passed else 'FAIL'}**\n",
             "\n## Результаты исследований\n",
             "| Label | n | Status | Dist | p | Файлы |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        files = "OK" if r["fit_ok"] and r["audit_ok"] else "FAIL"
        lines.append(f"| {r['label']} | {r['n']} | {r['status']} | {r['dist']} | {r['p']} | {files} |")

    lines += ["\n## Проверки", ""]
    lines.append(f"- ERROR статусы: {'нет' if not errors else [r['label'] for r in errors]}")
    lines.append(f"- Отсутствующие файлы: {'нет' if not files_missing else [r['label'] for r in files_missing]}")
    lines.append(f"- Все статусы одинаковые: {'да — FAIL' if all_same else 'нет'}")

    if passed:
        lines += ["\n## Вывод", "",
                  "Pipeline прошёл интеграционную проверку. Запустить полный прогон:",
                  "```bash", ".venv/bin/python work/MAS_errors/study_runner/run_all.py", "```"]
    else:
        lines += ["\n## Вывод", "", "Pipeline не прошёл проверку. Необходимо устранить проблемы перед полным прогоном."]

    report_path = _ROOT / "work/reports/TZ_8.6-report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines))
    print(f"\nОтчёт: {report_path}")


_ROOT = Path(__file__).resolve().parents[3]

if __name__ == "__main__":
    main()
