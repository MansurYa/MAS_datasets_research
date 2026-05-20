# ТЗ №4.6 — Полный статистический анализ ошибок из keyword search

**Дата:** 2026-05-05

## 1. Статистика keyword search — надёжные пары

Надёжные пары определены в `docs/tz4_5_category_interpretation.md`.
**Примечание:** KS-тест при n >> 3000 (nebius) имеет высокую мощность — отвержение H0 (p < 0.05) информативно и означает, что стандартное распределение не подходит для фактических данных.

| category | dataset | n_trajectories_with_error | n_trajectories_total | p_trajectory | P(traj)_CI95 | total_steps | p_message | P(msg)_CI95 | insufficient | best_dist | best_KS | best_p |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tool_web_failure | nebius | 26379 | 80036 | 0.3296 | [0.3263, 0.3329] | 4311283 | 0.022469 | [0.022329, 0.022609] |  | exponential | 0.1480 | 0.0000 |
| resource_not_found | nebius | 33565 | 80036 | 0.4194 | [0.4160, 0.4228] | 4311283 | 0.049727 | [0.049522, 0.049933] |  | exponential | 0.0893 | 0.0000 |
| tool_timeout | itbench | 80 | 105 | 0.7619 | [0.6721, 0.8332] | 19292 | 0.094288 | [0.090244, 0.098493] |  | weibull_min | 0.1288 | 0.1286 |
| permission_error | terminalbench | 267 | 52104 | 0.0051 | [0.0045, 0.0058] | 1622075 | 0.000409 | [0.000379, 0.000441] |  | lognorm | 0.1416 | 0.0000 |
| memory_error | terminalbench | 1750 | 52104 | 0.0336 | [0.0321, 0.0352] | 1622075 | 0.012443 | [0.012274, 0.012615] |  | exponential | 0.2663 | 0.0000 |

_P(traj) = n_trajectories_with_error / n_trajectories_total;_ _P(msg) = n_occurrences_total / total_steps._

## 2. Описательная статистика позиций ошибок

Две версии: абсолютная (номер шага) и нормализованная (step / trajectory_length).

### 2.1 `tool_web_failure` / `nebius` (n=26379)

**absolute позиция:**
| Метрика | Значение |
|---|---|
| n | 26379 |
| mean | 19.4064 |
| median | 14.0000 |
| std | 29.8608 |
| min | 2 |
| max | 594 |
| p25 | 8.0000 |
| p75 | 24.0000 |
| p90 | 36.0000 |
| p95 | 48.0000 |

![tool_web_failure/nebius absolute](data/plots/hist_kw_tool_web_failure_nebius.png)

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 2.0000, 17.4064 | 0.1480 | 0.0000 | ⚠️ |
| weibull_min | 1.0398, 0.0000, 19.7753 | 0.1044 | 0.0000 | ⚠️ |
| lognorm | 0.9778, 0.0000, 12.4067 | 0.1284 | 0.0000 | ⚠️ |

**exponential:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**weibull_min:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**lognorm:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.


**normalized позиция:**
| Метрика | Значение |
|---|---|
| n | 26379 |
| mean | 0.3956 |
| median | 0.3673 |
| std | 0.2606 |
| min | 0.0032 |
| max | 0.9932 |
| p25 | 0.1695 |
| p75 | 0.5957 |
| p90 | 0.7692 |
| p95 | 0.8571 |

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 0.0032, 0.3923 | 0.1208 | 0.0000 | ⚠️ |
| weibull_min | 1.4284, 0.0000, 0.4327 | 0.0620 | 0.0000 | ⚠️ |
| lognorm | 0.9955, 0.0000, 0.2793 | 0.1177 | 0.0000 | ⚠️ |
| beta | 0.9915, 1.5028, 0.0032, 0.9905 | 0.0185 | 0.0000 | ⚠️ |
| uniform | 0.0032, 0.9900 | 0.1563 | 0.0000 | ⚠️ |

**exponential:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**weibull_min:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**lognorm:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**beta:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**uniform:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.


### 2.2 `resource_not_found` / `nebius` (n=33565)

**absolute позиция:**
| Метрика | Значение |
|---|---|
| n | 33565 |
| mean | 13.1856 |
| median | 10.0000 |
| std | 12.0091 |
| min | 2 |
| max | 348 |
| p25 | 6.0000 |
| p75 | 16.0000 |
| p90 | 26.0000 |
| p95 | 36.0000 |

