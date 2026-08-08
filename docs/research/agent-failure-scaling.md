# Scaling game evaluation through agent-failure evidence

Date: 2026-08-07

## Decision

The library should accumulate a versioned, trace-grounded **Failure Atlas** and
use it to generate targeted challenge suites. This is recursive improvement of
the evaluation system, not policy training and not autonomous self-modification.

The loop has two different clocks:

```text
inner loop: GameRelease N -> fixed playtest panel -> verified failures -> GameRelease N+1

outer loop: verified failures -> Failure Atlas -> detectors and challenge suites
                                      ^                    |
                                      +---- holdout proof --+
```

Only the game changes inside an N versus N+1 comparison. The outer loop may
propose new failure classes, detectors, and challenge cases, but it cannot alter
historical profiles or current standing. A new atlas version applies only to a
new experiment series.

## Research basis

- [AgentRx](https://arxiv.org/abs/2602.02475) derives a cross-domain taxonomy
  from annotated failed trajectories and pairs failure localization with an
  auditable constraint-validation log. This supports trace-addressable failure
  observations and explicit constraints rather than free-form diagnosis.
- [Who & When](https://arxiv.org/abs/2505.00212) reports that its strongest
  method identified the responsible agent in 53.5% of cases but the decisive
  failure step in only 14.2%. It also reports annotation uncertainty and
  multi-agent mistakes. Automated attribution must therefore remain a proposal
  with confidence and alternatives, not an authoritative single cause.
- [MP-Bench](https://arxiv.org/abs/2603.25001) argues that multi-agent failures
  can admit several plausible attributions. The atlas should allow multi-label,
  multi-layer causality and an unresolved state rather than forcing one owner.
- [AgentBoard](https://arxiv.org/abs/2401.13178) evaluates intermediate
  progress, grounding, long-range interaction, and trajectories in addition to
  final success. This supports milestone and process diagnostics outside the
  binary outcome gate.
- [ToolSandbox](https://machinelearning.apple.com/research/toolsandbox-stateful-conversational-llm-benchmark)
  uses stateful execution and dynamic evaluation of intermediate and final
  milestones. This supports evaluating recorded state transitions rather than
  accepting a narrated procedure.
- [tau-bench](https://arxiv.org/abs/2406.12045) compares terminal database state
  with an annotated goal state and uses `pass^k` to expose reliability across
  repeated trials. A single successful episode is not difficulty standing.
- [Anthropic Bloom](https://www.anthropic.com/research/bloom) turns a specified
  behavior into generated evaluation scenarios, but its workflow still starts
  with a researcher-specified behavior and local iteration before large sweeps.
  Generated challenge cases should likewise be validated before joining a
  standing suite.
- [Inspect evaluation logs](https://inspect.aisi.org.uk/eval-logs.html) preserve
  sample status, errors, transcripts, scores, and metadata and distinguish
  successful from incomplete logs. The narrative library should preserve the
  same separation between execution status, verified outcome, and later
  offline analysis.

## Evidence the system learns from

In descending order of authority for this use case:

1. Canonical replay and deterministic state-transition checks.
2. Trace-addressable actions, observations, tool results, public messages, and
   terminal state from verified `EpisodeArchive` objects.
3. Counterfactual runs under the same frozen panel.
4. Independent agent attribution and blind evaluation receipts.
5. Human playtest and expert artifact feedback when supplied.
6. External primary research, benchmark specifications, and public failure
   corpora used to propose categories and experimental methods.

Private chain-of-thought and a model's self-explanation are not authoritative
evidence. A bounded reasoning summary may help propose a diagnosis, but the
accepted observation must cite visible events or replayed state.

## What the system looks like in operation

The operational unit is not an LLM critique. It is an `EpisodeAnalysis` derived
from one verified archive under one frozen experiment contract.

```text
GameRelease + EvaluationPanel
              |
              v
       EpisodeArchive
              |
       replay verification -------------------- invalid/incomplete archive
              |                                          |
              v                                          v
    deterministic signal detectors              infrastructure Incident
              |
              v
 knowledge-flow, contribution, progress, and intervention graphs
              |
              v
  one or more Failure Incidents with exact trace spans
              |
              v
 independent attribution proposals + counterfactual probes
              |
              v
       Difficulty Profile and Atlas evidence
```

An analyzer should produce four separable views:

1. **Integrity view:** did the archive replay, respect authorization, preserve
   identity isolation, and contain a complete provider result for every step?
2. **Outcome view:** were the declared terminal requirements satisfied by
   authoritative state transitions?
3. **Process view:** how did evidence, hypotheses, requests, interventions, and
   objectives progress through the episode?
4. **Attribution view:** which game, policy, interaction, host, runtime, or
   evaluator factors plausibly contributed, and what probe would distinguish
   them?

The first two views can gate an episode. Process and attribution are diagnostic
and retain uncertainty.

### Required derived graphs

The existing `EpisodeArchive` already records observations, calls, results,
messages, visibility, epistemic state, interventions, and terminal state. From
those records the analyzer can derive:

- a **knowledge-flow graph** whose edges show a Seat inspecting, privately
  sending, or publicly sharing a Resource;
- a **claim-support graph** connecting public findings and terminal claims to
  the records the speaker was licensed to cite;
- a **work graph** showing attempted, rejected, duplicated, and state-changing
  actions by Seat and phase;
- a **progress graph** showing when proof requirements, character objectives,
  and mandatory scenario states became possible or satisfied;
- an **intervention graph** connecting host actions to subsequent discoveries,
  claims, and termination;
- a **communication graph** showing public/private volume, direction,
  unanswered requests, challenges, and corroboration.

Natural-language acts such as requests, challenges, assignments, and agreement
cannot always be derived mechanically. They should be added as versioned,
confidence-bearing semantic annotations produced after the episode, or later as
typed optional communication metadata. They must never overwrite the original
message or become canonical truth.

### Evaluation cascade

One candidate should normally move through these stages:

1. Run static game and artifact validators.
2. Run deterministic replay and invariant checks.
3. Execute a small smoke panel and derive exact signals.
4. Run the fixed matrix only if the smoke panel is valid.
5. Aggregate recurrent Incidents by seed, Seat, policy, host condition, and
   proof path.
6. Request agentic attribution only for novel, ambiguous, or decision-relevant
   Incidents.
7. Schedule counterfactual Episodes that distinguish the leading causes.
8. Update the Difficulty Profile.
9. Propose Atlas additions only after recurrence or a deterministic proof.
10. Convert accepted game-owned failures into Requirements for the next Release.

The output presented to an operator should resemble an incident card, not a
single score:

```text
Incident: coordination.uncompleted-handoff (experimental)
Episode:  episode:...4104       Release: release:...v7
Outcome:  passed                 Integrity: passed
Signals:  evidence E7 inspected by Seat B at event 18
          Seat C requested corroboration at event 23
          E7 was never public before resolution at event 51
          host supplied the missing synthesis at event 44
Attribution candidates:
          coordination / missed handoff         0.58
          dossier / unclear responsibility      0.27
          host / premature recovery             0.15
Next probe:
          repeat with minimal host; rotate Seat B's policy to Seat D
Standing effect:
          none; one ambiguous passing episode
```

## Failure Atlas model

The atlas is a versioned directed acyclic graph rather than a forced tree.

### `FailureObservation`

- exact episode, release, panel, and trace identities;
- one or more event ranges and quoted visible spans;
- expected constraint or milestone and observed result;
- proposed failure classes and owning layers;
- reporter identity, method, confidence, and alternatives;
- status: `observed`, `corroborated`, `refuted`, or `unresolved`.

### `FailureClass`

- stable class ID, version, parents, definition, and explicit exclusions;
- applicable layer: game/world, evidence graph, dossier, artifact, reveal
  schedule, host orchestration, agent policy, runtime, provider, or evaluator;
- observable signatures and counterexamples;
- deterministic detector or frozen agentic instrument;
- severity, repair scope, and known confounders;
- supporting and refuting observation IDs;
- lifecycle: `proposed`, `experimental`, `promoted`, `deprecated`, `split`, or
  `merged`.

### `ChallengeCase`

- source failure class and exact generating mutation;
- canonical initial state, legal actions, terminal requirements, and oracle;
- expected manifestation and non-manifesting control;
- development or sealed-holdout designation;
- feasibility, solvability, authorization, and answer-leak checks.

### `AtlasRevision`

- parent atlas version;
- added, split, merged, or retired classes;
- exact evidence and review receipts;
- detector and challenge-suite version locks;
- migration notes without rewriting historical observations.

## Initial top-level taxonomy

Keep ownership and manifestation separate. One episode may carry several.

1. **Environment/game defects** — contradiction, inaccessible evidence,
   underdetermination, premature proof, missing state transition, role starvation.
2. **Agent cognition failures** — failed observation, retrieval, inference,
   planning, tool selection, execution, or self-correction.
3. **Coordination failures** — information hoarding, false consensus, duplicated
   work, unsupported trust, dominance, lost handoff, or absent corroboration.
4. **Host/scaffold failures** — answer-bearing hint, excessive recovery,
   premature termination, identity drift, context loss, or invalid scheduling.
5. **Runtime/provider failures** — rejected tool call, timeout, malformed output,
   rate limit, partial trajectory, or unsupported parameter.
6. **Evaluation failures** — answer leakage, reward hacking, false positive,
   false negative, ambiguous attribution, unstable judge, or contaminated panel.
7. **Artifact failures** — unrealistic form, internal inconsistency, unreadable
   rendering, or evidence text that accidentally supplies the deduction.

Only failures attributed to a game-owned layer may directly generate a game
revision requirement. Policy and infrastructure failures characterize the
instrument or invalidate the episode; they are not evidence that the game
should change.

## Finding multi-agent failures

A multi-agent failure is not merely an episode in which several agents were
present. It is an Incident whose causal mechanism depends on interaction,
information distribution, role allocation, or collective dynamics. No single
locally invalid action need exist.

### Exact detectors available from the trace

These can be computed without an LLM judge:

- **knowledge silo:** proof-critical evidence is inspected but never reaches an
  authorized public path before termination;
- **unsupported relay:** an Actor advances a finding or terminal citation that
  has no permitted inspection or public-sharing lineage;
- **duplicate investigation:** multiple Seats repeat an equivalent inspection
  while required reachable Resources remain uninspected;
- **action thrashing:** equivalent accepted or rejected calls recur without a
  relevant state change;
- **role starvation:** a Seat has no accepted action, objective progress, useful
  disclosure, or contribution opportunity over a declared phase;
- **host substitution:** a host disclosure or synthesis supplies a proof
  requirement no Seat had independently made public;
- **confession dependence:** the correct resolution occurs only after a culprit
  message supplies a required proposition;
- **mandatory-action omission:** the team describes an operation but the
  required command and resulting state transition never occur;
- **premature termination:** the host ends the episode while reachable mandatory
  actions or proof requirements remain unresolved;
- **identity or visibility breach:** contexts, observations, or private messages
  cross their authorized role boundaries;
- **panel drift:** model, prompt, tool, host, sampling, or condition locks differ
  between compared candidates.

Some terms such as `proof-critical` and `required` must come from the Release or
frozen rubric, not be inferred after seeing the outcome.

### Semantic detectors requiring bounded judgment

These require message interpretation and must preserve confidence and the exact
supporting spans:

- an explicit request for corroboration was ignored or falsely acknowledged;
- the team converged on a theory before independent support was public;
- an unsupported claim cascaded through deference or repetition;
- agents disagreed but never surfaced or resolved the contradiction;
- work was implicitly delegated and then abandoned;
- one Actor dominated decisions while other available evidence was suppressed;
- locally reasonable plans formed a cyclic wait or collective deadlock;
- an agent continued using a belief after receiving decisive contrary evidence;
- private information was laundered into a public claim without its source;
- roleplay pressure caused an Actor to violate the declared cooperation or
  contestability condition.

Use at least two independent attribution passes or one pass plus a deterministic
detector for standing-relevant claims. Disagreement becomes part of the Incident
rather than being averaged away.

### Counterfactual probes for causal attribution

Repeated observation establishes recurrence, not cause. Use controlled probes:

- **policy rotation:** if the failure follows the policy across Seats, suspect
  agent/scaffold capability; if it stays with the Seat, suspect dossier, access,
  objectives, or role design;
- **host-policy substitution:** if a minimal host fails and an active host
  passes, measure host dependence rather than calling the game solved;
- **culprit-condition substitution:** cooperative, evidence-triggered, evasive,
  and silent culprit conditions expose confession dependence;
- **evidence-path substitution:** rotate which valid proof route is available
  to expose single-route brittleness;
- **communication restriction:** compare declared public-only and private-enabled
  conditions to locate hidden coordination dependencies;
- **single-factor game mutation:** clarify one responsibility, reveal, or action
  affordance while retaining the identical panel;
- **model-family replication:** a pattern recurring across fixed capability
  lineups is stronger evidence of a game-owned defect than one confined to a
  policy family.

Never call a changed condition a replay. It is a new content-addressed Episode
whose identity records the changed factor.

### Distinguishing likely ownership

```text
failure follows a policy across role rotations  -> policy or scaffold
failure follows one Seat across policy rotations -> dossier, access, or role
failure follows one proof path across lineups    -> evidence/game structure
failure follows the host condition               -> host orchestration
failure follows one provider/runtime             -> infrastructure
failure appears only under one judge              -> evaluation instrument
failure recurs across all controlled factors      -> game or shared environment
```

These are diagnostic tendencies, not automatic verdicts. Several layers may be
causal, especially when a weak affordance and a weak policy interact.

## Worked coordination example

Consider an illustrative investigation in which Seat B inspects a maintenance
record that contradicts the public alibi. Seat C later asks for corroboration,
but B pursues another lead without sharing the record. Other Seats converge on
the wrong theory. An active host then discloses a synthesis that exposes the
contradiction, and the team submits a correct, evidence-licensed resolution.

The terminal result is `outcome=1` and `integrity=1`, but the trace supports:

- a knowledge-silo Signal;
- an unanswered-corroboration semantic Signal;
- host-substitution and host-recovery-dependence Signals;
- no conclusion yet about whether B, B's dossier, the host timing, or the game
  affordance caused the breakdown.

The next experiment runs the same Release and policy rotation with a minimal
host. If failure recurs only when the same policy occupies any Seat, it is likely
an instrument limitation. If it recurs whenever any policy occupies Seat B, it
is likely a role-design defect. If all Seats and lineups miss the handoff, the
game may need a clearer responsibility, action affordance, or redundant route.

This example shows why the system must preserve outcome, process, and attribution
as different objects. Passing is not evidence that coordination was healthy,
and a suspicious trace is not yet evidence for a game revision.

## Promotion gates

A proposed class joins a standing atlas version only when:

1. every observation points to a replay-verifiable trace or deterministic proof;
2. the class has a definition, exclusions, adjacent classes, and counterexample;
3. it is corroborated across distinct episodes or has a deterministic minimal
   reproduction;
4. ambiguous cases preserve alternative attributions and confidence;
5. a detector or frozen rubric can be rerun independently;
6. at least one positive fixture and one non-manifesting control pass;
7. any generated challenge is verified as coherent, solvable, authorized, and
   free of answer leakage;
8. an independent reviewer accepts the revision receipt;
9. a sealed standing suite does not regress;
10. the revision creates a new taxonomy and instrument version rather than
    changing historical measurements.

## Scaling strategy

Use an evaluation cascade so expensive multi-agent runs are concentrated where
they add information:

```text
static validators
    -> deterministic replay and mutation tests
        -> small role or proof-path simulations
            -> full fixed-panel episodes
                -> independent review or human play when valuable
```

Select new runs by novelty, disagreement, uncertainty, boundary proximity, and
regression risk. Preserve three suites:

- **development suite:** known failures and fast regression cases;
- **challenge suite:** automatically proposed, validated variations;
- **sealed standing suite:** withheld cases that determine whether the outer
  evaluation instrument actually improved.

Scale across independent axes rather than one headline number: releases,
episode seeds, policy lineups, host conditions, culprit conditions, failure
classes, proof paths, and game profiles. Report rates and uncertainty for each
slice. Do not let a larger volume of correlated rollouts masquerade as broader
coverage.

## Implications for issue #35

Issue #35 should add the following acceptance criteria:

- a versioned `FailureAtlas` stores trace-grounded observations and multi-label
  attributions separately from `DifficultyProfile`;
- deterministic analyzers run before agentic attribution;
- automated diagnoses are proposals until promotion gates pass;
- promoted failure classes compile into a detector, fixtures, and optionally a
  validated `ChallengeCase` generator;
- development, generated-challenge, and sealed-standing suites are distinct;
- taxonomy and panel changes start a new experiment series and never rewrite
  N versus N+1 comparisons;
- the first promoted class is the existing rescue defect: procedure narration
  without the required action and resulting state transition;
- scaling reports cost, coverage, uncertainty, and failure-class novelty in
  addition to game difficulty.

This creates compounding evaluation knowledge while keeping the climb
scientifically legible: the system can learn what to test next without learning
how to make its own current test pass.
