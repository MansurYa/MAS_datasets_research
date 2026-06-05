#!/usr/bin/env python3
"""Запуск парсера Claude Code Usage."""
from work.MAS_errors.parsers.claude_code_usage.parser import run

def run_all() -> None:
    run()

if __name__ == "__main__":
    run_all()