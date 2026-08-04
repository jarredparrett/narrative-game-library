"""Single game-facing adapter for the public Verismill Artifact Forge facade."""

from __future__ import annotations

from typing import Any, Protocol

from narrative_game.contracts.artifacts import ArtifactRequest, ArtifactResult


class PublicExperiment(Protocol):
    """The only Verismill behavior the downstream adapter consumes."""

    def emit_candidate(
        self,
        class_name: str,
        *,
        builder_run: str,
        explanation: dict,
        seed: int = 0,
        pins: dict | None = None,
        canon: dict | None = None,
        defect: dict | None = None,
        metadata: dict | None = None,
    ) -> str: ...

    def artifact_result(self, candidate: str | None = None) -> dict: ...


class VerismillArtifactForge:
    """Forge and materialize a measured artifact without private imports."""

    adapter_id = "narrative_game.verismill_artifact_forge"
    adapter_version = "0.1"

    def forge(
        self,
        experiment: PublicExperiment,
        request: ArtifactRequest,
        *,
        builder_run: str,
        explanation: dict[str, Any],
    ) -> ArtifactResult:
        candidate = experiment.emit_candidate(
            request.document_class,
            builder_run=builder_run,
            explanation=dict(explanation),
            seed=request.seed,
            pins=dict(request.pins) or None,
            canon=None if request.canon is None else dict(request.canon),
            defect=None if request.defect is None else dict(request.defect),
            metadata=None if request.metadata is None else dict(request.metadata),
        )
        exported = experiment.artifact_result(candidate)
        attestation = dict(exported["attestation"])
        attestation["adapter"] = {
            "id": self.adapter_id,
            "version": self.adapter_version,
        }
        return ArtifactResult(
            artifact_id=request.artifact_id,
            document=exported["artifact"],
            manifest=exported["manifest"],
            attestation=attestation,
            request=request.to_dict(),
        )
