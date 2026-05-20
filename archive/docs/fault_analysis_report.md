# Fault Analysis Report
**Проект:** Симулятор динамической доступности LLM-инфраструктуры
**Заказчик:** Huawei (СПбГУ × Huawei Joint Lab)
**Дата:** 2026-05-06
**Версия:** final (ТЗ №4.8, TRAIL + Who&When HC)

---

## 1. Executive Summary

Исследование посвящено классификации и статистическому анализу ошибок агентных траекторий — реальных мультишаговых выполнений LLM-агентов с tool-calling. Цель — извлечь реалистичные параметры для fault injection в симулятор динамической доступности (Dynamic Availability, DA): вероятности появления ошибок и распределения момента их возникновения.

**Ключевые находки:**
- TRAIL — наиболее качественный источник: 143 траектории, 836 ошибок, экспертная разметка. Лучшие данные для моделирования (data_quality = high).
- Наиболее частые ошибки в TRAIL: orchestration_failure (64% траекторий), hallucination (58%), instruction_adherence_failure (54%), code_error (52%).
- 12 из 20 уникальных типов ошибок относятся к Категории 1 (моделирование невозможно без перезапуска LLM).
- Для 4 типов ошибок подтверждено статистическое распределение с p-value KS-теста > 0.3.
- Keyword search по 3 крупным датасетам (nebius/SWE-agent, ITBench, terminalbench) даёт дополнительную статистику на десятки тысяч траекторий.

---

## 2. Методология

### 2.1 Источники данных

| Источник | Формат | Траекторий | Ошибок | Типизация | Качество |
|---|---|---|---|---|---|
| TRAIL (GAIA + SWE-bench Lite) | JSON | 148 | 836 | Экспертная | high |
| AgentRx / magentic_one | JSONL | 44 | ~50 | Аннотированная | medium |
| AgentRx / tau_retail | JSONL | 29 | ~25 | Аннотированная | medium |
| Who&When Hand-Crafted | Parquet | 58 | 46 | Частичная | medium |
| nebius/SWE-agent | Parquet | 80 036 | 33 565 + 26 379 | Keyword | high |
| ibm-research/ITBench | JSONL | 105 | 80 | Keyword | high |
| yoonholee/terminalbench | Parquet | 52 104 | 1 750 + 267 | Keyword | medium |

### 2.2 Обработка Who&When

Who&When имел 184 записи из двух сплитов:
- **Algorithm-Generated** (126): синтетические — **исключены**
- **Hand-Crafted** (58): реальные — **использованы**

Ошибка в предыдущих версиях: все 184 записи ошибочно включались в анализ. Исправлено.

### 2.3 Обработка TRAIL

TRAIL ошибочно исключался в предыдущих версиях как «синтетический». Исправлено: возвращён как источник экспертной разметки (148 трейсов, GAIA + SWE-bench Lite). TRAIL — единственный источник с полной пошаговой экспертной разметкой.

### 2.4 Метрики

- **P(traj)** — доля траекторий с хотя бы одним вхождением ошибки
- **P(msg)** — доля сообщений/шагов с вхождением ошибки среди всех шагов
- **Wilson 95% CI** — доверительный интервал для обеих вероятностей
- **insufficient_data** — флаг при n < 20 траекторий с ошибкой

### 2.5 Подгонка распределений

Для ошибок с n ≥ 20 в TRAIL подгонялись 8 распределений (Exponential, Weibull, LogNorm, Beta, Uniform, Pareto, Gamma, Lomax) по абсолютному номеру шага. Оценка MLE + KS-тест. Распределение считается подтверждённым при p-value > 0.3.

---

## 3. Таксономия ошибок

### 3.1 Полный список (20 уникальных error_id)

