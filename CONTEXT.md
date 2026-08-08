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

## Persistence language

An **Evidence Object** is immutable, content-addressed authoritative material
such as a Release, Episode, analysis, receipt, profile, Atlas revision, suite,
contract, or sealed external payload. Its identity is its canonical bytes, not
its filename or current location. _Avoid_: output file, mutable record, path ID.

An **Evidence Journal** is an append-only hash-chained history of authorized
domain events. Each event binds its actor, causal parent, idempotency identity,
and referenced Evidence Objects; the Journal orders authority but does not copy
or mutate object content. _Avoid_: audit log as cache, editable event stream.

An **Evidence Projection** is a disposable, rebuildable view derived entirely
from verified Journals and the transitive Evidence Object graph. It may support
monitoring, search, current Standing, and reports but cannot support a claim by
itself. _Avoid_: authoritative dashboard, current file as evidence.

A **Claim Manifest** is the immutable root of evidence for one reportable claim.
It names the claim and status, its exact typed Evidence Object roots, governing
contracts and schema versions, Journal authorization event, and required replay
verifiers. Its transitive object graph must verify without relying on a path or
Projection. _Avoid_: workspace archive as claim, link list, current head.

**Evidence Object Granularity** follows independent versioning and authority: a
Panel, Instrument, Episode Archive, Discovery Sweep, Incident, Attribution,
Counterfactual Plan, Difficulty Profile, Atlas Revision, Challenge Case,
Scheduling Receipt, or Standing Attestation is independently addressable. A
whole Workspace is not one object, and fields without independent identity are
not fragmented into separate objects. _Avoid_: monolithic evidence blob,
object-per-field.

The **Minimum Evidence Catalog** preserves every input and output at an
authority boundary. It includes frozen Release, Panel, Instrument, authority,
sampling, suite, target, and cost contracts; assignments, Episode Archives,
verification, prompts, model and tool receipts, and runtime outcomes; Evidence
Views, Sweeps, Signals, Incidents, hypotheses, Attributions, Counterfactuals,
Profiles, uncertainty, Atlas and Challenge objects, and Scheduling Receipts;
and Reviews, Transitions, Selections, Standing Attestations, and Claim Manifests.
Rejected, refuted, invalid, and incomplete objects remain in lineage.
_Avoid_: success-only archive, discarded proposal, summarized failure.

**Re-verification** reruns pinned deterministic verifiers over the exact stored
objects and must reproduce a Claim Manifest's status. **Re-execution** asks the
same provider or policy to act again and is best-effort because stochastic or
retired services may produce another trajectory. Provider-native requests and
responses may be sealed as external Evidence Objects for diagnosis, but the
canonical Episode Archive remains authoritative and inaccessible hidden
reasoning is neither required nor claimed. _Avoid_: model repeatability as
replay, provider log as Episode truth, fabricated thought trace.

The **User Data Root** is the operator-owned location outside source control
that contains Experiment Workspaces. An explicit user path wins, followed by a
dedicated configuration override, then the platform application-data default.
A repository-local ignored Workspace is opt-in rather than default. Credentials
belong to a separate secret authority and never enter Evidence Objects or
exports. _Avoid_: committed experiment, implicit current directory, archived
API key.

A **Workspace Archive** is the deterministic portable closure of one complete
Experiment Workspace: its Journals, every reachable Evidence Object, and a
canonical inventory. A **Claim Capsule** is the minimal portable closure of one
Claim Manifest plus required Journal inclusion proofs, schemas, and verifiers.
Both exclude credentials, absolute paths, locks, caches, and Projections and are
fully verified before import exposes a view. _Avoid_: copied folder, partial
claim ZIP, trusted archive path.

An **Evidence Schema Identity** independently versions one stable Evidence
Object kind, its canonicalization, producer component, and verifier contract.
Breaking interpretation changes advance that kind's major schema; compatible
additions advance its minor schema. Object, Journal, archive, and Projection
formats evolve independently rather than inheriting the package version.
_Avoid_: one global schema number, package version as evidence meaning, implicit
canonicalization.