![resource_not_found/nebius absolute](data/plots/hist_kw_resource_not_found_nebius.png)

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 2.0000, 11.1856 | 0.0893 | 0.0000 | ⚠️ |
| weibull_min | 1.2664, 0.0000, 14.3155 | 0.1060 | 0.0000 | ⚠️ |
| lognorm | 0.8072, 0.0000, 9.5762 | 0.1053 | 0.0000 | ⚠️ |

**exponential:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**weibull_min:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**lognorm:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.


**normalized позиция:**
| Метрика | Значение |
|---|---|
| n | 33565 |
| mean | 0.2934 |
| median | 0.2162 |
| std | 0.2391 |
| min | 0.0025 |
| max | 0.9903 |
| p25 | 0.1075 |
| p75 | 0.4235 |
| p90 | 0.6667 |
| p95 | 0.8000 |

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 0.0025, 0.2909 | 0.0592 | 0.0000 | ⚠️ |
| weibull_min | 1.2347, 0.0000, 0.3147 | 0.0393 | 0.0000 | ⚠️ |
| lognorm | 0.9756, 0.0000, 0.1985 | 0.0499 | 0.0000 | ⚠️ |
| beta | 0.9316, 2.4917, 0.0025, 1.1033 | 0.0584 | 0.0000 | ⚠️ |
| uniform | 0.0025, 0.9878 | 0.3337 | 0.0000 | ⚠️ |

**exponential:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**weibull_min:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**lognorm:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**beta:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.

**uniform:** KS-тест информативен (n>>3000): H0 отвергнута, распределение не подходит.


### 2.3 `tool_timeout` / `itbench` (n=80)

**absolute позиция:**
| Метрика | Значение |
|---|---|
| n | 80 |
| mean | 45.1625 |
| median | 47.5000 |
| std | 29.5264 |
| min | 9 |
| max | 161 |
| p25 | 17.7500 |
| p75 | 61.2500 |
| p90 | 76.5000 |
| p95 | 91.3000 |

![tool_timeout/itbench absolute](data/plots/hist_kw_tool_timeout_itbench.png)

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 9.0000, 36.1625 | 0.1782 | 0.0108 | ⚠️ n<100 |
| weibull_min | 1.5640, 0.0000, 50.2876 | 0.1288 | 0.1286 | ⚠️ n<100 |
| lognorm | 0.7976, 0.0000, 34.5962 | 0.1779 | 0.0110 | ⚠️ n<100 |

**exponential:** ⚠️ n=80<<3000. Низкая мощность KS-теста.

**weibull_min:** ⚠️ n=80<<3000. Низкая мощность KS-теста.

**lognorm:** ⚠️ n=80<<3000. Низкая мощность KS-теста.


**normalized позиция:**
| Метрика | Значение |
|---|---|
| n | 80 |
| mean | 0.2319 |
| median | 0.1989 |
| std | 0.1780 |
| min | 0.0266 |
| max | 0.8895 |
| p25 | 0.1149 |
| p75 | 0.2865 |
| p90 | 0.4570 |
| p95 | 0.6599 |

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 0.0266, 0.2053 | 0.1095 | 0.2728 | ⚠️ n<100 |
| weibull_min | 1.4217, 0.0000, 0.2567 | 0.0863 | 0.5614 | ⚠️ n<100 |
| lognorm | 0.7636, 0.0000, 0.1768 | 0.0794 | 0.6641 | ⚠️ n<100 |
| beta | 1.3434, 109.1127, 0.0247, 17.0317 | 0.0584 | 0.9326 | ⚠️ n<100 |
| uniform | 0.0266, 0.8629 | 0.4696 | 0.0000 | ⚠️ n<100 |

**exponential:** ⚠️ n=80<<3000. Низкая мощность KS-теста.

**weibull_min:** ⚠️ n=80<<3000. Низкая мощность KS-теста.

**lognorm:** ⚠️ n=80<<3000. Низкая мощность KS-теста.

**beta:** ⚠️ n=80<<3000. Низкая мощность KS-теста.

**uniform:** ⚠️ n=80<<3000. Низкая мощность KS-теста.


### 2.4 `permission_error` / `terminalbench` (n=267)

**absolute позиция:**
| Метрика | Значение |
|---|---|
| n | 267 |
| mean | 18.5243 |
| median | 11.0000 |
| std | 20.9925 |
| min | 3 |
| max | 183 |
| p25 | 8.0000 |
| p75 | 19.0000 |
| p90 | 42.0000 |
| p95 | 58.0000 |

