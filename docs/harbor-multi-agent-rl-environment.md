# Harbor as a multi-agent RL environment

## Implementation status

Version 0.21 implements the environment contract in this note:

- `narrative_game.simulation.MultiAgentEpisode` composes the existing Session
  Authority with seeded AEC scheduling, role credentials, conversation tools,
  observations, and immutable arena Events;
- `MultiAgentArenaRunner` and `AsyncMultiAgentArenaRunner` own one isolated
  provider adapter per actor and record provider usage plus exact token receipts
  when the provider supplies them;
- `verify_episode` replays the Session chain, validates the arena chain,
  re-derives every stored role projection at its historical Session revision,
  and verifies inspected evidence bytes against the frozen Release;
- `evaluate_episode` emits six hard gates, a team reward vector, per-role
  dimensions, and a hard-zero aggregate on any failed gate;
- `expand_trainable_rollouts` expands one Harbor trial into one rollout per
  trainable policy context;
- `HarborTaskExporter` and `write_trial_artifacts` implement current Harbor task,
  verifier, `/logs/artifacts/`, `reward.json`, and trajectory conventions;
- the concrete `HarborMultiAgentArenaAgent` uses Harbor's LiteLLM boundary to
  create one stateful provider session per role, supports homogeneous or
role-specific model lineups, and populates Harbor's multiple `rollout_details`
entries when exact trainable receipts exist; it writes a native
`agent/trajectory.json` with a chronological ATIF-v1.7 root and embedded,
role-local subagent trajectories;
- each Responses API policy chains its own `previous_response_id`; subsequent
  calls receive only the new role-visible delta instead of duplicated history;
- seat projections expose exact, access-bounded requestable resource IDs and,
  only in the resolution phase, candidate hypotheses plus proof-path evidence
  sets. They never expose the correct-hypothesis marker or bind a proof path to
  its accepted hypothesis;
- `plan_role_rotated_episodes` deterministically freezes the 20-episode,
  two-model-family role-rotation matrix used by the falsifying experiment.

The capability fixture proves the contract with the repository's compiled
Micro Game. The real task exporter was also exercised against accepted Sybil's
Cave production Candidate v5: Release
`sha256:06dc757ec5aff27b29c1a76a0d2386ce5a47f2365738046d98adf002978fc0a3`,
bundle
`sha256:2a0682fda6ae569e72ed98e99d7efe2dde2e2241ef8f877785bcf38421aa79f5`.
Harbor 0.20 parsed the resulting four-seat task successfully. That task remains
in untracked user experiment state, consistent with the repository boundary.
The exact Release also completed a deterministic five-context smoke episode in
12 AEC actions with an accepted proof-bearing resolution, verified trace, five
separate trajectories, and reward `0.9625` (Episode
`sha256:e59396b7042c1533966bc08618a4f9ead49fba683f431efc5d97b1334964fa69`).
One bounded live evaluation was completed with five isolated
`openai/gpt-5.6-sol` contexts and high reasoning effort. The episode terminated
after 18 actions with the correct `crane-forgery-confinement` hypothesis and
licensed `history-material-access` proof path. The frozen task verifier passed
all six hard gates and scored `0.7625`; provider usage was 193,252 input tokens,
5,231 output tokens, and `$0.46257575`. The preceding full-observation run used
398,389 input tokens, so stateful deltas reduced input use by about 51 percent.
This is a smoke result, not statistical standing. The planned 20 live,
role-rotated episodes remain a separate evaluation run.

The concrete agent defaults to `openai/gpt-5.6-sol`, the Responses API, high
reasoning effort, and non-trainable evaluation mode. Every model response must
produce a structured `reasoning_summary`, tool name, and arguments. Only that
concise, user-visible rationale is persisted; provider-private chain-of-thought
is neither requested nor copied into the Episode Archive. Provider-reported
usage is recorded even when exact token IDs are unavailable. A policy marked
trainable fails closed unless the provider returns prompt and completion token
IDs, preventing ordinary usage totals from being mislabeled as RL receipts.
OpenAI supplied usage but not exact token-ID receipts in the live smoke run, so
the episode correctly remained non-trainable and its token-attribution reward
dimension remained zero.

## Decision

Use Harbor downstream of generation as the rollout, scaling, reward, and
trajectory harness for frozen game releases. Harbor does not invoke Verismill
or narrative generation. A game release is an immutable environment instance;
one Harbor trial is one complete multi-agent play episode.

The narrative library owns game semantics, authorization, state transitions,
and replay. Harbor owns task packaging, sandbox lifecycle, parallel trials,
artifact collection, reward transport, and integration with RL trainers.

## Why Harbor fits

