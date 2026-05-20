"""ТЗ №5 Часть A — Исправление данных."""
# ВНИМАНИЕ: скрипт перемещён в archive/scripts/. Пути data/, report/, docs/ теперь archive/data/, archive/data/report_output/, archive/docs/. Запускать из корня репозитория с поправкой путей.
import json
import math
import re
from pathlib import Path

import pandas as pd

ROOT = Path("/Volumes/MansurSSD/MAS_datasets_research")
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "report"
TRAIL_DIR = ROOT / "TRAIL"
REPORT_DIR.mkdir(exist_ok=True)

TRAIL_MAPPING = {
    "Context Handling Failures": "kv_cache_loss",
    "Resource Abuse": "resource_abuse",
    "Timeout Issues": "tool_timeout",
    "Service Errors": "system_failure",
    "Tool-related": "hallucination",
    "Language-only": "hallucination",
    "Poor Information Retrieval": "misinterpretation_of_tool_output",
    "Tool Output Misinterpretation": "misinterpretation_of_tool_output",
    "Formatting Errors": "code_error",
    "Instruction Non-compliance": "instruction_adherence_failure",
    "Tool Definition Issues": "invalid_invocation",
    "Environment Setup Errors": "invalid_invocation",
    "Incorrect Problem Identification": "orchestration_failure",
    "Tool Selection Errors": "orchestration_failure",
    "Goal Deviation": "orchestration_failure",
    "Task Orchestration": "orchestration_failure",
    "Rate Limiting": "tool_web_failure",
    "Authentication Errors": "tool_web_failure",
    "Resource Not Found": "resource_not_found",
    "Resource Exhaustion": "resource_abuse",
    "Incorrect Memory Usage": "kv_cache_loss",
}

# A2: теоретические ошибки без данных
THEORETICAL_ERRORS = [
    ("hardware_degradation", "Деградация оборудования",
     "Постепенное ухудшение характеристик оборудования со временем", 4,
     "Симулятор не рассчитан на долгосрочную деградацию оборудования"),
    ("gpu_throttling", "Троттлинг GPU",
     "Снижение частот GPU из-за перегрева", 4,
     "Редко в крупных кластерах; вне области применения"),
    ("correlated_ssd_failure", "Коррелированные сбои SSD",
     "Одновременные отказы нескольких накопителей в стойке", 4,
     "Уровень инфраструктуры; вне области агентных траекторий"),
    ("network_power_failure", "Сетевые и электросбои",
     "Отказ сетевой инфраструктуры или электропитания", 4,
     "Уровень инфраструктуры; вне области агентных траекторий"),
    ("bad_retry_policy", "Неверная политика повторов",
     "Некорректные параметры backoff/jitter вызывают retry storm", 2,
     "Моделируется параметрами политики повторов в IR-блоках"),
    ("kv_transfer_failure", "Сбой передачи KV-кэша",
     "Ошибка при передаче кэша между узлами кластера", 2,
     "Моделируется как отказ передачи состояния в IR-графе"),
    ("memory_bandwidth_bottleneck", "Узкое место пропускной способности памяти",
     "Конкуренция запросов за HBM снижает производительность", 2,
     "Моделируется как снижение пропускной способности на блоках инференса"),
]

# A3: параметры распределений с подписями
DIST_PARAM_NAMES = {
    "gamma":       ["shape", "loc", "scale"],
    "exponential": ["loc", "scale"],
    "weibull_min": ["shape", "loc", "scale"],
    "lognorm":     ["s", "loc", "scale"],
    "beta":        ["a", "b", "loc", "scale"],
    "pareto":      ["b", "loc", "scale"],
    "lomax":       ["c", "loc", "scale"],
    "uniform":     ["loc", "scale"],
}


def label_params(dist_name, params_str):
    if not isinstance(params_str, str) or "fit_failed" in params_str:
        return params_str
    names = DIST_PARAM_NAMES.get(dist_name)
    if not names:
        return params_str
    try:
        vals = [v.strip() for v in params_str.split(",")]
        if len(vals) != len(names):
            return params_str
        return ", ".join(f"{n}={v}" for n, v in zip(names, vals))
    except Exception:
        return params_str


def flatten_spans(spans, counter=None):
    """Рекурсивно обходит spans, возвращает {span_id: step_number}."""
    if counter is None:
        counter = [0]
    result = {}
    for span in spans:
        counter[0] += 1
        sid = span.get("span_id")
        if sid:
            result[sid] = counter[0]
        children = span.get("child_spans", [])
        if children:
            result.update(flatten_spans(children, counter))
    return result


