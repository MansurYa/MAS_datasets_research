# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **data repository** containing curated agent trajectory datasets from Hugging Face — real multi-step execution traces with full reasoning → tool invocation → environment response chronology.

Full documentation: `AGENT_TRAJECTORY_DATASETS.md` (in Russian).

Related analysis:
- `p1_fault_mode_distributions.ipynb` — fault mode distribution analysis
- `fault_mode_analysis_and_classification_ru.html` — TRAIL taxonomy classification guide

---

## Dataset Index

| Folder | Hugging Face ID | Domain | Format | Size |
|--------|----------------|--------|--------|------|
| `nebius-SWE-agent-trajectories/` | `nebius/SWE-agent-trajectories` | SE / Terminal | Parquet | 1.0GB |
| `SWE-Gym-OpenHands-Sampled-Trajectories/` | `SWE-Gym/OpenHands-Sampled-Trajectories` | SE | Parquet | 289MB |
| `yoonholee-terminalbench-trajectories/` | `yoonholee/terminalbench-trajectories` | Terminal | Parquet | 213MB |
| `ibm-research-ITBench-Trajectories/` | `ibm-research/ITBench-Trajectories` | SRE | JSONL+JSON | 165MB |
| `microsoft-AgentRx/` | `microsoft/AgentRx` | Multi-Domain | JSONL | 7.1MB |
| `Kevin355-Who_and_When/` | `Kevin355/Who_and_When` | Multi-Agent | Parquet+JSON | 52MB |
| `iMeanAI-Mind2Web-Live/` | `iMeanAI/Mind2Web-Live` | Web Agents | JSON | 3.3MB |

---

## Quick Load Examples

```python
from datasets import load_dataset

# Software Engineering
ds = load_dataset("nebius/swe-agent-trajectories")
ds = load_dataset("SWE-Gym/OpenHands-Sampled-Trajectories")

# Terminal / Bash
ds = load_dataset("yoonholee/terminalbench-trajectories")

# SRE / Cloud diagnostics
ds = load_dataset("ibm-research/ITBench-Trajectories")

# Multi-agent failure analysis
ds = load_dataset("microsoft/AgentRx")
ds = load_dataset("Kevin355/Who_and_When")

# Web navigation
ds = load_dataset("iMeanAI/Mind2Web-Live")
```

---

## License Notes

- **SWE-agent:** CC BY 4.0, outputs require **Llama 3.1 License** compliance; SWE-bench extra licenses embedded.
- **Other datasets:** Check individual `README.md` files for license terms.

---

## Fault Mode Taxonomy (TRAIL)

Datasets include annotations using TRAIL taxonomy (Trace Reasoning and Agentic Issue Localization):
- **Reasoning Errors:** Hallucination, Information Processing, Decision Making, Response Generation
- **System Execution Errors:** Configuration, API Problems (Rate Limiting, Auth, Service Errors), Resource Management (Exhaustion, Timeouts)
- **Planning/Coordination Errors:** Context Management (Context Handling Failures, Resource Abuse), Task Management (Goal Deviation, Task Orchestration)

Key mappings in analysis:
- **KV-cache loss** → `Context Handling Failures`
- **Resource Abuse** → `Resource Abuse`
- **Tool call timeouts** → `Timeout Issues` / `Service Errors`

# Контекст проекта: Классификация ошибок и статистическое исследование

## Что это за проект

Исследовательский проект для Huawei (СПбГУ × Huawei Joint Lab). Цель — создать
симулятор динамической доступности (Dynamic Availability) распределённых систем
инференса LLM. Симулятор моделирует мультиагентные системы (MAS), где агенты
последовательно обращаются к языковым моделям для выполнения задач.

**Динамическая доступность (DA)** — процент запросов (или MAS-сессий), завершённых
успешно в рамках заданного SLA-порога времени.

## Что делается в этом чате

Задача: провести статистическое исследование ошибок в агентных траекториях.

Результат нужен для двух целей:
1. Получить параметры для fault injection в симулятор (вероятности появления ошибок,
   распределения момента их возникновения)
2. Подготовить отчёт для Patent Review Board (PRB) Huawei

## Архитектура симулятора (IR-граф)

Симулятор работает с абстрактным графом блоков (Intermediate Representation).
Каждый блок описывается параметрами:
- T — время выполнения
- P_err — вероятность ошибки
- P_rec — вероятность самовосстановления
- D — штраф по времени при ошибке

Ошибки инжектируются в блоки IR-графа. Чтобы задать реалистичные P_err и
распределение момента возникновения ошибки — нужны данные из реальных агентных
траекторий.

## Четыре категории ошибок

Каждая ошибка классифицируется по возможности моделирования в симуляторе:

**Категория 1: Невозможно моделировать**
Ошибки, для симуляции которых требуется полный прогон весов языковой модели.
Даже при наличии статистики — воспроизвести эффект в симуляторе невозможно без
запуска реального LLM.
Примеры: галлюцинации, неправильная постановка цели, зацикливание агента,
назначение задачи не тому агенту, Formatting Errors (семантические).

