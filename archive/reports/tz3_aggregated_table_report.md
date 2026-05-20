# ТЗ №3 — Агрегированная таблица ошибок с классификацией

**Дата:** 2026-05-04
**Всего ошибок:** 25

## 1. Сводная таблица

| error_id | name_en | modeling_class | total_n | sufficient_data | sources |
|---|---|---|---|---|---|
| instruction_adherence_failure | Instruction Adherence Failure | 1 | 31 | True | agentRx |
| code_error | Code Error | 1 | 30 | True | who_and_when |
| misinterpretation_of_tool_output | Misinterpretation of Tool Output | 1 | 24 | True | agentRx |
| orchestration_failure | Orchestration Failure | 1 | 17 | False | who_and_when |
| intent_plan_misalignment | Intent-Plan Misalignment | 1 | 15 | False | agentRx |
| underspecified_user_intent | Underspecified User Intent | 1 | 10 | False | agentRx |
| hallucination | Hallucination | 1 | 8 | False | who_and_when |
| intent_not_supported | Intent Not Supported | 1 | 7 | False | agentRx |
| factual_error | Factual Error | 1 | 6 | False | who_and_when |
| invention_of_new_information | Invention of New Information | 1 | 5 | False | agentRx |
| misinterpretation | Misinterpretation | 1 | 3 | False | who_and_when |
| kv_cache_loss | KV-Cache Loss | 2 | 44 | True | trail |
| tool_timeout | Tool Call Timeout | 2 | 4 | False | trail |
| memory_bandwidth_bottleneck | Memory Bandwidth Bottleneck | 2 | 0 | False | none |
| bad_retry_policy | Bad Retry Policy | 2 | 0 | False | none |
| kv_transfer_failure | KV-Transfer Failure | 2 | 0 | False | none |
| resource_abuse | Resource Abuse | 3 | 51 | True | trail, who_and_when |
| tool_web_failure | Tool/Web Access Failure | 3 | 25 | True | who_and_when |
| guardrails_triggered | Guardrails Triggered | 3 | 23 | True | agentRx |
| invalid_invocation | Invalid Tool Invocation | 3 | 3 | False | agentRx |
| system_failure | System Failure | 3 | 2 | False | agentRx |
| hardware_degradation | Hardware Degradation | 4 | 0 | False | none |
| gpu_throttling | GPU Throttling | 4 | 0 | False | none |
| correlated_ssd_failure | Correlated SSD Failure | 4 | 0 | False | none |
| network_power_failure | Network/Power Failure | 4 | 0 | False | none |

## 2. Таблица по классам моделирования

### Класс 1 — Невозможно моделировать

| error_id | name_en | name_ru | modeling_class_reason |
|---|---|---|---|
| instruction_adherence_failure | Instruction Adherence Failure | Несоблюдение инструкций | Requires full LLM reasoning to reproduce; cannot be injected as a structural IR-graph event. |
| misinterpretation_of_tool_output | Misinterpretation of Tool Output | Неверная интерпретация вывода инструмента | Semantic misinterpretation requires LLM reasoning; cannot be structurally injected. |
| intent_not_supported | Intent Not Supported | Неподдерживаемое намерение | Depends on LLM capability assessment; not reproducible without full model execution. |
| intent_plan_misalignment | Intent-Plan Misalignment | Несоответствие намерения и плана | Goal deviation requires LLM-level understanding of intent; not injectable structurally. |
| invention_of_new_information | Invention of New Information | Изобретение новой информации | Hallucination requires full LLM execution; cannot be reproduced structurally. |
| underspecified_user_intent | Underspecified User Intent | Недостаточно конкретное намерение пользователя | Ambiguity resolution depends on LLM reasoning; not injectable as a structural event. |
| code_error | Code Error | Ошибка в коде | Code correctness depends on LLM generation quality; cannot be injected structurally. |
| orchestration_failure | Orchestration Failure | Сбой оркестрации | Routing and delegation decisions require LLM reasoning; not injectable structurally. |
| hallucination | Hallucination | Галлюцинация | Hallucination requires full LLM execution; cannot be reproduced structurally. |
| factual_error | Factual Error | Фактическая ошибка | Factual correctness depends on LLM knowledge; not injectable structurally. |
| misinterpretation | Misinterpretation | Неверная интерпретация | Semantic misinterpretation requires LLM reasoning; not injectable structurally. |

