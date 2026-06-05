#!/usr/bin/env python3
"""Анонимизация usage dataset для исследования KV cache loss.

Оставляет только:
- Time (с вычетом 2 месяцев)
- Input Tokens, Output Tokens, Cache Read Tokens, Cache Creation Tokens

Фильтрует по API Key Name: Claude code (MAX), Claude code (fast), New Claude code (MAX)
"""

import pandas as pd
from dateutil.relativedelta import relativedelta

INPUT_FILE = "datasets/usage_2025-11-05_to_2026-05-31.csv"
OUTPUT_FILE = "datasets/claude_code_usage_kv_cache_loss_study.csv"

KEEP_COLUMNS = [
    "Time",
    "Input Tokens",
    "Output Tokens",
    "Cache Read Tokens",
    "Cache Creation Tokens",
]

FILTER_VALUES = {
    "Claude code (MAX)",
    "Claude code (fast)",
    "New Claude code (MAX)",
}


def main():
    df = pd.read_csv(INPUT_FILE)
    print(f"Загружено {len(df)} строк")

    # Фильтрация по API Key Name
    df_filtered = df[df["API Key Name"].isin(FILTER_VALUES)]
    print(f"После фильтрации: {len(df_filtered)} строк")

    # Вычитаем 2 месяца из даты
    df_filtered = df_filtered.copy()
    df_filtered["Time"] = pd.to_datetime(df_filtered["Time"]).apply(
        lambda dt: dt - relativedelta(months=2)
    )

    # Оставляем только нужные столбцы
    df_result = df_filtered[KEEP_COLUMNS]

    # Сохраняем
    df_result.to_csv(OUTPUT_FILE, index=False)
    print(f"Сохранено в {OUTPUT_FILE}")
    print(f"Столбцы: {list(df_result.columns)}")
    print(f"\nПервые 5 строк:")
    print(df_result.head())


if __name__ == "__main__":
    main()
