"""Deterministic integrity gates and reward vector for arena episodes."""

from __future__ import annotations

import base64
from collections import Counter
from typing import Any

from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import digest_json
from narrative_game.runtime import (
    AuthorizationContext,
    SessionHistory,
    host_snapshot,
    replay,
    retrieve_resource,
)
from narrative_game.runtime.runtime import verify_history

from .model import EpisodeArchive, GateResult, RewardReport
from .environment import _seat_arena_snapshot


def _history_at(history: SessionHistory, sequence: int) -> SessionHistory:
    if history.prefix_events:
        raise ValueError("arena episodes may not use forked Session histories")
    events = history.events[:sequence]
    event_hashes = {item.event_hash for item in events}
    receipts = tuple(
        item
        for item in history.receipts
        if item.accepted and set(item.event_hashes) <= event_hashes
    )
    result = SessionHistory(
        history.session_id,
        history.release_id,
        history.mode,
        None,
        (),
        events,
        receipts,
    )
    verify_history(result)
    return result


def _auth_for(archive: EpisodeArchive, actor_id: str) -> AuthorizationContext:
    genesis = archive.session_history.events[0]
    if actor_id.startswith("host:"):
        return AuthorizationContext("viewer", actor_id)
    binding = next(
        item for item in genesis.payload["bindings"] if item["actor"]["id"] == actor_id
    )
    return AuthorizationContext("actor", actor_id, str(binding["id"]))


def _visible_dialogue(
    archive: EpisodeArchive, actor_id: str, before_sequence: int
) -> list[dict[str, Any]]:
    dialogue = []
    for event in archive.events:
        if event.sequence >= before_sequence:
            break
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


