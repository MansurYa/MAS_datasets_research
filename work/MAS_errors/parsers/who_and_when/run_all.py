"""Запускает все парсеры Who_and_When."""
from work.MAS_errors.parsers.who_and_when.parser import run as run_ww

def run_all() -> None:
    run_ww()

if __name__ == "__main__":
    run_all()