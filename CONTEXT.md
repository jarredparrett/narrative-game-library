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

An **Analysis Lineage** is the dependency path from one Episode through its
Signals, Incident, interpretations, Attributions, and any resulting Atlas or
Challenge proposal. Principal conflicts are enforced within a Lineage so no
agent analyzes, validates, classifies, or reviews its own contribution; a
principal may be reused on an unrelated Lineage. _Avoid_: globally unique
agent, authority identifier alone.

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

A **Failure Signal** is one trace-addressable observation of an unmet
constraint, milestone, or expected state transition. It states what happened
without claiming why. _Avoid_: root cause, model critique.

A **Failure Incident** groups related Failure Signals from one verified Episode
around one failed or suspicious outcome. An invalid or incomplete Episode may
produce an infrastructure Incident but cannot establish game difficulty.
_Avoid_: failed run, bug report.

A **Failure Attribution** is an evidence-backed causal hypothesis that relates
an Incident to contributing actors, interactions, or owning layers while
preserving confidence and alternative explanations. It may be multi-label and
unresolved; it is not an assignment of blame. _Avoid_: root cause, guilty agent.

A **Coordination Failure** is a system-level Incident caused by the relationship
between otherwise locally plausible agent actions, information states, or
handoffs. It cannot be reduced to an invalid action by one Actor.
_Avoid_: weak agent, inactivity.

A **Failure Class** is a reusable, versioned definition with explicit
inclusions, exclusions, observable signatures, counterexamples, and a rerunnable
detector or frozen rubric. _Avoid_: tag, free-form category.

A **Failure Atlas** is the versioned graph of Failure Classes and their
supporting, refuting, and unresolved evidence. An Atlas revision changes future
instruments; it never rewrites historical Difficulty Profiles or Standing.
_Avoid_: error list, self-updating rubric.

A **Counterfactual Episode** is a new Episode that changes exactly one declared
experimental factor under an otherwise identical Evaluation Panel to test a
causal dependency. It is not a replay of the original trajectory.
_Avoid_: retry, trace edit, ablation replay.

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