### Класс 2 — Моделируется напрямую

| error_id | name_en | name_ru | modeling_class_reason |
|---|---|---|---|
| kv_cache_loss | KV-Cache Loss | Потеря KV-кэша | Directly modeled by removing cached state in IR-graph block; no LLM required. |
| tool_timeout | Tool Call Timeout | Таймаут вызова инструмента | Modeled directly as a probabilistic delay/failure on tool-call blocks in IR-graph. |
| memory_bandwidth_bottleneck | Memory Bandwidth Bottleneck | Узкое место по memory bandwidth | Modeled directly as throughput reduction parameter on inference blocks in IR-graph. |
| bad_retry_policy | Bad Retry Policy | Неверная политика ретраев | Directly modeled by setting retry policy parameters in IR-graph blocks. |
| kv_transfer_failure | KV-Transfer Failure | Сбой KV-transfer | Directly modeled as state-transfer failure block in IR-graph. |

### Класс 3 — Моделируется статистически

| error_id | name_en | name_ru | modeling_class_reason |
|---|---|---|---|
| resource_abuse | Resource Abuse | Избыточное потребление ресурсов | Cannot reproduce without LLM reasoning, but frequency and step distribution can be estimated statistically. |
| guardrails_triggered | Guardrails Triggered | Срабатывание защитных ограничений | Frequency can be estimated statistically; effect modeled as a step-level failure event. |
| invalid_invocation | Invalid Tool Invocation | Некорректный вызов инструмента | Can be modeled as a probabilistic tool-call failure event with estimated frequency. |
| system_failure | System Failure | Системный сбой | Modeled as a probabilistic hard-failure event on execution blocks. |
| tool_web_failure | Tool/Web Access Failure | Сбой доступа к инструменту/веб | Modeled as probabilistic tool-call failure; frequency and step distribution available from data. |

### Класс 4 — Нецелесообразно моделировать

| error_id | name_en | name_ru | modeling_class_reason |
|---|---|---|---|
| hardware_degradation | Hardware Degradation | Деградация оборудования | Technically feasible but simulator is not designed for long-horizon hardware degradation scenarios. |
| gpu_throttling | GPU Throttling | Троттлинг GPU | Rarely occurs in large clusters; out of scope for the simulator's target scenarios. |
| correlated_ssd_failure | Correlated SSD Failure | Коррелированные сбои SSD | Infrastructure-level failure outside the scope of agent trajectory simulation. |
| network_power_failure | Network/Power Failure | Сетевые и power-сбои | Infrastructure-level failure outside the scope of agent trajectory simulation. |

## 3. Статистика по источникам

