# ТЗ №4.8 — Отчёт: исправление данных
Дата: 2026-05-06  
Версия: v2 (TRAIL + Who&When HC)  

---
## 1. Что исправлено

Обнаружены две методологические ошибки в предыдущих шагах:

1. **TRAIL** — ошибочно исключён как синтетический. Исправлено: возвращён как источник экспертной разметки (148 трейсов, GAIA + SWE-bench Lite).

2. **Who&When** — содержал 184 записи (126 Algorithm-Generated + 58 Hand-Crafted). Исправлено: осталены только 58 Hand-Crafted.

### Изменения в количестве записей

| Сущность | Было (старое) | Стало (новое) | Δ |
|---|---|---|---|
| Who&When (источник ошибок) | 184 | 58 | −126 |
| Who&When (trajectories) | 184 | 46 | −138 |
| errors_classified.csv | 518 строк | ~38 строк | varies |
| stats_full.csv | старый | 38 строк | varies |
| **+ TRAIL** | 0 | 143 trajectories, 836 errors | **+836** |

## 2. TRAIL: извлечённые ошибки

Источник: TRAIL — 148 трейсов (117 GAIA + 31 SWE-bench Lite), экспертная разметка.

| error_id | name_ru | n trajectories | p(traj) [95% CI] | n errors | p(msg) |
|---|---|---|---|---|---|
| orchestration_failure | Сбой оркестрации | 92/143 | 0.643 [0.562, 0.717] | 185 | 0.04093 |
| hallucination | Галлюцинация | 83/143 | 0.580 [0.498, 0.658] | 105 | 0.02311 |
| instruction_adherence_failure | Несоблюдение инструкций | 77/143 | 0.538 [0.457, 0.618] | 154 | 0.03411 |
| code_error | Ошибка в коде | 74/143 | 0.517 [0.436, 0.598] | 197 | 0.04335 |
| resource_abuse | Избыточное потребление ресурсов | 45/143 | 0.315 [0.244, 0.395] | 60 | 0.01320 |
| kv_cache_loss | Потеря KV-кэша | 44/143 | 0.308 [0.238, 0.388] | 49 | 0.01078 |
| misinterpretation_of_tool_output | Неверная интерпретация результата | 40/143 | 0.280 [0.213, 0.358] | 57 | 0.01254 |
| invalid_invocation | Некорректный вызов инструмента | 10/143 | 0.070 [0.038, 0.124] | 11 | 0.00242 |
| tool_web_failure | Сбой доступа к веб-ресурсу | 5/143 | 0.035 [0.015, 0.079] | 5 | 0.00110 |
| resource_not_found | Ресурс не найден | 4/143 | 0.028 [0.011, 0.070] | 7 | 0.00154 |
| system_failure | Системный сбой | 2/143 | 0.014 [0.004, 0.050] | — | 0.00044 |
| tool_timeout | Таймаут вызова инструмента | 2/143 | 0.014 [0.004, 0.050] | — | 0.00044 |

## 3. Who&When Hand-Crafted: обновлённая классификация

Источник: только Hand-Crafted.parquet — 58 трейдов, 46 с классифицированными ошибками.

| error_id | name_ru | n trajectories | p(traj) |
|---|---|---|---|
| tool_web_failure | Сбой доступа к веб-ресурсу | 23/46 | 0.500 |
| orchestration_failure | Сбой оркестрации | 16/46 | 0.348 |
| code_error | Ошибка в коде | 11/46 | 0.239 |
| resource_abuse | Избыточное потребление ресурсов | 5/46 | 0.109 |
| factual_error | Фактическая ошибка | 4/46 | 0.087 |
| hallucination | Галлюцинация | 2/46 | 0.043 |

## 4. Обновлённая статистика

### TRAIL (GAIA + SWE-bench Lite, 2024)

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| orchestration_failure | 92/143 | 0.6434 | 0.04093 | 0.562–0.717 |  |
| hallucination | 83/143 | 0.5804 | 0.02311 | 0.498–0.658 |  |
| instruction_adherence_failure | 77/143 | 0.5385 | 0.03411 | 0.457–0.618 |  |
| code_error | 74/143 | 0.5175 | 0.04335 | 0.436–0.598 |  |
| resource_abuse | 45/143 | 0.3147 | 0.01320 | 0.244–0.395 |  |
| kv_cache_loss | 44/143 | 0.3077 | 0.01078 | 0.238–0.388 |  |
| misinterpretation_of_tool_output | 40/143 | 0.2797 | 0.01254 | 0.213–0.358 |  |
| invalid_invocation | 10/143 | 0.0699 | 0.00242 | 0.038–0.124 | ⚠ |
| tool_web_failure | 5/143 | 0.0350 | 0.00110 | 0.015–0.079 | ⚠ |
| resource_not_found | 4/143 | 0.0280 | 0.00154 | 0.011–0.070 | ⚠ |
| system_failure | 2/143 | 0.0140 | 0.00044 | 0.004–0.050 | ⚠ |
| tool_timeout | 2/143 | 0.0140 | 0.00044 | 0.004–0.050 | ⚠ |

