"""Atomic append-only, independently verifiable Workspace journals."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from narrative_game.contracts.canonical import canonical_json, digest_json

from .io import atomic_write, file_mutex


class ConcurrencyConflict(RuntimeError):
    """The caller targeted a head that is no longer current."""


class IdempotencyConflict(RuntimeError):
    """An idempotency key was reused for a different operation."""


_UNSET = object()


class Journal:
    """A logical append-only hash chain committed by atomic file replacement."""

    schema_version = "0.1"

    def __init__(self, path: str | Path, *, journal_id: str):
        self.path = Path(path)
        self.journal_id = journal_id
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events = []
        for number, line in enumerate(self.path.read_bytes().splitlines(), 1):
            if not line.strip():
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid {self.journal_id} journal line {number}") from exc
        return events

    def head(self) -> str | None:
        events = self.read()
        return events[-1]["event_hash"] if events else None

    def event_for_key(self, idempotency_key: str) -> dict[str, Any] | None:
        return next(
            (event for event in self.read() if event["idempotency_key"] == idempotency_key),
            None,
        )

    def append(
        self,
        event_type: str,
        *,
        actor: str,
        payload: dict[str, Any],
        object_refs: list[str] | tuple[str, ...] = (),
        idempotency_key: str,
        expected_head: str | None | object = _UNSET,
    ) -> dict[str, Any]:
        if not event_type.strip() or not actor.strip() or not idempotency_key.strip():
            raise ValueError("event_type, actor, and idempotency_key are required")
        intent = {
            "event_type": event_type,
            "actor": actor,
            "payload": payload,
            "object_refs": sorted(set(object_refs)),
            "idempotency_key": idempotency_key,
        }
        with file_mutex(self.lock_path):
            events = self.read()
            existing = next(
                (event for event in events if event["idempotency_key"] == idempotency_key),
                None,
            )
            if existing is not None:
                if any(existing[key] != value for key, value in intent.items()):
                    raise IdempotencyConflict(
                        f"idempotency key {idempotency_key!r} names another operation"
                    )
                return existing
            head = events[-1]["event_hash"] if events else None
            if expected_head is not _UNSET and expected_head != head:
                raise ConcurrencyConflict(
                    f"journal head changed: expected {expected_head!r}, found {head!r}"
                )
            event = {
                "schema_version": self.schema_version,
                "journal_id": self.journal_id,
                "sequence": len(events) + 1,
                "previous_hash": head,
                **intent,
            }
            event["event_hash"] = digest_json(event)
            encoded = b"".join(canonical_json(item) + b"\n" for item in [*events, event])
            atomic_write(self.path, encoded)
            return event

    def verify(self) -> tuple[bool, list[str]]:
        failures = []
        try:
            events = self.read()
        except (OSError, ValueError) as exc:
            return False, [str(exc)]
        previous = None
        seen_keys = set()
        for sequence, event in enumerate(events, 1):
            if event.get("schema_version") != self.schema_version:
                failures.append(f"event {sequence} has unsupported schema")
            if event.get("journal_id") != self.journal_id:
                failures.append(f"event {sequence} names another journal")
            if event.get("sequence") != sequence:
                failures.append(f"event {sequence} has wrong sequence")
            if event.get("previous_hash") != previous:
                failures.append(f"event {sequence} has wrong previous hash")
            claimed = event.get("event_hash")
            material = {key: value for key, value in event.items() if key != "event_hash"}
            if claimed != digest_json(material):
                failures.append(f"event {sequence} hash is invalid")
            key = event.get("idempotency_key")
            if key in seen_keys:
                failures.append(f"event {sequence} repeats an idempotency key")
            seen_keys.add(key)
            previous = claimed
        return not failures, failures
