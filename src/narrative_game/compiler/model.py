"""Immutable values at the Draft → Candidate → Game Release boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from narrative_game.contracts.canonical import digest_bytes, digest_json
from narrative_game.narrative import GameDefinition


@dataclass(frozen=True)
class CompilationFinding:
    code: str
    severity: str
    owner: str
    owner_version: str
    locus: str
    quote: str
    message: str
    evidence: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.severity not in {"blocker", "warning"}:
            raise ValueError(f"invalid compilation severity: {self.severity!r}")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "owner": self.owner,
            "owner_version": self.owner_version,
            "locus": self.locus,
            "quote": self.quote,
            "message": self.message,
            "evidence": dict(self.evidence),
        }


@dataclass(frozen=True)
class MaterialInput:
    resource_id: str
    media_type: str
    data: bytes
    reproduction_receipt: Mapping[str, Any]
    artifact_attestation: Mapping[str, Any] | None = None

    @property
    def content_hash(self) -> str:
        return digest_bytes(self.data)

    def descriptor(self) -> dict[str, Any]:
        result = {
            "resource_id": self.resource_id,
            "media_type": self.media_type,
            "content_hash": self.content_hash,
            "bytes": len(self.data),
            "reproduction_receipt_hash": digest_json(self.reproduction_receipt),
        }
        if self.artifact_attestation is not None:
            result["artifact_attestation_hash"] = digest_json(self.artifact_attestation)
        return result


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    game: GameDefinition
    materials: tuple[MaterialInput, ...]
    seed: int
    component_lock: Mapping[str, Any]
    compilation_options: Mapping[str, Any]
    advisories: tuple[CompilationFinding, ...]
    frozen_manifest: Mapping[str, Any]


@dataclass(frozen=True)
class FreezeResult:
    candidate: Candidate | None
    findings: tuple[CompilationFinding, ...]

    @property
    def ok(self) -> bool:
        return self.candidate is not None and not any(
            item.severity == "blocker" for item in self.findings
        )


@dataclass(frozen=True)
class BundledFile:
    path: str
    media_type: str
    data: bytes
    audience: str

    @property
    def content_hash(self) -> str:
        return digest_bytes(self.data)

    def descriptor(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "media_type": self.media_type,
            "content_hash": self.content_hash,
            "bytes": len(self.data),
            "audience": self.audience,
        }


@dataclass(frozen=True)
class GameRelease:
    release_id: str
    candidate_id: str
    manifest: Mapping[str, Any]
    files: tuple[BundledFile, ...]
    bundle_bytes: bytes
    bundle_hash: str

    def file(self, path: str) -> BundledFile:
        try:
            return next(item for item in self.files if item.path == path)
        except StopIteration as exc:
            raise KeyError(path) from exc


@dataclass(frozen=True)
class CompilationAttempt:
    attempt_id: str
    candidate_id: str
    compiler_version: str
    outcome: str
    findings: tuple[CompilationFinding, ...]
    release_id: str | None
    bundle_hash: str | None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "candidate_id": self.candidate_id,
            "compiler_version": self.compiler_version,
            "outcome": self.outcome,
            "findings": [item.to_mapping() for item in self.findings],
            "release_id": self.release_id,
            "bundle_hash": self.bundle_hash,
        }


@dataclass(frozen=True)
class CompilationResult:
    release: GameRelease | None
    attempt: CompilationAttempt

    @property
    def ok(self) -> bool:
        return self.release is not None
