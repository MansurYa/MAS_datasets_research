# ТЗ №4.7 — Подгонка тяжёлых хвостов и финальная сводная таблица

**Дата:** 2026-05-06

## 1. Результаты подгонки всех распределений

### 1.1 `tool_web_failure` / `nebius` (n=26379, KS-тест информативен (n>>3000))

**absolute:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| exponential | 2.0000, 17.4064 | 0.1480 | 0.0000 | ✗ |
| weibull_min | 1.0398, 0.0000, 19.7753 | 0.1044 | 0.0000 | ✗ |
| lognorm | 0.9778, 0.0000, 12.4067 | 0.1284 | 0.0000 | ✗ |
| pareto | 0.5479, 0.0000, 2.0000 | 0.3046 | 0.0000 | ✗ |
| gamma | 1.2582, 0.0000, 15.4242 | 0.0855 | 0.0000 | ✗ |
| lomax | 11.1861, 0.0000, 194.7230 | 0.1446 | 0.0000 | ✗ |

**normalized:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| exponential | 0.0032, 0.3923 | 0.1208 | 0.0000 | ✗ |
| weibull_min | 1.4284, 0.0000, 0.4327 | 0.0620 | 0.0000 | ✗ |
| lognorm | 0.9955, 0.0000, 0.2793 | 0.1177 | 0.0000 | ✗ |
| beta | 0.9915, 1.5028, 0.0032, 0.9905 | 0.0185 | 0.0000 | ✗ |
| uniform | 0.0032, 0.9900 | 0.1563 | 0.0000 | ✗ |
| pareto | 0.2242, 0.0000, 0.0032 | 0.3882 | 0.0000 | ✗ |
| gamma | 1.5829, 0.0000, 0.2499 | 0.0779 | 0.0000 | ✗ |
| lomax | 43475093949654.0000, 0.0000, 17197459188347.6055 | 0.1219 | 0.0000 | ✗ |

### 1.2 `resource_not_found` / `nebius` (n=33565, KS-тест информативен (n>>3000))

**absolute:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| exponential | 2.0000, 11.1856 | 0.0893 | 0.0000 | ✗ |
| weibull_min | 1.2664, 0.0000, 14.3155 | 0.1060 | 0.0000 | ✗ |
| lognorm | 0.8072, 0.0000, 9.5762 | 0.1053 | 0.0000 | ✗ |
| pareto | 0.6385, 0.0000, 2.0000 | 0.2832 | 0.0000 | ✗ |
| gamma | 1.7110, 0.0000, 7.7063 | 0.0971 | 0.0000 | ✗ |
| lomax | 6879259383091.1924, 0.0000, 90707024836581.9375 | 0.1873 | 0.0000 | ✗ |

**normalized:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| exponential | 0.0025, 0.2909 | 0.0592 | 0.0000 | ✗ |
| weibull_min | 1.2347, 0.0000, 0.3147 | 0.0393 | 0.0000 | ✗ |
| lognorm | 0.9756, 0.0000, 0.1985 | 0.0499 | 0.0000 | ✗ |
| beta | 0.9316, 2.4917, 0.0025, 1.1033 | 0.0584 | 0.0000 | ✗ |
| uniform | 0.0025, 0.9878 | 0.3337 | 0.0000 | ✗ |
| pareto | 0.2288, 0.0000, 0.0025 | 0.4054 | 0.0000 | ✗ |
| gamma | 1.4235, 0.0000, 0.2061 | 0.0308 | 0.0000 | ✗ |
| lomax | 13657881869456.3789, 0.0000, 4007197326207.0059 | 0.0651 | 0.0000 | ✗ |

### 1.3 `tool_timeout` / `itbench` (n=80, ⚠️ низкая мощность KS-теста)

