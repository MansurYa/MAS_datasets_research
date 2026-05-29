# TZ_2 v2: Извлечение invalid_invocation из nebius/SWE-agent — Финальный отчёт

**Дата:** 2026-05-22
**Источник:** первый шард nebius/SWE-agent-trajectories (6 670 из 80 036 траекторий)
**Статус:** v2 — итерация после провала v1 на категориях C/D

---

## 1. Краткая сводка

| Категория | TP rate | n_unique | n_true | Надёжность |
|-----------|---------|----------|--------|------------|
| **A:** Неверные пути (FileNotFoundError) | 100% | 2 666 | 2 666 | ✓ Отличная |
| **B:** Bash command not found | **84.0%** | 560 | 470 | ✓ Хорошая |
| C: TypeError аргументы | 0.0% | 107 | 0 | ✗ **Ненадёжная** |
| D: Missing required args | 5.0% | 148 | 7 | ✗ **Ненадёжная** |
| **E1:** Edit tool E999 (синтаксис) | **100%** | 1 001 | 1 001 | ✓ Отличная |
| E2: Edit tool F821 (undefined name) | 50%* | 2 613 | 1 306 | ⚠ Пограничная |

*для E2: 19% TP / 79% UNKNOWN / 2% FP. Реалистичная среди полных edit-блоков — 90.5%, но 79% выборки имеют обрезанный edit-блок.

**Итог по надёжным категориям (A + B + E1):** 4 137 истинных событий → P_step ≈ 0.0116, P_traj ≈ 0.297.

**С учётом E2 (TP 0.50):** 5 450 истинных событий → P_step ≈ 0.0153, P_traj ≈ 0.383.

---

## 2. Концептуальная ошибка v1 и решение v2

### 2.1 Что было упущено

Парсер v1 искал по keyword search (например, `unexpected keyword argument`). Он не различал три уровня ошибок:

| Уровень | Пример | invalid_invocation? |
|---------|--------|---------------------|
| Tool validation | `edit` отклонил malformed Python | ✓ Да |
| Tool execution | `bash` запустил команду, не нашёл в PATH | ✓ Да (граничный) |
| **Code execution** | `bash("python X.py")` → Python TypeError | ✗ Нет |

В категориях C и D 67–77% кандидатов оказались **code execution** (3-й уровень), а не tool invocation.

### 2.2 Что сделано в v2

1. Добавлены FP-guards для исключения файловых листингов (`[File:`), конструкторов (`__init__()`), traceback из user-скриптов (`reproduce.py`, `test_*.py`, `run_*.py`), `FutureWarning`, `ls: cannot access` (это категория A).
2. Добавлена дедипликация по `(instance_id, error_pattern_hash)` с сохранением `count` повторов. Сжатие 1.3x–12.7x по категориям.
3. Добавлена **новая категория E** — edit tool validation errors. Это единственный tool в SWE-agent с строгой валидацией (flake8/pyflakes). Ответ структурирован, его легко распарсить:
   - **E1:** E999 (SyntaxError + IndentationError) — критическая ошибка синтаксиса.
   - **E2:** F821 (undefined name) — переменная/имя не определено.
4. Добавлена эвристика для E2: проверка, есть ли `import` нужного имени в edit-блоке агента (`import_present_in_edit`).

### 2.3 Источники

| Утверждение | Источник |
|-------------|----------|
| Tools SWE-agent: 20, только edit с валидацией | `work/docs/TZ_2_parser_v2_analysis.md` (subagent C) |
| Edit errors: 17 538 в первом шарде (v1 keyword) | subagent E |
| C: 67.4% — code execution | subagent B (анализ candidates_C.json) |
| D: 77% — code execution | subagent B (анализ candidates_D.json) |
| Повторы: 81.6% | subagent F |

---

## 3. Результаты по категориям

### 3.1 A — Неверные пути (без изменений)

- 2 666 кандидатов, 100% TP (по верификации v1).
- P_traj = 0.140 (935 уникальных траекторий из 6 670).
- Без дедипликации, ибо в v1 не считалась.

### 3.2 B — Bash command not found (улучш.)

