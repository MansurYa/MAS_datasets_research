# Концепция invalid_invocation: что это и где границы

Дата создания: 2026-05-28
Обновление: 2026-05-29 (после FP-анализа субагентами, отключение C и D)
Контекст: парсер `work/scripts/nebius_all_errors.py` для nebius/SWE-agent-trajectories

## Определение

**invalid_invocation = ошибка, обнаруженная pre-execution.**

Критерий: валидатор отвергает вызов/edit/команду **до side-effect**. Файл не модифицируется, команда не выполняется, функция не запускается.

**TP** = pre-execution отказ (истинный invalid_invocation)
**FP** = runtime внутри уже запущенного скрипта (ошибка генерации кода, не invalid_invocation)

## Две независимые оси

1. **Timing** (когда обнаружено): pre-execution vs runtime
2. **Cause** (что не так с агентом): формат параметра vs значение vs качество кода

Все 6 категорий парсера pre-execution по timing. Различаются по **cause**.

## FP-анализ категорий (субагенты, 2026-05-28)

Метод: 25 случайных примеров на категорию → TP/FP по timing.

### Итоговая таблица FP rate

| Категория | TP | FP | INVALID | FP rate | Интерпретация |
|-----------|:--:|:-:|-------:|:-------:|---------------|
| A: FileNotFoundError | 24 | 1 | 0 | **4%** | Преимущественно pre-execution |
| B: command not found | 18 | 0 | 6 | **0%** | Чистый pre-execution; 24% — парсер ловит markdown |
| C: TypeError | 0 | 25 | 0 | **100%** | Полностью runtime; не invalid_invocation |
| D: missing arg | 0 | 0 | 25 | **—** | **ОТКЛЮЧЕНА 2026-05-29: 100% INVALID (CoT reasoning)** |
| E1: Edit E999 | 25 | 0 | 0 | **0%** | Чистый pre-execution через flake8 |
| E2: Edit F821 | 25 | 0 | 0 | **0%** | Чистый pre-execution через flake8 |

**INVALID** — записи, которые парсер захватил ошибочно (не ошибка из этой категории).

## Разбор по категориям

### A: FileNotFoundError / No such file or directory

**FP rate: 4% (1/25). Подавляющее большинство — pre-execution.**

3 записи классифицированы парсером как A, но ими не являются:
- `PyCQA__flake8-1642` → E1 (SyntaxError)
- `google__mobly-194` → E1 (SyntaxError)
- `ipython__ipython-11358` → B (`env: 'python': No such file`)

**Подтипы TP (24/25):**

| Подтип | Доля | Примеры |
|--------|:----:|---------|
| `ls -F <dir>` (несуществующая директория) | 58% | `ls -F src`, `ls tests` |
| `python <script>` (скрипт не создан) | 17% | `python reproduce.py` |
| `mv/rm` на несуществующий файл | 13% | `rm Dockerfile`, `mv test_md5.py ..` |
| `mkdir` с несуществующим родителем | 4% | `mkdir linkify-it-py_fork/staged-recipes` |

**Единственный FP: `melexis__warnings-plugin-57`** — агент запустил `python test_warnings_command.py`, скрипт выполнился, внутри сделал `open('cat')` → FileNotFoundError из traceback Python. Ключевой маркер: ошибка изнутри сгенерированного скрипта, не от tool runner.

**Слепое пятно:** парсер ловит только ошибки из stderr. FP может быть недооценён.

### B: command not found / cannot stat / cannot access

**FP rate: 0% (0/18 TP). Повторная верификация (seed=99).**

6 записей (24%) — **INVALID**. Парсер захватил текст из `` ```submit ``` `` markdown-блоков рассуждения агента, не bash-ошибку.

**Подтипы TP (18 записей):**

| Подтип | Доля | Примеры |
|--------|:----:|---------|
| Опечатки bash (нет пробела) | 44% | `find.`, `cd..`, `ls.dvc` |
| Галлюцинации инструментов | 28% | `search_duckduckgo`, `search_module`, `create.sqlfluff` |
| Python в bash | 11% | `close`, `from`, `end_of_edit` |
| Утилита не установлена | 11% | `flake8-bugbear`, `convert`, `delete` |

`iterative__dvc-3876` (count=217) и `iterative__dvc-8587` (count=147) — агент зацикливается на опечатке и повторяет 147-217 раз. Парсер фиксирует первое вхождение.

