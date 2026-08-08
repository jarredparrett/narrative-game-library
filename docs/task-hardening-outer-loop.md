# Failure-driven task hardening v1

This is the implementation-ready contract for turning a verified agent failure
into a harder-but-fair child task. It specifies the complete outer-loop proof;
it does not implement the runtime, train a policy, or claim a measured game.

The retained logic prototype is branch `codex/task-hardening-prototype` at
commit `1b3dee2`. Its accepted reference path and fifteen rejected paths are
primary evidence for the state ordering and fail-closed rules below.

## Decision

A promoted agent-capability or Coordination Failure may become a generation
target only after causal ownership is supported and material game, artifact,
runtime, provider, and evaluator defects have been excluded. The resulting Task
Hardening Requirement describes a capability demand and protected invariants,
not an answer or prescribed story mutation.

The current generation-and-climb path creates a child Release. Independent
preflight establishes that the child is fair enough to measure. The exact same
Evaluation Panel and Analysis Instrument then measure baseline and child under
their precommitted assignments. Challenge Admission binds the preflight and
measurement evidence. A matched comparison, sealed-governance evidence, and an
independent Review must all pass before a deterministic Hardening Transition.

No score or failure count can compensate for a failed integrity gate.

## The three routes

Every corroborated Incident receives exactly one route before generation.

| Evidence state | Route | Consequence |
|---|---|---|
| Promoted agent-capability or Coordination Failure; causal ownership supported; no material defect cause | `harden` | Freeze a Task Hardening Requirement and enter child generation. |
| Game, artifact, runtime, provider, or evaluator defect materially caused the observation | `repair` | Send the defect to its owning repair loop. Its Episodes cannot support a hardness claim. |
| Ownership, corroboration, or evidence remains materially unresolved | `quarantine` | Preserve the evidence and schedule a discriminating probe. No requirement or child may be created. |

Partial Attribution is eligible only when the accepted agent/coordination factor
is sufficient for the scoped challenge demand and every unresolved branch is
either held invariant or excluded by a control. A weak game affordance plus a
weak policy does not become hardening evidence until the game-owned factor is
repaired or experimentally controlled.

This routing does not contradict the rule that only a game-owned failure may
authorize a game *repair*. Hardening does not claim that the baseline game was
defective. It uses a promoted agent or collective capability class as the
declared behavior to challenge while retaining all game-quality gates.

## Frozen identities

One Hardening Demonstration freezes these identities before child generation:

- baseline Release and complete baseline Difficulty Profile;
- Evaluation Panel, Analysis Instrument, Published Failure Atlas, and
  Difficulty Target Contract;
- source Incident, both independent Causal Hypothesis Sets, Counterfactual Plan,
  contrasts, and accepted Owning-Layer Finding;
- promoted Failure Class and exact class version;
- Task Hardening Requirement and Generation Intent;
- standing and diagnostic sampling plans, budgets, stop policy, and invalid-run
  replacement chains;
- game profile adapter, Generative Framework version, Component Lock, and seed
  policy;
- Challenge Admission Instrument, independent principals, sealed-governance
  rule, and comparison rule.

Changing any frozen identity creates a new Demonstration lineage. A retry cannot
quietly change one.

## Task Hardening Requirement contract

A v1 Task Hardening Requirement contains:

| Field | Meaning |
|---|---|
| `source_failure_class_ref` | One promoted class in the pinned Published Failure Atlas. |
| `owning_layer_finding_ref` | The accepted causal evidence that makes the class eligible for hardening. |
| `capability_demand` | Answer-safe behavior the task requires, stated without hidden truth or a solution path. |
| `challenge_mechanism` | Observable interaction or information dependency intended to exercise that demand. |
| `allowed_mutation_surface` | Exact game surfaces generation may change. |
| `forbidden_mutations` | Contradiction, ambiguity, impossibility, hidden required action, authorization gap, answer-bearing hint, runtime degradation, or evaluator change. |
| `protected_invariants` | Coherence, authorized reachability, independent solvability, oracle validity, bounded answers, leakage resistance, artifact realism, and narrative quality. |
| `expected_manifestation` | Trace-observable behavior predicted under the fixed Panel. |
| `non_manifesting_control` | Matched case that removes the challenge mechanism while preserving facts and oracle. |
| `target_contract_ref` | Required target bands, coverage, uncertainty method, and allowed trade-offs. |
| `generation_intent_ref` | Open-method generation objective and bounded stopping rule. |
| `lineage_refs` | Exact upstream evidence and receipts. |

