# Карта репозитория MAS_datasets_research

**Обновлено:** 2026-05-20 (после реструктуризации — два цикла разделены)

## Проект

Исследовательский проект для Huawei (СПбГУ × Huawei Joint Lab).
Цель — извлечь параметры ошибок агентных траекторий для fault injection в симулятор динамической доступности (DA) LLM.

**Статус:** Старый цикл (ТЗ №1–7) отклонён Huawei → архив. Текущая работа: TZ_1.

---

## Структура директорий

### Корень

| Файл/Папка | Описание |
|-----------|---------|
| `CLAUDE.md` | Инструкции для Claude Code — читать первым |
| `AGENT_TRAJECTORY_DATASETS.md` | Документация датасетов (RU) |
| `fault_mode_analysis_and_classification_ru.html` | TRAIL таксономия (интерактивный HTML) |
| `p1_fault_mode_distributions.ipynb` | Jupyter notebook с анализом распределений |
| `.gitignore` | Исключения git |

### datasets/

Все датасеты Hugging Face. Не трогать без необходимости — большие файлы.

| Папка | HuggingFace ID | Домен | Размер | Типизация ошибок |
|-------|---------------|-------|--------|-----------------|
| `TRAIL/` | — | Multi-Domain | — | Да (экспертная разметка, 836 ошибок) |
| `Kevin355-Who_and_When/` | `Kevin355/Who_and_When` | Multi-Agent | 52MB | Да (только HC-сплит, 58 записей) |
| `microsoft-AgentRx/` | `microsoft/AgentRx` | Multi-Domain | 7.1MB | Да (failure_category, root_cause) |
| `nebius-SWE-agent-trajectories/` | `nebius/SWE-agent-trajectories` | SE/Terminal | 1.0GB | Нет |
| `SWE-Gym-OpenHands-Sampled-Trajectories/` | `SWE-Gym/OpenHands-Sampled-Trajectories` | SE | 289MB | Нет |
| `yoonholee-terminalbench-trajectories/` | `yoonholee/terminalbench-trajectories` | Terminal | 213MB | Нет |
| `ibm-research-ITBench-Trajectories/` | `ibm-research/ITBench-Trajectories` | SRE | 165MB | Нет |
| `iMeanAI-Mind2Web-Live/` | `iMeanAI/Mind2Web-Live` | Web Agents | 3.3MB | Нет |
| `AI45Research-ATBench-Claw/` | — | — | — | — |

**Важно:** Who&When — использовать только Hand-Crafted сплит (58 записей). Algorithm-Generated (126) — синтетические, исключены.

### work/

Текущая работа (новый цикл).

| Папка/Файл | Описание |
|-----------|---------|
| `specs/TZ_0.md` | Реструктуризация репозитория (завершено) |
| `specs/TZ_1.md` | Анализ типов ошибок tool call (в работе) |
| `reports/TZ_1_report.md` | Отчёт TZ_1 (в процессе) |
| `scripts/` | Новые скрипты |
| `data/` | Выходные CSV и графики |

### archive/

Старый цикл (ТЗ №1–7). Отклонён Huawei. Хранится как справочный материал.

| Папка | Содержимое |
|-------|-----------|
| `scripts/` | 23 скрипта tz*.py (пути сломаны — запускать нельзя без правки) |
| `specs/` | ТЗ №1.md … ТЗ №7.md |
| `reports/` | Отчёты по фазам 1–7 |
| `data/` | CSV-результаты + графики старого цикла |
| `docs/` | fault_analysis_report.md (ОТКЛОНЁН), methodology.md |

### reference/

Справочные материалы.

| Файл | Описание |
|------|---------|
| `REPOSITORY_MAP.md` | Этот файл |
| `STATS_BOOK_INDEX.md` | Индекс учебника Буре-Парилина — какой параграф решает какую задачу |
| `OCR Методы прикладной Статистики…txt` | Полный текст учебника (OCR, 655K символов) |

### memory/

Персистентная память для Claude Code.

| Файл | Описание |
|------|---------|
| `TZ_STATUS.md` | Статус всех TZ + структура репозитория — читать в начале сессии |
| `MEMORY_INDEX.md` | Индекс memory-файлов |
