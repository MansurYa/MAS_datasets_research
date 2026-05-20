"""ТЗ №4.8 Часть D — Финальная сводная таблица и отчёт."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
TRAIL_DIR = ROOT / "TRAIL"

# ── Modeling class definitions ───────────────────────────────────────────────
MODELING_CLASS = {
    "hallucination":                   (1, "Требует воспроизведения LLM-рассуждений"),
    "factual_error":                   (1, "Требует воспроизведения LLM-рассуждений"),
    "instruction_adherence_failure":   (1, "Требует воспроизведения LLM-рассуждений"),
    "misinterpretation":              (1, "Требует воспроизведения LLM-рассуждений"),
    "intent_plan_misalignment":        (1, "Требует воспроизведения LLM-рассуждений"),
    "underspecified_user_intent":      (1, "Требует воспроизведения LLM-рассуждений"),
    "intent_not_supported":            (1, "Требует воспроизведения LLM-рассуждений"),
    "invention_of_new_information":   (1, "Требует воспроизведения LLM-рассуждений"),
    "kv_cache_loss":                   (2, "Известно как моделировать через IR-блок"),
    "tool_timeout":                    (3, "Статистическое: задаётся распределением"),
    "tool_web_failure":                (3, "Статистическое: задаётся распределением"),
    "resource_not_found":              (3, "Статистическое: задаётся распределением"),
    "resource_abuse":                  (3, "Статистическое: задаётся распределением"),
    "permission_error":                (3, "Статистическое: задаётся распределением"),
    "memory_error":                    (3, "Статистическое: задаётся распределением"),
    "code_error":                      (3, "Статистическое: задаётся распределением"),
    "orchestration_failure":           (3, "Статистическое: задаётся распределением"),
    "misinterpretation_of_tool_output":(3, "Статистическое: задаётся распределением"),
    "guardrails_triggered":            (3, "Статистическое: задаётся распределением"),
    "system_failure":                  (3, "Статистическое: задаётся распределением"),
    "invalid_invocation":              (3, "Статистическое: задаётся распределением"),
    "bad_retry_policy":                (3, "Статистическое: задаётся распределением"),
    "kv_transfer_failure":            (3, "Статистическое: задаётся распределением"),
    "memory_bandwidth_bottleneck":     (2, "Моделируется через параметры блока"),
    "hardware_degradation":            (4, "Нецелесообразно для данного симулятора"),
    "gpu_throttling":                  (4, "Нецелесообразно для крупных кластеров"),
    "correlated_ssd_failure":          (4, "Нецелесообразно для данного симулятора"),
    "network_power_failure":           (4, "Нецелесообразно для данного симулятора"),
}

# ── Data quality by source ───────────────────────────────────────────────────
SOURCE_QUALITY = {
    "trail":                          "high",
    "keyword_search_nebius":          "high",
    "keyword_search_itbench":         "high",
    "keyword_search_terminalbench":   "medium",
    "magentic_one":                   "medium",
    "tau_retail":                     "medium",
    "who_and_when_hc":               "medium",
}

# ── Name/description in Russian ───────────────────────────────────────────────
NAME_RU = {
    "kv_cache_loss":                  "Потеря KV-кэша",
    "tool_timeout":                   "Таймаут вызова инструмента",
    "tool_web_failure":               "Сбой доступа к веб-ресурсу",
    "resource_not_found":             "Ресурс не найден",
    "resource_abuse":                 "Избыточное потребление ресурсов",
    "permission_error":               "Ошибка доступа",
    "memory_error":                   "Ошибка памяти (OOM)",
    "code_error":                     "Ошибка в коде",
    "instruction_adherence_failure":  "Несоблюдение инструкций",
    "hallucination":                  "Галлюцинация",
    "orchestration_failure":          "Сбой оркестрации",
    "misinterpretation_of_tool_output": "Неверная интерпретация результата",
    "guardrails_triggered":           "Срабатывание защитных ограничений",
    "factual_error":                   "Фактическая ошибка",
    "system_failure":                 "Системный сбой",
    "invalid_invocation":             "Некорректный вызов инструмента",
    "misinterpretation":              "Неверная интерпретация",
    "intent_plan_misalignment":       "Несоответствие намерения и плана",
    "invention_of_new_information":   "Изобретение информации",
    "intent_not_supported":           "Неподдерживаемое намерение",
    "underspecified_user_intent":     "Недоопределённое намерение",
    "bad_retry_policy":               "Неверная политика повторов",
    "kv_transfer_failure":            "Сбой передачи KV-кэша",
    "memory_bandwidth_bottleneck":    "Узкое место по пропускной способности памяти",
    "hardware_degradation":            "Деградация оборудования",
    "gpu_throttling":                 "Троттлинг GPU",
    "correlated_ssd_failure":          "Коррелированные сбои SSD",
    "network_power_failure":          "Сетевые и power-сбои",
}

DESC_RU = {
    "kv_cache_loss":                  "Потеря кэша ключей-значений после перезапуска модуля или вытеснения из памяти GPU",
    "tool_timeout":                   "Внешний инструмент или shell-команда не ответили за отведённое время",
    "tool_web_failure":               "HTTP-ошибка при обращении к внешнему API или веб-сервису",
    "resource_not_found":             "Файл, директория или запрашиваемый ресурс не существует в среде выполнения",
    "resource_abuse":                 "Исчерпание лимита шагов, зацикливание агента, чрезмерное потребление ресурсов",
    "permission_error":              "Отказ в доступе к файлу, директории или сервису из-за недостаточных прав",
    "memory_error":                   "Нехватка оперативной памяти при выполнении вычислительной задачи",
    "code_error":                     "Агент сгенерировал синтаксически или логически неверный код",
    "instruction_adherence_failure":  "Агент не выполнил инструкцию оркестратора или пользователя",
    "hallucination":                  "Агент выдумал факты, данные или ссылки",
    "orchestration_failure":          "Неверная маршрутизация задачи, ошибочное решение о следующем шаге",
    "misinterpretation_of_tool_output": "Агент неправильно понял вывод инструмента",
    "guardrails_triggered":           "Внешний сервис заблокировал запрос агента",
    "factual_error":                  "Агент использовал неверные факты из своих знаний",
    "system_failure":                 "Критический сбой инфраструктуры выполнения",
    "invalid_invocation":             "Агент вызвал инструмент с неверными параметрами",
    "misinterpretation":              "Агент неправильно истолковал входные данные",
    "intent_plan_misalignment":       "Агент составил план не соответствующий задаче",
    "invention_of_new_information":   "Агент выдумал данные, которых не было в источниках",
    "intent_not_supported":           "Агент не способен выполнить запрошенное действие",
    "underspecified_user_intent":     "Запрос пользователя слишком неточен для выполнения",
    "bad_retry_policy":               "Некорректная настройка параметров повторных попыток",
    "kv_transfer_failure":            "Ошибка при передаче кэша между узлами кластера",
    "memory_bandwidth_bottleneck":    "Снижение производительности из-за конкуренции за HBM",
    "hardware_degradation":           "Постепенное ухудшение характеристик оборудования",
    "gpu_throttling":                 "Снижение частот GPU из-за перегрева",
    "correlated_ssd_failure":         "Одновременные отказы нескольких накопителей",
    "network_power_failure":          "Отказ сетевой инфраструктуры или электропитания",
}

# ── Source display names ──────────────────────────────────────────────────────
SOURCE_LABEL = {
    "trail":                          "TRAIL (GAIA + SWE-bench Lite, 2024)",
    "magentic_one":                   "AgentRx / magentic_one",
    "tau_retail":                     "AgentRx / tau_retail",
    "who_and_when_hc":                "Who&When Hand-Crafted",
    "keyword_search_nebius":          "nebius/SWE-agent-trajectories (keyword)",
    "keyword_search_itbench":         "ibm-research/ITBench-Trajectories (keyword)",
    "keyword_search_terminalbench":   "yoonholee/terminalbench-trajectories (keyword)",
}


def main():
    stats = pd.read_csv(DATA_DIR / "stats_full_v2.csv")
    dists = pd.read_csv(DATA_DIR / "distributions_v2.csv")

    # Build best-dist lookup (best KS p-value per (error_id, source))
    best_idx = dists.groupby(["error_id", "source"])["ks_pvalue"].idxmax()
    best_dist = dists.loc[best_idx].set_index(["error_id", "source"])

    # Build final table
    rows = []
    for _, row in stats.iterrows():
        eid = row["error_id"]
        src = row["source"]

        cls, cls_reason = MODELING_CLASS.get(eid, (1, "Не определена"))
        mc = f"Категория {cls}"

        # Best distribution
        bd_row = best_dist.loc[(eid, src)] if (eid, src) in best_dist.index else None
        if bd_row is not None and row["step_n"] >= 20:
            best_dist_name = bd_row["distribution"]
            params = bd_row["params"]
            ks_p = bd_row["ks_pvalue"]
            low = bd_row["low_confidence"]
            if ks_p >= 0.05:
                conclusion = f"{best_dist_name} подтверждён (p={ks_p:.4f})"
            elif ks_p >= 0.01:
                conclusion = f"{best_dist_name} не отвергнут (p={ks_p:.4f})"
            else:
                conclusion = f"{best_dist_name} отвергнут (p={ks_p:.4f}), {best_dist_name}"
        else:
            best_dist_name = params = ks_p = conclusion = None

        data_quality = SOURCE_QUALITY.get(src, "low")
        # Downgrade keyword search medium if n is low
        if src.startswith("keyword_") and row["n_trajectories_with_error"] < 20:
            data_quality = "low"

        rows.append({
            "error_id":                        eid,
            "name_ru":                         NAME_RU.get(eid, eid),
            "description_ru":                  DESC_RU.get(eid, ""),
            "source":                          src,
            "source_label":                    SOURCE_LABEL.get(src, src),
            "modeling_class":                  mc,
            "modeling_class_reason":           cls_reason,
            "n_trajectories_with_error":       int(row["n_trajectories_with_error"]),
            "n_trajectories_total":            int(row["n_trajectories_total"]),
            "p_trajectory":                    round(row["p_trajectory"], 6) if pd.notna(row["p_trajectory"]) else None,
            "p_traj_ci_lower":                 round(row["p_traj_ci_lower"], 6) if pd.notna(row["p_traj_ci_lower"]) else None,
            "p_traj_ci_upper":                 round(row["p_traj_ci_upper"], 6) if pd.notna(row["p_traj_ci_upper"]) else None,
            "total_steps":                     int(row["total_steps"]) if pd.notna(row["total_steps"]) else None,
            "p_message":                       round(row["p_message"], 6) if pd.notna(row["p_message"]) else None,
            "p_msg_ci_lower":                  round(row["p_msg_ci_lower"], 6) if pd.notna(row["p_msg_ci_lower"]) else None,
            "p_msg_ci_upper":                  round(row["p_msg_ci_upper"], 6) if pd.notna(row["p_msg_ci_upper"]) else None,
            "step_mean":                       round(row["step_mean"], 2) if pd.notna(row["step_mean"]) else None,
            "step_median":                     round(row["step_median"], 2) if pd.notna(row["step_median"]) else None,
            "step_std":                        round(row["step_std"], 2) if pd.notna(row["step_std"]) else None,
            "step_n":                          int(row["step_n"]) if pd.notna(row["step_n"]) else None,
            "step_p25":                        round(row["step_p25"], 2) if pd.notna(row["step_p25"]) else None,
            "step_p75":                        round(row["step_p75"], 2) if pd.notna(row["step_p75"]) else None,
            "step_p90":                        round(row["step_p90"], 2) if pd.notna(row["step_p90"]) else None,
            "best_distribution":               best_dist_name,
            "best_dist_params":                params,
            "best_dist_ks_p":                  round(ks_p, 4) if ks_p is not None else None,
            "fit_conclusion":                  conclusion,
            "data_quality":                    data_quality,
            "insufficient_data":               bool(row["insufficient_data"]) if pd.notna(row["insufficient_data"]) else True,
        })

    final = pd.DataFrame(rows)
    final.to_csv(DATA_DIR / "all_errors_final.csv", index=False)
    print(f"Saved all_errors_final.csv: {len(final)} rows")
    print(f"\nBy modeling class:")
    print(final["modeling_class"].value_counts())
    print(f"\nBy source:")
    print(final["source"].value_counts())

    # ── Write report ────────────────────────────────────────────────────────────
    report = []
    report.append("# ТЗ №4.8 — Отчёт: исправление данных\n")
    report.append(f"Дата: 2026-05-06  \n")
    report.append(f"Версия: v2 (TRAIL + Who&When HC)  \n")
    report.append("\n---\n")

    # Section 1: What was fixed
    report.append("## 1. Что исправлено\n\n")
    report.append("Обнаружены две методологические ошибки в предыдущих шагах:\n\n")
    report.append("1. **TRAIL** — ошибочно исключён как синтетический. Исправлено: возвращён как источник экспертной разметки (148 трейсов, GAIA + SWE-bench Lite).\n\n")
    report.append("2. **Who&When** — содержал 184 записи (126 Algorithm-Generated + 58 Hand-Crafted). Исправлено: осталены только 58 Hand-Crafted.\n\n")
    report.append("### Изменения в количестве записей\n\n")
    report.append("| Сущность | Было (старое) | Стало (новое) | Δ |\n")
    report.append("|---|---|---|---|\n")
    report.append(f"| Who&When (источник ошибок) | 184 | 58 | −126 |\n")
    report.append(f"| Who&When (trajectories) | 184 | 46 | −138 |\n")
    report.append(f"| errors_classified.csv | 518 строк | ~{len(final)} строк | varies |\n")
    report.append(f"| stats_full.csv | старый | 38 строк | varies |\n")
    report.append(f"| **+ TRAIL** | 0 | 143 trajectories, 836 errors | **+836** |\n")
    report.append("\n")

    # Section 2: TRAIL errors
    trail_stats = stats[stats["source"] == "trail"]
    report.append("## 2. TRAIL: извлечённые ошибки\n\n")
    report.append(f"Источник: {TRAIL_DIR.name} — 148 трейсов (117 GAIA + 31 SWE-bench Lite), экспертная разметка.\n\n")
    report.append("| error_id | name_ru | n trajectories | p(traj) [95% CI] | n errors | p(msg) |\n")
    report.append("|---|---|---|---|---|---|\n")
    for _, r in trail_stats.sort_values("n_trajectories_with_error", ascending=False).iterrows():
        ci = f"[{r.p_traj_ci_lower:.3f}, {r.p_traj_ci_upper:.3f}]"
        pm = f"{r.p_message:.5f}" if pd.notna(r.p_message) else "N/A"
        n_step = f"{int(r.step_n)}" if pd.notna(r.step_n) else "—"
        report.append(f"| {r.error_id} | {NAME_RU.get(r.error_id, r.error_id)} | "
                    f"{r.n_trajectories_with_error}/{r.n_trajectories_total} | "
                    f"{r.p_trajectory:.3f} {ci} | {n_step} | {pm} |\n")
    report.append("\n")

    # Section 3: Who&When Hand-Crafted
    ww_stats = stats[stats["source"] == "who_and_when_hc"]
    report.append("## 3. Who&When Hand-Crafted: обновлённая классификация\n\n")
    report.append(f"Источник: только Hand-Crafted.parquet — 58 трейдов, 46 с классифицированными ошибками.\n\n")
    report.append("| error_id | name_ru | n trajectories | p(traj) |\n")
    report.append("|---|---|---|---|\n")
    for _, r in ww_stats.sort_values("n_trajectories_with_error", ascending=False).iterrows():
        report.append(f"| {r.error_id} | {NAME_RU.get(r.error_id, r.error_id)} | "
                    f"{r.n_trajectories_with_error}/{r.n_trajectories_total} | "
                    f"{r.p_trajectory:.3f} |\n")
    report.append("\n")

    # Section 4: Updated statistics (all sources)
    report.append("## 4. Обновлённая статистика\n\n")
    for src in ["trail", "who_and_when_hc", "magentic_one", "tau_retail",
                "keyword_search_nebius", "keyword_search_itbench", "keyword_search_terminalbench"]:
        src_stats = stats[stats["source"] == src]
        if len(src_stats) == 0:
            continue
        label = SOURCE_LABEL.get(src, src)
        report.append(f"### {label}\n\n")
        report.append("| error_id | n_traj | p(traj) | p(msg) | CI p(traj) | insufficient |\n")
        report.append("|---|---|---|---|---|---|\n")
        for _, r in src_stats.sort_values("n_trajectories_with_error", ascending=False).iterrows():
            ci = (f"{r.p_traj_ci_lower:.3f}–{r.p_traj_ci_upper:.3f}"
                  if pd.notna(r.p_traj_ci_lower) else "N/A")
            pm = f"{r.p_message:.5f}" if pd.notna(r.p_message) else "N/A"
            insuf = "⚠" if r.insufficient_data else ""
            report.append(f"| {r.error_id} | {r.n_trajectories_with_error}/{r.n_trajectories_total} | "
                        f"{r.p_trajectory:.4f} | {pm} | {ci} | {insuf} |\n")
        report.append("\n")

    # Section 5: Distributions
    report.append("## 5. Распределения ошибок (TRAIL, n≥20)\n\n")
    trail_dists = dists[(dists["source"] == "trail") & (dists["position_type"] == "absolute")]
    best_trail = trail_dists.loc[trail_dists.groupby("error_id")["ks_pvalue"].idxmax()]
    best_trail = best_trail[best_trail["error_id"].isin(
        trail_stats[trail_stats["step_n"] >= 20]["error_id"]
    )]
    report.append("| error_id | Лучшее распределение | Параметры | KS p-value | Вывод |\n")
    report.append("|---|---|---|---|---|\n")
    for _, r in best_trail.sort_values("ks_pvalue", ascending=False).iterrows():
        conclusion_map = {True: "⚠ слабое", False: "✓"}
        concl = conclusion_map.get(r.low_confidence, "")
        report.append(f"| {r.error_id} | {r.distribution} | {r.params} | "
                     f"{r.ks_pvalue:.4f} | {concl} |\n")
    report.append("\n")

    # Section 6: Final table (compact)
    report.append("## 6. Финальная сводная таблица (all_errors_final.csv)\n\n")
    report.append(f"Всего строк: {len(final)}  \n")
    report.append(f"Источников: {final['source'].nunique()}  \n")
    report.append(f"Уникальных error_id: {final['error_id'].nunique()}  \n\n")

    report.append("### По классам моделирования\n\n")
    for mc in sorted(final["modeling_class"].unique()):
        sub = final[final["modeling_class"] == mc]
        report.append(f"**{mc}** ({len(sub)} записей):  \n")
        eids = sub["error_id"].unique()
        report.append(", ".join(eids) + "\n\n")

    report.append("### Распределение data_quality\n\n")
    for dq, cnt in final["data_quality"].value_counts().items():
        report.append(f"- **{dq}**: {cnt} записей\n")

    report_path = DOCS_DIR / "tz4_8_report.md"
    report_path.write_text("".join(report), encoding="utf-8")
    print(f"\nSaved report: {report_path}")
    print(f"Report length: {len(report_path.read_text())} chars")


if __name__ == "__main__":
    main()