The Requirement may specify *what demand changes* but not *how the builder must
write the answer*. Builders receive no hidden truth from analysis, sealed cases,
or prior model failures beyond the answer-safe fields above.

## Thirteen-state demonstrator

Each state produces an immutable receipt. A failed state terminates or routes
the current lineage; it is never skipped.

| # | State | Required evidence | Successful transition |
|---:|---|---|---|
| 1 | Baseline eligibility | Complete, replay-valid baseline Episodes and Difficulty Profile under the frozen Panel and Instrument | Freeze baseline evidence. |
| 2 | Failure analysis | Corroborated Incident, Semantic Interpretation, two isolated Attributions, and causal probes | Freeze an Owning-Layer Finding or preserve unresolved evidence. |
| 3 | Failure routing | Supported owning layer and material-confounder inventory | Route to `harden`, `repair`, or `quarantine`. |
| 4 | Class promotion | Promoted Failure Class, positive fixture, non-manifesting fixture, independent review, and pinned Atlas | Bind the exact class version. |
| 5 | Requirement freeze | Complete answer-safe requirement with allowed mutations and protected invariants | Freeze Requirement and Generation Intent. |
| 6 | Child generation | Current generation plan, independent builder/reviewer, budgets, and exact requirement | Produce one immutable child Release and generation receipt. |
| 7 | Challenge preflight | Compilation, coherence, authorization, reachability, two independent solver Lineages, oracle, leakage/shortcut review, matched control, artifact realism, and narrative quality | Freeze preflight evidence or quarantine child. |
| 8 | Matched remeasurement | Same Panel, Instrument, assignments, host, tools, prompts, sampling, seeds, and replacement rules | Produce complete child Episodes and Difficulty Profile. |
| 9 | Target comparison | Matched baseline/child Profiles, uncertainty envelopes, all invalid/missing counts, target bands, and control behavior | Produce Release Comparison or indeterminate result. |
| 10 | Challenge Admission | Generation receipt, complete preflight, matched measurement, target difficulty, novelty, and independent principals | Admit to Generated Challenge Suite or quarantine. |
| 11 | Sealed non-regression | Applicable opaque sealed qualification evidence | Bind an opaque pass or reject. |
| 12 | Independent Review | Frozen proposal, complete lineage, disagreements, gates, controls, and receipts | Accept or reject without editing. |
| 13 | Hardening Transition | Accepted Review and complete lineage closure | Append the selected child and suite binding. |

The state order deliberately places Challenge Admission after measurement.
Preflight proves that a candidate is eligible to measure; Admission additionally
requires target-difficulty and novelty evidence from that measurement.

## Child generation

The child uses the existing generation-and-climb machinery rather than a second
generator:

1. Convert the Task Hardening Requirement into property-level Requirements in
   the frozen Generation Plan.
2. Invoke the independent builder and reviewer through the existing typed
   Tasks and persist their Model Receipts.
3. Apply only an independently accepted Proposal to create the child Draft.
4. Rebuild every affected game and Verismill artifact surface; unchanged
   accepted artifact bytes retain exact lineage rather than implied reuse.
5. Compile an immutable child Candidate, Release, Physical Export, and Episode
   environment under the pinned profile and Component Lock.

If the existing Generative Framework cannot express the Requirement, the Cycle
may research or propose a Generative Framework Revision under ADR 0009. That is
a separate, content-addressed proposal with separate review and sealed-cohort
obligations. A current-run code patch is never smuggled into the child identity.

