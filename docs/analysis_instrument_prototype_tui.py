#!/usr/bin/env python3
"""PROTOTYPE — interactive terminal shell for Analysis Instrument eligibility."""

from __future__ import annotations

import json
from pathlib import Path

from analysis_instrument_prototype_logic import scenarios, validate


BOLD = "\x1b[1m"
DIM = "\x1b[2m"
RESET = "\x1b[0m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"


def render(instrument, cases, index: int) -> None:
    state = validate(instrument, cases[index])
    print("\033[2J\033[H", end="")
    print(f"{BOLD}FROZEN ANALYSIS INSTRUMENT — LOGIC PROTOTYPE{RESET}")
    print(f"{DIM}Case {index + 1}/{len(cases)} · no persistence · no model calls{RESET}\n")
    print(f"{BOLD}scenario{RESET}: {state['scenario']}")
    print(f"{BOLD}instrument{RESET}: {state['instrument_ref'][:26]}…")
    print(f"{BOLD}assignments{RESET}: {state['complete_assignments']}/{state['assignment_count']} complete")
    verdict = f"{GREEN}ELIGIBLE{RESET}" if state["eligible"] else f"{RED}INELIGIBLE{RESET}"
    print(f"{BOLD}verdict{RESET}: {verdict}")
    print(f"{BOLD}finding_count{RESET}: {state['finding_count']}\n")
    print(f"{BOLD}findings{RESET}")
    if state["findings"]:
        for finding in state["findings"]:
            print(f"  - {finding}")
    else:
        print("  - none; every tested authority boundary is satisfied")
    print(f"\n{DIM}The deterministic validator establishes eligibility, not semantic truth.{RESET}")
    print(f"\n{BOLD}[n]{RESET} next  {BOLD}[p]{RESET} previous  {BOLD}[j]{RESET} JSON state  {BOLD}[q]{RESET} quit")


def main() -> None:
    root = Path(__file__).resolve().parent
    instrument = json.loads((root / "analysis-instrument-v1.prototype.json").read_text())
    cases = scenarios(instrument)
    index = 0
    while True:
        render(instrument, cases, index)
        choice = input("> ").strip().lower()
        if choice == "q":
            return
        if choice == "n":
            index = (index + 1) % len(cases)
        elif choice == "p":
            index = (index - 1) % len(cases)
        elif choice == "j":
            print(json.dumps(validate(instrument, cases[index]), indent=2))
            input("press enter to continue")


if __name__ == "__main__":
    main()