**Категория 2: Возможно моделировать напрямую**
Ошибки, которые симулятор воспроизводит без статистических допущений — через
изменение структуры IR-графа или параметров блоков.
Примеры: потеря KV-кэша, упор в пропускную способность канала, достижение
максимального размера контекстного окна.

**Категория 3: Возможно моделировать статистически**
Ошибки, которые нельзя воспроизвести напрямую, но можно описать вероятностно:
взять датасет, оценить частоту появления, подобрать распределение и по нему
генерировать события в симуляторе.
Примеры: Resource Abuse, таймауты вызовов внешних инструментов.

Важное разграничение с категорией 1: если ошибка статистически описана, но
непонятно как она влияет на DA в симуляторе — это категория 1, а не 3.

**Категория 4: Возможно моделировать, но нецелесообразно**
Ошибки, которые технически реализуемы, но не имеют смысла в рамках проекта.
Примеры: деградация оборудования на длинном горизонте (симулятор не рассчитан
на такие горизонты), троттлинг GPU (в крупных кластерах практически не встречается).

## Источники данных

### Датасеты с явной типизацией ошибок (основные источники)

**Who&When** (`Kevin355/Who_and_When`)
- 184 аннотированных случая отказов из реальных прогонов мультиагентных систем
- Поля: `mistake_reason`, `failure_category`, `mistake_agent`, `mistake_step`
- Это основной источник типизированных ошибок

**AgentRx** (`microsoft/AgentRx`)
- ~159 неуспешных траекторий с пошаговой аннотацией отказов
- Поля: `failure_category`, `failed_agent`, `root_cause`, `step_number`
- Второй основной источник типизированных ошибок

### Датасеты без явной типизации (дополнительная статистика)

**nebius/SWE-agent-trajectories** — 80 036 траекторий, только exit_status
**SWE-Gym/OpenHands-Sampled-Trajectories** — 6 055 траекторий
**yoonholee/terminalbench-trajectories** — 52 104 траектории
**ibm-research/ITBench-Trajectories** — 105 траекторий SRE-агентов
**iMeanAI/Mind2Web-Live** — 542 задачи веб-навигации

Из этих датасетов можно извлечь: статистику успех/провал, длины траекторий,
длины контекста — но не типы ошибок напрямую.

### Существующая классификация

Файл `fault_mode_analysis_and_classification_ru` содержит уже готовую таксономию
ошибок на основе TRAIL и Who&When. Это стартовая точка — не нужно изобретать
заново. Новые ошибки из датасетов добавляются к этой таксономии.

## ВАЖНО: Два поколения работы — читать первым

### Старый цикл (АРХИВ — не использовать как основу)
- Скрипты: `archive/scripts/tz*.py` (23 файла)
- Спецификации: `archive/specs/ТЗ №1.md … ТЗ №7.md`
- Отчёты: `archive/reports/`, `archive/docs/`
- Данные: `archive/data/`
- Финальный отчёт: `archive/docs/fault_analysis_report.md`
- **Статус: ОТКЛОНЁН Huawei. Хранится как архив.**

### Новый цикл (ТЕКУЩАЯ РАБОТА)
- Спецификации: `work/specs/TZ_N.md` (латиница, нумерация с 0)
- Отчёты: `work/reports/TZ_N_report.md`
- Скрипты: `work/scripts/`
- Данные: `work/data/`
- **Текущая задача: читать `work/specs/TZ_1.md`**

Подробный статус: `memory/TZ_STATUS.md` — читать в начале каждой сессии.

## Структура репозитория

```
datasets/           ← все датасеты Hugging Face (TRAIL/, AgentRx/, Who_and_When/ и др.)
work/               ← ТЕКУЩАЯ РАБОТА
  specs/            ← TZ_0.md, TZ_1.md, TZ_2.md …
  scripts/          ← новые скрипты
  reports/          ← TZ_1_report.md, TZ_2_report.md …
  data/             ← выходные CSV и графики
archive/            ← СТАРЫЙ ЦИКЛ (ТЗ №1–7, отклонён Huawei)
  scripts/          ← tz*.py (пути сломаны — это нормально, архив)
  specs/            ← ТЗ №1.md … ТЗ №7.md
  reports/          ← старые отчёты
  data/             ← старые CSV и графики
  docs/             ← fault_analysis_report.md и методология
reference/          ← STATS_BOOK_INDEX.md + OCR учебник + REPOSITORY_MAP.md
memory/             ← TZ_STATUS.md + MEMORY_INDEX.md
```

## Рабочий процесс (новый цикл)

1. TZ-спецификация создаётся в `work/specs/`
2. Скрипт пишется в `work/scripts/`
3. Выходные CSV → `work/data/`, отчёты → `work/reports/`
4. После завершения TZ обновить `memory/TZ_STATUS.md`

## Важные ограничения

1. Большинство датасетов НЕ имеют типизации ошибок — только Who&When HC и TRAIL
2. Для большинства ошибок данных мало (n < 20) — честно указываем "данных недостаточно"
3. Датасеты большие — не загружать целиком без необходимости
4. Стандартный KS-тест некорректен при MLE-оценке параметров — использовать модифицированный (§2.2.4 учебника)
5. Who&When: использовать только Hand-Crafted (58 записей), не Algorithm-Generated (126)