| error_id | name_ru | Источники |
|---|---|---|
| hallucination | Галлюцинация | TRAIL, Who&When HC |
| instruction_adherence_failure | Несоблюдение инструкций | TRAIL, AgentRx |
| intent_not_supported | Неподдерживаемое намерение | AgentRx |
| intent_plan_misalignment | Несоответствие намерения и плана | AgentRx |
| invention_of_new_information | Изобретение информации | AgentRx |
| underspecified_user_intent | Недоопределённое намерение | AgentRx |
| factual_error | Фактическая ошибка | Who&When HC |
| kv_cache_loss | Потеря KV-кэша | TRAIL |
| code_error | Ошибка в коде | TRAIL, Who&When HC |
| invalid_invocation | Некорректный вызов инструмента | TRAIL, AgentRx |
| misinterpretation_of_tool_output | Неверная интерпретация результата | TRAIL, AgentRx |
| orchestration_failure | Сбой оркестрации | TRAIL, Who&When HC |
| resource_abuse | Избыточное потребление ресурсов | TRAIL, Who&When HC |
| resource_not_found | Ресурс не найден | TRAIL, keyword (nebius) |
| system_failure | Системный сбой | TRAIL, AgentRx |
| tool_timeout | Таймаут вызова инструмента | TRAIL, keyword (ITBench) |
| tool_web_failure | Сбой доступа к веб-ресурсу | TRAIL, Who&When HC, keyword (nebius) |
| guardrails_triggered | Срабатывание защитных ограничений | AgentRx |
| memory_error | Ошибка памяти (OOM) | keyword (terminalbench) |
| permission_error | Ошибка доступа | keyword (terminalbench) |

### 3.2 Описания

**hallucination** — Агент выдумал факты, данные или ссылки. Нет подтверждения в источниках. Пример: агент цитирует несуществующий документ или делает ложное утверждение о версии API.

**instruction_adherence_failure** — Агент не выполнил инструкцию оркестратора или пользователя. Не полностью прочитал задачу, пропустил ограничение, выполнил лишнее действие.

**intent_not_supported** — Агент не способен выполнить запрошенное действие. Задача за пределами возможностей модели или tooling.

**intent_plan_misalignment** — Агент составил план, не соответствующий задаче. Ошибка планирования: декомпозиция неверна или приоритеты расставлены неправильно.

**invention_of_new_information** — Агент выдумал данные, которых не было в источниках. Отличается от hallucination тем, что не может быть проверено (в hallucination данные доступны, но неверно интерпретированы).

**underspecified_user_intent** — Запрос пользователя слишком неточен для выполнения. Агент не может уточнить или делает неверные предположения.

**factual_error** — Агент использовал неверные факты из своих знаний (парадигматическая ошибка LLM, не зависящая от retrieval).

**kv_cache_loss** — Потеря кэша ключей-значений после перезапуска модуля или вытеснения из памяти GPU. Контекст теряется, агент начинает «забывать» результаты предыдущих шагов.

**code_error** — Агент сгенерировал синтаксически или логически неверный код. Линт-ошибки, Runtime exceptions, неправильный shell-синтаксис.

**invalid_invocation** — Агент вызвал инструмент с неверными параметрами: несуществующий tool_name, неправильные аргументы, вызов в неправильном контексте.

**misinterpretation_of_tool_output** — Агент неправильно понял вывод инструмента. Текст ответа API или результат shell-команды интерпретирован неверно.

**orchestration_failure** — Неверная маршрутизация задачи, ошибочное решение о следующем шаге. Агент выбрал не тот инструмент, неверный порядок действий, или продолжает после того как задача уже решена.

**resource_abuse** — Исчерпание лимита шагов, зацикливание агента, чрезмерное потребление ресурсов. Агент повторяет одно и то же действие или генерирует слишком длинный контекст.

**resource_not_found** — Файл, директория или запрашиваемый ресурс не существует в среде выполнения. Путь указан неверно или файл был удалён/перемещён.

**system_failure** — Критический сбой инфраструктуры выполнения. Среда или API не отвечают, segfault, kernel panic.

**tool_timeout** — Внешний инструмент или shell-команда не ответили за отведённое время. Сеть медленная, сервис перегружен.

**tool_web_failure** — HTTP-ошибка при обращении к внешнему API или веб-сервису. Rate limiting (429), Auth error (401/403), server error (5xx).

**guardrails_triggered** — Внешний сервис заблокировал запрос агента. Safety filter, content moderation, policy violation.

**memory_error** — Нехватка оперативной памяти при выполнении вычислительной задачи. OOM killer, swap thrashing.

**permission_error** — Отказ в доступе к файлу, директории или сервису из-за недостаточных прав. chmod, chown, sudo required.

---

## 4. Категории моделирования

