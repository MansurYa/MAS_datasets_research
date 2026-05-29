# datasets/ — Датасеты Hugging Face

Агентные траектории из 9 источников. Не загружать целиком без необходимости — файлы большие.

| Папка | Домен | Размер | Типизация ошибок |
|-------|-------|--------|-----------------|
| `TRAIL/` | Multi-Domain | — | **Да** (836 ошибок, экспертная разметка) |
| `Kevin355-Who_and_When/` | Multi-Agent | 52MB | **Да** (только HC-сплит, 58 записей) |
| `microsoft-AgentRx/` | Multi-Domain | 7.1MB | **Да** (failure_category, root_cause) |
| `nebius-SWE-agent-trajectories/` | SE/Terminal | 1.0GB | Нет |
| `SWE-Gym-OpenHands-Sampled-Trajectories/` | SE | 289MB | Нет |
| `yoonholee-terminalbench-trajectories/` | Terminal | 213MB | Нет |
| `ibm-research-ITBench-Trajectories/` | SRE | 165MB | Нет |
| `iMeanAI-Mind2Web-Live/` | Web Agents | 3.3MB | Нет |
| `AI45Research-ATBench-Claw/` | — | — | — |

**Важно:** Who&When — только Hand-Crafted сплит (58 записей). Algorithm-Generated (126) — синтетические, исключены из анализа.
