"""Immutable contracts at the difficulty-analysis boundary."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _require_ref(value: str, *, label: str) -> None:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError(f"{label} must be a SHA-256 content reference")
    if any(character not in "0123456789abcdef" for character in value[7:]):
        raise ValueError(f"{label} must be a SHA-256 content reference")


@dataclass(frozen=True)
class NormativeContract:
    """One exact source whose bytes define an accepted difficulty contract."""

    contract_id: str
    source_path: str
    content_ref: str
    declared_version: str

    def __post_init__(self) -> None:
        if not self.contract_id.strip() or not self.source_path.strip():
            raise ValueError("normative contract identity and source path are required")
        if self.source_path.startswith("/") or ".." in self.source_path.split("/"):
            raise ValueError("normative contract source must be repository-relative")
        if not self.declared_version.strip():
            raise ValueError("normative contract version is required")
        _require_ref(self.content_ref, label="normative contract content_ref")

    def to_mapping(self) -> dict[str, str]:
        return {
            "contract_id": self.contract_id,
            "source_path": self.source_path,
            "content_ref": self.content_ref,
            "declared_version": self.declared_version,
        }


@dataclass(frozen=True)
class NormativeContractCatalog:
    """The exact accepted contract sources an implementation may target."""

    entries: tuple[NormativeContract, ...]
    schema_version: str = "difficulty-contract-catalog.1"

    def __post_init__(self) -> None:
        ids = [item.contract_id for item in self.entries]
        paths = [item.source_path for item in self.entries]
        if len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
            raise ValueError("normative contract IDs and source paths must be unique")

    @property
    def catalog_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entries": [
                item.to_mapping()
                for item in sorted(self.entries, key=lambda entry: entry.contract_id)
            ],
        }

    def verify_materials(self, materials: Mapping[str, bytes]) -> tuple[str, ...]:
        """Compare caller-supplied source bytes without reading ambient files."""
        expected = {item.source_path: item for item in self.entries}
        findings = []
        for path in sorted(expected.keys() - materials.keys()):
            findings.append(f"missing normative source: {path}")
        for path in sorted(materials.keys() - expected.keys()):
            findings.append(f"unexpected normative source: {path}")
        for path in sorted(expected.keys() & materials.keys()):
            observed = digest_bytes(materials[path])
            if observed != expected[path].content_ref:
                findings.append(
                    f"normative source changed: {path}; expected "
                    f"{expected[path].content_ref}, observed {observed}"
                )
        return tuple(findings)


DIFFICULTY_CONTRACT_CATALOG = NormativeContractCatalog(
    (
        NormativeContract(
            "difficulty.domain-language",
            "CONTEXT.md",
            "sha256:8934b5d8488b74e890b7d0fd40e9a5a527287291ed493ba5cc4f5dd128b09496",
            "2026-08-08",
        ),
        NormativeContract(
            "difficulty.acceptance-matrix",
            "docs/acceptance-matrix.md",
            "sha256:2a21226ad5046e1e6b9ee20f8ccb8bc4a4b90128909e6bca99592b457482f47f",
            "0.32.0",
        ),
        NormativeContract(
            "difficulty.analysis-instrument",
            "docs/analysis-instrument-v1.md",
            "sha256:a3e98557a3f586e886293678998433b2ca1df6516113a467afff6a0ffb0958e0",
            "1.0.0",
        ),
        NormativeContract(
            "difficulty.task-hardening",
            "docs/task-hardening-outer-loop.md",
            "sha256:2b39025f34a749b3a5156464d445bf57ae36f2057b1c737723bf99a8464eb749",
            "1",
        ),
        NormativeContract(
            "difficulty.operator-monitor",
            "docs/operator-evidence-monitor.md",
            "sha256:c706f6fcee26f73ebb605eafc0ba74a3e44bd37d24b988f23cfc4c1d44246fa1",
            "1",
        ),
        NormativeContract(
            "difficulty.failure-atlas",
            "docs/adr/0008-bounded-failure-atlas.md",
            "sha256:3f7ee3de7ec658a806a00751f0089c7992b1963f0fe88a849271bd93618d020a",
            "accepted-2026-08-07",
        ),
        NormativeContract(
            "difficulty.recursive-generation",
            "docs/adr/0009-recursive-generation-uses-sealed-governance.md",
            "sha256:2dd9243f28041c9db7e6ddac1de7ff4696f71d8abff7eaf50df613504e892912",
            "accepted-2026-08-08",
        ),
        NormativeContract(
            "difficulty.sampling-separation",
            "docs/adr/0010-separate-standing-from-adaptive-diagnostics.md",
            "sha256:bc5e451dad95e7f0f3be1b29d95f9c77044a6df749704906644b617feae9f4d1",
            "accepted-2026-08-08",
        ),
        NormativeContract(
            "difficulty.evidence-lineage",
            "docs/adr/0011-content-addressed-evidence-lineage.md",
            "sha256:d3fca0a9920256d0d49b981f6d80d2d0e5c625e926f81c818943c318693f7451",
            "accepted-2026-08-08",
        ),
        NormativeContract(
            "difficulty.failure-scaling-research",
            "docs/research/agent-failure-scaling.md",
            "sha256:5608b6b98865956b6491fa318aedb5dc9abaea5caf82c2b622e7b8ad11ab87a8",
            "2026-08-07",
        ),
        NormativeContract(
            "difficulty.implementation-handoff",
            "docs/agentic-difficulty-implementation-plan.md",
            "sha256:c9f2c8b5a3a564661240ca3b3e364de5ee70f71c94dd05869735dea25069a728",
            "1",
        ),
    )
)


@dataclass(frozen=True)
class CanonicalEvidenceSpan:
    """One addressable, unedited span from a canonical Episode Archive."""

    span_id: str
    source_kind: str
    source_index: int
    visibility: tuple[str, ...]
    content: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.span_id.strip() or self.source_index < 0:
            raise ValueError("evidence span identity and non-negative index are required")
        object.__setattr__(self, "content", _copy(self.content))

    @property
    def content_ref(self) -> str:
        return digest_json(self.content)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "source_kind": self.source_kind,
            "source_index": self.source_index,
            "visibility": list(self.visibility),
            "content": _copy(self.content),
            "content_ref": self.content_ref,
        }


@dataclass(frozen=True)
class VerificationStatus:
    """Claim-scoped replay status for a set of canonical spans."""

    scope: str
    status: str
    verifier_version: str
    span_ids: tuple[str, ...]
    findings: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status not in {"verified", "invalid", "incomplete"}:
            raise ValueError(f"unsupported verification status: {self.status}")
        if self.status == "verified" and self.findings:
            raise ValueError("verified status cannot retain findings")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "scope": self.scope,
            "status": self.status,
            "verifier_version": self.verifier_version,
            "span_ids": list(self.span_ids),
            "findings": list(self.findings),
        }


@dataclass(frozen=True)
class EpisodeEvidencePackage:
    """Canonical, content-addressed source for one Episode's later views."""

    episode_id: str
    release_id: str
    archive_ref: str
    contract_catalog_id: str
    spans: tuple[CanonicalEvidenceSpan, ...]
    verification: VerificationStatus
    schema_version: str = "episode-evidence.1"

    def __post_init__(self) -> None:
        _require_ref(self.archive_ref, label="episode archive_ref")
        _require_ref(self.contract_catalog_id, label="contract catalog_id")
        ids = [item.span_id for item in self.spans]
        if len(set(ids)) != len(ids):
            raise ValueError("canonical evidence span IDs must be unique")
        if set(self.verification.span_ids) != set(ids):
            raise ValueError("Verification Status must name every canonical evidence span")

    @property
    def package_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "release_id": self.release_id,
            "archive_ref": self.archive_ref,
            "contract_catalog_id": self.contract_catalog_id,
            "spans": [item.to_mapping() for item in self.spans],
            "verification": self.verification.to_mapping(),
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_mapping())


