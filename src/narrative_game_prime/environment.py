"""Prime Verifiers v1 adapter over the canonical narrative-game arena."""

from __future__ import annotations

from contextlib import AsyncExitStack
import base64
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import verifiers.v1 as vf
from pydantic import Field, model_validator

from narrative_game.compiler import load_release
from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.simulation import (
    AsyncMultiAgentArenaRunner,
    EpisodeArchive,
    EpisodeConfig,
    MultiAgentEpisode,
    PolicyDecision,
    PolicyIdentity,
    PolicyLineup,
    SeatAssignment,
    ToolCall,
    evaluate_episode,
)
from narrative_game.simulation.policy_prompt import (
    TOOL_ARGUMENT_CONTRACTS,
    model_observation,
    policy_guidance,
)


PLUGIN_ID = "narrative_game_prime"
REWARD_NAME = "outcome_integrity"

_OUTPUT_CONTRACT = """You are one isolated actor in a facilitated mystery game.
For every turn, read only the supplied turn payload and return exactly one JSON object:
{"reasoning_summary":"brief decision rationale without private chain of thought","tool":"one legal tool name","arguments":{}}
Use only a tool listed in legal_tools. Return no Markdown and no extra keys.
Never claim facts absent from authorized_observation. The environment, not you, decides whether an action succeeds."""


def _role_system_prompt(game: Mapping[str, Any], role: str) -> str:
    """Bind stable identity and conduct without copying phase-gated knowledge."""
    lines = [_OUTPUT_CONTRACT, f"Your immutable role is {role}."]
    if role == "host":
        lines.extend(
            (
                "You are the facilitator, not a player character.",
                "Coordinate the legal reveal schedule, protect each Seat's knowledge boundary, "
                "and require an evidence-backed resolution.",
            )
        )
        return "\n".join(lines)

    seat_id = role.split(":", 1)[1]
    characters = game.get("narrative", {}).get("characters", [])
    character = next(
        (item for item in characters if str(item.get("seat_id")) == seat_id),
        None,
    )
    if character is None:
        raise ValueError(f"Prime role {role} has no character identity")
    character_name = str(character["name"])
    character_id = str(character["id"])
    lines.extend(
        (
            f"You are {character_name} (character {character_id}). Stay in character.",
            "Treat game.character and game.dossier in authorized_observation as your private "
            "character brief; never claim another Seat's private knowledge.",
            "Pursue the objectives and disclosure timing in the current authorized_observation "
            "without inventing facts or obstructing an urgent rescue.",
            "Phase-specific knowledge, evidence, objectives, and legal actions come only from "
            "the current authorized_observation.",
        )
    )
    return "\n".join(lines)


def _parse_decision_object(raw: str) -> dict[str, Any]:
    """Recover exactly the first JSON object without accepting prose as action data."""
    start = raw.find("{")
    if start < 0:
        raise ValueError("response contains no JSON object")
    try:
        parsed, _ = json.JSONDecoder().raw_decode(raw[start:])
    except json.JSONDecodeError as exc:
        raise ValueError("response contains no valid JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError("response JSON must be an object")
    return parsed


class NarrativeGameTaskData(vf.TaskData):
    """One frozen Release and deterministic seed shipped to the Prime worker."""

    release_base64: str
    release_id: str
    episode_seed: int
    episode_config: dict[str, Any]


class NarrativeRoleTaskData(vf.TaskData):
    """One actor-local prompt; no answer key or another Seat's private state."""

    actor_id: str
    role: str
    episode_id: str
    release_id: str


class NarrativeGameTask(vf.Task[NarrativeGameTaskData]):
    pass


class NarrativeRoleTask(vf.Task[NarrativeRoleTaskData]):
    pass


class NarrativeGameTasksetConfig(vf.TasksetConfig):
    release_paths: list[Path] = Field(default_factory=list)
    episode_seeds: list[int] = Field(default_factory=lambda: [0])
    episode_config: dict[str, Any] = Field(default_factory=lambda: EpisodeConfig().to_mapping())

    @model_validator(mode="after")
    def _requires_work(self) -> "NarrativeGameTasksetConfig":
        EpisodeConfig.from_mapping(self.episode_config)
        return self


class NarrativeGameTaskset(vf.Taskset[NarrativeGameTask, NarrativeGameTasksetConfig]):
    """Materialize Release bytes into portable Prime TaskData."""

    def load(self) -> Iterable[NarrativeGameTask]:
        if not self.config.release_paths:
            raise ValueError("release_paths must contain at least one frozen Release ZIP")
        if not self.config.episode_seeds:
            raise ValueError("episode_seeds must contain at least one deterministic seed")
        index = 0
        for path in self.config.release_paths:
            bundle = path.read_bytes()
            release = load_release(bundle)
            encoded = base64.b64encode(bundle).decode("ascii")
            for seed in self.config.episode_seeds:
                yield NarrativeGameTask(
                    NarrativeGameTaskData(
                        idx=index,
                        name=f"{release.release_id[:19]} seed {seed}",
                        description="Run one verified multi-agent narrative episode.",
                        prompt=None,
                        release_base64=encoded,
                        release_id=release.release_id,
                        episode_seed=int(seed),
                        episode_config=dict(self.config.episode_config),
                    )
                )
                index += 1


class NarrativeGameEnvConfig(vf.EnvConfig):
    host: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})
    player: vf.AgentConfig = vf.AgentConfig(harness={"id": "null"})
    train_host: bool = False
    train_players: bool = True