**absolute:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| weibull_min | 1.5640, 0.0000, 50.2876 | 0.1288 | 0.1286 | ✓ |
| gamma | 2.0269, 0.0000, 22.2818 | 0.1487 | 0.0523 | ✓ |
| lognorm | 0.7976, 0.0000, 34.5962 | 0.1779 | 0.0110 | ⚠ |
| exponential | 9.0000, 36.1625 | 0.1782 | 0.0108 | ⚠ |
| lomax | 26270110267956.7031, 0.0000, 1186423950900159.2500 | 0.1807 | 0.0093 | ⚠ |
| pareto | 0.7427, 0.0000, 9.0000 | 0.2634 | 0.0000 | ⚠ |

**normalized:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| beta | 1.3434, 109.1127, 0.0247, 17.0317 | 0.0584 | 0.9326 | ✓ |
| gamma | 1.9958, 0.0000, 0.1162 | 0.0708 | 0.7913 | ✓ |
| lognorm | 0.7636, 0.0000, 0.1768 | 0.0794 | 0.6641 | ✓ |
| weibull_min | 1.4217, 0.0000, 0.2567 | 0.0863 | 0.5614 | ✓ |
| exponential | 0.0266, 0.2053 | 0.1095 | 0.2728 | ✓ |
| lomax | 12104982424417.0078, 0.0000, 2806904797605.3828 | 0.1604 | 0.0289 | ⚠ |
| uniform | 0.0266, 0.8629 | 0.4696 | 0.0000 | ⚠ |
| pareto | 0.5282, 0.0000, 0.0266 | 0.3135 | 0.0000 | ⚠ |

### 1.4 `permission_error` / `terminalbench` (n=267, ⚠️ умеренная мощность)

**absolute:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| lognorm | 0.7507, 0.0000, 13.0739 | 0.1416 | 0.0000 |  |
| exponential | 3.0000, 15.5243 | 0.1618 | 0.0000 |  |
| weibull_min | 1.1405, 0.0000, 19.6198 | 0.1719 | 0.0000 |  |
| pareto | 0.6793, 0.0000, 3.0000 | 0.3194 | 0.0000 |  |
| gamma | 1.5809, 0.0000, 11.7174 | 0.1947 | 0.0000 |  |
| lomax | 13.6771, 0.0000, 234.4275 | 0.2361 | 0.0000 |  |

**normalized:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| weibull_min | 1.8824, 0.0000, 0.4875 | 0.0376 | 0.8302 | ✓ |
| beta | 1.1352, 1.8285, 0.0484, 1.0058 | 0.0557 | 0.3645 | ✓ |
| gamma | 2.7511, 0.0000, 0.1572 | 0.0701 | 0.1387 | ✓ |
| lognorm | 0.6823, 0.0000, 0.3568 | 0.1105 | 0.0027 |  |
| exponential | 0.0494, 0.3832 | 0.1791 | 0.0000 |  |
| uniform | 0.0494, 0.9506 | 0.2075 | 0.0000 |  |
| pareto | 0.5057, 0.0000, 0.0494 | 0.3342 | 0.0000 |  |
| lomax | 52431160927563.2500, 0.0000, 22680189783861.2109 | 0.2105 | 0.0000 |  |

### 1.5 `memory_error` / `terminalbench` (n=1750, ⚠️ умеренная мощность)

**absolute:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| exponential | 1.0000, 19.3794 | 0.2663 | 0.0000 |  |
| weibull_min | 0.7714, 0.0000, 17.1342 | 0.1429 | 0.0000 |  |
| lognorm | 1.3632, 0.0000, 8.6379 | 0.1750 | 0.0000 |  |
| pareto | 0.4638, 0.0000, 1.0000 | 0.2143 | 0.0000 |  |
| gamma | 0.7036, 0.0000, 28.9661 | 0.1535 | 0.0000 |  |
| lomax | 2.0835, 0.0000, 24.0380 | 0.1632 | 0.0000 |  |

**normalized:**
| distribution | params | KS_stat | KS_p | ok |
|---|---|---|---|---|
| exponential | 0.0011, 0.3627 | 0.1269 | 0.0000 |  |
| weibull_min | 0.9211, 0.0000, 0.3517 | 0.1227 | 0.0000 |  |
| lognorm | 1.4775, 0.0000, 0.1788 | 0.1599 | 0.0000 |  |
| beta | 0.6733, 1.5133, 0.0011, 1.1148 | 0.0888 | 0.0000 |  |
| uniform | 0.0011, 0.9989 | 0.2464 | 0.0000 |  |
| pareto | 0.1959, 0.0000, 0.0011 | 0.3355 | 0.0000 |  |
| gamma | 0.8312, 0.0000, 0.4376 | 0.1229 | 0.0000 |  |
| lomax | 25003408654697.2383, 0.0000, 9095739407215.1055 | 0.1247 | 0.0000 |  |

