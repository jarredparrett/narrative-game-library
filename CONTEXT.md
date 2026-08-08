# Domain context

The library models games as access-controlled interactions over one canonical
world, not as branching prose or a folder of documents.

## Ownership

- The **Kernel** owns Resource, Seat, identity, typed references, access,
  extension activation, deterministic lifecycle, replay, and projection.
- The **Narrative extension** owns represented Events, Propositions, the Truth
  Model, Characters, Beliefs, Objectives, Evidence Relations, Hypotheses, Proof
  Paths, Reveals, Phases, Interventions, and Resolution policy.
- The **agentic authoring and experiment layer** owns Proposals, receipts,
  independent Review, Candidates, measurement, and standing. Typed agent roles
  may complete the loop; human feedback remains distinct optional evidence.
- Adapters translate external systems. They do not own or invent domain truth.

## Canonical rules

A Proposition is a stable semantic atom. The Truth Model is its one truth
owner for an immutable Candidate or Release. Character Beliefs may accept,
reject, or remain uncertain about that Proposition. Claims and their veracity
are derived. A Material is a Kernel Resource; Evidence is the Narrative meaning
that relates that Resource to a Proposition or Hypothesis.

A Reveal is authored availability policy. A later Disclosure Event records
that access actually changed in one Session. A Character is represented-world
identity; a Seat is an access/action boundary; an Actor occupies a Seat; a
Viewer may observe without occupying one.

Version one ships one profile: **Facilitated Investigation**. It has fixed truth
per Release, asymmetric knowledge, competing hypotheses, evidence, phased
disclosure, a host, proof-based resolution, explicit hints/recovery, and
physical/web/hybrid delivery. Other genres become profiles or extensions, not
Kernel exceptions.

## Agentic climb language

A **Frozen Instrument** defines dimensions, weights, acceptance rules, blind
protocol, and hard gates before a measured round. A **Task** binds one Candidate
and Instrument to an **Authority**. An agent occupying that Task leaves an
exact **Model Receipt**; a judge also receives an explicit **Exposure Ledger**.

An unblinded harvest produces quoted **Findings**, never a score. Findings are
translated into property-level **Requirements** so the builder does not receive
judge-only answers. A builder returns an immutable **Proposal**. It is not a
Draft Revision and has no transition authority. A **Review** either rejects it
or approves every named Requirement; only that exact approval may create a
**Transition** and child Draft. An **Agent Review** carries the independent
reviewer's Model Receipt and cannot share a principal with the builder. A
**Human Review** is the equivalent optional first-order decision from a person.
_Avoid_: self-approval, bare CI.

A fresh judge then measures the frozen child under the unchanged Instrument.
A **Standing Attestation** says exactly what the evidence supports. Agentic
standing and human-play evidence remain separate: neither impersonates the
other. Model identity is an
occupancy receipt, not domain identity, so different providers and models can
fill the same typed Task without changing the Kernel or losing lineage.

A **Blind Trial** is a complete authorized player-facing projection of one
compiled Candidate. It contains the materials, access, sequence, and production
evidence needed for judgment while excluding trusted truth, answer keys,
provenance, prior scores, and builder rationale. _Avoid_: source summary,
anonymized Candidate.

A **Selection Decision** applies one Frozen Instrument's acceptance rules to
baseline and child Evaluations after hard gates replay. It chooses evidence for
the next rung; it does not authorize a Draft transition or confer human-play
Standing. _Avoid_: approval, acceptance.

A **Candidate** is the compiler's complete frozen game input: canonical Game
Definition, exact materials, seed, compilation options, and Component Lock.
Workspace may checkpoint a Draft, but that checkpoint is not measurement
identity. _Avoid_: Draft checkpoint, branch head.

An **Experiment** is one operator-owned, persisted quality-climb lineage under
one Experiment Plan. It contains Tasks, evidence, Reviews, Transitions, and
Selection Decisions without owning game-profile authoring rules.
_Avoid_: run, benchmark folder, Ashwood climb.

A **Game Profile Adapter** is the versioned boundary that builds and revises a
specific game profile for an Experiment. Its identity is frozen in the Plan;
changing it creates a different Experiment contract.
_Avoid_: experiment plugin, fixture builder.

