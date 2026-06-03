# Аудит-отчёт: UNDERPOWERED

## Условия исследования

| Параметр | Значение |
|---|---|
| Распределение | W3 |
| N (полный) | 847 |
| N_fit / N_test | 0 / 847 |
| Ветвь | UNDERPOWERED |
| Инженерный допуск ε | 0.03 |
| Уровень значимости α | 0.05 |
| Целевая мощность | 0.8 |
| Версия | Методология 2.0 / scipy 1.17.1 |
| Время | 0.00 сек |
| Хэш данных | `1aff1c3c79b3e191...` |
| График |  |

## Вердикт: UNDERPOWERED




Анализ ЗАБЛОКИРОВАН: данных недостаточно для вывода.

## Статистика

| Метрика | Значение | Интерпретация |
|---|---|---|
| D_obs | 0.0000 | Макс. отклонение ECDF от CDF |
| p_value | N/A | Односторонний p-value |
| p_final | N/A | Meinshausen: 2 × median(p₁..p_K) |
| p_LRT | N/A | LRT 2P vs 3P |
| Skewness | N/A | Бутстреп-асимметрия (порог: 0.5) |
| N_min / N_max | 3600 / 1000000 | Режим: UNDERPOWERED |

## Параметры модели

| Параметр | Оценка | Метод | ДИ или статус |
|---|---|---|---|


## Статус-коды

Нет

## Предупреждения

- pilot_study

## Трассировка решений

| Шаг | Компонент | Действие | Результат |
|---|---|---|---|
| 1 | utils | check_scipy_version | OK |
| 2 | utils | check_dependency_constraints | OK |
| 3 | utils | compute_data_hash | 1aff1c3c79b3e191... |
| 4 | select | scale_selector | mode=UNDERPOWERED |
| 5 | validate | Branch UNDERPOWERED | UNDERPOWERED |


## Рисунок

![Fit visualization]()

*Рис. 1.* ECDF (синяя ступенчатая) vs Theoretical CDF (красная гладкая).
Shaded region — область максимального отклонения.
D_obs=0.0000, verdict=UNDERPOWERED.

## Математические источники


| Метод | Источник |
|---|---|
| KS D*, K(x) | Буре, Парилина (2018), §2.2.2, формулы (2.2.2)–(2.2.3) |
| Модифицированные статистики | Буре, Парилина (2018), §2.2.4, Табл. 2.1–2.2 |
| LRT | Буре, Парилина (2018), (3.2.25) |
| Kaplan-Meier | Kaplan & Meier (1958) |
| TOST / DKW | Dvoretzky, Kiefer, Wolfowitz (1956) |
| Meinshausen correction | Meinshausen & Bühlmann (2009), JASA 101(476) |
| Профильное MLE | Cohen & Whitten (1980); EnvStats doc |