## 2. Q-Q plots для лучшего распределения

Q-Q plot сравнивает эмпирические квантили с теоретическими. Точки на диагонали — хорошая подгонка.

**tool_web_failure / nebius — absolute**
![tool_web_failure/nebius/absolute](data/plots/qq_tool_web_failure_nebius_absolute.png)

**tool_web_failure / nebius — normalized**
![tool_web_failure/nebius/normalized](data/plots/qq_tool_web_failure_nebius_normalized.png)

**resource_not_found / nebius — absolute**
![resource_not_found/nebius/absolute](data/plots/qq_resource_not_found_nebius_absolute.png)

**resource_not_found / nebius — normalized**
![resource_not_found/nebius/normalized](data/plots/qq_resource_not_found_nebius_normalized.png)

**tool_timeout / itbench — absolute**
![tool_timeout/itbench/absolute](data/plots/qq_tool_timeout_itbench_absolute.png)

**tool_timeout / itbench — normalized**
![tool_timeout/itbench/normalized](data/plots/qq_tool_timeout_itbench_normalized.png)

**permission_error / terminalbench — absolute**
![permission_error/terminalbench/absolute](data/plots/qq_permission_error_terminalbench_absolute.png)

**permission_error / terminalbench — normalized**
![permission_error/terminalbench/normalized](data/plots/qq_permission_error_terminalbench_normalized.png)

**memory_error / terminalbench — absolute**
![memory_error/terminalbench/absolute](data/plots/qq_memory_error_terminalbench_absolute.png)

**memory_error / terminalbench — normalized**
![memory_error/terminalbench/normalized](data/plots/qq_memory_error_terminalbench_normalized.png)

## 3. Финальные выводы по распределениям

| error | dataset | n | position | conclusion | fit_type |
|---|---|---|---|---|---|
| tool_web_failure | nebius | 26379 | absolute | no_parametric_fit: эмпирическое распределение | непригодно |
| tool_web_failure | nebius | 26379 | normalized | no_parametric_fit: эмпирическое распределение | непригодно |
| resource_not_found | nebius | 33565 | absolute | no_parametric_fit: эмпирическое распределение | непригодно |
| resource_not_found | nebius | 33565 | normalized | no_parametric_fit: эмпирическое распределение | непригодно |
| tool_timeout | itbench | 80 | absolute | best_fit: weibull_min (p=0.1286, ⚠️ низкая мощность) | ориентировочно |
| tool_timeout | itbench | 80 | normalized | best_fit: beta (p=0.9326, ⚠️ низкая мощность) | ориентировочно |
| permission_error | terminalbench | 267 | absolute | inconclusive: формальное отвержение | неопределённо |
| permission_error | terminalbench | 267 | normalized | best_fit: weibull_min (p=0.8302) | пригодно (с оговоркой) |
| memory_error | terminalbench | 1750 | absolute | inconclusive: формальное отвержение | неопределённо |
| memory_error | terminalbench | 1750 | normalized | inconclusive: формальное отвержение | неопределённо |

**fit_type:** пригодно = KS p ≥ 0.05, информативный тест (n ≥ 3000).

## 4. Рекомендации для симулятора (ошибки классов 2–3)

### Класс 2 — Моделируется напрямую

**`tool_timeout`** (keyword_search_itbench):
- P(traj)=0.7619, P(msg)=0.094288
- Распределение: inconclusive: низкая мощность теста, данных недостаточно | inconclusive: низкая мощность теста, данных недостаточно
- Рекомендация: Использовать эмпирическое распределение нормализованной позиции. P(traj)=0.76 высока, ошибка систематически происходит. Weibull(1.42, 0, 0.26) даёт приемлемую аппроксимацию при n=80.

