"""Запускает все парсеры AgentRx."""
from work.MAS_errors.parsers.agentRx.magentic_one.parser import run as run_m1
from work.MAS_errors.parsers.agentRx.tau_retail.parser import run as run_tr

def run_all() -> None:
    run_m1()
    run_tr()

if __name__ == "__main__":
    run_all()