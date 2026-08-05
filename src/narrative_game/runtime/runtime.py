"""Pure Session Authority: command validation, events, replay, and projections."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any, Iterable, Mapping

from narrative_game.authoring import parse_game_definition
from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.narrative import available_evidence

from .model import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    CommandReceipt,
    SessionCommand,
    SessionEvent,
    SessionHistory,
    ViewerGrant,
)


RUNTIME_VERSION = "0.4.0"


class AuthorizationDenied(RuntimeError):
    """Opaque public authorization failure."""


@dataclass(frozen=True)
class CommandResult:
    history: SessionHistory
    receipt: CommandReceipt
    events: tuple[SessionEvent, ...]


def _game(release: GameRelease):
    return parse_game_definition(release.file("trusted/game.json").data)


def _event(
    *,
    session_id: str,
    release_id: str,
    sequence: int,
    previous_hash: str | None,
    command_id: str,
    authority: Mapping[str, Any],
    event_type: str,
    payload: Mapping[str, Any],
    phase_id: str,
) -> SessionEvent:
    provisional = SessionEvent(
        session_id=session_id,
        release_id=release_id,
        sequence=sequence,
        previous_hash=previous_hash,
        command_id=command_id,
        authority=json.loads(canonical_json(authority)),
        event_type=event_type,
        payload=json.loads(canonical_json(payload)),
        represented_phase_id=phase_id,
        event_hash="",
    )
    return replace(provisional, event_hash=digest_json(provisional.material()))


def _receipt(
    *,
    command_id: str,
    request_hash: str,
    accepted: bool,
    public_reason: str,
    trusted_reason: str,
    event_hashes: Iterable[str] = (),
) -> CommandReceipt:
    provisional = CommandReceipt(
        receipt_id="",
        command_id=command_id,
        request_hash=request_hash,
        accepted=accepted,
        public_reason=public_reason,
        trusted_reason=trusted_reason,
        event_hashes=tuple(event_hashes),
    )
    return replace(provisional, receipt_id=digest_json(provisional.material()))


def _request_hash(command: SessionCommand, auth: AuthorizationContext) -> str:
    return digest_json({"command": command.to_mapping(), "authorization": auth.to_mapping()})


def verify_history(history: SessionHistory) -> None:
    ordered = history.ordered_events
    previous = None
    for sequence, event in enumerate(ordered, 1):
        if event.sequence != sequence:
            raise ValueError(f"Event sequence is not contiguous at {sequence}")
        if event.previous_hash != previous:
            raise ValueError(f"Event previous hash is invalid at {sequence}")
        if event.release_id != history.release_id:
            raise ValueError(f"Event Release differs at {sequence}")
        if event.event_hash != digest_json(event.material()):
            raise ValueError(f"Event hash is invalid at {sequence}")
        previous = event.event_hash
    if history.fork_source is None:
        if history.prefix_events:
            raise ValueError("non-fork Session cannot carry prefix Events")
        if any(event.session_id != history.session_id for event in history.events):
            raise ValueError("Event names another Session")
    else:
        expected_sequence = int(history.fork_source["source_sequence"])
        expected_hash = history.fork_source["prefix_hash"]
        if len(history.prefix_events) != expected_sequence:
            raise ValueError("fork prefix length differs from its receipt")
        if not history.prefix_events or history.prefix_events[-1].event_hash != expected_hash:
            raise ValueError("fork prefix hash differs from its receipt")
        if any(event.session_id != history.session_id for event in history.events):
            raise ValueError("fork suffix Event names another Session")
    for receipt in history.receipts:
        if receipt.receipt_id != digest_json(receipt.material()):
            raise ValueError(f"Command Receipt is invalid: {receipt.command_id}")
        if receipt.accepted:
            if not receipt.event_hashes or any(item not in {event.event_hash for event in ordered} for item in receipt.event_hashes):
                raise ValueError(f"accepted Command Receipt has invalid Events: {receipt.command_id}")
        elif receipt.event_hashes:
            raise ValueError(f"rejected Command Receipt names Events: {receipt.command_id}")
    accepted_commands = {item.command_id for item in history.receipts if item.accepted}
    for event in history.events:
        if event.event_type != "session-created" and event.command_id not in accepted_commands:
            raise ValueError(f"Event lacks an accepted Command Receipt: {event.command_id}")


def create_session(
    *,
    release: GameRelease,
    session_id: str,
    mode: str,
    bindings: Iterable[ActorBinding],
    viewers: Iterable[ViewerGrant],
) -> SessionHistory:
    """Create one Session pinned to exactly one immutable Release."""
    if mode not in {"live", "simulation"}:
        raise ValueError("Session mode must be live or simulation")
    runtime_components = [
        item
        for item in release.manifest["component_lock"]["components"]
        if item["id"] == "runtime" and item["version"] == RUNTIME_VERSION
    ]
    if len(runtime_components) != 1:
        raise ValueError("Release does not pin this Session runtime")
    game = _game(release)
    binding_tuple = tuple(bindings)
    viewer_tuple = tuple(viewers)
    seats = {item.id for item in game.kernel.seats}
    if {item.seat_id for item in binding_tuple} != seats:
        raise ValueError("Session requires exactly one Actor Binding per Release Seat")
    if len({item.seat_id for item in binding_tuple}) != len(binding_tuple):
        raise ValueError("one Seat cannot have multiple controlling Actors")
    if len({item.actor.id for item in binding_tuple}) != len(binding_tuple):
        raise ValueError("one Actor cannot control multiple Seats in version one")
    if len({item.id for item in binding_tuple}) != len(binding_tuple):
        raise ValueError("Actor Binding IDs must be unique")
    if any(item.start_sequence != 1 for item in binding_tuple):
        raise ValueError("initial Actor Bindings begin at Session sequence one")
    if len({item.viewer_id for item in viewer_tuple}) != len(viewer_tuple):
        raise ValueError("Viewer grants must be unique")
    if mode == "live" and any(item.actor.kind != "human" for item in binding_tuple):
        raise ValueError("live Sessions support human Actors only")
    if not any(item.role == "host" for item in viewer_tuple):
        raise ValueError("Facilitated Investigation requires a host Viewer")
    opening = min(game.phases, key=lambda item: item.order)
    genesis = _event(
        session_id=session_id,
        release_id=release.release_id,
        sequence=1,
        previous_hash=None,
        command_id=f"system:create:{session_id}",
        authority={"kind": "system", "principal_id": "session-authority"},
        event_type="session-created",
        payload={
            "mode": mode,
            "bindings": [item.to_mapping() for item in sorted(binding_tuple, key=lambda x: x.seat_id)],
            "viewers": [item.to_mapping() for item in sorted(viewer_tuple, key=lambda x: x.viewer_id)],
        },
        phase_id=opening.id,
    )
    history = SessionHistory(
        session_id=session_id,
        release_id=release.release_id,
        mode=mode,
        fork_source=None,
        prefix_events=(),
        events=(genesis,),
        receipts=(),
    )
    verify_history(history)
    return history


def _initial_state(history: SessionHistory) -> dict[str, Any]:
    return {
        "session_id": history.session_id,
        "release_id": history.release_id,
        "mode": history.mode,
        "status": "uninitialized",
        "phase_id": None,
        "sequence": 0,
        "event_head": None,
        "bindings": {},
        "binding_history": [],
        "viewers": {},
        "disclosures": {},
        "private_notes": {},
        "hint_requests": [],
        "evidence_requests": [],
        "public_claims": [],
        "interventions": [],
        "submissions": [],
        "resolution": None,
    }


def _reduce(state: dict[str, Any], event: SessionEvent) -> None:
    payload = event.payload
    if event.event_type == "session-created":
        state["status"] = "created"
        for binding in payload["bindings"]:
            state["bindings"][binding["seat_id"]] = {**binding, "active": True}
            state["binding_history"].append({**binding, "active": True})
            state["disclosures"][binding["seat_id"]] = []
        state["viewers"] = {item["viewer_id"]: item["role"] for item in payload["viewers"]}
    elif event.event_type == "session-opened":
        state["status"] = "active"
        for disclosure in payload["disclosures"]:
            resources = state["disclosures"][disclosure["seat_id"]]
            if disclosure["resource_id"] not in resources:
                resources.append(disclosure["resource_id"])
    elif event.event_type in {
        "resource-disclosed",
        "intervention-delivered",
        "exceptional-intervention-recorded",
    }:
        for disclosure in payload["disclosures"]:
            resources = state["disclosures"][disclosure["seat_id"]]
            if disclosure["resource_id"] not in resources:
                resources.append(disclosure["resource_id"])
        if event.event_type in {
            "intervention-delivered",
            "exceptional-intervention-recorded",
        }:
            state["interventions"].append(
                {
                    "sequence": event.sequence,
                    "kind": (
                        "planned"
                        if event.event_type == "intervention-delivered"
                        else "exceptional"
                    ),
                    "intervention_id": payload.get("intervention_id"),
                    "reason": payload.get("reason"),
                }
            )
    elif event.event_type == "hint-requested":
        state["hint_requests"].append(
            {"sequence": event.sequence, "seat_id": payload["seat_id"], "request": payload["request"]}
        )
    elif event.event_type == "evidence-requested":
        state["evidence_requests"].append(
            {
                "sequence": event.sequence,
                "seat_id": payload["seat_id"],
                "resource_id": payload["resource_id"],
            }
        )
    elif event.event_type == "claim-shared":
        state["public_claims"].append(
            {
                "sequence": event.sequence,
                "seat_id": payload["seat_id"],
                "proposition_id": payload["proposition_id"],
                "stance": payload["stance"],
            }
        )
    elif event.event_type == "phase-advanced":
        state["phase_id"] = payload["phase_id"]
    elif event.event_type == "resolution-submitted":
        state["submissions"].append({"sequence": event.sequence, **payload})
    elif event.event_type == "resolution-recorded":
        state["status"] = "resolved"
        state["resolution"] = {"sequence": event.sequence, **payload}
    elif event.event_type == "actor-replaced":
        old = state["bindings"][payload["seat_id"]]
        old["active"] = False
        replacement = {**payload["new_binding"], "active": True}
        state["bindings"][payload["seat_id"]] = replacement
        state["binding_history"].append(replacement)
    elif event.event_type == "private-note-added":
        state["private_notes"].setdefault(payload["actor_id"], []).append(payload["note"])
    state["phase_id"] = event.represented_phase_id
    state["sequence"] = event.sequence
    state["event_head"] = event.event_hash
    for resources in state["disclosures"].values():
        resources.sort()


def replay(release: GameRelease, history: SessionHistory) -> dict[str, Any]:
    if history.release_id != release.release_id:
        raise ValueError("Session is pinned to another Release")
    verify_history(history)
    state = _initial_state(history)
    for event in history.ordered_events:
        _reduce(state, event)
    return json.loads(canonical_json(state))


def _is_host(state: Mapping[str, Any], auth: AuthorizationContext) -> bool:
    return auth.kind == "viewer" and state["viewers"].get(auth.principal_id) == "host"


def _actor_binding(state: Mapping[str, Any], auth: AuthorizationContext) -> Mapping[str, Any] | None:
    if auth.kind != "actor" or auth.binding_id is None:
        return None
    return next(
        (
            binding
            for binding in state["bindings"].values()
            if binding["id"] == auth.binding_id
            and binding["actor"]["id"] == auth.principal_id
            and binding["active"]
        ),
        None,
    )


def _reject(
    history: SessionHistory,
    command: SessionCommand,
    auth: AuthorizationContext,
    trusted_reason: str,
) -> CommandResult:
    receipt = _receipt(
        command_id=command.command_id,
        request_hash=_request_hash(command, auth),
        accepted=False,
        public_reason="command rejected",
        trusted_reason=trusted_reason,
    )
    return CommandResult(
        history=replace(history, receipts=(*history.receipts, receipt)),
        receipt=receipt,
        events=(),
    )


def _disclosures(game, *, phase_id: str, audience: Iterable[str], resource_ids: Iterable[str], grade: str):
    phase_order = {item.id: item.order for item in game.phases}
    evidence = {item.resource_id: item.id for item in game.evidence}
    reveals = [item for item in game.reveals if phase_order[item.phase_id] <= phase_order[phase_id]]
    result = []
    for resource_id in resource_ids:
        evidence_id = evidence.get(resource_id)
        for seat_id in audience:
            if not any(
                item.evidence_id == evidence_id and seat_id in item.audience_seat_ids
                for item in reveals
            ):
                raise AuthorizationDenied("not authorized")
            result.append(
                {
                    "seat_id": seat_id,
                    "resource_id": resource_id,
                    "evidence_grade": grade,
                }
            )
    return result


def apply_command(
    release: GameRelease,
    history: SessionHistory,
    command: SessionCommand,
    auth: AuthorizationContext,
) -> CommandResult:
    """Accept one atomic Event or append only a trusted rejection receipt."""
    request_hash = _request_hash(command, auth)
    matching = next(
        (
            item
            for item in history.receipts
            if item.command_id == command.command_id and item.request_hash == request_hash
        ),
        None,
    )
    if matching is not None:
        return CommandResult(history=history, receipt=matching, events=())
    existing = next((item for item in history.receipts if item.command_id == command.command_id), None)
    if existing is not None:
        return _reject(history, command, auth, "idempotency key names another request")
    try:
        state = replay(release, history)
    except ValueError as exc:
        return _reject(history, command, auth, f"invalid Session history: {exc}")
    if command.session_id != history.session_id or command.release_id != history.release_id:
        return _reject(history, command, auth, "Session or Release identity mismatch")
    if command.expected_sequence != state["sequence"]:
        return _reject(history, command, auth, "stale expected Session sequence")
    host = _is_host(state, auth)
    binding = _actor_binding(state, auth)
    game = _game(release)
    phase_order = {item.id: item.order for item in game.phases}
    current_phase = state["phase_id"]
    payload: dict[str, Any]
    event_type: str

    try:
        if command.action == "open-session":
            if not host or state["status"] != "created":
                return _reject(history, command, auth, "host authority or created state required")
            opening = min(game.phases, key=lambda item: item.order)
            disclosures = []
            evidence = {item.id: item for item in game.evidence}
            for seat in game.kernel.seats:
                for evidence_id in available_evidence(game, seat_id=seat.id, phase_id=opening.id):
                    disclosures.append(
                        {
                            "seat_id": seat.id,
                            "resource_id": evidence[evidence_id].resource_id,
                            "evidence_grade": "runtime-enforced",
                        }
                    )
            event_type = "session-opened"
            payload = {"disclosures": disclosures}
        elif command.action == "request-hint":
            if binding is None or state["status"] != "active":
                return _reject(history, command, auth, "active Actor Binding required")
            event_type = "hint-requested"
            payload = {"seat_id": binding["seat_id"], "request": str(command.payload["request"])}
        elif command.action == "request-evidence":
            if binding is None or state["status"] != "active":
                return _reject(history, command, auth, "active Actor Binding required")
            resource_id = str(command.payload["resource_id"])
            if resource_id not in {item.id for item in game.kernel.resources}:
                return _reject(history, command, auth, "requested object is unavailable")
            event_type = "evidence-requested"
            payload = {"seat_id": binding["seat_id"], "resource_id": resource_id}
        elif command.action == "share-claim":
            if binding is None or state["status"] != "active":
                return _reject(history, command, auth, "active Actor Binding required")
            proposition_id = str(command.payload["proposition_id"])
            stance = str(command.payload["stance"])
            if proposition_id not in {item.id for item in game.propositions} or stance not in {
                "accepts",
                "rejects",
            }:
                return _reject(history, command, auth, "Claim is malformed or unavailable")
            event_type = "claim-shared"
            payload = {
                "seat_id": binding["seat_id"],
                "proposition_id": proposition_id,
                "stance": stance,
            }
        elif command.action == "advance-phase":
            if not host or state["status"] != "active":
                return _reject(history, command, auth, "active host authority required")
            target = str(command.payload["phase_id"])
            if target not in phase_order or phase_order[target] != phase_order[current_phase] + 1:
                return _reject(history, command, auth, "target is not the next Phase")
            event_type = "phase-advanced"
            payload = {"phase_id": target}
        elif command.action == "disclose-resource":
            if not host or state["status"] != "active":
                return _reject(history, command, auth, "active host authority required")
            grade = str(command.payload["evidence_grade"])
            if grade not in {"runtime-enforced", "host-witnessed", "actor-reported"}:
                return _reject(history, command, auth, "unsupported physical evidence grade")
            payload = {
                "disclosures": _disclosures(
                    game,
                    phase_id=current_phase,
                    audience=command.payload["audience_seat_ids"],
                    resource_ids=[str(command.payload["resource_id"])],
                    grade=grade,
                )
            }
            event_type = "resource-disclosed"
        elif command.action == "deliver-intervention":
            if not host or state["status"] != "active":
                return _reject(history, command, auth, "active host authority required")
            intervention_id = str(command.payload["intervention_id"])
            intervention = next(
                (item for item in game.interventions if item.id == intervention_id), None
            )
            if intervention is None or phase_order[intervention.phase_id] > phase_order[current_phase]:
                return _reject(history, command, auth, "Intervention is not available")
            evidence = {item.id: item for item in game.evidence}
            resources = [evidence[item].resource_id for item in intervention.evidence_ids]
            audiences = tuple(str(item) for item in command.payload["audience_seat_ids"])
            event_type = "intervention-delivered"
            payload = {
                "intervention_id": intervention_id,
                "reason": str(command.payload["reason"]),
                "disclosures": _disclosures(
                    game,
                    phase_id=current_phase,
                    audience=audiences,
                    resource_ids=resources,
                    grade="runtime-enforced",
                ),
            }
        elif command.action == "record-exceptional-intervention":
            if not host or state["status"] != "active":
                return _reject(history, command, auth, "active host authority required")
            audiences = tuple(str(item) for item in command.payload["audience_seat_ids"])
            if not audiences or not set(audiences) <= set(state["bindings"]):
                return _reject(history, command, auth, "exceptional audience is unavailable")
            resources = tuple(str(item) for item in command.payload.get("resource_ids", []))
            event_type = "exceptional-intervention-recorded"
            payload = {
                "reason": str(command.payload["reason"]),
                "materialized_content": str(command.payload["materialized_content"]),
                "audience_seat_ids": list(audiences),
                "affected_object_ids": sorted(
                    str(item) for item in command.payload.get("affected_object_ids", [])
                ),
                "disclosures": _disclosures(
                    game,
                    phase_id=current_phase,
                    audience=audiences,
                    resource_ids=resources,
                    grade="host-witnessed",
                ),
            }
        elif command.action == "submit-resolution":
            if binding is None or state["status"] != "active":
                return _reject(history, command, auth, "active Actor Binding required")
            if phase_order[current_phase] < phase_order[game.resolution.phase_id]:
                return _reject(history, command, auth, "Resolution is not open")
            hypothesis_id = str(command.payload["hypothesis_id"])
            proof_path_id = str(command.payload["proof_path_id"])
            if hypothesis_id not in {item.id for item in game.hypotheses} or proof_path_id not in {
                item.id for item in game.proof_paths
            }:
                return _reject(history, command, auth, "submitted objects are unavailable")
            event_type = "resolution-submitted"
            payload = {
                "seat_id": binding["seat_id"],
                "hypothesis_id": hypothesis_id,
                "proof_path_id": proof_path_id,
            }
        elif command.action == "record-resolution":
            if not host or state["status"] != "active":
                return _reject(history, command, auth, "active host authority required")
            sequence = int(command.payload["submission_sequence"])
            submission = next(
                (
                    item
                    for item in history.ordered_events
                    if item.sequence == sequence and item.event_type == "resolution-submitted"
                ),
                None,
            )
            if submission is None:
                return _reject(history, command, auth, "submission does not exist")
            correct = (
                submission.payload["hypothesis_id"] == game.resolution.correct_hypothesis_id
                and submission.payload["proof_path_id"]
                in game.resolution.acceptable_proof_path_ids
            )
            event_type = "resolution-recorded"
            payload = {"submission_sequence": sequence, "correct": correct}
        elif command.action == "replace-actor":
            if not host:
                return _reject(history, command, auth, "host authority required")
            seat_id = str(command.payload["seat_id"])
            if seat_id not in state["bindings"]:
                return _reject(history, command, auth, "Seat is unavailable")
            actor_value = command.payload["actor"]
            actor = Actor(
                id=str(actor_value["id"]),
                kind=str(actor_value["kind"]),
                label=str(actor_value["label"]),
            )
            if history.mode == "live" and actor.kind != "human":
                return _reject(history, command, auth, "live model occupancy is unsupported")
            if any(
                item["actor"]["id"] == actor.id and item["seat_id"] != seat_id
                for item in state["bindings"].values()
            ):
                return _reject(history, command, auth, "Actor already controls another Seat")
            if any(
                item["id"] == str(command.payload["binding_id"])
                for item in state["binding_history"]
            ):
                return _reject(history, command, auth, "Actor Binding ID already exists")
            new_binding = ActorBinding(
                id=str(command.payload["binding_id"]),
                actor=actor,
                seat_id=seat_id,
                start_sequence=state["sequence"] + 1,
            )
            event_type = "actor-replaced"
            payload = {"seat_id": seat_id, "new_binding": new_binding.to_mapping()}
        elif command.action == "add-private-note":
            if binding is None:
                return _reject(history, command, auth, "active Actor Binding required")
            event_type = "private-note-added"
            payload = {"actor_id": auth.principal_id, "note": str(command.payload["note"])}
        else:
            return _reject(history, command, auth, "unknown Command action")
    except (KeyError, TypeError, ValueError, AuthorizationDenied):
        return _reject(history, command, auth, "malformed, unavailable, or unauthorized payload")

    next_phase = payload.get("phase_id", current_phase)
    accepted_event = _event(
        session_id=history.session_id,
        release_id=history.release_id,
        sequence=history.sequence + 1,
        previous_hash=history.event_head,
        command_id=command.command_id,
        authority=auth.to_mapping(),
        event_type=event_type,
        payload=payload,
        phase_id=next_phase,
    )
    receipt = _receipt(
        command_id=command.command_id,
        request_hash=request_hash,
        accepted=True,
        public_reason="accepted",
        trusted_reason="accepted",
        event_hashes=[accepted_event.event_hash],
    )
    updated = replace(
        history,
        events=(*history.events, accepted_event),
        receipts=(*history.receipts, receipt),
    )
    verify_history(updated)
    return CommandResult(history=updated, receipt=receipt, events=(accepted_event,))


def seat_snapshot(
    release: GameRelease, history: SessionHistory, auth: AuthorizationContext
) -> dict[str, Any]:
    state = replay(release, history)
    binding = _actor_binding(state, auth)
    if binding is None:
        raise AuthorizationDenied("not authorized")
    seat_id = binding["seat_id"]
    baseline = json.loads(release.file(f"projections/seats/{seat_id}.json").data)
    materials = {item["resource_id"]: item for item in release.manifest["materials"]}
    visible_events = []
    for event in history.ordered_events:
        if event.event_type in {"phase-advanced", "resolution-recorded", "claim-shared"}:
            visible_events.append({"sequence": event.sequence, "event_type": event.event_type})
        elif event.event_type == "exceptional-intervention-recorded" and seat_id in event.payload[
            "audience_seat_ids"
        ]:
            visible_events.append(
                {
                    "sequence": event.sequence,
                    "event_type": event.event_type,
                    "materialized_content": event.payload["materialized_content"],
                }
            )
        elif event.event_type in {"resource-disclosed", "intervention-delivered"} and any(
            item["seat_id"] == seat_id for item in event.payload["disclosures"]
        ):
            visible_events.append({"sequence": event.sequence, "event_type": event.event_type})
    return {
        "schema_version": "0.4",
        "session_id": history.session_id,
        "release_id": history.release_id,
        "revision": state["sequence"],
        "status": state["status"],
        "phase_id": state["phase_id"],
        "seat": baseline["seat"],
        "character": baseline["character"],
        "resources": [
            {
                "resource_id": resource_id,
                "media_type": materials[resource_id]["media_type"],
                "content_hash": materials[resource_id]["content_hash"],
            }
            for resource_id in state["disclosures"][seat_id]
        ],
        "private_notes": list(state["private_notes"].get(auth.principal_id, [])),
        "visible_events": visible_events,
        "resolution_prompt": baseline["resolution_prompt"],
        "allowed_actions": (
            []
            if state["status"] != "active"
            else [
                "request-evidence",
                "request-hint",
                "share-claim",
                *(
                    ["submit-resolution"]
                    if state["phase_id"]
                    == json.loads(release.file("trusted/game.json").data)["narrative"]["resolution"]["phase_id"]
                    else []
                ),
            ]
        ),
    }


def host_snapshot(
    release: GameRelease, history: SessionHistory, auth: AuthorizationContext
) -> dict[str, Any]:
    state = replay(release, history)
    if not _is_host(state, auth):
        raise AuthorizationDenied("not authorized")
    return {
        "schema_version": "0.4",
        "authority": "trusted-host",
        "state": state,
        "game": json.loads(release.file("projections/host.json").data),
    }


def retrieve_resource(
    release: GameRelease,
    history: SessionHistory,
    auth: AuthorizationContext,
    resource_id: str,
) -> bytes:
    state = replay(release, history)
    if _is_host(state, auth):
        return release.file(f"materials/{resource_id}").data
    binding = _actor_binding(state, auth)
    if binding is None or resource_id not in state["disclosures"][binding["seat_id"]]:
        raise AuthorizationDenied("not authorized")
    return release.file(f"materials/{resource_id}").data


def fork_session(
    source: SessionHistory, *, session_id: str, at_sequence: int
) -> SessionHistory:
    """Create an isolated simulation arm over one verified immutable prefix."""
    verify_history(source)
    if at_sequence < 1 or at_sequence > source.sequence:
        raise ValueError("fork sequence is outside the source history")
    prefix = source.ordered_events[:at_sequence]
    fork = SessionHistory(
        session_id=session_id,
        release_id=source.release_id,
        mode="simulation",
        fork_source={
            "source_session_id": source.session_id,
            "source_sequence": at_sequence,
            "prefix_hash": prefix[-1].event_hash,
        },
        prefix_events=prefix,
        events=(),
        receipts=(),
    )
    verify_history(fork)
    return fork