## Challenge preflight and Admission

Preflight is fail-closed. It requires:

- canonical compilation and cross-resource coherence;
- authorized reachability of every required action and evidence path;
- two isolated solver principals that each reach an authorized valid solution;
- oracle validation and either one unique answer or a bounded explicit answer
  set;
- an isolated adversarial review for answer leakage, shortcuts, ambiguity, and
  impossible assumptions;
- the matched non-manifesting control;
- exact Verismill Artifact Attestations for affected artifacts; and
- independent narrative-quality and host/dossier-usability gates where the
  profile requires them.

Any unresolved hard finding quarantines the child. It cannot be measured as a
failure, counted as difficult, or enter any evaluation suite.

Challenge Admission occurs only after matched remeasurement and additionally
binds target-difficulty, novelty, generation, preflight, and analysis receipts.
Its Generated Challenge Suite binding is immutable and can never later become a
Sealed Standing Suite binding.

## Matched measurement and comparison

The primary comparison uses the same exact Evaluation Panel and Analysis
Instrument. Baseline and child receive distinct Panel Applications because they
bind different Releases, but all model, prompt, tool, host, sampling, schedule,
seed, and analysis contracts remain fixed.

The comparison must satisfy all of these rules:

1. Every precommitted assignment is present or follows its frozen invalid-run
   replacement chain.
2. Invalid, incomplete, timed-out, or authorization-broken Episodes remain in
   the denominator ledger but never count as agent failures.
3. The declared capability manifestation moves in the required direction under
   a paired 95% interval that excludes no-change.
4. Required Difficulty Profile intervals lie inside the frozen target bands;
   a harder point estimate outside the solvability band is rejection.
5. Episode validity, integrity, coherence, authorization, leakage resistance,
   artifact realism, narrative quality, and required slices do not regress.
6. The matched non-manifesting control does not show the same increase; otherwise
   the mechanism is not isolated.
7. No weighted aggregate compensates for a failed gate or an indeterminate
   dimension.

The outcome is `supported-target-band`, `provisionally-target-band`,
`too-easy`, `too-hard`, `brittle`, or `indeterminate` under the pinned Target
Contract. Only `supported-target-band` plus every hard gate can support the
Hardening Demonstration.

## Sealed governance

The challenge designer, generator, and measured Actors never see sealed cases or
case-level results. The demonstrator receives only the opaque decision receipt
required by the governing framework contract.

- If the Generative Framework identity is unchanged, bind its current valid
  sealed qualification and prove the exact framework hash remained unchanged;
  do not consume a cohort merely for generating a new case.
- If a Framework Revision participated, consume one fresh single-use Sealed
  Cohort and require its opaque pass before framework or hardening transition.

A failed receipt rejects the transition. Its aggregate result cannot become a
repair gradient, and retrying requires a new Revision and fresh cohort.

## Authority and principal separation

The following principals are distinct within one hardening lineage:

- Episode Actors and host;
- discovery, interpretation, and both attribution principals;
- Counterfactual planner and result interpreters;
- Atlas Curator and Atlas Reviewer;
- Challenge Designer and generation builder;
- generation reviewer;
- two Admission solvers and leakage reviewer;
- measured child Actors;
- Sealed Suite Curator; and
- final Independent Reviewer.

Authority equality is not enough: actual principal and isolated context
identities are checked. A contributor cannot review its own proposal, and a
solver cannot certify the child it helped generate.

## Required lineage closure

The Hardening Demonstration must contain this connected evidence path:

