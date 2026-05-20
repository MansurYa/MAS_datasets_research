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

**TZ_1:** понять что Huawei имеет в виду под "Incorrect tool call". Смотреть в сырые данные TRAIL и AgentRx, не угадывать.

- Спецификация: `work/specs/TZ_1.md` (техническое задание от Мансура)
- Отчёт: `work/reports/TZ_1_report.md` (готовый отчёт по выполнению)

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

## Важные ограничения
- Who&When: использовать только Hand-Crafted (58 записей), не Algorithm-Generated (126)
- TRAIL — основной источник с экспертной разметкой
- Стандартный KS-тест некорректен при MLE — использовать модифицированный (§2.2.4)
- Датасеты большие — не загружать целиком без необходимости
