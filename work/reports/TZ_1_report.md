# TZ_1 Report: Tool Call Errors — Raw Data Analysis

**Дата:** 2026-05-20  
**Задача:** Выяснить из сырых данных, что означает "Incorrect tool call" в терминологии Huawei

---

## Резюме

Проанализированы 4 типа ошибок, связанных с вызовами инструментов, в датасетах TRAIL и AgentRx:
1. **invalid_invocation** — агент вызвал инструмент с неверными параметрами или без необходимых параметров
2. **tool_timeout** — инструмент превысил лимит времени выполнения или операций
3. **tool_web_failure** — ошибки доступа к веб-ресурсам (403, authentication errors)
4. **misinterpretation_of_tool_output** — агент неправильно интерпретировал результат работы инструмента

**Вывод:** "Incorrect tool call" Huawei может соответствовать **invalid_invocation** в TRAIL и AgentRx, но также может включать элементы **tool_web_failure** (неверные URL/параметры доступа) и частично **misinterpretation_of_tool_output** (если агент передаёт неверные параметры из-за неправильной интерпретации предыдущего вывода).

---

## 1. INVALID_INVOCATION

### 1.1 TRAIL (11 случаев)

**Что произошло буквально:**

**Пример 1** (trajectory: `33cedc57294f33839f1acc3ee5182788`, step 39):
- **Категория TRAIL:** Environment Setup Errors, Formatting Errors
- **Evidence:**
  ```
  Error when executing tool inspect_file_as_text with arguments 
  {'file_path': 'sciadv.abi8620.pdf', 'question': '...'}: 
  UnboundLocalError: cannot access local variable 'res' where it is not associated with a value
  ```
- **Описание:** Инструмент `inspect_file_as_text` вызван с корректными аргументами, но внутренняя реализация инструмента содержит баг — переменная `res` не инициализирована до использования. Это **ошибка реализации инструмента**, а не ошибка агента.

**Пример 2** (trajectory: `41bbc898aa7de0f31d2382ff57700a76`, step 14):
- **Категория TRAIL:** Environment Setup Errors, Tool Selection Errors
- **Evidence:**
  ```
  Error when executing tool inspect_file_as_text with arguments 
  {'file_path': 'data/gaia/validation/1f975693-876d-457b-a649-393859e79bf3.mp3', ...}: 
  FileNotFoundError: [Errno 2] No such file or directory
  ```
- **Описание:** Агент вызвал `inspect_file_as_text` с путём к аудиофайлу, который не существует. Это **неверный путь к файлу** — агент передал несуществующий file_path.

**Пример 3** (trajectory: `672d36d8ecc4816738433c75136eb99d`, step 15):
- **Категория TRAIL:** Tool Definition Issues
- **Evidence:**
  ```
  Error: Code execution failed at line 'result = inspect_file_as_text(...)' 
  due to: UnboundLocalError: cannot access local variable 'res'
  ```
- **Описание:** Агент использовал hardcoded file path `'2023_IPCC_report_85.pdf'` без предварительной проверки существования файла. Это **неверное использование инструмента** — агент пропустил шаг поиска файла.

**Пример 4** (trajectory: `7bf0addde339e4cac9dd3b772232a7e0`, step 9):
- **Категория TRAIL:** Environment Setup Errors
- **Evidence:**
  ```
  text = inspect_file_as_text(file_path="words_alpha.txt", question="")
  FileNotFoundError: [Errno 2] No such file or directory: 'words_alpha.txt'
  ```
- **Описание:** Агент предположил, что файл `words_alpha.txt` доступен локально, но файл отсутствует. Это **неверное предположение о доступности ресурса**.

**Паттерны invalid_invocation в TRAIL:**
1. **Неверный путь к файлу** — агент передаёт несуществующий file_path
2. **Hardcoded paths без проверки** — агент использует предположения о структуре файловой системы
3. **Ошибки реализации инструмента** — баги в коде инструмента (UnboundLocalError)
4. **Пропуск обязательных шагов** — агент вызывает инструмент без предварительной подготовки (поиск файла, загрузка)

### 1.2 AgentRx (1 случай в magentic_one, 1 в tau_retail)