def _model_provider(model: str | None) -> str:
    value = model or "run-default"
    return value.split("/", 1)[0] if "/" in value else "prime"


def _identity(
    *,
    role: str,
    release_id: str,
    seed: int,
    model: str | None,
    trainable: bool,
) -> PolicyIdentity:
    material = {
        "adapter": "prime-verifiers-v1",
        "release_id": release_id,
        "episode_seed": seed,
        "role": role,
        "model": model or "run-default",
    }
    suffix = digest_json(material).split(":", 1)[1][:24]
    return PolicyIdentity(
        policy_id=f"prime-policy-{suffix}",
        provider=_model_provider(model),
        model=model or "run-default",
        agent_id=f"prime-agent-{role}",
        context_id=f"prime-context-{suffix}",
        trainable=trainable,
    )


class _PrimeInteractionPolicy:
    """Translate one persistent Prime interaction into strict arena decisions."""

    def __init__(self, actor_id: str, interaction: Any) -> None:
        self.actor_id = actor_id
        self.interaction = interaction
        self.turn = 0
        self._last_dialogue_sequence = -1
        self._prior_action_count = 0

    async def decide(self, observation: Mapping[str, Any]) -> PolicyDecision:
        self.turn += 1
        legal_tools = [str(item) for item in observation["legal_tools"]]
        prompt = {
            "authorized_observation": model_observation(
                observation,
                include_static=self.turn == 1,
                dialogue_after=self._last_dialogue_sequence,
                actions_after=self._prior_action_count,
            ),
            "legal_tools": legal_tools,
            "argument_contracts": {
                tool: TOOL_ARGUMENT_CONTRACTS.get(tool, {}) for tool in legal_tools
            },
            "output_contract": {
                "reasoning_summary": "concise decision rationale",
                "tool": "one exact legal_tools value",
                "arguments": "object matching that tool's argument contract",
            },
            "policy_guidance": policy_guidance(str(observation["role"]), observation),
        }
        segment = await self.interaction.turn(canonical_json(prompt).decode("utf-8"))
        if segment.terminated:
            raise RuntimeError(f"Prime actor {self.actor_id} terminated before answering")
        try:
            parsed = _parse_decision_object(segment.last_reply)
        except ValueError as exc:
            raise ValueError(f"Prime actor {self.actor_id} returned invalid JSON") from exc
        if not isinstance(parsed, dict) or set(parsed) != {
            "reasoning_summary",
            "tool",
            "arguments",
        }:
            raise ValueError(f"Prime actor {self.actor_id} violated the action schema")
        if not isinstance(parsed["reasoning_summary"], str):
            raise ValueError("reasoning_summary must be a string")
        if not isinstance(parsed["tool"], str) or not isinstance(parsed["arguments"], dict):
            raise ValueError("tool must be a string and arguments must be an object")
        if parsed["tool"] not in legal_tools:
            raise ValueError(f"Prime actor {self.actor_id} chose a non-legal tool")
        dialogue = observation.get("dialogue", [])
        if dialogue:
            self._last_dialogue_sequence = max(
                self._last_dialogue_sequence,
                max(int(item.get("sequence", -1)) for item in dialogue),
            )
        self._prior_action_count = len(observation.get("own_prior_actions", []))
        call_id = "prime-call-" + digest_json(
            {
                "actor_id": self.actor_id,
                "turn": self.turn,
                "observation": observation,
                "tool": parsed["tool"],
                "arguments": parsed["arguments"],
            }
        ).split(":", 1)[1][:24]
        return PolicyDecision(
            ToolCall(call_id, parsed["tool"], parsed["arguments"]),
            reasoning_summary=parsed["reasoning_summary"],
        )


