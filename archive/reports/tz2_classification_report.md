# ТЗ №2 — Унификация таксономии и классификация ошибок

**Дата:** 2026-05-04

## 1. Унифицированная таксономия AgentRx

| Оригинал | Унифицированное | Вхождений |
|---|---|---|
| Guardrails Triggered | guardrails_triggered | 24 |
| Instruction Adherence Failure | instruction_adherence_failure | 6 |
| Instruction/Plan Adherence Failure | instruction_adherence_failure | 197 |
| Intent Not Supported | intent_not_supported | 2 |
| Intent Plan Misalignment | intent_plan_misalignment | 27 |
| Intent not supported | intent_not_supported | 22 |
| Invalid Invocation | invalid_invocation | 5 |
| Invention of new information | invention_of_new_information | 8 |
| Misinterpretation of Tool Output | misinterpretation_of_tool_output | 31 |
| System Failure | system_failure | 2 |
| Underspecified User Intent | underspecified_user_intent | 10 |

## 2. Результаты классификации Who&When

| Категория | Кол-во | % от 184 |
|---|---|---|
| unclassified | 85 | 46.2% |
| code_error | 30 | 16.3% |
| tool_web_failure | 26 | 14.1% |
| orchestration_failure | 17 | 9.2% |
| resource_abuse | 9 | 4.9% |
| hallucination | 8 | 4.3% |
| factual_error | 6 | 3.3% |
| misinterpretation | 3 | 1.6% |

**Неклассифицировано:** 85 из 184 (46.2%)

### 2.1 Примеры по категориям

**unclassified:**
- `The agent fails to collect price data for the daily tickets and season passes for California's Great`
- `The plan to solve the problem is incorrect.`
**code_error:**
- `The Python code is incorrect.`
- `The code is incorrect, as executing it returns no output.`
**resource_abuse:**
- `The agent assumes that the video is available for download, exhausting the step limit.`
- `The Paintball_Expert provides incorrect addresses for karting tracks and paintball venues in Cologne`
**misinterpretation:**
- `The expert misinterprets the output of the OCR function and provides the simplified fractions in an `
- `The step assumed the extracted population value (56,583) was the 2020 estimate without verifying its`
**hallucination:**
- `The agent hallucinates the video ID and calls the tool with placeholder data. The task is not attemp`
- `The agent assumes the existence of the file houston_weather_june_2020_2023.csv, which is not provide`
**factual_error:**
- `Made an incorrect assumption that the PDF file was available and accessible.`
- `The expert made a factual error. Thriller is not a song but an album.`
**tool_web_failure:**
- `The agent failed to locate the correct URL for the dataset from the USGS Nonindigenous Aquatic Speci`
- `The time of the oldest closed issue is not the same as the time when the 'Regression' label was adde`
**orchestration_failure:**
- `The agent is approaching the task in the wrong direction. It failed to locate the restaurant's name.`
- `The Orchestrator should instruct WebSurfer to collect the full list of Daniel Craig's movies on IMDb`

## 3. Статистика по категориям

