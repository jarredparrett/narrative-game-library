"""Typed evidence, checkpoints, manifests, and portable claim capsules."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import PurePosixPath
from typing import Any, Mapping
import zipfile

from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json

from .store import ObjectStore, refs_in


JOURNAL_IDS = {
    "lineage": "experiment-lineage",
    "operational": "operational-audit",
    "climb": "agentic-climb",
    "analysis": "difficulty-analysis",
    "qualification": "game-qualification",
    "access": "evidence-access",
}


def typed_evidence_object(
    *,
    object_kind: str,
    object_schema: str,
    value: Mapping[str, Any],
    producer: str,
    verifier: str,
) -> dict[str, Any]:
    if not all(item.strip() for item in (object_kind, object_schema, producer, verifier)):
        raise ValueError("typed evidence identity, producer, and verifier are required")
    return {
        "schema_version": "evidence-object.1",
        "kind": "evidence_object",
        "object_kind": object_kind,
        "object_schema": object_schema,
        "producer": producer,
        "verifier": verifier,
        "value": json.loads(canonical_json(value)),
    }


def transitive_object_closure(store: ObjectStore, roots: tuple[str, ...]) -> tuple[str, ...]:
    pending = list(roots)
    closure = set()
    while pending:
        ref = pending.pop()
        if ref in closure:
            continue
        if not store.verify(ref):
            raise ValueError(f"missing or corrupt evidence object: {ref}")
        closure.add(ref)
        try:
            pending.extend(refs_in(store.read_json(ref)))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    return tuple(sorted(closure))


@dataclass(frozen=True)
class WorkspaceCheckpoint:
    workspace_id: str
    journal_heads: Mapping[str, Mapping[str, Any]]
    schema_version: str = "workspace-checkpoint.1"

    def __post_init__(self) -> None:
        if set(self.journal_heads) != set(JOURNAL_IDS):
            raise ValueError("Checkpoint must pin every Workspace Journal")
        normalized = {}
        for name, expected_id in JOURNAL_IDS.items():
            value = self.journal_heads[name]
            if value.get("journal_id") != expected_id:
                raise ValueError(f"Checkpoint names another {name} Journal")
            sequence = int(value.get("sequence", -1))
            head = value.get("head")
            if sequence < 0 or (sequence == 0) != (head is None):
                raise ValueError(f"Checkpoint has incoherent {name} head")
            if head is not None and (
                not str(head).startswith("sha256:") or len(str(head)) != 71
            ):
                raise ValueError(f"Checkpoint has invalid {name} head identity")
            normalized[name] = {
                "journal_id": expected_id,
                "sequence": sequence,
                "head": head,
            }
        object.__setattr__(self, "journal_heads", normalized)

    @property
    def checkpoint_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": "workspace_checkpoint",
            "workspace_id": self.workspace_id,
            "journal_heads": {
                key: dict(value) for key, value in sorted(self.journal_heads.items())
            },
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorkspaceCheckpoint":
        if value.get("kind") != "workspace_checkpoint":
            raise ValueError("object is not a Workspace Checkpoint")
        return cls(
            str(value["workspace_id"]),
            {str(key): dict(item) for key, item in value["journal_heads"].items()},
            str(value["schema_version"]),
        )


@dataclass(frozen=True)
class ClaimManifest:
    claim_id: str
    checkpoint_ref: str
    root_refs: tuple[str, ...]
    schema_refs: tuple[str, ...]
    verifier_refs: tuple[str, ...]
    object_refs: tuple[str, ...]
    schema_version: str = "claim-manifest.1"

    def __post_init__(self) -> None:
        if not self.claim_id.strip():
            raise ValueError("Claim Manifest identity is required")
        groups = {
            "root": self.root_refs,
            "schema": self.schema_refs,
            "verifier": self.verifier_refs,
            "object": self.object_refs,
        }
        for label, refs in groups.items():
            if not refs or tuple(sorted(set(refs))) != refs:
                raise ValueError(
                    f"Claim Manifest {label} refs must be non-empty and canonical"
                )
            for ref in refs:
                if not ref.startswith("sha256:") or len(ref) != 71:
                    raise ValueError(f"Claim Manifest has invalid {label} ref")
        if not self.checkpoint_ref.startswith("sha256:") or len(self.checkpoint_ref) != 71:
            raise ValueError("Claim Manifest has invalid Checkpoint ref")

    @property
    def manifest_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kind": "claim_manifest",
            "claim_id": self.claim_id,
            "checkpoint_ref": self.checkpoint_ref,
            "root_refs": list(self.root_refs),
            "schema_refs": list(self.schema_refs),
            "verifier_refs": list(self.verifier_refs),
            "object_refs": list(self.object_refs),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ClaimManifest":
        if value.get("kind") != "claim_manifest":
            raise ValueError("object is not a Claim Manifest")
        return cls(
            str(value["claim_id"]),
            str(value["checkpoint_ref"]),
            tuple(str(item) for item in value["root_refs"]),
            tuple(str(item) for item in value["schema_refs"]),
            tuple(str(item) for item in value["verifier_refs"]),
            tuple(str(item) for item in value["object_refs"]),
            str(value["schema_version"]),
        )


def journal_prefix(events: list[dict[str, Any]], head: str | None) -> list[dict[str, Any]]:
    if head is None:
        return []
    for index, event in enumerate(events):
        if event.get("event_hash") == head:
            return events[: index + 1]
    raise ValueError(f"Checkpoint head is absent from Journal: {head}")


def verify_journal_prefix(
    events: list[dict[str, Any]],
    *,
    journal_id: str,
    expected_head: str | None,
) -> tuple[str, ...]:
    findings = []
    previous = None
    seen_keys = set()
    for sequence, event in enumerate(events, 1):
        if event.get("schema_version") != "0.1":
            findings.append(f"{journal_id} event {sequence} has unsupported schema")
        if event.get("journal_id") != journal_id:
            findings.append(f"{journal_id} event {sequence} names another Journal")
        if event.get("sequence") != sequence:
            findings.append(f"{journal_id} event {sequence} has wrong sequence")
        if event.get("previous_hash") != previous:
            findings.append(f"{journal_id} event {sequence} has wrong previous hash")
        claimed = event.get("event_hash")
        material = {key: value for key, value in event.items() if key != "event_hash"}
        if claimed != digest_json(material):
            findings.append(f"{journal_id} event {sequence} hash is invalid")
        key = event.get("idempotency_key")
        if key in seen_keys:
            findings.append(f"{journal_id} event {sequence} repeats an idempotency key")
        seen_keys.add(key)
        previous = claimed
    if previous != expected_head:
        findings.append(f"{journal_id} prefix does not end at Checkpoint head")
    return tuple(findings)


def deterministic_zip(members: Mapping[str, bytes]) -> bytes:
    stream = BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_STORED) as archive:
        for path, data in sorted(members.items()):
            relative = PurePosixPath(path)
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe capsule member: {path}")
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o600 << 16
            archive.writestr(info, data)
    return stream.getvalue()


def capsule_members(value: bytes) -> dict[str, bytes]:
    result = {}
    with zipfile.ZipFile(BytesIO(value), "r") as archive:
        for info in archive.infolist():
            relative = PurePosixPath(info.filename)
            if relative.is_absolute() or ".." in relative.parts or info.is_dir():
                raise ValueError(f"unsafe capsule member: {info.filename}")
            if info.filename in result:
                raise ValueError(f"duplicate capsule member: {info.filename}")
            result[info.filename] = archive.read(info)
    return result


def verify_claim_capsule_bytes(value: bytes) -> dict[str, Any]:
    failures = []
    try:
        members = capsule_members(value)
        descriptor = json.loads(members["capsule.json"])
    except (KeyError, OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        return {"ok": False, "failures": [f"capsule unreadable: {exc}"]}
    if descriptor.get("schema_version") != "claim-capsule.1":
        failures.append("unsupported Claim Capsule schema")
    object_refs = tuple(str(item) for item in descriptor.get("object_refs", []))
    if object_refs != tuple(sorted(set(object_refs))):
        failures.append("capsule object list is not canonical")
    objects = {}
    for ref in object_refs:
        path = f"objects/sha256/{ref[7:9]}/{ref[9:]}"
        data = members.get(path)
        if data is None or digest_bytes(data) != ref:
            failures.append(f"missing or corrupt capsule object: {ref}")
        else:
            objects[ref] = data
    manifest_ref = str(descriptor.get("claim_manifest_ref", ""))
    checkpoint_ref = str(descriptor.get("checkpoint_ref", ""))
    try:
        manifest = ClaimManifest.from_mapping(json.loads(objects[manifest_ref]))
        checkpoint = WorkspaceCheckpoint.from_mapping(json.loads(objects[checkpoint_ref]))
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"claim closure unreadable: {exc}")
        manifest = None
        checkpoint = None
    if manifest is not None:
        if manifest.manifest_ref != manifest_ref:
            failures.append("Claim Manifest identity mismatch")
        if manifest.checkpoint_ref != checkpoint_ref:
            failures.append("Claim Manifest names another Checkpoint")
        expected = set(manifest.object_refs) | {manifest_ref}
        if set(object_refs) != expected:
            failures.append("capsule object list differs from Claim Manifest closure")
        for ref in manifest.object_refs:
            if ref not in objects:
                continue
            try:
                for child in refs_in(json.loads(objects[ref])):
                    if child not in manifest.object_refs:
                        failures.append(f"Claim Manifest omits transitive object: {child}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
    if checkpoint is not None:
        for name, head in checkpoint.journal_heads.items():
            path = f"journals/{name}.jsonl"
            try:
                events = [
                    json.loads(line)
                    for line in members.get(path, b"").splitlines()
                    if line.strip()
                ]
            except json.JSONDecodeError as exc:
                failures.append(f"{name} Journal proof unreadable: {exc}")
                continue
            failures.extend(
                verify_journal_prefix(
                    events,
                    journal_id=str(head["journal_id"]),
                    expected_head=head["head"],
                )
            )
            if len(events) != int(head["sequence"]):
                failures.append(f"{name} Journal proof has wrong sequence length")
    return {
        "ok": not failures,
        "failures": failures,
        "claim_manifest_ref": manifest_ref or None,
        "checkpoint_ref": checkpoint_ref or None,
        "objects_verified": len(objects),
    }
