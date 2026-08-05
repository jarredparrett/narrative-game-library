"""Portable immutable Session contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class Actor:
    id: str
    kind: str
    label: str

    def to_mapping(self) -> dict[str, str]:
        return {"id": self.id, "kind": self.kind, "label": self.label}


@dataclass(frozen=True)
class ActorBinding:
    id: str
    actor: Actor
    seat_id: str
    start_sequence: int

    def to_mapping(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "actor": self.actor.to_mapping(),
            "seat_id": self.seat_id,
            "start_sequence": self.start_sequence,
        }


@dataclass(frozen=True)
class ViewerGrant:
    viewer_id: str
    role: str

    def to_mapping(self) -> dict[str, str]:
        return {"viewer_id": self.viewer_id, "role": self.role}


@dataclass(frozen=True)
class AuthorizationContext:
    kind: str
    principal_id: str
    binding_id: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "principal_id": self.principal_id,
            "binding_id": self.binding_id,
        }


@dataclass(frozen=True)
class SessionCommand:
    command_id: str
    session_id: str
    release_id: str
    expected_sequence: int
    action: str
    payload: Mapping[str, Any]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "0.4",
            "command_id": self.command_id,
            "session_id": self.session_id,
            "release_id": self.release_id,
            "expected_sequence": self.expected_sequence,
            "action": self.action,
            "payload": _copy(self.payload),
        }


@dataclass(frozen=True)
class SessionEvent:
    session_id: str
    release_id: str
    sequence: int
    previous_hash: str | None
    command_id: str
    authority: Mapping[str, Any]
    event_type: str
    payload: Mapping[str, Any]
    represented_phase_id: str
    event_hash: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.4",
            "event_type_version": "1.0.0",
            "session_id": self.session_id,
            "release_id": self.release_id,
            "sequence": self.sequence,
            "previous_hash": self.previous_hash,
            "command_id": self.command_id,
            "authority": _copy(self.authority),
            "event_type": self.event_type,
            "payload": _copy(self.payload),
            "represented_phase_id": self.represented_phase_id,
        }

    def to_mapping(self) -> dict[str, Any]:
        return {**self.material(), "event_hash": self.event_hash}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "SessionEvent":
        return cls(
            session_id=str(value["session_id"]),
            release_id=str(value["release_id"]),
            sequence=int(value["sequence"]),
            previous_hash=value.get("previous_hash"),
            command_id=str(value["command_id"]),
            authority=_copy(value["authority"]),
            event_type=str(value["event_type"]),
            payload=_copy(value["payload"]),
            represented_phase_id=str(value["represented_phase_id"]),
            event_hash=str(value["event_hash"]),
        )


@dataclass(frozen=True)
class CommandReceipt:
    receipt_id: str
    command_id: str
    request_hash: str
    accepted: bool
    public_reason: str
    trusted_reason: str
    event_hashes: tuple[str, ...]

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.4",
            "command_id": self.command_id,
            "request_hash": self.request_hash,
            "accepted": self.accepted,
            "public_reason": self.public_reason,
            "trusted_reason": self.trusted_reason,
            "event_hashes": list(self.event_hashes),
        }

    def to_mapping(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.material()}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CommandReceipt":
        return cls(
            receipt_id=str(value["receipt_id"]),
            command_id=str(value["command_id"]),
            request_hash=str(value["request_hash"]),
            accepted=bool(value["accepted"]),
            public_reason=str(value["public_reason"]),
            trusted_reason=str(value["trusted_reason"]),
            event_hashes=tuple(str(item) for item in value["event_hashes"]),
        )


@dataclass(frozen=True)
class SessionHistory:
    session_id: str
    release_id: str
    mode: str
    fork_source: Mapping[str, Any] | None
    prefix_events: tuple[SessionEvent, ...]
    events: tuple[SessionEvent, ...]
    receipts: tuple[CommandReceipt, ...]

    @property
    def ordered_events(self) -> tuple[SessionEvent, ...]:
        return (*self.prefix_events, *self.events)

    @property
    def sequence(self) -> int:
        return len(self.ordered_events)

    @property
    def event_head(self) -> str | None:
        return self.ordered_events[-1].event_hash if self.ordered_events else None

    @property
    def content_hash(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": "0.4",
            "session_id": self.session_id,
            "release_id": self.release_id,
            "mode": self.mode,
            "fork_source": _copy(self.fork_source),
            "prefix_events": [item.to_mapping() for item in self.prefix_events],
            "events": [item.to_mapping() for item in self.events],
            "receipts": [item.to_mapping() for item in self.receipts],
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_mapping())

    @classmethod
    def from_bytes(cls, value: bytes) -> "SessionHistory":
        parsed = json.loads(value)
        return cls(
            session_id=str(parsed["session_id"]),
            release_id=str(parsed["release_id"]),
            mode=str(parsed["mode"]),
            fork_source=_copy(parsed.get("fork_source")),
            prefix_events=tuple(SessionEvent.from_mapping(item) for item in parsed["prefix_events"]),
            events=tuple(SessionEvent.from_mapping(item) for item in parsed["events"]),
            receipts=tuple(CommandReceipt.from_mapping(item) for item in parsed["receipts"]),
        )
