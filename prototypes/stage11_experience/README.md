# Stage 11 experience prototype

**Question:** should the game-maker, host, player, and print experiences share
one product shell, or should they share only an authorized projection language?

Run the disposable study:

```bash
uv run python prototypes/stage11_experience/serve.py
```

Use the bottom arrows or `?variant=A|B|C`; switch roles with
`?surface=maker|host|player|print`.

- **A — Custody rail:** spacious authoring workspace organized around evidence
  timing and measurement.
- **B — Control room:** dense live state, event stream, requests, and host
  actions.
- **C — Artifact stack:** represented-world character material with a quieter
  chain-of-custody index.

## Verdict

Do not force all roles into one dashboard. Use A for the maker, B for the host,
and C for player and print handoff. Reuse the chain-of-custody rail, exact
Release/Session identity, phase vocabulary, and explicit authorization cues.
Keep mutation outside view rendering: surfaces emit typed action intents, and
the existing Experiment or Session authority decides whether they can occur.

This directory is a primary-source prototype. It is intentionally not the
shipping implementation.
