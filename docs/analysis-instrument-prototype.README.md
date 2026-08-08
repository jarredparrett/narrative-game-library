# Frozen Analysis Instrument logic prototype

**PROTOTYPE — THROW AWAY.** This answers one question: does a concrete roster,
view, prompt, output, retry, and receipt contract make the already-decided
analysis authority boundaries mechanically inspectable before runtime
implementation?

Run from the repository root:

```bash
python3 docs/analysis_instrument_prototype_tui.py
```

Use `n` and `p` to move through a valid lineage and seven deliberately invalid
ones. The TUI shows the full relevant state and the deterministic eligibility
findings after each action. The JSON instrument is illustrative but exact; it
freezes the proposed v1 roster and contracts for review. It does not call a
model, persist state, or implement the production analysis runtime.

The validated decision belongs on `main`; these prototype files remain on the
throwaway branch linked from the Wayfinder ticket.