`d-Rickyy-b__pyBrematic-30` — `search_engine: command not found`. Агент придумал инструмент. **Галлюцинация reasoning LLM**.

**Вывод:** B — чистый pre-execution. 0% FP. 24% — парсер ловит markdown (следует добавить фильтр: "submit" или "edit" в многострочном markdown → INVALID).

### C: TypeError (unexpected keyword argument / wrong positional)

**FP rate: 100% (0 TP из 25). Все — runtime ошибки в сгенерированных скриптах.**

**Полная неожиданность.** Ни одного случая pre-execution валидации.

Все 25 — агент написал скрипт/reproduce/тест, тот выполнился, Python проверил сигнатуру при вызове.

**Подтипы:**

| Подтип | Доля | Описание |
|--------|:----:|----------|
| pytest failures | 32% | Агент написал тест, тот выполнился |
| reproduce script | 28% | Агент написал reproduce.py, скрипт выполнился |
| edit с кодом | 24% | Агент применил edit с кодом, код выполнился |
| module init | 8% | Код выполняется при import модуля |
| CLI wrapper | 8% | Агент написал обёртку для CLI |

**Примеры FP:**

`tableau__server-client-python-109`:
```python
tableau.auth.sign_in("username", "password")
TypeError: sign_in() takes 2 positional arguments but 3 were given
```

`ShawHahnLab__igseq-43`:
```
File "/igseq/igseq/getreads.py", line 107, in getreads
  _run_bcl2fastq(args, **kwargs)
TypeError: _run_bcl2fastq() got an unexpected keyword argument 'args_extra'
```

**Вывод:** C — **не invalid_invocation**. Это целиком Категория 1 (runtime сгенерированного кода). Парсер C — ловушка: он ловит ошибки из запущенных скриптов, а не отказы инструментов.

### D: missing required argument → ОТКЛЮЧЕНА (2026-05-29)

**Статус: ОТКЛЮЧЕНА. 100% INVALID (CoT reasoning text).**

Парсер D отключён. Детальный анализ — в секции **«Эволюция Категории D (после добавления Traceback-фильтра 2026-05-29)»** ниже.

Кратко:
- Паттерн `"missing" + "required" + "argument"` ловит **три разных сущности**: CoT reasoning (~45%), runtime (~36%), Edit tool (~19%)
- После Traceback-фильтра остались только CoT reasoning → 100% INVALID
- Маркер `"Your changes have NOT been applied"` не найден в observation-поле (0 совпадений)
- Парсер E1/E2 работает (ловит через `"would have looked if applied"`), D-маркер не совпадает с форматом nebius
- **Код сохранён (закомментирован)** для будущих задач по анализу runtime ошибок кодогенерации

*(Полный анализ до отключения — см. версию 2026-05-28)* (после добавления Traceback-фильтра 2026-05-29)

#### Что изменилось и почему

После FP-анализа D (2026-05-28, 44% FP rate) были добавлены жёсткие FP-фильтры:
- `[File:` — отсекает traceback из пользовательского скрипта
- `__init__()` — отсекает TypeError при инициализации классов
- `'self'"` — отсекает сигнатуры методов
- `'config'` + `'parameter'` — отсекает конфигурационные рассуждения
- `'Traceback'` — жёсткий отсекатель runtime

После добавления этих фильтров все 25 оставшихся записей оказались **INVALID** (100% INVALID rate).

#### Корневая причина

Паттерн `"missing" + "required" + "argument"` в nebius/SWE-agent ловит **три разных сущности**:

| Сущность | Доля (2026-05-28) | Timing | Парсер ловит |
|----------|:-----------------:|:------:|-------------|
| Runtime argparse в пользовательском скрипте | ~36% | Runtime | Да (Traceback) |
| Agent CoT reasoning о недостающих параметрах | ~45% | — | Да (без фильтра) |
| Edit tool rejection | ~19% | Pre-execution | Да ("Your changes have NOT been applied") |

После Traceback-фильтра остались только CoT reasoning (~45%) + Edit tool rejection (~19%). Все 25 оказались CoT reasoning → **100% INVALID**.

#### Попытка grep по "Your changes have NOT been applied"

Был предпринят поиск точного маркера pre-execution отказа:
```
grep "Your changes have NOT been applied" (точное совпадение)
```
**0 совпадений** в observation-поле всех 80 036 траекторий.