A **Complete Package** binds one Candidate to its exact Game Release, Physical
Export, Blind Trial, and replayed hard gates before measurement.
_Avoid_: build output, trial ZIP.

An **Artifact Truth Binding** couples one artifact's exact request truth values
to the semantic projection of the canonical Propositions, truth assignments,
and Events they claim to express. Changing either side invalidates the binding;
it is never a second owner of world truth.
_Avoid_: copied canon, document facts, truth snapshot.

An **Artifact Suite Import** admits an already forged, independently measured,
attested Verismill suite into one exact Game Blueprint. Import verifies and
binds evidence; it never implies that the game library forged, rebuilt,
remeasured, or upgraded the suite.
_Avoid_: artifact materialization, forge adapter, suite build.

A **Human Receipt** is the exact persisted observation of a human judge
occupying a Task. It is first-order evidence and is never represented as a
Model Receipt.
_Avoid_: manual model result, unstructured feedback note.

A **Game Blueprint** is the editable source for one game: its canonical game
structure, rich-text Materials, deterministic seed, and Arc Beats. It derives a
Game Definition and Candidate; it is not itself a measured Candidate.
_Avoid_: prompt, game JSON, mutable Candidate.

An **Arc Beat** states the dramatic question, intended player shift, target
duration, and Evidence delivery for one Phase. It is authoring intent checked
against canonical Reveals, not a second runtime timeline.
_Avoid_: chapter, scene script, Phase.

An **Authoring Operation** is one typed, reviewable change to a Game Blueprint
that names the Requirements it addresses. A set of operations remains an inert
Proposal until an exact independent Review authorizes a Transition.
_Avoid_: JSON patch, autonomous edit, rewrite.

A **Playtest Protocol** is the frozen human-play contract for one exact
Candidate, Release, Physical Export, and Instrument. It fixes consent,
participant, observation, freshness, and standing requirements before play.
_Avoid_: test plan, survey template, facilitator notes.

A **Playtest Run** is one completed live Session with a distinct participant
cohort, exact production receipt, consent receipts, observations, and scores.
Reviewing a Blind Trial without playing is not a Playtest Run.
_Avoid_: Human Receipt, model simulation, demo.

A **Play Observation** is a phase-scoped human statement preserved with its
exact response and the role from which it was observed.
_Avoid_: model finding, retrospective summary, score.

An **Evidence Comparison** records agreement or divergence between blind model
measurement and Playtest Runs for the same Candidate and Instrument. It is
diagnostic evidence; it does not average humans and models into one voice.
_Avoid_: combined score, ensemble verdict.

## Simulation-evaluation language

An **Evaluation Panel** is the release-independent, version-locked measuring
population and complete Episode matrix: model policies, prompts, tools,
sampling settings, host policies, behavioral conditions, role rotations,
seeds, scheduling, and evaluation-only context rules. It describes the test,
not where a run happens. _Avoid_: agent team, benchmark, game-specific lineup.

A **Panel Application** binds one Evaluation Panel to one immutable Release and
proves that every required role, tool, condition, and Episode assignment remains
compatible. It does not change Panel identity. _Avoid_: configured panel,
release-specific benchmark.

An **Analysis Instrument** is the independently versioned set of analysis-agent
roles, prompts, Failure Atlas, rubric, attribution rules, and aggregation rules
used to interpret preserved Episodes. Changing it creates a new analysis series
without changing or rerunning the Evaluation Panel. _Avoid_: panel rubric,
self-judging agents.

An **Analysis Authority** is one named responsibility in that Instrument:
Incident Discoverer, Semantic Interpreter, Attribution Analyst, Atlas Curator,
Challenge Designer, or Independent Reviewer. Authorities may communicate when
the communication is exposed, but independently occupied authorities cannot
receive one another's conclusions before freezing their own. _Avoid_: analyst,
omniscient judge.

An **Evidence View** is the exact content-addressed projection an Analysis
Authority may inspect. Its **Analysis Receipt** binds that view and Exposure
Ledger to the occupying principal, model configuration, structured conclusion,
trace citations, alternatives, confidence, and upstream receipts without
requiring private chain-of-thought. _Avoid_: context dump, judge transcript.

