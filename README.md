# narrative-game-library

Deterministic narrative game building with agentic, inspectable hill-climb
lineage and optional first-order human evidence.

This repository is the implementation of the approved
[Verismill narrative-game specification](https://github.com/jarredparrett/verismill-lean/issues/3).
It is intentionally a library first: a pure domain Kernel, deterministic Game
Release compiler, authorized Session runtime, physical exporter, persisted
experiment lineage, and renderer-independent experience projections. Optional
applications consume those projections without owning game or authority rules.

## Status

Version `0.24.0` remains in the experimental contract epoch. Stages 0-12 form one
working path: public Artifact Forge boundary, content-addressed Workspace,
pure Kernel and Facilitated Investigation profile, deterministic compiler,
authorized Session runtime, deterministic Physical Export, and a native
agentic hill-climb ledger exercised by real blind model panels. Stage 9 adds
the reusable Game Blueprint and first-party authoring adapter; Stage 10 keeps
agentic standing and optional human-play evidence distinct. Stage 11 adds a tutorial-led
maker workspace, host control room, authorized character view, and print
operator projection over the same exact Release and Session identities. Public
schema compatibility is not promised yet. Stage 12 freezes public-release
qualification as twelve independently reported gates. The current version
remains `not_qualified` until its exact agentic evidence, tagged upstreams, and
stable compatibility epoch exist. Hashes, receipts, role independence,
dependency direction, and reproducible outputs are never optional.

The qualification spine added in 0.12 keeps gameplay, accessibility, artifact
realism, human play, and public release as separate evidence classes. A game can
therefore pass development gameplay while remaining honestly unaccepted for
artifact realism and unqualified for public release.

Version 0.13 adds impact-scoped experiment planning. A climb names exactly one
qualification target, routes each finding to its owning loop, derives rebuild
and replay scope from contract changes, and persists a bounded preflight or a
formal measurement plan. Independent blind judges run concurrently, while
their replay receipts and aggregation remain deterministically ordered.

Version 0.18 makes qualification non-blocking: independent agents may review
Proposals, establish machine-qualified Standing, and attest releases. Human
feedback remains first-order evidence but is not a mandatory gate.

Version 0.19 adds the missing front half: a strict Creative Brief and
Generation Plan can now drive initial Blueprint creation, independent agent
review, compilation, blind measurement, bounded revision, selection, and
durable progress projections. Realism-sensitive documents are supplied as an
accepted Verismill Artifact Suite; each document keeps its own climb and is
never hidden inside a blended game score.

Version 0.20 closes the production-realism loophole exposed by the Sybil's Cave
end-to-end run. A Plan now declares either a `development` or `production`
release target. Development may use authored text and is always reported as
development-only. Production fails closed unless every evidence Resource other
than a character Dossier has a bound Artifact Specification, every exact member
has accepted Verismill standing and embedded accessible text, complete private
Dossiers and host-only instructions exist, and the blind panel visually inspects
the exact print PDFs under independent design and host-usability floors. Accepted
artifact bytes enter the player package unchanged; provenance stays on the
container so post-measurement decoration cannot invalidate the attestation.

Version 0.21 adds a deterministic multi-agent episode boundary for evaluation
and reinforcement learning. A frozen Game Release can now be reset with a
role-isolated model lineup, played through a seeded agent-environment-cycle
scheduler, replayed from hash-chained Session and arena Events, verified under
hard-zero authorization and proof gates, expanded into one token-attributed
trajectory per trainable role, and exported as a Harbor task. Harbor is an
optional downstream harness; it never invokes game generation or Verismill.

Version 0.22 adds a native Prime Verifiers v1 plugin. Prime owns model/runtime
placement and one trace per interaction; the library still owns authorization,
the deterministic AEC scheduler, the hash-chained Episode Archive, replay, and
binary outcome-and-integrity reward. One host interaction and one separately
opened interaction per player Seat provide variable-cast role isolation even
when all Seats share one trainable player policy.

Version 0.23 closes the answer-leakage path found in the first Sybil's Cave
Prime episode. Model-operated hosts now receive a facilitator projection rather
than trusted truth; player observations expose competing theories but never the
proof graph. Records become citable only through an exact inspection or a public
share by their inspecting role, and the environment privately derives a complete
proof path before accepting a resolution. Prime action framing also preserves the
first valid JSON action when a provider appends non-action prose. A real five-agent
Sol episode passed the corrected v3 outcome-and-integrity contract with no model
receiving the answer key.

Version 0.24 starts the agentic-difficulty implementation without claiming the
analyzer exists yet. It freezes the accepted contract sources by content,
packages replay-verified Episode actions, observations, results, messages,
visibility, state transitions, and receipts as addressable evidence, and derives
an answer-safe preflight Discovery view. Two deterministic falsifiers preserve
the important gap in the current reward: an Episode may pass outcome and
integrity while omitting a required rescue transition or evidence handoff.

## Multi-agent RL episodes with Harbor

The environment lives in `narrative_game.simulation` and runs without Harbor:

```python
from narrative_game.simulation import (
    EpisodeConfig, MultiAgentEpisode, PolicyLineup, SeatAssignment,
)

lineup = PolicyLineup(
    seats=(
        SeatAssignment("historian", historian_policy),
        SeatAssignment("reporter", reporter_policy),
        SeatAssignment("conservator", conservator_policy),
        SeatAssignment("appraiser", appraiser_policy),
    ),
    host=deterministic_host_policy,
)
episode = MultiAgentEpisode.reset(
    frozen_release,
    episode_seed=4100,
    lineup=lineup,
    config=EpisodeConfig(max_steps=80),
)
```

Only the arena runner holds the returned role credentials. Each policy receives
its own `observe()` projection and may call only the tools legal for its current
turn. `MultiAgentArenaRunner` accepts provider-specific policy adapters and
returns a portable `EpisodeArchive`. Verify and score it with
`verify_episode(...)` and `evaluate_episode(...)`.

New episodes use `narrative-arena-tools-v2` and
`narrative-multi-agent-reward-v3`: the official reward is
binary and shared. It is `1.0` only when both integrity and outcome pass;
otherwise it is `0.0`. Participation, communication, turn use, intervention
dependence, objective progress, cost, and token attribution remain persisted as
diagnostics and never dilute a successful outcome.

An outcome is proof-bearing only when its cited records were previously opened
by the submitting role or publicly shared by a role that opened them. The arena
derives the matching proof path privately and rejects unsupported submissions;
agents never receive the proof-path graph or its answer-key evidence sets.

For Harbor, use `HarborTaskExporter` to package one exact Release as a task and
`write_trial_artifacts(...)` to write the Episode Archive, Session history,
per-role trajectories, trainer rollouts, release attestation, and full reward
details under `/logs/artifacts/`. On Python 3.12+, install `.[harbor]` only when
running the concrete `HarborMultiAgentArenaAgent`. The agent uses Harbor's
LiteLLM boundary and creates one stateful model session per exact role; the
shared library retains game authority, scheduling, replay, and reward semantics.
Responses API sessions chain by provider response ID, and later turns send only
new dialogue, newly visible evidence, current phase state, and the role's newest
tool result. Seat observations name requestable resource IDs without exposing
their contents. The resolution phase names competing candidate theories, while
proof paths remain hidden and the terminal submission cites acquired resource
IDs.
It also writes Harbor's
native `agent/trajectory.json`: the root ATIF-v1.7 trace preserves global AEC
order, while embedded subagent trajectories preserve exact per-role policy and
credit-assignment boundaries for the Viewer and downstream trace tooling.

Run a real model episode after exporting a task and configuring the provider's
normal credentials (for OpenAI, `OPENAI_API_KEY`):

```bash
uv run --extra harbor harbor run \
  --path /path/to/exported-task \
  --agent narrative_game.adapters.harbor_agent:HarborMultiAgentArenaAgent \
  --model openai/gpt-5.6-sol \
  --agent-kwarg episode_seed=4100 \
  --agent-kwarg reasoning_effort=high \
  --agent-kwarg use_responses_api=true \
  --agent-kwarg trainable=false \
  --job-name sybils-cave-live
```

`trainable=false` still records real prompt/output/cache token counts, cost, safe
decision rationales, actions, and ATIF traces. Set it to `true` only for a
provider that returns exact prompt and completion token IDs; the agent fails
closed if a nominally trainable policy lacks those receipts. Use
`role_models_json` or `host_model_name` agent kwargs to run heterogeneous model
lineups without changing the Release or reward contract.

A bounded live Sybil's Cave episode with five isolated `gpt-5.6-sol` contexts
reached an accepted, correct, proof-bearing resolution in 18 actions. The frozen
v1 verifier passed all six hard gates and scored the historical episode
`0.7625`; provider
usage was 193,252 input tokens, 5,231 output tokens, and `$0.46257575`. This is
one evaluation smoke result, not trainable standing or a 20-episode benchmark.
The immutable v1 archive is not reinterpreted; an equivalent new v2 episode
would receive the binary passing reward `1.0`.

The complete contract, reward definitions, and Sybil's Cave falsifying matrix
are in [Harbor as a multi-agent RL environment](docs/harbor-multi-agent-rl-environment.md).

## Multi-agent RL episodes on Prime

Install the optional adapter and point the taskset at any frozen Game Release:

```bash
uv sync --extra prime
uv run eval narrative_game_prime \
  -m deepseek/deepseek-v4-flash -n 1 -r 1 -c 1 \
  --env.taskset.release-paths /absolute/path/game-release.zip \
  --env.taskset.episode-seeds 4100 \
  --env.host.runtime.type prime \
  --env.player.runtime.type prime \
  --env.host.model deepseek/deepseek-v4-flash \
  --env.player.model deepseek/deepseek-v4-flash \
  --sampling.max-tokens 1600 \
  --sampling.temperature 0
```

Prime may run different models for host and player without changing the Release
or verifier. Set `--env.train-host true` and/or `--env.train-players true` to
declare which shared policy receives the team reward. Every Seat still receives
its own interaction and private transcript. See
[Prime hosted multi-agent execution](docs/prime-hosted-multi-agent.md) for the
execution boundary, outputs, local-debug command, and training sequence.

## Generate a game from a brief

The public generation path starts from intent rather than prepared game JSON:

```python
from narrative_game import (
    ArtifactPlan, CreativeBrief, FacilitatedInvestigationAuthoringAdapter,
    GenerationBudget, GenerationCoordinator, GenerationDrivers,
    GenerationPlan, ModelRoleAssignment, StopPolicy,
)

brief = CreativeBrief(
    title="The Vanished Ledger",
    premise="A private ledger disappears during an estate inventory.",
    experience_targets=("deduction", "negotiation"),
    content_boundaries=("no graphic violence",),
    player_count=4,
    target_minutes=120,
    delivery_format="hybrid",
    seed=6103,
)
plan = GenerationPlan(
    experiment_id="vanished-ledger-1",
    profile_id=FacilitatedInvestigationAuthoringAdapter.profile_id,
    profile_version=FacilitatedInvestigationAuthoringAdapter.profile_version,
    seed=brief.seed,
    role_assignments=(
        ModelRoleAssignment("builder", "creator", "your-provider", "creator-model", "creator-agent", "creator-context"),
        ModelRoleAssignment("reviewer", "reviewer", "your-provider", "review-model", "review-agent", "review-context"),
        ModelRoleAssignment("judge", "judge-a", "your-provider", "judge-model", "judge-agent", "judge-context"),
    ),
    budget=GenerationBudget(max_model_calls=12, max_tokens=60_000, max_rounds=3),
    stop_policy=StopPolicy(max_consecutive_invalid_outputs=2),
    artifact_plan=ArtifactPlan((), ()),
    release_target="development",
)

coordinator = GenerationCoordinator.create(
    "/path/to/user-data/vanished-ledger-1",
    plan=plan,
    brief=brief,
    instrument=your_frozen_instrument,
    component_lock=FacilitatedInvestigationAuthoringAdapter.component_lock,
)
coordinator.run(
    FacilitatedInvestigationAuthoringAdapter(),
    drivers=GenerationDrivers({
        "creator": creator_driver,
        "reviewer": reviewer_driver,
        "judge-a": judge_driver,
    }),
    translator=your_answer_safe_requirement_translator,
    scratch_root="/path/to/user-data/vanished-ledger-1/scratch",
)
```

Drivers are provider-neutral and must return the resolved model, actual agent
identity, isolated context identity, and token usage. The coordinator rejects a
receipt that differs from its frozen assignment, and a Plan cannot reuse an
agent or context across builder, reviewer, or judge roles. Reopen after
interruption with `GenerationCoordinator.open(...)`; model
calls, proposals, reviews, artifact suites, measurements, and selections are
idempotent. Humans can monitor `generation-status.md` or
`generation-status.json` without treating either projection as authoritative
state. Read `release_qualification`, not `phase`, before describing an output:
only `production_candidate_ready` means the production contract was satisfied.

For realistic documents, bind each `ArtifactSpecification` to the Blueprint's
referenced world facts with `bind_artifact_specification`, put those exact bound
values in both the Plan and generated Blueprint, and supply a
`VerismillArtifactSuiteImporter`. The importer accepts only a pre-existing,
attested, release-ready suite whose every member has accepted Verismill
standing; it does not forge or remeasure artifacts. Artifact display claims
trace to canonical fact references and request pins, and any relevant world
change invalidates the binding. Authored text remains a design source, not the
shipped PDF.

For a shareable package set `release_target="production"`. The facilitated
investigation adapter derives the mandatory Artifact coverage from the complete
evidence graph; an empty or partial `ArtifactPlan` is rejected before generation.
This target also requires a complete `CharacterProgram`, a host-only guide,
accessible artifact renditions, and a production Instrument with explicit
`production_design_quality` and `host_and_dossier_usability` floors. The blind
protocol must set `inspect_print_renditions=True` and use at least three judges.

See [Agentic game generation](docs/generation.md) for the complete lifecycle,
model replacement rules, artifact boundary, monitoring projection, and
evidence limits.

## Repository boundary

The dependency direction is one-way:

```text
narrative-game-library -> verismill -> mattermill
```

The game library requests measured documents through one public Verismill
Artifact Forge adapter. It does not import Mattermill directly in the normal
path and never reads Verismill's object store or bus.

For the prototype, the upstream dependency is pinned to the exact commit that
introduces the public artifact-result contract. This pin is replaced by tagged
Verismill and Mattermill releases before the first PyPI publication.

## Stage 0 quickstart

```bash
uv sync --all-extras --dev
uv run python -m narrative_game.stage0_fixture /tmp/narrative-game-stage0
uv run pytest -q
```

The fixture creates a Verismill experiment through its public facade, emits a
seeded 1997 New Jersey deed, materializes its bytes and Artifact Attestation,
and prints the content hashes and verification result. Repeating it in another
directory produces byte-identical artifact and manifest hashes.

## Complete worked example

`The Ashwood Ledger` is the first end-to-end release fixture. It is a fully
written two-player estate-archive mystery with asymmetric dossiers, phased
evidence, two independent proof paths, host recovery, a joint resolution,
accessible evidence, and a Verismill-forged 1997 Madison deed.

```bash
uv sync --all-extras --dev
uv run narrative-game-example /tmp/ashwood-ledger
```

The command writes only to the new user-owned directory. Its `output/` folder
contains:

- `game-release.zip` - the byte-identical digital Release;
- `physical-package.zip` - print assets, containers, labels, preflight, claim
  lineage, and an assembly guide;
- `session-history.json` - a complete replayable, correctly resolved Session;
- `workspace.ngw`, `workspace-lineage.md`, and `hill-climb-lineage.md` -
  portable experiment state and human-readable proposal, authorization,
  measurement, release, export, and replay lineage;
- `stage5-result.json` - exact identities and verification results.

Run the same command with another empty directory under the same resolved
toolchain and the Candidate, Release, artifact, physical package, Session, and
Workspace lineage hashes match. No network is used after the pinned
dependencies are installed. Cross-environment replay uses the exact artifact
bytes persisted in the Candidate and Release; regenerating an upstream PDF on
a different operating system may produce a different Candidate.

The printable deed is visibly marked as fictional game material. The exact,
unmodified Verismill artifact and its Artifact Attestation remain inside the
embedded Game Release. The deed's current Verismill measurement standing is
reported honestly as `development_only`; the physical package claims only
production-ready layout and assembly, not independently validated legal
realism.

### Winter Observatory human handoff

The exact Winter Observatory Candidate 6 materials are available as a focused,
human-shareable [host handoff](examples/winter-observatory-candidate-6/README.md).
It contains 19 evidence PDFs, host instructions, six private player dossiers,
shared play aids, a combined review PDF, a contact sheet, and one downloadable
ZIP—without experiment internals or model traces.

## Native hill climbing

Stage 6 makes iteration a library contract instead of an informal sequence of
agent messages. A person triggers work; agents may build, fix, harvest, or
judge; and the Workspace records the exact authority, task, model invocation,
input exposure, proposal, evaluation, and standing.

```text
Frozen Instrument + baseline Candidate
  -> blind Task + Exposure Ledger + Model Receipt
  -> Evaluation + quoted Findings
  -> answer-safe Requirements
  -> builder Task + Proposal
  -> independent Agent or Human Review
  -> authorized child Draft + Candidate
  -> fresh blind Task under the same Instrument
  -> honest Standing Attestation
```

Models are replaceable occupants of typed Tasks. Each invocation records its
provider, requested and resolved model, prompt/context/tool hashes, input
hashes, raw output, parsed output, and seed. Changing a model creates new
evidence; it does not change the workflow or silently overwrite earlier state.
Builders and fixers are excluded from judging their own child, and a blind
judge's Exposure Ledger makes contamination inspectable.

Human feedback is first-order evidence when available. An agent Proposal is
inert until an exact `approved` Review covers every Requirement. An Agent Review
must carry an independent Model Receipt and cannot share a principal with the
builder; Human Review remains an optional equivalent. Agentic and human-play
Standing are always reported separately.

Run the complete offline control-plane example:

```bash
uv sync --all-extras --dev
uv run narrative-game-climb-example /tmp/ashwood-climb
```

It persists a baseline measurement, quoted tell, translated Requirement,
model-authored Proposal, human-approved Transition, child Candidate, and fresh
blind remeasurement over `The Ashwood Ledger`. The output includes a portable
`ashwood-stage6.ngw` archive, `stage6-result.json`, and a concise lineage
report. The fixture proves the loop and a 66.9 -> 82.8 score movement without
hard-gate regression; it deliberately retains `development_only` standing
because recorded offline judge fixtures are not fresh human playtests.

### Real measured-climb proof

Stage 7 replaces the illustrative scores with live, replaceable model drivers
and complete anonymous trial packages. Preparation is deliberately separate
from execution so panel occupancy and any proposed child remain inspectable:

```bash
uv run narrative-game-climb-prepare /path/to/user-data/ashwood-stage7
uv run narrative-game-climb-measure /path/to/user-data/ashwood-stage7 \
  --provider YOUR_PROVIDER --model YOUR_MODEL -- YOUR_JSON_MODEL_COMMAND
```

The first persisted experiment ran a three-member fresh blind panel under
Instrument 1.1. Its final child scored `72.4`, failed the frozen `75` threshold,
and was not selected. All package hard gates passed. The ledger therefore
retained the baseline and claimed no quality or human-play standing. That is a
successful proof of the process—not an assertion that the worked game is
finished. Stage 8 generalizes the experiment API before more fixture-specific
quality work.

## Reusable Experiment API

Stage 8 separates the evidence workflow from any one game. An `Experiment`
owns its persisted plan, frozen Instrument, authority graph, model and human
receipts, Reviews, Transitions, Selection Decisions, and portable archive. A
versioned `GameProfileAdapter` owns how its domain data becomes a complete
Candidate package and how builder output becomes a proposed revision.

```python
from narrative_game import Experiment
from narrative_game.climb import Authority

experiment = Experiment.create(
    "/path/to/user-data/my-experiment",
    experiment_id="my-game-v1",
    profile_id="my-domain.facilitated-investigation",
    profile_version="1.0.0",
    instrument=my_frozen_instrument,
    initial_data=my_game_data,
    component_lock=my_component_lock,
    reviewer=Authority("review-agent", "agent", "reviewer", "independent-reviewer"),
)

package, binding = experiment.build_and_bind(
    my_profile_adapter,
    scratch_root="/path/to/user-data/build-scratch",
    idempotency_key="bind-baseline",
)
assert experiment.verify()["ok"]
```

Model and human judges occupy the same typed blind-measurement workflow, but
leave distinct `ModelReceipt` and `HumanReceipt` evidence. Aggregation strategy
and adapter identity are frozen in the Experiment contract, so changing either
is explicit rather than an ambient behavior change. Profile adapters may be
added for other game genres—or domains such as insurance and accounting—without
placing their authoring rules in the experiment core.

## Portable qualification and current standing

`ExperimentSpine` records each selected rung in a fourth hash-chained Workspace
journal. It stores the exact Release, Physical Export, artifact collection,
scoped human approvals, game evidence, accessibility contracts, and opaque
content-addressed references to external Verismill Experiments. Every selection
automatically exports a relocatable `.ngw` and replaces two derived projections:
`current-standing.json` for tools and `current-standing.md` for people.

The projections are never edited as state. Reopening the Workspace rebuilds
them from the journal, and verification detects stale projections, corrupt or
missing objects, broken parentage, incomplete proof paths, unequal accessible
evidence, and approval scope mismatches.

```python
from narrative_game import ExperimentSpine, Workspace

workspace = Workspace.open("/path/to/user-data/my-game")
spine = ExperimentSpine(workspace)
assert spine.verify()["ok"]
standing = spine.derive_projection()
print(standing["standings"]["artifact_realism"]["status"])
```

The first historical migration is the exact Winter Observatory Candidate 6
baseline. It uses only Verismill's public `Experiment` facade and does not read
its private bus or object store:

```python
from narrative_game.experiment import migrate_winter_observatory_candidate_6

migrate_winter_observatory_candidate_6(
    "/path/to/winter-observatory",
    workspace_root="/path/to/user-data/experiments/winter-observatory-candidate-6",
    archive_path="/path/to/user-data/experiments/winter-observatory-candidate-6.ngw",
)
```

That migration creates no candidate and no new standing. It preserves the
recorded result: coherent build passed, development gameplay passed, critical
accessibility parity passed, artifact realism `0/19` accepted, human play
unmeasured, and public release unclaimed. See the
[full retrospective](docs/retrospectives/winter-observatory-hill-climb.md).

## Efficient climbs: diagnose narrowly, measure formally once

`EfficiencyPlan` separates cheap diagnosis from evidence that may change
standing:

1. Freeze one qualification target and Instrument before any scoring.
2. The route table assigns findings to the smallest owning loop. A broader
   loop requires a persisted reason.
3. `assess_impact` carries content-identical outputs forward and derives only
   the rebuild, remeasurement, and replay obligations caused by changed
   contracts.
4. An independent receipted Review authorizes one repair tranche. Its bounded
   preflight runs until pass, budget exhaustion, or repeated structural failure.
5. Fresh independent blind judges run the complete formal Instrument once.
6. Frozen selection rules select, retain, park, or escalate from that evidence.

Preflight scores are diagnostic and cannot confer standing. Instrument changes
start a new standing lineage; fixers cannot judge their own child. The
Workspace stores plans, approvals, observations, budgets, stop decisions, and
object hashes in its operational journal. `active-experiment.json` and the
`active_experiment` field in `current-standing.json` are replaceable projections
that answer: what are we improving, why this loop, what was invalidated, what
budget remains, and what transition is authorized next?

```python
from narrative_game.contracts import canonical_json
from narrative_game.experiment import EfficiencyController
from narrative_game.stage11_efficiency_fixture import (
    winter_observatory_efficiency_proof,
)

plan, comparison = winter_observatory_efficiency_proof()
approval_bytes = canonical_json({
    "schema_version": "0.13",
    "plan_id": plan.plan_id,
    "boundary": "target_and_instrument",
    "decision": "approved",
    "scope": {
        "primary_target": plan.primary_target,
        "instrument_id": plan.instrument_id,
    },
})
controller = EfficiencyController(experiment.workspace)
controller.record_plan(plan, target_authorization_bytes=approval_bytes)
```

The complete worked policy is
[`winter_observatory_efficiency_proof`](src/narrative_game/stage11_efficiency_fixture.py).
It routes the shared historical handwriting tell first to
`night_observing_log` as a representative renderer benchmark: at most three
diagnostic builds and six diagnostic calls, followed by one three-judge formal
panel if the preflight passes. The other eighteen artifact results carry
forward only when their content hashes are identical. This proves reduced work
and preserved authority—not quality, which remains unclaimed until formal
measurement.

## Game authoring

Stage 9 makes the editable game source explicit. A `GameBlueprint` wraps the
canonical `GameDefinition` with rich-text Materials, exact visible claim
traces, a deterministic seed, and one `ArcBeat` per Phase. Resource hashes are
derived from source text; Arc Beats are checked against canonical Reveals; and
the existing validator remains the only owner of world, character, evidence,
proof, access, and resolution consistency.

```python
from narrative_game import (
    Experiment,
    FacilitatedInvestigationAuthoringAdapter,
    GameBlueprint,
    validate_blueprint,
)
from narrative_game.examples import vanished_ledger_blueprint

blueprint = vanished_ledger_blueprint()  # Or GameBlueprint.from_mapping(your_data)
assert validate_blueprint(blueprint) == ()

adapter = FacilitatedInvestigationAuthoringAdapter()
experiment = Experiment.create(
    "/path/to/user-data/my-game",
    experiment_id="my-game-v1",
    profile_id=adapter.profile_id,
    profile_version=adapter.profile_version,
    instrument=my_frozen_instrument,
    initial_data=blueprint.to_mapping(),
    component_lock=adapter.component_lock,
    reviewer=my_independent_review_agent,
)
package, binding = experiment.build_and_bind(
    adapter,
    scratch_root="/path/to/user-data/scratch",
    idempotency_key="bind-baseline",
)
```

Builders return typed `AuthoringOperation` values: replace direction, world,
cast, deduction graph, arc, or displayed claims; upsert a rich-text Material;
or remove one. Every operation names the Requirements it addresses and carries
a rationale. The adapter applies the operations, revalidates the complete
Blueprint, builds a full preview package, and stops at an inert Proposal. The
same human Review and child remeasurement loop from Stage 8 then governs the
transition. Iterative authoring is therefore the default without putting model
behavior inside the deterministic compiler.

## Human play evidence

Stage 10 turns a playtest into persisted experiment evidence, not an informal
note after the climb. A `PlaytestProtocol` is frozen before recruitment and
binds one exact Candidate, Game Release, Physical Export, Instrument, consent
version, cohort minimum, observation categories, and model-comparison rule.

```python
from narrative_game import PlaytestProgram

playtests = PlaytestProgram(experiment)
protocol = playtests.freeze_protocol(
    binding_id=binding.binding_id,
    name="two-seat facilitated play",
    version="1.0.0",
    consent_version="playtest-consent-v1",
)

run = playtests.record_run(
    protocol_id=protocol.protocol_id,
    run_key="cohort-01",
    session_history=completed_live_session,
    production_receipt=exact_release_and_physical_export_receipt,
    participants=participant_authorities,
    facilitator=facilitator_authority,
    observers=observer_authorities,
    consent_responses=versioned_consent_responses,
    observations=phase_scoped_quoted_observations,
    scores=instrument_scores,
    idempotency_key="cohort-01",
)
```

A Run counts only when it is a completed live Session over that exact package,
with a fresh participant cohort and exact consent and observation receipts.
Simulations and Blind Trial reviews are useful evidence, but they are not
human play. Quoted Run Findings can be translated into answer-safe
Requirements and passed to `Experiment.propose_revision_from_requirements`, so
human feedback enters the same Proposal, Review, child-build, and fresh
measurement loop as other tells.

Blind model scores and human-play medians remain separate. An
`EvidenceComparison` records `aligned` or `divergent`; it never averages the
two into a synthetic voice. Human-play Standing requires the protocol's minimum
number of passing fresh Runs, the exact comparison, and an independent human
reviewer who did not participate in, facilitate, or observe those Runs. It is
additional evidence, not a public-release prerequisite. Model disagreement
remains visible and does not overrule observed human play.

## Tutorial-led product experience

Stage 11 keeps interface policy outside the deterministic domain model. The
library projects four deliberately different surfaces from the same exact
objects:

- the maker sees editable intent, package custody, hill-climb lineage, and a
  guided explanation of the game components;
- the host sees a dense live Session control room and only authorized commands;
- each player sees that Actor Binding's character, evidence, notes, events, and
  available actions without trusted truth or another Seat's private material;
- the print operator sees the immutable Physical Export plan, files, and
  preflight evidence.

The tutorial walks one real game through Blueprint, world and truth, cast and
Seats, Evidence and Materials, Arc and Phases, Candidate and Release, delivery,
Session authority, measurement, Proposal and Review, and supported Standing.
It is a deterministic projection contract rather than UI-owned explanatory
state.

```bash
uv run narrative-game-experience /tmp/narrative-game-experience
```

The command writes standalone offline HTML and JSON projections, the tutorial,
the exact Game Release and Physical Export archives, a replayable Session
History, and a content-hashed summary. Controls emit typed intents; they cannot
mutate a game or Session unless the owning Experiment or Session authority
accepts them. Repeating the command in another empty directory produces
byte-identical output.

## State ownership

Evolving authoring and experiment state is user data, not repository content.
Later stages place Workspaces in the platform user-data directory by default
and support explicit overrides, portable archives, and offline verification.
Only minimal synthetic fixtures and capability tests are committed here.

## Development

```bash
uv sync --all-extras --dev
uv run pytest -q
```

See [the acceptance matrix](docs/acceptance-matrix.md) for the evidence required
at each implementation gate.

### Workspace lineage

```python
from narrative_game import Workspace

workspace = Workspace.create("/path/to/user-data/game", workspace_id="my-game")
head = workspace.commit_draft(
    branch="main",
    expected_head=None,
    data={"title": "My game"},
    reason="create the first Draft Revision",
    actor="human:maker",
    component_lock={"components": []},
    operation_receipt={"operation": "draft.create", "inputs": {}, "outputs": {}},
    idempotency_key="draft-main-1",
)
assert workspace.verify()["ok"]
```

Canonical history lives in immutable objects and independently verifiable
lineage, operational, and climb journals. Branch Heads and `workspace.json` are
projections that can be rebuilt after interruption. Workspace Archives are
deterministic and path-independent and carry exact model outputs and human
Review receipts with the game.

### Author and validate a game

The canonical authoring form is explicit JSON. It contains no runtime state,
artifact bytes, model configuration, or reviewer standing.

```python
from pathlib import Path

from narrative_game import parse_game_definition, validate_facilitated_investigation

game = parse_game_definition(Path("fixtures/micro-game/game.json").read_bytes())
findings = validate_facilitated_investigation(game)
assert findings == ()
print(game.content_hash)
```

Findings are stable records with a requirement code, severity, precise locus,
quoted defective value, and explanation. The committed Micro Fixture has two
Seats and two evidence routes. Its single-delta Defect Deck proves the validator
rejects contradictory truth, missing references, access leakage, inaccessible
evidence, fragile or premature proof, inactive Seats, and missing recovery.

See [the domain context](CONTEXT.md) for ownership vocabulary and the
[research evidence register](docs/research-evidence-register.md) for the source
provenance behind Stage 2 requirements.

### Freeze and compile a Release

Candidate freeze accepts only a valid Game Definition, exact material bytes and
receipts, a deterministic seed, compilation options, and the resolved Component
Lock. Compilation is pure and produces either one self-contained Release or
structured blockers—never partial Release bytes.

```python
from pathlib import Path

from narrative_game.compiler import compile_candidate
from narrative_game.stage3_fixture import build_micro_candidate

candidate = build_micro_candidate(Path("fixtures/micro-game/game.json").read_bytes())
result = compile_candidate(candidate)
assert result.release is not None
assert result.release.bundle_hash.startswith("sha256:")
```

The deterministic bundle contains its trusted canonical game, host and
simulation views, an authorized projection for each Seat, exact materials,
reproduction receipts, artifact attestations, Component Lock, compilation
report, and Release manifest. Seat projections never contain trusted truth,
proof paths, answer keys, future information, or material bytes.

### Run and replay a Session

One Session Authority accepts an untrusted Command only after checking its
trusted Actor Binding or host Viewer context, Release identity, expected
revision, availability, and transition legality. Acceptance appends a hashed
Event; rejection appends only an operational Command Receipt.

```python
from pathlib import Path

from narrative_game.runtime import replay, seat_snapshot
from narrative_game.stage4_fixture import run_micro_session

release, history, authorization = run_micro_session(
    Path("fixtures/micro-game/game.json").read_bytes()
)
state = replay(release, history)
assert state["status"] == "resolved"
avery = seat_snapshot(release, history, authorization["avery"])
assert avery["revision"] == history.sequence
```

Session History is canonical portable data. Reloading the same Release and
History yields identical state and Seat Snapshots. Live Sessions allow human
Actors; model Actors use isolated simulation forks over a verified Event
prefix. Actor replacement, physical disclosure grades, hints, planned recovery,
and exceptional host actions remain explicit Events.

### Build deep, phase-aware characters

Version 0.14 adds canonical deep Dossiers and phase-aware Character Programs.
Every supported Seat can receive a layered 3–5 page private Dossier with a
two-minute Quick Start, relationships, knowledge boundaries, reveal windows,
phase choices, fallbacks, and ending choices. Human and model Actors use the
same Session Authority; human direction and evolving Character State persist
without changing world truth.

To inspect the complete six-role Winter Observatory example:

```bash
uv run narrative-game-character-example ./winter-character-example
open ./winter-character-example/dossiers/eleanor-vale.pdf
```

The command writes six deterministic Markdown/PDF pairs, the exact canonical
game with its Character Program, and a hash-bearing summary. The validator
blocks cross-role leakage, host-only solution knowledge, unreachable private
truths, future-phase moves, and phase states with no fallback.

### Prepare first-order six-player evidence

Version 0.18 carries forward the exact human-play boundary for the six-role Winter
Observatory package. Given the selected Candidate 6 Release, it builds the
deep-Dossier child Release and Physical Export, persists a portable Experiment,
and writes consent, roster, pre-game, host-observation, post-game, and group
debrief instruments:

```bash
uv run narrative-game-playtest-prepare ./winter-playtest \
  --parent-release ./candidate-6/game-release.zip
```

Preparation is not a Playtest Run. First run an independent blind model panel
under the same Instrument; its exact Evaluation is the comparison baseline,
not a substitute for play:

```bash
uv run narrative-game-playtest-model-baseline \
  ./winter-playtest/experiment \
  ./winter-playtest/model-panel.json
```

Then two distinct six-person cohorts and their hosts must consent and complete
separate live Sessions. The library refuses to record
a rich Run without all frozen rubric categories, individual pre/post responses,
timestamped facilitator observations for every played Phase, and attributable
response objects. See the [exact prepared lineage](docs/playtests/winter-observatory-six-player-preparation.md).

Completed forms enter that same Experiment through an offline operator bundle,
not a custom Python session:

```bash
uv run narrative-game-playtest-session \
  ./winter-playtest/packages/game-release.zip \
  ./winter-playtest/session-plan.json \
  --output ./winter-playtest/completed/session-history.json

uv run narrative-game-playtest-record \
  ./winter-playtest/experiment \
  ./winter-playtest/recording-manifest.json
```

The preparation includes host-transcript, recording-manifest, and completed-file
templates. The session command verifies the Release and applies every recorded
host/Seat command in memory, writing only a fully resolved live history. The recorder
then loads that Session, production receipt, consent responses,
observations, and scores; preflights the complete future ledger without writes;
then persists the Run idempotently. A rejected submission leaves journals and
the object store unchanged.

After both fresh Runs, a human who did not play, host, or observe reviews their
raw evidence and the model comparison. Only an explicit approval may issue
accepted Standing:

```bash
uv run narrative-game-playtest-review \
  ./winter-playtest/experiment \
  ./winter-playtest/standing-review.json
```

The preparation includes model-panel and standing-review manifests. Every
panel member selects its own provider, requested model, and JSON-command driver,
so comparison evidence is model-portable without hard-coding a provider.
For Codex users, the bundled `narrative-game-codex-judge-driver` is a conforming
adapter: set the member command to that executable and provide an explicit
Codex model. It extracts only the anonymous trial into an ephemeral read-only
workspace and records the CLI event trace as a replay receipt. Other providers
remain ordinary JSON-command adapters. If a provider returns an invalid quote
or schema, its Task and receipt remain trace evidence but no Evaluation is
issued; retry under a fresh Task and Authority rather than rewriting history.

## Public-release qualification

Stage 12 evaluates one exact library version and reference Experiment against a
content-addressed policy. It reports all gates and never upgrades game Standing:

```bash
uv run narrative-game-release-qualify \
  ./winter-playtest/experiment \
  ./release-evidence.json \
  --output ./release-qualification.json \
  --allow-not-qualified
```

Omit `--allow-not-qualified` in release CI so any failed gate returns a nonzero
exit status. The exact policy, evidence shape, current limitations, and path to
qualification are documented in
[Public-release qualification](docs/public-release-qualification.md). The first
profile-extension pattern is in [Extending the library](docs/extending.md).