![permission_error/terminalbench absolute](data/plots/hist_kw_permission_error_terminalbench.png)

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 3.0000, 15.5243 | 0.1618 | 0.0000 | ⚠️ n<100 |
| weibull_min | 1.1405, 0.0000, 19.6198 | 0.1719 | 0.0000 | ⚠️ n<100 |
| lognorm | 0.7507, 0.0000, 13.0739 | 0.1416 | 0.0000 | ⚠️ n<100 |


**normalized позиция:**
| Метрика | Значение |
|---|---|
| n | 267 |
| mean | 0.4326 |
| median | 0.4000 |
| std | 0.2391 |
| min | 0.0494 |
| max | 1.0000 |
| p25 | 0.2500 |
| p75 | 0.5702 |
| p90 | 0.7831 |
| p95 | 0.8947 |

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 0.0494, 0.3832 | 0.1791 | 0.0000 | ⚠️ n<100 |
| weibull_min | 1.8824, 0.0000, 0.4875 | 0.0376 | 0.8302 | ⚠️ n<100 |
| lognorm | 0.6823, 0.0000, 0.3568 | 0.1105 | 0.0027 | ⚠️ n<100 |
| beta | 1.1352, 1.8285, 0.0484, 1.0058 | 0.0557 | 0.3645 | ⚠️ n<100 |
| uniform | 0.0494, 0.9506 | 0.2075 | 0.0000 | ⚠️ n<100 |


### 2.5 `memory_error` / `terminalbench` (n=1750)

**absolute позиция:**
| Метрика | Значение |
|---|---|
| n | 1750 |
| mean | 20.3794 |
| median | 10.0000 |
| std | 32.8247 |
| min | 1 |
| max | 623 |
| p25 | 2.0000 |
| p75 | 26.0000 |
| p90 | 50.0000 |
| p95 | 73.0000 |

![memory_error/terminalbench absolute](data/plots/hist_kw_memory_error_terminalbench.png)

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 1.0000, 19.3794 | 0.2663 | 0.0000 | ⚠️ n<100 |
| weibull_min | 0.7714, 0.0000, 17.1342 | 0.1429 | 0.0000 | ⚠️ n<100 |
| lognorm | 1.3632, 0.0000, 8.6379 | 0.1750 | 0.0000 | ⚠️ n<100 |


**normalized позиция:**
| Метрика | Значение |
|---|---|
| n | 1750 |
| mean | 0.3638 |
| median | 0.3243 |
| std | 0.3107 |
| min | 0.0011 |
| max | 1.0000 |
| p25 | 0.0513 |
| p75 | 0.6197 |
| p90 | 0.8214 |
| p95 | 0.9064 |

**Подгонка распределений:**

| distribution | params | KS_stat | KS_p | note |
|---|---|---|---|---|
| exponential | 0.0011, 0.3627 | 0.1269 | 0.0000 | ⚠️ n<100 |
| weibull_min | 0.9211, 0.0000, 0.3517 | 0.1227 | 0.0000 | ⚠️ n<100 |
| lognorm | 1.4775, 0.0000, 0.1788 | 0.1599 | 0.0000 | ⚠️ n<100 |
| beta | 0.6733, 1.5133, 0.0011, 1.1148 | 0.0888 | 0.0000 | ⚠️ n<100 |
| uniform | 0.0011, 0.9989 | 0.2464 | 0.0000 | ⚠️ n<100 |


## 3. Сводная таблица всех ошибок

Объединены: AgentRx (magentic_one, tau_retail), Who&When (who_and_when), keyword search (keyword_search_nebius, keyword_search_itbench, keyword_search_terminalbench).

### Класс 1 — Невозможно моделировать (требует LLM)