A **Discovery Sweep** is one independently occupied, truth-blind application of
a frozen discovery lens to an Episode Evidence Package. It emits trace-cited
Failure Signal proposals or an explicit no-finding receipt before any
cross-sweep synthesis, and cannot see other sweeps' conclusions. The Analysis
Instrument's fixed sweep roster determines discovery coverage.
_Avoid_: detector pass, generalist review, root-cause analysis.

**Sweep Coverage** records the global Episode structure and factual-graph
regions a Discovery Sweep traversed, the exact spans it expanded, its search
for counterevidence, and every omitted, truncated, or failed region. Selective
inspection without this receipt is not a complete Sweep.
_Avoid_: context-window size, transcript summary, implied coverage.

**Sweep Completion** is `complete` only when the frozen coverage contract and
counterevidence search finish. Budget exhaustion produces `partial` with an
exact continuation cursor; a partial Sweep may preserve provisional Signals but
cannot corroborate an Incident, and only a complete Sweep may report no finding.
_Avoid_: timeout as no finding, best-effort complete, discarded partial pass.

A **Novel Signal Proposal** is a trace-cited expected-versus-observed gap that
a Discovery Sweep cannot express with the Analysis Instrument's frozen known
patterns. It follows the same Discovery Corroboration rule as a known-pattern
proposal and cannot create an Atlas class, alter Standing, or harden a task.
_Avoid_: new failure class, other label, taxonomy update.

**Incident Assembly** is a separately occupied, truth-blind grouping of frozen
Discovery Sweep outputs into proposed Failure Incidents. It may group, split,
preserve exclusions and disagreement, or request a targeted additional Sweep;
it cannot invent a Signal, suppress a sweep receipt, assign cause, consult the
Failure Atlas, or alter cited evidence. Signals may share an Incident only when
they concern the same expected milestone, required transition, terminal claim,
or directly linked obligation and have overlapping windows or an explicit
factual-graph connection. _Avoid_: root-cause synthesis, thematic clustering,
majority vote, incident judge.

**Discovery Corroboration** is the independent evidence check required before a
proposed Failure Incident may enter Semantic Interpretation. Eligibility needs
either convergence by two independently occupied Discovery Sweeps or
confirmation by a separately occupied targeted Sweep that receives the claim
but not the first principal's reasoning. Failed or materially conflicting
corroboration leaves an unresolved Signal proposal; it is never silently
discarded. _Avoid_: majority confidence, self-confirmation, duplicate sampling.

An **Analysis Lineage** is the dependency path from one Episode through its
Signals, Incident, interpretations, Attributions, and any resulting Atlas or
Challenge proposal. Principal conflicts are enforced within a Lineage so no
agent analyzes, validates, classifies, or reviews its own contribution; a
principal may be reused on an unrelated Lineage. _Avoid_: globally unique
agent, authority identifier alone.

An **Episode Evidence Package** is the content-addressed source for every
Evidence View of one Episode. Its **Canonical Episode Evidence** preserves what
was recorded—including actions, observations, results, messages, visibility,
state transitions, receipts, and errors—without asserting that spoken content
is true. A message proves what was said; only corroborating evidence can prove
the proposition it expresses. _Avoid_: transcript as truth, cleaned trace.

A **Verification Status** states which Episode or evidence spans can be
reconstructed and trusted for a particular claim. Invalid or incomplete spans
remain evidence with explicit limitations rather than invalidating unrelated
recorded history. _Avoid_: valid Episode as an all-or-nothing property.

A **Derived Episode Fact** is a reproducible result computed from Canonical
Episode Evidence and a frozen Release by a named, versioned derivation. A
**Semantic Annotation** is an append-only agent or human interpretation over
exact cited spans, using a frozen vocabulary, confidence band, alternatives,
and provenance. Factual graph edges remain distinct from semantic overlays.
_Avoid_: inferred fact, mutable label, free-form score.

**Auxiliary Commentary** is a safe reasoning summary or self-explanation kept
outside default Evidence Views. It may suggest exploratory hypotheses but
cannot support standing, causal Attribution, or task hardening and never
contains required private chain-of-thought. _Avoid_: rationale as evidence.

A **Release Comparison** is the auditable relationship between baseline and
candidate Panel Applications under one Evaluation Panel and one Analysis
Instrument. It names whether model identity is exactly or operationally matched
and preserves all missing and invalid Episodes; an incomplete comparison may be
inspected but cannot support a release-selection claim. _Avoid_: score delta,
winner.

