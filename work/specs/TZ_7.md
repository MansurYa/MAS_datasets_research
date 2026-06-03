# TZ_7.md

> **Контекст:** Полная реализация `МЕТОДОЛОГИЯ-2.0` (файл `work/specs/МЕТОДОЛОГИЯ-2.0.md`) — математический аппарат проверки согласия данных с теоретическим распределением. Перед написанием кода прочитать `МЕТОДОЛОГИЯ-2.0.md` **целиком** (все 12 секций), включая Quality Gate, 9 защитных механизмов и таблицы квантилей в приложении. Прочитать **также** `work/specs/Исследование_библиотек.md`.

---

## 📁 Входные файлы и ожидаемые артефакты

| Файл | Прочитать | Описание |
|---|---|---|
| `work/specs/МЕТОДОЛОГИЯ-2.0.md` | ✅ Целиком, все секции | Мат. спецификация: формулы, архитектура, QC |
| `work/specs/Исследование_библиотек.md` | ✅ Целиком | Библиотечные источники: scipy, R-pkgs |
| `work/reports/TZ_7_report.md` | **Создать** | Отчёт о выполнении |

| Артефакт | Путь |
|---|---|
| Модули Python | `work/scripts/distribution_validator/*.py` |
| Unit-тесты | `work/scripts/distribution_validator/tests/` |
| Демо-отчёт | `work/docs/distribution_validator/` |
| Демо-график | `work/plots/distribution_validator/` |

---

## 🗂️ Структура модулей

```
work/scripts/distribution_validator/
├── main.py                  # Entry point
├── utils.py                 # Утилиты: проверки, paths, hashing
├── distributions.py          # 12 распределений (11 scipy + 1 loglogistic)
├── ecdf.py                  # ECDF: full, censored KM, DKW CI
├── profile_mle.py            # Profile MLE для 3P (Subtasks A–E)
├── bootstrap.py              # Parametric bootstrap, multi-split, Meinshausen
├── goodness.py               # KS distance computation
├── diagnostics.py            # TOST, Fleming KS, статус-коды
├── select.py                  # Function 1: scale_selector
├── validate.py                # Function 2: validate + Branch A/B/C
├── visualization.py           # Один PNG
├── report.py                  # Аудит-отчёт .md
└── tests/
    ├── test_distributions.py
    ├── test_jittering.py
    ├── test_profile_mle.py
    ├── test_bootstrap.py
    └── test_integration.py
```

---

## 🛠 Задача 1: Перед написанием кода — список соответствий

Выпиши **один список** в следующем формате:

```
Секция МЕТОДОЛОГИЯ → Модуль TZ → Что конкретно реализуется

5.1 (12 распределений) → distributions.py →
5.2 (адаптивный ξ) → select.py →
5.3 (N_max) → select.py →
5.4 (N_min + buffer zone) → select.py →
5.5 (UNDERPOWERED) → select.py →
5.6 (jittering) → utils.py →
5.7 (Profile MLE A–E) → profile_mle.py →
5.8 (Ветвь A) → bootstrap.py + validate.py →
5.9 (Ветвь B) → bootstrap.py + validate.py →
5.10 (Ветвь C TOST) → diagnostics.py + validate.py →
5.11 (Kaplan-Meier) → ecdf.py →
6 (9 защитных механизмов) → распределены по модулям →
8 (scipy constraints + GPL filter) → utils.py →
11 (аудит-отчёт) → report.py →
12 (визуализация) → visualization.py →
4 (Function 1 + Function 2) → select.py + validate.py + main.py →
```

**ЖДИ АППРУВА ПЕРЕД ЛЮБЫМ КОДОМ.** Не пиши ни одной строки кода, пока этот список не согласован.

---

## 🛠 Задача 2: Реализация модулей

Реализуй модули **в порядке зависимостей** (каждый модуль зависит только от предыдущих).

### 2.1. `utils.py` — Утилиты

