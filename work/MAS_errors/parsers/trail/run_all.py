"""Запускает все парсеры TRAIL."""
from work.MAS_errors.parsers.trail.parser import run as run_trail

def run_all() -> None:
    run_trail()

if __name__ == "__main__":
    run_all()