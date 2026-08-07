"""Typed boundary between game generation and independently climbed artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from typing import Any, Mapping, Protocol

from pypdf import PdfReader

from narrative_game.contracts import ArtifactResult, canonical_json

from .model import ArtifactPlan


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class ArtifactSuiteMaterialization:
    """Exact outputs of one verified, independently measured artifact suite."""

    suite_attestation: Mapping[str, Any]
    results: Mapping[str, ArtifactResult]
    schema_version: str = "0.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "suite_attestation", _copy(self.suite_attestation))
        object.__setattr__(self, "results", dict(self.results))
        if not self.suite_attestation:
            raise ValueError("artifact suite attestation is required")
        if self.suite_attestation.get("qualification", {}).get("release_ready") is not True:
            raise ValueError("artifact suite must have accepted release-ready qualification")
        if set(self.results) != {item.artifact_id for item in self.results.values()}:
            raise ValueError("artifact suite result keys must match Artifact Result identities")

    def validate_for(self, plan: ArtifactPlan) -> None:
        expected = {item.artifact_id: item for item in plan.specifications}
        if set(self.results) != set(expected):
            raise ValueError("artifact suite must materialize every planned artifact exactly once")
        for artifact_id, result in self.results.items():
            specification = expected[artifact_id]
            request = result.request
            if request.get("artifact_id") != artifact_id:
                raise ValueError(f"artifact {artifact_id} request names another identity")
            if request.get("document_class") != specification.document_class:
                raise ValueError(f"artifact {artifact_id} used another document class")
            if request.get("seed") != specification.seed:
                raise ValueError(f"artifact {artifact_id} used another seed")
            if dict(request.get("pins") or {}) != dict(specification.pins):
                raise ValueError(f"artifact {artifact_id} used different pins")
            if dict(request.get("canon") or {}) != dict(specification.canon):
                raise ValueError(f"artifact {artifact_id} used different canon")
            expected_fact_references = (
                *specification.proposition_ids,
                *specification.event_ids,
            )
            if tuple(request.get("fact_references", ())) != expected_fact_references:
                raise ValueError(
                    f"artifact {artifact_id} used different canonical fact references"
                )
            metadata = request.get("metadata") or {}
            if metadata.get("narrative_truth_binding") != specification.truth_binding:
                raise ValueError(
                    f"artifact {artifact_id} is not bound to the planned canonical world"
                )
            verification = result.attestation.get("verification", {})
            if verification.get("ok") is not True:
                raise ValueError(f"artifact {artifact_id} is not verified")
            if result.attestation.get("measurement", {}).get("status") != "accepted":
                raise ValueError(f"artifact {artifact_id} lacks accepted realism standing")

    def validate_production_for(self, plan: ArtifactPlan) -> None:
        """Require exact accepted bytes to remain independently readable."""
        self.validate_for(plan)
        expected = {item.artifact_id: item for item in plan.specifications}
        for artifact_id, result in self.results.items():
            specification = expected[artifact_id]
            if specification.accessibility.get("required") is not True:
                raise ValueError(
                    f"production artifact {artifact_id} lacks an accessibility requirement"
                )
            if specification.media_type == "application/pdf":
                try:
                    reader = PdfReader(BytesIO(result.document))
                    extracted = "\n".join(
                        page.extract_text() or "" for page in reader.pages
                    )
                except Exception as exc:
                    raise ValueError(
                        f"production artifact {artifact_id} is not a readable PDF"
                    ) from exc
                if not extracted.strip():
                    raise ValueError(
                        f"production artifact {artifact_id} lacks embedded text or OCR"
                    )


class ArtifactSuiteImporter(Protocol):
    """Import an already forged, measured, and attested suite.

    Implementations may verify and translate a public suite snapshot. They do
    not create, revise, forge, or measure Verismill Experiments.
    """

    def import_suite(
        self,
        plan: ArtifactPlan,
        blueprint: Any,
    ) -> ArtifactSuiteMaterialization: ...


class ArtifactSuiteMaterializer(ArtifactSuiteImporter, Protocol):
    """Compatibility surface for coordinators that still call ``materialize``.

    The operation is an import despite the legacy method name. A provider that
    must forge or remeasure artifacts belongs in a separate, explicit workflow.
    """

    def materialize(
        self,
        plan: ArtifactPlan,
        blueprint: Any,
        *,
        scratch_root: Path,
    ) -> ArtifactSuiteMaterialization: ...


__all__ = [
    "ArtifactSuiteImporter",
    "ArtifactSuiteMaterialization",
    "ArtifactSuiteMaterializer",
]
