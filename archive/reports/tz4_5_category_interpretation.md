# ТЗ №4.5 — Интерпретация категорий keyword search

Что реально находит каждая категория в текстах траекторий, на основе анализа топ-5 примеров.

---

## tool_timeout

**Что ищем:** `timeout`, `timed out`, `deadline exceeded`, `request timeout`, `operation timed`

**Что реально находится:**

- **ITBench (точно):** команды завершились по таймауту — `command timed out after 10152 milliseconds`, exit_code=124. Это настоящие инфраструктурные таймауты shell-команд.
- **Nebius/SWE-Gym (смешанно):** в основном `timeout` встречается в именах тестовых файлов (`test_timeout.py`), в параметрах конфигурации (`grpc_connect_timeout`, `connection_timeout`), и в комментариях к коду. Реальных таймаутов выполнения мало.
- **TerminalBench (смешанно):** есть реальные таймауты установки пакетов (`apt install timed out`), но также упоминания в рассуждениях агента (`Let me add a timeout`).

**Вывод:** для ITBench — надёжный сигнал. Для nebius/SWE-Gym — сильно завышено из-за кода с параметрами timeout.

---

## tool_web_failure

**Что ищем:** `404`, `403`, `500`, `502`, `503`, `connection refused`, `connection error`, `network error`, `failed to connect`, `no route to host`, `name resolution failed`, `dns`

**Что реально находится:**

- **Nebius (точно):** реальные HTTP-ошибки при вызове внешних API — `HTTPError: 403 Client Error: Forbidden for url: https://api.memset.com/...`. Агент пытается обратиться к внешнему сервису и получает отказ.
- **SWE-Gym (ложные срабатывания):** числа `403`, `404`, `500` встречаются как номера строк кода (`line 403`, `line 500`), имена методов, константы. Реальных сетевых ошибок мало.
- **ITBench (точно):** задачи SRE явно описывают HTTP 500 как симптом инцидента — `tend to return http 500`. Это описание проблемы, которую агент должен диагностировать.
- **TerminalBench (ложные срабатывания):** числа `500`, `5000` встречаются как размеры выборок (`5000 samples`), не как HTTP-коды.

**Вывод:** для nebius и ITBench — надёжный сигнал. Для SWE-Gym и TerminalBench — сильно завышено из-за числовых совпадений.

---

## resource_not_found

**Что ищем:** `filenotfounderror`, `no such file`, `not found`, `does not exist`, `cannot find`, `path does not exist`

**Что реально находится:**

- **Nebius (точно):** реальные ошибки файловой системы в ответах среды — `Directory src not found`, `lexicon/__main__.py not found`. Агент пытается открыть файл/директорию, которой нет.
- **SWE-Gym (смешанно):** есть реальные ошибки (`does not exist. Please provide a valid path`), но также `not found` в комментариях к коду (`# If record does not exist, do nothing`), в docstring (`None if member was not found`).
- **ITBench (точно):** реальные ошибки — `No such file or directory`, `column 'alertname' not found`. Агент не может найти файл или поле в данных.
- **TerminalBench (смешанно):** реальные ошибки (`R not found`, `sudo is not found`) вперемешку с рассуждениями агента (`R not found yet, checking apt status`).

**Вывод:** наиболее надёжная категория для nebius и ITBench. Для SWE-Gym умеренная точность.

---

## permission_error

**Что ищем:** `permission denied`, `access denied`, `permissionerror`, `not permitted`, `operation not permitted`

**Что реально находится:**

- **Nebius (ложные срабатывания):** примеры — это строки исходного кода с обработкой ошибок: `print("ERROR: Permission denied when reading file...")`. Агент читает код, который обрабатывает PermissionError, а не сам получает эту ошибку.
- **SWE-Gym (смешанно):** есть реальные ошибки (`except PermissionError as e`, `S3 error: Access Denied`), но также `not permitted as a Field keyword argument` — это ошибка валидации Pydantic, не файловая система.
- **TerminalBench (точно):** реальные ошибки прав доступа — `permission denied, so I need to use sudo`, `Permission denied error. The script does not have execute permissions`, `Access denied on FTP server`.
- **ITBench:** единичные случаи, `permission denied` в контексте проверки директорий.

**Вывод:** для TerminalBench — надёжный сигнал. Для nebius — сильно завышено (код с обработкой ошибок). Для SWE-Gym — умеренная точность.

---

## memory_error

**Что ищем:** `out of memory`, `oom`, `memoryerror`, `memory error`, `killed`, `cannot allocate`

**Что реально находится:**

