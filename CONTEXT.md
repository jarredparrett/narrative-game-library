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