An **Evidence Migration** is an append-only deterministic conversion from one
Evidence Object to another. Its Migration Receipt binds source and destination,
migrator identity, schema change, warnings, and loss declaration. A lossless
format conversion may preserve claim meaning; semantic reinterpretation starts
a new analysis or claim lineage under normal review. Unknown schemas remain
preservable and exportable even when not currently interpretable.
_Avoid_: in-place upgrade, silent coercion, migration as reanalysis.

A **Verifier Bundle** is the content-addressed offline runtime needed to
re-verify a Claim Manifest: verifier entry points, exact library artifacts,
dependency lock, supported runtime, and integrity hashes. Standing, Atlas and
framework promotion, and release claims require one in their portable closure;
a source commit or package name alone is insufficient. Model or provider access
is unnecessary because verification replays recorded evidence.
_Avoid_: install latest, network-required replay, verifier by convention.

**Durable Evidence** is any object reachable from an Evidence Journal or Claim
Manifest. It is retained by default and never automatically collected. An
explicit operator prune requires a verified replacement archive and appends an
**Evidence Tombstone** naming removed hashes, reason, archive identity, and
affected claims; any missing required object makes those claims
non-reverifiable. Caches, locks, partial downloads, and unsealed intermediates
are ephemeral. Consumed sealed cases remain durable under a changed access
state. _Avoid_: age-based evidence deletion, silent prune, sealed-case erasure.

A **Lineage Edge** is an immutable typed relation between Evidence Objects. Its
families cover identity (`applies-to`, `occupies`, `measured-under`), evidence
(`observes`, `supports`, `refutes`, `invalidates`), derivation (`derived-from`,
`generated-from`, `aggregates`), experiment (`controls`, `contrasts-with`,
`replicates`), authority (`proposed-by`, `reviewed-by`, `authorized-by`),
versioning (`supersedes`, `migrates-from`, `deprecates`), suites (`member-of`,
`exposed-from`, `retired-to`), and selection (`compares`, `selects`, `rejects`).
Historical and derivation subgraphs are acyclic; disagreement uses opposing
edges rather than mutation. _Avoid_: generic parent, inferred filename edge,
overwritten conflict.

A **Workspace Checkpoint** is an immutable coherent snapshot that pins the
verified heads of the separate lineage, operations and scheduling, climb and
analysis, qualification, and access and exposure Journals. Claim Manifests bind
one Checkpoint. A partial cross-Journal update cannot displace the previous
Checkpoint until every intended head and object verifies. _Avoid_: one global
journal, latest file from each stream, assumed cross-file transaction.

**Logical Evidence Order** comes from Journal sequence, prior hash, causal event
references, and Workspace Checkpoint rather than wall-clock time. Timing matters
only when a caller supplies a hashed Time Observation with its clock source and
uncertainty; the library never samples a clock implicitly to define evidence
identity or causality. _Avoid_: timestamp order, render time as evidence,
implicit now.

**External Evidence Portability** requires exact third-party bytes needed by a
qualifying claim to be sealed as Evidence Objects. Source URI, provider ID,
media type, and acquisition receipt remain provenance, not storage. Evidence
that cannot be captured makes its claim `externally-dependent` and ineligible
for offline-verifiable Standing. _Avoid_: URL as evidence, provider lookup as
replay, path-only attachment.

A **Reproducibility Status** is `complete` when the Claim Manifest closure,
Checkpoint, schemas, and Verifier Bundle all verify; `degraded` when optional
diagnostic attachments are unavailable; `externally-dependent` when required
bytes remain remote; `unsupported` when preserved evidence lacks a runnable
schema or verifier; or `corrupt` when integrity fails. Only `complete` may
support offline-verifiable Standing. _Avoid_: warning-only missing evidence,
unknown means pass, archive present means reproducible.

An **Evidence Import** verifies an Archive or Capsule in quarantine, deduplicates
Evidence Objects by hash, and appends an Import Receipt that binds the source
Workspace identity, source Checkpoint, archive inventory, and destination
authorization. Source Journals retain their own identities and are never
spliced into a destination sequence. _Avoid_: merged event stream, trusted ZIP,
copied object without provenance.

**Projection Freshness** binds every Evidence Projection to its exact Workspace
Checkpoint and derivation contract. A Projection is `current` only when that
Checkpoint remains the authorized head, `stale` when any source Journal has
advanced, and `invalid` when its derivation or source closure fails verification.
_Avoid_: unversioned dashboard, last-modified freshness, plausible stale report.