A **Difficulty Experiment** applies one Evaluation Panel and one Analysis
Instrument to one or more immutable Releases. Changing either starts a new
experiment series rather than extending an existing primary comparison.
_Avoid_: training run, simulation batch.

A **Difficulty Profile** is the trace-derived distribution of outcomes,
integrity, progress, dependence, coordination, effort, and bottlenecks for one
Release under one Evaluation Panel. It is diagnostic evidence, not reward or
Standing. _Avoid_: difficulty score, leaderboard result.

Its seven canonical **Profile Dimensions** are Episode validity, resolution
reliability, progress and effort, proof robustness, coordination quality,
recovery dependence, and sensitivity or brittleness. Each remains a
distribution with exact Episode references and experimental slices; no weighted
overall difficulty scalar is canonical. Artifact realism and human-play evidence
retain their independent measurement systems. _Avoid_: composite reward,
realism-adjusted difficulty, model-human average.

An **Uncertainty Envelope** binds a profile statistic to exact observations,
valid, invalid, and missing counts, coverage, the independent sampling unit,
correlation groups, point and interval methods, and matched-comparison identity.
Binary rates use 95% Wilson intervals; count and continuous diagnostics use
median, interquartile range, and stratified 95% bootstrap intervals only with at
least eight independent assignments. Smaller samples are `insufficient`.
_Avoid_: turn-level sample size, omitted denominator, false precision.

A **Difficulty Target Contract** is the profile-specific, versioned declaration
of required Panel coverage, minimum independent assignments, eligibility gates,
dimension and condition bands, brittleness tolerances, classification rules,
and descriptive-only measures. An Experiment pins it before execution; changing
the Contract starts a new target series and cannot reclassify historical
Profiles in place. _Avoid_: universal difficulty threshold, mutable target.

A **Difficulty Classification** is `too-easy`, `too-hard`, `brittle`,
`provisionally-target-band`, `supported-target-band`, or `indeterminate` under
one Difficulty Target Contract. Conclusive easy or hard claims require the 95%
interval outside the relevant band; supported target claims require gating
intervals inside it. Point estimates may support only provisional target status,
and incomplete or invalid required coverage is indeterminate.
_Avoid_: pass or fail, point-estimate standing, missing run as failure.

A **Calibration Suite** is the frozen set of independently authored easy,
target-shaped, hard, and brittle reference Releases used to derive and validate
one Difficulty Target Contract. The Panel and Instrument applied to it match
candidate measurement; the derivation must separate the controls before the
Contract can support Standing. Candidate results never recalibrate their own
target. _Avoid_: guessed threshold, candidate-relative target, live tuning.

**Target Dominance** is the non-scalar Selection rule between matched Release
Profiles. A child must preserve integrity and completeness, move no gating
dimension or required slice conclusively farther from band, and move at least
one declared repair target closer under paired uncertainty. Only trade-offs
frozen in the Target Contract are permitted; otherwise neither Release
dominates and the Selection remains indeterminate.
_Avoid_: weighted winner, post-hoc trade-off, narrative selection.

A **Failure Signal** is one trace-addressable observation of an unmet
constraint, milestone, or expected state transition. It states what happened
without claiming why. _Avoid_: root cause, model critique.

A **Failure Incident** groups related Failure Signals from one Episode around
one failed or suspicious outcome. Each claim names the Verification Status of
its supporting spans; unverified evidence constrains that claim without erasing
unrelated usable history. _Avoid_: failed run, bug report.

A **Failure Attribution** is an evidence-backed causal hypothesis that relates
an Incident to contributing actors, interactions, or owning layers while
preserving confidence and alternative explanations. It may be multi-label and
unresolved; it is not an assignment of blame. _Avoid_: root cause, guilty agent.

A **Causal Hypothesis Set** is one independently frozen Attribution output. It
relates candidate factors across Actor, interaction, Seat, host, game, runtime,
provider, and evaluator layers; names each factor as necessary, sufficient,
contributing, amplifying, recovery, or confounding; and binds evidence,
counterevidence, alternatives, confidence, and a falsifiable counterfactual
prediction. Interaction hypotheses remain explicit rather than being flattened
into equal labels. _Avoid_: ranked blame list, single root cause, confidence sum.

