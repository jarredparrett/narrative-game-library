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

## Climb design principles

These principles carry Stage 7's evidence into reusable orchestration without
turning one worked mystery into the architecture:

1. **Bound the proof.** Each stage answers a named design question. A measured
   failure is a valid outcome when lineage is complete and selection remains
   honest; fixture polishing continues only when it tests a new general rule.
2. **Validate information in time.** A form, fact, or action required at one
   phase must be available in that phase. Later delivery cannot satisfy an
   earlier dependency.
3. **Preserve earned disclosure.** Shared or opening projections must not
   duplicate the private or later facts whose interpretation creates play.
4. **Separate character voice from procedure.** Operational instructions may
   be systematic, but character-authored records and role decisions need
   distinct language, knowledge, and agency.
5. **Make measurements applicable.** Every preflight or judge claim declares
   which artifact classes it can measure. A skipped or inapplicable check is
   never reported as evidence of quality.
6. **Let evidence inform humans, not replace them.** Agents propose and measure;
   humans may approve direction. Frozen selection rules decide only which
   measured Candidate supports the next rung.
