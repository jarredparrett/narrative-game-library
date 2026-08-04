# Working in narrative-game-library

This repository implements a deterministic narrative-game library above
Verismill. Keep these boundaries intact:

- `contracts`, `kernel`, `compiler`, and runtime reducers are pure.
- effects belong to Workspace, adapters, experiments, CLI, and output writers.
- normal document work goes through the public Verismill Artifact Forge
  adapter; do not import Mattermill directly from game-owned code.
- never import Verismill private modules or read its object store or bus.
- authoring and experiment state is user data and must not be committed.
- every accepted requirement has one attributable capability test.
- same version, component lock, seed, and inputs must produce byte-identical
  deterministic outputs across processes and offline.
- agents propose; humans approve canonical changes and standing.
- never let a builder or fixer certify its own blind measurement.

Before committing, run `uv run pytest -q` and verify the current stage against
`docs/acceptance-matrix.md`.
