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
  human review, Candidates, measurement, and standing. Agents propose; humans
  authorize canonical transitions and publication.
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
Draft Revision and has no transition authority. A human **Review** either
rejects it or approves every named Requirement; only that exact approval may
create a **Transition** and child Draft.

A fresh judge then measures the frozen child under the unchanged Instrument.
A **Standing Attestation** says exactly what the evidence supports. Offline or
model-only evidence cannot impersonate fresh human play. Model identity is an
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
Proposal until exact human Review authorizes a Transition.
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
It does not imply that the reference game has accepted human Standing.
_Avoid_: public release, production ready.

**Reference Game Standing** is the accepted, exact-version human evidence used
to prove the library's primary profile in a Release Qualification. It remains a
property of that Candidate, not of every game the library may create.

A **Publisher Approval** is a first-order human decision over the exact policy,
library version, reference Standing, and distribution artifact hashes. The
publisher must be distinct from the players, host, observers, and independent
standing reviewer. _Avoid_: merge approval, CI pass, maintainer sign-off.
