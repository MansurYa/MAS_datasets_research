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
- TZ_2 v1 + v2 (парсер `invalid_invocation` из nebius) — **завершён**
- TZ_3 (Baseline EDA по nebius/SWE-agent-trajectories) — **завершён** (2026-05-29)
- TZ_4 (Реформа дедупликации) — **завершён** (2026-05-29)
- TZ_5 (Data Integrity Check) — **завершён** (2026-05-29)
- TZ_6 (Survival Analysis: Weibull Mixture, Context Rot) — **завершён** (2026-05-29)

## Текущая задача

TZ_6 завершён. TZ_7 завершён (2026-06-03).

**TZ_7: Реализация МЕТОДОЛОГИЯ-2.0 (2026-06-03)**
- Модуль: `work/scripts/distribution_validator/` (12 Python-файлов + 5 тестов, 54 теста, 0 failures)
- Отчёт: `work/reports/TZ_7_report.md`
- Функциональность: проверка согласия данных с 12 теоретическими распределениями (W2/W3/LN2/LN3/G2/G3/LL2/LL3/N/GU/E1/E2)
- Ключевые алгоритмы: Profile MLE (Subtasks A–E), параметрический bootstrap (B=10000), Multi-split K=100, TOST (Branch C), Kaplan-Meier для цензурированных данных
- Демо: Weibull_3P(α=4247, β=1.31, γ=1240), N=847 → ACCEPT (Branch B_SPLIT)
- Отклонение от спецификации: Subtask A (Weibull probability paper) пропущен — ненадёжен для 3P-данных со сдвигом; LRT сам определяет 2P vs 3P

**TZ_5: Data Integrity Check (2026-05-29)**
- Скрипт: `work/scripts/verify_tz5.py` — проверка 4 инвариантов
- Инварианты: [1] ключи, [2] монотонность аккумуляторов, [3] границы индексов, [4] local_traj_idx монотонен без пропусков
- Баг: local_counters сбрасывались между шардами parquet → 337K нарушений
- Фикс: формула `local = global - first_occurrence[inst]` (two-pass)
- Финальный результат: 317 349 пар проверено, 10 993 instance_id, **все 4 PASS**
- Данные: A=31 193, B=69 023, E1=133 088, E2=84 045 записей в `errors_invalid_invocation.json` (381MB)

**Уборка репозитория (2026-05-29):**
- Удалены промежуточные скрипты TZ_2 v1 (TZ_2_filter_*.py, TZ_2_setup.py, TZ_2_aggregate.py)
- Удалены черновые документы итераций (TZ_2_iteration_*.md, TZ_2_v2_iteration_*.md)
- Удалены промежуточные данные (TZ_2_candidates_*.json, TZ_2_v2_candidates_*.json, TZ_2_v2_sample_*.json)
- Удалены IDE-конфиги (.idea/, work/.idea/)
- Финальная архитектура: nebius_all_errors.py + nebius_errors_cli.py (категории A/B/E1/E2)

**TZ_4: Реформа дедупликации (2026-05-29)**
- Скрипт: `work/scripts/nebius_all_errors.py` — унифицированный парсер A/B/E1/E2
- Выход: плоский `errors_invalid_invocation.json` с ключами A/B/E1/E2
- traj_idx — абсолютный индекс (0–80035), не локальный
- Новые поля: `occurrence_in_traj`, `is_first_occurrence_in_traj`
- Старые файлы `nebius_invalid_invocation_errors_*.json` удалены при запуске парсера
- CLI: `work/scripts/nebius_errors_cli.py` (обновлён под плоский формат)
- Документация: `invalid_invocation_concept.md` (добавлен раздел эволюции), `структура_датасетов_ошибок.md` (обновлён)

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

- TZ_3: `work/specs/TZ_3.md` + `work/reports/TZ_3_baseline_eda_report.md` (обновлён 2026-05-29)
  - Baseline EDA по 80 036 траекториям nebius/SWE-agent-trajectories
  - Метрики: n_steps, n_chars (символы, не токены — tiktoken недоступен); n_ai_steps удалён
  - Группы: success (51 087, 63.83%), limit_hit (24 707, 30.87%), failed (4 242, 5.30%)
  - **Главный инсайт:** среда убивает агента **по объёму контекста, не по числу шагов**
    - 90% limit_hit лежит в диапазоне 85k–130k символов
    - После 100k символов вероятность success падает с ~85% до ~3%
    - Жёсткой стенки на конкретном n_steps нет (распределение гладкое)
  - **Новый инсайт (target):** submitted ≠ задача решена; только 24.8% submitted имеют target=True
    - target=True траектории короче: медиана 24 шага / 29k символов vs 27 / 35k у target=False
  - Knowledge base: `work/docs/baseline_trajectory_physics.md` (8 аксиом, добавлена A8)
  - Скрипт: `work/scripts/baseline_eda.py` (полный проход ~23s)
  - Артефакты: `TZ_3_trajectory_lengths.csv` (теперь с колонкой target), `TZ_3_descriptive_stats.csv`, 8 PNG в `work/data/plots/`

- TZ_4: `work/specs/TZ_4.md` (2026-05-29)
  - Реформа дедупликации: плоский формат вместо вложенного
  - **Было:** группировка по (instance_id, pattern_hash), traj_idx локальный, 4 файла *_A.json и т.д.
  - **Стало:** плоский список, traj_idx глобальный (0–80035), 1 файл `errors_invalid_invocation.json`
  - Новые поля: `occurrence_in_traj`, `is_first_occurrence_in_traj` — для анализа Time-to-First-Failure и Thrashing
  - Обновлены: `nebius_all_errors.py`, `nebius_errors_cli.py`, `invalid_invocation_concept.md`, `структура_датасетов_ошибок.md`

- TZ_5: `work/specs/TZ_5.md` + `work/scripts/verify_tz5.py` (2026-05-29)
  - Data Integrity Check: 4 инварианта в `errors_invalid_invocation.json`
  - **Инвариант [4] (local_traj_idx):** главный баг — счётчик сбрасывался между 12 шардами parquet
  - Фикс: two-pass с `first_occurrence[inst]` и формулой `local = global - first_occurrence`
  - Проблема multi-error: один шаг содержит 2 разных E999 → добавлен `error_type` в ключ дедупликации
  - Проверено 317 349 пар, 10 993 instance_id → **все 4 PASS**

- TZ_6: `work/specs/TZ_6.md` + `work/scripts/survival_analysis.py` + `work/reports/TZ_6_survival_analysis_report.md` (2026-05-29)
  - Survival Analysis по 10 000 стратифицированным траекториям (seed=42)
  - **Эксперимент 1 (Right-Wall):** limit_hit → Weibull_Mixture (BIC=67869), α₁=114846, β₁=11.7, proportion=0.865
  - **Эксперимент 2 (Context Rot):** β для Weibull — E1=1.177 (>1, деградация!), A=0.994, B=0.837, E2=0.900
    - **Главный инсайт:** только E1 (edit syntax) показывает Context Rot; остальные — нет
  - **Эксперимент 3 (Mixture vs CR):** Weibull_Mixture (BIC=82391) vs Weibull_CR (BIC=85717) — смесь лучше
  - Параметры: `work/data/TZ_6_fit_params.csv`, 7 Probability Plots в `work/data/reliability_plots/`

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