- `check_scipy_version()` — `assert scipy.__version__ >= "1.11.0"`, выбросить `EnvironmentError` если меньше
- `check_dependency_constraints()` — проверить, что `weibullr`, `envstats`, `gofcens`, `hdi`, `rpy2` не установлены; выбросить `EnvironmentError` если найдены
- `compute_data_hash(X)` — SHA-256 от `np.subplex(X)` (не от float-значений, а от объекта массива)
- `safe_jitter(x, support_lower, delta)` — секция 5.6 МЕТОДОЛОГИИ
- `PLOTS_DIR = work/plots/distribution_validator`
- `DOCS_DIR = work/docs/distribution_validator`
- Создание директорий: `mkdir(parents=True, exist_ok=True)`
- `audit_id()` — `f"audit-{datetime.now():%Y%m%d-%H%M%S}"`

### 2.2. `distributions.py` — 12 распределений

- 11 распределений — scipy.stats wrappers: `weibull_min`, `lognorm`, `gamma`, `norm`, `gumbel_r`, `expon`
- 1 распределение реализуется вручную: `custom_loglogistic(alpha, beta)` — CDF, PPF, rvs
- Для 3P-версий всех распределений — сдвиг `gamma` добавляется в данные перед вызовом scipy, вычитается из PPF-результата

### 2.3. `ecdf.py` — ECDF

- `ecdf_full(X)` — `scipy.stats.ecdf(X)`
- `ecdf_censored(T, event)` — `scipy.stats.CensoredData(uncensored, event).ecdf()`
- `dkw_confidence_interval(ecdf_result)` — `ecdf_result.confidence_interval(method='dkw')`

### 2.4. `profile_mle.py` — Profile MLE (Секция 5.7)

Subtasks по порядку:

- **Subtask A** — предварительная проверка β (линейная регрессия на вейбулловской бумаге). Если β ≤ 1 → `γ_LOCKED_BY_SINGULARITY`, переход к 2P.
- **Subtask B** — сеточный поиск по γ (100 точек, fine grid 201 при Δ_LL > 1.0)
- **Subtask C** — оптимизация Брента по γ (`scipy.optimize.minimize_scalar`, `xtol=1e-10`, `tol_abs=1e-6`, `tol_rel=1e-8`, `max_iter=200`)
- **Subtask D** — внутренний MLE 2P (`scipy.optimize.minimize` с L-BFGS-B, контексты `for_grid`/`for_brent`/`final` с разными `gtol`/`max_iter`)
- **Subtask E** — LRT 2P vs 3P (`scipy.stats.chi2(1).sf(λ)`, df=1, α=0.05)

Возвращает `ProfileMLE_Result` со статус-кодами: `γ_LOCKED_BY_SINGULARITY`, `γ_NOT_SIGNIFICANT`, `γ_MARGINAL`, `γ_NEAR_BOUNDARY`, `DOUBLE_WARNING`, `CONVERGENCE_WARNING`.

### 2.5. `bootstrap.py` — Parametric bootstrap и Meinshausen

- `parametric_bootstrap(X_test, F_frozen, theta, gamma, B=10000)` — генерация через PPF (`dist.ppf(uniform)`), не через `fit()`. Re-fitting параметров — через `scipy.optimize.minimize`.
- `multi_split_K100(X, F_frozen, seed=42)` — 100 сплитов 50/50, `sklearn.utils.resample` или ручной split
- `meinshausen_correction(p_values)` — `min(1, 2 * median(p_values))`
- `skewness_bootstrap(D_boot)` — перцентильная асимметрия, порог |skew| > 0.5

### 2.6. `goodness.py` — Статистические расстояния

- `ks_distance(X_sorted, F0, theta, gamma)` — формула (2.2.2) Буре: `max(|i/N - F0|, |F0 - (i-1)/N|)`
- `kolmogorov_pvalue(D, n)` — `scipy.stats.kstwobign.sf(D * sqrt(n))`

### 2.7. `diagnostics.py` — TOST и Fleming KS

- `tost_check(D_up, epsilon, D_real)` — ACCEPT_EQUIVALENCE если D_up ≤ ε
- `fleming_ks_statistic(T, event, F0, theta)` — модифицированная статистика с Greenwood variance
- `compute_sup_distance_KM(T, event, F0, theta)` — sup |KM_ECDF − F0| в точках t_i, t_i⁻, τ
- `generate_recommendation(margin, censored, n_events)` — таблица секции 5.10

### 2.8. `select.py` — Function 1 (Секция 5.2–5.5)