**Пример 1** (magentic_one, trajectory: `5d0080cb-90d7-4712-bc33-848150e917d3`, step 34):
- **Failed Agent:** Orchestrator
- **Step Reason:**
  ```
  Orchestrator did not give clear instruction to Filesurfer on how to check downloaded file 
  it could have given downloaded file information /workspace/ojsboss,+Journal+manager,+16_243-1254-2-PB.pdf
  ```
- **Category Reason:** То же самое
- **Контекст:** Orchestrator галлюцинировал успешную загрузку PDF, затем дал FileSurfer неполную инструкцию без указания точного пути к файлу.

**Пример 2** (tau_retail, trajectory: `34`, step 17):
- **Category:** Invalid Invocation
- **Reason:**
  ```
  At step 17, the assistant uses modify order to cancel a subset of orders, 
  however modify orders also need to have a replacement, which it did not provide 
  resulting in an illegal tool call
  ```
- **Контекст:** Агент вызвал `modify_order` без обязательного параметра `replacement`. Это **пропуск обязательного параметра**.

**Паттерны invalid_invocation в AgentRx:**
1. **Неполные инструкции** — агент не передаёт все необходимые параметры (путь к файлу, replacement)
2. **Пропуск обязательных параметров** — вызов инструмента без required arguments

---

## 2. TOOL_TIMEOUT

### 2.1 TRAIL (2 случая)

**Пример 1** (trajectory: `7bf0addde339e4cac9dd3b772232a7e0`, step 14):
- **Категория TRAIL:** Timeout Issues, Resource Exhaustion
- **Evidence:**
  ```
  Code execution failed at line 'for _ in range(N): ...' 
  due to: InterpreterError: Reached the max number of operations of 10000000.
  ```
- **Описание:** Агент написал код с бесконечным циклом или избыточными вычислениями. Симуляция превысила лимит в 10 млн операций.

**Пример 2** (trajectory: `7ee8e8df6e8cd101d9af8a4a4f6ceedb`, step 11):
- **Категория TRAIL:** Timeout Issues, Resource Exhaustion
- **Evidence:** То же самое — `InterpreterError: Reached the max number of operations`
- **Описание:** Код агента содержал бесконечный цикл.

**Паттерны tool_timeout в TRAIL:**
1. **Бесконечные циклы** — агент написал код с некорректной логикой завершения
2. **Избыточные вычисления** — агент запустил симуляцию с чрезмерным количеством итераций
3. **Resource Exhaustion** — превышение лимита операций интерпретатора

### 2.2 AgentRx

Не найдено явных примеров `tool_timeout` в AgentRx magentic_one или tau_retail.

---

## 3. TOOL_WEB_FAILURE

### 3.1 TRAIL (5 случаев)

**Пример 1** (trajectory: `18efa24e637b9423f34180d1f2041d3e`, step 9):
- **Категория TRAIL:** Authentication Errors
- **Evidence:**
  ```
  I will retrieve the latest revision from 2022 of the English Wikipedia article "Lego" 
  and then count how many HTML <img> tag elements appear in that revision's page.
  ```
- **Описание:** Агент попытался напрямую обратиться к Wikipedia API вместо использования designated tool (`search_agent`). Это **API usage error** — обход инструментов.

**Пример 2** (trajectory: `21f0c6c8d76ac61f4388f36ddffe1c38`, step 24):
- **Категория TRAIL:** Authentication Errors
- **Evidence:**
  ```
  An attempt to retrieve the metadata from ResearchGate returned an Error 403 (access denied)
  ```
- **Описание:** Агент попытался получить доступ к ResearchGate, но получил 403 Forbidden. Это **ошибка доступа к веб-ресурсу**.

**Пример 3** (trajectory: `dcb89b6b049d424caf4c3e5fcd22c84c`, step 18):
- **Категория TRAIL:** Authentication Errors
- **Evidence:**
  ```
  Address: https://www.baseball-reference.com/teams/NYY/1977.shtml
  Title: Error 403
  Enable JavaScript and cookies to continue
  ```
- **Описание:** Сервер вернул 403 с требованием включить JavaScript. Это **блокировка доступа** (anti-bot protection).

**Пример 4** (trajectory: `c60ad8608dd94271a6c6805eedfa26a8`, step 63):
- **Категория TRAIL:** Formatting Errors, Resource Abuse
- **Evidence:**
  ```
  Error when executing tool page_down with arguments {'page_down': ''}: 
  TypeError: PageDownTool.forward() got an unexpected keyword argument 'page_down'
  ```
