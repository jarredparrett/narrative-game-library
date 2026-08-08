# Failure-driven task-hardening logic prototype

**PROTOTYPE — THROW AWAY.** This answers one question: can a promoted
agent-capability or coordination Failure Class drive a targeted child task that
is measurably harder for the same fixed panel while remaining solvable,
coherent, authorized, non-leaking, and inside its frozen target band?

Run from the repository root:

```bash
python3 docs/task_hardening_outer_loop_prototype_tui.py
```

Use `a` to advance the current state machine, `n` and `p` to change cases, and
`j` to inspect the complete JSON state. The reference case traverses the full
lineage from baseline Episodes through accepted transition. The falsifying
cases demonstrate that game/runtime/evaluator defects route to repair,
uncertain ownership quarantines the signal, and defects, leakage, panel drift,
invalid-run inflation, target overshoot, missing targeted movement, sealed
regression, or self-review prevent acceptance.

The prototype makes no model calls and persists nothing. It uses illustrative
evidence values to test the transition logic; it does not claim that the worked
task has been generated or measured. The validated decision belongs on `main`.
These files remain on the throwaway branch linked from the Wayfinder ticket.