Вариации:
- `changes have NOT been applied` (case-insensitive) → 246 560 совпадений
  - Но 246 560 попаданий в lowercase-полях (tool_call, reasoning), не в observation
- `changes were not applied` → 302 совпадения
  - Все в lowercase-полях (reasoning), 0 в observation
- `"changes were not applied"` (observation only) → 0 совпадений

**Вывод:** Edit tool в nebius/SWE-agent **не использует** фразу `"Your changes have NOT been applied"`. Поле observation содержит ответ валидатора, но без этой фразы. Альтернативные маркеры не дали результата.

#### Выводы

1. **D — не invalid_invocation.** Паттерн `"missing required argument"` в nebius/SWE-agent ловит CoT-рассуждения агента о недостающих параметрах, а не отказы инструментов.

2. **100% INVALID.** После добавления Traceback-фильтра все оставшиеся записи — CoT reasoning, не ошибки.

3. **"Your changes have NOT been applied" отсутствует.** Edit tool в nebius использует другой формат ответа валидатора. Парсер E1/E2 работает (ловит через фразу `"Your proposed edit has introduced new syntax error"`), но D-маркер не совпадает с реальным форматом.

4. **Парсер D отключён.** Код сохранён (закомментирован), не удалён — для будущих задач по анализу runtime ошибок кодогенерации (Категория 1).

5. **Category C и D — общий урок:** Парсеры, заточенные на keyword search, ловят широкий класс текстов. Без надёжных структурных маркеров (как `"would have looked if applied"` для E1/E2) — FP rate стремится к 100%.

#### Обновлённые FP rate (2026-05-29)

| Категория | Статус | FP rate | Причина |
|-----------|:------:|:-------:|---------|
| A | Активна | 4% | Редкие FP изнутри скрипта |
| B | Активна | 0% | Markdown-фильтр (2026-05-29) |
| C | **Отключена** | **100%** | Runtime, не tool invocation |
| D | **Отключена** | **100% INVALID** | CoT reasoning, нет маркера pre-execution |
| E1 | Активна | 0% | Чистый pre-execution |
| E2 | Активна | 0% | Чистый pre-execution |

### E1: Edit E999 (SyntaxError, IndentationError)

**FP rate: 0% (0/25). Чистый pre-execution через flake8.**

Все 25 содержат `"Your proposed edit has introduced new syntax error(s)"` — Edit tool отвергает edit до применения через flake8 (E999).

**Подтипы E999:**

| Подтип | Доля | Пример |
|--------|:----:|--------|
| IndentationError: unexpected indent | 48% | 12 случаев |
| IndentationError: expected an indented block | 20% | 5 случаев |
| SyntaxError: unterminated string literal | 12% | 3 случая |
| SyntaxError: '(' was never closed | 8% | 2 случая |
| SyntaxError: invalid syntax | 8% | 2 случая |
| SyntaxError: unmatched ')' | 4% | 1 случай |

`iterative__dvc-4086` (count=28) — агент оставил "висячий" `help=argparse.SUPPRESS,` без родительского `add_argument()`. Повторил 28 раз.

`pydantic__pydantic-1658` (count=53) — агент создал пустой класс. Много повторений (53).

**Вывод:** E1 — идеальный чистый invalid_invocation. Категория 3.

### E2: Edit F821 (undefined name)

**FP rate: 0% (0/25). Все — pre-execution через flake8.**

Все 25 содержат `"This is how your edit would have looked if applied"` — Edit tool отверг edit до применения. Код **никогда не применялся** к файлу.

**Подтипы причин F821:**

| Подтип | Доля | Примеры |
|--------|:----:|---------|
| Забытый import стандартной библиотеки | 40% | os, sys, logging, datetime, pprint, mimetypes |
| Забытый import стороннего модуля | 32% | pytest, musicbrainzngs, tdclient, bleach |
| Массовая потеря импортов при рефакторинге | 16% | dvc (3 случая), vault-cli, dataspec |
| Псевдокод с придуманными функциями | 8% | ForLoop, get_declared_variable_name, update_import |
| Сломанный scope (переменная недоступна) | 4% | deadline, js, error (вне except) |

**Примеры:**

`peopledoc__vault-cli-111` (count=354) — агент удалил блок импортов (VaultClientBase, JSONValue, Optional, types, settings). 354 F821 в одной попытке. Edit tool отверг всё.

