from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_path: str = "work/MAS_errors/LOG.txt") -> logging.Logger:
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s PID%(process)d %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    if not any(isinstance(h, logging.FileHandler) for h in root.handlers):
        root.addHandler(file_handler)

    return logging.getLogger("MAS_errors")
