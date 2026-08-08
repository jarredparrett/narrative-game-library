# Live difficulty qualification — 2026-08-08

This record closes the first provider-backed checkpoint without promoting a
Failure Class, generating a child, or claiming Standing. The run used the exact
frozen `gpt-5.6-sol` / `gpt-5.6-terra` roster through authenticated local Codex
CLI sessions. All execution state remains in untracked user space; this file
records the immutable identities needed to locate and verify the evidence.

## Command and boundary

```bash
uv run narrative-game-difficulty-live \
  --game fixtures/micro-game/game.json \
  --output "${XDG_DATA_HOME:-$HOME/.local/share}/narrative-game-library/difficulty-live" \
  --fixture both
```

The adapter starts one isolated, ephemeral, read-only Codex session per attempt.
It ignores user config and repository rules, exposes only content-addressed files
in the assignment's Evidence View, and records the provider response ID, resolved
model, token usage, raw output, parsed output, schema diagnostics, and exposure
ledger. It never records private chain-of-thought. The Episode Actors are not
analysis principals, and Attribution A and B remain mutually unexposed until both
outputs freeze.

## Results

| Episode | Current reward | Hidden missing obligation | Analysis | Mechanical eligibility | Provider calls | Reported tokens |
|---|---:|---|---|---|---:|---:|
| missing rescue | 1.0 | no `character-state-updated` event records `quill-safe-exit=true` | complete Incident and complete Semantic Interpretation | eligible | 13 | 2,619,862 |
| failed handoff | 1.0 | no public `camera-log` evidence handoff before submission | complete Incident and complete Semantic Interpretation | eligible | 14 | 3,758,130 |

The missing-rescue Semantic Interpreter distinguished an accepted speech action
from authoritative state: the narration emitted no runtime event, and no session
event recorded the required safe-exit transition. The failed-handoff assembler
corroborated one Incident from three independent sweep outputs, while preserving
the counterevidence that the camera log might not have changed the accepted
outcome. Its Semantic Interpreter found no public share, assessment,
incorporation, or explicit retirement before terminal submission.

Both Episodes produced distinct blinded Attribution outputs. Their causal
emphases remained separate through curation: actor choice, opportunity timing,
seat-scoped visibility, host facilitation, game policy, and runtime gating were
retained as competing or confounded hypotheses rather than collapsed into a
single cause.

The first run revealed two framework defects rather than being treated as a
pass. First, the Game Release core referenced from Episode evidence had not been
inserted into the Claim closure. Second, downstream aggregate grants exposed
only opaque object hashes, so the Incident Assembler could not inspect the
frozen sweeps. Both are now capability-tested. A third inefficiency duplicated
the complete answer-safe Episode across fourteen category objects; the corrected
projection uses fourteen grants over two unique objects. On the subsequent
missing-rescue run, reported usage fell by about 30% relative to the earlier
failed-handoff run, though provider-side usage remains high and is visible debt.

## Immutable evidence identities

Instrument Definition for both lineages:
`sha256:458bafd21d75d12ccdda0c344396c2e64f1f311e6d3c6093e361f39a9e981ef2`.

Missing-rescue lineage:

- Application: `sha256:30e54798ff4c732a96cf70dc03d0daccace0524dc9ca0b4eb847f5ea9def96a8`
- Analysis Lineage object: `sha256:674e0dbd6d5c14bd2916256d04ef9009f4ca825a472e274036831f8e665cf720`
- Diagnostic Claim Manifest: `sha256:947b37ee44e9810a92a3d44f4c0e4f2b79455d83ccb2d08688bb2314aea56ac2`
- Hardening terminal: `sha256:cf1d384f4f72bd8467bc28fad9f326cc89f187f733b861e4103f286bec01085b`
- Hardening Claim Manifest: `sha256:abe77c30f8bd611b3e3313f2eeb88113f98b2188919e12a6ba0a9c1266cd7d19`

Failed-handoff lineage:

- Application: `sha256:472b95cedd13900124cd29a34bda307edc1ebc4bed640f47d92a0db171968f3c`
- Analysis Lineage object: `sha256:3a8c66e4b30599f70942be4606ddcda9aa3f875f1a3dd262c041a61098059c1d`
- Diagnostic Claim Manifest: `sha256:927c704ab68805de4b0ffa244603e80936922b332cc72ca2581f9592681d31c5`

The local evidence used for this record was written beneath
`$HOME/.local/share/narrative-game-library/`; it is deliberately not Git content.
Copy either `.ngc` capsule to another machine and verify it offline:

```bash
uv run python -c \
  'from narrative_game.workspace import Workspace; import sys; print(Workspace.verify_claim_capsule(sys.argv[1]))' \
  /path/to/diagnostic-claim.ngc
```

## D5 terminal

The live evidence supports testable causal hypotheses but contains zero
successful Counterfactual Contrast receipts. The hardening router therefore
stopped at `failure-routing` with status `quarantined` and blocker:
`fewer than two causal Contrasts support the route`.

That result is the required explicit non-accepting terminal. Advancing to class
promotion or child generation would have converted agent hypotheses into causal
fact. The next legal work is to run two independent contrasts under the frozen
Panel and Instrument; only corroborated causal ownership may reopen the
`harden` route.