```text
baseline Release
  -> baseline Panel Application -> baseline Episodes -> baseline Profile
                                      |
                                      v
Signals -> Incident -> Interpretation -> Attribution A + Attribution B
                                      -> Counterfactual Plan and Contrasts
                                      -> Owning-Layer Finding
                                      -> promoted Failure Class
                                      -> Task Hardening Requirement
                                      -> Generation Intent -> child Release
                                                               |
                         preflight and two solver Lineages <-----+
                                                               |
                         child Panel Application -> child Episodes
                                                   -> child Profile
baseline Profile + child Profile -> matched Release Comparison
preflight + comparison -> Challenge Admission -> Generated Suite Binding
Challenge Admission -> opaque sealed evidence -> Independent Review
Independent Review -> Hardening Transition
```

Every node is content-addressed. Every edge names the transition receipt that
created it. Missing, cyclic, stale, or cross-Workspace references make the
Demonstration ineligible even when the visible metrics look correct.

## Worked falsifying example

The prototype uses a promoted `coordination.uncompleted-handoff` class. The
Task Hardening Requirement distributes two complementary proof fragments to
different Seats and requires an explicit authorized corroborated handoff. Its
matched control gives both fragments to one authorized Seat while preserving
facts and oracle.

Illustrative frozen evidence:

| Measure | Baseline | Child | Required |
|---|---:|---:|---:|
| Resolution reliability, 95% interval | `[0.79, 0.91]` | `[0.60, 0.72]` | child inside `[0.55, 0.75]` |
| Proof-critical handoff failure, 95% interval | `[0.05, 0.14]` | `[0.25, 0.38]` | child inside `[0.20, 0.45]` |
| Paired targeted delta, 95% interval | — | `[0.12, 0.28]` | strictly above zero |
| Episode validity | `1.00` | `1.00` | at least `0.99` |
| Integrity | `1.00` | `1.00` | at least `0.99` |
| Independent solver demonstrations | — | `2/2` | `2/2` |
| Sealed governance | qualified framework | opaque pass | no regression |

These numbers demonstrate the decision logic only. They are not empirical
standing. A real implementation must derive them from complete persisted
Episodes under the frozen sampling and uncertainty contracts.

## Required falsifying fixtures

Implementation must reproduce the prototype's reference case and reject each
of these cases at the named boundary:

1. game contradiction routes to repair;
2. runtime timeout routes to repair;
3. evaluator false positive routes to repair;
4. unresolved ownership quarantines;
5. unpromoted Failure Class rejects;
6. ambiguity mutation rejects;
7. unsolvable child rejects in preflight;
8. answer leakage rejects in preflight;
9. Panel or Instrument drift invalidates comparison;
10. invalid Episodes cannot inflate hardness;
11. child outside the solvability band rejects;
12. targeted paired interval containing zero rejects;
13. sealed regression rejects;
14. contributor/reviewer principal collision rejects; and
15. incomplete lineage closure rejects.

Additional implementation fixtures must cover incomplete standing assignments,
matched-control manifestation, Instrument drift, stale Atlas or Target Contract,
failed artifact realism, and a Framework Revision that attempts to reuse a
consumed sealed cohort.

## Version and retry boundaries

Retries repeat only exact transport or schema operations permitted by the
underlying Generation Plan and Analysis Instrument. Changing evidence, model,
prompt, tool, principal, Release, Panel, Instrument, Atlas, Target Contract,
Requirement, framework, or suite binding creates a new object and lineage.

Rejected and quarantined children, invalid Episodes, failed reviews, consumed
sealed receipts, and exhausted campaigns remain durable evidence. A later Cycle
may cite them, but it cannot rewrite or silently resume their identities.

## Implementation acceptance

The implementation handoff is complete only when executable capability tests
prove:

- all thirteen transitions and all terminal routes;
- exact Task Hardening Requirement validation and answer-safe builder input;
- complete principal-conflict and Evidence View enforcement;
- admission ordering and all preflight gates;
- exact Panel/Instrument match and invalid-run accounting;
- uncertainty-aware target movement and matched-control discrimination;
- sealed-framework identity or fresh-cohort governance as applicable;
- full content-addressed lineage and offline replay after relocation; and
- a worked real-agent example whose measured evidence, not fixture constants,
  supports one accepted harder-but-fair child.