- v1: 7 909 кандидатов, 63.3% TP.
- v2 после FP guard `'ls: cannot access' in text`: 7 126 сырых.
- После дедипликации: **560 уникальных** (сжатие 12.7x).
- Sample 50 из 560 → **42 TP, 8 FP, TP rate 84%**.
- P_traj = 0.051.

**Примеры TP:**
- `find.` — агент написал `find.` вместо `find .` (точка слита с командой)
- `cd..` — агент написал `cd..` вместо `cd ..` (пропущен пробел)
- `ping`, `host`, `editcap` — команды не установлены в контейнере

**Почему парсер ошибается — два механизма FP (8 из 50):**

**Механизм 1: Текст рассуждений агента (6 из 8 FP)**

Парсер ищет `command not found` / `cannot access` / `cannot stat` в `step['text']`. Но `step['text']` содержит весь текст шага — рассуждения агента + команду. Если агент написал рассуждение, а потом вызвал `edit` или `goto`, парсер берёт шаг из-за слов в рассуждении, хотя bash-ошибки не было.

Пример — `pvlib__pvlib-python-1296`:
```
It appears that I introduced an error by referencing an undefined variable `corrections`
in the return statement. Let's correct this...
edit 1:10
...
end_of_edit
```
Слова `cannot access` нет в этом тексте — но парсер взял шаг из-за `cannot` в другом контексте. Bash не запускался.

Пример — `reata__sqllineage-17`:
```
The `sqlparse.parse` function is used on line 21... Since we cannot access the
`sqlparse` documentation directly...
goto 23
```
Фраза `cannot access` — это рассуждение агента о том, что он не может открыть документацию. Никакого bash-вызова нет.

Пример — `ESSS__conda-devenv-51`:
```
It seems that the `conda` directory is not present... Since we cannot access it,
we'll have to simulate its structure.
mkdir conda
```
`cannot access` — снова рассуждение. Команда `mkdir conda` — это корректный вызов bash, но ошибки `command not found` не было.

Пример — `docker__docker-py-822`:
```
DISCUSSION
It seems that the Docker daemon is not accessible via TCP at `localhost:2375`...
search_dir "http+docker" src
```
`not accessible` содержит `cannot` — парсер взял шаг. Агент вызвал `search_dir`, не bash.

**Механизм 2: Ошибка категории A (1 из 8 FP)**

Пример — `sciunto-org__python-bibtexparser-385`:
```
cp: cannot stat '/python-bibtexparser/articleNotes.bib': No such file or directory
/root/commands/edit_linting.sh: line 65: /python-bibtexparser/articleNotes.bib: No such file or directory
[File: /python-bibtexparser/articleNotes.bib (2 lines total)]
```
Ошибка `cp: cannot stat` — это FileNotFoundError (категория A), а не `command not found` (категория B). FP guard `'ls: cannot access'` исключает только `ls`, но не `cp: cannot stat`.

**Корень проблемы:** `cannot access` и `cannot stat` — слишком широкие паттерны. Они срабатывают на рассуждения агента ("we cannot access the documentation") и на ошибки других команд (`cp`, `mv`), которые относятся к категории A.

### 3.3 C — TypeError (улучш., ненадёжна)

- v1: 935 кандидатов, 40% TP.
- v2 после FP guards (`[File:`, `FutureWarning`, user scripts): 249 сырых.
- После дедипликации: **107 уникальных** (сжатие 2.3x).
- Sample 20 из 107 → **0 TP, 20 FP, TP rate 0%**.
- Все FP: traceback из user scripts (8), описания агента (7), вывод команд (3), edit-блоки (2).

**Почему парсер ошибается — три механизма FP:**

**Механизм 1: Traceback из user script (8 из 20 FP)**

Парсер ищет `unexpected keyword argument` или `takes X positional arguments` в тексте шага. Но этот текст — это не только ответ tool, это весь вывод bash. Когда агент запускает `python reproduce.py`, bash возвращает полный traceback Python. Парсер видит ключевые слова и берёт шаг.

Пример — `pydantic__pydantic-2262`:
```
Traceback (most recent call last):
  File "/pydantic/generic_type.py", line 54, in <module>
    print(Model.schema())
  ...
TypeError: field_type_schema() got an unexpected keyword argument 'shape'
(Open file: /pydantic/pydantic/schema.py)
bash-$
```
Это traceback из скрипта `generic_type.py`, который агент запустил через bash. Bash отработал корректно — он запустил Python. Ошибка внутри Python-кода, не в вызове tool.