def _trace_findings(release: GameRelease, archive: EpisodeArchive) -> list[str]:
    findings: list[str] = []
    if archive.release_id != release.release_id or archive.session_history.release_id != release.release_id:
        findings.append("release identity mismatch")
    expected_episode = digest_json(
        {
            "kind": "narrative-multi-agent-episode-v1",
            "release_id": archive.release_id,
            "episode_seed": archive.episode_seed,
            "lineup": archive.lineup.to_mapping(),
            "config": archive.config.to_mapping(),
        }
    )
    if archive.episode_id != expected_episode:
        findings.append("episode identity mismatch")
    previous = None
    for sequence, event in enumerate(archive.events, 1):
        if event.sequence != sequence:
            findings.append(f"arena sequence mismatch at {sequence}")
        if event.previous_hash != previous:
            findings.append(f"arena previous hash mismatch at {sequence}")
        if event.event_hash != digest_json(event.material()):
            findings.append(f"arena event hash mismatch at {sequence}")
        if event.session_id != archive.session_history.session_id:
            findings.append(f"arena Session mismatch at {sequence}")
        if event.release_id != archive.release_id:
            findings.append(f"arena Release mismatch at {sequence}")
        previous = event.event_hash
    try:
        verify_history(archive.session_history)
        state = replay(release, archive.session_history)
        if digest_json(state) != archive.terminal_state_hash:
            findings.append("terminal state hash mismatch")
    except ValueError as exc:
        findings.append(f"Session replay failed: {exc}")
    runtime_events = {
        item.event_hash: item.to_mapping() for item in archive.session_history.events
    }
    for event in archive.events:
        if event.event_type in {"said", "host-broadcast"} and event.visibility != ("public",):
            findings.append(f"public dialogue has invalid visibility at {event.sequence}")
        if event.event_type == "private-message":
            if len(event.visibility) != 2 or event.actor_id not in event.visibility:
                findings.append(f"private message has invalid visibility at {event.sequence}")
        for runtime_event in event.payload.get("runtime_events", []):
            expected = runtime_events.get(runtime_event.get("event_hash"))
            if expected != runtime_event:
                findings.append(f"arena event {event.sequence} names an invalid runtime Event")
    arena_calls = {
        event.payload["call"]["call_id"]: event
        for event in archive.events
        if isinstance(event.payload.get("call"), dict)
    }
    seen_receipts: set[str] = set()
    actors = set()
    for trajectory in archive.trajectories:
        if trajectory.actor_id in actors:
            findings.append(f"duplicate trajectory for {trajectory.actor_id}")
        actors.add(trajectory.actor_id)
        if trajectory.policy.context_id in {
            item.policy.context_id
            for item in archive.lineup.seats
            if item.policy.policy_id != trajectory.policy.policy_id
        }:
            findings.append(f"shared context in trajectory {trajectory.actor_id}")
        for step in trajectory.steps:
            if step.observation_hash != digest_json(step.observation):
                findings.append(f"observation hash mismatch for {step.call.call_id}")
            arena_event = arena_calls.get(step.call.call_id)
            if arena_event is None or arena_event.actor_id != trajectory.actor_id:
                findings.append(f"trajectory call lacks matching arena Event: {step.call.call_id}")
            elif (
                arena_event.payload.get("call") != step.call.to_mapping()
                or arena_event.payload.get("result") != step.result.to_mapping()
                or arena_event.payload.get("observation_hash") != step.observation_hash
            ):
                findings.append(f"trajectory differs from arena Event: {step.call.call_id}")
            try:
                prefix = _history_at(archive.session_history, step.session_sequence)
                auth = _auth_for(archive, trajectory.actor_id)
                expected_game: dict[str, Any]
                if trajectory.role == "host":
                    expected_game = host_snapshot(release, prefix, auth)
                    expected_resources: list[dict[str, str]] = []
                else:
                    expected_game, expected_resources = _seat_arena_snapshot(
                        release, prefix, auth
                    )
                if step.observation.get("game") != expected_game:
                    findings.append(f"unauthorized or stale observation: {step.call.call_id}")
                if step.observation.get("requestable_resources") != expected_resources:
                    findings.append(
                        f"requestable resource projection differs: {step.call.call_id}"
                    )
                if step.observation.get("dialogue") != _visible_dialogue(
                    archive, trajectory.actor_id, step.arena_sequence
                ):
                    findings.append(f"unauthorized dialogue observation: {step.call.call_id}")
                if step.observation.get("actor_id") != trajectory.actor_id:
                    findings.append(f"observation names another actor: {step.call.call_id}")
                prior = [
                    {
                        "turn": item.turn,
                        "call": item.call.to_mapping(),
                        "result": item.result.to_mapping(),
                    }
                    for item in trajectory.steps
                    if item.turn < step.turn
                ]
                if step.observation.get("own_prior_actions") != prior:
                    findings.append(f"prior-action projection differs: {step.call.call_id}")
                if step.call.tool.replace("-", "_") == "inspect_evidence" and step.result.accepted:
                    resource_id = str(step.call.arguments["resource_id"])
                    expected_data = retrieve_resource(release, prefix, auth, resource_id)
                    if step.result.content.get("content_base64") != base64.b64encode(
                        expected_data
                    ).decode("ascii"):
                        findings.append(f"evidence bytes differ for {step.call.call_id}")
            except (KeyError, StopIteration, ValueError):
                findings.append(f"observation cannot be replayed: {step.call.call_id}")
            if step.policy_receipt is not None:
                if step.policy_receipt.receipt_id in seen_receipts:
                    findings.append(f"token receipt reused: {step.policy_receipt.receipt_id}")
                seen_receipts.add(step.policy_receipt.receipt_id)
    expected_actors = {
        f"seat:{item.seat_id}:{item.policy.policy_id}" for item in archive.lineup.seats
    } | {f"host:{archive.lineup.host.policy_id}"}
    if actors != expected_actors:
        findings.append("archive does not contain exactly one trajectory per role")
    return sorted(set(findings))


def verify_episode(release: GameRelease, archive: EpisodeArchive) -> tuple[str, ...]:
    """Return exact replay or isolation findings; an empty tuple is verified."""
    return tuple(_trace_findings(release, archive))