### Категория 1: Невозможно моделировать
Требуется полный прогон весов языковой модели. Даже при наличии статистики — воспроизвести эффект в симуляторе невозможно без запуска реального LLM.

| error_id | reason |
|---|---|
| hallucination | Ошибка в «мышлении» модели — определяется внутренним состоянием |
| factual_error | Парадигматическая ошибка знаний модели |
| invention_of_new_information | Модель генерирует убедительно выглядящую, но неверифицируемую информацию |
| instruction_adherence_failure | Ошибка понимания/следования инструкциям — требует оценки семантики |
| intent_not_supported | Оценка возможностей модели — без запуска не определить |
| intent_plan_misalignment | Ошибка планирования — зависит от способности модели к декомпозиции |
| underspecified_user_intent | Ошибка интерпретации пользовательского запроса — требует семантики |

**7 ошибок. Нельзя моделировать статистически в текущем симуляторе.**

### Категория 2: Моделируется напрямую
Симулятор воспроизводит без статистических допущений — через изменение структуры IR-графа или параметров блоков.

| error_id | reason |
|---|---|
| kv_cache_loss | Известен механизм: вытеснение из памяти GPU, сброс контекста. Моделируется как удаление состояния блока. |

**1 ошибка. Подтверждено статистикой из TRAIL (n=44, gamma, p=0.94).**

### Категория 3: Моделируется статистически
Нельзя воспроизвести напрямую, но можно описать вероятностно: оценить частоту, подобрать распределение, генерировать события.

| error_id | source | n | distribution | ks_p |
|---|---|---|---|---|
| code_error | TRAIL | 74 | beta | 0.67 |
| resource_abuse | TRAIL | 45 | beta | 0.84 |
| kv_cache_loss | TRAIL | 44 | gamma | 0.94 |
| misinterpretation_of_tool_output | TRAIL | 40 | beta | 0.49 |
| guardrails_triggered | magentic_one | 23 | lognorm | 0.99 |
| misinterpretation_of_tool_output | magentic_one | 17 | gamma | 0.74 |
| tool_web_failure | who_and_when_hc | 23 | lognorm | 0.98 |
| tool_web_failure | nebius (keyword) | 26379 | — | — |
| resource_not_found | nebius (keyword) | 33565 | — | — |
| tool_timeout | ITBench (keyword) | 80 | — | — |
| memory_error | terminalbench (keyword) | 1750 | — | — |
| permission_error | terminalbench (keyword) | 267 | — | — |
| orchestration_failure | TRAIL | 92 | exponential (отклонён) | 0.00 |
| code_error | Who&When HC | 11 | insufficient | — |
| resource_abuse | Who&When HC | 5 | insufficient | — |
| orchestration_failure | Who&When HC | 16 | insufficient | — |
| invalid_invocation | TRAIL | 10 | insufficient | — |
| system_failure | TRAIL | 2 | insufficient | — |
| tool_timeout | TRAIL | 2 | insufficient | — |
| tool_web_failure | TRAIL | 5 | insufficient | — |
| resource_not_found | TRAIL | 4 | insufficient | — |

**21 запись (12 уникальных ошибок). Рекомендуется использовать подтверждённые распределения для fault injection.**

### Категория 4: Нецелесообразно
Технически реализуемо, но не имеет смысла в рамках проекта.

*Нет.*

---

## 5. Статистика по источникам

### 5.1 TRAIL (GAIA + SWE-bench Lite, 2024)
**143 траектории, 836 ошибок, 4 544 шагов**

| error_id | p(traj) | 95% CI | p(msg) | n errors | confirmed distribution |
|---|---|---|---|---|---|
| orchestration_failure | 0.643 | [0.562, 0.717] | 0.0409 | 185 | exponential (отклонён) |
| hallucination | 0.580 | [0.498, 0.658] | 0.0231 | 105 | lognorm (p=0.001) |
| instruction_adherence_failure | 0.538 | [0.457, 0.618] | 0.0341 | 154 | gamma (p=0.002) |
| code_error | 0.517 | [0.436, 0.598] | 0.0434 | 197 | **beta (p=0.67)** ✓ |
| resource_abuse | 0.315 | [0.244, 0.395] | 0.0132 | 60 | **beta (p=0.84)** ✓ |
| kv_cache_loss | 0.308 | [0.238, 0.388] | 0.0108 | 49 | **gamma (p=0.94)** ✓ |
| misinterpretation_of_tool_output | 0.280 | [0.213, 0.358] | 0.0125 | 57 | **beta (p=0.49)** ✓ |
| invalid_invocation | 0.070 | [0.038, 0.124] | 0.0024 | 11 | insufficient |
| tool_web_failure | 0.035 | [0.015, 0.079] | 0.0011 | 5 | insufficient |
| resource_not_found | 0.028 | [0.011, 0.070] | 0.0015 | 7 | insufficient |
| system_failure | 0.014 | [0.004, 0.050] | 0.0004 | 2 | insufficient |
| tool_timeout | 0.014 | [0.004, 0.050] | 0.0004 | 2 | insufficient |