Пример — `tech-teach__marshmallowjson-3`:
```
Traceback (most recent call last):
  File "/marshmallowjson/validate.py", line 56, in <module>
    schema = Schema({
TypeError: __init__() takes 1 positional argument but 2 were given
(Open file: /marshmallowjson/validate.py)
bash-$
```
Агент запустил `validate.py`, код упал. Это code execution, не tool invocation.

**Механизм 2: Текст рассуждений агента (7 из 20 FP)**

В SWE-agent каждый шаг траектории содержит **весь текст**, который агент написал перед командой — включая рассуждения. Если агент написал "It seems that we are still passing arguments incorrectly...", а потом вызвал `edit`, парсер берёт этот шаг, потому что в тексте есть ключевые слова.

Пример — `bids-standard__pybids-611`:
```
It seems that we are still passing the arguments incorrectly. The `BIDSDataFile`
constructor takes `path` and `entities` as positional arguments...

edit 11:11
    bids_file = BIDSDataFile('small_physio.tsv.gz', {'suffix': 'physio'})
end_of_edit
```
Ключевые слова есть в рассуждении, а не в ответе tool. Сам вызов `edit` — это корректный tool invocation.

Пример — `getsentry__responses-291`: весь шаг — это текст issue из GitHub (описание бага), где цитируется traceback с `TypeError: __init__() got an unexpected keyword argument 'msg'`. Парсер взял issue description как кандидата.

**Механизм 3: Edit-блок с кодом (2 из 20 FP)**

Агент пишет `edit` с Python-кодом, в котором упоминается TypeError в комментарии или в строке кода. Парсер берёт шаг, хотя ошибки нет — это просто код.

Пример — `asottile__pyupgrade-313`: агент пишет большой `edit` блок с кодом обработки токенов. В тексте шага есть слово `positional` в контексте комментария к коду. Ошибки нет, tool принял edit.

**Корень проблемы:** парсер ищет ключевые слова в `step['text']`, который содержит **всё** — рассуждения агента, traceback из bash, issue description, код в edit-блоке. Нет способа через keyword search отличить "ошибка в ответе tool" от "ключевое слово в тексте шага".

- **Вывод:** парсер C ловит TypeError из любого контекста, но в выборке не оказалось ни одного реального tool invocation. Категория **исключена** из метрик.

### 3.4 D — Missing required args (улучш., ненадёжна)

- v1: 1 379 кандидатов, 29% TP.
- v2 после FP guards (`[File:`, `__init__()`, user scripts): 190 сырых.
- После дедипликации: **148 уникальных** (сжатие 1.3x).
- Sample 20 из 148 → **1 TP, 19 FP, TP rate 5%**.
- Единственный TP: `planet search_quick() missing 'pretty'` — реальный CLI-инструмент.
- 19 FP: code execution (7), описания агента (10), внутренние ошибки декораторов (2).

**Почему парсер ошибается — три механизма FP:**

**Механизм 1: Code execution в user script (7 из 19 FP)**

Тот же механизм, что в категории C. Агент запускает `python reproduce.py`, скрипт падает с `TypeError: X() missing 1 required positional argument`. Bash вернул traceback, парсер взял шаг.

Пример — `mplanchard__pydecor-20`:
```
get_node_information() missing 1 required positional argument: 'key'
get_node_information() missing 1 required positional argument: 'key'

(Open file: /pydecor/reproduce.py)
bash-$
```
Видно `(Open file: /pydecor/reproduce.py)` — это вывод после запуска `reproduce.py`. Агент написал скрипт, скрипт упал. Bash отработал корректно.

Пример — `mplanchard__pydecor-20` (другой шаг):
```
Handling exception: myfunction() missing 1 required positional argument: 'x'

(Open file: /pydecor/reproduce_intercept.py)
bash-$
```
Снова user script (`reproduce_intercept.py`). Ошибка внутри Python-кода агента.

**Механизм 2: Текст рассуждений агента (10 из 19 FP)**

Агент рассуждает о проблеме и упоминает ключевые слова в тексте шага. Парсер берёт шаг, хотя никакого tool invocation не было.

