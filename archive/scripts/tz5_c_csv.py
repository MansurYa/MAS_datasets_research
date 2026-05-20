"""ТЗ №5 Часть C — Итоговый CSV."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
from pathlib import Path
import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "report"
PLOTS_DIR = REPORT_DIR / "plots"

MODELING_REASON_RU = {
    "kv_cache_loss": "Моделируется напрямую: удаление кэшированного состояния в IR-блоке",
    "tool_timeout": "Моделируется как вероятностная задержка/отказ на блоках вызова инструментов",
    "tool_web_failure": "Частота оценивается статистически; эффект — отказ на уровне шага",
    "resource_not_found": "Частота оценивается статистически; эффект — отказ на уровне шага",
    "resource_abuse": "Частота и распределение по шагам оцениваются статистически",
    "permission_error": "Частота оценивается статистически; эффект — отказ на уровне шага",
    "memory_error": "Частота оценивается статистически; эффект — отказ на уровне шага",
    "code_error": "Корректность кода зависит от генерации LLM",
    "instruction_adherence_failure": "Требует полного рассуждения LLM; нельзя инжектировать структурно",
    "hallucination": "Галлюцинация требует полного выполнения LLM",
    "orchestration_failure": "Решения о маршрутизации требуют рассуждения LLM",
    "misinterpretation_of_tool_output": "Семантическая интерпретация требует рассуждения LLM",
    "guardrails_triggered": "Частота оценивается статистически; эффект — отказ на уровне шага",
    "factual_error": "Фактическая корректность зависит от знаний LLM",
    "system_failure": "Моделируется как вероятностный жёсткий отказ",
    "invalid_invocation": "Моделируется как вероятностный отказ вызова инструмента",
    "misinterpretation": "Семантическая интерпретация требует рассуждения LLM",
    "intent_plan_misalignment": "Отклонение от цели требует понимания LLM",
    "invention_of_new_information": "Галлюцинация требует полного выполнения LLM",
    "intent_not_supported": "Зависит от оценки возможностей LLM",
    "underspecified_user_intent": "Разрешение неоднозначности зависит от рассуждения LLM",
    "bad_retry_policy": "Моделируется параметрами политики повторов в IR-блоках",
    "kv_transfer_failure": "Моделируется как отказ передачи состояния в IR-графе",
    "memory_bandwidth_bottleneck": "Моделируется как снижение пропускной способности на блоках инференса",
    "hardware_degradation": "Симулятор не рассчитан на долгосрочную деградацию оборудования",
    "gpu_throttling": "Редко в крупных кластерах; вне области применения",
    "correlated_ssd_failure": "Уровень инфраструктуры; вне области агентных траекторий",
    "network_power_failure": "Уровень инфраструктуры; вне области агентных траекторий",
}

DATA_QUALITY_RU = {
    "trail": "экспертная разметка",
    "magentic_one": "аннотация на уровне шагов",
    "tau_retail": "аннотация на уровне шагов",
    "who_and_when_hc": "keyword matching",
    "keyword_search_nebius": "keyword search в траекториях",
    "keyword_search_itbench": "keyword search в траекториях",
    "keyword_search_terminalbench": "keyword search в траекториях",
    "теоретическая": "нет данных",
    "high": "экспертная разметка",
    "medium": "аннотация на уровне шагов",
    "нет данных": "нет данных",
}


def fit_conclusion_ru(row):
    n = row.get("step_n")
    ks_p = row.get("best_dist_ks_p")
    fit = row.get("fit_conclusion")
    if fit == "нет данных" or (not n and not ks_p):
        return "нет данных"
    if isinstance(ks_p, float) and ks_p > 0.05:
        return "подгонка найдена"
    if isinstance(n, float) and n >= 100:
        return "параметрическое не подходит"
    return "низкая мощность теста"


def get_plots(row):
    eid = row.get("error_id", "")
    src = row.get("source", "")
    files = []
    for prefix in ["hist", "qq"]:
        fname = f"{prefix}_{eid}_{src}.png"
        if (PLOTS_DIR / fname).exists():
            files.append(fname)
    return ";".join(files)


def main():
    df = pd.read_csv(DATA_DIR / "all_errors_fixed.csv")

    # Build final CSV
    out = pd.DataFrame()
    out["error_id"] = df["error_id"]
    out["name_ru"] = df["name_ru"]
    out["description_ru"] = df["description_ru"]
    out["source"] = df["source"]
    out["modeling_class"] = df["modeling_class"]
    out["modeling_class_reason_ru"] = df["error_id"].map(MODELING_REASON_RU).fillna(df.get("modeling_class_reason", ""))
    out["n_trajectories_with_error"] = df["n_trajectories_with_error"]
    out["n_trajectories_total"] = df["n_trajectories_total"]
    out["p_trajectory"] = df["p_trajectory"]
    out["p_traj_ci_lower"] = df["p_traj_ci_lower"]
    out["p_traj_ci_upper"] = df["p_traj_ci_upper"]
    out["total_steps"] = df["total_steps"]
    out["p_message"] = df["p_message"]
    out["p_msg_ci_lower"] = df["p_msg_ci_lower"]
    out["p_msg_ci_upper"] = df["p_msg_ci_upper"]
    out["step_mean"] = df["step_mean"]
    out["step_median"] = df["step_median"]
    out["step_std"] = df["step_std"]
    out["step_n"] = df["step_n"]
    out["best_distribution"] = df["best_distribution"]
    out["best_dist_params"] = df["best_dist_params"]
    out["best_dist_ks_p"] = df["best_dist_ks_p"]
    out["fit_conclusion_ru"] = df.apply(fit_conclusion_ru, axis=1)
    out["data_quality_ru"] = df["source"].map(DATA_QUALITY_RU).fillna("аннотация на уровне шагов")
    out["insufficient_data"] = df["insufficient_data"]
    out["plots"] = df.apply(get_plots, axis=1)

    # Clean: replace NaN with empty string
    out = out.where(pd.notna(out), "")

    out.to_csv(REPORT_DIR / "all_errors_final.csv", index=False)
    print(f"Сохранено report/all_errors_final.csv: {len(out)} строк")
    print(f"Столбцы: {list(out.columns)}")
    print(f"Графики найдены: {(out['plots'] != '').sum()} строк")


if __name__ == "__main__":
    main()