| error_id | name_en | trail_n | trail_p | trail_ci_lower | trail_ci_upper | agentRx_n | agentRx_p | agentRx_ci_lower | agentRx_ci_upper | who_and_when_n | who_and_when_p | who_and_when_ci_lower | who_and_when_ci_upper | total_n | sufficient_data |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| resource_abuse | Resource Abuse | 42 | 0.2838 | 0.2173 | 0.3612 | 0 |  |  |  | 9 | 0.0489 | 0.0259 | 0.0903 | 51 | True |
| kv_cache_loss | KV-Cache Loss | 44 | 0.2973 | 0.2295 | 0.3753 | 0 |  |  |  | 0 |  |  |  | 44 | True |
| instruction_adherence_failure | Instruction Adherence Failure | 0 |  |  |  | 31 | 0.4247 | 0.3178 | 0.539 | 0 |  |  |  | 31 | True |
| code_error | Code Error | 0 |  |  |  | 0 |  |  |  | 30 | 0.163 | 0.1167 | 0.2232 | 30 | True |
| tool_web_failure | Tool/Web Access Failure | 0 |  |  |  | 0 |  |  |  | 25 | 0.1359 | 0.0938 | 0.1929 | 25 | True |
| misinterpretation_of_tool_output | Misinterpretation of Tool Output | 0 |  |  |  | 24 | 0.3288 | 0.2319 | 0.4427 | 0 |  |  |  | 24 | True |
| guardrails_triggered | Guardrails Triggered | 0 |  |  |  | 23 | 0.5227 | 0.3794 | 0.6625 | 0 |  |  |  | 23 | True |
| orchestration_failure | Orchestration Failure | 0 |  |  |  | 0 |  |  |  | 17 | 0.0924 | 0.0585 | 0.143 | 17 | False |
| intent_plan_misalignment | Intent-Plan Misalignment | 0 |  |  |  | 15 | 0.2055 | 0.1287 | 0.3117 | 0 |  |  |  | 15 | False |
| underspecified_user_intent | Underspecified User Intent | 0 |  |  |  | 10 | 0.3448 | 0.1994 | 0.5266 | 0 |  |  |  | 10 | False |
| hallucination | Hallucination | 0 |  |  |  | 0 |  |  |  | 8 | 0.0435 | 0.0222 | 0.0834 | 8 | False |
| intent_not_supported | Intent Not Supported | 0 |  |  |  | 7 | 0.0959 | 0.0472 | 0.185 | 0 |  |  |  | 7 | False |
| factual_error | Factual Error | 0 |  |  |  | 0 |  |  |  | 6 | 0.0326 | 0.015 | 0.0693 | 6 | False |
| invention_of_new_information | Invention of New Information | 0 |  |  |  | 5 | 0.1136 | 0.0495 | 0.2398 | 0 |  |  |  | 5 | False |
| tool_timeout | Tool Call Timeout | 4 | 0.027 | 0.0106 | 0.0674 | 0 |  |  |  | 0 |  |  |  | 4 | False |
| invalid_invocation | Invalid Tool Invocation | 0 |  |  |  | 3 | 0.0411 | 0.0141 | 0.114 | 0 |  |  |  | 3 | False |
| misinterpretation | Misinterpretation | 0 |  |  |  | 0 |  |  |  | 3 | 0.0163 | 0.0056 | 0.0468 | 3 | False |
| system_failure | System Failure | 0 |  |  |  | 2 | 0.0274 | 0.0075 | 0.0945 | 0 |  |  |  | 2 | False |
| memory_bandwidth_bottleneck | Memory Bandwidth Bottleneck | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |
| hardware_degradation | Hardware Degradation | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |
| gpu_throttling | GPU Throttling | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |
| correlated_ssd_failure | Correlated SSD Failure | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |
| kv_transfer_failure | KV-Transfer Failure | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |
| bad_retry_policy | Bad Retry Policy | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |
| network_power_failure | Network/Power Failure | 0 |  |  |  | 0 |  |  |  | 0 |  |  |  | 0 | False |

## 4. Выводы

### Ошибки классов 2–3 с sufficient_data=True (готовы к анализу распределений в ТЗ №4):

| error_id | name_en | modeling_class | total_n | sources |
|---|---|---|---|---|
| kv_cache_loss | KV-Cache Loss | 2 | 44 | trail |
| resource_abuse | Resource Abuse | 3 | 51 | trail, who_and_when |
| guardrails_triggered | Guardrails Triggered | 3 | 23 | agentRx |
| tool_web_failure | Tool/Web Access Failure | 3 | 25 | who_and_when |

### Распределение по классам:

- Класс 1: 11 ошибок
- Класс 2: 5 ошибок
- Класс 3: 5 ошибок
- Класс 4: 4 ошибок

### Источники данных:

- TRAIL: 3 ошибки с данными (n=148 траекторий)
- AgentRx: 9 ошибок с данными (magentic_one=44 + tau_retail=29 траекторий)
- Who&When: 7 ошибок с данными (n=184 случая)

**Итого с sufficient_data=True:** 7 из 25