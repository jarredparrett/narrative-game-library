#!/usr/bin/env python3
"""PROTOTYPE — interactive shell for the task-hardening outer loop."""

from __future__ import annotations

import json
from pathlib import Path
import sys

from task_hardening_outer_loop_prototype_logic import (
    STAGES,
    advance,
    run_to_terminal,
    scenarios,
)


BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
YELLOW = "\x1b[33m"


def _verdict(status: str) -> str:
    if status == "accepted":
        return f"{GREEN}{status.upper()}{RESET}"
    if status == "running":
        return f"{YELLOW}{status.upper()}{RESET}"
    return f"{RED}{status.upper()}{RESET}"


def render(contract: dict, state: dict, index: int, total: int) -> None:
    print("\033[2J\033[H", end="")
    print(f"{BOLD}FAILURE-DRIVEN TASK HARDENING — LOGIC PROTOTYPE{RESET}")
    print(f"{DIM}Case {index + 1}/{total} · no persistence · no model calls{RESET}\n")
    print(f"{BOLD}scenario{RESET}: {state['scenario']}")
    print(f"{BOLD}expected terminal{RESET}: {state['expected_terminal']}")
    print(f"{BOLD}status{RESET}: {_verdict(state['status'])}")
    print(f"{BOLD}current stage{RESET}: {state['stage']}")
    print(f"{BOLD}route{RESET}: {state['route'] or 'not decided'}")
    print(
        f"{BOLD}contract{RESET}: {state['contract_ref'][:24]}…  "
        f"{BOLD}receipts{RESET}: {len(state['receipts'])}  "
        f"{BOLD}lineage edges{RESET}: {len(state['lineage_edges'])}/{len(contract['required_lineage'])}"
    )

    print(f"\n{BOLD}frozen comparison{RESET}")
    print(f"  panel:      {state['baseline']['panel_ref']}")
    print(f"  instrument: {state['baseline']['instrument_ref']}")
    print(
        "  resolution reliability: "
        f"baseline {state['baseline']['resolution_reliability_interval']}  "
        f"child {state['child']['resolution_reliability_interval']}"
    )
    print(
        "  handoff failure:        "
        f"baseline {state['baseline']['handoff_failure_interval']}  "
        f"child {state['child']['handoff_failure_interval']}  "
        f"paired Δ {state['child']['targeted_delta_interval']}"
    )
    failed_gates = [
        key for key, passed in state["admission"]["gate_results"].items() if not passed
    ]
    print(f"  Admission:  {'all pass' if not failed_gates else ', '.join(failed_gates)}")
    print(
        f"  sealed:     {state['sealed']['result']} "
        f"(contents exposed={state['sealed']['contents_exposed']})"
    )

    print(f"\n{BOLD}transition history{RESET}")
    if state["history"]:
        print("  " + " -> ".join(state["history"][-6:]))
    else:
        print("  none")
    print(f"\n{BOLD}blockers{RESET}")
    if state["blockers"]:
        for blocker in state["blockers"]:
            print(f"  - {blocker}")
    else:
        print("  - none")

    if state["status"] == "running":
        print(f"\n{DIM}Next action evaluates {state['stage']}.{RESET}")
    else:
        matched = state["status"] == state["expected_terminal"]
        word = f"{GREEN}YES{RESET}" if matched else f"{RED}NO{RESET}"
        print(f"\n{BOLD}matches expected terminal{RESET}: {word}")
    print(
        f"\n{BOLD}[a]{RESET} advance  {BOLD}[r]{RESET} reset  "
        f"{BOLD}[n]{RESET} next case  {BOLD}[p]{RESET} previous  "
        f"{BOLD}[j]{RESET} JSON  {BOLD}[q]{RESET} quit"
    )


def run_all(contract: dict, cases: list[dict]) -> int:
    failures = 0
    for case in cases:
        result = run_to_terminal(contract, case)
        matched = result["status"] == result["expected_terminal"]
        mark = "PASS" if matched else "FAIL"
        print(
            f"{mark:4}  {result['scenario']} -> {result['status']} "
            f"({len(result['receipts'])}/{len(STAGES)} transitions)"
        )
        failures += not matched
    return 1 if failures else 0


def main() -> int:
    root = Path(__file__).resolve().parent
    contract = json.loads(
        (root / "task-hardening-outer-loop-v1.prototype.json").read_text()
    )
    cases = scenarios(contract)
    if "--all" in sys.argv:
        return run_all(contract, cases)

    index = 0
    state = cases[index]
    while True:
        render(contract, state, index, len(cases))
        choice = input("> ").strip().lower()
        if choice == "q":
            return 0
        if choice == "a":
            state = advance(contract, state)
        elif choice == "r":
            state = scenarios(contract)[index]
        elif choice == "n":
            index = (index + 1) % len(cases)
            state = scenarios(contract)[index]
        elif choice == "p":
            index = (index - 1) % len(cases)
            state = scenarios(contract)[index]
        elif choice == "j":
            print(json.dumps(state, indent=2))
            input("press enter to continue")


if __name__ == "__main__":
    raise SystemExit(main())