**Attribution Agreement** is overlap between two isolated Causal Hypothesis
Sets. It prioritizes a hypothesis for testing but cannot establish an owning
layer or authorize a repair requirement without counterfactual evidence or a
deterministic minimal reproduction. _Avoid_: analyst consensus as proof,
ensemble confidence.

A **Coordination Failure** is a system-level Incident caused by the relationship
between otherwise locally plausible agent actions, information states, or
handoffs. It cannot be reduced to an invalid action by one Actor.
_Avoid_: weak agent, inactivity.

A **Failure Class** is a reusable, versioned definition with explicit
inclusions, exclusions, observable signatures, counterexamples, and a rerunnable
detector or frozen rubric. _Avoid_: tag, free-form category.

A **Class Evidence Stage** records whether a Failure Class is `proposed`,
`experimental`, or `promoted`. Proposal needs one independently corroborated
Incident; experimentation needs two distinct Analysis Lineages or a deterministic
minimal reproduction; promotion needs three Lineages spanning two evaluation
axes or a deterministic reproduction, plus positive and non-manifesting
fixtures, rerunnable measurement, independent review, and sealed non-regression.
Causal ownership remains separate. _Avoid_: occurrence count, popularity,
curator confidence.

**Class Evolution** is append-only. Compatible clarification versions one
stable class identity; material splits and merges create new identities linked
from every superseded source. Deprecation discourages new classification, while
retirement removes a class from future Instruments. Historical observations,
detectors, fixtures, challenges, and measurements retain their exact original
class versions; migrations add annotations rather than rewriting them.
_Avoid_: rename in place, deleted class, historical relabeling.

**Class Retirement** is an independently reviewed Atlas change supported by
demonstrated invalidity, systematic false positives, explicit scope removal, or
supersession with migration. Absence of recent observations is not evidence for
retirement. A class normally remains deprecated for one Atlas version first;
immediate retirement requires evidence that continued use invalidates
measurement. _Avoid_: unused cleanup, silent removal, detector deletion.

A **Failure Atlas** is the versioned graph of Failure Classes and their
supporting, refuting, and unresolved evidence. An Atlas revision changes future
instruments; it never rewrites historical Difficulty Profiles or Standing.
_Avoid_: error list, self-updating rubric.

The **Atlas Workbench** is the append-only research surface for proposed and
experimental classes, failed promotions, evidence, disagreement, detector
drafts, and review receipts. The **Published Failure Atlas** contains only
independently accepted class versions and lifecycle links. Analysis Instruments
pin a Published Atlas version; Workbench evolution does not change experiment
identity, while publication does. _Avoid_: experimental class as active rubric,
mutable published atlas.

An **Atlas Revision Proposal** is an immutable Atlas Curator output that names
its parent Atlas, exact class and evidence changes, migrations, detector and
fixture effects, and complete Analysis Lineage. An Independent Reviewer may
accept or reject an eligible Proposal but cannot edit it or waive a gate; only
a deterministic **Atlas Transition** materializes an accepted Proposal as a new
Atlas version. Human evidence may supplement but is not mandatory.
_Avoid_: live taxonomy edit, reviewer patch, autonomous promotion.

A **Counterfactual Episode** is a new Episode that changes exactly one declared
experimental factor under an otherwise identical Evaluation Panel to test a
causal dependency. It is not a replay of the original trajectory.
_Avoid_: retry, trace edit, ablation replay.

A **Counterfactual Contrast** binds a predeclared causal prediction and fixed
invariants to matched factual and Counterfactual Episodes that differ in one
factor. A contrast may test a hypothesis but cannot by itself establish an
owning layer. _Avoid_: before-and-after anecdote, post-hoc explanation.

A **Counterfactual Plan** is a content-addressed selection of single-factor
Contrasts designed by a principal distinct from the hypothesis authors. It
freezes competing hypotheses, discriminating predictions, invariants, controls,
and stop conditions before new Episodes execute. A fresh isolated Attribution
pair interprets the results, and neither planners nor interpreters may accept
their own Owning-Layer Finding. _Avoid_: favorable test selection, adaptive
story, self-confirming ablation.

