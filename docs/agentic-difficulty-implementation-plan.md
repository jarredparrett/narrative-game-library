# Agentic difficulty implementation handoff

Status: implementation-ready specification; no capability in this document is
implemented or accepted merely because this plan exists.

## Outcome

Implement one evidence-backed loop that can replay a fixed multi-agent Episode,
run the frozen Analysis Instrument, preserve competing failure explanations,
measure a Release under a fixed Evaluation Panel, propose a harder-but-fair
child, remeasure it, and expose the complete lineage to an operator. Agents may
discover, interpret, attribute, schedule, generate, and review. Deterministic
transitions alone authorize state changes and reportable claims.

The shortest path to useful evidence is deliberately earlier than the first
qualified hardening claim. After Slice D2, real agents must be able to analyze
two preserved Episodes and produce portable receipts. That result may falsify
the prompts, views, schemas, or evidence model, but it cannot establish
Standing, promote an Atlas class, or accept a child. The first full-loop claim
arrives only after Slices D3-D5 and the external qualification inputs below.

## Evidence ledger

This handoff synthesizes the resolved decisions rather than reinterpreting their
literature. Implementation requirements retain these direct sources:

| Source | Accepted decision carried into implementation |
|---|---|
| [#38](https://github.com/jarredparrett/narrative-game-library/issues/38) | Freeze Evaluation Panel identity separately from each Panel Application and Release Comparison. |
| [#39](https://github.com/jarredparrett/narrative-game-library/issues/39) | Bound Analysis Authorities, Evidence Views, exposure, principal conflicts, and independent causal passes. |
| [#40](https://github.com/jarredparrett/narrative-game-library/issues/40) | Preserve Canonical Episode Evidence, claim-scoped verification, factual graphs, and append-only semantic overlays. |
| [#41](https://github.com/jarredparrett/narrative-game-library/issues/41) | Present one layered Incident Brief, Trace Lens, and Causal Bench without adding transition authority. |
| [#42](https://github.com/jarredparrett/narrative-game-library/issues/42) | Run five truth-blind Discovery Sweeps, record coarse-to-fine coverage, and require independent corroboration. |
| [#44](https://github.com/jarredparrett/narrative-game-library/issues/44) | Preserve multi-label Attribution and require isolated planning plus orthogonal or deterministic causal corroboration. |
| [#45](https://github.com/jarredparrett/narrative-game-library/issues/45) | Separate the append-only Atlas Workbench from immutable, independently reviewed Published Atlas versions. |
| [#47](https://github.com/jarredparrett/narrative-game-library/issues/47) | Keep seven Difficulty Profile dimensions as distributions with uncertainty and profile-specific target contracts. |
| [#43](https://github.com/jarredparrett/narrative-game-library/issues/43) | Permit recursive framework revision only through independent review and single-use sealed-cohort governance. |
| [#55](https://github.com/jarredparrett/narrative-game-library/issues/55) | Separate precommitted Standing samples from adaptive diagnostics and govern scheduling, budgets, and costs deterministically. |
| [#46](https://github.com/jarredparrett/narrative-game-library/issues/46) | Persist typed content-addressed evidence, separate Journals, Checkpoints, Claim Manifests, migrations, and portable verifier closures. |
| [#49](https://github.com/jarredparrett/narrative-game-library/issues/49) | Freeze Analysis Instrument v1's exact models, twelve assignments, prompts, views, tools, schemas, retries, and conflicts. |
| [#50](https://github.com/jarredparrett/narrative-game-library/issues/50) | Route evidence through repair, quarantine, or all thirteen hardening states and require matched remeasurement. |
| [#59](https://github.com/jarredparrett/narrative-game-library/issues/59) | Derive one read-only Operator Evidence Monitor with explicit freshness, completeness, corruption, lineage, and authority state. |

The normative implementation contracts remain [Analysis Instrument v1](analysis-instrument-v1.md),
[task hardening v1](task-hardening-outer-loop.md), the
[Operator Evidence Monitor](operator-evidence-monitor.md), the
[persistence ADR](adr/0011-content-addressed-evidence-lineage.md), and the
[research synthesis](research/agent-failure-scaling.md). If this handoff and a
normative contract disagree, the normative contract wins and implementation
stops for a new decision.

## Package and authority boundary

Add one `narrative_game.difficulty` package rather than scattering the new
language across `climb`, `simulation`, and `experiment`:

```text
simulation              execute and replay Episodes; own no interpretation
difficulty.contracts    pure typed evidence, panel, instrument, profile,
                        atlas, scheduling, and hardening contracts
difficulty.derivations  pure factual graphs, verification, uncertainty,
                        comparison, projection, and eligibility functions
difficulty.transitions  pure fail-closed state machines and conflict checks
experiment.difficulty   effectful model calls and work-package coordination
workspace               immutable objects, Journals, Checkpoints, capsules,
                        migrations, and projection storage
generation              existing child-generation path; no second generator
adapters.verismill      existing public Artifact Forge and attestations
experience              read-only operator projection renderer
```

Pure contracts, derivations, and transitions may not import filesystem,
network, clock, model-driver, or ambient-random effects. `experiment.difficulty`
receives those effects explicitly and exposes the public orchestration API.
Existing `climb` remains the game/artifact quality climb; `difficulty` consumes
immutable Releases and Episodes and must not merge its diagnostic evidence into
realism or human-play Standing.

## Ordered implementation slices

Each slice is one reviewable series of small PRs. A later slice may depend only
on accepted capability rows from earlier slices. Fixture constants may prove a
transition, but only provider receipts from the named live demonstration may
support its empirical claim.

### D0 — lock contracts and falsifying fixtures

Inventory every normative schema and version, then preserve two minimal,
replay-valid Episodes: the missing-rescue false pass and the passing
failed-handoff case. Each fixture contains canonical actions, observations,
messages, visibility, state transitions, terminal claims, verification status,
and the frozen Release reference. Neither contains an answer key in an Actor or
Discovery view.

Exit: the catalog fails on an unknown or silently changed normative version;
both fixtures replay with exact span addresses and have deterministic expected
view manifests. No model call and no quality claim occurs.

### D1 — evidence spine and portable claims

Extend the existing Workspace rather than replacing it. Add typed Evidence
Objects; `analysis` and `access` Journals; multi-Journal Checkpoints; Claim
Manifests; deterministic Workspace Archives and Claim Capsules; import receipts;
projection freshness; and offline verifier bundles. Retain rejected, invalid,
incomplete, and unsupported objects.

Exit: a Claim Capsule relocates to an empty path, verifies offline, rebuilds its
projection byte-identically in two processes, and detects object, Journal,
Checkpoint, manifest, and schema tampering.

### D2 — frozen Instrument and one-Episode analysis

Implement Instrument Definition/Application identity, exact Prompt Contracts,
bounded Evidence Views and tools, twelve isolated assignments, Analysis
Attempts and Receipts, retry limits, coverage cursors, and the principal-conflict
graph. Add deterministic factual graph derivations before any agent view is
built. Run the nine eligibility fixtures from Instrument v1.

Then run the exact `gpt-5.6-sol`/`gpt-5.6-terra` roster on both D0 Episodes.
The run is useful only if all attempted assignments and malformed outputs are
preserved, every factual statement cites an allowed span, independent outputs
remain unexposed until frozen, and disagreements survive assembly. At least one
Episode must yield an independently corroborated Incident to prove the semantic
path is live; the contract does not preordain its label or causal conclusion.

Exit: publish a portable diagnostic Claim Capsule and cost report. This is the
first falsifying checkpoint: failure means revise a versioned prompt, view,
schema, or evidence contract and start a new Instrument lineage. It is not a
Standing, Atlas-promotion, or child-acceptance result.

### D3 — matched measurement and governed scheduling

Implement Evaluation Panel and Panel Application compatibility; Standing
Sampling Plans and replacement chains; the seven-dimensional Difficulty
Profile; Uncertainty Envelopes; Difficulty Target Contracts and non-scalar
Target Dominance; Diagnostic Sampling Queues; the Evidence Cascade; complete
Evidence Work Packages; Budget Envelopes; Cost Models; sealed handles; and
Scheduling Receipts.

Exit: fixture panels prove exact-match and drift behavior, preserve every
invalid and missing denominator, separate adaptive diagnostics from Standing,
refuse unsupported precision, protect sealed/Standing budgets, and produce the
same scheduling decision from the same evidence snapshot.

### D4 — discovery, causal evidence, and Atlas lifecycle

Implement the five Discovery Sweeps, coverage and partial-state handling,
Incident Assembly and Corroboration, Semantic Interpretation, two isolated
Attributions, Counterfactual Plans and Contrasts, owning-layer findings, the
Atlas Workbench, promotion review, Published Atlas versions, Challenge
proposals, Admission, and immutable suite bindings.

Exit: the failed-handoff fixture can preserve competing hypotheses, schedule a
discriminating probe, route a supported observation without flattening it to a
single blame label, and either promote with every gate or remain visibly
unresolved. A development or generated case can never become sealed.

### D5 — failure-driven hardening

Connect the accepted Task Hardening Requirement to the existing generation
coordinator. Do not create a second generator. Implement `repair`, `quarantine`,
and all thirteen `harden` transitions; answer-safe builder input; child
preflight; two isolated solver lineages; exact Verismill Artifact Attestations;
matched non-manifesting controls; matched Panel/Instrument remeasurement;
Challenge Admission; opaque sealed evidence; independent review; and lineage
closure.

Exit: the reference path passes and every rejection case named in task
hardening v1 fails at its named boundary. Framework source changes are separate
Framework Revision objects and never current-run patches hidden in a child.

### D6 — operator surface and release qualification

Build the Evidence Spine overview, Coverage Plot, and Incident Workbench as
rebuildable read-only projections. Implement current, incomplete, stale, and
corrupt behavior; trace every visible conclusion to a Claim Manifest or
Scheduling Receipt; expose only allowlisted sealed fields; and provide no
mutation command. Package the verifier, schemas, exact component lock, and
worked evidence as a release Claim Capsule.

Exit: all fifteen monitor fixtures pass, deletion and regeneration changes no
claim, responsive/accessibility checks pass, and an unfamiliar operator can
verify the complete result offline after relocation.

## First falsifying full-loop demonstration

After D5, run one Facilitated Investigation demonstration around the promoted
`coordination.uncompleted-handoff` class:

```text
baseline Release -> fixed Panel -> verified Episodes -> fixed Instrument
  -> corroborated Incident -> isolated Attributions -> causal contrast
  -> promoted class -> answer-safe hardening requirement -> generated child
  -> coherence + solver + leakage + Verismill preflight
  -> same Panel and Instrument -> matched Profile comparison + control
  -> Challenge Admission -> sealed receipt -> independent Review
  -> deterministic Hardening Transition -> portable Claim Capsule
```

The challenge mechanism distributes complementary proof fragments across two
Seats and requires an authorized, corroborated handoff. The matched control
places both fragments with one authorized Seat while preserving the facts and
oracle. The demonstration passes only when measured evidence supports every
hard gate, target movement under paired uncertainty, control discrimination,
and complete lineage. Any missing assignment, model drift, failed artifact,
unresolved cause, target miss, leakage, invalid Episode, or stale evidence makes
the result `indeterminate`, `quarantined`, or `rejected`; none is converted into
difficulty.

## External qualification inputs and honest blockers

These inputs are not resolved by implementation code and must exist before the
full-loop demonstration can claim acceptance:

1. A frozen Facilitated Investigation Calibration Suite with independently
   authored easy, target-shaped, hard, and brittle Releases. Until it produces
   an accepted Difficulty Target Contract, real comparisons remain diagnostic
   or `indeterminate`; illustrative bands in the prototype are not thresholds.
2. An accessible provider resolution for both exact Instrument v1 model slots.
   A different resolved model creates a different Instrument Application and
   cannot be called an exact matched run.
3. A qualified Generative Framework identity and its current opaque sealed
   receipt, or a fresh single-use Sealed Cohort for any Framework Revision.
4. A pinned Verismill Artifact Forge component lock capable of returning exact
   attestations for every affected artifact. A text substitute is a failed
   preflight, never an acceptable fallback.

Cross-profile generalization remains deferred. The first implementation targets
only Facilitated Investigation; another profile requires its own adapter,
Calibration Suite, target contract, and eligibility evidence.

## Migration boundaries

| Boundary | Required behavior |
|---|---|
| Existing Workspace `0.1` | Read unchanged. A deterministic migration creates new objects and a Migration Receipt; it never edits existing objects or Journals. |
| Existing `climb.jsonl` | Retain its identity and history. Add `analysis.jsonl` and `access.jsonl`; do not relabel old climb events as new analysis evidence. |
| New evidence schemas | Begin independently versioned at `1.0`; compatible fields advance minor versions, interpretation changes advance major versions. |
| Analysis Instrument | Pin `analysis-instrument.1` / `1.0.0`. Prompt, view, model, tool, schema, retry, conflict, Atlas, or fixture change starts a new identity. |
| Profiles and targets | Never reclassify a historical Profile under a changed Target Contract. Emit a new comparison lineage. |
| Atlas and suites | Workbench entries are append-only; publication creates a new Atlas version; suite bindings are immutable and one-way. |
| Projections | Version separately, name their source Checkpoint, and remain disposable. Projection migration cannot alter canonical evidence. |
| Package release | Bump the library version only when the corresponding planned acceptance rows pass; documentation alone makes no runtime-version claim. |

## Pull-request and acceptance order

Use one requirement-bearing PR at a time inside each slice. Every PR adds the
named capability test and its fixture with the implementation. A PR may mark a
row `implemented` only after local and public Python 3.11/3.13 tests pass; live
evidence rows remain `process evidence` or `diagnostic` until their exact
provider receipts and Claim Capsule are reviewed. The merge order is strictly
D0 -> D1 -> D2 -> D3 -> D4 -> D5 -> D6.

Implementation is complete only when every planned row in the
[acceptance matrix](acceptance-matrix.md) is accepted, the full-loop Claim
Capsule verifies offline, and none of the blockers above is represented as a
warning or favorable default.