`PyCQA__flake8-bugbear-220` — агент написал псевдокод:
```python
if isinstance(node, ForLoop):
    declared_variable_name = get_declared_variable_name(node)
```
Эти хелперы не существуют в codebase. **Галлюцинация**.

`graphql-python__graphene-751` — scope bug:
```python
except AssertionError as error:
    assert 'Must receive a CustomNode id.' in error
assert 'a' in error  # 'error' вне except-блока
```

**Вывод:** E2 — 100% pre-execution. Категория 3.

## Уровни валидации (пересмотренная модель)

Старая модель (timing) слишком груба. Все 6 категорий pre-execution по timing. Новая модель — **уровни валидации**:

| Уровень | Где происходит | Категории | Invalid invocation? |
|---------|---------------|-----------|---------------------|
| L1: Сигнатура вызова | Парсер аргументов | ~~D~~ (отключена) | — |
| L2: Простая валидация параметра | Tool runner | A | Да |
| L3: Валидация кода через flake8 | Edit tool + flake8 | E1, E2 | Да |
| L4: Subprocess отвергает команду | Bash (PATH lookup) | B | Да |
| L5: Subprocess исполнил, код упал | Runtime среды | C (отклющена) | **Нет** |

**L5 не ловится парсером** (заточен на L1-L4). C — 100% L5, D — 44% L5.

## Корректировка статистики ошибок

Пересчёт долей FP в исходных данных (Вариант 4, все вхождения):

| Категория | Вхождений (Σ) | Доля | FP rate | Истинных pre-execution |
|-----------|-------------:|:----:|:-------:|:---------------------:|
| E2 | 181,646,818 | 87% | 0% | **181,6M** |
| E1 | 8,131,958 | 4% | 0% | **8,1M** |
| B | 17,008,489 | 8% | 0% | **17,0M** |
| A | 1,055,063 | 0.5% | 4% | **~1,0M** |
| C | 92,942 | 0.04% | **100% (отклющена)** | **~0** |
| D | 33,189 | 0.02% | **100% INVALID (отклющена)** | **~0** |

**Итого:** из 207,968,459 "ошибок invalid_invocation" — истинных pre-execution: **~207,8M (99.9%)**.

## Категории для симулятора Huawei

- **A, B, E1, E2** → Категория 3 (статистическое моделирование)
- **D** → **ОТКЛЮЧЕНА 2026-05-29** (100% INVALID, CoT reasoning, не invalid_invocation)
- **C** → целиком Категория 1 (100% runtime сгенерированного кода, не invalid_invocation)

C — **не invalid_invocation**. Парсер ловит ошибки из запущенных скриптов, а не отказы инструментов.

## Слепые пятна парсера

1. **B ловит markdown** (24% INVALID): `` ```submit ``` `` в рассуждении агента → захватывается как bash-ошибка. Фильтр: если текст ошибки содержит "submit" или "edit" в многострочном markdown-блоке → INVALID.

2. **C — ловушка**: парсер ловит TypeError из запущенных скриптов. Это runtime ошибки, не отказы инструментов. C не является invalid_invocation.

3. **C и D — ловушки keyword search:**
   - C: парсер ловит TypeError из запущенных скриптов (100% runtime, не invalid_invocation)
   - D: паттерн `"missing required argument"` ловит CoT-рассуждения агента; после Traceback-фильтра — 100% INVALID. **Отключена 2026-05-29.**
   - Общий урок: без надёжных структурных маркеров (как `"would have looked if applied"` для E1/E2) — FP rate стремится к 100%.

4. **L5 не ловится**: парсер заточен на L1-L4. Настоящий runtime (сгенерированный код упал без характерного сообщения) — невидим.

5. **A/B классификация пересекается**: `cannot stat` — то ли в bash (B), то ли в пользовательском скрипте (A). Парсер разделяет по ключевым словам, но граница нечёткая.

## Связанные документы

- `work/scripts/nebius_all_errors.py` — парсер всех 6 категорий
- `work/scripts/nebius_errors_cli.py` — CLI для интерактивного анализа
- `work/docs/nebius_error_statistics.md` — статистика по 4 вариантам подсчёта
- `memory/project_nebius_invalid_invocation.md` — контекст парсера
- `memory/project_nebius_error_stats_detailed.md` — статистика с 4 вариантами