A **Counterfactual Factor** is one versioned experimental variable from the
frozen registry: policy occupancy, Seat or role design, host policy, culprit
behavior, proof path or evidence availability, communication condition, game
affordance or reveal policy, runtime or provider, or evaluator or Analysis
Instrument. Each Contrast changes one Factor; an interaction hypothesis uses a
minimal factorial matrix whose edges remain single-factor Contrasts.
_Avoid_: bundled mutation, unnamed condition, post-hoc factor.

A **Diagnostic Cross-Contract Contrast** tests a runtime, provider, evaluator,
or Analysis Instrument factor that cannot vary within one primary experiment
identity. It creates an explicitly separate diagnostic lineage with every
contract difference visible; it may support causal ownership but cannot enter
the original Difficulty Profile, Standing, or same-instrument Release
Comparison. _Avoid_: matched primary comparison, silent panel drift.

An **Owning-Layer Finding** is a reviewer-accepted causal conclusion supported
by either two orthogonal Counterfactual Contrasts whose frozen predictions hold
or a deterministic minimal reproduction. One contrast plus replication marks a
hypothesis tested, not owned; an owning layer need not be the sole cause.
_Avoid_: likely owner, analyst agreement, repair target.

**Partial Attribution** is the state in which at least one factor has an
accepted Owning-Layer Finding while other material causal branches remain
unresolved. A scoped Causal Repair may address the accepted factor without
claiming sole cause or closing the Incident; conflicting evidence remains
explicit rather than being averaged. _Avoid_: resolved root cause, partial fix
as incident closure.

A **Causal Repair** changes an accepted owning layer and may resolve the linked
Owning-Layer Finding after its predicted effect is validated. A **Resilience
Mitigation** changes another layer to reduce recurrence or impact; it preserves
the causal record and cannot close or relabel the originating Finding. Both
retain their own predictions, trade-offs, and validation evidence.
_Avoid_: convenient fix as cause, mitigation as repair, closed by workaround.

A **Challenge Case** is a validated scenario or mutation derived from one
Failure Class with an oracle, feasibility proof, non-manifesting control, and
declared development or sealed-holdout status. _Avoid_: generated test prompt,
adversarial example.


## Character-play language

A **Dossier** is the complete Seat-private character source, containing a
scannable **Quick Start** and deeper canonical context for sustained play.
_Avoid_: character sheet, bio, summary page.

A **Knowledge Boundary** divides facts a Character knows, beliefs they may
revise, lies they may tell, and facts they must not contradict. It is canonical
policy, not prompt memory.

A **Phase Arc** names one Character's pressure, active Objectives, and available
**Moves** during one Phase. A Move is a permitted action, bargain, challenge,
fallback, or post-exposure response; it offers agency without scripting.

A **Reveal Path** is a fair disclosure window for a private truth together with
its host-owned recovery Intervention. _Avoid_: forced reveal, clue drop.

**Character State** is the replayable Session record of chosen Moves, evolving
beliefs, Objective progress, and human direction. A **Character Agent** is an
optional Actor occupying a Seat under the same Knowledge Boundary and Session
Authority as a human player. _Avoid_: agent memory, NPC bot, autonomous player.

## Publication language

A **Release Qualification** is a content-addressed decision over one library
version, one policy version, one exact reference Candidate, and all required
Stage 8-12 evidence. It reports every gate independently and cannot create or
upgrade game Standing. _Avoid_: release checklist, green build, readiness.

**Distribution Readiness** means the sdist, wheel, dependency versions,
compatibility promise, documentation, and support-matrix receipts are complete.
It does not imply any particular reference-game Standing.
_Avoid_: public release, production ready.

**Agentic Standing** is exact-version machine-qualified evidence from at least
two independently occupied passing Blind Evaluations plus a review agent who
was neither builder nor judge. It can qualify the reference game without
claiming observed human experience.

**Human Play Evidence** is optional first-order evidence from completed live
Playtest Runs. It is reported separately and may create new Findings or a
human-play Standing Attestation; its absence never blocks agentic progression.

**Reference Game Standing** is the exact Candidate standing named by a Release
Qualification. Policy version 2 requires Agentic Standing; any human-play
standing is additional evidence, not a substitute or gate.

A **Release Attestation** is an independent release agent's exact Model Receipt
over the policy, library version, reference Standing, and distribution hashes.
Its principal is distinct from builders, judges, and the standing reviewer.
_Avoid_: Publisher Approval, merge approval, bare CI pass.