- `adaptive_xi(X)` — секция 5.2
- `compute_N_max(xi, alpha=0.05)` — секция 5.3, K_0.95 = 1.358
- `compute_N_min(alpha, power, epsilon)` — численный Monte-Carlo с кэшем в `~/.cache/distfit_validator/`. Fallback при N > 3000 — асимптотическая формула. При N < 50 — код UNDERPOWERED.
- `scale_selector(X, epsilon, alpha, power)` — возвращает `(mode, N_min, N_max, xi, recommendations)`. Режимы: `UNDERPOWERED`, `BOOTSTRAP`, `SPLIT_EXACT`, `BIG_DATA`. Буферная зона `[0.8·N_min, 1.2·N_min]` — оба режима возвращаются с пометкой `ZONE_UNCERTAINTY`.

### 2.9. `validate.py` — Function 2 (Секция 5.6–5.11)

Внутреннее ветвление **строго** по секции 4.3 МЕТОДОЛОГИИ:

```
event_mask → Branch C (TOST)
trained_on_same=True → Branch A (Param Bootstrap)
trained_on_same=False, N_test ≤ N_max/2 → Branch B (Multi-split)
trained_on_same=False, N_test > N_max/2 → Branch C (TOST)
```

### 2.10. `visualization.py` — Один PNG (Секция 12)

Одна панель:
- ECDF (step, синяя) + Theoretical CDF (smooth, красная) + PDF overlay
- Shaded diff region — только если D_obs > 0.01
- Max deviation line + annotation с цветовым кодом вердикта
- Для 3P: вертикальная линия γ̂
- Для censored: KM ECDF + DKW CI + маркеры цензурирования
- Для TOST: ε-полоса (CDF ± ε)
- Цветовой код: ACCEPT=зелёный, REJECT=красный, ACCEPT_EQUIVALENCE=жёлтый, UNDERPOWERED=голубой

### 2.11. `report.py` — Аудит-отчёт (Секция 11)

Шаблон секции 11.3.1 МЕТОДОЛОГИИ:
- Все поля из `AuditReport` dataclass
- Таблицы — не текст
- Формулы — только ссылки (Буре §2.2.2, Мейнсхаузен 2009, DKW 1956)
- Decision trace: 5–7 строк максимум
- Рисунок: одна строка с путём
- Путь: `work/docs/distribution_validator/audit-{id}.md`

### 2.12. `main.py` — Entry point

```
main(X, dist_type,
     event_mask=None,
     epsilon=0.03, alpha=0.05, power=0.80,
     do_split=True,
     B=10000,
     seed=42)

Pipeline:
  1. check_scipy_version()
  2. check_dependency_constraints()
  3. compute_data_hash(X)
  4. scale_selector(X, epsilon, alpha, power) → mode
  5. Сплит если нужно → X_fit, X_test
  6. F_frozen = profile_mle(X_fit) если 3P иначе mle_2p(X_fit)
  7. validate(X_test, F_frozen, trained_on_same, N_max, event_mask, epsilon)
  8. plot_fit(report, F_frozen, X_test)
  9. generate_report(report, figure_path)
 10. Вернуть (ValidationResult, plot_path, md_path)
```

CLI-интерфейс: `argparse` с полями `--data`, `--dist`, `--epsilon`, `--alpha`, `--power`, `--fast` (B=1000), `--event-col`, `--time-col`, `--seed`.

---

## 🛑 ЖЁСТКИЕ ОГРАНИЧЕНИЯ

### Данные

1. **`scipy >= 1.11.0` — ПРОВЕРЯТЬ В `utils.py`.** Все функции ECDF, DKW, CensoredData доступны только с этой версии.

2. **Не читать CSV/Parquet целиком в память.** Если файл > 100 MB — chunk reading. Если массив > 1 000 000 элементов — стратифицированный downsampling до 100 000.

3. **`event_mask` — только 0 и 1.** Любое другое значение → `ValueError`.

### Математика

4. **`scipy.stats.fit()` в цикле parametric bootstrap (B > 100) — ЗАПРЕЩЁН.** Причина: GIL делает Python-цикл с `fit()` в 10–100 раз медленнее векторизованного NumPy-подхода. Использовать `dist.ppf(uniform_array)` для генерации псевдовыборок. Для разовых MLE-вызовов (Profile MLE, Subtask D) — `scipy.stats.fit()` **разрешён**.

5. **Loglogistic — только из `distributions.py`.** Не использовать `scipy.stats.genlogistic` (это обобщённое логистическое, формула CDF отличается).