def a1_fix_trail():
    """Перезапустить извлечение TRAIL, включая траектории с unknown ошибками."""
    rows = []
    skipped_json = 0

    for benchmark, subdir, raw_subdir in [
        ("GAIA", "processed_annotations_gaia", "GAIA"),
        ("SWE-bench", "processed_annotations_swe_bench", "SWE Bench"),
    ]:
        ann_dir = TRAIL_DIR / subdir
        raw_dir = TRAIL_DIR / raw_subdir

        for ann_file in sorted(ann_dir.glob("*.json")):
            trace_id = ann_file.stem
            try:
                with open(ann_file) as f:
                    ann = json.load(f)
            except json.JSONDecodeError:
                skipped_json += 1
                continue

            raw_file = raw_dir / f"{trace_id}.json"
            if not raw_file.exists():
                continue

            with open(raw_file) as f:
                raw = json.load(f)

            span_map = flatten_spans(raw.get("spans", []))
            traj_len = len(span_map)

            errors = ann.get("errors", [])
            if not errors:
                # Траектория без ошибок — добавляем одну строку-заглушку
                rows.append({
                    "trajectory_id": trace_id, "trail_category": "",
                    "error_id": "no_errors", "error_step": None,
                    "trajectory_length": traj_len, "normalized_position": None,
                    "impact": "", "benchmark": benchmark,
                })
                continue

            for err in errors:
                category = err.get("category", "")
                location = err.get("location", "")
                impact = err.get("impact", "")
                error_id = TRAIL_MAPPING.get(category, "unknown")
                step = span_map.get(location)
                if step is None:
                    continue
                rows.append({
                    "trajectory_id": trace_id, "trail_category": category,
                    "error_id": error_id, "error_step": step,
                    "trajectory_length": traj_len,
                    "normalized_position": round(step / traj_len, 6) if traj_len else 0,
                    "impact": impact, "benchmark": benchmark,
                })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "trail_errors.csv", index=False)
    n_traj = df["trajectory_id"].nunique()
    n_errors = len(df[df["error_id"] != "no_errors"])
    print(f"A1: trail_errors.csv — {n_traj} траекторий, {n_errors} ошибок (skipped JSON: {skipped_json})")
    return df


def a2_add_theoretical(df):
    """Добавить 7 теоретических ошибок без данных."""
    existing_ids = set(df["error_id"].unique())
    new_rows = []
    for eid, name_ru, desc_ru, mc, mc_reason in THEORETICAL_ERRORS:
        if eid not in existing_ids:
            new_rows.append({
                "error_id": eid, "name_ru": name_ru, "description_ru": desc_ru,
                "source": "теоретическая", "modeling_class": mc,
                "modeling_class_reason": mc_reason,
                "n_trajectories_with_error": None, "n_trajectories_total": None,
                "p_trajectory": None, "p_traj_ci_lower": None, "p_traj_ci_upper": None,
                "total_steps": None, "p_message": None,
                "p_msg_ci_lower": None, "p_msg_ci_upper": None,
                "step_mean": None, "step_median": None, "step_std": None, "step_n": None,
                "best_distribution": None, "best_dist_params": None,
                "best_dist_ks_p": None, "fit_conclusion": "нет данных",
                "data_quality": "нет данных", "insufficient_data": True,
            })
    if new_rows:
        df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
    print(f"A2: добавлено {len(new_rows)} теоретических ошибок")
    return df


def a3_label_params(df):
    """Подписать параметры распределений."""
    def fix(row):
        dist = row.get("best_distribution")
        params = row.get("best_dist_params")
        if pd.isna(dist) or pd.isna(params):
            return params
        return label_params(str(dist), str(params))
    df["best_dist_params"] = df.apply(fix, axis=1)
    print("A3: параметры распределений подписаны")
    return df


def a4_remove_dashes(df):
    """Заменить длинные тире на пустую строку."""
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].replace({"—": "", "–": ""})
            df[col] = df[col].apply(
                lambda x: "" if isinstance(x, str) and x.strip() in ("—", "–") else x)
    print("A4: длинные тире убраны")
    return df


def a5_add_plots_column(df):
    """Добавить столбец plots с именами файлов графиков."""
    plots_dir = ROOT / "report" / "plots"

    def get_plots(row):
        eid = row.get("error_id", "")
        src = row.get("source", "")
        files = []
        hist = f"hist_{eid}_{src}.png"
        qq = f"qq_{eid}_{src}.png"
        if (plots_dir / hist).exists():
            files.append(hist)
        if (plots_dir / qq).exists():
            files.append(qq)
        return ";".join(files) if files else ""

    df["plots"] = df.apply(get_plots, axis=1)
    print("A5: столбец plots добавлен")
    return df


def main():
    # A1: исправить TRAIL
    a1_fix_trail()

    # Загрузить текущую финальную таблицу
    df = pd.read_csv(DATA_DIR / "all_errors_final.csv")

    # A2: добавить теоретические
    df = a2_add_theoretical(df)

    # A3: подписать параметры
    df = a3_label_params(df)

    # A4: убрать тире
    df = a4_remove_dashes(df)

    # A5: добавить plots (после генерации графиков в части B)
    # Пока создаём без plots, добавим после B
    df.to_csv(DATA_DIR / "all_errors_fixed.csv", index=False)
    print(f"Сохранено data/all_errors_fixed.csv: {len(df)} строк")
    return df


if __name__ == "__main__":
    main()
