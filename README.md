# narrative-game-library

Deterministic, agent-authored narrative game building with human-governed
hill-climb lineage.

This repository is the implementation of the approved
[Verismill narrative-game specification](https://github.com/jarredparrett/verismill-lean/issues/3).
It is intentionally a library first: a pure domain Kernel, deterministic Game
Release compiler, authorized Session runtime, physical exporter, persisted
experiment lineage, and renderer-independent experience projections. Optional
applications consume those projections without owning game or authority rules.

## Status

Version `0.15.0` remains in the experimental contract epoch. Stages 0-11 form one
working path: public Artifact Forge boundary, content-addressed Workspace,
pure Kernel and Facilitated Investigation profile, deterministic compiler,
authorized Session runtime, deterministic Physical Export, and a native
agentic hill-climb ledger exercised by a real blind model panel. Stage 9 adds
the reusable Game Blueprint and first-party authoring adapter; Stage 10 makes
live human play the primary acceptance evidence. Stage 11 adds a tutorial-led
maker workspace, host control room, authorized character view, and print
operator projection over the same exact Release and Session identities. Public
schema compatibility is not promised yet, but hashes, receipts, dependency
direction, human authorization, and reproducible outputs are never optional.

The qualification spine added in 0.12 keeps gameplay, accessibility, artifact
realism, human play, and public release as separate evidence classes. A game can
therefore pass development gameplay while remaining honestly unaccepted for
artifact realism and unqualified for public release.

Version 0.13 adds impact-scoped experiment planning. A climb names exactly one
qualification target, routes each finding to its owning loop, derives rebuild
and replay scope from contract changes, and persists a bounded preflight or a
formal measurement plan. Independent blind judges run concurrently, while
their replay receipts and aggregation remain deterministically ordered.

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
  -> Human Review
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

Human feedback is first-order evidence and first-order authority. An agent
Proposal is inert. Only an exact `approved` Review from a human reviewer may
advance a Workspace branch. Model-only evidence can support development or
machine-qualified standing, but never the library's accepted human-play
standing.

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
from execution so a human can choose the panel and approve any proposed child:

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
    reviewer=Authority("owner", "human", "reviewer", "game-maker"),
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

1. A human approves one qualification target and frozen instrument.
2. The route table assigns findings to the smallest owning loop. A broader
   loop requires a persisted reason.
3. `assess_impact` carries content-identical outputs forward and derives only
   the rebuild, remeasurement, and replay obligations caused by changed
   contracts.
4. A human approves one repair tranche. Agents may run its one- or two-unit
   bounded preflight autonomously until it passes, exhausts its budget, or
   repeats the same structural failure three times.
5. A human reviews the completed exact Candidate. Only then does a fresh,
   independent blind panel run the complete formal instrument once.
6. A human selects, retains, parks, or escalates from the formal evidence.

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
    reviewer=my_human_reviewer,
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
two into a synthetic voice. Accepted Standing requires the protocol's minimum
number of passing fresh Runs, the exact comparison, and a human publisher who
did not participate in, facilitate, or observe those Runs. Model disagreement
remains visible but does not overrule observed human play.

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

Version 0.15 freezes the exact human-play boundary for the six-role Winter
Observatory package. Given the selected Candidate 6 Release, it builds the
deep-Dossier child Release and Physical Export, persists a portable Experiment,
and writes consent, roster, pre-game, host-observation, post-game, and group
debrief instruments:

```bash
uv run narrative-game-playtest-prepare ./winter-playtest \
  --parent-release ./candidate-6/game-release.zip
```

Preparation is not a Playtest Run. Six distinct humans and one distinct host
must still consent and complete the live Session. The library refuses to record
a rich Run without all frozen rubric categories, individual pre/post responses,
timestamped facilitator observations for every played Phase, and attributable
response objects. See the [exact prepared lineage](docs/playtests/winter-observatory-six-player-preparation.md).