6. **R-пакеты (WeibullR, EnvStats, GofCens, hdi) — не являются зависимостями проекта.** Их исходный код и статьи — **документация** для реализации формул вручную. Пакет `rpy2` — запрещён.

7. **`check_dependency_constraints()` — выбросить `EnvironmentError`** если любой из запрещённых пакетов обнаружен через `importlib.metadata`.

### Вычисления

8. **Monte-Carlo N_min — кэшировать.** Файл `~/.cache/distfit_validator/n_barriers_cache.json`. Хэш-ключ: `SHA256(f"{epsilon:.6f}{alpha:.6f}{power:.6f}")`. Fallback: in-memory dict при `PermissionError`.

9. **Seed — воспроизводимость.** Все рандомизированные операции принимают `seed`. По умолчанию `seed=42`.

### Архитектура

10. **Глобальные переменные — запрещены.** Все состояние — через dataclass-аргументы.

11. **Никаких параллельных субагентов** (subagents). Последовательная реализация модулей.

12. **Логирование — `logging`, не `print`.** INFO для основных шагов, DEBUG для численных итераций.

---

## 🧪 Задача 3: Тестирование

Писать тесты **после каждого модуля**, запускать **сразу**:

### 3.1. `test_distributions.py` — после `distributions.py`

- Симулировать по 1000 точек из каждого из 12 распределений
- Round-trip: CDF → PPF → rvs → проверить совпадение с исходными (относительная ошибка < 1%)
- Edge cases loglogistic: PPF при u = 0.0001 и u = 0.9999 (не падает, значения конечны)

### 3.2. `test_jittering.py` — после `utils.py`

- 1000 точек, 10 применений jittering
- Проверить: все значения ≥ support_lower + delta

### 3.3. `test_profile_mle.py` — после `profile_mle.py`

- Симулировать Weibull_3P(α=1000, β=1.5, γ=100), N=500
- Сравнить оценки с истинными параметрами (относительная ошибка < 10%)
- Проверить `γ_LOCKED_BY_SINGULARITY` при β=0.5
- Проверить `γ_NOT_SIGNIFICANT` при γ=0

### 3.4. `test_bootstrap.py` — после `bootstrap.py`

- Симулировать Weibull_2P(α=1000, β=1.5), N=200, B=10000
- **1000 симуляций** (не 100!). Для набора {p₁..p₁₀₀₀} вычислить: доля p < 0.05. Должна быть ∈ [3%, 7%]. Если < 3% или > 7% — FAIL. Это проверяет, что bootstrap не систематически занижает p-value.
- Проверить: Meinshausen correction при K=100 не меняет долю < 5% систематически

### 3.5. `test_integration.py` — после `main.py`

- Симулировать Weibull_3P(α=4247, β=1.31, γ=1240), N=847
- Должен выдать ACCEPT с p_final > 0.05
- Должен сгенерировать PNG и MD без ошибок
- PNG читаем: файл существует, размер > 10 KB
- MD читаем: содержит "ACCEPT", содержит путь к PNG, содержит D_obs, p_final

Запуск: `pytest work/scripts/distribution_validator/tests/ -v`.

---

## 🚀 Запуск

```bash
# Базовый
python main.py \
    --data work/data/sample_trajectories.csv \
    --dist W3 \
    --epsilon 0.03

# Быстрый (B=1000)
python main.py --data work/data/sample.csv --dist LN2 --fast

# С цензурированными данными
python main.py \
    --data work/data/sample.csv \
    --dist W3 \
    --event-col event_status \
    --time-col duration

# Выход:
#   work/docs/distribution_validator/audit-{timestamp}-{dist}-N{...}-{verdict}.md
#   work/plots/distribution_validator/audit-{timestamp}-{dist}-N{...}-{verdict}.png
```

---

<sub-instruction>

**ПЛАН РЕАЛИЗАЦИИ:**

1. **Прочитай** `МЕТОДОЛОГИЯ-2.0.md` целиком. Выпиши список секция → модуль → что делает.
2. **Покажи мне** этот список. ЖДИ АППРУВА.
3. После аппрува — реализуй модули **в порядке**: `utils.py` → `distributions.py` → `ecdf.py` → `profile_mle.py` → `bootstrap.py` → `goodness.py` → `diagnostics.py` → `select.py` → `validate.py` → `visualization.py` → `report.py` → `main.py`.
4. После каждого модуля — его тесты, сразу запускать.
5. После `main.py` — `test_integration.py` + демо-запуск.
6. После демо-запуска — написать `work/reports/TZ_7_report.md`.

