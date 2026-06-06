# MAS_errors Pipeline: Подробный План Решения

> **Дата:** 2026-06-06
> **Статус:** ПЛАНИРОВАНИЕ (не имплементация)
> **Основание:** Пользователь запросил план до имплементации

---

## Фаза 0: Исправление Критического бага TRAIL Parser

### Задача 0.1: Исправить TRAIL parser
**Файл:** `work/MAS_errors/parsers/trail/parser.py`
**Баг:** Строка 89 — `step_idx=0` жестко закодирован для всех записей

**Решение:**
```python
def flatten_spans(spans, step_idx_start=0):
    """Recursively flatten spans including nested child_spans."""
    flat = []
    for i, span in enumerate(spans):
        flat.append((step_idx_start + i, span.get('span_id')))
        if 'child_spans' in span and span['child_spans']:
            child_flat = flatten_spans(span['child_spans'], step_idx_start + len(spans))
            flat.extend(child_flat)
    return flat

def get_step_idx(trace, location):
    """Extract step_idx from span_id location."""
    flat_spans = flatten_spans(trace.get('spans', []))
    span_id_to_step = {span_id: idx for idx, span_id in flat_spans}
    return span_id_to_step.get(location, 0)
```

### Задача 0.2: Перезапустить TRAIL исследования
```bash
cd work/MAS_errors
python -m study_runner.run_study --dataset trail --rerun
```

### Задача 0.3: Проверить исчезновение коллизий
```python
# Проверить что data_hash коллизии исчезли
# Ожидаемое: 52 коллизии → 0 коллизий
```

---

## Фаза 1: Миграция недостающих типов ошибок

### Gap Analysis (по результатам исследования)

#### Типы из archive, отсутствующие в current (18):
```
hardware_degradation        - теоретическая (категория 4)
gpu_throttling             - теоретическая (категория 4)
correlated_ssd_failure     - теоретическая (категория 4)
network_power_failure      - теоретическая (категория 4)
bad_retry_policy           - теоретическая (категория 2)
kv_transfer_failure        - теоретическая (категория 2)
memory_bandwidth_bottleneck - теоретическая (категория 2)
underspecified_user_intent - tau_retail (категория 1)
factual_error              - who_and_when_hc (категория 1)
hallucination              - trail, who_and_when_hc (категория 1)
orchestration_failure      - trail, who_and_when_hc (категория 1)
tool_timeout               - keyword_search_itbench (категория 3)
tool_web_failure           - keyword_search_nebius, who_and_when_hc
```

**Примечание:** Часть этих типов — теоретические (категория 4) или не моделируемые (категория 1). Решение: пометить их как "не требуют исследования" в метаданных.

#### Новые типы в current, отсутствующие в archive (17):
```
code_execution              - новая категория (nebius)
authentication_errors        - новая (trail)
context_handling_failures   - новая (trail)
environment_setup_errors    - новая (trail)
formatting_errors           - новая (trail)
goal_deviation              - новая (trail)
incorrect_problem_identification - новая (trail)
instruction_noncompliance   - новая (trail)
language_only               - новая (trail)
poor_information_retrieval  - новая (trail)
resource_exhaustion         - новая (trail)
service_errors              - новая (trail)
task_orchestration          - новая (trail)
task_orchestration_errors   - новая (trail)
timeout_issues              - новая (trail)
tool_definition_issues      - новая (trail)
tool_selection              - новая (trail)
processing_error            - новая (who_and_when)
tool_failure                - новая (who_and_when)
wrong_reasoning             - новая (who_and_when)
```

### Задача 1.1: Создать скрипт проверки миграции
**Файл:** `work/scripts/check_migration_coverage.py`

```python
"""
Скрипт для проверки покрытия миграции.
Сравнивает archive/data/errors_stats.csv с текущими результатами.
"""
import pandas as pd
from pathlib import Path

# Load data
archive = pd.read_csv("archive/data/errors_stats.csv")
current = pd.read_csv("work/MAS_errors/results.csv")

# Extract unique (error_type, source) from archive
archive_errors = set(zip(archive['error_id'], archive['source']))

# Extract unique (error_type, dataset) from current
current_errors = set()
for study_id in current['study_id']:
    parts = study_id.split('_')
    # Parse: dataset_errorType_errorSubtype_...
    ...

# Find missing
missing = archive_errors - current_errors
extra = current_errors - archive_errors

print(f"Missing from current: {len(missing)}")
print(f"Extra in current: {len(extra)}")
```

### Задача 1.2: Запустить check_migration_coverage.py
```bash
python work/scripts/check_migration_coverage.py
```

### Задача 1.3: Доработать парсеры для недостающих типов
1. **tool_timeout (ITBench)** — keyword search парсер
2. **tool_web_failure (Nebius)** — keyword search парсер  
3. **hallucination, orchestration_failure (Who&When)** — аннотации HC

---

## Фаза 2: Генерация гистограмм для UNDERPOWERED

### Current State
- UNDERPOWERED статусы НЕ генерируют PNG
- Правило "один study = один график" нарушено