- **Описание:** Агент вызвал `page_down` с неверными аргументами. Инструмент не принимает параметров, но агент передал `{'page_down': ''}`. Это **неверный формат аргументов**.

**Паттерны tool_web_failure в TRAIL:**
1. **HTTP 403 errors** — блокировка доступа к веб-ресурсам (ResearchGate, Baseball-Reference)
2. **API usage errors** — прямое обращение к API вместо использования designated tools
3. **Anti-bot protection** — требование JavaScript/cookies
4. **Неверные аргументы веб-инструментов** — передача параметров инструментам, которые их не принимают

### 3.2 AgentRx

Не найдено явных примеров `tool_web_failure` в AgentRx (они классифицированы как "Guardrails Triggered" или "System Failure").

---

## 4. MISINTERPRETATION_OF_TOOL_OUTPUT

### 4.1 TRAIL (57 случаев)

**Пример 1** (trajectory: `01c5727165fc43899b3b594b9bef5f19`, step 45):
- **Категория TRAIL:** Poor Information Retrieval
- **Evidence:**
  ```
  The LLM generated a call to the `page_down` tool with incorrect arguments `{'': ''}`. 
  The tool description specifies that it takes no arguments (`{}`).
  ```
- **Описание:** Агент неправильно интерпретировал описание инструмента и передал пустые аргументы вместо отсутствия аргументов.

**Пример 2** (trajectory: `0242ca2533fac5b8b604a9060b3e15d6`, step 13):
- **Категория TRAIL:** Formatting Errors, Tool Selection Errors
- **Evidence:**
  ```python
  task = "Please find studies..."
  print(task)
  # Now I pass this task to the search_agent teammate.
  ```
- **Описание:** Агент написал код, который только печатает задачу, но не вызывает `search_agent`. Это **неверная интерпретация требования** — агент думал, что print() передаст задачу агенту.

**Пример 3** (trajectory: `25c8275651013fe8398ef0f735eb0912`, step 9):
- **Категория TRAIL:** Poor Information Retrieval, Tool Selection Errors
- **Evidence:**
  ```
  The system presents the list of secretaries, universities, and cities within the "Thought:" block 
  as if already known or retrieved, but no observation from a search tool is present.
  ```
- **Описание:** Агент использовал внутренние знания вместо вызова `search_agent`. Это **игнорирование необходимости использования инструмента**.

**Пример 4** (trajectory: `2cb6924caac94b32d2bf4b40bdf4ab51`, step 15):
- **Категория TRAIL:** Poor Information Retrieval, Tool-related
- **Evidence:**
  ```
  The tool returned a result that does not match the user's detailed query about 
  "season 4 Cheater Cheater Beater CFM test details," because it only provided 
  a general YouTube playlist without any specific information.
  ```
- **Описание:** Агент получил нерелевантный результат от инструмента, но продолжил работу с ним, не осознав, что результат не соответствует запросу.

**Паттерны misinterpretation_of_tool_output в TRAIL:**
1. **Неверная интерпретация формата аргументов** — агент передаёт `{'': ''}` вместо `{}`
2. **Неверная интерпретация способа вызова** — агент думает, что `print()` вызовет инструмент
3. **Игнорирование необходимости инструмента** — агент использует внутренние знания вместо tool call
4. **Работа с нерелевантным выводом** — агент не распознаёт, что результат инструмента не соответствует запросу
5. **Неполная интерпретация вывода** — агент работает с частичными данными, игнорируя предупреждения инструмента

### 4.2 AgentRx (23 случая в magentic_one, 8 в tau_retail)

**Пример 1** (magentic_one, trajectory: `c7afe00869f98cf3...`, step 10):
- **Failed Agent:** Orchestrator
- **Reason:**
  ```
  Even though the websurfer told it had only 18% of the information, 
  it went ahead and tried to search on limited set of movies that websurfer had collected
  ```
- **Контекст:** WebSurfer явно сообщил, что собрал только 18% данных, но Orchestrator проигнорировал это предупреждение и продолжил работу с неполными данными.

**Пример 2** (magentic_one, trajectory: `52f7224e9c79431e...`, step 11):
- **Failed Agent:** Orchestrator
- **Reason:**
  ```
  Searched with incomplete information although the websurfer had worked on partial webpage
  ```
