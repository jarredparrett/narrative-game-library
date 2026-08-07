"""Single game-facing adapter for the public Verismill Artifact Forge facade."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Protocol

from narrative_game.blueprint import GameBlueprint, derive_artifact_truth_binding
from narrative_game.contracts.artifacts import ArtifactRequest, ArtifactResult
from narrative_game.generation.artifacts import ArtifactSuiteMaterialization
from narrative_game.generation.model import ArtifactPlan


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


class PublicArtifactSuite(Protocol):
    """Portable public surface consumed from Verismill's ArtifactSuite."""

    def verify(self) -> dict: ...

    def attestation(self) -> dict | None: ...

    def artifact_results(self) -> dict[str, dict]: ...


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


@dataclass(frozen=True)
class VerismillArtifactSuiteImporter:
    """Import one exact accepted public Verismill suite into a game build.

    The suite must already exist, verify, be attested, and have accepted member
    measurements. This adapter never creates an Experiment, emits a Candidate,
    revises an artifact, runs a panel, or upgrades standing.
    """

    suite: PublicArtifactSuite
    member_ids: Mapping[str, str] = field(default_factory=dict)

    def import_suite(
        self,
        plan: ArtifactPlan,
        blueprint: GameBlueprint,
    ) -> ArtifactSuiteMaterialization:
        if not isinstance(blueprint, GameBlueprint):
            raise TypeError("Artifact Suite import requires a Game Blueprint")
        if tuple(blueprint.artifact_specifications) != tuple(plan.specifications):
            raise ValueError(
                "Artifact Plan and Blueprint must name the same exact specifications"
            )
        for specification in plan.specifications:
            if derive_artifact_truth_binding(blueprint, specification) != (
                specification.truth_binding
            ):
                raise ValueError(
                    f"artifact {specification.artifact_id} has a stale canonical truth binding"
                )
        verification = self.suite.verify()
        if verification.get("ok") is not True:
            raise ValueError("Verismill Artifact Suite failed public verification")
        attestation = self.suite.attestation()
        if attestation is None:
            raise ValueError("Verismill Artifact Suite is not attested")
        exported = self.suite.artifact_results()
        member_ids = {
            item.artifact_id: self.member_ids.get(item.artifact_id, item.artifact_id)
            for item in plan.specifications
        }
        if len(set(member_ids.values())) != len(member_ids):
            raise ValueError("Artifact Suite mapping reuses a member")
        if set(member_ids.values()) != set(exported):
            raise ValueError("Artifact Plan must cover the exact attested Suite membership")
        results = {}
        for specification in plan.specifications:
            raw = exported[member_ids[specification.artifact_id]]
            manifest = raw["manifest"]
            if manifest.get("class") != specification.document_class:
                raise ValueError(
                    f"artifact {specification.artifact_id} manifest names another class"
                )
            if manifest.get("seed") != specification.seed:
                raise ValueError(
                    f"artifact {specification.artifact_id} manifest names another seed"
                )
            if dict(manifest.get("pins") or {}) != dict(specification.pins):
                raise ValueError(
                    f"artifact {specification.artifact_id} manifest has different pins"
                )
            if dict(manifest.get("canon") or {}) != dict(specification.canon):
                raise ValueError(
                    f"artifact {specification.artifact_id} manifest has different canon"
                )
            request = ArtifactRequest(
                artifact_id=specification.artifact_id,
                document_class=specification.document_class,
                seed=specification.seed,
                pins=specification.pins,
                canon=specification.canon,
                metadata={
                    "accessibility": dict(specification.accessibility),
                    "narrative_truth_binding": specification.truth_binding,
                    "suite_boundary_operation": "import-existing-attested-suite",
                },
                fact_references=(
                    *specification.proposition_ids,
                    *specification.event_ids,
                ),
                narrative_function="planned evidence artifact",
                permitted_disclosures=specification.permitted_audience_ids,
            )
            results[specification.artifact_id] = ArtifactResult(
                specification.artifact_id,
                raw["artifact"],
                raw["manifest"],
                raw["attestation"],
                request.to_dict(),
            )
        materialization = ArtifactSuiteMaterialization(attestation, results)
        materialization.validate_for(plan)
        return materialization

    def materialize(
        self,
        plan: ArtifactPlan,
        blueprint: GameBlueprint,
        *,
        scratch_root: Path,
    ) -> ArtifactSuiteMaterialization:
        """Compatibility spelling for the coordinator; performs import only."""

        del scratch_root
        return self.import_suite(plan, blueprint)


# Compatibility alias for the Stage 7-8 API. New integrations should use the
# honest importer name; both names expose the same import-only implementation.
VerismillArtifactSuiteMaterializer = VerismillArtifactSuiteImporter


__all__ = [
    "PublicArtifactSuite",
    "PublicExperiment",
    "VerismillArtifactForge",
    "VerismillArtifactSuiteImporter",
    "VerismillArtifactSuiteMaterializer",
]
