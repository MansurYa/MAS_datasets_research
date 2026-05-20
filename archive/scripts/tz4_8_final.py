"""ТЗ №4.8 Часть D — Финальная сводная таблица + отчёт."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import math
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
PLOTS_DIR = DATA_DIR / "plots"
DOCS_DIR.mkdir(exist_ok=True)

NAME_RU = {
    "kv_cache_loss": ("Потеря KV-кэша", "Потеря кэша ключей-значений после перезапуска модуля или вытеснения из памяти GPU"),
    "tool_timeout": ("Таймаут вызова инструмента", "Внешний инструмент или shell-команда не ответили за отведённое время"),
    "tool_web_failure": ("Сбой доступа к веб-ресурсу", "HTTP-ошибка при обращении к внешнему API или веб-сервису"),
    "resource_not_found": ("Ресурс не найден", "Файл, директория или запрашиваемый ресурс не существует в среде выполнения"),
    "resource_abuse": ("Избыточное потребление ресурсов", "Исчерпание лимита шагов, зацикливание агента, чрезмерное потребление ресурсов"),
    "permission_error": ("Ошибка доступа", "Отказ в доступе к файлу, директории или сервису из-за недостаточных прав"),
    "memory_error": ("Ошибка памяти (OOM)", "Нехватка оперативной памяти при выполнении вычислительной задачи"),
    "code_error": ("Ошибка в коде", "Агент сгенерировал синтаксически или логически неверный код"),
    "instruction_adherence_failure": ("Несоблюдение инструкций", "Агент не выполнил инструкцию оркестратора или пользователя"),
    "hallucination": ("Галлюцинация", "Агент выдумал факты, данные или ссылки"),
    "orchestration_failure": ("Сбой оркестрации", "Неверная маршрутизация задачи, ошибочное решение о следующем шаге"),
    "misinterpretation_of_tool_output": ("Неверная интерпретация результата", "Агент неправильно понял вывод инструмента"),
    "guardrails_triggered": ("Срабатывание защитных ограничений", "Внешний сервис заблокировал запрос агента"),
    "factual_error": ("Фактическая ошибка", "Агент использовал неверные факты из своих знаний"),
    "system_failure": ("Системный сбой", "Критический сбой инфраструктуры выполнения"),
    "invalid_invocation": ("Некорректный вызов инструмента", "Агент вызвал инструмент с неверными параметрами"),
    "misinterpretation": ("Неверная интерпретация", "Агент неправильно истолковал входные данные"),
    "intent_plan_misalignment": ("Несоответствие намерения и плана", "Агент составил план не соответствующий задаче"),
    "invention_of_new_information": ("Изобретение информации", "Агент выдумал данные которых не было в источниках"),
    "intent_not_supported": ("Неподдерживаемое намерение", "Агент не способен выполнить запрошенное действие"),
    "underspecified_user_intent": ("Недоопределённое намерение", "Запрос пользователя слишком неточен для выполнения"),
    "bad_retry_policy": ("Неверная политика повторов", "Некорректная настройка параметров повторных попыток"),
    "kv_transfer_failure": ("Сбой передачи KV-кэша", "Ошибка при передаче кэша между узлами кластера"),
    "memory_bandwidth_bottleneck": ("Узкое место по пропускной способности памяти", "Снижение производительности из-за конкуренции за HBM"),
    "hardware_degradation": ("Деградация оборудования", "Постепенное ухудшение характеристик оборудования"),
    "gpu_throttling": ("Троттлинг GPU", "Снижение частот GPU из-за перегрева"),
    "correlated_ssd_failure": ("Коррелированные сбои SSD", "Одновременные отказы нескольких накопителей"),
    "network_power_failure": ("Сетевые и power-сбои", "Отказ сетевой инфраструктуры или электропитания"),
}

MODELING_CLASS = {
    "kv_cache_loss": (2, "Моделируется напрямую: удаление кэшированного состояния в IR-блоке"),
    "tool_timeout": (2, "Моделируется как вероятностная задержка/отказ на блоках вызова инструментов"),
    "tool_web_failure": (3, "Частота оценивается статистически; эффект — отказ на уровне шага"),
    "resource_not_found": (3, "Частота оценивается статистически; эффект — отказ на уровне шага"),
    "resource_abuse": (3, "Частота и распределение по шагам оцениваются статистически"),
    "permission_error": (3, "Частота оценивается статистически; эффект — отказ на уровне шага"),
    "memory_error": (3, "Частота оценивается статистически; эффект — отказ на уровне шага"),
    "code_error": (1, "Корректность кода зависит от генерации LLM"),
    "instruction_adherence_failure": (1, "Требует полного рассуждения LLM; нельзя инжектировать структурно"),
    "hallucination": (1, "Галлюцинация требует полного выполнения LLM"),
    "orchestration_failure": (1, "Решения о маршрутизации требуют рассуждения LLM"),
    "misinterpretation_of_tool_output": (1, "Семантическая интерпретация требует рассуждения LLM"),
    "guardrails_triggered": (3, "Частота оценивается статистически; эффект — отказ на уровне шага"),
    "factual_error": (1, "Фактическая корректность зависит от знаний LLM"),
    "system_failure": (3, "Моделируется как вероятностный жёсткий отказ"),
    "invalid_invocation": (3, "Моделируется как вероятностный отказ вызова инструмента"),
    "misinterpretation": (1, "Семантическая интерпретация требует рассуждения LLM"),
    "intent_plan_misalignment": (1, "Отклонение от цели требует понимания LLM"),
    "invention_of_new_information": (1, "Галлюцинация требует полного выполнения LLM"),
    "intent_not_supported": (1, "Зависит от оценки возможностей LLM"),
    "underspecified_user_intent": (1, "Разрешение неоднозначности зависит от рассуждения LLM"),
    "bad_retry_policy": (2, "Моделируется параметрами политики повторов в IR-блоках"),
    "kv_transfer_failure": (2, "Моделируется как отказ передачи состояния в IR-графе"),
    "memory_bandwidth_bottleneck": (2, "Моделируется как снижение пропускной способности на блоках инференса"),
    "hardware_degradation": (4, "Симулятор не рассчитан на долгосрочную деградацию оборудования"),
    "gpu_throttling": (4, "Редко в крупных кластерах; вне области применения"),
    "correlated_ssd_failure": (4, "Уровень инфраструктуры; вне области агентных траекторий"),
    "network_power_failure": (4, "Уровень инфраструктуры; вне области агентных траекторий"),
}

DATA_QUALITY = {
    "trail": "high",
    "magentic_one": "medium",
    "tau_retail": "medium",
    "who_and_when_hc": "medium",
    "keyword_search_nebius": "high",
    "keyword_search_itbench": "high",
    "keyword_search_terminalbench": "high",
}


def fmt(v, d=4):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v:.{d}f}" if isinstance(v, float) else str(v)


def df_to_md(df):
    lines = ["| " + " | ".join(str(c) for c in df.columns) + " |",
             "|" + "|".join(["---"] * len(df.columns)) + "|"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(
            "—" if (v is None or (isinstance(v, float) and math.isnan(v))) else str(v)
            for v in row) + " |")
    return "\n".join(lines)


def build_final_table():
    stats_v2 = pd.read_csv(DATA_DIR / "stats_full_v2.csv")
    dist_v2 = pd.read_csv(DATA_DIR / "distributions_v2.csv")

    # Also include keyword search from previous TZ
    kw_stats = pd.read_csv(DATA_DIR / "keyword_stats_full.csv")
    kw_dist = pd.read_csv(DATA_DIR / "keyword_distributions.csv")

    rows = []

    # New sources: TRAIL + AgentRx + Who&When HC
    for _, r in stats_v2.iterrows():
        eid = r["error_id"]
        src = r["source"]
        mc, mc_reason = MODELING_CLASS.get(eid, (1, ""))
        name_ru, desc_ru = NAME_RU.get(eid, (eid, ""))

        # Best distribution
        dr = dist_v2[(dist_v2["error_id"] == eid) & (dist_v2["source"] == src) &
                     (dist_v2["position_type"] == "absolute")]
        valid = dr[dr["ks_pvalue"].notna()]
        if len(valid):
            best = valid.sort_values("ks_pvalue", ascending=False).iloc[0]
            best_dist = best["distribution"]
            best_params = best["params"]
            best_ks_p = best["ks_pvalue"]
            n = r.get("step_n")
            if n and n >= 3000:
                fit_conc = "best_fit_available" if best_ks_p >= 0.05 else "no_parametric_fit"
            elif n and n >= 100:
                fit_conc = "best_fit_available" if best_ks_p >= 0.05 else "inconclusive"
            else:
                fit_conc = "inconclusive: низкая мощность теста"
        else:
            best_dist = best_params = best_ks_p = fit_conc = None

        rows.append({
            "error_id": eid, "name_ru": name_ru, "description_ru": desc_ru,
            "source": src, "modeling_class": mc, "modeling_class_reason": mc_reason,
            "n_trajectories_with_error": int(r["n_trajectories_with_error"]),
            "n_trajectories_total": int(r["n_trajectories_total"]),
            "p_trajectory": r["p_trajectory"], "p_traj_ci_lower": r["p_traj_ci_lower"],
            "p_traj_ci_upper": r["p_traj_ci_upper"], "total_steps": int(r["total_steps"]),
            "p_message": r["p_message"], "p_msg_ci_lower": r["p_msg_ci_lower"],
            "p_msg_ci_upper": r["p_msg_ci_upper"],
            "step_mean": r.get("step_mean"), "step_median": r.get("step_median"),
            "step_std": r.get("step_std"), "step_n": r.get("step_n"),
            "best_distribution": best_dist, "best_dist_params": best_params,
            "best_dist_ks_p": best_ks_p, "fit_conclusion": fit_conc,
            "data_quality": DATA_QUALITY.get(src, "medium"),
            "insufficient_data": bool(r["insufficient_data"]),
        })

    # Keyword search (unchanged from TZ4.7)
    for _, r in kw_stats.iterrows():
        eid = r["category"]
        ds = r["dataset"]
        src = f"keyword_search_{ds}"
        mc, mc_reason = MODELING_CLASS.get(eid, (3, ""))
        name_ru, desc_ru = NAME_RU.get(eid, (eid, ""))

        kd = kw_dist[(kw_dist["category"] == eid) & (kw_dist["dataset"] == ds) &
                     (kw_dist["position_type"] == "absolute")]
        valid = kd[kd["ks_pvalue"].notna()]
        if len(valid):
            best = valid.sort_values("ks_pvalue", ascending=False).iloc[0]
            best_dist = best["distribution"]
            best_params = best["params"]
            best_ks_p = best["ks_pvalue"]
            n = r.get("step_n")
            fit_conc = "best_fit_available" if (best_ks_p and best_ks_p >= 0.05) else "inconclusive"
        else:
            best_dist = best_params = best_ks_p = fit_conc = None

        n_with = int(r["n_trajectories_with_error"]) if not math.isnan(r["n_trajectories_with_error"]) else 0
        rows.append({
            "error_id": eid, "name_ru": name_ru, "description_ru": desc_ru,
            "source": src, "modeling_class": mc, "modeling_class_reason": mc_reason,
            "n_trajectories_with_error": n_with,
            "n_trajectories_total": int(r["n_trajectories_total"]),
            "p_trajectory": r["p_trajectory"], "p_traj_ci_lower": r["p_traj_ci_lower"],
            "p_traj_ci_upper": r["p_traj_ci_upper"], "total_steps": int(r["total_steps"]),
            "p_message": r["p_message"], "p_msg_ci_lower": r["p_msg_ci_lower"],
            "p_msg_ci_upper": r["p_msg_ci_upper"],
            "step_mean": r.get("step_mean"), "step_median": r.get("step_median"),
            "step_std": r.get("step_std"), "step_n": r.get("step_n"),
            "best_distribution": best_dist, "best_dist_params": best_params,
            "best_dist_ks_p": best_ks_p, "fit_conclusion": fit_conc,
            "data_quality": DATA_QUALITY.get(src, "high"),
            "insufficient_data": n_with < 20,
        })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "all_errors_final.csv", index=False)
    print(f"Saved all_errors_final.csv: {len(df)} rows")
    return df


def generate_report(final_df):
    stats_v2 = pd.read_csv(DATA_DIR / "stats_full_v2.csv")
    trail_df = pd.read_csv(DATA_DIR / "trail_errors.csv")
    ww_hc = pd.read_csv(DATA_DIR / "who_and_when_handcrafted_classified.csv")

    lines = [
        "# ТЗ №4.8 — Исправление данных: возврат TRAIL, чистка Who&When, пересчёт статистики",
        "",
        "**Дата:** 2026-05-06",
        "",
    ]

    # ── Раздел 1: Что исправлено ──────────────────────────────────────────────
    lines += ["## 1. Что исправлено", ""]
    lines += [
        "| Источник | Было | Стало | Изменение |",
        "|---|---|---|---|",
        "| TRAIL | Исключён (ошибочно помечен как синтетический) | Возвращён: 143 траектории, 816 ошибок | +143 траектории |",
        f"| Who&When | 184 записи (Algorithm-Generated + Hand-Crafted) | 58 записей (только Hand-Crafted) | −126 синтетических |",
        "| AgentRx | 73 траектории (без изменений) | 73 траектории | — |",
        "| Keyword search | Без изменений | Без изменений | — |",
        "",
    ]

    # ── Раздел 2: TRAIL ───────────────────────────────────────────────────────
    lines += ["## 2. TRAIL: извлечённые ошибки", ""]
    trail_clean = trail_df[trail_df["error_id"] != "unknown"]
    trail_freq = trail_clean.groupby(["trail_category", "error_id"]).size().reset_index(name="n")
    trail_freq = trail_freq.sort_values("n", ascending=False)
    lines.append(df_to_md(trail_freq))
    lines += [
        "",
        f"**Итого:** {len(trail_clean)} ошибок из {trail_clean['trajectory_id'].nunique()} траекторий",
        f"- GAIA: {len(trail_clean[trail_clean['benchmark']=='GAIA'])} ошибок",
        f"- SWE-bench: {len(trail_clean[trail_clean['benchmark']=='SWE-bench'])} ошибок",
        "",
    ]

    # ── Раздел 3: Who&When Hand-Crafted ──────────────────────────────────────
    lines += ["## 3. Who&When Hand-Crafted (58 записей)", ""]
    ww_freq = ww_hc["category_unified"].value_counts().reset_index()
    ww_freq.columns = ["Категория", "Кол-во"]
    ww_freq["% от 58"] = (ww_freq["Кол-во"] / 58 * 100).round(1).astype(str) + "%"
    lines.append(df_to_md(ww_freq))
    lines += ["", f"**Неклассифицировано:** {(ww_hc['category_unified']=='unclassified').sum()} из 58", ""]

    # ── Раздел 4: Обновлённая статистика ─────────────────────────────────────
    lines += ["## 4. Обновлённая статистика", ""]
    disp_cols = ["error_id", "source", "n_trajectories_with_error", "n_trajectories_total",
                 "p_trajectory", "p_traj_ci_lower", "p_traj_ci_upper",
                 "p_message", "p_msg_ci_lower", "p_msg_ci_upper", "insufficient_data"]
    s = stats_v2[disp_cols].copy()
    for col in ["p_trajectory", "p_traj_ci_lower", "p_traj_ci_upper"]:
        s[col] = s[col].apply(lambda x: fmt(x, 4))
    for col in ["p_message", "p_msg_ci_lower", "p_msg_ci_upper"]:
        s[col] = s[col].apply(lambda x: fmt(x, 6))
    lines.append(df_to_md(s))
    lines.append("")

    # ── Раздел 5: Распределения ───────────────────────────────────────────────
    lines += ["## 5. Распределения (n ≥ 20)", ""]
    dist_v2 = pd.read_csv(DATA_DIR / "distributions_v2.csv")
    eligible = stats_v2[stats_v2["step_n"].notna() & (stats_v2["step_n"] >= 20)]
    if len(eligible):
        for _, row in eligible.iterrows():
            eid = row["error_id"]
            src = row["source"]
            n = int(row["step_n"])
            lines.append(f"### {eid} / {src} (n={n})")
            lines.append("")
            dr = dist_v2[(dist_v2["error_id"] == eid) & (dist_v2["source"] == src) &
                         (dist_v2["position_type"] == "absolute")]
            if len(dr):
                d_disp = dr[["distribution", "params", "ks_statistic", "ks_pvalue", "low_confidence"]].copy()
                d_disp["ks_pvalue"] = d_disp["ks_pvalue"].apply(lambda x: fmt(x, 4))
                d_disp["ks_statistic"] = d_disp["ks_statistic"].apply(lambda x: fmt(x, 4))
                lines.append(df_to_md(d_disp))
            # Histogram link
            plot_path = PLOTS_DIR / f"hist48_absolute_{eid}_{src}.png"
            if plot_path.exists():
                lines.append(f"\n![{eid}_{src}]({plot_path.relative_to(ROOT)})")
            lines.append("")
    else:
        lines.append("_Нет ошибок с n ≥ 20 в новых источниках._")
        lines.append("")

    # ── Раздел 6: Финальная сводная таблица ───────────────────────────────────
    lines += ["## 6. Финальная сводная таблица (компактная)", ""]
    compact_cols = ["error_id", "name_ru", "source", "modeling_class",
                    "n_trajectories_with_error", "p_trajectory",
                    "best_distribution", "best_dist_ks_p", "data_quality", "insufficient_data"]
    compact = final_df[compact_cols].copy()
    compact["p_trajectory"] = compact["p_trajectory"].apply(lambda x: fmt(x, 4))
    compact["best_dist_ks_p"] = compact["best_dist_ks_p"].apply(lambda x: fmt(x, 4))
    lines.append(df_to_md(compact))
    lines.append("")

    return "\n".join(lines)


def main():
    final_df = build_final_table()
    report = generate_report(final_df)
    report_path = DOCS_DIR / "tz4_8_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Saved docs/tz4_8_report.md ({report_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