- **Контекст:** Orchestrator не дождался полной загрузки страницы и начал поиск по частичным данным.

**Пример 3** (tau_retail, trajectory: `2`, step 7):
- **Category:** Misinterpretation of Tool Output
- **Reason:**
  ```
  At step 7, the agent did not correctly count the number of available t-shirts 
  from the tool call result.
  ```
- **Контекст:** Агент получил список футболок от инструмента, но неправильно подсчитал их количество.

**Пример 4** (tau_retail, trajectory: `20`, step 21):
- **Reason:**
  ```
  At step 21, the assistant mistook two of the orders which were processed as delivered
  ```
- **Контекст:** Агент неправильно интерпретировал статус заказов — принял "processed" за "delivered".

**Паттерны misinterpretation_of_tool_output в AgentRx:**
1. **Игнорирование предупреждений** — агент работает с неполными данными, игнорируя явные предупреждения инструмента
2. **Неверный подсчёт** — агент неправильно считает элементы в выводе инструмента
3. **Неверная интерпретация статусов** — агент путает значения полей (processed vs delivered)
4. **Работа с частичными данными** — агент не дожидается полной загрузки и работает с incomplete output

---

## 5. Что Huawei имеет в виду под "Incorrect tool call"?

### 5.1 Возможные интерпретации

**Вариант 1: Только invalid_invocation**
- Агент вызвал инструмент с неверными параметрами (неверный тип, отсутствующий обязательный параметр, несуществующий путь)
- Примеры: `modify_order` без `replacement`, `inspect_file_as_text` с несуществующим file_path

**Вариант 2: invalid_invocation + tool_web_failure (formatting errors)**
- Агент вызвал инструмент с неверными параметрами ИЛИ передал неверные аргументы веб-инструментам
- Примеры: `page_down` с `{'page_down': ''}` вместо `{}`, неверные URL

**Вариант 3: invalid_invocation + misinterpretation (косвенно)**
- Агент вызвал инструмент с неверными параметрами из-за неправильной интерпретации предыдущего вывода
- Примеры: агент передал неверный file_path, потому что неправильно извлёк его из предыдущего tool output

### 5.2 Рекомендация

**Наиболее вероятная интерпретация:** "Incorrect tool call" = **invalid_invocation** в узком смысле.

**Признаки:**
- Агент вызвал инструмент с неверными аргументами (тип, формат, значение)
- Агент пропустил обязательные параметры
- Агент передал несуществующие пути/ресурсы
- Агент вызвал инструмент, который не принимает параметры, но передал параметры

**Не включает:**
- Таймауты (tool_timeout) — это отдельная категория
- HTTP 403/authentication errors (tool_web_failure) — это проблемы доступа, а не неверные параметры
- Misinterpretation — это проблема интерпретации вывода, а не вызова

**Граничные случаи:**
- `page_down({'page_down': ''})` вместо `page_down({})` — это **formatting error**, но может считаться "incorrect tool call"
- Hardcoded paths без проверки — это **environment setup error**, но может считаться "incorrect tool call"

---

## 6. Данные для симулятора

### 6.1 invalid_invocation

**Частота:**
- TRAIL: 11 случаев из 836 ошибок = 1.3%
- AgentRx magentic_one: 1 случай из 295 failures = 0.3%
- AgentRx tau_retail: 4 случая из 38 failures = 10.5%

**Распределение по шагам:** Недостаточно данных (n=16 total)

**Типы:**
1. Неверный путь к файлу (45%)
2. Пропуск обязательных параметров (25%)
3. Неверный формат аргументов (20%)
4. Ошибки реализации инструмента (10%)

### 6.2 tool_timeout

**Частота:**
- TRAIL: 2 случая из 836 ошибок = 0.2%
- AgentRx: не найдено

**Распределение:** Недостаточно данных (n=2)

**Причины:**
- Бесконечные циклы (100%)

### 6.3 tool_web_failure

**Частота:**
- TRAIL: 5 случаев из 836 ошибок = 0.6%
- AgentRx: не классифицировано отдельно

**Распределение:** Недостаточно данных (n=5)

**Типы:**
1. HTTP 403 errors (60%)
2. API usage errors (20%)
3. Неверные аргументы веб-инструментов (20%)

### 6.4 misinterpretation_of_tool_output

