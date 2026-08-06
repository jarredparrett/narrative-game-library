# Winter Observatory six-player playtest preparation

Status: **blind model baseline complete; awaiting two distinct six-player cohorts**

The exact human-play package was prepared on 2026-08-06 from selected Candidate 6. It is a child Candidate because the six deep Dossiers replace the earlier short dossier Resources. No human responses, scores, findings, or standing have been invented.

## Exact lineage

- Parent Candidate: `sha256:130fe43a5596ad26458b31859e31951fc3b9d4f6925b1bf58cc55a95427404b6`
- Parent Release: `sha256:f4892894e4503c5f4e69cdfea350a9a1f233ccfbc391fd46a084d0860d0857bd`
- Playtest Candidate: `sha256:f1d0425d76d7c30d39f0c0adacb45358c5fe8eba5c845f20249c53747a6fc767`
- Playtest Release: `sha256:5d170735b396081142eb22a4b33c0479fe5bb089770a837268d0c658c05fb998`
- Physical Export: `sha256:9cd7267b39f7fa88a1edbfb2bd188f1df1f7b84e72ef3b2b56b249b1bc67b463`
- Blind Trial: `sha256:11d6caf9ee177e73b2962bfcd984721b58957b1e4791ef6a867250380d8cd8eb`
- Trial Binding: `trial-binding:8c4854032c33ea686f9beb4cd003a0c2b90a4dd603df8f37feee4d790168f401`
- Character Program: `character-program:ba341b17cc066b91d93903c6c8103a2f3d906b0e49746449b7df2c74b5f385ac`
- Frozen Instrument: `instrument:22df667df25d2399cdaaca4faaecacf691d6cb398c42e0db7bd36315b7d9b850`
- Playtest Protocol: `playtest-protocol:50d7b5d363e4bd036568b51ecbfd55a6d8f1743f4a46d80feb78d4fe58c9a862`
- Seed: `19370117`

The preparation Workspace verifies cleanly. Dossier page counts are Eleanor 4, Felix 5, Lillian 4, Ruth 4, Samuel 4, and Thomas 4.

Preparation v7 supersedes v1-v6. The Candidate and produced game bytes did not
change; v2 froze the clarified positive-direction cognitive-load wording, v3
added the closed-ledger recording path, and v4 orders the host transcript so
players submit in the authored Resolution Phase before debrief. Version 5
exposed the previously missing comparison gap; v6 adds the configured blind
model baseline and independent Standing-review operator manifests. Its live
model evaluation then revealed that six dossier paths in the preflight schedule
did not name shipped files. Version 7 corrects only that Trial projection,
issues a fresh binding and Protocol, and preserves v6 as diagnostic evidence.

## Blind model baseline

The fresh v7 panel produced Evaluation
`evaluation:5b1fdbed784e9c3a4a76f760e69c72331ec9fae00e5dece63f9b9178c5b250d9`
with Model Receipt
`model-receipt:d6368bdef3deb2c43519a708e8808c78c03ae531521db025af62bd2a6fc60603`.
All three hard gates passed. Its overall mean was 70.2, below the frozen 75
acceptance threshold, so its outcome is honestly `fail`. Strongest dimensions
were role onboarding (82), post-exposure agency (82), and role recall (80);
the main predicted friction was host intervention (57), relationship clarity
(58), cognitive load (61), and reveal guidance (66). These are hypotheses for
human observation, not permission to rewrite the game before play.

## Human boundary

The kit freezes all ten issue #17 rubric dimensions, consent v1, six Seat assignments, pre-game comprehension, timestamped host observations in every Phase, individual post-game responses, group debrief, and the defect-owner taxonomy: dossier, evidence, hosting, pacing, and UI.

The blind model baseline is complete under the same frozen Instrument. The next
authorized action is recruitment and scheduling for two distinct six-player
cohorts and their distinct hosts. To reproduce a model panel under a new Task
and Authority, copy `model-panel.example.json`, configure the operator-selected
provider, model, and JSON-command driver, and run:

```bash
narrative-game-playtest-model-baseline ./experiment ./model-panel.json
```

The optional first-party Codex adapter is
`narrative-game-codex-judge-driver`; other providers implement the same
canonical stdin/stdout protocol. The adapter exposes only the extracted
anonymous Blind Trial in an ephemeral read-only directory and retains its CLI
event trace. Invalid structured output remains a failed Task/receipt without an
Evaluation. A retry must use a fresh Task key and judge Authority.

The resulting exact Evaluation ID is required for later model-human comparison.
It cannot confer human standing. A `PlaytestRun` may be recorded only after
actual humans supply affirmative consent, a resolved live Session history,
exact responses and quotes, scores for every dimension, and the production
receipt. The frozen Protocol requires two Runs with distinct participant
cohorts and distinct Session histories.

## Record a completed Run

First copy `session-plan.example.json`, preserve the actual Phase changes,
disclosures, Interventions, and chosen resolution, and materialize its exact
history:

```bash
narrative-game-playtest-session packages/game-release.zip session-plan.json \
  --output completed/session-history.json
```

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

Repeat the complete Session and ingestion workflow with a distinct participant
cohort. Then give both Run records, their attributable evidence, Findings, and
the blind Evaluation to an independent human who did not play, host, or observe
either Run. An approval is materialized without custom Python through:

```bash
narrative-game-playtest-review ./experiment ./standing-review.json
```

The command computes the frozen dimension-by-dimension model-human comparison,
preflights the reviewer, comparison, and accepted Standing together, and writes
nothing if the reviewer is not independent. A non-approved review remains
feedback: it must not be converted into accepted Standing. Findings require
human direction before becoming answer-safe Requirements; a changed child needs
fresh blind and human remeasurement before improved standing.

## Reproduce the preparation

```bash
uv run narrative-game-playtest-prepare \
  /path/to/new-playtest-directory \
  --parent-release /path/to/candidate-6/game-release.zip
```

The command refuses a non-empty output directory and rejects a parent Release whose canonical game is not the selected Candidate 6 game.