@dataclass(frozen=True)
class EvidenceViewSpan:
    """One derived span and its exact redaction lineage."""

    source_span_id: str
    content: Mapping[str, Any]
    redacted_paths: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "content", _copy(self.content))

    @property
    def content_ref(self) -> str:
        return digest_json(self.content)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "source_span_id": self.source_span_id,
            "content": _copy(self.content),
            "content_ref": self.content_ref,
            "redacted_paths": list(self.redacted_paths),
        }


@dataclass(frozen=True)
class EvidenceViewManifest:
    """The exact answer-safe projection made available to one authority."""

    view_contract: str
    episode_package_id: str
    spans: tuple[EvidenceViewSpan, ...]
    denied_fields: tuple[str, ...]
    schema_version: str = "evidence-view-manifest.1"

    def __post_init__(self) -> None:
        _require_ref(self.episode_package_id, label="episode package_id")
        ids = [item.source_span_id for item in self.spans]
        if len(set(ids)) != len(ids):
            raise ValueError("Evidence View may project each source span at most once")

    @property
    def manifest_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "view_contract": self.view_contract,
            "episode_package_id": self.episode_package_id,
            "spans": [item.to_mapping() for item in self.spans],
            "denied_fields": list(self.denied_fields),
        }

    def to_bytes(self) -> bytes:
        return canonical_json(self.to_mapping())


@dataclass(frozen=True)
class SemanticFixtureExpectation:
    """A hidden fixture oracle that must never enter a Discovery view."""

    expectation_id: str
    source_kind: str
    event_type: str
    required_content: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.expectation_id.strip() or not self.event_type.strip():
            raise ValueError("semantic fixture expectation identity is required")
        object.__setattr__(self, "required_content", _copy(self.required_content))

    @property
    def expectation_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "expectation_id": self.expectation_id,
            "source_kind": self.source_kind,
            "event_type": self.event_type,
            "required_content": _copy(self.required_content),
        }