| category | source | n_failures | n_trajectories_with_error | n_trajectories_total | p_trajectory | ci_lower | ci_upper | insufficient_data |
|---|---|---|---|---|---|---|---|---|
| instruction_adherence_failure | magentic_one | 197 | 25 | 44 | 0.5682 | 0.4222 | 0.7032 | False |
| guardrails_triggered | magentic_one | 24 | 23 | 44 | 0.5227 | 0.3794 | 0.6625 | False |
| misinterpretation_of_tool_output | magentic_one | 23 | 17 | 44 | 0.3864 | 0.2572 | 0.5338 | True |
| intent_not_supported | magentic_one | 22 | 5 | 44 | 0.1136 | 0.0495 | 0.2398 | True |
| intent_plan_misalignment | magentic_one | 19 | 7 | 44 | 0.1591 | 0.0793 | 0.2937 | True |
| invention_of_new_information | magentic_one | 8 | 5 | 44 | 0.1136 | 0.0495 | 0.2398 | True |
| invalid_invocation | magentic_one | 1 | 1 | 44 | 0.0227 | 0.004 | 0.1181 | True |
| system_failure | magentic_one | 1 | 1 | 44 | 0.0227 | 0.004 | 0.1181 | True |
| underspecified_user_intent | tau_retail | 10 | 10 | 29 | 0.3448 | 0.1994 | 0.5266 | True |
| intent_plan_misalignment | tau_retail | 8 | 8 | 29 | 0.2759 | 0.147 | 0.4572 | True |
| misinterpretation_of_tool_output | tau_retail | 8 | 7 | 29 | 0.2414 | 0.1222 | 0.4211 | True |
| instruction_adherence_failure | tau_retail | 6 | 6 | 29 | 0.2069 | 0.0985 | 0.3839 | True |
| invalid_invocation | tau_retail | 4 | 2 | 29 | 0.069 | 0.0191 | 0.2196 | True |
| intent_not_supported | tau_retail | 2 | 2 | 29 | 0.069 | 0.0191 | 0.2196 | True |
| system_failure | tau_retail | 1 | 1 | 29 | 0.0345 | 0.0061 | 0.1718 | True |
| unclassified | who_and_when | 85 | 74 | 184 | 0.4022 | 0.334 | 0.4743 | False |
| code_error | who_and_when | 30 | 30 | 184 | 0.163 | 0.1167 | 0.2232 | False |
| tool_web_failure | who_and_when | 26 | 25 | 184 | 0.1359 | 0.0938 | 0.1929 | False |
| orchestration_failure | who_and_when | 17 | 17 | 184 | 0.0924 | 0.0585 | 0.143 | True |
| resource_abuse | who_and_when | 9 | 9 | 184 | 0.0489 | 0.0259 | 0.0903 | True |
| hallucination | who_and_when | 8 | 8 | 184 | 0.0435 | 0.0222 | 0.0834 | True |
| factual_error | who_and_when | 6 | 6 | 184 | 0.0326 | 0.015 | 0.0693 | True |
| misinterpretation | who_and_when | 3 | 3 | 184 | 0.0163 | 0.0056 | 0.0468 | True |

## 4. Распределение ошибок по шагам