Harbor defines a trial as an agent attempt on a task and describes it as a
rollout that produces reward. Jobs expand tasks, models, and agents into many
parallel trials. This gives us the right outer structure for repeated play
episodes and held-out evaluation sets. See Harbor's [core
concepts](https://www.harborframework.com/docs/core-concepts) and [RL
workflow](https://harborframework.com/docs/training-workflows/rl).

Harbor's RL guidance explicitly centers token and reward capture and recommends
custom rollout interfaces around `TrialConfig` or `JobConfig`. Its reference
example reads reward and token metadata from each trial result. The official
[Terminus-2 RL documentation](https://harborframework.com/docs/agents/terminus-2)
also describes turn-level prompt tokens, completion tokens, log probabilities,
and ATIF trajectories.

Harbor supports custom agents without modifying Harbor itself, environment
MCP servers, container sidecars, separate verifiers, multi-valued rewards,
post-trial artifact collection, a trajectory viewer, and cloud-parallel jobs:

- [Custom agents](https://www.harborframework.com/docs/agents)
- [MCP task configuration](https://www.harborframework.com/docs/tutorials/mcp-server-task)
- [Task and verifier configuration](https://www.harborframework.com/docs/tasks)
- [Reward Kit and multi-reward output](https://www.harborframework.com/docs/rewardkit)
- [Artifact collection](https://www.harborframework.com/docs/run-jobs/results-and-artifacts)
- [Job viewer](https://www.harborframework.com/docs/run-jobs/run-evals)

## Important limitation

Harbor's documented trial is single-agent-shaped: one configured agent runs
against one task environment. A Harbor job may sweep multiple agent/model
configurations, but the public task contract does not define several isolated
agent policies acting within the same trial.

Therefore the game needs a custom Harbor `BaseAgent` implementation that is a
**multi-agent arena runner**. It owns several model sessions and emits one
team-level Harbor result plus per-seat rollout details. This is an adapter, not
a change to Harbor and not a reason to put game rules in Harbor.

## Episode contract

### Reset

`reset(release_id, episode_seed, lineup)` must:

1. load one content-addressed, frozen game release read-only;
2. create a new hash-chained session;
3. bind one policy identity and private context to every seat;
4. optionally bind a host policy;
5. return only each actor's authorized opening observation;
6. record the release, rules, scheduler, tool-schema, reward, model, and seed
   versions used for the episode.

### State

The trusted environment owns:

- canonical truth and resolution requirements;
- phase and turn position;
- evidence availability and disclosure history;
- public dialogue and private messages;
- per-seat beliefs, objectives, and private notes;
- host requests and interventions;
- immutable session events and tool receipts.

Policies never receive the raw state. They receive projections.

### Observation

For seat `i`, observation `o[i,t]` contains:

- the seat's current private dossier projection;
- its objectives, beliefs, and permitted reveal paths;
- evidence currently authorized for that seat;
- public dialogue and private messages addressed to it;
- current phase, remaining action budget, and legal actions;
- its own prior actions and updated character state.

The host receives the host projection and recovery queues. A post-episode
verifier may receive canonical truth. No character policy may do so.

### Actions and tools

Player policies should receive a stable, role-bound tool surface:

- `observe()`
- `inspect_evidence(resource_id)`
- `say(text)`
- `message(seat_id, text)` when the game permits private communication
- `request_evidence(resource_id)`
- `request_hint(text)`
- `share_claim(proposition_id, stance, explanation)`
- `update_character_state(...)`
- `submit_resolution(hypothesis_id, proof_path_id, explanation)`

The host policy receives:

- `open_session()`
- `advance_phase(phase_id)`
- `disclose_resource(resource_id, audiences)`
- `deliver_intervention(intervention_id, audiences, reason)`
- `broadcast(text)`
- `end_session(reason)`

The current narrative runtime already has deterministic projections and most
structured session actions. It lacks a first-class conversational event/tool
surface suitable for agent play. That should be added to the environment
kernel, not improvised inside a Harbor prompt.

Tool authorization must be enforced with seat-bound credentials at the runtime
boundary. Harbor can register task-level MCP servers, but task-level MCP
configuration is not per-subagent access control. A role-aware MCP gateway or
separate per-seat endpoints must reject cross-seat reads even if a policy asks
for them.

### Transition and scheduling

Use an event-sourced, seeded scheduler. True concurrent writes would make
episodes difficult to reproduce and assign credit to. A practical first
version is agent-environment-cycle scheduling:

1. host opens or advances the phase;
2. each active seat receives a fresh observation;
3. each seat may speak and make a bounded number of structured actions;
4. requests and disclosures are resolved;
5. the environment records the ordered batch and advances;
6. the final phase accepts a proof-bearing resolution.

Seat order may rotate by episode seed, but the realized order must be persisted.

### Termination

An episode ends on one of:

- accepted resolution with a licensed proof path;
- explicit incorrect final resolution;
- phase, turn, token, or wall-clock budget exhaustion;
- unrecoverable authorization or state-integrity failure;
- safety termination;
- host-declared end under an authorized rule.

## Reward design

Do not train on culprit correctness alone. That would reward answer leakage,
guessing, and collapsed social play. Harbor supports multiple numeric rewards
in `reward.json`, and Reward Kit can preserve per-criterion details and create
an aggregate training reward.

### Hard-zero gates

- invalid or unverifiable session trace;
- hidden-information access or unauthorized tool use;
- fabricated evidence treated as canonical evidence;
- resolution accepted without a licensed proof path;
- safety or mandatory rescue failure;
- environment or verifier tampering.

### Shared team rewards

- correct resolution supported by independent evidence;
- rescue or other safety-critical objective completed on time;
- proof-path coverage and elimination of material alternatives;
- balanced participation across seats and phases;
- useful information exchange and belief revision;
- low dependence on host recovery interventions;
- pacing and completion within the episode budget;
- efficient tool and token use.

### Individual rewards

- progress on the seat's public and private objectives;
- coherent use of authorized knowledge;
- role-specific relationships, bargains, and consequential choices;
- truthful handling of must-not-contradict facts;
- permitted deception that remains counterable by evidence;
- meaningful participation after a secret or culpability is exposed.

The culpable seat should be rewarded for forcing an evidence-backed accusation,
not for blocking rescue, exploiting private state, or making the game
unsolvable. Preserve the full reward vector even when a trainer requires one
aggregate scalar.

## Multi-agent rollout and credit assignment

One Harbor trial should produce:

- a team reward vector;
- an optional per-seat reward vector;
- one ATIF-compatible trajectory per policy context;
- token IDs, masks, and log probabilities per trainable policy;
- the canonical session history and tool receipts;
- the frozen release and environment version identifiers.

Harbor's documented RL example assumes one rollout per trial. Our rollout
adapter must expand a trial into one rollout per trainable seat, or train a
single shared policy from several seat trajectories with role-conditioned
observations. The distinction must be explicit in the trainer interface.

Training every seat simultaneously creates a moving-target problem. Start with:

1. train the host against a frozen player-policy pool;
2. train one investigator policy against frozen host, culprit, and peer pools;
3. rotate roles and games while sampling opponents from versioned policy pools;
4. only then evaluate population self-play or centralized-critic methods.

Hold out entire games and world families. Success on repeated Sybil's Cave
episodes may measure memorization rather than transferable investigation,
hosting, or social reasoning.

## Harbor packaging

- **Task:** one frozen game release plus environment/reward configuration.
- **Dataset:** many releases, cast variants, difficulty bands, and held-out
  worlds.
- **Trial:** one seeded multi-agent play episode with one policy lineup.
- **Job:** many episodes across lineups, models, role rotations, and seeds.
- **Verifier:** deterministic integrity/authorization checks plus isolated
  trajectory judges for social and experiential dimensions.
- **Artifacts:** session archive, public/private transcripts with access labels,
  per-seat trajectories, tool receipts, reward details, release attestations,
  and failure summaries under `/logs/artifacts/`.

The Harbor viewer can then compare rewards, timing, token usage, tool calls,
failures, and collected files across jobs. Harbor's artifact-collection
documentation also supports sidecar evidence, which is useful for keeping the
trusted game server's trace outside the policies' writable filesystem.

## Architecture

```text
Verismill + narrative generation (upstream, outside Harbor)
                         |
                  frozen Game Release
                         |
         Harbor task: one immutable environment instance
                         |
       +-----------------+------------------+
       | trusted game server / state kernel |
       | projections, ACLs, phase, evidence |
       +-----+---------+---------+-----------+
             |         |         |
          seat A    seat B    seat C ... host
          policy    policy    policy     policy
             |         |         |          |
       role-bound tools and private observations
             +---------+---------+----------+
                         |
              hash-chained episode trace
                         |
     isolated verifier -> reward vector + hard gates
                         |
      Harbor artifacts / viewer / rollout interface
                         |
                    RL trainer
```

## Smallest falsifying experiment

Use the accepted Sybil's Cave release as a single Harbor task, but do not train
yet. Implement one fixed-order four-player simulation with a deterministic host
policy and four isolated model contexts. Run at least 20 role-rotated episodes
across two model families.

The experiment succeeds only if:

- no seat can retrieve another seat's dossier or unreleased evidence;
- every episode replays to the same verified terminal state from its event log;
- each seat has a separate trajectory and token receipt;
- the verifier emits both hard gates and the full reward vector;
- Harbor collects and displays the session artifacts;
- changing only a seat policy changes behavior without changing the frozen
  environment or reward definition.

If Harbor cannot preserve per-seat trajectories and token attribution cleanly,
the custom rollout adapter is the first design problem to solve before any RL
training claim.
