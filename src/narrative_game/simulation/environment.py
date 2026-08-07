"""Deterministic agent-environment-cycle arena over Session Authority."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.runtime import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    AuthorizationDenied,
    SessionHistory,
    SessionCommand,
    ViewerGrant,
    apply_command,
    create_session,
    host_snapshot,
    replay,
    retrieve_resource,
    seat_snapshot,
)

from .model import (
    ArenaEvent,
    EpisodeArchive,
    EpisodeConfig,
    PolicyCallReceipt,
    PolicyCallUsage,
    PolicyLineup,
    PolicyTrajectory,
    ToolCall,
    ToolResult,
    TrajectoryStep,
)


def _seat_arena_snapshot(
    release: GameRelease,
    history: SessionHistory,
    auth: AuthorizationContext,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Project a replayable seat view plus safe action identifiers."""
    snapshot = seat_snapshot(release, history, auth)
    seat_id = str(snapshot["seat"]["id"])
    trusted_game = json.loads(release.file("trusted/game.json").data)
    kernel = trusted_game["kernel"]
    resources = {item["id"]: item for item in kernel["resources"]}
    authorized = {
        str(item["resource"]).removeprefix("resource:")
        for item in kernel["access_policies"]
        if f"seat:{seat_id}" in item["grantees"]
    }
    requestable_resources = [
        {
            "resource_id": resource_id,
            "label": str(resources[resource_id]["label"]),
            "media_type": str(resources[resource_id]["media_type"]),
        }
        for resource_id in sorted(authorized)
    ]
    resolution = trusted_game["narrative"]["resolution"]
    if snapshot["phase_id"] == resolution["phase_id"]:
        snapshot["resolution_options"] = {
            "hypotheses": [
                {
                    "id": str(item["id"]),
                    "label": str(item["label"]),
                    "proposition_ids": [str(value) for value in item["proposition_ids"]],
                }
                for item in trusted_game["narrative"]["hypotheses"]
            ],
            "proof_paths": [
                {
                    "id": str(item["id"]),
                    "evidence_ids": [str(value) for value in item["evidence_ids"]],
                }
                for item in trusted_game["narrative"]["proof_paths"]
            ],
        }
    return snapshot, requestable_resources


ARENA_VERSION = "1.0.0"


@dataclass(frozen=True)
class ArenaCredential:
    """Opaque role binding held by the arena runner, never by another seat."""

    actor_id: str
    token: str


