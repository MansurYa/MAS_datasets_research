---
name: mas-datasets-tz-status
description: Текущий статус TZ и ключевые артефакты проекта MAS datasets research (Huawei)
metadata:
  type: project
---

# MAS Datasets Research — Текущий статус

## Проект
Анализ ошибок агентных траекторий для симулятора динамической доступности LLM.
Huawei Joint Lab, СПбГУ × Huawei. Начало 2025.

**Why:** Получить параметры (P_err, распределения) для fault injection в IR-граф симулятора DA.
**How to apply:** Читать в начале каждой сессии для восстановления контекста.

## Статус циклов

**Старый цикл (ТЗ №1–7):** завершён, финальный отчёт отклонён Huawei → **АРХИВ** (`archive/`)

**Новый цикл:**
- TZ_0 (реструктуризация репозитория) — удалён (2026-05-20), потерял актуальность
- TZ_1 (анализ типов ошибок tool call по сырым данным) — **завершён**

## Текущая задача

Нет активной TZ. TZ_1 и TZ_2 (v1 + v2) завершены.

**Уборка репозитория (2026-05-29):**
- Удалены промежуточные скрипты TZ_2 v1 (TZ_2_filter_*.py, TZ_2_setup.py, TZ_2_aggregate.py)
- Удалены черновые документы итераций (TZ_2_iteration_*.md, TZ_2_v2_iteration_*.md)
- Удалены промежуточные данные (TZ_2_candidates_*.json, TZ_2_v2_candidates_*.json, TZ_2_v2_sample_*.json)
- Удалены IDE-конфиги (.idea/, work/.idea/)
- Финальная архитектура: nebius_all_errors.py + nebius_errors_cli.py (категории A/B/E1/E2)

**Новое: Унифицированный парсер (2026-05-23)**
- Скрипт: `work/scripts/nebius_invalid_invocation_errors.py`
- Исправлен баг с traj_idx: теперь всегда локальный (относительно instance_id)
- Все категории в одном формате: category, locations[], traj_idxs[], step_idxs[]
- Файлы: `work/data/nebius_invalid_invocation_errors_{A,B,C,D,E1,E2}.json`
- Ноутбук: `work/nebius_review.ipynb` (обновлён для унифицированного формата)

**Актуальный парсер: nebius_all_errors.py (2026-05-29)**
- Скрипт: `work/scripts/nebius_all_errors.py` — унифицированный парсер A/B/C/D/E1/E2
- Категории A, B, E1, E2 — активны
- Категории C, D — **отключены** (закомментированы, код сохранён):
  - C (TypeError): 100% FP rate — runtime ошибки кодогенерации, не invalid_invocation (2026-05-28)
  - D (missing args): 100% INVALID — CoT reasoning, паттерн не совпадает с форматом nebius (2026-05-29)
- CLI: `work/scripts/nebius_errors_cli.py` (categories: A, B, E1, E2)

**Завершённые задачи:**
- TZ_1: `work/specs/TZ_1.md` + `work/reports/TZ_1_report.md`
  - Анализ типов ошибок tool call по сырым данным (TRAIL, AgentRx)
  - Раздел 8: углублённый анализ tool_web_failure — автоматическое разделение на подкатегории
  - Ключевой вывод: nebius (26 379 "совпадений") — артефакт keyword search, SWE-agent не имеет веб-инструментов

- TZ_2 v1: `work/specs/TZ_2.md` + `work/reports/TZ_2_report.md` (2026-05-20)
  - Извлечение `invalid_invocation` из nebius (80 036 траекторий, первый шард: 6670)
  - 4 категории: A (неверные пути), B (bash команды), C (TypeError), D (missing args)
  - Результаты: A (100% TP), B (63.3% TP), C (40% TP), D (29% TP)
  - Вывод: только категория A надёжна. Парсер требует доработки → TZ_2 v2

- TZ_2 v2: `work/reports/TZ_2_v2_report.md` (2026-05-22)
  - Концептуальная ошибка v1: парсер ловил code execution вместо tool invocation в C/D
  - 5 субагентов параллельно: верификация B/C/D/E1/E2
  - FP guards для B (`ls: cannot access`), C (`[File:`, `FutureWarning`), D (`[File:`, `__init__()`)
  - Дедипликация по (instance_id, error_pattern_hash). Сжатие 1.3x–12.7x
  - **Новая категория E** (edit tool errors): E1 (E999 syntax) + E2 (F821 undefined name)
  - Финальные TP rate: A 100%, B 84%, C 0%, D 5%, E1 100%, E2 50% (пограничная)
  - **Надёжные категории (A+B+E1):** 4 137 истинных событий, P_step ≈ 0.0116, P_traj ≈ 0.297
  - **С учётом E2:** P_step ≈ 0.0153, P_traj ≈ 0.383
  - Экстраполяция на 80 036 траекторий: ≈ 30 622 траекторий с ошибкой

## Структура репозитория

```
datasets/           ← все датасеты Hugging Face
work/               ← ТЕКУЩАЯ РАБОТА
  specs/            ← TZ_0.md, TZ_1.md …
  scripts/          ← новые скрипты
  reports/          ← TZ_1_report.md …
  data/             ← выходные CSV и графики
archive/            ← СТАРЫЙ ЦИКЛ (отклонён Huawei)
  scripts/          ← tz*.py (пути сломаны — это нормально)
  specs/            ← ТЗ №1.md … ТЗ №7.md
  reports/          ← старые отчёты
  data/             ← старые CSV и графики
  docs/             ← fault_analysis_report.md (отклонён)
reference/          ← STATS_BOOK_INDEX.md + OCR учебник
memory/             ← этот файл + MEMORY_INDEX.md
```

## Ключевые файлы для нового цикла
- `datasets/TRAIL/` — основной источник (143 траектории, 836 ошибок, экспертная разметка)
- `datasets/microsoft-AgentRx/` — второй источник типизированных ошибок
- `datasets/Kevin355-Who_and_When/` — только Hand-Crafted сплит (58 записей)
- `reference/STATS_BOOK_INDEX.md` — какой параграф решает какую задачу

## Ключевые файлы архива (справочник)
- `archive/docs/errors_stats.csv` — итоговая таблица ошибок с классификацией и параметрами распределений (ТЗ №5)
- `archive/docs/methodology.md` — методологический документ (таксономия TRAIL, классы моделирования 1–4) (ТЗ №6)
- `archive/scripts/` — папка со всеми парсерами и утилитами (23 файла, см. `memory/reference_archive_map.md`)
  - Парсеры: `tz1_reconnaissance.py` (разведка), `tz4_8_trail_extract.py` (TRAIL), `tz4_8_who_when.py` (Who&When HC), `tz4_5_keyword_search.py` (keyword search)
  - Утилиты: `tz4_distributions.py`, `tz4_7_heavy_tails.py`, `tz5_a_fix_data.py`, `tz6_plots_v2.py` и др.

## Важные ограничения
- Who&When: использовать только Hand-Crafted (58 записей), не Algorithm-Generated (126)
- TRAIL — основной источник с экспертной разметкой
- Стандартный KS-тест некорректен при MLE — использовать модифицированный (§2.2.4)
- Датасеты большие — не загружать целиком без необходимости