**Принцип:** один модуль → его тесты → следующий. НЕ писать всё сразу.

</sub-instruction>

---

# work/reports/TZ_7_report.md

# TZ_7: Отчёт о реализации МЕТОДОЛОГИЯ-2.0

> **Цель отчёта:** Показать, что каждое требование TZ_7 выполнено, и читатель может в этом убедиться сам, пройдясь по артефактам.

---

## 1. Предварительные требования

### 1.1. Документы прочитаны

| Документ | Прочитан | Доказательство |
|---|---|---|
| `МЕТОДОЛОГИЯ-2.0.md` | [ ] | Указать номера секций, которые использованы |
| `Исследование_библиотек.md` | [ ] | Указать блоки, которые использованы |

### 1.2. Структура модулей

Проверить: `work/scripts/distribution_validator/` содержит все файлы:

```
[ ] main.py
[ ] utils.py
[ ] distributions.py
[ ] ecdf.py
[ ] profile_mle.py
[ ] bootstrap.py
[ ] goodness.py
[ ] diagnostics.py
[ ] select.py
[ ] validate.py
[ ] visualization.py
[ ] report.py
[ ] tests/test_distributions.py
[ ] tests/test_jittering.py
[ ] tests/test_profile_mle.py
[ ] tests/test_bootstrap.py
[ ] tests/test_integration.py
```

---

## 2. Соответствие секция → модуль

Каждая строка ниже должна быть проверена по коду:

| Секция МЕТОДОЛОГИЯ | Модуль TZ | Проверено |
|---|---|---|
| 5.1 — 12 распределений | `distributions.py` | [ ] |
| 5.2 — адаптивный ξ | `select.py` | [ ] |
| 5.3 — N_max | `select.py` | [ ] |
| 5.4 — N_min + buffer zone | `select.py` | [ ] |
| 5.5 — UNDERPOWERED 4 сценария | `select.py` | [ ] |
| 5.6 — jittering | `utils.py` | [ ] |
| 5.7 — Profile MLE A–E | `profile_mle.py` | [ ] |
| 5.8 — Ветвь A | `bootstrap.py` + `validate.py` | [ ] |
| 5.9 — Ветвь B | `bootstrap.py` + `validate.py` | [ ] |
| 5.10 — Ветвь C TOST | `diagnostics.py` + `validate.py` | [ ] |
| 5.11 — Kaplan-Meier ECDF | `ecdf.py` | [ ] |
| 8 — scipy constraints + GPL | `utils.py` (check_dependency_constraints) | [ ] |
| 11 — аудит-отчёт | `report.py` | [ ] |
| 12 — визуализация | `visualization.py` | [ ] |

---

## 3. ЖЁСТКИЕ ОГРАНИЧЕНИЯ — проверка по коду

Для каждого ограничения указать конкретную строку кода:

| Ограничение | Файл:строка | Как проверено |
|---|---|---|
| 1. scipy >= 1.11.0 | [ ]:[ ] | [ ] |
| 2. Chunk reading > 100MB | [ ]:[ ] | [ ] |
| 3. event_mask только 0/1 | [ ]:[ ] | [ ] |
| 4. fit() в цикле bootstrap — ЗАПРЕЩЁН | [ ]:[ ] | [ ] |
| 5. Loglogistic — только из distributions.py | [ ]:[ ] | [ ] |
| 6. R-пакеты не являются зависимостями | [ ]:[ ] | [ ] |
| 7. check_dependency_constraints() | [ ]:[ ] | [ ] |
| 8. Кэш N_min в ~/.cache/ | [ ]:[ ] | [ ] |
| 9. Seed во всех рандомизированных операциях | [ ]:[ ] | [ ] |
| 10. Глобальные переменные — запрещены | [ ]:[ ] | [ ] |
| 11. Никаких параллельных субагентов | N/A (архитектурное) | [ ] |
| 12. logging, не print | [ ]:[ ] | [ ] |

---

## 4. Тесты — результаты

Запустить `pytest work/scripts/distribution_validator/tests/ -v` и записать результат:

### 4.1. test_distributions.py

```
$ pytest tests/test_distributions.py -v
[РЕЗУЛЬТАТ ВСТАВИТЬ]
Все 12 распределений — round-trip ошибка < 1%: [ПРОШЁЛ / НЕ ПРОШЁЛ]
Edge cases loglogistic: [ПРОШЁЛ / НЕ ПРОШЁЛ]
```

### 4.2. test_jittering.py

```
$ pytest tests/test_jittering.py -v
Все значения ≥ support_lower + delta: [ПРОШЁЛ / НЕ ПРОШЁЛ]
```

### 4.3. test_profile_mle.py

```
$ pytest tests/test_profile_mle.py -v
Weibull_3P(1000, 1.5, 100), N=500, ошибка < 10%: [ПРОШЁЛ / НЕ ПРОШЁЛ]
β=0.5 → γ_LOCKED_BY_SINGULARITY: [ПРОШЁЛ / НЕ ПРОШЁЛ]
γ=0 → γ_NOT_SIGNIFICANT: [ПРОШЁЛ / НЕ ПРОШЁЛ]
```

### 4.4. test_bootstrap.py (КРИТИЧЕСКИЙ)

```
$ pytest tests/test_bootstrap.py -v
1000 симуляций Weibull_2P(1000, 1.5), N=200
Доля p < 0.05 ∈ [3%, 7%]: [РЕЗУЛЬТАТ ВСТАВИТЬ]
Meinshausen correction не систематична: [ПРОШЁЛ / НЕ ПРОШЁЛ]
```

### 4.5. test_integration.py (ФИНАЛЬНЫЙ)

```
$ pytest tests/test_integration.py -v
ACCEPT с p_final > 0.05: [ПРОШЁЛ / НЕ ПРОШЁЛ]
PNG сгенерирован: [ПУТЬ ВСТАВИТЬ], размер > 10 KB: [ДА / НЕТ]
MD сгенерирован: [ПУТЬ ВСТАВИТЬ]
MD содержит "ACCEPT": [ДА / НЕТ]
MD содержит путь к PNG: [ДА / НЕТ]
MD содержит D_obs и p_final: [ДА / НЕТ]
```

---

## 5. Демо-запуск

```bash
python main.py --data work/data/sample.csv --dist W3 --epsilon 0.03 --seed 42

Отчёт: [ПУТЬ К СГЕНЕРИРОВАННОМУ .md ФАЙЛУ]
График: [ПУТЬ К СГЕНЕРИРОВАННОМУ .png ФАЙЛУ]
```

**Проверить глазами:**
- [ ] PNG читается за 10 секунд — данные визуально на кривой?
- [ ] ECDF (синяя) близка к CDF (красная)?
- [ ] D_obs < ε?
- [ ] Вердикт в MD совпадает с ожидаемым?

---

## 6. Соответствие с Quality Gate МЕТОДОЛОГИЯ-2.0

| Критерий из Quality Gate | Выполнен | Доказательство |
|---|---|---|
| Все формулы верифицированы перерасчётом | [ ] | Указать где проверено |
| N_max явно в интерфейсе Function 2 | [ ] | Файл:строка |
| Jittering с защитой области определения | [ ] | Файл:строка |
| Censored data → KM → TOST | [ ] | Файл:строка |
| 4 сценария UNDERPOWERED документированы | [ ] | Файл:строка |
| Profile MLE: все этапы с fallback | [ ] | Файл:строка |
| Model selection: LRT | [ ] | Файл:строка |
| Convergence warning в RESULT dataclass | [ ] | Файл:строка |
| Skewness threshold обоснован | [ ] | Файл:строка |
| Buffer zone [0.8·N_min, 1.2·N_min] | [ ] | Файл:строка |

---

## 7. Итоговая таблица

| Параграф TZ | Статус | Комментарий |
|---|---|---|
| 1. Документы прочитаны | [ ] / [ ] | |
| 2. Все 14 модулей созданы | [ ] / [ ] | |
| 3. Все 12 жёстких ограничений проверены | [ ] / [ ] | |
| 4. Все 5 тестов проходят | [ ] / [ ] | |
| 5. Демо-запуск успешен | [ ] / [ ] | |
| 6. Quality Gate покрыт | [ ] / [ ] | |
| **ИТОГО** | **N / 6** | |

---