class NarrativeGameEnv(vf.Env[NarrativeGameEnvConfig]):
    """Run one host and N isolated player contexts, then score the team once."""

    async def setup(self, agents: vf.Agents) -> None:
        agents.host.trainable = self.config.train_host
        agents.player.trainable = self.config.train_players

    async def run(self, task: vf.Task, agents: vf.Agents) -> None:
        if not isinstance(task, NarrativeGameTask):
            raise TypeError("NarrativeGameEnv requires NarrativeGameTask")
        data = task.data
        release = load_release(base64.b64decode(data.release_base64, validate=True))
        if release.release_id != data.release_id:
            raise ValueError("Prime task Release identity does not match its bytes")
        config = EpisodeConfig.from_mapping(data.episode_config)
        game = json.loads(release.file("trusted/game.json").data)
        seat_ids = tuple(sorted(str(item["id"]) for item in game["kernel"]["seats"]))
        host_identity = _identity(
            role="host",
            release_id=release.release_id,
            seed=data.episode_seed,
            model=agents.host.config.model,
            trainable=agents.host.trainable,
        )
        seat_identities = {
            seat_id: _identity(
                role=f"seat:{seat_id}",
                release_id=release.release_id,
                seed=data.episode_seed,
                model=agents.player.config.model,
                trainable=agents.player.trainable,
            )
            for seat_id in seat_ids
        }
        episode = MultiAgentEpisode.reset(
            release,
            episode_seed=data.episode_seed,
            lineup=PolicyLineup(
                tuple(SeatAssignment(seat_id, seat_identities[seat_id]) for seat_id in seat_ids),
                host_identity,
            ),
            config=config,
        )
        actor_roles = {
            actor_id: (
                "host" if actor_id.startswith("host:") else f"seat:{actor_id.split(':', 2)[1]}"
            )
            for actor_id in episode.credentials
        }
        policies: dict[str, _PrimeInteractionPolicy] = {}
        interactions: dict[str, Any] = {}
        async with AsyncExitStack() as stack:
            for actor_id, role in sorted(actor_roles.items()):
                prime_agent = agents.host if role == "host" else agents.player
                role_task = NarrativeRoleTask(
                    NarrativeRoleTaskData(
                        prompt=None,
                        system_prompt=_role_system_prompt(game, role),
                        actor_id=actor_id,
                        role=role,
                        episode_id=episode.episode_id,
                        release_id=release.release_id,
                    )
                )
                interaction = await stack.enter_async_context(prime_agent.interaction(role_task))
                interaction.trace.info.update(
                    {
                        "narrative_actor_id": actor_id,
                        "narrative_role": role,
                        "narrative_episode_id": episode.episode_id,
                        "narrative_release_id": release.release_id,
                    }
                )
                interactions[actor_id] = interaction
                policies[actor_id] = _PrimeInteractionPolicy(actor_id, interaction)
            archive = await AsyncMultiAgentArenaRunner().run(episode, policies)
            host_actor = next(key for key, role in actor_roles.items() if role == "host")
            interactions[host_actor].trace.info["narrative_episode_archive_base64"] = (
                base64.b64encode(archive.to_bytes()).decode("ascii")
            )

    async def finalize(self, task: vf.Task, episode: vf.Episode) -> None:
        if not isinstance(task, NarrativeGameTask):
            raise TypeError("NarrativeGameEnv requires NarrativeGameTask")
        host_traces = [trace for trace in episode.traces if trace.agent.name == "host"]
        if len(host_traces) != 1:
            raise ValueError("Prime episode must contain exactly one host trace")
        encoded = host_traces[0].info.get("narrative_episode_archive_base64")
        if not isinstance(encoded, str):
            raise ValueError("Prime host trace is missing the canonical episode archive")
        archive = EpisodeArchive.from_bytes(base64.b64decode(encoded, validate=True))
        release = load_release(base64.b64decode(task.data.release_base64, validate=True))
        if archive.release_id != release.release_id:
            raise ValueError("Prime trace archive belongs to a different Release")
        trace_actors = [trace.info.get("narrative_actor_id") for trace in episode.traces]
        archive_actors = [trajectory.actor_id for trajectory in archive.trajectories]
        if len(trace_actors) != len(set(trace_actors)) or set(trace_actors) != set(archive_actors):
            raise ValueError("Prime traces do not map one-to-one onto canonical arena roles")
        report = evaluate_episode(release, archive)
        for trace in episode.traces:
            trace.record_reward(REWARD_NAME, report.aggregate)
            trace.record_metrics(
                {
                    "integrity": report.team["integrity"],
                    "outcome": report.team["outcome"],
                    **{f"diagnostic.{key}": value for key, value in report.diagnostics.items()},
                }
            )
            actor_id = str(trace.info["narrative_actor_id"])
            for name, value in report.per_actor.get(actor_id, {}).items():
                trace.record_metric(f"actor.{name}", value)
        host_traces[0].info["narrative_reward_report"] = report.to_mapping()