| category | source | step_mean | step_median | step_std | step_p25 | step_p75 | step_min | step_max | step_n |
|---|---|---|---|---|---|---|---|---|---|
| instruction_adherence_failure | magentic_one | 54.38 | 52.0 | 35.08 | 22.0 | 81.0 | 5 | 129 | 197 |
| guardrails_triggered | magentic_one | 40.21 | 27.0 | 34.33 | 17.0 | 52.25 | 5 | 129 | 24 |
| misinterpretation_of_tool_output | magentic_one | 14.57 | 11.0 | 8.22 | 10.0 | 18.5 | 2 | 34 | 23 |
| intent_not_supported | magentic_one | 45.82 | 24.0 | 40.27 | 16.25 | 95.0 | 4 | 112 | 22 |
| intent_plan_misalignment | magentic_one | 68.79 | 78.0 | 40.57 | 41.0 | 103.0 | 4 | 120 | 19 |
| invention_of_new_information | magentic_one | 38.12 | 26.0 | 37.0 | 16.5 | 38.75 | 12 | 124 | 8 |
| invalid_invocation | magentic_one | 34.0 | 34.0 | 0.0 | 34.0 | 34.0 | 34 | 34 | 1 |
| system_failure | magentic_one | 17.0 | 17.0 | 0.0 | 17.0 | 17.0 | 17 | 17 | 1 |
| underspecified_user_intent | tau_retail | 25.8 | 26.0 | 6.49 | 21.0 | 31.5 | 14 | 34 | 10 |
| intent_plan_misalignment | tau_retail | 25.5 | 24.0 | 7.62 | 20.0 | 31.5 | 17 | 37 | 8 |
| misinterpretation_of_tool_output | tau_retail | 24.5 | 18.0 | 18.45 | 10.0 | 38.0 | 7 | 57 | 8 |
| instruction_adherence_failure | tau_retail | 20.33 | 20.0 | 15.78 | 7.0 | 31.5 | 3 | 41 | 6 |
| invalid_invocation | tau_retail | 37.0 | 35.0 | 21.42 | 20.0 | 52.0 | 17 | 61 | 4 |
| intent_not_supported | tau_retail | 31.0 | 31.0 | 16.97 | 25.0 | 37.0 | 19 | 43 | 2 |
| system_failure | tau_retail | 26.0 | 26.0 | 0.0 | 26.0 | 26.0 | 26 | 26 | 1 |
| unclassified | who_and_when | 5.25 | 4.0 | 6.46 | 1.0 | 6.0 | 0 | 32 | 85 |
| code_error | who_and_when | 2.67 | 1.0 | 3.28 | 1.0 | 3.0 | 0 | 14 | 30 |
| tool_web_failure | who_and_when | 10.88 | 8.0 | 9.25 | 5.75 | 12.0 | 3 | 39 | 26 |
| orchestration_failure | who_and_when | 20.18 | 12.0 | 22.01 | 4.0 | 25.0 | 1 | 82 | 17 |
| resource_abuse | who_and_when | 4.11 | 2.0 | 5.49 | 1.0 | 5.0 | 0 | 18 | 9 |
| hallucination | who_and_when | 3.88 | 4.0 | 2.03 | 3.25 | 5.0 | 1 | 7 | 8 |
| factual_error | who_and_when | 11.33 | 4.0 | 19.64 | 1.5 | 7.25 | 0 | 51 | 6 |
| misinterpretation | who_and_when | 3.0 | 3.0 | 1.0 | 2.5 | 3.5 | 2 | 4 | 3 |

## 5. Выводы

### Категории с достаточным числом данных (n ≥ 20):

| category | source | n_trajectories_with_error |
|---|---|---|
| instruction_adherence_failure | magentic_one | 25 |
| guardrails_triggered | magentic_one | 23 |
| unclassified | who_and_when | 74 |
| code_error | who_and_when | 30 |
| tool_web_failure | who_and_when | 25 |

### Категории с недостаточным числом данных (n < 20):

| category | source | n_trajectories_with_error |
|---|---|---|
| misinterpretation_of_tool_output | magentic_one | 17 |
| intent_not_supported | magentic_one | 5 |
| intent_plan_misalignment | magentic_one | 7 |
| invention_of_new_information | magentic_one | 5 |
| invalid_invocation | magentic_one | 1 |
| system_failure | magentic_one | 1 |
| underspecified_user_intent | tau_retail | 10 |
| intent_plan_misalignment | tau_retail | 8 |
| misinterpretation_of_tool_output | tau_retail | 7 |
| instruction_adherence_failure | tau_retail | 6 |
| invalid_invocation | tau_retail | 2 |
| intent_not_supported | tau_retail | 2 |
| system_failure | tau_retail | 1 |
| orchestration_failure | who_and_when | 17 |
| resource_abuse | who_and_when | 9 |
| hallucination | who_and_when | 8 |
| factual_error | who_and_when | 6 |
| misinterpretation | who_and_when | 3 |

### Рекомендации:

- Для ТЗ №3/4 использовать: `instruction_adherence_failure`, `guardrails_triggered`, `unclassified`, `code_error`, `tool_web_failure`
- Who&When: 46.2% записей не классифицировано — рекомендуется расширить keyword-правила или добавить ручную разметку
- AgentRx: `instruction_adherence_failure` доминирует (>60% failures в magentic_one) — основной источник для статистики по этой категории