### Задача 2.1: Модифицировать run_study.py
**Файл:** `work/MAS_errors/study_runner/run_study.py`

Найти условие генерации PNG и убрать проверку на UNDERPOWERED:
```python
# Было:
if status != "UNDERPOWERED":
    save_histogram(data, output_path)

# Стало:
save_histogram(data, output_path)  # Всегда генерируем
if status == "UNDERPOWERED":
    add_watermark(fig, "UNDERPOWERED: insufficient data for statistical test")
```

### Задача 2.2: Проверить все UNDERPOWERED исследования
```bash
python -c "
import pandas as pd
df = pd.read_csv('work/MAS_errors/results.csv')
underpowered = df[df['status'] == 'UNDERPOWERED']
print(f'UNDERPOWERED: {len(underpowered)}')
for sid in underpowered['study_id']:
    png_path = f'work/MAS_errors/{sid}.png'
    print(f'{sid}: exists={png_path.exists()}')
"
```

---

## Фаза 3: Расширение results.csv

### Current State
- `results.csv` содержит 15 колонок
- `archive/errors_stats.csv` содержит 26 колонок

### Задача 3.1: Добавить metadata fields
**Файл:** `work/MAS_errors/study_runner/run_study.py`

Добавить в results.csv колонки:
```python
ADDITIONAL_COLUMNS = [
    'dataset',           # nebius, agentRx, trail, etc.
    'error_type',        # основной тип
    'error_subtype',     # подтип
    'analysis_variable', # step_idx, chars_before_error
    'de_duplicated',     # True/False
    'n_errors',          # число ошибок
    'n_trajectories',    # число траекторий
    'mean',              # среднее
    'std',               # стандартное отклонение
    'p25',               # 25th percentile
    'p50',               # 50th percentile (median)
    'p75',               # 75th percentile
    'p90',               # 90th percentile
    'p95',               # 95th percentile
    'p99',               # 99th percentile
]
```

### Задача 3.2: Генерировать percentile statistics
**Файл:** `work/MAS_errors/study_runner/run_study.py`

```python
def compute_percentiles(data):
    """Compute percentile statistics for the data."""
    import numpy as np
    p = np.percentile(data, [25, 50, 75, 90, 95, 99])
    return {
        'p25': p[0],
        'p50': p[1],
        'p75': p[2],
        'p90': p[3],
        'p95': p[4],
        'p99': p[5],
    }
```

---

## Фаза 4: Улучшение audit_report.md

### Current State (по результатам исследования)
Текущий шаблон содержит:
- Dataset, Error Type, Error Subtype, Subgroup, Analysis Variable, De-duplicated
- Status, Best Distribution, p-value, D-statistic, Errors, Attempts, Duration
- Attempts Log

### Missing Fields
| Поле | Описание |
|------|----------|
| `N_total` | Total sample size |
| `N_fit / N_test` | Training/test set sizes |
| `epsilon` | Engineering tolerance (default: 0.03) |
| `alpha` | Significance level (default: 0.05) |
| `branch` | A_BOOTSTRAP / B_SPLIT / C_TOST |
| `figure_path` | Path to PNG visualization |
| `data_hash` | Full SHA-256 hash |
| `parameters` | Fitted distribution parameters |
| `skewness` | Bootstrap skewness |
| `warnings` | List of warnings |

### Задача 4.1: Расширить шаблон audit_report.md
**Файл:** `work/MAS_errors/study_runner/run_study.py`, функция `save_artefacts()`

```markdown
# Audit Report: {study_id}

## Metadata
- **Dataset:** {dataset}
- **Error Type:** {error_type}
- **Error Subtype:** {error_subtype}
- **Subgroup:** {subgroup}
- **Analysis Variable:** {analysis_variable}
- **De-duplicated:** {de_duplicated}

## Methodology
- **Branch:** {branch} (A_BOOTSTRAP/B_SPLIT/C_TOST)
- **Alpha:** {alpha}
- **Epsilon:** {epsilon}
- **N_total:** {n_total}
- **N_fit:** {n_fit}
- **N_test:** {n_test}

## Results
- **Status:** {status}
- **Best Distribution:** {best_dist}
- **p-value:** {p_value}
- **D-statistic:** {D_statistic}
- **Errors:** {n_errors}
- **Attempts:** {n_attempts}
- **Duration:** {duration_s}s

## Data Summary
- **Min:** {min}
- **Max:** {max}
- **Mean:** {mean}
- **Std:** {std}
- **Percentiles:** p25={p25}, p50={p50}, p75={p75}

## Distribution Parameters
{params_table}

## Attempts Log
{attempts_table}

## Visualization
![Histogram]({figure_path})

## Quality Assurance
- **Data Hash:** {data_hash}
- **Skewness:** {skewness}
- **Warnings:** {warnings}
```

### Задача 4.2: Организовать файлы по структуре
```
work/MAS_errors/
  parsers/
    nebius/
      invalid_invocation/
        ALL/
          audit_report.md
          fit_log.json
          histogram.png
    agentRx/
      magentic_one/
        guardrails_triggered/
          audit_report.md
          ...
```