### Класс 3 — Моделируется статистически

**`guardrails_triggered`** (magentic_one):
- P(traj)=0.5227, P(msg)=0.008019
- Распределение: from AgentRx/Who&When
- Рекомендация: P(traj)=0.5227, P(msg)=0.008019.

**`invalid_invocation`** (magentic_one):
- P(traj)=0.0227, P(msg)=0.000334
- Распределение: from AgentRx/Who&When
- Рекомендация: P(traj)=0.0227, P(msg)=0.000334.

**`system_failure`** (magentic_one):
- P(traj)=0.0227, P(msg)=0.000334
- Распределение: from AgentRx/Who&When
- Рекомендация: P(traj)=0.0227, P(msg)=0.000334.

**`invalid_invocation`** (tau_retail):
- P(traj)=0.0690, P(msg)=0.003759
- Распределение: from AgentRx/Who&When
- Рекомендация: P(traj)=0.0690, P(msg)=0.003759.

**`system_failure`** (tau_retail):
- P(traj)=0.0345, P(msg)=0.000940
- Распределение: from AgentRx/Who&When
- Рекомендация: P(traj)=0.0345, P(msg)=0.000940.

**`tool_web_failure`** (who_and_when):
- P(traj)=0.1359, P(msg)=0.006354
- Распределение: from AgentRx/Who&When
- Рекомендация: Эмпирическое распределение (все параметрические отвергнуты). P(traj)=0.1359, P(msg)=0.006354.

**`resource_abuse`** (who_and_when):
- P(traj)=0.0489, P(msg)=0.002199
- Распределение: from AgentRx/Who&When
- Рекомендация: P(traj)=0.0489, P(msg)=0.002199.

**`tool_web_failure`** (keyword_search_nebius):
- P(traj)=0.3296, P(msg)=0.022469
- Распределение: no_parametric_fit: рекомендуется эмпирическое распределение | no_parametric_fit: рекомендуется эмпирическое распределение
- Рекомендация: Эмпирическое распределение (все параметрические отвергнуты). P(traj)=0.3296, P(msg)=0.022469.

**`resource_not_found`** (keyword_search_nebius):
- P(traj)=0.4194, P(msg)=0.049727
- Распределение: no_parametric_fit: рекомендуется эмпирическое распределение | no_parametric_fit: рекомендуется эмпирическое распределение
- Рекомендация: Эмпирическое распределение (все параметрические отвергнуты). P(traj)=0.4194, P(msg)=0.049727.

**`permission_error`** (keyword_search_terminalbench):
- P(traj)=0.0051, P(msg)=0.000409
- Распределение: inconclusive: формальное отвержение при умеренной мощности | best_fit_available: 3/8 not rejected
- Рекомендация: best_fit: weibull_min (p=0.8302). P(traj)=0.0051, P(msg)=0.000409.

**`memory_error`** (keyword_search_terminalbench):
- P(traj)=0.0336, P(msg)=0.012443
- Распределение: inconclusive: формальное отвержение при умеренной мощности | inconclusive: формальное отвержение при умеренной мощности
- Рекомендация: Приближённо inconclusive: формальное отвержение (⚠️ малая выборка). P(traj)=0.0336, P(msg)=0.012443.

## 5. Ограничения

1. **Тяжёлые хвосты:** nebius-категории имеют длинные хвосты (max=594 при median=14). Pareto и Lomax дают физически нереалистичные параметры (scale~10^13), что указывает на нестабильность MLE при данных значениях.
2. **KS-тест при n>>3000:** отвержение H0 для всех 8 распределений означает, что простые аналитические формы не описывают данные. Это не недостаток данных, а ограничение параметрического подхода — рекомендуется эмпирическое CDF.
3. **KS-тест при n<100:** для ITBench (n=80) и TerminalBench (n=267) мощность теста ограничена. Результаты носят ориентировочный характер.
4. **Все fit-функции используют floc=0** (фиксированный сдвиг loc=0). Для данных, начинающихся не с 0, это может давать смещённые оценки.