- **Nebius (ложные срабатывания):** примеры — `TooManyExpressionsInStarredAssignment` (это Python AST-ошибка, не память), `CheckpointKilledError` (это DVC-исключение, не OOM). Слово `killed` срабатывает на имена исключений в коде.
- **SWE-Gym (ложные срабатывания):** `TooManyUnions`, `TooManyTags`, `CheckpointKilledError` — имена классов исключений в коде, не реальные ошибки памяти.
- **TerminalBench (точно):** реальные OOM — `OOM killed. Let me use a pure numpy/scipy approach`, `algorithm is being OOM killed`, `process was killed, likely due to high computation`. Агент реально сталкивается с нехваткой памяти.
- **ITBench (нет примеров в топ-5):** 100% траекторий — вероятно, слово `memory` встречается в описаниях задач или метриках.

**Вывод:** для TerminalBench — надёжный сигнал (реальные OOM). Для nebius и SWE-Gym — сильно завышено (имена классов исключений). ITBench требует ручной проверки.

---

## code_execution_error

**Что ищем:** `traceback (most recent call last)`, `syntaxerror`, `nameerror`, `typeerror`, `valueerror`, `indexerror`, `keyerror`, `attributeerror`, `importerror`, `modulenotfounderror`

**Что реально находится:**

- **Nebius (завышено, но реально):** реальные Python traceback при запуске тестов — `Traceback (most recent call last): File "/usr/local/bin/lexicon"`. Это настоящие ошибки выполнения, но они часть SWE-задачи (агент должен их исправить), а не инфраструктурный сбой.
- **SWE-Gym (смешанно):** `TypeError`, `ImportError` встречаются как в реальных traceback, так и в исходном коде (`raise TypeError(...)`, `except ImportError`).
- **TerminalBench (точно для инфраструктуры):** `ModuleNotFoundError: No module named 'pyro'` — реальная ошибка отсутствия зависимости в среде выполнения. `ImportError` при установке пакетов. Это инфраструктурные проблемы окружения.
- **ITBench:** единичные случаи.

**Вывод:** категория принципиально неоднородна. Для nebius/SWE-Gym — это ошибки в коде задачи (не инфраструктура). Для TerminalBench — частично инфраструктурные (отсутствие модулей в среде). Использовать с осторожностью.

---

## tool_execution_error

**Что ищем:** `command not found`, `no such command`, `bash: `, `sh: `, `error:`, `failed:`, `exception:`

**Что реально находится:**

- **Nebius (ложные срабатывания):** `TypeError: string indices must be integers` — это Python-исключение в тексте GitHub issue (описание бага), не ошибка выполнения команды. Ключевое слово `error:` срабатывает на любой текст с двоеточием после слова error.
- **SWE-Gym (смешанно):** `ERROR: The view_range parameter is not allowed` — это ошибка инструмента редактора файлов (реальная ошибка вызова инструмента агентом). Но `error:` также срабатывает на код.
- **TerminalBench (смешанно):** `CancelledError: CancelledError()` — это Python asyncio исключение, не bash-ошибка. Но `command not found` для bash — реальный сигнал.
- **ITBench:** нет примеров в топ-5 для этой категории.

**Вывод:** самая ненадёжная категория. Ключевые слова `error:`, `failed:`, `exception:` слишком широкие — срабатывают на любой текст с этими словами. Только `command not found`, `bash: `, `sh: ` дают надёжный сигнал.

---

## Итоговая матрица надёжности

| Категория | nebius | swegym | terminalbench | itbench |
|---|---|---|---|---|
| tool_timeout | низкая | низкая | средняя | высокая |
| tool_web_failure | высокая | низкая | низкая | высокая |
| resource_not_found | высокая | средняя | средняя | высокая |
| permission_error | низкая | средняя | высокая | средняя |
| memory_error | низкая | низкая | высокая | неизвестно |
| code_execution_error | средняя* | средняя* | средняя | средняя |
| tool_execution_error | низкая | средняя | низкая | неизвестно |

*\* Для nebius/SWE-Gym: реальные ошибки выполнения кода, но это часть задачи (SWE-benchmark), а не инфраструктурный сбой.*

---

## Рекомендации для fault injection

Категории, пригодные для оценки P_err в симуляторе (высокая надёжность):

| Категория | Лучший источник | Интерпретация для симулятора |
|---|---|---|
| tool_timeout | ITBench, TerminalBench | Таймаут вызова внешнего инструмента/команды |
| tool_web_failure | nebius, ITBench | HTTP-ошибка при обращении к внешнему API |
| resource_not_found | nebius, ITBench | Файл/ресурс не найден в среде выполнения |
| permission_error | TerminalBench | Отказ в доступе к файлу/директории |
| memory_error | TerminalBench | OOM при выполнении вычислительной задачи |
