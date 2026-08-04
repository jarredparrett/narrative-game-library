"""Game-facing Artifact Forge request and result contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

from .canonical import digest_bytes


def _mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(value or {}))


@dataclass(frozen=True)
class ArtifactRequest:
    """Resolved narrative facts to express through one document class."""

    artifact_id: str
    document_class: str
    seed: int
    pins: Mapping[str, Any] = field(default_factory=dict)
    canon: Mapping[str, Any] | None = None
    defect: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] | None = None
    fact_references: tuple[str, ...] = ()
    narrative_function: str = ""
    permitted_disclosures: tuple[str, ...] = ()
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if not self.artifact_id.strip() or not self.document_class.strip():
            raise ValueError("artifact_id and document_class are required")
        if not isinstance(self.seed, int):
            raise TypeError("artifact seed must be an integer")
        if any(not item.strip() for item in self.fact_references):
            raise ValueError("fact references must be non-empty identifiers")
        object.__setattr__(self, "pins", _mapping(self.pins))
        object.__setattr__(self, "canon", None if self.canon is None else _mapping(self.canon))
        object.__setattr__(self, "defect", None if self.defect is None else _mapping(self.defect))
        object.__setattr__(
            self, "metadata", None if self.metadata is None else _mapping(self.metadata)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "document_class": self.document_class,
            "seed": self.seed,
            "pins": dict(self.pins),
            "canon": None if self.canon is None else dict(self.canon),
            "defect": None if self.defect is None else dict(self.defect),
            "metadata": None if self.metadata is None else dict(self.metadata),
            "fact_references": list(self.fact_references),
            "narrative_function": self.narrative_function,
            "permitted_disclosures": list(self.permitted_disclosures),
        }


@dataclass(frozen=True)
class ArtifactResult:
    """Materialized document bytes plus their trusted experiment attestation."""

    artifact_id: str
    document: bytes
    manifest: Mapping[str, Any]
    attestation: Mapping[str, Any]
    request: Mapping[str, Any]
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        if not self.document:
            raise ValueError("artifact result document must not be empty")
        object.__setattr__(self, "manifest", _mapping(self.manifest))
        object.__setattr__(self, "attestation", _mapping(self.attestation))
        object.__setattr__(self, "request", _mapping(self.request))
        if self.manifest.get("sha256") != self.content_hash:
            raise ValueError("artifact manifest does not match document bytes")
        if self.attestation.get("artifact_hash") != self.content_hash:
            raise ValueError("artifact attestation does not match document bytes")

    @property
    def content_hash(self) -> str:
        return digest_bytes(self.document)