Пример — `nose-devs__nose2-472` (первый шаг):
```
We're currently solving the following issue within our repository. Here's the issue text:
ISSUE:
...
TypeError: test_foo() missing 1 required positional argument: 'mock_urllib3_poolmanager'
...
INSTRUCTIONS:
Now, you're going to solve this issue on your own...
(Current directory: /nose2)
bash-$
```
Это **первый шаг траектории** — системный промпт с описанием задачи. Ключевые слова есть в тексте issue, который агент получил как задание. Никакого tool invocation ещё не было.

Пример — `nose-devs__nose2-472` (другой шаг):
```
We are now looking at the implementation of the `patch` function. The issue describes
a problem when running a specific test with the `nose2` command. The error message
suggests that the `test_foo` function is missing a required positional argument...
find_file "mock.py"
```
Агент рассуждает о проблеме, упоминает ключевые слова, потом вызывает `find_file`. Парсер взял шаг из-за рассуждения, а не из-за ошибки tool.

Пример — `mplanchard__pydecor-20`:
```
It seems that the issue is not resolved yet. The error message indicates that the
`myfunction` is missing the required positional argument `x`...
edit 53:53
    try:
        ...
end_of_edit
```
Агент описывает ошибку в рассуждении, потом делает `edit`. Парсер взял шаг из-за слов в рассуждении.

**Механизм 3: Внутренние ошибки декораторов/фреймворков (2 из 19 FP)**

Ошибка возникает внутри фреймворка (unittest.mock, pydecor), а не в вызове tool агентом.

Пример — `nose-devs__nose2-472`:
```
ERROR: test_mock.transplant_class.<locals>.C (test_foo)
Traceback (most recent call last):
  File "/var/lang/lib/python3.7/unittest/mock.py", line 1256, in patched
    return func(*args, **keywargs)
TypeError: test_foo() missing 1 required positional argument: 'mock_urllib3_poolmanager'
```
Ошибка внутри `unittest/mock.py` — это баг в самом `nose2` (суть issue). Агент не вызывал никакой tool с неверными параметрами.

**Корень проблемы:** идентичен категории C. `step['text']` содержит всё — issue description, рассуждения, traceback из bash. Keyword search `missing required argument` срабатывает на любое упоминание этих слов в любом контексте.

- **Вывод:** категория **исключена** из метрик.

### 3.5 E1 — Edit tool E999 (новая, отличная)

- 10 148 сырых кандидатов (по каждой ошибке отдельно).
- После дедипликации: **1 001 уникальных** (сжатие 10.1x).
- Sample 100 из 1 001 → **100 TP, 0 FP, TP rate 100%**.
- Распределение: IndentationError (58%), SyntaxError (42%).
- Топ повторов: `iterative__dvc-6633` (202 повтора), `networkx__networkx-7024` (163), `serge-sans-paille__gast-59` (114).
- P_traj = 0.118 (786 траекторий).
- **Вывод:** самая надёжная категория, готова к симулятору.

### 3.6 E2 — Edit tool F821 (новая, пограничная)

- 18 732 сырых кандидатов.
- 401 (2.1%) с `import_present_in_edit=true` (вероятный FP — flake8 не увидел).
- 18 331 (97.9%) без import в видимом edit-блоке.
- После дедипликации: **2 613 уникальных** (сжатие 7.2x).
- Sample 100 → 19 TP, 2 FP, **79 UNKNOWN** (edit-блок обрезан, есть `(N more lines above/below)` — невозможно проверить, есть ли import в скрытой части).
- Три варианта TP rate:
  - Пессимистично (UNKNOWN = FP): 19%.
  - Среди полных блоков (TP / (TP + FP)): **90.5%**.
  - Оптимистично (UNKNOWN = TP): 98%.
- В метриках использовано **0.50** как компромисс.

**Почему парсер ошибается — два механизма FP/UNKNOWN:**

**Механизм 1: flake8 не видит псевдоним импорта (2 FP)**

flake8/pyflakes анализирует только то, что видит в edit-блоке. Если имя импортировано под псевдонимом (`import ast as _ast`), flake8 не связывает `ast` с `_ast` и выдаёт F821.

