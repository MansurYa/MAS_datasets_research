# Отчёт TZ_8.6 — Интеграционная проверка pipeline

**Дата:** 2026-06-04

**Итог: PASS**


## Результаты исследований

| Label | n | Status | Dist | p | Файлы |
|---|---|---|---|---|---|
| nebius_A_step | 31193 | REJECT | LN2 | 0.0000 | OK |
| nebius_B_step | 69023 | ACCEPT | N | — | OK |
| nebius_ALL_step | 153160 | REJECT | W2 | — | OK |
| nebius_A_chars | 31193 | REJECT | W2 | 0.0000 | OK |
| agentRx_iah | 197 | ACCEPT | W2 | 0.4899 | OK |

## Проверки

- ERROR статусы: нет
- Отсутствующие файлы: нет
- Все статусы одинаковые: нет

## Вывод

Pipeline прошёл интеграционную проверку. Запустить полный прогон:
```bash
.venv/bin/python work/MAS_errors/study_runner/run_all.py
```