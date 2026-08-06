# Winter Observatory six-player playtest preparation

Status: **awaiting six distinct human players and one host**

The exact human-play package was prepared on 2026-08-06 from selected Candidate 6. It is a child Candidate because the six deep Dossiers replace the earlier short dossier Resources. No human responses, scores, findings, or standing have been invented.

## Exact lineage

- Parent Candidate: `sha256:130fe43a5596ad26458b31859e31951fc3b9d4f6925b1bf58cc55a95427404b6`
- Parent Release: `sha256:f4892894e4503c5f4e69cdfea350a9a1f233ccfbc391fd46a084d0860d0857bd`
- Playtest Candidate: `sha256:f1d0425d76d7c30d39f0c0adacb45358c5fe8eba5c845f20249c53747a6fc767`
- Playtest Release: `sha256:5d170735b396081142eb22a4b33c0479fe5bb089770a837268d0c658c05fb998`
- Physical Export: `sha256:9cd7267b39f7fa88a1edbfb2bd188f1df1f7b84e72ef3b2b56b249b1bc67b463`
- Character Program: `character-program:ba341b17cc066b91d93903c6c8103a2f3d906b0e49746449b7df2c74b5f385ac`
- Frozen Instrument: `instrument:22df667df25d2399cdaaca4faaecacf691d6cb398c42e0db7bd36315b7d9b850`
- Playtest Protocol: `playtest-protocol:1bd2ef9487895b3453de0ffe0aeb91ea2e6e66a1ba9b84ea3ea7ba8266c3ea0f`
- Seed: `19370117`

The preparation Workspace verifies cleanly. Dossier page counts are Eleanor 4, Felix 5, Lillian 4, Ruth 4, Samuel 4, and Thomas 4.

Preparation v2 supersedes v1. The Candidate and produced game bytes did not
change; v2 freezes the clarified positive-direction cognitive-load wording and
adds the closed-ledger recording manifest.

## Human boundary

The kit freezes all ten issue #17 rubric dimensions, consent v1, six Seat assignments, pre-game comprehension, timestamped host observations in every Phase, individual post-game responses, group debrief, and the defect-owner taxonomy: dossier, evidence, hosting, pacing, and UI.

The next authorized action is recruitment and scheduling. A `PlaytestRun` may be recorded only after actual humans supply affirmative consent, a resolved live Session history, exact responses and quotes, scores for every dimension, and the production receipt. Findings require human review before becoming answer-safe Requirements; a child needs fresh remeasurement before improved standing.

## Record a completed Run

Copy `recording-manifest.example.json` to `recording-manifest.json`, replace
every placeholder with the actual Session principals and cohort key, and place
the completed Session, production, consent, and observation JSON files under
`completed/`. Then run:

```bash
narrative-game-playtest-record ./experiment ./recording-manifest.json
```

The command rejects paths outside the bundle, preflights all Authorities,
Findings, and the Run as one closed ledger, and writes nothing when validation
fails. A successful idempotent replay returns the same Run ID and leaves one
Run in the Experiment.

## Reproduce the preparation

```bash
uv run narrative-game-playtest-prepare \
  /path/to/new-playtest-directory \
  --parent-release /path/to/candidate-6/game-release.zip
```

The command refuses a non-empty output directory and rejects a parent Release whose canonical game is not the selected Candidate 6 game.