**Выводы:** Оркестрация и халлюцинации — доминирующие классы ошибок (свыше 50% траекторий). Ошибки в коде встречаются в ~50% траекторий. Наибольшая частота появления: code_error (p=0.043) и orchestration_failure (p=0.041).

### 5.2 AgentRx / magentic_one (44 траектории)

| error_id | p(traj) | 95% CI | confirmed distribution |
|---|---|---|---|
| instruction_adherence_failure | 0.568 | [0.422, 0.703] | weibull_min (p=0.34) |
| guardrails_triggered | 0.523 | [0.379, 0.662] | **lognorm (p=0.99)** ✓ |
| misinterpretation_of_tool_output | 0.386 | [0.257, 0.534] | **gamma (p=0.74)** ✓ |
| intent_plan_misalignment | 0.159 | [0.079, 0.294] | insufficient |
| intent_not_supported | 0.114 | [0.050, 0.240] | insufficient |
| invention_of_new_information | 0.114 | [0.050, 0.240] | insufficient |
| invalid_invocation | 0.023 | [0.004, 0.118] | insufficient |
| system_failure | 0.023 | [0.004, 0.118] | insufficient |

### 5.3 AgentRx / tau_retail (29 траекторий)

| error_id | p(traj) | 95% CI |
|---|---|---|
| underspecified_user_intent | 0.345 | [0.199, 0.527] |
| intent_plan_misalignment | 0.276 | [0.147, 0.457] |
| misinterpretation_of_tool_output | 0.241 | [0.122, 0.421] |
| instruction_adherence_failure | 0.207 | [0.098, 0.384] |
| intent_not_supported | 0.069 | [0.019, 0.220] |
| invalid_invocation | 0.069 | [0.019, 0.220] |
| system_failure | 0.035 | [0.006, 0.172] |

### 5.4 Who&When Hand-Crafted (46 траекторий с классифицированными ошибками)

| error_id | p(traj) | p(msg) | confirmed distribution |
|---|---|---|---|
| tool_web_failure | 0.500 | 0.010 | **lognorm (p=0.98)** ✓ |
| orchestration_failure | 0.348 | 0.0067 | insufficient |
| code_error | 0.239 | 0.0046 | insufficient |
| resource_abuse | 0.109 | 0.0021 | insufficient |
| factual_error | 0.087 | 0.0017 | insufficient |
| hallucination | 0.043 | 0.0008 | insufficient |

### 5.5 Keyword search (крупные датасеты)

| error_id | dataset | n_traj | n_total | p(traj) | p(msg) |
|---|---|---|---|---|---|
| tool_web_failure | nebius/SWE-agent | 26 379 | 80 036 | 0.330 | 0.0225 |
| resource_not_found | nebius/SWE-agent | 33 565 | 80 036 | 0.419 | 0.0497 |
| tool_timeout | ITBench | 80 | 105 | 0.762 | 0.0943 |
| memory_error | terminalbench | 1 750 | 52 104 | 0.034 | 0.0124 |
| permission_error | terminalbench | 267 | 52 104 | 0.005 | 0.0004 |

---

## 6. Параметры для fault injection

### 6.1 Подтверждённые распределения (для использования в симуляторе)

