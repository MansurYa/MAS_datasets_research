"""ТЗ №5 Часть D — Отчёт на русском."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path
import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "report"

TRAIL_MAPPING_TABLE = [
    ("Context Handling Failures", "kv_cache_loss"),
    ("Resource Abuse", "resource_abuse"),
    ("Timeout Issues", "tool_timeout"),
    ("Service Errors", "system_failure"),
    ("Tool-related (Hallucinations)", "hallucination"),
    ("Language-only (Hallucinations)", "hallucination"),
    ("Poor Information Retrieval", "misinterpretation_of_tool_output"),
    ("Tool Output Misinterpretation", "misinterpretation_of_tool_output"),
    ("Formatting Errors", "code_error"),
    ("Instruction Non-compliance", "instruction_adherence_failure"),
    ("Tool Definition Issues", "invalid_invocation"),
    ("Environment Setup Errors", "invalid_invocation"),
    ("Incorrect Problem Identification", "orchestration_failure"),
    ("Tool Selection Errors", "orchestration_failure"),
    ("Goal Deviation", "orchestration_failure"),
    ("Task Orchestration", "orchestration_failure"),
    ("Rate Limiting", "tool_web_failure"),
    ("Authentication Errors", "tool_web_failure"),
    ("Resource Not Found", "resource_not_found"),
    ("Resource Exhaustion", "resource_abuse"),
    ("Incorrect Memory Usage", "kv_cache_loss"),
]

KEYWORD_RULES_WW = [
    ("hallucination", ["hallucinate", "fabricat", "made up", "assumes the existence", "placeholder"]),
    ("resource_abuse", ["exhaustion of the step limits", "step limit", "too many steps", "repeatedly"]),
    ("orchestration_failure", ["orchestrator", "replan", "wrong direction", "should not decide", "should instruct"]),
    ("tool_web_failure", ["failed to access", "404", " retrieve", "websurfer", "filesurfer", "could not access", "not found", "url", "cloudflare"]),
    ("code_error", ["code is incorrect", "code is wrong", "python code", "incorrect code", "code provided", " bug ", "syntax", "the code is"]),
    ("factual_error", ["factual error", "incorrect information", "incorrect assumption", "incorrect fact", "wrong answer"]),
    ("misinterpretation", ["misinterpret", "misidentif", "incorrect interpretation", "wrong interpretation"]),
]

KEYWORD_SEARCH_RULES = [
    ("tool_timeout", ["timeout", "timed out", "time out", "timeouterror", "deadline exceeded", "request timeout", "operation timed"]),
    ("tool_web_failure", ["404", "403", "500", "502", "503", "connection refused", "connection error", "network error", "failed to connect", "could not connect", "no route to host", "name resolution failed", "dns"]),
    ("resource_not_found", ["filenotfounderror", "no such file", "not found", "does not exist", "cannot find", "path does not exist"]),
    ("permission_error", ["permission denied", "access denied", "permissionerror", "not permitted", "operation not permitted"]),
    ("memory_error", ["out of memory", "oom", "memoryerror", "memory error", "killed", "cannot allocate"]),
]


def fmt(v, d=4):
    if v is None or v == "" or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)


def df_to_md(df, cols=None):
    if cols:
        df = df[cols]
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |",
             "|" + "|".join(["---"] * len(df.columns)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(
            "—" if (v is None or v == "" or (isinstance(v, float) and math.isnan(v))) else str(v)
            for v in row) + " |")
    return "\n".join(lines)


def generate_report():
    df = pd.read_csv(REPORT_DIR / "all_errors_final.csv")
    dist_v2 = pd.read_csv(DATA_DIR / "distributions_v2.csv")
    dist_ext = pd.read_csv(DATA_DIR / "distributions_extended.csv")
    trail_df = pd.read_csv(DATA_DIR / "trail_errors.csv")

    lines = []

    # ── Раздел 1: Введение ────────────────────────────────────────────────────
    lines += [
        "# Анализ ошибок мультиагентных систем: статистическое исследование",
        "",
        "**Дата:** 2026-05-06  ",
        "**Проект:** Huawei × СПбГУ Joint Lab — симулятор динамической доступности LLM-инференса",
        "",
        "## 1. Введение",
        "",
        "Цель исследования — получить статистические параметры ошибок агентных траекторий для двух задач:",
        "1. Задать реалистичные вероятности и распределения момента появления ошибок в симуляторе динамической доступности (IR-граф).",
        "2. Подготовить отчёт для Patent Review Board (PRB) Huawei.",
        "",
        "Исследование охватывает 7 датасетов агентных траекторий из Hugging Face.",
        "Из них 2 содержат явную типизацию ошибок (TRAIL, AgentRx), 1 — свободный текст с причиной ошибки (Who&When),",
        "остальные 4 — только статус выполнения без типизации.",
        "",
        "### Таблица датасетов",
        "",
        "| Датасет | Траекторий | Тип разметки | Что извлечено |",
        "|---|---|---|---|",
        "| TRAIL (Patronus AI) | 147 | Экспертная ручная аннотация (4 эксперта, 4 раунда верификации) | Типы ошибок, позиции (span_id), impact |",
        "| AgentRx (Microsoft) | 73 | Аннотация на уровне шагов | Типы ошибок, номера шагов |",
        "| Who&When Hand-Crafted | 58 | Свободный текст (mistake_reason) | Типы ошибок через keyword matching |",
        "| nebius/SWE-agent | 80 036 | Только exit_status | P(traj) и позиции через keyword search |",
        "| ITBench (IBM) | 105 | Только exit_status | P(traj) и позиции через keyword search |",
        "| TerminalBench | 52 104 | Только exit_status | P(traj) и позиции через keyword search |",
        "| Mind2Web-Live | 542 | Только exit_status | Не использован (нет релевантных ошибок) |",
        "",
    ]

    # ── Раздел 2: Методология ─────────────────────────────────────────────────
    lines += [
        "## 2. Методология",
        "",
        "### 2.1 Определения",
        "",
        "**P(траектория)** — доля траекторий, содержащих хотя бы одно вхождение ошибки данного типа:",
        "P = k / n, где k — число траекторий с ошибкой, n — общее число траекторий в источнике.",
        "",
        "**P(сообщение)** — доля шагов траекторий, содержащих ошибку: P = m / S,",
        "где m — суммарное число шагов с ошибкой, S — суммарное число шагов во всех траекториях источника.",
        "Ограничение: шаги внутри одной траектории не являются независимыми наблюдениями,",
        "поэтому доверительный интервал формально занижен.",
        "",
        "**Wilson 95% доверительный интервал** — интервальная оценка биномиальной пропорции,",
        "устойчивая при малых n и крайних p (в отличие от интервала Вальда):",
        "```",
        "center = (p + z²/(2n)) / (1 + z²/n)",
        "margin = z · √(p(1-p)/n + z²/(4n²)) / (1 + z²/n)",
        "CI = [center − margin, center + margin],  z = 1.96",
        "```",
        "",
        "**Критерий Колмогорова-Смирнова (KS-тест)** — непараметрический тест согласия.",
        "Статистика D = max|F_emp(x) − F_theor(x)|.",
        "Ограничение: при оценке параметров по тем же данным (сложная гипотеза) p-value завышен.",
        "При n >> 3000 мощность теста высока и отвержение H0 информативно.",
        "При n < 100 мощность низка и неотвержение H0 не означает хорошую подгонку.",
        "",
        "**Порог достаточности данных (n ≥ 20)** — минимальное число траекторий с ошибкой",
        "для осмысленной статистики. При n < 20 Wilson CI слишком широк (более 30 п.п.),",
        "подгонка распределений невозможна.",
        "",
        "**Порог надёжной подгонки (n ≥ 3000)** — минимальный объём для уверенных выводов",
        "о виде распределения. При n < 3000 KS-тест не различает распределения;",
        "результаты подгонки носят ориентировочный характер.",
        "",
        "### 2.2 Классы моделируемости",
        "",
        "| Класс | Название | Определение | Пример |",
        "|---|---|---|---|",
        "| 1 | Невозможно моделировать | Воспроизведение ошибки требует полного прогона LLM. Нельзя инжектировать как структурное событие в IR-граф | Галлюцинация, ошибка в коде |",
        "| 2 | Моделируется напрямую | Ошибка воспроизводится изменением параметров или структуры IR-графа без статистических допущений | Потеря KV-кэша, таймаут |",
        "| 3 | Моделируется статистически | Ошибка описывается вероятностью и распределением момента появления. Инжектируется как случайное событие | Resource Abuse, tool_web_failure |",
        "| 4 | Нецелесообразно моделировать | Технически возможно, но выходит за рамки проекта | Деградация оборудования |",
        "",
        "### 2.3 Качество источников данных",
        "",
        "| Категория | Определение | Источники |",
        "|---|---|---|",
        "| Экспертная разметка | Ошибки размечены вручную экспертами на уровне отдельных участков траектории | TRAIL (147 трейсов) |",
        "| Аннотация на уровне шагов | Типы ошибок и номера шагов размечены аннотаторами | AgentRx (73 траектории) |",
        "| Keyword matching | Классификация свободного текста (mistake_reason) по ключевым словам | Who&When HC (58 записей) |",
        "| Keyword search в траекториях | Поиск паттернов ошибок (HTTP-коды, traceback, timeout) в ответах среды выполнения | nebius, ITBench, TerminalBench |",
        "| Нет данных | Теоретическая ошибка без эмпирических наблюдений | 7 ошибок классов 2, 4 |",
        "",
    ]

    # ── Раздел 3: Сводная таблица ─────────────────────────────────────────────
    lines += [
        "## 3. Сводная таблица ошибок",
        "",
        "Таблица сгруппирована по классу моделируемости.",
        "Полная версия с CI и параметрами распределений: `all_errors_final.csv`.",
        "",
    ]

    for mc in [1, 2, 3, 4]:
        mc_names = {1: "Класс 1 — Невозможно моделировать",
                    2: "Класс 2 — Моделируется напрямую",
                    3: "Класс 3 — Моделируется статистически",
                    4: "Класс 4 — Нецелесообразно моделировать"}
        lines.append(f"### {mc_names[mc]}")
        lines.append("")
        sub = df[df["modeling_class"] == mc].copy()
        sub["P(traj)"] = sub["p_trajectory"].apply(lambda x: fmt(float(x), 3) if str(x).replace(".", "").isdigit() else "—")
        sub["CI 95%"] = sub.apply(
            lambda r: f"[{fmt(float(r['p_traj_ci_lower']),3)}, {fmt(float(r['p_traj_ci_upper']),3)}]"
            if str(r["p_traj_ci_lower"]).replace(".", "").isdigit() else "—", axis=1)
        sub["n"] = sub["n_trajectories_with_error"].apply(lambda x: str(int(float(x))) if str(x).replace(".", "").isdigit() else "—")
        sub["Распределение"] = sub.apply(
            lambda r: f"{r['best_distribution']} (p={fmt(float(r['best_dist_ks_p']),3)})"
            if str(r.get("best_distribution", "")).strip() and str(r.get("best_dist_ks_p", "")).replace(".", "").isdigit() else "—", axis=1)
        sub["Графики"] = sub["plots"].apply(lambda x: x if x else "—")
        tbl = sub[["error_id", "name_ru", "source", "n", "P(traj)", "CI 95%", "Распределение", "Графики"]].rename(
            columns={"error_id": "error_id", "name_ru": "Название", "source": "Источник"})
        lines.append(df_to_md(tbl))
        lines.append("")

    # ── Раздел 4: Анализ по классам ───────────────────────────────────────────
    lines += [
        "## 4. Анализ по классам",
        "",
        "### Класс 1 — Невозможно моделировать",
        "",
        "Все ошибки класса 1 являются семантическими: их появление определяется внутренним состоянием",
        "языковой модели в момент генерации. Инжектировать такую ошибку в IR-граф без запуска реального LLM невозможно.",
        "",
        "Ошибки класса 1:",
    ]
    for _, r in df[df["modeling_class"] == 1].drop_duplicates("error_id").iterrows():
        lines.append(f"- **{r['name_ru']}** (`{r['error_id']}`): {r['description_ru']}")
    lines.append("")

    lines += [
        "### Класс 2 — Моделируется напрямую",
        "",
        "Ошибки класса 2 воспроизводятся изменением параметров IR-графа без статистических допущений.",
        "",
    ]
    for eid in df[df["modeling_class"] == 2]["error_id"].unique():
        sub = df[df["error_id"] == eid]
        r = sub.iloc[0]
        lines.append(f"**{r['name_ru']}** (`{eid}`)")
        lines.append(f"> {r['description_ru']}")
        lines.append(f"> Моделирование: {r['modeling_class_reason_ru']}")
        has_data = sub[sub["n_trajectories_with_error"].apply(lambda x: str(x).replace(".", "").isdigit() and float(x) > 0)]
        if len(has_data):
            for _, hr in has_data.iterrows():
                n = int(float(hr["n_trajectories_with_error"]))
                p = fmt(float(hr["p_trajectory"]), 3) if str(hr["p_trajectory"]).replace(".", "").isdigit() else "—"
                lines.append(f"> Данные ({hr['source']}): n={n}, P(traj)={p}")
        else:
            lines.append("> Эмпирических данных нет. Параметры требуют экспертной оценки.")
        lines.append("")

    lines += [
        "### Класс 3 — Моделируется статистически",
        "",
        "Ошибки класса 3 инжектируются как случайные события с вероятностью P(traj) и распределением момента появления.",
        "",
    ]
    for eid in df[df["modeling_class"] == 3]["error_id"].unique():
        sub = df[df["error_id"] == eid]
        r = sub.iloc[0]
        lines.append(f"**{r['name_ru']}** (`{eid}`)")
        lines.append(f"> {r['description_ru']}")
        for _, hr in sub.iterrows():
            n_str = str(hr["n_trajectories_with_error"])
            if n_str.replace(".", "").isdigit() and float(n_str) > 0:
                n = int(float(n_str))
                p = fmt(float(hr["p_trajectory"]), 3) if str(hr["p_trajectory"]).replace(".", "").isdigit() else "—"
                dist = hr.get("best_distribution", "")
                fit = hr.get("fit_conclusion_ru", "")
                lines.append(f"> {hr['source']}: n={n}, P(traj)={p}, лучшее распределение: {dist or '—'} ({fit})")
        lines.append("")

    lines += [
        "### Класс 4 — Нецелесообразно моделировать",
        "",
    ]
    for _, r in df[df["modeling_class"] == 4].drop_duplicates("error_id").iterrows():
        lines.append(f"**{r['name_ru']}** (`{r['error_id']}`): {r['modeling_class_reason_ru']}")
    lines.append("")

    # ── Раздел 5: Распределения ───────────────────────────────────────────────
    lines += [
        "## 5. Результаты подгонки распределений",
        "",
        "Для ошибок классов 2–3 с n ≥ 20. Проверено 8 распределений: Exponential, Weibull, LogNormal, Beta, Uniform, Pareto, Gamma, Lomax.",
        "Параметры оценены методом MLE. KS-тест: H0 — данные соответствуют распределению.",
        "⚠️ При n < 3000 мощность теста низка; результаты носят ориентировочный характер.",
        "",
    ]

    eligible = df[
        df["step_n"].apply(lambda x: str(x).replace(".", "").isdigit() and float(x) >= 20) &
        df["modeling_class"].isin([2, 3])
    ]

    for _, row in eligible.iterrows():
        eid = row["error_id"]
        src = row["source"]
        n = int(float(row["step_n"]))
        name_ru = row["name_ru"]
        lines.append(f"### {name_ru} / {src} (n={n})")
        lines.append("")

        # Descriptive stats
        stats_vals = {
            "mean": row.get("step_mean"), "median": row.get("step_median"),
            "std": row.get("step_std"),
        }
        lines.append(f"Описательная статистика: mean={fmt(float(stats_vals['mean']),1) if str(stats_vals['mean']).replace('.','').lstrip('-').isdigit() else '—'}, "
                     f"median={fmt(float(stats_vals['median']),1) if str(stats_vals['median']).replace('.','').lstrip('-').isdigit() else '—'}, "
                     f"std={fmt(float(stats_vals['std']),1) if str(stats_vals['std']).replace('.','').lstrip('-').isdigit() else '—'}")
        lines.append("")

        # Distribution table
        if "keyword_search" in src:
            ds = src.replace("keyword_search_", "")
            dr = dist_ext[(dist_ext["category"] == eid) & (dist_ext["dataset"] == ds) &
                          (dist_ext["position_type"] == "absolute")]
        else:
            dr = dist_v2[(dist_v2["error_id"] == eid) & (dist_v2["source"] == src) &
                         (dist_v2["position_type"] == "absolute")]

        if len(dr):
            tbl = dr[["distribution", "params", "ks_statistic", "ks_pvalue"]].copy()
            tbl["ks_pvalue"] = tbl["ks_pvalue"].apply(lambda x: fmt(float(x), 4) if pd.notna(x) else "—")
            tbl["ks_statistic"] = tbl["ks_statistic"].apply(lambda x: fmt(float(x), 4) if pd.notna(x) else "—")
            lines.append(df_to_md(tbl))
            lines.append("")

        # Conclusion
        lines.append(f"**Вывод:** {row.get('fit_conclusion_ru', '—')}")
        if str(row.get("best_distribution", "")).strip():
            lines.append(f"Лучшее распределение: **{row['best_distribution']}** (KS p={fmt(float(row['best_dist_ks_p']),4) if str(row.get('best_dist_ks_p','')).replace('.','').isdigit() else '—'})")
            lines.append(f"Параметры: `{row.get('best_dist_params', '—')}`")

        # Plot
        hist_file = f"hist_{eid}_{src}.png"
        if (REPORT_DIR / "plots" / hist_file).exists():
            lines.append(f"\n![{name_ru}](plots/{hist_file})")
        lines.append("")

    # ── Раздел 6: Ограничения ─────────────────────────────────────────────────
    lines += [
        "## 6. Ограничения",
        "",
        "- **TRAIL:** 147 траекторий (1 файл аннотаций повреждён). Малая выборка для подгонки распределений (n < 3000 для всех категорий).",
        "- **Who&When HC:** keyword matching покрывает ~71% записей (17 из 58 не классифицированы).",
        "- **Keyword search:** возможны ложные срабатывания — числа как номера строк кода (resource_not_found), имена классов как ошибки памяти (memory_error).",
        "- **KS-тест:** параметры оценены по тем же данным (сложная гипотеза, §2.2.4 Буре), p-value завышен. Результат не является строгим подтверждением подгонки.",
        "- **P(сообщение):** нарушение независимости шагов внутри траектории — CI формально занижен.",
        "- **Ошибки классов 2, 4 с n=0:** параметры (P_err, D) требуют экспертной оценки или литературных данных.",
        "- **AgentRx:** 334 failures из 73 траекторий — одна траектория может содержать несколько ошибок одного типа.",
        "",
    ]

    # ── Раздел 7: Приложения ──────────────────────────────────────────────────
    lines += [
        "## 7. Приложения",
        "",
        "### 7.1 Маппинг TRAIL категорий на error_id",
        "",
        "| TRAIL категория | error_id |",
        "|---|---|",
    ]
    for trail_cat, eid in TRAIL_MAPPING_TABLE:
        lines.append(f"| {trail_cat} | {eid} |")
    lines.append("")

    lines += [
        "### 7.2 Правила keyword matching для Who&When HC",
        "",
        "| error_id | Ключевые слова |",
        "|---|---|",
    ]
    for eid, kws in KEYWORD_RULES_WW:
        lines.append(f"| {eid} | {', '.join(kws)} |")
    lines.append("")

    lines += [
        "### 7.3 Правила keyword search для nebius/ITBench/TerminalBench",
        "",
        "| error_id | Ключевые слова |",
        "|---|---|",
    ]
    for eid, kws in KEYWORD_SEARCH_RULES:
        lines.append(f"| {eid} | {', '.join(kws)} |")
    lines.append("")

    lines += [
        "### 7.4 Матрица надёжности keyword search",
        "",
        "| Категория | Датасет | Надёжность | Обоснование |",
        "|---|---|---|---|",
        "| tool_web_failure | nebius | Высокая | HTTP-коды в ответах среды однозначны |",
        "| resource_not_found | nebius | Высокая | FileNotFoundError/no such file — специфичные паттерны |",
        "| tool_timeout | itbench | Высокая | timeout/deadline exceeded — специфичные паттерны |",
        "| permission_error | terminalbench | Высокая | permission denied — специфичный паттерн |",
        "| memory_error | terminalbench | Средняя | OOM/killed — возможны ложные срабатывания |",
        "",
    ]

    return "\n".join(lines)


def main():
    report = generate_report()
    path = REPORT_DIR / "fault_analysis_report.md"
    path.write_text(report, encoding="utf-8")
    print(f"Сохранено report/fault_analysis_report.md ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
