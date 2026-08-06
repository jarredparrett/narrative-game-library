# Public release requires accepted reference-game standing

- Status: accepted
- Date: 2026-08-06

## Context

A wheel can be reproducible, documented, and installable while its first-party game has never survived exact-version human play. Calling both states “release ready” would collapse distribution evidence into a quality claim and undermine the library's human-first measurement model.

## Decision

Public Release Qualification is a deterministic report over twelve frozen Stage 8-12 gates. Distribution Readiness is necessary but insufficient: qualification also requires accepted human Standing for one exact reference Candidate, independent standing review, and a separate human Publisher Approval scoped to the policy, library version, Standing, and sdist/wheel hashes. The evaluator reports failures but never manufactures evidence or upgrades Standing.

## Consequences

Version 0.16 can publish an honest `not_qualified` report even when every automated test passes. The first public release remains gated by real play and tagged Verismill/Mattermill releases; downstream games inherit library contracts, not the reference game's Standing.
