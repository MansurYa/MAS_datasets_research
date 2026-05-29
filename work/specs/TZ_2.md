# TZ_2 — Извлечение `invalid_invocation` из nebius (исправленная версия)

## 📌 Цель

Из nebius/SWE-agent-trajectories (80 036 траекторий) извлечь ошибки типа `invalid_invocation` — агент вызвал инструмент с неверными параметрами. Траектории не типизированы — выводим из паттернов в поле `text`. Используем exit_status для фокусировки на failed траекториях.

## 📌 Ключевые исправления (по сравнению с прошлым парсером)

| Проблема прошлого парсера | Исправление в TZ_2 |
|---|---|
| Искал `tool_web_failure` по ключевым словам — получил 26 379 FP (номера строк, pytest errors) | Только `invalid_invocation`. Чёткие категории. Ручная верификация каждой. |
| Не использовал exit_status — разбавлял данные успешными траекториями | Сначала проверить наличие exit_status → фильтровать на failed |
| Не определил критерий "что считать invalid_invocation" до фильтрации | Явный критерий зафиксирован до начала фильтрации |
| Фиксированный n=25 при переменном объёме candidates | Адаптивный sample size |

## 📌 Структура данных nebius

```python
trajectory: List[Dict]
  ├─ role: str          # "user" | "assistant" | ...
  └─ text: str         # ВЕСЬ текст шага — tool call + error в одном поле

# Также проверить:
parquet schema
  ├─ trajectory: List[Dict]
  ├─ exit_status: str  # ← проверить наличие этого поля
  └─ ...другие поля?
```

## 📌 Принципы

**"Докажи мне" означает:**
- Каждое число подкреплено сырыми строками
- Mansur может открыть parquet и проверить любую candidate строку
- Если Mansur нашёл ошибку — это победа, не провал

**Суб-агенты — минимум 3:**
- Агент A: исследовать old parser + exit_status
- Агент B: TRAIL invalid_invocation examples
- Агент C: проектировать фильтры

**Вопросы:** Если сомневаешься — стоп, спроси.

## 📌 Шаг 1 — Исследовать old parser + exit_status

**1.1** Прочитать `archive/scripts/tz4_5_keyword_search.py`, строки 95–134.

Понять: почему 100% FP для tool_web_failure. Конкретно — какие keywords дали ложные срабатывания.

**1.2** Проверить структуру parquet:

```python
import pandas as pd
import pyarrow.parquet as pq

# Проверить schema первых 10 файлов
for i in range(1, 11):
    path = f"datasets/nebius-SWE-agent-trajectories/data/train.parquet"
    # или какой путь правильный?
```

Ключевые вопросы:
- Есть ли поле `exit_status` или аналог?
- Какой формат: `failed` / `success` / `passed` / коды?
- Если exit_status нет — как определить failed траекторию?

**1.3** Если exit_status есть → записать:
- Сколько траекторий failed
- Сколько passed
- Соотношение failed/total

Если exit_status нет → сообщить Mansur, спросить: работать со всеми 80 036 или есть другой способ выделить failed?

**Сохранить:** `work/reports/TZ_2_step1.md`

## 📌 Шаг 2 — TRAIL invalid_invocation examples

Из TRAIL взять 5–8 сырых примеров. Понять паттерны.

**Ключевой критерий (зафиксировать до фильтрации!):**

> Мы считаем строку `invalid_invocation`, если:
> 1. Агент вызвал инструмент с параметрами X
> 2. Инструмент вернул ошибку Y
> 3. Ошибка Y вызвана **неверными параметрами X**, а не внутренним багом инструмента

**Примеры:**
- `inspect_file_as_text({'file_path': 'data/gaia/validation/1f975693.mp3'}` → `FileNotFoundError` → **invalid_invocation** (агент передал несуществующий путь)
- `page_down({'page_down': ''}` → `TypeError: got an unexpected keyword argument` → **invalid_invocation** (агент передал аргумент, который инструмент не принимает)
- `inspect_file_as_text(...)` → `UnboundLocalError: cannot access local variable 'res'` → **НЕ invalid_invocation** (баг инструмента, не агента)

**Сохранить:** `work/reports/TZ_2_step2.md`

## 📌 Шаг 3 — Фильтры

### Категория A — Неверные пути к файлам