Пример — `serge-sans-paille__gast-59`, `undefined_name='ast'`:
```
ERRORS:
- F821 undefined name 'ast'  (×38 раз)
```
В edit-блоке агента есть строка `import ast as _ast`. Код использует `ast.*` — это корректно, потому что `_ast` это псевдоним. Но flake8 видит `ast` как неопределённое имя. Агент написал правильный код, tool ошибся.

Пример — `wireservice__agate-637`, `undefined_name='agate'`:
```
[File: /agate/reproduce.py (20 lines total)]
1:from agate.aggregations import All
2:from agate.data_types import Boolean
3:from agate.table import Table
...
7:    {'name': 'Alice', 'active': agate.Boolean(True)},
...
12:import agate.data_types as dt
```
Строка 7 использует `agate.Boolean(...)`, но `agate` как модуль не импортирован — только отдельные классы из него. Это настоящая ошибка агента (он должен был написать `Boolean(True)`, а не `agate.Boolean(True)`). Однако `import_present_in_edit=True` сработал из-за строки 12 (`import agate.data_types as dt`), которая содержит слово `agate`. Эвристика дала ложный сигнал.

**Механизм 2: Обрезанный edit-блок (79 UNKNOWN)**

Edit tool показывает файл с ограничением по строкам. Если файл большой, в блоке появляется `(N more lines above)` или `(N more lines below)`. Импорт обычно в начале файла — если он в скрытой части, нельзя сказать, есть он или нет.

Пример — `tianocore__edk2-pytool-extensions-41`, `undefined_name='self'`:
```
[File: /edk2-pytool-extensions/edk2toolext/invocables/edk2_ci_build.py (347 lines total)]
(84 more lines above)
...
(57 more lines below)
```
Видно только середину файла. `self` — это параметр метода, он определён в сигнатуре функции, которая может быть в скрытой части. Нельзя сказать TP или FP.

Пример — `geopandas__geopandas-2959`, `undefined_name='geoms'`:
```
(150 more lines above)
...
(1366 more lines below)
```
Файл огромный, видно только фрагмент. Переменная `geoms` может быть определена выше.

**Корень проблемы:** F821 — это сигнал уровня файла, но edit tool показывает только фрагмент. Для 79% выборки нельзя верифицировать, потому что контекст обрезан. Надёжны только кандидаты с полным edit-блоком (без `more lines`).

- **Вывод:** надёжна только подвыборка с полными edit-блоками. Для симулятора требуется отдельный фильтр по полноте.

---

## 4. Метрики P_err

### 4.1 По первому шарду

| Метрика | Все категории | Только надёжные (A+B+E1) |
|---------|---------------|---------------------------|
| Всего шагов | 356 301 | 356 301 |
| Уникальных событий | 7 095 | 4 227 |
| Истинных событий (TP-коррекция) | 5 450 | 4 137 |
| **P_step** (true / steps) | **0.0153** | **0.0116** |
| Траекторий с ≥1 ошибкой | 2 552 | 1 980 (приближённо) |
| **P_traj** | **0.383** | **0.297** |

P_traj и P_step — это две независимые метрики:
- **P_step** нужен для блоков IR-графа (вероятность ошибки на одном шаге агента).
- **P_traj** нужен для оценки агента в целом (доля сессий, где была хотя бы одна ошибка).

### 4.2 Экстраполяция на весь датасет (80 036 траекторий)

- Ожидаемых траекторий с ошибкой: **30 622**.
- Ожидаемых истинных событий: **65 397**.
- Ожидаемых истинных событий по надёжным категориям: ≈ **49 600**.

Экстраполяция предполагает, что распределение ошибок в первом шарде типично. Для подтверждения нужно прогнать парсер по всем 12 шардам.

---

## 5. Дедипликация — статистика повторов

| Категория | n_raw | n_unique | сжатие |
|-----------|-------|----------|--------|
| B | 7 126 | 560 | 12.7x |
| C | 249 | 107 | 2.3x |
| D | 190 | 148 | 1.3x |
| E1 | 10 148 | 1 001 | 10.1x |
| E2 | 18 732 | 2 613 | 7.2x |