An **Evidence Event** is the canonical Journal envelope containing its event
schema, Journal identity, sequence, prior hash, event type, Actor and Authority,
idempotency identity, causal event references, Evidence Object and Lineage Edge
references, and event hash. Authoritative domain content remains in referenced
objects rather than mutable event payload copies. _Avoid_: event as object dump,
untyped audit message, timestamp-only causality.

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

A **Standing Sampling Plan** precommits the estimand, assignment matrix, strata,
seeds, quotas, maximum sample size, invalid-replacement rule, and stopping rule
whose Episodes may enter one Difficulty Profile or Standing claim. Outcomes
cannot change membership or stop timing. _Avoid_: convenient sample, early stop
after pass, adaptive standing denominator.

A **Diagnostic Sampling Queue** is the adaptive, append-only ordering of
additional Episodes, Discovery Sweeps, Counterfactual Contrasts, replications,
and challenge runs selected to reduce uncertainty or improve the next
experiment. Its evidence remains diagnostic and cannot enter the current
Standing estimate. It may motivate a newly frozen Standing Sampling Plan in a
new series. _Avoid_: active sample pooled into standing, retroactive holdout.

A **Scheduling Priority Vector** orders eligible diagnostic work
lexicographically by required validity and coverage debt, proximity to a frozen
target or transition boundary, expected causal discrimination, uncertainty
reduction, promoted-failure regression risk, structural and Failure-Class
novelty, then expected cost and latency. A lower tier cannot compensate for a
higher-tier deficit; cost ranks alternatives only after required coverage and
decision relevance are preserved. _Avoid_: opaque utility score, cheapest first,
coverage traded for throughput.

An **Evidence Cascade** maps one explicit claim and its minimum sufficient
evidence to the cheapest eligible instrument: static validation, deterministic
replay or mutation, focused solver or Discovery Sweep, Counterfactual Contrast,
full fixed-panel Episode, then independent review or sealed check. Escalation
occurs only when the cheaper layer is ineligible or inconclusive; evidence from
a lower layer cannot decide a claim outside its authority. _Avoid_: full Episode
by default, structural proxy for semantic play, escalation without claim.

A **Scheduling Analysis** is an agentic proposal over one bounded evidence
snapshot. It estimates structural and Failure-Class novelty, causal
discrimination, regression risk, and likely information value, preserving
alternatives, uncertainty, evidence references, and its Model Receipt. A
deterministic **Scheduling Transition** alone applies the frozen eligibility,
suite-blindness, Priority Vector, and budget rules to select the next action.
Every eligible alternative and rejection reason remains inspectable.
_Avoid_: agent-edited queue, hidden ranking rationale, scheduler as analyst.

A **Budget Envelope** reserves cost, calls, tokens, wall time, and concurrency
for one evidence purpose: Standing assignments, invalid replacements,
diagnostic exploration, counterfactual discrimination, promoted-class
regression, sealed checks, or independently authorized contingency. Adaptive
reallocation is allowed only among diagnostic envelopes under a frozen rule;
Standing and sealed reserves cannot fund exploration. Exhaustion yields
`insufficient` or `unresolved`, never a favorable default. _Avoid_: shared burn
pool, borrowed holdout budget, success by exhaustion.

A **Sealed Scheduling Handle** is the only projection of a Sealed Cohort visible
to scheduling: opaque cohort identity, declared cost, eligibility state, and
predeclared promotion gate. Once launched, the complete Cohort yields one
aggregate decision receipt or remains incomplete. The scheduler cannot inspect
or reorder cases, react to interim outcomes, stop on a favorable partial result,
or expose case-level findings. _Avoid_: adaptive sealed sampling, partial
holdout pass, case-aware scheduler.

A **Coverage Cell** is one declared combination of independent evaluation axes:
Failure Class, proof path and evidence topology, Seat or policy occupancy,
communication condition, host and culprit policy, Release, seed, model family,
Game Profile, and target band. Structural Novelty means adding or repairing an
underrepresented Cell under a frozen Coverage Contract. Surface paraphrase does
not establish novelty, and repeated observations remain replications rather
than new coverage. _Avoid_: embedding distance as diversity, renamed fixture,
correlated volume as breadth.

