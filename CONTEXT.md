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