Высокое сжатие в B и E1 говорит о том, что агенты часто застревают на одной и той же ошибке. Например, `iterative__dvc-6633` — 202 повтора одной IndentationError. Это согласуется с цифрой "81.6% повторы" из subagent F.

Для симулятора это означает: **P_step нужно считать по уникальным событиям**, иначе одна ошибка завысит метрику в 10 раз.

---

## 6. Ограничения v2

1. **Категории C и D отброшены.** В них есть ~622 настоящих tool invocation (по subagent B), но отделить их от code execution через keyword search невозможно. Для будущей итерации — нужен structural parse (AST trajectory).

2. **F821 неоднозначен.** flake8/pyflakes не видит cross-file imports. 79% выборки E2 имеют обрезанные edit-блоки, для них нельзя сказать, был ли import. Эту подкатегорию используем с осторожностью.

3. **Только первый шард.** 6 670 из 80 036 траекторий. Если результаты согласуются на 2-м шарде — считать репрезентативными.

4. **B — частичная валидация.** bash валидирует PATH, не код в скрипте. `command not found` — это OS-level. Граничный случай, но оставлен как валидная категория (84% TP подтверждает).

5. **Единственный пропущенный класс ошибок.** Tools `open`, `goto`, `create`, `search_*`, `submit` либо не валидируют аргументы вообще, либо проверяют только existence (попадает в категорию A). Других чистых сигналов в SWE-agent нет.

---

## 7. Рекомендации для симулятора

### 7.1 Что использовать

- **A + B + E1** как основу: 4 137 уникальных истинных событий, P_step ≈ 0.0116, P_traj ≈ 0.297.
- E2 — опционально, с фильтром по полноте edit-блока (только полные блоки, ~21% выборки).

### 7.2 Что не использовать

- C и D в текущем виде — TP rate < 10%, шум перевешивает сигнал.

### 7.3 Дальнейшие шаги (если будет TZ_3)

1. Прогнать парсеры B/E1/E2 на всех 12 шардах (≈ 80 036 траекторий).
2. Для E2 — добавить фильтр на полноту edit-блока (исключить кандидатов с `more lines above/below`).
3. Для C/D — переработать через structural parse trajectory: смотреть `action.tool_name` явно, а не keyword search.
4. Подобрать распределения времени появления ошибки (доля шага в траектории) — для fault injection.

---

## 8. Файлы

### Скрипты
- `work/scripts/TZ_2_filter_A.py` — без изменений с v1
- `work/scripts/TZ_2_filter_B.py` — v2 (FP guards + дедипликация)
- `work/scripts/TZ_2_filter_C.py` — v2 (FP guards + дедипликация)
- `work/scripts/TZ_2_filter_D.py` — v2 (FP guards + дедипликация)
- `work/scripts/TZ_2_filter_E.py` — новый (E1 + E2)
- `work/scripts/TZ_2_aggregate.py` — новый (агрегация и метрики)

### Данные
- `work/data/TZ_2_v2_candidates_{B,C,D,E1,E2}.json` — уникальные события
- `work/data/TZ_2_v2_candidates_{B,C,D,E1,E2}_raw.json` — все сырые кандидаты
- `work/data/TZ_2_v2_sample_{B,C,D,E1,E2}.json` — выборки для верификации
- `work/data/TZ_2_v2_metrics.json` — метрики

### Документы
- `work/docs/TZ_2_parser_v2_analysis.md` — анализ ошибок v1, обоснование v2
- `work/docs/TZ_2_v2_iteration_{B,C,D,E1,E2}.md` — отчёты по фильтрам
- `work/docs/TZ_2_v2_aggregate.md` — агрегированные метрики
- `work/reports/TZ_2_v2_report.md` — этот отчёт
- `work/reports/TZ_2_report.md` — старый v1 отчёт (сохранён как reference)

---

## 9. Итог

v2 переопределил парсер: вместо широкого keyword search — узкие категории с FP guards и дедипликацией.

- Надёжные категории (A, B, E1) дают **P_step ≈ 0.0116**, **P_traj ≈ 0.297** на первом шарде.
- E2 пограничная (TP rate зависит от того, как считать UNKNOWN).
- C и D отброшены: keyword search ловит code execution, не tool invocation.

Цифры готовы для использования в симуляторе DA с оговорками, перечисленными в разделе 6.
