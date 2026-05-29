# Методология FP-анализа категорий nebius_invalid_invocation

Дата: 2026-05-29
Контекст: FP-анализ 6 категорий ошибок в nebius/SWE-agent-trajectories

## Определения

**TP (True Positive):** pre-execution отказ. Валидатор отвергает вызов/edit/команду **до side-effect**. Файл не модифицируется, команда не выполняется, функция не запускается.

**FP (False Positive):** runtime ошибка внутри уже запущенного скрипта. Агент сгенерировал код (команду), который при выполнении падает с ошибкой.

**INVALID:** запись, которую парсер захватил ошибочно (не ошибка из этой категории).

## Критерий разграничения TP/FP

Ключевой вопрос: **в какой момент обнаруживается ошибка?**

| Критерий | TP (pre-execution) | FP (runtime) |
|----------|-------------------|---------------|
| **Момент** | До side-effect | После запуска |
| **Кто обнаруживает** | Валидатор инструмента | Интерпретатор/исполнитель |
| **Код применён?** | Нет | Да (для Edit), Да (для скриптов) |
| **Маркер Edit tool** | `"Your changes have NOT been applied"` или `"would have looked if applied"` | `"Traceback"` + путь к пользовательскому скрипту |
| **Маркер bash** | `/bin/bash: line N: COMMAND: command not found` (PATH lookup) | Runtime скрипт (не ловится парсером B) |

## Инструменты

**CLI:** `work/scripts/nebius_errors_cli.py`

```bash
.venv/bin/python work/scripts/nebius_errors_cli.py sample --category X --n 25 --seed 42
.venv/bin/python work/scripts/nebius_errors_cli.py show --instance-id ID --traj N --step M --context 1
```

**Обязательное чтение перед анализом:**
1. `work/docs/invalid_invocation_concept.md` — концепция и определения
2. `work/docs/структура_датасетов_ошибок.md` — структура JSON и парсера

## Пошаговый процесс для каждой категории

### Шаг 1: Выборка
```bash
.venv/bin/python work/scripts/nebius_errors_cli.py sample --category X --n 25 --seed 42
```
Другой seed = другая выборка (для верификации).

### Шаг 2: Предварительная классификация
Для каждого примера определить TP/FP по **timing-критерию**:

**Edit tool (E1, E2):**
- `"would have looked if applied"` → **TP** (edit отвергнут, файл не изменён)
- `"Traceback"` + применённый edit → **FP** (edit прошёл, код упал later)

**Bash (B):**
- `/bin/bash: line N: COMMAND: command not found` → **TP** (PATH lookup, pre-execution)
- Команда внутри скрипта → **FP** (парсер B не ловит такие, но могут встретиться)

**FileNotFoundError (A):**
- Агент вызвал `ls file` напрямую → **TP**
- Агент запустил скрипт, тот сделал `open('cat')` → **FP** (ключевой маркер: ошибка изнутри скрипта)

**TypeError (C):**
- ВСЕ — **FP** (парсер ловит ошибки из запущенных скриптов)
- Маркер: `"File .../reproduce.py"` в traceback

**missing arg (D):**
- `"Your changes have NOT been applied"` → **TP** (Edit tool отверг)
- `"Traceback"` + `File ".../reproduce.py"` + function call → **FP** (скрипт выполнился)
- Click CLI (`/opt/conda/envs/...`) → **FP** (subprocess started)

### Шаг 3: Углублённый анализ (по необходимости)
Если непонятно — смотреть предыдущий шаг:
```bash
.venv/bin/python work/scripts/nebius_errors_cli.py show --instance-id ID --traj N --step M --context 1
```
**Производительность:** show грузит parquet (~4 сек). Делать по 5 в параллельных Bash-вызовах, НЕ последовательно.

### Шаг 4: Финальный вердикт
**ВСЕ 25 должны получить вердикт.** Пограничные — TP/FP с обоснованием (1-2 предложения), НЕ выкидывать.

## Формат ответа субагента

Просто текст (без создания файлов):

```
[1] instance_id=X — TP/FP/INVALID. Обоснование (1-2 строки).
...
[25] ...

Сводный отчёт:
- TP: X/25, FP: Y/25, INVALID: Z/25
- FP rate: Z%
- Подтипы (доли, описания)
- 2-3 интересных примера: instance_id, текст ошибки, разбор
- Слепые пятна парсера
```

## Ожидаемые результаты по категориям

| Категория | Ожидаемый FP rate | Ключевой маркер TP | Ключевой маркер FP |
|----------|:-----------------:|-------------------|-------------------|
| A | ~4% | Агент вызвал ls/python напрямую | Traceback изнутри скрипта |
| B | 0% | PATH lookup | (не ловится парсером) |
| C | **100%** | Нет | Traceback, все — runtime |
| D | ~44% | "Your changes have NOT been applied" | Traceback + reproduce.py |
| E1 | 0% | "would have looked if applied" | (редко) |
| E2 | 0% | "would have looked if applied" | (редко) |

## Важные нюансы

### Edit tool и pre-execution
Edit tool запускает flake8 на предложенном коде **до применения**. Фраза `"would have looked if applied"` означает: edit отвергнут, файл НЕ изменён. Это pre-execution TP, даже если ошибка semantic (F821).

### Bash PATH lookup
Bash проверяет PATH **до** выполнения команды. `/bin/bash: line N: COMMAND: command not found` — это pre-execution PATH lookup, не runtime. Агент вызвал команду, которой нет в PATH — это TP.

### Парсер ловит markdown вместо bash (B)
Иногда парсер захватывает текст из `` ```submit ``` `` markdown-блоков рассуждения агента, не bash-ошибку. Ключевой признак: ошибка содержит "submit" или "edit" в контексте многострочного markdown. Это **INVALID**, не категория B.

### C — ловушка
Парсер C ловит TypeError из запущенных скриптов, а не отказы инструментов. Это **100% FP** — парсер заточен на ошибки кодогенерации, не invalid_invocation. C не является invalid_invocation.

### D — смесь
D смешивает Edit tool rejection (TP) и runtime script failures (FP) под одним паттерном `"missing ... required ... argument"`. Без контекста шага невозможно полностью исключить FP. Эвристика по маркерам даёт ~85% accuracy.

## Метрики для отчёта

1. **FP rate** = FP / (TP + FP) — доля FP среди всех вердиктов
2. **INVALID rate** = INVALID / 25 — доля INVALID в выборке
3. **Подтипы TP/FP** — группировка по корневой причине
4. **Примеры** — 2-3 конкретных случая с разбором

## Ограничения

- Выборка: 25 примеров на категорию, один seed
- Верификация: только визуальный анализ текста ошибки и предыдущего шага
- Не проверено: L5 (runtime ошибки без характерного сообщения)