| error_id | distribution | params | n | mean step | median step | notes |
|---|---|---|---|---|---|---|
| kv_cache_loss | gamma | shape=2.87, loc=0, scale=12.03 | 44 | 34.5 | 32 | **Категория 2** |
| guardrails_triggered | lognorm | mean=0.89, loc=0, scale=28.10 | 23 | 40.2 | 27 | Категория 3 |
| tool_web_failure (WW) | lognorm | shape=0.98, loc=0, scale=0.24 | 23 | 11.3 | 8 | Категория 3 |
| misinterpretation (m1) | gamma | shape=3.22, loc=0, scale=4.52 | 17 | 14.6 | 11 | Категория 3 |
| resource_abuse | beta | a=1.12, b=0.77, loc=0.09, scale=0.82 | 45 | 27.5 | 22 | Категория 3 |
| code_error | beta | a=1.38, b=1.38, loc=0.12, scale=0.86 | 74 | 29.6 | 23 | Категория 3 |
| misinterpretation (trail) | beta | a=0.92, b=0.69, loc=0.11, scale=0.85 | 40 | 31.1 | 21 | Категория 3 |

### 6.2 Рекомендации по категориям

**Для Категории 2 (kv_cache_loss):**
- Реализовать как сброс состояния IR-блока при превышении порога памяти
- Распределение: gamma(shape=2.87, scale=12.03) — момент сброса
- Не требует статистической генерации: достаточно правила

**Для Категории 3 (остальные с подтверждённым распределением):**
- Использовать распределение для генерации момента ошибки
- P(traj) — задать как параметр блока (вероятность наступления в пределах сессии)
- Для больших датасетов (nebius, ITBench): использовать keyword p(traj) как upper bound

### 6.3 Недостаточно данных (insufficient)

Для 12 записей n < 20. Рекомендации:
- Использовать средние значения step_mean/step_median как точечную оценку
- P(traj) использовать как есть (без CI смысла при малом n)
- Не подгонять распределение

---

## 7. Ограничения и честные оговорки

1. **TRAIL** — единственный источник с экспертной разметкой, но домен ограничен: GAIA (вопросы-ответы) и SWE-bench (исправление багов). Поведение агентов в production-системах может отличаться.

2. **Who&When Hand-Crafted** — только 58 траекторий, много записей остаются «unclassified». Keyword matching недостаточно точен для полной классификации.

3. **AgentRx** — не имеет данных о total_steps, поэтому p_message = None для всех записей. P(traj) — единственная надёжная метрика.

4. **Keyword search** — подход по ключевым словам даёт высокую полноту, но низкую точность. Ошибка: resource_not_found по ключу "not found" может включать нерелевантные совпадения.

5. **7 ошибок в Категории 1** — моделировать в текущем симуляторе нельзя. Для полноты симуляции необходимо либо добавить прокси-модель оценки, либо исключить эти ошибки из моделирования.

---

## 8. Артефакты проекта

| Файл | Описание |
|---|---|
| `report/all_errors_final.csv` | Финальная таблица: 45 строк (38 эмпирических + 7 теоретических) |
| `data/stats_full_v2.csv` | Статистика всех источников |
| `data/distributions_v2.csv` | Подгонки распределений (136 строк) |
| `data/trail_errors_v2.csv` | TRAIL ошибки (836 шт.) |
| `data/who_and_when_handcrafted_classified.csv` | Who&When HC классификация |
| `docs/tz4_8_report.md` | ТЗ №4.8 — методологические исправления |
| `docs/tz4_distributions_report.md` | ТЗ №4 — подгонки распределений |
| `docs/fault_mode_analysis_and_classification_ru.html` | TRAIL таксономия (руководство по классификации) |
| `p1_fault_mode_distributions.ipynb` | Jupyter-ноутбук с анализом распределений |

---

## 9. Заключение

Исследование покрывает 20 типов ошибок агентов из 7 источников. 12 ошибок невозможно моделировать без перезапуска LLM (Категория 1). 1 ошибка (kv_cache_loss) моделируется напрямую через структуру IR-графа. 7+ типов ошибок статистически описаны и готовы для fault injection (Категория 3). Keyword search по крупным датасетам подтверждает высокие частоты tool_web_failure (~33%) и resource_not_found (~42%) в production-подобных условиях.

**Практическая рекомендация для симулятора DA:** реализовать fault injection для kv_cache_loss (Категория 2) как сброс состояния блока; для code_error, resource_abuse, tool_web_failure, misinterpretation_of_tool_output использовать подтверждённые статистические распределения. Ошибки Категории 1 игнорировать на первом этапе.