---

## Фаза 5: Улучшение PNG файлов

### Current State
PNG содержат только study_id в заголовке

### Задача 5.1: Расширить заголовок PNG
**Файл:** `work/MAS_errors/visualization/histogram.py`

```python
def save_histogram(data, output_path, metadata):
    """Save histogram with extended metadata in title."""
    fig, ax = plt.subplots()
    
    title = (
        f"{metadata['dataset']} / {metadata['error_type']} / {metadata['error_subtype']}\n"
        f"Variable: {metadata['analysis_variable']} | Dedup: {metadata['de_duplicated']}\n"
        f"Status: {metadata['status']} | Distribution: {metadata['best_dist']}\n"
        f"n_errors={metadata['n_errors']} | D={metadata['D_statistic']}"
    )
    ax.set_title(title, fontsize=10)
    
    # Add UNDERPOWERED watermark if applicable
    if metadata['status'] == 'UNDERPOWERED':
        ax.text(0.5, 0.5, 'UNDERPOWERED',
                transform=ax.transAxes, fontsize=40,
                color='gray', alpha=0.3,
                ha='center', va='center')
```

---

## Фаза 6: HTML отчёт

### Задача 6.1: Создать генератор HTML отчёта
**Файл:** `work/scripts/generate_html_report.py`

```python
"""
Генератор HTML отчёта для просмотра всех исследований.
"""
import pandas as pd
from pathlib import Path

def generate_html_report(results_csv, output_html):
    """Generate HTML report from results.csv."""
    df = pd.read_csv(results_csv)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MAS_errors Results</title>
        <style>
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #4CAF50; color: white; }
            tr:nth-child(even) { background-color: #f2f2f2; }
            .ACCEPT { color: green; }
            .REJECT { color: red; }
            .UNDERPOWERED { color: orange; }
        </style>
    </head>
    <body>
        <h1>MAS_errors Pipeline Results</h1>
        <p>Total studies: {n_studies}</p>
        <table>
            <tr>
                <th>Study ID</th>
                <th>Dataset</th>
                <th>Error Type</th>
                <th>Status</th>
                <th>Best Dist</th>
                <th>n_errors</th>
                <th>D-stat</th>
            </tr>
    """.format(n_studies=len(df))
    
    for _, row in df.iterrows():
        html += f"""
            <tr>
                <td>{row['study_id']}</td>
                <td>{row.get('dataset', 'N/A')}</td>
                <td>{row.get('error_type', 'N/A')}</td>
                <td class="{row['status']}">{row['status']}</td>
                <td>{row['best_dist']}</td>
                <td>{row['errors']}</td>
                <td>{row['D_statistic']:.4f}</td>
            </tr>
        """
    
    html += """
        </table>
    </body>
    </html>
    """
    
    with open(output_html, 'w') as f:
        f.write(html)

if __name__ == "__main__":
    generate_html_report(
        "work/MAS_errors/results.csv",
        "work/MAS_errors/results.html"
    )
```

### Задача 6.2: Запустить генератор
```bash
python work/scripts/generate_html_report.py
```

---

## Приоритет задач

| # | Задача | Приоритет | effort | Критичность |
|---|--------|-----------|--------|--------------|
| 0.1 | Исправить TRAIL parser (step_idx) | 1 | 2h | КРИТИЧЕСКИЙ |
| 0.2 | Перезапустить TRAIL исследования | 1 | 30min | КРИТИЧЕСКИЙ |
| 1.1 | Создать check_migration_coverage.py | 2 | 2h | Высокая |
| 1.2 | Запустить check и определить gap | 2 | 1h | Высокая |
| 2.1 | UNDERPOWERED генерируют PNG | 3 | 1h | Средняя |
| 3.1 | Добавить metadata в results.csv | 4 | 2h | Средняя |
| 3.2 | Генерировать percentile statistics | 4 | 2h | Средняя |
| 4.1 | Расширить audit_report.md | 5 | 3h | Средняя |
| 4.2 | Организовать файлы | 5 | 2h | Средняя |
| 5.1 | Расширить заголовок PNG | 6 | 1h | Низкая |
| 6.1 | Создать генератор HTML | 6 | 3h | Средняя |

---

## Ресурсы

### Исследования субагентов
- `memory/research/archive_parser_analysis.md` — полная структура errors_stats.csv
- `memory/research/audit_report_structure.md` — структура audit_report.md
- `memory/research/png_generation_analysis.md` — генерация PNG
- `memory/research/migration_gap_analysis.md` — gap analysis

### Ключевые файлы
- `work/MAS_errors/parsers/trail/parser.py` — TRAIL parser
- `work/MAS_errors/study_runner/run_study.py` — генерация отчётов
- `work/MAS_errors/visualization/` — код визуализации
- `work/MAS_errors/schemas.py` — схемы данных

### Архивные референсы
- `archive/data/errors_stats.csv` — 46 строк типизированных ошибок
- `archive/scripts/tz5_*.py` — генерация графиков
- `archive/data/plots/` — архивные PNG