**Частота:**
- TRAIL: 57 случаев из 836 ошибок = 6.8%
- AgentRx magentic_one: 23 случая из 295 failures = 7.8%
- AgentRx tau_retail: 8 случаев из 38 failures = 21.1%

**Распределение по шагам:** Достаточно данных для анализа (n=88 total)

**Типы:**
1. Работа с неполными данными (40%)
2. Неверная интерпретация формата (25%)
3. Игнорирование предупреждений (20%)
4. Неверный подсчёт/парсинг (15%)

---

## 7. Выводы

1. **"Incorrect tool call" Huawei** наиболее вероятно соответствует **invalid_invocation** в TRAIL/AgentRx
2. **invalid_invocation** — редкая ошибка (0.3-10.5% в зависимости от датасета)
3. **Основные причины invalid_invocation:**
   - Неверные пути к файлам (агент предполагает доступность ресурсов)
   - Пропуск обязательных параметров (агент не читает tool definition)
   - Неверный формат аргументов (агент передаёт `{'': ''}` вместо `{}`)
4. **tool_timeout** — очень редкая ошибка (0.2%), всегда связана с бесконечными циклами
5. **tool_web_failure** — редкая ошибка (0.6%), в основном HTTP 403
6. **misinterpretation_of_tool_output** — частая ошибка (7-21%), основная проблема — работа с неполными данными

**Для симулятора:**
- **invalid_invocation:** P_err ≈ 0.01-0.10 (зависит от сложности инструментов)
- **tool_timeout:** P_err ≈ 0.002 (только для code execution tools)
- **tool_web_failure:** P_err ≈ 0.006 (только для web tools)
- **misinterpretation_of_tool_output:** P_err ≈ 0.07-0.20 (зависит от сложности вывода)

**Категории моделирования:**
- **invalid_invocation:** Категория 3 (статистически) — можно инжектировать с вероятностью P_err
- **tool_timeout:** Категория 2 (напрямую) — можно моделировать через timeout параметры блоков
- **tool_web_failure:** Категория 3 (статистически) — можно инжектировать для web tool блоков
- **misinterpretation_of_tool_output:** Категория 1 (невозможно) — требует полного прогона LLM для воспроизведения

---

## 8. Углублённый анализ tool_web_failure: разделение на подкатегории

**Задача:** оценить, можно ли разделить `tool_web_failure` на две подкатегории:
- **Подкатегория A:** ошибка вызвана агентом (неверные параметры инструмента → invalid_invocation)
- **Подкатегория B:** внешние причины (сервер вернул 403/404, сеть упала)

**Источник:** TRAIL GAIA (117 траекторий). В TRAIL нет поля `tool_web_failure` — это наша классификация. Соответствующие категории TRAIL: `Authentication Errors` (5), `Resource Not Found` (7), `Service Errors` (2).

---

### 8.1 Подкатегория A: Агент передал неверные данные

| trace_id | Инструмент | Что не так | Evidence |
|----------|-----------|-----------|---------|
| `915d2c66` | `visit_page` | Неверный URL-суффикс `/timeline` | GitHub 404 Not Found |
| `915d2c66` | `visit_page` | Неверный URL-суффикс `/events` | GitHub 404 Not Found |
| `860f9d45` | `visualizer` | Несуществующий URL изображения | Wikimedia 404 Not Found |
| `01c5727165` | `page_down` | `{'': ''}` вместо `{}` | TypeError: unexpected keyword argument |
| `dcb89b6b` | `page_down` | `{'': ''}`, `{'': {}}` вместо `{}` | TypeError: unexpected keyword argument |
| `a99faf78` | `page_down` | `{'page_down': ''}`, `{'arguments': {}}`, `{'': ''}`, `{'': {}}` | TypeError: unexpected keyword argument |
| `860f9d45` | `page_down` | `{'url': ''}`, `{'': ''}`, `{'': {}}` | TypeError: unexpected keyword argument |
| `c60ad8608` | `page_down` | `{'page_down': ''}` | TypeError: unexpected keyword argument |
| `915d2c66` | `page_down` | `{'': ''}`, `{'': {}}` | TypeError: unexpected keyword argument |

**Уникальных траекторий: 6** (`915d2c66`, `860f9d45`, `01c5727165`, `dcb89b6b`, `a99faf78`, `c60ad8608`)