**Критерий:** Агент передал путь, которого нет в environment.

**Keywords:**
- `FileNotFoundError`
- `No such file or directory`
- `Path does not exist`
- `Is a directory` (агент передал директорию вместо файла)
- `cannot open file`

**НЕ включать:**
- Номера строк кода (`line 404`, `error at line 500`)
- Пути в исходном коде (pytest, assert)
- Ошибки в stdout программ

**Алгоритм:**
```python
# Псевдокод
if "FileNotFoundError" in text or "No such file" in text:
    if "line" in text.lower() and any(c.isdigit() for c in text):
        # номер строки — пропустить
        continue
    candidate = True
```

### Категория B — Неверные bash команды

**Критерий:** Агент вызвал команду, которой нет в PATH.

**Keywords:**
- `command not found`
- `ls: cannot access`
- `cp: cannot stat`
- `bash: line X: ...: command not found`

**НЕ включать:**
- `program not found` (программа не установлена, не агент виноват)
- Ошибки в stdout запущенных программ

### Категория C — TypeError в аргументах

**Критерий:** Агент передал аргумент, который инструмент не принимает.

**Keywords:**
- `unexpected keyword argument`
- `missing.*required.*argument` (regex)
- `takes.*positional.*argument.*but.*was given`

### Категория D — Пропущенные required arguments

**Критерий:** Агент пропустил обязательный параметр.

**Сложность:** Тяжело отличить от tool bug. Верифицировать очень осторожно.

**Keywords:**
- `missing.*required.*argument`
- `required.*argument`

**Сохранить:** `work/reports/TZ_2_step3.md` с обоснованием каждого keyword.

## 📌 Шаг 4 — Итеративный парсинг

Для каждой категории отдельно:

**4A.1** Написать `work/scripts/TZ_2_filter_A.py`. Запустить на nebius.

**4A.2** Если exit_status доступен → запустить только на failed траекториях.
Если нет → на всех, но записать в отчёт, что разбавлено.

**4A.3** Взять candidates. Оценить объём:
- < 20 candidates → хорошо, верифицировать все
- 20–500 → адаптивный sample (см. ниже)
- > 500 → адаптивный sample

**4A.4 Ручная верификация — адаптивный sample size:**

| n_candidates | verify |
|---|---|
| < 20 | Все |
| 20–200 | 20 |
| 200–1000 | 50 |
| 1000–5000 | 100 |
| > 5000 | 150 |

**Как верифицировать:** Каждую candidate строку проверить по критерию из Шага 2. Результат: TP / FP.

**Повторить для B, C, D.**

**Сохранить:** Итерации A-D → отдельные файлы `TZ_2_iteration_A.md`, `B.md`, `C.md`, `D.md`.

## 📌 Шаг 5 — Итоговый подсчёт

После верификации всех категорий:

```markdown
| Категория | n_candidates | n_verified | TP_rate | n_true |
|----------|--------------|------------|---------|--------|
| A: Пути | X | Y | Z% | W |
| B: Команды | X | Y | Z% | W |
| C: TypeError | X | Y | Z% | W |
| D: Missing args | X | Y | Z% | W |
| **ИТОГО** | **X** | **Y** | **Z%** | **W** |
```

**P(traj) для nebius:**
= n_true / (N_failed_trajectories или N_total_trajectories)

**Честно:** Если n_true < 20 для любой категории — сказать: "данных недостаточно".

## 📌 Шаг 6 — Отчёт

Создать `work/reports/TZ_2_report.md`:

```markdown
# TZ_2: invalid_invocation в nebius

## exit_status
[Есть ли поле, сколько failed]

## Критерий invalid_invocation
[Зафиксированный критерий из шага 2]

## Фильтры
| Категория | Keywords | Обоснование |
|----------|----------|------------|
| A | ... | Почему это invalid_invocation, а не tool bug |

## Результаты по категориям
[Таблица]

## Примеры — подтверждённые (сырые строки)
[Для каждой категории: 3-5 примеров с raw text snippet]

## Примеры — false positives
[3-5 примеров FP — чтобы было видно границу]

## Ручная верификация
[Что проверяли, как оценивали TP/FP]

## Ограничения
[Честно: где данных мало, где TP rate < 50%, где непонятно]
```