class MultiAgentEpisode:
    """One in-memory, replayable multi-agent episode over a frozen Release."""

    def __init__(
        self,
        *,
        release: GameRelease,
        episode_seed: int,
        lineup: PolicyLineup,
        config: EpisodeConfig,
    ) -> None:
        self.release = release
        self.episode_seed = int(episode_seed)
        self.lineup = lineup
        self.config = config
        self.episode_id = digest_json(
            {
                "kind": "narrative-multi-agent-episode-v1",
                "release_id": release.release_id,
                "episode_seed": self.episode_seed,
                "lineup": lineup.to_mapping(),
                "config": config.to_mapping(),
            }
        )
        self.session_id = "arena-session-" + self.episode_id.split(":", 1)[1][:24]
        game = json.loads(release.file("trusted/game.json").data)
        seat_ids = tuple(sorted(item["id"] for item in game["kernel"]["seats"]))
        assignments = {item.seat_id: item for item in lineup.seats}
        if set(assignments) != set(seat_ids):
            raise ValueError("Lineup must bind exactly every Release Seat")
        self._seat_actor_ids = {
            seat_id: f"seat:{seat_id}:{assignments[seat_id].policy.policy_id}"
            for seat_id in seat_ids
        }
        self._host_actor_id = f"host:{lineup.host.policy_id}"
        self.realized_seat_order = tuple(
            sorted(
                seat_ids,
                key=lambda seat_id: (
                    digest_json({"episode_seed": self.episode_seed, "seat_id": seat_id}),
                    seat_id,
                ),
            )
        )
        self._schedule = (
            self._host_actor_id,
            *(self._seat_actor_ids[item] for item in self.realized_seat_order),
        )
        self._turn_index = 0
        bindings = []
        self._auth: dict[str, AuthorizationContext] = {}
        for seat_id in seat_ids:
            assignment = assignments[seat_id]
            actor_id = self._seat_actor_ids[seat_id]
            binding_id = "binding-" + digest_json(
                {"episode_id": self.episode_id, "seat_id": seat_id}
            ).split(":", 1)[1][:24]
            bindings.append(
                ActorBinding(
                    binding_id,
                    Actor(actor_id, "model", assignment.policy.model),
                    seat_id,
                    1,
                )
            )
            self._auth[actor_id] = AuthorizationContext("actor", actor_id, binding_id)
        self._auth[self._host_actor_id] = AuthorizationContext("viewer", self._host_actor_id)
        self.history = create_session(
            release=release,
            session_id=self.session_id,
            mode="simulation",
            bindings=bindings,
            viewers=(ViewerGrant(self._host_actor_id, "host"),),
        )
        self._credentials = {
            actor_id: ArenaCredential(
                actor_id,
                digest_json(
                    {
                        "kind": "arena-role-credential-v1",
                        "episode_id": self.episode_id,
                        "actor_id": actor_id,
                    }
                ),
            )
            for actor_id in self._auth
        }
        self._events: list[ArenaEvent] = []
        self._trajectory_steps: dict[str, list[TrajectoryStep]] = {
            actor_id: [] for actor_id in self._auth
        }
        self._violations: list[str] = []
        self._termination_reason: str | None = None
        self._steps = 0
        component_versions = {
            str(item["id"]): str(item["version"])
            for item in release.manifest["component_lock"]["components"]
        }
        self.version_locks = {
            "arena": ARENA_VERSION,
            "release": release.release_id,
            "scheduler": config.scheduler_version,
            "tools": config.tool_schema_version,
            "reward": config.reward_version,
            **{f"component:{key}": value for key, value in sorted(component_versions.items())},
        }
        self._append_event(
            actor_id="system",
            event_type="episode-reset",
            visibility=("trusted",),
            payload={
                "episode_id": self.episode_id,
                "episode_seed": self.episode_seed,
                "realized_seat_order": list(self.realized_seat_order),
                "schedule": list(self._schedule),
                "lineup": lineup.to_mapping(),
                "version_locks": self.version_locks,
                "session_history_hash": self.history.content_hash,
            },
        )

    @classmethod
    def reset(
        cls,
        release: GameRelease,
        *,
        episode_seed: int,
        lineup: PolicyLineup,
        config: EpisodeConfig = EpisodeConfig(),
    ) -> "MultiAgentEpisode":
        """Create a fresh isolated episode without opening the first phase."""
        return cls(release=release, episode_seed=episode_seed, lineup=lineup, config=config)

    @property
    def active_actor_id(self) -> str | None:
        return None if self.done else self._schedule[self._turn_index]

    @property
    def done(self) -> bool:
        return self._termination_reason is not None

    @property
    def termination_reason(self) -> str | None:
        return self._termination_reason

    @property
    def credentials(self) -> Mapping[str, ArenaCredential]:
        """Return runner-held credentials keyed by exact actor identity."""
        return dict(self._credentials)

    def _append_event(
        self,
        *,
        actor_id: str,
        event_type: str,
        visibility: tuple[str, ...],
        payload: Mapping[str, Any],
    ) -> ArenaEvent:
        event = ArenaEvent.create(
            sequence=len(self._events) + 1,
            previous_hash=self._events[-1].event_hash if self._events else None,
            session_id=self.session_id,
            release_id=self.release.release_id,
            actor_id=actor_id,
            event_type=event_type,
            visibility=visibility,
            payload=payload,
        )
        self._events.append(event)
        return event

    def _credential(self, credential: ArenaCredential) -> AuthorizationContext:
        expected = self._credentials.get(credential.actor_id)
        if expected is None or expected != credential:
            raise AuthorizationDenied("not authorized")
        return self._auth[credential.actor_id]

    def _seat_id(self, actor_id: str) -> str | None:
        return next(
            (seat_id for seat_id, value in self._seat_actor_ids.items() if value == actor_id),
            None,
        )

    def _dialogue_for(self, actor_id: str) -> list[dict[str, Any]]:
        dialogue = []
        for event in self._events:
            if event.event_type not in {"said", "private-message", "host-broadcast"}:
                continue
            if "public" not in event.visibility and actor_id not in event.visibility:
                continue
            dialogue.append(
                {
                    "sequence": event.sequence,
                    "actor_id": event.actor_id,
                    "event_type": event.event_type,
                    **dict(event.payload),
                }
            )
        return dialogue

    def _legal_tools(self, actor_id: str, snapshot: Mapping[str, Any]) -> list[str]:
        if self.done or actor_id != self.active_actor_id:
            return []
        if actor_id == self._host_actor_id:
            status = snapshot["state"]["status"]
            if status == "created":
                return ["open_session"]
            if status != "active":
                return []
            tools = ["broadcast", "disclose_resource", "deliver_intervention", "end_session"]
            game = snapshot["game"]["game"]
            phases = sorted(game["narrative"]["phases"], key=lambda item: item["order"])
            current = snapshot["state"]["phase_id"]
            if next(item for item in phases if item["id"] == current)["order"] < phases[-1]["order"]:
                tools.append("advance_phase")
            return sorted(tools)
        tools = ["inspect_evidence", "say"]
        if self.config.allow_private_messages:
            tools.append("message")
        tools.extend(item.replace("-", "_") for item in snapshot["allowed_actions"])
        return sorted(set(tools))

    def observe(self, credential: ArenaCredential) -> dict[str, Any]:
        """Return the caller's authorized projection and no other role's data."""
        auth = self._credential(credential)
        requestable_resources: list[dict[str, str]] = []
        if credential.actor_id == self._host_actor_id:
            snapshot = host_snapshot(self.release, self.history, auth)
            role = "host"
        else:
            snapshot, requestable_resources = _seat_arena_snapshot(
                self.release, self.history, auth
            )
            seat_id = self._seat_id(credential.actor_id)
            role = f"seat:{seat_id}"
        own_steps = self._trajectory_steps[credential.actor_id]
        return {
            "schema_version": "1.0",
            "episode_id": self.episode_id,
            "release_id": self.release.release_id,
            "actor_id": credential.actor_id,
            "role": role,
            "active_actor_id": self.active_actor_id,
            "remaining_steps": max(0, self.config.max_steps - self._steps),
            "legal_tools": self._legal_tools(credential.actor_id, snapshot),
            "requestable_resources": requestable_resources,
            "game": snapshot,
            "dialogue": self._dialogue_for(credential.actor_id),
            "own_prior_actions": [
                {
                    "turn": item.turn,
                    "call": item.call.to_mapping(),
                    "result": item.result.to_mapping(),
                }
                for item in own_steps
            ],
        }

    def _runtime_command(
        self,
        *,
        actor_id: str,
        call: ToolCall,
        action: str,
        payload: Mapping[str, Any],
    ) -> tuple[ToolResult, list[dict[str, Any]]]:
        command = SessionCommand(
            call.call_id,
            self.session_id,
            self.release.release_id,
            self.history.sequence,
            action,
            payload,
        )
        result = apply_command(self.release, self.history, command, self._auth[actor_id])
        self.history = result.history
        tool_result = ToolResult(
            call.call_id,
            result.receipt.accepted,
            result.receipt.public_reason,
            {
                "receipt_id": result.receipt.receipt_id,
                "event_hashes": list(result.receipt.event_hashes),
                "session_sequence": self.history.sequence,
            },
        )
        return tool_result, [item.to_mapping() for item in result.events]

    def _execute(
        self, actor_id: str, call: ToolCall
    ) -> tuple[ToolResult, list[dict[str, Any]], tuple[str, ...], str]:
        tool = call.tool.replace("-", "_")
        arguments = dict(call.arguments)
        runtime_events: list[dict[str, Any]] = []
        visibility: tuple[str, ...] = ("trusted",)
        event_type = "tool-call"
        if actor_id == self._host_actor_id:
            if tool == "open_session":
                result, runtime_events = self._runtime_command(
                    actor_id=actor_id, call=call, action="open-session", payload={}
                )
            elif tool == "advance_phase":
                result, runtime_events = self._runtime_command(
                    actor_id=actor_id,
                    call=call,
                    action="advance-phase",
                    payload={"phase_id": str(arguments["phase_id"])},
                )
            elif tool == "disclose_resource":
                audiences = arguments.get("audiences", arguments.get("audience_seat_ids"))
                result, runtime_events = self._runtime_command(
                    actor_id=actor_id,
                    call=call,
                    action="disclose-resource",
                    payload={
                        "resource_id": str(arguments["resource_id"]),
                        "audience_seat_ids": list(audiences),
                        "evidence_grade": str(arguments.get("evidence_grade", "runtime-enforced")),
                    },
                )
            elif tool == "deliver_intervention":
                audiences = arguments.get("audiences", arguments.get("audience_seat_ids"))
                result, runtime_events = self._runtime_command(
                    actor_id=actor_id,
                    call=call,
                    action="deliver-intervention",
                    payload={
                        "intervention_id": str(arguments["intervention_id"]),
                        "audience_seat_ids": list(audiences),
                        "reason": str(arguments["reason"]),
                    },
                )
            elif tool == "broadcast":
                text = str(arguments["text"]).strip()
                if not text:
                    raise ValueError("broadcast text is empty")
                result = ToolResult(call.call_id, True, "accepted", {"text": text})
                event_type = "host-broadcast"
                visibility = ("public",)
            elif tool == "end_session":
                reason = str(arguments["reason"]).strip()
                if not reason:
                    raise ValueError("end reason is empty")
                result = ToolResult(call.call_id, True, "accepted", {"reason": reason})
                self._termination_reason = (
                    "safety_failure" if reason == "safety_failure" else "host_end"
                )
            else:
                raise AuthorizationDenied("not authorized")
        else:
            seat_id = self._seat_id(actor_id)
            if seat_id is None:
                raise AuthorizationDenied("not authorized")
            if tool == "inspect_evidence":
                resource_id = str(arguments["resource_id"])
                data = retrieve_resource(self.release, self.history, self._auth[actor_id], resource_id)
                result = ToolResult(
                    call.call_id,
                    True,
                    "accepted",
                    {
                        "resource_id": resource_id,
                        "content_base64": base64.b64encode(data).decode("ascii"),
                    },
                )
            elif tool == "say":
                text = str(arguments["text"]).strip()
                if not text:
                    raise ValueError("speech text is empty")
                result = ToolResult(call.call_id, True, "accepted", {"text": text})
                event_type = "said"
                visibility = ("public",)
            elif tool == "message":
                if not self.config.allow_private_messages:
                    raise AuthorizationDenied("not authorized")
                target_seat = str(arguments["seat_id"])
                target_actor = self._seat_actor_ids.get(target_seat)
                if target_actor is None or target_actor == actor_id:
                    raise AuthorizationDenied("not authorized")
                text = str(arguments["text"]).strip()
                if not text:
                    raise ValueError("message text is empty")
                result = ToolResult(
                    call.call_id, True, "accepted", {"seat_id": target_seat, "text": text}
                )
                event_type = "private-message"
                visibility = (actor_id, target_actor)
            elif tool in {
                "request_evidence",
                "request_hint",
                "share_claim",
                "update_character_state",
                "submit_resolution",
            }:
                action = tool.replace("_", "-")
                payload = dict(arguments)
                payload.pop("explanation", None)
                result, runtime_events = self._runtime_command(
                    actor_id=actor_id, call=call, action=action, payload=payload
                )
                if tool == "submit_resolution" and result.accepted:
                    submission_sequence = self.history.sequence
                    resolution_call = ToolCall(
                        f"{call.call_id}:environment-resolution",
                        "record_resolution",
                        {"submission_sequence": submission_sequence},
                    )
                    resolution, resolution_events = self._runtime_command(
                        actor_id=self._host_actor_id,
                        call=resolution_call,
                        action="record-resolution",
                        payload={"submission_sequence": submission_sequence},
                    )
                    runtime_events.extend(resolution_events)
                    if not resolution.accepted:
                        raise RuntimeError("environment could not record submitted resolution")
                    state = replay(self.release, self.history)
                    self._termination_reason = (
                        "accepted_resolution"
                        if state["resolution"]["correct"]
                        else "incorrect_resolution"
                    )
                    result = ToolResult(
                        call.call_id,
                        True,
                        "accepted",
                        {
                            **dict(result.content),
                            "resolution_receipt_id": resolution.content["receipt_id"],
                            "correct": state["resolution"]["correct"],
                        },
                    )
            else:
                raise AuthorizationDenied("not authorized")
        return result, runtime_events, visibility, event_type

    def _terminate_for_violation(self, code: str, actor_id: str, call: ToolCall) -> ToolResult:
        self._violations.append(code)
        self._termination_reason = "authorization_failure"
        return ToolResult(call.call_id, False, "tool rejected", {"violation": code})

    def step(
        self,
        credential: ArenaCredential,
        call: ToolCall,
        *,
        policy_receipt: PolicyCallReceipt | None = None,
        policy_usage: PolicyCallUsage | None = None,
        reasoning_summary: str | None = None,
    ) -> ToolResult:
        """Apply one authorized tool call and advance the deterministic AEC turn."""
        if self.done:
            raise RuntimeError("episode is already terminal")
        auth = self._credential(credential)
        del auth
        actor_id = credential.actor_id
        reasoning_summary = reasoning_summary.strip() if reasoning_summary else None
        observation = self.observe(credential)
        session_sequence = self.history.sequence
        legal_tools = set(observation["legal_tools"])
        normalized = call.tool.replace("-", "_")
        if actor_id != self.active_actor_id:
            result = self._terminate_for_violation("out_of_turn_action", actor_id, call)
            runtime_events: list[dict[str, Any]] = []
            visibility = ("trusted",)
            event_type = "tool-rejected"
        elif normalized not in legal_tools:
            result = self._terminate_for_violation("unauthorized_tool", actor_id, call)
            runtime_events = []
            visibility = ("trusted",)
            event_type = "tool-rejected"
        else:
            try:
                result, runtime_events, visibility, event_type = self._execute(actor_id, call)
            except AuthorizationDenied:
                result = self._terminate_for_violation("authorization_boundary", actor_id, call)
                runtime_events = []
                visibility = ("trusted",)
                event_type = "tool-rejected"
            except (KeyError, TypeError, ValueError):
                result = ToolResult(call.call_id, False, "tool rejected", {"error": "malformed_payload"})
                runtime_events = []
                visibility = ("trusted",)
                event_type = "tool-rejected"
        event = self._append_event(
            actor_id=actor_id,
            event_type=event_type,
            visibility=visibility,
            payload={
                "call": call.to_mapping(),
                "result": result.to_mapping(),
                "observation_hash": digest_json(observation),
                "session_sequence_before": session_sequence,
                "session_sequence_after": self.history.sequence,
                "runtime_events": runtime_events,
                "session_history_hash": self.history.content_hash,
                "reasoning_summary": reasoning_summary,
            },
        )
        trajectory = TrajectoryStep(
            turn=self._steps + 1,
            arena_sequence=event.sequence,
            session_sequence=session_sequence,
            observation=observation,
            observation_hash=digest_json(observation),
            call=call,
            result=result,
            policy_receipt=policy_receipt,
            policy_usage=policy_usage,
            reasoning_summary=reasoning_summary,
        )
        self._trajectory_steps[actor_id].append(trajectory)
        self._steps += 1
        if not self.done and self._steps >= self.config.max_steps:
            self._termination_reason = "step_budget_exhausted"
            self._append_event(
                actor_id="system",
                event_type="episode-terminated",
                visibility=("public",),
                payload={"reason": self._termination_reason},
            )
        if not self.done:
            self._turn_index = (self._turn_index + 1) % len(self._schedule)
        return result

    def archive(self) -> EpisodeArchive:
        """Freeze the current episode into portable canonical bytes."""
        policies = {
            self._host_actor_id: ("host", self.lineup.host),
            **{
                self._seat_actor_ids[item.seat_id]: (f"seat:{item.seat_id}", item.policy)
                for item in self.lineup.seats
            },
        }
        trajectories = tuple(
            PolicyTrajectory(actor_id, policies[actor_id][0], policies[actor_id][1], tuple(steps))
            for actor_id, steps in sorted(self._trajectory_steps.items())
        )
        state_hash = digest_json(replay(self.release, self.history))
        return EpisodeArchive(
            self.episode_id,
            self.release.release_id,
            self.episode_seed,
            self.config,
            self.lineup,
            self.version_locks,
            self.realized_seat_order,
            tuple(self._events),
            self.history,
            trajectories,
            tuple(self._violations),
            self._termination_reason,
            state_hash,
        )
