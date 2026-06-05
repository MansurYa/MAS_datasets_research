"""Запускает все парсеры nebius.

Discovery (2026-06-04):
  work/scripts/nebius_all_errors.py      — TZ_4, унифицированный парсер A/B/E1/E2, выход: errors_invalid_invocation.json (381MB)
  work/scripts/nebius_edit_errors.py    — TZ_2, парсит только Edit tool errors (E999/F821), выход: errors_invalid_invocation.json
  work/scripts/nebius_errors_cli.py     — CLI для анализа errors_invalid_invocation.json
  work/scripts/stats_errors_detailed.py — статистика по errors_invalid_invocation.json
  work/scripts/stats_errors_per_trajectory.py — статистика по траекториям
  work/scripts/baseline_eda.py          — TZ_3, baseline EDA по 80 036 траекториям
  work/scripts/gen_notebook.py          — генерация ноутбуков
"""

from pathlib import Path


def run_all() -> None:
    from work.MAS_errors.parsers.nebius.invalid_invocation.parser import run as run_invalid_invocation
    from work.MAS_errors.parsers.nebius.code_execution.parser import run as run_code_execution

    run_invalid_invocation()
    run_code_execution()

    # Добавлено: code_execution (TZ_10) — runtime errors из agent scripts.
    # Исключает invalid_invocation (A/B/E1/E2) через is_invalid_invocation()."


if __name__ == "__main__":
    run_all()