"""Immutable SHA-256 object storage for Workspace-owned state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from narrative_game.contracts.canonical import canonical_json, digest_bytes

from .io import atomic_write


_OBJECT_REF_KEYS = frozenset(
    {
        "artifact",
        "artifact_result",
        "attestation",
        "authority",
        "baseline_draft",
        "candidate",
        "child_draft",
        "component_lock",
        "draft_revision",
        "evaluation",
        "exposure",
        "finding",
        "instrument",
        "manifest",
        "model_receipt",
        "object",
        "operation_receipt",
        "parents",
        "parsed_output",
        "prompt",
        "proposal",
        "proposed_data",
        "human_review",
        "raw_output",
        "requirement",
        "resource",
        "resources",
        "standing",
        "task",
        "trial_binding",
        "blind_trial",
        "physical_archive",
        "release_bundle",
        "selection",
        "context",
        "tool_contract",
        "transition",
    }
)


def refs_in(value: Any, *, key: str | None = None) -> Iterable[str]:
    """Yield Workspace object edges, not arbitrary external content digests.

    Receipts legitimately contain SHA-256 values for prompts, source commits,
    package implementations, and other material that is not copied into this
    object store. An internal graph edge is therefore defined by a typed field,
    never inferred merely from the digest's shape.
    """
    if isinstance(value, str):
        normalized_key = key
        if normalized_key and normalized_key.endswith("_refs"):
            normalized_key = normalized_key[:-5]
        elif normalized_key and normalized_key.endswith("_ref"):
            normalized_key = normalized_key[:-4]
        if normalized_key in _OBJECT_REF_KEYS and value.startswith("sha256:") and len(value) == 71:
            yield value
    elif isinstance(value, dict):
        for child_key, item in value.items():
            if child_key in {"input_hashes", "inputs"}:
                continue
            yield from refs_in(item, key=child_key)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from refs_in(item, key=key)


class ObjectStore:
    """A portable object store whose references depend only on content."""

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path_for(self, ref: str) -> Path:
        if not ref.startswith("sha256:") or len(ref) != 71:
            raise ValueError(f"invalid object reference: {ref!r}")
        digest = ref.removeprefix("sha256:")
        if any(character not in "0123456789abcdef" for character in digest):
            raise ValueError(f"invalid object reference: {ref!r}")
        return self.root / digest[:2] / digest[2:]

    def put_bytes(self, value: bytes) -> str:
        ref = digest_bytes(value)
        path = self.path_for(ref)
        if path.exists():
            if path.read_bytes() != value:
                raise ValueError(f"content collision or corrupt object: {ref}")
            return ref
        atomic_write(path, value)
        return ref

    def put_json(self, value: Any) -> str:
        return self.put_bytes(canonical_json(value))

    def read_bytes(self, ref: str) -> bytes:
        value = self.path_for(ref).read_bytes()
        if digest_bytes(value) != ref:
            raise ValueError(f"object failed content verification: {ref}")
        return value

    def read_json(self, ref: str) -> Any:
        return json.loads(self.read_bytes(ref))

    def verify(self, ref: str) -> bool:
        try:
            return digest_bytes(self.path_for(ref).read_bytes()) == ref
        except (OSError, ValueError):
            return False

    def references(self) -> list[str]:
        result = []
        for prefix in sorted(self.root.iterdir()) if self.root.exists() else []:
            if not prefix.is_dir() or len(prefix.name) != 2:
                continue
            for item in sorted(prefix.iterdir()):
                if item.is_file() and not item.name.endswith(".tmp"):
                    result.append("sha256:" + prefix.name + item.name)
        return result

    def verify_all(self) -> tuple[bool, list[str]]:
        failures = [ref for ref in self.references() if not self.verify(ref)]
        return not failures, failures
