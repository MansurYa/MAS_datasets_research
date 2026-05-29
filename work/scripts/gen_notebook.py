#!/usr/bin/env python3
"""Генератор notebook для просмотра логов nebius + ошибок из JSON."""

import json
from pathlib import Path

PARQUET_DIR = "datasets/nebius-SWE-agent-trajectories/data/"
JSON_FILE = "work/data/TZ_2_candidates_A.json"

NOTEBOOK = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0"
        }
    },
    "cells": [
        {
            "cell_type": "code",
            "metadata": {},
            "source": "# Пути к данным\nfrom pathlib import Path\nimport os\n\n# Определяем корень проекта по местоположению notebook-файла\n# (notebook лежит в work/, поднимаемся на один уровень вверх)\nNOTEBOOK_PATH = Path(r\"/Volumes/MansurSSD/MAS_datasets_research/work/nebius_review.ipynb\")\nPROJECT_ROOT = NOTEBOOK_PATH.resolve().parent.parent\n\nPARQUET_DIR = PROJECT_ROOT / \"datasets\" / \"nebius-SWE-agent-trajectories\" / \"data\"\nJSON_FILE = PROJECT_ROOT / \"work\" / \"data\" / \"TZ_2_candidates_A.json\"\n\nos.chdir(PROJECT_ROOT)\nprint(\"Проект: \" + str(PROJECT_ROOT))\nprint(\"cwd:    \" + os.getcwd())\n"
        },
        {
            "cell_type": "code",
            "metadata": {},
            "source": "import json\n\nwith open(JSON_FILE) as f:\n    errors = json.load(f)\n\nprint(\"Ошибок в файле: \" + str(len(errors)))\nprint(\"\\nПервые 5:\")\nfor e in errors[:5]:\n    print(\"  \" + e[\"instance_id\"] + \"  step=\" + str(e.get(\"step_idx\")))\n"
        },
        {
            "cell_type": "code",
            "metadata": {},
            "source": "import pyarrow.dataset as ds\n\n# instance_id берём из errors (ячейка 2)\nINSTANCE_ID = \"AnalogJ__lexicon-336\"\n\ndataset = ds.dataset(PARQUET_DIR, format=\"parquet\")\ntable = dataset.to_table(filter=ds.field(\"instance_id\") == INSTANCE_ID)\n\nif len(table) > 0:\n    d = table.to_pydict()\n    traj_list = d[\"trajectory\"]\n    # trajectory = list[list[step_dict]] — берём первый элемент\n    steps = traj_list[0]\n    print(\"Траектория: \" + INSTANCE_ID)\n    print(\"Всего шагов: \" + str(len(steps)))\nelse:\n    print(\"Траектория не найдена\")\n    steps = None\n"
        },
        {
            "cell_type": "code",
            "metadata": {},
            "source": "# STEP_IDX берём из errors (ячейка 2)\nSTEP_IDX = 29\n\nif steps is None:\n    print(\"Нет данных — сначала выполни ячейку 3\")\nelif STEP_IDX >= len(steps):\n    print(\"STEP_IDX=\" + str(STEP_IDX) + \" за пределами (шагов: \" + str(len(steps)) + \")\")\nelse:\n    step = steps[STEP_IDX]\n    print(\"=== Шаг \" + str(STEP_IDX) + \" ===\")\n    # Поле 'text' содержит содержимое шага (не model_message)\n    text = step.get(\"text\", \"\") or \"\"\n    print(\"Длина: \" + str(len(text)))\n    print(text[:500] if text else \"(пусто)\")\n"
        },
        {
            "cell_type": "code",
            "metadata": {},
            "source": "INST = \"AnalogJ__lexicon-336\"\nmatching = [e for e in errors if e[\"instance_id\"] == INST]\nprint(\"Ошибок для '\" + INST + \"': \" + str(len(matching)))\nfor e in matching:\n    idx = e.get(\"step_idx\") or e.get(\"first_step_idx\")\n    txt = e.get(\"text\", \"\")[:80]\n    print(\"  step=\" + str(idx) + \": \" + txt + \"...\")\n"
        },
    ]
}


def save(path="work/nebius_review.ipynb"):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(NOTEBOOK, f, indent=1, ensure_ascii=False)
    print("Сохранено: " + str(out))


if __name__ == "__main__":
    save()