### Who&When Hand-Crafted

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| tool_web_failure | 23/46 | 0.5000 | 0.01003 | 0.361–0.639 |  |
| orchestration_failure | 16/46 | 0.3478 | 0.00668 | 0.227–0.492 | ⚠ |
| code_error | 11/46 | 0.2391 | 0.00459 | 0.139–0.379 | ⚠ |
| resource_abuse | 5/46 | 0.1087 | 0.00209 | 0.047–0.230 | ⚠ |
| factual_error | 4/46 | 0.0870 | 0.00167 | 0.034–0.203 | ⚠ |
| hallucination | 2/46 | 0.0435 | 0.00084 | 0.012–0.145 | ⚠ |

### AgentRx / magentic_one

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| instruction_adherence_failure | 25/44 | 0.5682 | N/A | 0.422–0.703 |  |
| guardrails_triggered | 23/44 | 0.5227 | N/A | 0.379–0.662 |  |
| misinterpretation_of_tool_output | 17/44 | 0.3864 | N/A | 0.257–0.534 | ⚠ |
| intent_plan_misalignment | 7/44 | 0.1591 | N/A | 0.079–0.294 | ⚠ |
| intent_not_supported | 5/44 | 0.1136 | N/A | 0.050–0.240 | ⚠ |
| invention_of_new_information | 5/44 | 0.1136 | N/A | 0.050–0.240 | ⚠ |
| invalid_invocation | 1/44 | 0.0227 | N/A | 0.004–0.118 | ⚠ |
| system_failure | 1/44 | 0.0227 | N/A | 0.004–0.118 | ⚠ |

### AgentRx / tau_retail

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| underspecified_user_intent | 10/29 | 0.3448 | N/A | 0.199–0.527 | ⚠ |
| intent_plan_misalignment | 8/29 | 0.2759 | N/A | 0.147–0.457 | ⚠ |
| misinterpretation_of_tool_output | 7/29 | 0.2414 | N/A | 0.122–0.421 | ⚠ |
| instruction_adherence_failure | 6/29 | 0.2069 | N/A | 0.098–0.384 | ⚠ |
| intent_not_supported | 2/29 | 0.0690 | N/A | 0.019–0.220 | ⚠ |
| invalid_invocation | 2/29 | 0.0690 | N/A | 0.019–0.220 | ⚠ |
| system_failure | 1/29 | 0.0345 | N/A | 0.006–0.172 | ⚠ |

### nebius/SWE-agent-trajectories (keyword)

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| resource_not_found | 33565/80036 | 0.4194 | 0.04973 | 0.416–0.423 |  |
| tool_web_failure | 26379/80036 | 0.3296 | 0.02247 | 0.326–0.333 |  |

### ibm-research/ITBench-Trajectories (keyword)

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| tool_timeout | 80/105 | 0.7619 | 0.09429 | 0.672–0.833 |  |

### yoonholee/terminalbench-trajectories (keyword)

| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |
|---|---|---|---|---|---|
| memory_error | 1750/52104 | 0.0336 | 0.01244 | 0.032–0.035 |  |
| permission_error | 267/52104 | 0.0051 | 0.00041 | 0.005–0.006 |  |

## 5. Распределения ошибок (TRAIL, n≥20)

| error_id | Лучшее распределение | Параметры | KS p-value | Вывод |
|---|---|---|---|---|
| kv_cache_loss | gamma | 2.8675, 0.0000, 12.0348 | 0.9389 | ⚠ слабое |
| resource_abuse | gamma | 2.4850, 0.0000, 11.0462 | 0.8071 | ⚠ слабое |
| misinterpretation_of_tool_output | exponential | 7.0000, 24.1404 | 0.1726 | ⚠ слабое |
| code_error | gamma | 2.0510, 0.0000, 14.4343 | 0.1670 | ✓ |
| instruction_adherence_failure | gamma | 2.4012, 0.0000, 7.7450 | 0.0015 | ✓ |
| hallucination | lognorm | 0.7251, 0.0000, 16.7880 | 0.0011 | ✓ |
| orchestration_failure | exponential | 7.0000, 9.2541 | 0.0000 | ✓ |

## 6. Финальная сводная таблица (all_errors_final.csv)

Всего строк: 38  
Источников: 7  
Уникальных error_id: 20  

### По классам моделирования

**Категория 1** (12 записей):  
hallucination, instruction_adherence_failure, intent_not_supported, intent_plan_misalignment, invention_of_new_information, underspecified_user_intent, factual_error

**Категория 2** (1 записей):  
kv_cache_loss

**Категория 3** (25 записей):  
code_error, invalid_invocation, misinterpretation_of_tool_output, orchestration_failure, resource_abuse, resource_not_found, system_failure, tool_timeout, tool_web_failure, guardrails_triggered, permission_error, memory_error

### Распределение data_quality

- **medium**: 23 записей
- **high**: 15 записей
