# Working in narrative-game-library

This repository implements a deterministic narrative-game library above
Verismill. The library generates and compiles games; Verismill measures and
renders their document artifacts; Harbor and Prime can execute frozen Releases
as multi-agent playtest episodes.

## Architectural boundaries

- `contracts`, `kernel`, `compiler`, and runtime reducers are pure.
- Effects belong to Workspace, adapters, experiments, CLI, and output writers.
- Normal document work goes through the public `VerismillArtifactForge`
  adapter. Do not import Mattermill directly from game-owned code.
- Never import Verismill private modules or read its object store or bus.
- The narrative library owns game authority, legal tools, role projections,
  scheduling, replay, and reward semantics. Prime and Harbor own model/runtime
  placement and operational traces; they do not own game rules.
- Same version, component lock, seed, and inputs must produce byte-identical
  deterministic outputs across processes and offline.
- Every accepted requirement has one attributable capability test recorded in
  `docs/acceptance-matrix.md`.
- Independent agents may propose, review, measure, and qualify; every role
  leaves an exact receipt, and builders never certify their own blind work.
- Human feedback is first-order evidence when supplied, but never a mandatory
  transition, standing, or release gate.

## Route the work before editing

| Work | Read first | Primary code |
|---|---|---|
| Generate a game from a brief | `docs/generation.md` | `generation/`, `profiles/` |
| Add or measure realistic documents | `README.md` Artifact Forge sections | `adapters/verismill.py`, `physical/` |
| Change game or runtime contracts | `docs/acceptance-matrix.md` | `contracts/`, `kernel/`, `runtime/` |
| Run or change multi-agent episodes | `docs/harbor-multi-agent-rl-environment.md` | `simulation/` |
| Run Prime locally or hosted | `docs/prime-hosted-multi-agent.md` | `narrative_game_prime/` |
| Package a Harbor task | `docs/harbor-multi-agent-rl-environment.md` | `adapters/harbor.py`, `adapters/harbor_agent.py` |

## Current multi-agent contract

`EpisodeConfig` in `src/narrative_game/simulation/model.py` is the source of
truth for current tool and reward versions. New episodes currently use
`narrative-arena-tools-v2` and `narrative-multi-agent-reward-v3`; older versions
exist only for replay compatibility.

- A model host receives facilitator controls, not truth, private character
  state, hypotheses, correctness markers, or proof paths.
- Each Prime Seat has an isolated persistent context. Its system prompt binds a
  stable character identity and conduct boundary; phase-specific knowledge,
  objectives, evidence, and legal actions come from its authorized observation.
- A Seat must inspect a record before sharing it publicly. A terminal answer may
  cite only records that the submitter inspected or another inspector publicly
  shared. The environment derives a matching proof path privately.
- Never report success from a theory label, confession, provider response, or
  process exit code alone. Success requires a canonical `EpisodeArchive`,
  `verify_episode(...) == ()`, accepted termination, and reward/integrity/outcome
  values supported by the replayed trace.
- For current game-development work, agents are fixed playtest instruments, not
  training targets. Do not introduce policy training unless the user explicitly
  asks for it. When comparing game candidates, keep model, prompt, tools, host
  policy, and sampling locks fixed.

## Prime operating guide

Read `docs/prime-hosted-multi-agent.md` before running Prime.

1. Install the optional runtime with `uv sync --extra prime`.
2. Run a frozen Release locally before using hosted runtimes. The null harness
   still creates one isolated persistent interaction for the host and each Seat.
3. The default Prime endpoint uses `PRIME_API_KEY` or `prime login`. An OpenAI
   endpoint uses `OPENAI_API_KEY` plus the matching client base URL. Never print,
   hardcode, or commit credentials.
4. Use only sampling parameters supported by the chosen model. In particular,
   current Sol endpoints reject explicit `temperature=0`; omit `temperature`
   and retain the chosen reasoning effort.
5. A Prime evaluation may finish its CLI process while role traces contain
   provider or runtime errors. Inspect `traces.jsonl`, locate the host trace,
   decode its `narrative_episode_archive_base64`, and replay-verify the archive
   before claiming a completed episode.
6. Keep local concurrency at one until latency, rate limits, and spend are
   understood. Hosted placement changes execution location, not authority.

## Harbor operating guide

Harbor is an optional execution and trajectory adapter. On Python 3.12+, install
it with `uv sync --extra harbor`. Use `HarborTaskExporter` to package one frozen
Release and `HarborMultiAgentArenaAgent` to run it. Do not modify Harbor or put
game rules in its prompts. New Harbor episodes obey the same `EpisodeConfig`,
authorization, evidence-lineage, replay, and reward contracts as Prime.

## User and experiment state

Authoring state, generated artifacts, credentials, and experiment outputs are
user data, not repository content. In particular, `.narrative-game/`,
`workspaces/`, `artifacts/`, `.prime-test/`, `build/`, and `dist/` are ignored.
Do not add them to commits. Preserve useful local traces long enough for review;
when a result matters to a commit, record the Release ID, episode seed, model and
prompt locks, termination, verifier result, and remaining limitations in the PR
or commit message.

## Before committing

1. Run `uv run pytest -q`.
2. Verify every changed requirement against `docs/acceptance-matrix.md`.
3. If package or release-facing contracts changed, run `uv build` and keep
   `pyproject.toml`, `src/narrative_game/__init__.py`, `uv.lock`, and the README
   Status version aligned.
4. If an emitter or Artifact Forge boundary changed, run its exact artifact
   measurement; ordinary unit tests do not establish realism.
5. If a multi-agent claim changed, verify a canonical archive rather than citing
   dialogue or a model's self-report.
