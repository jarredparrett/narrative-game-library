# Public-release qualification

Public release is a measured claim, not a synonym for “the wheel builds.” The
frozen `narrative-game-public-release` policy evaluates one library version,
one exact reference Candidate, and twelve gates without changing any source
Standing.

| Gate | Required evidence |
|---|---|
| Stage 8: portable Experiment | verified Workspace/ledger and exact Candidate, Release, Physical Export, and Blind Trial binding |
| Stage 9: reusable authoring | content-addressed Game Blueprint and Game Profile Adapter proof |
| Stage 10: accepted human Standing | at least the frozen number of passing fresh Playtest Runs, model-human comparison, and accepted Standing |
| Stage 10: independent verification | a human standing reviewer who did not play, facilitate, or observe |
| Stage 11: creator/player/print | one exact maker, host, player, and print lineage proof |
| Stage 12: tagged upstreams | released Verismill and Mattermill versions; git/commit pins fail |
| Stage 12: compatibility | stable contract epoch 1 and an exact compatibility-policy document |
| Stage 12: support matrix | passing content-addressed receipts for Python 3.11 and 3.13 |
| Stage 12: package artifacts | exact sdist and wheel hashes |
| Stage 12: documentation | exact quickstart, tutorial, extension, release-policy, and limitations documents |
| Stage 12: known limitations | nonempty, honest disclosure |
| Stage 12: publisher approval | a distinct human publisher approves the exact policy, version, accepted Standing, and package hashes |

`qualify_public_release(experiment, evidence, evidence_objects=objects)` returns a deterministic
`ReleaseQualificationReport`. Every gate includes its owner, evidence refs,
explanation, and remediation. The report is `qualified` only when every gate
passes. It does not average partial readiness into a score. The CLI evidence
manifest includes an `object_paths` map from every claimed `sha256:` reference
to its local evidence file; each file is rehashed before its reference can pass.

## Version boundaries

- Version 0.17 remains in the experimental contract epoch. Public schema
  compatibility is not promised.
- Public 1.0 requires contract epoch `1` and Semantic Versioning for the public
  import and serialized-contract surfaces named by the compatibility policy.
- Verismill and Mattermill must be consumed as released versions. Repository
  commit pins are permitted during prototyping but fail public qualification.
- A new policy version is required when gates, supported Python versions, or
  required evidence classes change. Existing reports retain their policy ID.

## Current disposition

The software path through Stage 12 exists, but qualification is still blocked
by external human evidence and release decisions. The Winter Observatory
package is waiting for two fresh six-player runs under the frozen protocol;
Verismill and Mattermill remain repository-pinned; contract epoch 1 has not
been declared; and no Publisher Approval exists. These are failed gates, not
missing documentation and not reasons to lower the policy.

See [Known limitations](known-limitations.md) for the present public boundary.
