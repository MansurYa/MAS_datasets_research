---
name: reference-archive-map
description: Полная карта archive/ — все ТЗ, скрипты, парсеры, зависимости между ними
metadata:
  type: reference
---

# Карта архива (archive/)

**Статус:** Старый цикл, отклонён Huawei. Хранится как справочник парсеров и методологии.

## ТЗ архива (archive/specs/)

| ТЗ | Название | Что делать | Основной скрипт |
|----|----------|-----------|-----------------|
| ТЗ №1 | Разведка источников | Изучить структуру 7 датасетов, извлечь схемы | `tz1_reconnaissance.py` |
| ТЗ №2 | Унификация таксономии | Нормализовать AgentRx, классифицировать Who&When | `tz2_unify_classify.py` |
| ТЗ №3 | Агрегированная таблица | Собрать единый список ошибок, присвоить классы 1–4 | `tz3_aggregate.py` |
| ТЗ №4 | Статистический анализ | Подогнать распределения (Exp, Weibull, LogNormal) | `tz4_distributions.py` |
| ТЗ №4.6 | Keyword search статистика | Извлечь позиции ошибок из nebius/ITBench/terminalbench | `tz4_5_keyword_search.py`, `tz4_6_keyword_stats.py` |
| ТЗ №4.7 | Тяжёлые хвосты | Подогнать Pareto/Gamma/Lomax, Q-Q plots | `tz4_7_heavy_tails.py` |
| ТЗ №4.8 | Финальная сводка | Вернуть TRAIL, пересчитать для 3 источников | `tz4_8_trail_extract.py`, `tz4_8_stats.py`, `tz4_8_final.py` |
| ТЗ №5 | Финальный отчёт | Исправления, графики, документ на русском | `tz5_a_fix_data.py`, `tz5_d_report.py` |
| ТЗ №6 | Финализация | Исправить аномалии, методологический документ | `tz6_histograms.py`, `tz6_plots_v2.py` |
| ТЗ №7 | Подгонка распределений | Сравнить 8+ распределений для tool_web_failure/nebius | `tz7_analysis.py` |

## Парсеры датасетов (archive/scripts/)

### Основные парсеры

| Датасет | Парсер | Что делает |
|---------|--------|-----------|
| nebius/SWE-agent-trajectories | `tz1_reconnaissance.py` | Разведка структуры, извлечение ошибок |
| SWE-Gym/OpenHands-Sampled-Trajectories | `tz1_reconnaissance.py` | Разведка структуры, извлечение ошибок |
| yoonholee/terminalbench-trajectories | `tz1_reconnaissance.py` | Разведка структуры, извлечение ошибок |
| ibm-research/ITBench-Trajectories | `tz1_reconnaissance.py` | Разведка структуры, извлечение ошибок |
| microsoft/AgentRx | `tz2_unify_classify.py` | Унификация таксономии, классификация |
| Kevin355/Who_and_When | `tz2_unify_classify.py`, `tz4_8_who_when.py` | Классификация Hand-Crafted (исключение Algorithm-Generated) |
| iMeanAI/Mind2Web-Live | `tz1_reconnaissance.py` | Разведка структуры |
| TRAIL (GAIA + SWE-bench) | `tz4_8_trail_extract.py` | Извлечение ошибок, маппинг категорий |

### Утилиты и вспомогательные скрипты

| Скрипт | Назначение |
|--------|-----------|
| `tz4_5_keyword_search.py` | Поиск ошибок по ключевым словам в nebius, SWE-Gym, TerminalBench, ITBench |
| `tz4_6_keyword_stats.py` | Статистический анализ результатов keyword search |
| `tz4_7_heavy_tails.py` | Подгонка тяжёлых хвостов (Pareto, Gamma, Lomax) |
| `tz5_a_fix_data.py` | Исправление ошибок в данных (TRAIL, Who&When, параметры) |
| `tz5_b_plots.py` | Генерация графиков (гистограммы, Q-Q, сводные) |
| `tz5_c_csv.py` | Итоговый CSV с полной информацией |
| `tz5_d_report.py` | Финальный отчёт на русском |
| `tz6_histograms.py` | Гистограммы с наложением подогнанных распределений |
| `tz6_n_obs_v2.py` | График объёма наблюдений (log₁₀ шкала) |
| `tz6_plots.py` | Сводные графики (P(trajectory), pie chart, log₁₀(n)) |
| `tz6_plots_v2.py` | Улучшенные сводные графики |
| `tz7_analysis.py` | Глубокий анализ tool_web_failure/nebius (8+ распределений, AIC/BIC, diptest) |

## Pipeline зависимостей

```
tz1_reconnaissance.py
├─→ tz2_unify_classify.py
│   ├─→ tz3_aggregate.py
│   ├─→ tz4_distributions.py
│   └─→ tz4_5_keyword_search.py
│       ├─→ tz4_6_keyword_stats.py
│       │   ├─→ tz4_6_report.py
│       │   └─→ tz4_7_heavy_tails.py
│       │       └─→ tz4_7_report.py
│       └─→ tz7_analysis.py
│
├─→ tz4_8_trail_extract.py
├─→ tz4_8_who_when.py
└─→ tz4_8_stats.py
    └─→ tz4_8_final.py
        └─→ tz4_8_final_table.py
            └─→ tz5_a_fix_data.py
                ├─→ tz5_b_plots.py
                ├─→ tz5_c_csv.py
                └─→ tz5_d_report.py
                    ├─→ tz6_histograms.py
                    ├─→ tz6_n_obs_v2.py
                    ├─→ tz6_plots.py
                    └─→ tz6_plots_v2.py
```

## Ключевые файлы данных

| Файл | Источник | Описание |
|------|----------|---------|
| `archive/docs/errors_stats.csv` | ТЗ №5 | Итоговая таблица ошибок с классификацией и параметрами распределений |
| `archive/docs/methodology.md` | ТЗ №6 | Методологический документ (таксономия TRAIL, классы моделирования 1–4) |
| `archive/docs/fault_analysis_report.md` | ТЗ №5 | Финальный отчёт (отклонён Huawei) |

## Как найти нужный парсер

**Нужен парсер nebius?**
→ `tz1_reconnaissance.py` (разведка) или `tz4_5_keyword_search.py` (поиск по ключевым словам)

**Нужна классификация AgentRx?**
→ `tz2_unify_classify.py`

**Нужна классификация Who&When (только Hand-Crafted)?**
→ `tz4_8_who_when.py`

**Нужна классификация TRAIL?**
→ `tz4_8_trail_extract.py`

**Нужна подгонка распределений?**
→ `tz4_distributions.py` (базовая) или `tz4_7_heavy_tails.py` (тяжёлые хвосты) или `tz7_analysis.py` (глубокий анализ)

**Нужны графики?**
→ `tz5_b_plots.py` (базовые) или `tz6_plots_v2.py` (улучшенные) или `tz6_histograms.py` (гистограммы)

## Важные ограничения

- **Who&When:** использовать только Hand-Crafted (58 записей), не Algorithm-Generated (126)
- **TRAIL:** 143 траектории, 836 ошибок, экспертная разметка
- **Keyword search:** работает только для nebius, SWE-Gym, TerminalBench, ITBench (остальные датасеты не имеют явной типизации ошибок)
- **Распределения:** стандартный KS-тест некорректен при MLE — использовать модифицированный (§2.2.4 учебника)
