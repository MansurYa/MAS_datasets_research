"""Запускает ВСЕ парсеры всех датасетов."""
from work.MAS_errors.parsers.trail.run_all import run_all as run_trail
from work.MAS_errors.parsers.agentRx.run_all import run_all as run_agentrx
from work.MAS_errors.parsers.who_and_when.run_all import run_all as run_whowhen

def run_all() -> None:
    print("=== TRAIL ===")
    run_trail()
    print("\n=== AgentRx ===")
    run_agentrx()
    print("\n=== Who_and_When ===")
    run_whowhen()
    print("\n=== ВСЕ парсеры завершены ===")

if __name__ == "__main__":
    run_all()