# Agentic qualification keeps human evidence optional

- Status: accepted
- Date: 2026-08-06

## Context

Mandatory human approval made every canonical transition and public release
depend on scarce external coordination. That prevented a kicked-off experiment
from reaching a reproducible conclusion even when independent blind agents,
exact receipts, frozen policy, and deterministic selection were available.
Removing human evidence entirely would lose the highest-fidelity observation
of actual play.

## Decision

The default loop is agentic and non-blocking. A builder Proposal requires an
independent Agent Review with an exact Model Receipt before transition. Agentic
Standing requires two independently occupied passing Blind Evaluations and a
third review agent. Public release additionally requires a distinct Release
Attestation bound to the policy, version, Standing, package hashes, and its
Model Receipt. Principals cannot cross these boundaries.

Human Review, Human Receipts, and live Playtest Runs remain first-order evidence
and are reported separately. They can redirect a climb or support an explicit
human-play standing claim, but they are not required for agentic transition,
standing, selection, or release.

## Consequences

An experiment can run end to end without waiting for a person while preserving
inspectable separation of duties. Agentic qualification never claims that
humans enjoyed, understood, or successfully played a game. Later human evidence
may reveal defects and start a new lineage without rewriting the earlier
attestation.