| error_id | source | n_trajectories_with_error | n_trajectories_total | p_trajectory | total_steps | p_message | best_distribution | data_quality | insufficient_data |
|---|---|---|---|---|---|---|---|---|---|
| instruction_adherence_failure | magentic_one | 25 | 44 | 0.5682 | 2993 | 0.065820 | — | medium | False |
| misinterpretation_of_tool_output | magentic_one | 17 | 44 | 0.3864 | 2993 | 0.007685 | — | medium | True |
| intent_not_supported | magentic_one | 5 | 44 | 0.1136 | 2993 | 0.007350 | — | medium | True |
| intent_plan_misalignment | magentic_one | 7 | 44 | 0.1591 | 2993 | 0.006348 | — | medium | True |
| invention_of_new_information | magentic_one | 5 | 44 | 0.1136 | 2993 | 0.002673 | — | medium | True |
| underspecified_user_intent | tau_retail | 10 | 29 | 0.3448 | 1064 | 0.009399 | — | medium | True |
| intent_plan_misalignment | tau_retail | 8 | 29 | 0.2759 | 1064 | 0.007519 | — | medium | True |
| misinterpretation_of_tool_output | tau_retail | 7 | 29 | 0.2414 | 1064 | 0.007519 | — | medium | True |
| instruction_adherence_failure | tau_retail | 6 | 29 | 0.2069 | 1064 | 0.005639 | — | medium | True |
| intent_not_supported | tau_retail | 2 | 29 | 0.0690 | 1064 | 0.001880 | — | medium | True |
| unclassified | who_and_when | 74 | 184 | 0.4022 | 4092 | 0.020772 | exponential | medium | False |
| code_error | who_and_when | 30 | 184 | 0.1630 | 4092 | 0.007331 | exponential | medium | False |
| orchestration_failure | who_and_when | 17 | 184 | 0.0924 | 4092 | 0.004154 | — | medium | True |
| hallucination | who_and_when | 8 | 184 | 0.0435 | 4092 | 0.001955 | — | medium | True |
| factual_error | who_and_when | 6 | 184 | 0.0326 | 4092 | 0.001466 | — | medium | True |
| misinterpretation | who_and_when | 3 | 184 | 0.0163 | 4092 | 0.000733 | — | medium | True |

### Класс 2 — Моделируется напрямую

| error_id | source | n_trajectories_with_error | n_trajectories_total | p_trajectory | total_steps | p_message | best_distribution | data_quality | insufficient_data |
|---|---|---|---|---|---|---|---|---|---|
| tool_timeout | keyword_search_itbench | 80 | 105 | 0.7619 | 19292 | 0.094288 | weibull_min | high | False |

### Класс 3 — Моделируется статистически

| error_id | source | n_trajectories_with_error | n_trajectories_total | p_trajectory | total_steps | p_message | best_distribution | data_quality | insufficient_data |
|---|---|---|---|---|---|---|---|---|---|
| guardrails_triggered | magentic_one | 23 | 44 | 0.5227 | 2993 | 0.008019 | — | medium | False |
| invalid_invocation | magentic_one | 1 | 44 | 0.0227 | 2993 | 0.000334 | — | medium | True |
| system_failure | magentic_one | 1 | 44 | 0.0227 | 2993 | 0.000334 | — | medium | True |
| invalid_invocation | tau_retail | 2 | 29 | 0.0690 | 1064 | 0.003759 | — | medium | True |
| system_failure | tau_retail | 1 | 29 | 0.0345 | 1064 | 0.000940 | — | medium | True |
| tool_web_failure | who_and_when | 25 | 184 | 0.1359 | 4092 | 0.006354 | exponential | medium | False |
| resource_abuse | who_and_when | 9 | 184 | 0.0489 | 4092 | 0.002199 | — | medium | True |
| tool_web_failure | keyword_search_nebius | 26379 | 80036 | 0.3296 | 4311283 | 0.022469 | exponential | high | False |
| resource_not_found | keyword_search_nebius | 33565 | 80036 | 0.4194 | 4311283 | 0.049727 | exponential | high | False |
| permission_error | keyword_search_terminalbench | 267 | 52104 | 0.0051 | 1622075 | 0.000409 | lognorm | high | False |
| memory_error | keyword_search_terminalbench | 1750 | 52104 | 0.0336 | 1622075 | 0.012443 | exponential | high | False |

## 4. Ограничения

1. **Ложные срабатывания:** для nebius `tool_web_failure` и `resource_not_found` — ошибки могут появляться в коде задачи (решаемая проблема), а не как инфраструктурный сбой.
2. **Кластерная структура:** шаги внутри одной траектории не независимы. Wilson CI для P(message) занижен, так как не учитывает корреляцию.
3. **KS-тест при n >> 3000:** при большом n мощность теста высока — любое отклонение от модели отвергается. Это не означает, что данные «плохие»; это означает, что простые аналитические распределения не подходят.
4. **KS-тест при n < 100 (ITBench):** низкая мощность, результаты носят иллюстративный характер.
5. **n_occurrences_total** для keyword search использует данные из `keyword_search_results.csv` (ТЗ 4.5), где подсчёт вёлся по всем категориям. Для надёжных пар это соответствует реальному числу вхождений.