A **Diagnostic Stop State** is frozen with the claim before adaptive work starts:
`resolved` by its required evidence threshold, `refuted`, `invalidated` by an
evidence-quality failure, `saturated` because no eligible action adds causal
discrimination or Coverage, or `unresolved` because its Budget Envelope expired.
The current lead of a preferred hypothesis is not a stop condition.
_Avoid_: stopped means solved, favorable early stop, silent abandonment.

An **Evidence Work Package** is the atomic schedulable evidence obligation for
one action. An Episode Package includes canonical execution, replay verification,
the complete frozen Discovery Sweep roster, corroboration, receipts, and costs;
a Counterfactual Package includes its complete matched matrix and independent
interpretation. Eligibility and budget reservation use the whole Package, and
an incomplete Package cannot support its claim. _Avoid_: partial cheap run,
selected sweep, unmatched contrast.

A **Replacement Chain** is the precommitted sequence of retry and substitute
assignments for one Standing Coverage Cell. A transient retry repeats the exact
assignment under a frozen policy; any substitute identity and order are fixed
before outcomes. Every invalid attempt remains in the Difficulty Profile, and
exhausting the Chain leaves the Cell incomplete. _Avoid_: favorable replacement,
erased invalid run, scheduler-selected seed.

A **Cost Model** is the versioned forecast of model calls, tokens, provider
spend, wall-clock latency, concurrency occupancy, retry burden, and complete
Evidence Work Package cost. Estimates use receipts matched by exact model,
runtime, and Package type and preserve uncertainty ranges; actual cost is always
recorded. New receipts may calibrate only a future Cost Model version.
_Avoid_: live price tuning, point-cost certainty, partial-package estimate.

**Assignment Immutability** means scheduling may choose when an assignment runs
but never who occupies it. An unavailable model, provider, host policy, Seat
assignment, tool version, or sampling lock may use only a predeclared
operationally equivalent route; otherwise the assignment pauses or remains
incomplete. Substitution creates a different Evaluation Panel and experiment
series. _Avoid_: cheaper fallback model, convenient policy swap, hidden panel
drift.

A **Scheduling Receipt** binds one Scheduling Transition to its evidence
snapshot, Scheduling and Cost Model versions, all eligible alternatives and
Priority Vectors, the Scheduling Analysis and Model Receipt, selected, deferred,
and rejected actions with reasons, protected and remaining Budget Envelopes,
forecast and actual costs, resulting stop state, and next eligible actions.
_Avoid_: current queue only, unexplained deferral, cost without decision lineage.

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
declared Suite Binding. _Avoid_: generated test prompt, adversarial example.

A **Suite Binding** immutably assigns a Challenge Case to one evaluation use.
The **Development Suite** is visible and supports debugging and regression; the
**Generated Challenge Suite** holds validated generated cases for difficulty
and diversity exploration; the **Sealed Standing Suite** contains independently
instantiated, withheld cases used only for Standing. A case exposed outside its
sealed execution boundary is permanently retired to development use, with its
history preserved. No development or generated-challenge case may later enter
the Sealed Standing Suite. _Avoid_: suite promotion, recycled holdout,
standing-by-volume.

A **Sealed Suite Curator** is a principal distinct from framework builders,
Challenge Designers, measured Actors, and Standing reviewers. It instantiates
cases from a frozen generation specification using hidden seeds or source
materials, freezes membership and oracles, and exposes only the projections
required for execution. _Avoid_: builder-selected holdout, secret test edited in
place.

A **Sealed Cohort** is a single-use subset of one versioned Sealed Standing
Suite assigned to exactly one framework-promotion attempt. The attempt receives
only the predeclared aggregate decision receipt. After that decision the Cohort
is consumed and can never judge another revision; if its contents are released,
they become development evidence. A failed Revision must face a fresh Cohort,
not tune against the prior result. _Avoid_: reusable hidden test, repeated
holdout probing, failure details as next-round gradient.

