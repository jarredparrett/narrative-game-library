"""Immutable contracts for deterministic multi-agent play episodes."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.runtime import SessionHistory


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class PolicyIdentity:
    """The exact policy implementation occupying one episode role."""

    policy_id: str
    provider: str
    model: str
    agent_id: str
    context_id: str
    trainable: bool = True

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "provider": self.provider,
            "model": self.model,
            "agent_id": self.agent_id,
            "context_id": self.context_id,
            "trainable": self.trainable,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PolicyIdentity":
        return cls(
            str(value["policy_id"]),
            str(value["provider"]),
            str(value["model"]),
            str(value["agent_id"]),
            str(value["context_id"]),
            bool(value.get("trainable", True)),
        )


@dataclass(frozen=True)
class SeatAssignment:
    seat_id: str
    policy: PolicyIdentity

    def to_mapping(self) -> dict[str, Any]:
        return {"seat_id": self.seat_id, "policy": self.policy.to_mapping()}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SeatAssignment":
        return cls(str(value["seat_id"]), PolicyIdentity.from_mapping(value["policy"]))


@dataclass(frozen=True)
class PolicyLineup:
    seats: tuple[SeatAssignment, ...]
    host: PolicyIdentity

    def __post_init__(self) -> None:
        if len({item.seat_id for item in self.seats}) != len(self.seats):
            raise ValueError("Lineup Seat IDs must be unique")
        identities = [item.policy.policy_id for item in self.seats] + [self.host.policy_id]
        contexts = [item.policy.context_id for item in self.seats] + [self.host.context_id]
        if len(set(identities)) != len(identities):
            raise ValueError("Each arena role requires a distinct Policy identity")
        if len(set(contexts)) != len(contexts):
            raise ValueError("Each arena role requires an isolated context identity")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "seats": [
                item.to_mapping() for item in sorted(self.seats, key=lambda item: item.seat_id)
            ],
            "host": self.host.to_mapping(),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PolicyLineup":
        return cls(
            tuple(SeatAssignment.from_mapping(item) for item in value["seats"]),
            PolicyIdentity.from_mapping(value["host"]),
        )


@dataclass(frozen=True)
class EpisodeConfig:
    max_steps: int = 80
    allow_private_messages: bool = True
    scheduler_version: str = "aec-seeded-v1"
    tool_schema_version: str = "narrative-arena-tools-v1"
    reward_version: str = "narrative-multi-agent-reward-v2"

    def __post_init__(self) -> None:
        if self.max_steps < 1:
            raise ValueError("Episode max_steps must be positive")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "allow_private_messages": self.allow_private_messages,
            "scheduler_version": self.scheduler_version,
            "tool_schema_version": self.tool_schema_version,
            "reward_version": self.reward_version,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EpisodeConfig":
        return cls(
            int(value["max_steps"]),
            bool(value["allow_private_messages"]),
            str(value["scheduler_version"]),
            str(value["tool_schema_version"]),
            str(value["reward_version"]),
        )


@dataclass(frozen=True)
class PolicyCallReceipt:
    """Trainer-facing token attribution for exactly one policy decision."""

    receipt_id: str
    input_token_ids: tuple[int, ...]
    output_token_ids: tuple[int, ...]
    mask_ids: tuple[int, ...]
    logprobs: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.mask_ids) != len(self.input_token_ids) + len(self.output_token_ids):
            raise ValueError("mask_ids must cover every input and output token")
        if self.logprobs and len(self.logprobs) != len(self.output_token_ids):
            raise ValueError("logprobs must align with output_token_ids")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "input_token_ids": list(self.input_token_ids),
            "output_token_ids": list(self.output_token_ids),
            "mask_ids": list(self.mask_ids),
            "logprobs": list(self.logprobs),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PolicyCallReceipt":
        return cls(
            str(value["receipt_id"]),
            tuple(int(item) for item in value["input_token_ids"]),
            tuple(int(item) for item in value["output_token_ids"]),
            tuple(int(item) for item in value["mask_ids"]),
            tuple(float(item) for item in value["logprobs"]),
        )


@dataclass(frozen=True)
class PolicyCallUsage:
    """Provider-reported usage for one model decision, even without token IDs."""

    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int = 0
    cost_usd: float = 0.0
    model_name: str | None = None
    response_id: str | None = None

    def __post_init__(self) -> None:
        if min(self.prompt_tokens, self.completion_tokens, self.cached_tokens) < 0:
            raise ValueError("policy usage token counts cannot be negative")
        if self.cost_usd < 0:
            raise ValueError("policy usage cost cannot be negative")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cached_tokens": self.cached_tokens,
            "cost_usd": self.cost_usd,
            "model_name": self.model_name,
            "response_id": self.response_id,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PolicyCallUsage":
        return cls(
            int(value["prompt_tokens"]),
            int(value["completion_tokens"]),
            int(value.get("cached_tokens", 0)),
            float(value.get("cost_usd", 0.0)),
            str(value["model_name"]) if value.get("model_name") else None,
            str(value["response_id"]) if value.get("response_id") else None,
        )


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    tool: str
    arguments: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {"call_id": self.call_id, "tool": self.tool, "arguments": _copy(self.arguments)}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ToolCall":
        return cls(str(value["call_id"]), str(value["tool"]), _copy(value["arguments"]))


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    accepted: bool
    public_reason: str
    content: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "accepted": self.accepted,
            "public_reason": self.public_reason,
            "content": _copy(self.content),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ToolResult":
        return cls(
            str(value["call_id"]),
            bool(value["accepted"]),
            str(value["public_reason"]),
            _copy(value["content"]),
        )


@dataclass(frozen=True)
class ArenaEvent:
    sequence: int
    previous_hash: str | None
    session_id: str
    release_id: str
    actor_id: str
    event_type: str
    visibility: tuple[str, ...]
    payload: Mapping[str, Any]
    event_hash: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "sequence": self.sequence,
            "previous_hash": self.previous_hash,
            "session_id": self.session_id,
            "release_id": self.release_id,
            "actor_id": self.actor_id,
            "event_type": self.event_type,
            "visibility": list(self.visibility),
            "payload": _copy(self.payload),
        }

    def to_mapping(self) -> dict[str, Any]:
        return {**self.material(), "event_hash": self.event_hash}

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        previous_hash: str | None,
        session_id: str,
        release_id: str,
        actor_id: str,
        event_type: str,
        visibility: tuple[str, ...],
        payload: Mapping[str, Any],
    ) -> "ArenaEvent":
        provisional = cls(
            sequence,
            previous_hash,
            session_id,
            release_id,
            actor_id,
            event_type,
            tuple(visibility),
            _copy(payload),
            "",
        )
        return replace(provisional, event_hash=digest_json(provisional.material()))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArenaEvent":
        return cls(
            int(value["sequence"]),
            value.get("previous_hash"),
            str(value["session_id"]),
            str(value["release_id"]),
            str(value["actor_id"]),
            str(value["event_type"]),
            tuple(str(item) for item in value["visibility"]),
            _copy(value["payload"]),
            str(value["event_hash"]),
        )


@dataclass(frozen=True)
class TrajectoryStep:
    turn: int
    arena_sequence: int
    session_sequence: int
    observation: Mapping[str, Any]
    observation_hash: str
    call: ToolCall
    result: ToolResult
    policy_receipt: PolicyCallReceipt | None
    policy_usage: PolicyCallUsage | None = None
    reasoning_summary: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "turn": self.turn,
            "arena_sequence": self.arena_sequence,
            "session_sequence": self.session_sequence,
            "observation": _copy(self.observation),
            "observation_hash": self.observation_hash,
            "call": self.call.to_mapping(),
            "result": self.result.to_mapping(),
            "policy_receipt": self.policy_receipt.to_mapping() if self.policy_receipt else None,
            "policy_usage": self.policy_usage.to_mapping() if self.policy_usage else None,
            "reasoning_summary": self.reasoning_summary,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TrajectoryStep":
        receipt = value.get("policy_receipt")
        usage = value.get("policy_usage")
        return cls(
            int(value["turn"]),
            int(value["arena_sequence"]),
            int(value["session_sequence"]),
            _copy(value["observation"]),
            str(value["observation_hash"]),
            ToolCall.from_mapping(value["call"]),
            ToolResult.from_mapping(value["result"]),
            PolicyCallReceipt.from_mapping(receipt) if receipt is not None else None,
            PolicyCallUsage.from_mapping(usage) if usage is not None else None,
            str(value["reasoning_summary"]) if value.get("reasoning_summary") else None,
        )


@dataclass(frozen=True)
class PolicyTrajectory:
    actor_id: str
    role: str
    policy: PolicyIdentity
    steps: tuple[TrajectoryStep, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "atif_version": "1.0",
            "actor_id": self.actor_id,
            "role": self.role,
            "policy": self.policy.to_mapping(),
            "steps": [item.to_mapping() for item in self.steps],
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PolicyTrajectory":
        return cls(
            str(value["actor_id"]),
            str(value["role"]),
            PolicyIdentity.from_mapping(value["policy"]),
            tuple(TrajectoryStep.from_mapping(item) for item in value["steps"]),
        )


@dataclass(frozen=True)
class EpisodeArchive:
    episode_id: str
    release_id: str
    episode_seed: int
    config: EpisodeConfig
    lineup: PolicyLineup
    version_locks: Mapping[str, str]
    realized_seat_order: tuple[str, ...]
    events: tuple[ArenaEvent, ...]
    session_history: SessionHistory
    trajectories: tuple[PolicyTrajectory, ...]
    violations: tuple[str, ...]
    termination_reason: str | None
    terminal_state_hash: str

    @property
    def trace_head(self) -> str | None:
        return self.events[-1].event_hash if self.events else None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "episode_id": self.episode_id,
            "release_id": self.release_id,
            "episode_seed": self.episode_seed,
            "config": self.config.to_mapping(),
            "lineup": self.lineup.to_mapping(),
            "version_locks": dict(sorted(self.version_locks.items())),
            "realized_seat_order": list(self.realized_seat_order),
            "events": [item.to_mapping() for item in self.events],
            "session_history": self.session_history.to_mapping(),
            "trajectories": [
                item.to_mapping() for item in sorted(self.trajectories, key=lambda item: item.actor_id)
            ],
            "violations": list(self.violations),
            "termination_reason": self.termination_reason,
            "terminal_state_hash": self.terminal_state_hash,
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_mapping())

    @classmethod
    def from_bytes(cls, value: bytes) -> "EpisodeArchive":
        parsed = json.loads(value)
        history = SessionHistory.from_bytes(canonical_json(parsed["session_history"]))
        return cls(
            str(parsed["episode_id"]),
            str(parsed["release_id"]),
            int(parsed["episode_seed"]),
            EpisodeConfig.from_mapping(parsed["config"]),
            PolicyLineup.from_mapping(parsed["lineup"]),
            {str(key): str(item) for key, item in parsed["version_locks"].items()},
            tuple(str(item) for item in parsed["realized_seat_order"]),
            tuple(ArenaEvent.from_mapping(item) for item in parsed["events"]),
            history,
            tuple(PolicyTrajectory.from_mapping(item) for item in parsed["trajectories"]),
            tuple(str(item) for item in parsed["violations"]),
            parsed.get("termination_reason"),
            str(parsed["terminal_state_hash"]),
        )


@dataclass(frozen=True)
class GateResult:
    code: str
    passed: bool
    explanation: str

    def to_mapping(self) -> dict[str, Any]:
        return {"code": self.code, "passed": self.passed, "explanation": self.explanation}


@dataclass(frozen=True)
class RewardReport:
    reward_version: str
    aggregate: float
    hard_gates: tuple[GateResult, ...]
    team: Mapping[str, float]
    diagnostics: Mapping[str, float]
    per_actor: Mapping[str, Mapping[str, float]]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "reward_version": self.reward_version,
            "reward": self.aggregate,
            "hard_gates": [item.to_mapping() for item in self.hard_gates],
            "team": dict(sorted(self.team.items())),
            "diagnostics": dict(sorted(self.diagnostics.items())),
            "per_actor": {
                key: dict(sorted(value.items())) for key, value in sorted(self.per_actor.items())
            },
        }