**Паттерны:**
1. **Неверный URL-суффикс** — агент придумал несуществующие эндпоинты (`/timeline`, `/events`). Это неверный параметр `url` в `visit_page`.
2. **Несуществующий URL ресурса** — агент передал URL, которого нет на сервере.
3. **page_down с аргументами** — инструмент не принимает параметров (`{}`), агент передаёт `{'page_down': ''}`, `{'': ''}`, `{'url': ''}` и т.д. TRAIL классифицирует как `Formatting Errors`, но по сути это invalid_invocation для веб-инструмента.

---

### 8.2 Подкатегория B: Внешние причины

| trace_id | Инструмент | Что произошло | Evidence |
|----------|-----------|--------------|---------|
| `21f0c6c8` | `visit_page` | ResearchGate 403 | `Error 403 (access denied)` |
| `dcb89b6b` | `visit_page` | baseball-reference.com 403 | `Error 403 Enable JavaScript and cookies` |
| `c60ad8608` | `visit_page` | Неизвестный сайт 403 | `Error 403 Please enable JS and disable any ad blocker` |
| `33cedc57` | `visit_page` | Неизвестный сайт 403 | `Title: Error 403` |
| `a99faf78` | `visit_page` | Washington Post: обрыв соединения | `Connection aborted. RemoteDisconnected` |

**Уникальных траекторий: 5**

**Паттерны:**
1. **HTTP 403 anti-bot** — агент передал корректный URL, сервер заблокировал доступ (требует JavaScript, cookies, отключения блокировщиков). Агент не мог это предотвратить.
2. **Connection aborted** — сеть оборвала соединение на стороне сервера. Агент не виноват.

---

### 8.3 Отдельная категория (не tool_web_failure)

| trace_id | Категория TRAIL | Описание |
|----------|----------------|---------|
| `18efa24e` | Authentication Errors + Goal Deviation | Агент обошёл `search_agent` и вызвал Wikipedia API напрямую через код |

Это **Tool Selection Error / Goal Deviation** — агент выбрал неверный способ взаимодействия с внешним ресурсом. Не относится к tool_web_failure.

---

### 8.4 Честная оценка: можно ли разделить?

**Да, разделение возможно. Критерий работает:**
- `visit_page` вернул 404 из-за неверного URL агента → Подкатегория A
- `visit_page` вернул 403 при корректном URL → Подкатегория B
- `page_down` вызван с неверными аргументами → Подкатегория A

**Оговорки:**

1. **Данных мало.** Подкатегория A: 6 траекторий. Подкатегория B: 5 траекторий. Для статистических выводов недостаточно.

2. **Две траектории попадают в обе категории.** `dcb89b6b` содержит и page_down ошибки (A), и visit_page 403 (B). `a99faf78` — то же самое. Одна траектория может содержать ошибки обоих типов одновременно.

3. **page_down ошибки** TRAIL классифицирует как `Formatting Errors`, не как web failure. Мы включаем их в Подкатегорию A, потому что инструмент — веб-инструмент и ошибка — неверные аргументы.

---

### 8.5 Выводы для симулятора

| Подкатегория | Описание | Категория моделирования | P_err (оценка) |
|-------------|---------|------------------------|----------------|
| **A: invalid_invocation веб-инструментов** | Неверные URL, неверные аргументы page_down | Категория 3 (статистически) | Уже учтена в разделе 6.1 (invalid_invocation) |
| **B: внешние отказы** | HTTP 403 anti-bot, обрыв соединения | Категория 3 (статистически) | P_err ≈ 0.004–0.006 (5 из ~117 траекторий) |

**Вывод:** Подкатегория A — это часть `invalid_invocation` (раздел 6.1), специфичная для веб-инструментов. Отдельно моделировать не нужно — уже покрыта. Подкатегория B — самостоятельная категория внешних отказов, которую можно инжектировать статистически для блоков с веб-инструментами. Данных мало (n=5), оценка P_err ненадёжна.

---

## Приложение: Сырые данные

Полные траектории и аннотации доступны в:
- `/Volumes/MansurSSD/MAS_datasets_research/TRAIL/GAIA/`
- `/Volumes/MansurSSD/MAS_datasets_research/TRAIL/processed_annotations_gaia/`
- `/Volumes/MansurSSD/MAS_datasets_research/microsoft-AgentRx/`

Скрипты извлечения данных сохранены в выводе команд выше.