def evaluate_episode(release: GameRelease, archive: EpisodeArchive) -> RewardReport:
    """Apply hard-zero gates and preserve team and per-policy reward dimensions."""
    findings = verify_episode(release, archive)
    state = replay(release, archive.session_history) if not findings else None
    resolution = state.get("resolution") if state is not None else None
    submissions = state.get("submissions", []) if state is not None else []
    proof_bearing = bool(
        resolution
        and submissions
        and resolution["submission_sequence"] in {item["sequence"] for item in submissions}
    )
    gates = (
        GateResult("trace_valid", not findings, "; ".join(findings) or "hash chains replay"),
        GateResult(
            "authorization_integrity",
            not archive.violations,
            ", ".join(archive.violations) or "no unauthorized tool or turn was accepted",
        ),
        GateResult(
            "canonical_evidence_only",
            not any(item == "fabricated_canonical_evidence" for item in archive.violations),
            "dialogue never mutates canonical evidence",
        ),
        GateResult(
            "proof_bearing_resolution",
            proof_bearing,
            "terminal resolution names a recorded hypothesis and licensed proof path"
            if proof_bearing
            else "no proof-bearing resolution was recorded",
        ),
        GateResult(
            "mandatory_safety",
            archive.termination_reason != "safety_failure",
            "no safety termination" if archive.termination_reason != "safety_failure" else "safety failed",
        ),
        GateResult("environment_untampered", not findings, "deterministic verifier owns scoring"),
    )
    seat_trajectories = [item for item in archive.trajectories if item.role.startswith("seat:")]
    counts = {item.actor_id: len(item.steps) for item in seat_trajectories}
    active = sum(1 for value in counts.values() if value > 0)
    participation = active / len(seat_trajectories) if seat_trajectories else 0.0
    public_speakers = {
        event.actor_id
        for event in archive.events
        if event.event_type in {"said", "host-broadcast"}
    }
    exchange = min(1.0, len(public_speakers) / max(1, len(seat_trajectories)))
    interventions = len(state.get("interventions", [])) if state is not None else 0
    all_steps = [step for item in archive.trajectories for step in item.steps]
    attributed = sum(1 for item in all_steps if item.policy_receipt is not None)
    token_attribution = attributed / len(all_steps) if all_steps else 0.0
    correct = 1.0 if resolution and resolution.get("correct") else 0.0
    completed = 1.0 if archive.termination_reason in {
        "accepted_resolution", "incorrect_resolution", "host_end"
    } else 0.0
    efficiency = max(0.0, 1.0 - (len(all_steps) / archive.config.max_steps))
    team = {
        "correct_resolution": correct,
        "proof_path_coverage": 1.0 if proof_bearing and correct else 0.0,
        "balanced_participation": participation,
        "information_exchange": exchange,
        "low_recovery_dependence": 1.0 / (1.0 + interventions),
        "pacing_completion": completed,
        "tool_efficiency": efficiency,
        "token_attribution": token_attribution,
    }
    character_states = state.get("character_states", {}) if state is not None else {}
    per_actor: dict[str, dict[str, float]] = {}
    for trajectory in seat_trajectories:
        seat_id = trajectory.role.split(":", 1)[1]
        statuses = character_states.get(seat_id, {}).get("objective_statuses", {})
        progressed = sum(value in {"advanced", "satisfied"} for value in statuses.values())
        objective_progress = progressed / len(statuses) if statuses else 0.0
        receipts = [item.policy_receipt for item in trajectory.steps]
        per_actor[trajectory.actor_id] = {
            "participation": 1.0 if trajectory.steps else 0.0,
            "objective_progress": objective_progress,
            "authorized_knowledge": 1.0 if not archive.violations else 0.0,
            "token_attribution": (
                sum(item is not None for item in receipts) / len(receipts) if receipts else 0.0
            ),
        }
    aggregate = sum(team.values()) / len(team)
    if not all(item.passed for item in gates):
        aggregate = 0.0
    return RewardReport(
        archive.config.reward_version,
        round(aggregate, 6),
        gates,
        team,
        per_actor,
    )