A **Challenge Admission** is the immutable evidence bundle required before a
case enters the Generated Challenge Suite. It binds the generation receipt and
must pass canonical compilation and coherence, authorization and reachability,
independent agentic solvability, oracle uniqueness or explicitly bounded
acceptable answers, leakage and shortcut review, a matched non-manifesting
control, and target-difficulty and novelty measurement. Deterministic validators
decide structural facts; isolated analysis agents decide semantic feasibility
under a frozen Admission Instrument. Human evidence may supplement but is not
mandatory. Semantic Admission requires two independent solver Lineages that
reach an authorized valid solution and one isolated adversarial review for
leakage, shortcuts, ambiguity, and impossible assumptions. Any unresolved hard
feasibility or leakage Finding quarantines the case as research evidence; it
cannot enter an evaluation suite. _Avoid_: generated means valid, one successful
rollout, validator as semantic judge.

A **Recursive Generation Cycle** uses evidence from measured Episodes and the
Published Failure Atlas to propose either a new Challenge Case or a deeper
change to the machinery that produces cases. Its search surface expressly
includes new research, domain models, prompts, tools, algorithms, adapters, and
generation code; recursion is not limited to parameter tuning or mutation of an
existing template. A Cycle may begin from a promoted Failure Class, a measured
coverage gap or performance plateau, or a research-backed generation
hypothesis. The latter two remain exploratory until their evidence earns any
required Failure Class and Atlas promotion; they cannot create evaluation
authority merely by generating a case. _Avoid_: fixed-template mutation loop,
automatic self-edit, novelty as authority.

A **Generation Intent** is the content-addressed objective frozen before one
Recursive Generation Cycle. It names the triggering evidence or research
hypothesis, desired capability, target Difficulty Profile, protected integrity
constraints, comparison rule, and stopping rule. It deliberately leaves the
method open: agents may research, redesign, add tools, or replace generation
code. _Avoid_: prescribed patch, mutable objective, post-hoc rationale.

A **Generation Campaign** is a resumable sequence of Recursive Generation
Cycles under one Generation Intent. The Intent freezes limits for attempts,
model and tool cost, wall time, and Sealed Cohort consumption. The Campaign
stops when its Framework Target Contract is satisfied, no admissible novel
candidate remains, repeated quarantines demand a newly scoped framework
revision, or a budget is exhausted. Its complete evidence persists for a later
Campaign; exhaustion never implies success or failure. _Avoid_: unbounded
self-editing loop, discarded plateau, budget-as-verdict.

A **Research Receipt** preserves every external source that materially informs
a Recursive Generation Cycle: stable source identity and retrieval date,
source-specific claims, the hypothesis derived from them, applicability limits
and contrary evidence, resulting domain-model, prompt, tool, algorithm, adapter,
or code changes, and the Model and tool receipts needed to replay the analysis
path. Research is optional, but research-derived changes without this receipt
are ineligible for framework promotion. _Avoid_: bibliography without claims,
research hidden in agent context, citation as validation.

A **Generative Framework Revision** is an immutable, reviewable proposal to
change that machinery. It cites the Failure Classes or coverage gaps motivating
the change, records research provenance when used, declares the expected effect
and affected generation surface, and is evaluated as a new framework version
against frozen development, challenge, and sealed-standing suites. The agents
that research, design, or implement the Revision may not occupy its Independent
Reviewer authority. The Revision cannot inspect or alter the sealed cases,
suite membership, oracle, or Instrument that judges it; only an accepted,
content-addressed transition makes it the generator for future cycles.
_Avoid_: current-run code patch, generator and judge changing together,
research-derived authority without measurement.

A **Framework Target Contract** freezes how one Generative Framework Revision
will be compared with its parent. Integrity gates require no regression in
feasibility, solvability, authorization, leakage resistance, artifact realism,
or narrative quality. Improvement must address named Failure Classes or profile
gaps and demonstrate better accepted-case yield or generation efficiency,
broader structural diversity, and target Difficulty Profile movement that
remains inside its solvability band. A fresh Sealed Cohort must pass. No weighted
aggregate can compensate for a failed integrity gate. _Avoid_: harder is better,
headline score, post-hoc success criterion.

A **Framework Transition** is the deterministic operation that installs one
independently accepted, content-addressed Generative Framework Revision as a new
framework version for future Campaigns. Parent versions, rejected revisions,
Research Receipts, cases, Suite Bindings, and evaluation evidence remain
replayable. Rollback selects an earlier version without rewriting history.
_Avoid_: generator overwritten in place, deleted failed experiment, mutable
default.


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
