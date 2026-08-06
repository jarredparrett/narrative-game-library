# Public-release qualification

Public release is a measured claim, not a synonym for “the wheel builds.” Policy
`narrative-game-public-release` version `2.0.0` evaluates one library version,
one exact reference Candidate, and twelve gates without upgrading Standing.

| Gate | Required evidence |
|---|---|
| Stage 8: portable Experiment | verified Workspace/ledger and exact Candidate, Release, Physical Export, and Blind Trial binding |
| Stage 9: reusable authoring | content-addressed Game Blueprint and Game Profile Adapter proof |
| Stage 10: agentic Standing | two independently occupied passing Blind Evaluations and machine-qualified Standing |
| Stage 10: independent verification | a review agent whose principal was neither builder nor blind judge |
| Stage 11: creator/player/print | one exact maker, host, player, and print lineage proof |
| Stage 12: tagged upstreams | released Verismill and Mattermill versions; git/commit pins fail |
| Stage 12: compatibility | stable contract epoch 1 and an exact compatibility-policy document |
| Stage 12: support matrix | passing content-addressed receipts for Python 3.11 and 3.13 |
| Stage 12: package artifacts | exact sdist and wheel hashes |
| Stage 12: documentation | exact quickstart, tutorial, extension, release-policy, and limitations documents |
| Stage 12: known limitations | nonempty, honest disclosure |
| Stage 12: release attestation | a distinct release agent and Model Receipt over the policy, version, Standing, and package hashes |

`qualify_public_release(experiment, evidence, evidence_objects=objects)` returns
a deterministic `ReleaseQualificationReport`. Every gate has an owner,
evidence refs, explanation, and remediation. Qualification requires all gates;
there is no blended readiness score. Every claimed `sha256:` object is rehashed
from the supplied bytes.

## Independence and human evidence

The builder, blind judges, standing reviewer, and release reviewer are separate
authorities. Authority IDs are not enough: their principals must also be
distinct. The two blind evaluations must pass under the frozen Instrument, and
the release reviewer must leave an exact `ModelReceipt`.

Human play remains a separate first-order evidence class. A live Playtest Run
may reveal defects, redirect a climb, or support a human-play Standing claim.
It is never synthesized from simulation and never required for agentic
qualification. A qualified report therefore claims a reproducible, independently
measured agentic system—not demonstrated human enjoyment.

## Version boundaries

- Public 1.0 requires contract epoch `1` and Semantic Versioning for the named
  public import and serialized-contract surfaces.
- Verismill and Mattermill must be consumed as released versions. Repository
  pins are permitted during prototyping but fail public qualification.
- A new policy version is required when gates, supported Python versions, or
  required evidence classes change. Existing reports retain their policy ID.

## Current disposition

Version 0.18 implements the policy and agent-only path, but is not automatically
declared qualified. The real report must still bind exact current evidence;
repository-pinned upstreams and the experimental contract epoch remain honest
failed gates until released versions and compatibility commitments exist.
