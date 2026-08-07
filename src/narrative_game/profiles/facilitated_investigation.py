"""Reusable authoring adapter for the Facilitated Investigation profile."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from narrative_game.blueprint import (
    BLUEPRINT_SCHEMA_VERSION,
    BlueprintProposal,
    GameBlueprint,
    apply_blueprint_proposal,
    validate_blueprint,
)
from narrative_game.climb import FrozenInstrument, Requirement, prepare_blind_trial
from narrative_game.compiler import compile_candidate, freeze_candidate, reference_component_lock
from narrative_game.contracts import canonical_json
from narrative_game.experiment import CompletePackage, ProposedRevision
from narrative_game.generation import (
    ArtifactPlan,
    CreativeBrief,
    GENERATION_SCHEMA_VERSION,
)
from narrative_game.generation.artifacts import ArtifactSuiteMaterialization
from narrative_game.physical import export_physical


class FacilitatedInvestigationAuthoringAdapter:
    """Build and revise complete rich-text investigation Blueprints."""

    profile_id = "narrative.facilitated-investigation-authoring"
    profile_version = "1.0.0"
    component_lock = reference_component_lock()
    supported_hard_gates = frozenset(
        {"authoring.valid", "compiler.valid", "physical.valid", "blind.valid"}
    )
    production_dimension_floors = {
        "production_design_quality": 75,
        "host_and_dossier_usability": 75,
    }

    def __init__(
        self, artifact_suite: ArtifactSuiteMaterialization | None = None
    ) -> None:
        self._artifact_suite = artifact_suite

    def with_artifact_suite(
        self, materialization: ArtifactSuiteMaterialization
    ) -> "FacilitatedInvestigationAuthoringAdapter":
        """Return a build adapter bound to one exact accepted suite snapshot."""
        return type(self)(materialization)

    @staticmethod
    def required_artifact_resource_ids(
        blueprint: GameBlueprint,
    ) -> tuple[str, ...]:
        """Return evidence Resources whose player-visible form needs realism.

        Character dossiers are authored production interfaces rather than
        diegetic records. Every other Resource used as Evidence is a purported
        record, report, message, form, log, or reference handout and must cross
        the independently measured Artifact Forge boundary for production.
        """
        game = blueprint.materialize_game()
        dossier_resources = (
            {
                item.resource_id
                for item in game.character_program.dossiers
            }
            if game.character_program is not None
            else set()
        )
        return tuple(
            sorted(
                {item.resource_id for item in game.evidence}
                - dossier_resources
            )
        )

    def validate_release_target(
        self,
        blueprint: GameBlueprint,
        artifact_plan: ArtifactPlan,
        *,
        release_target: str,
    ) -> None:
        """Fail closed when a production Plan leaves evidence unmeasured."""
        if tuple(blueprint.artifact_specifications) != tuple(
            artifact_plan.specifications
        ):
            raise ValueError(
                "Blueprint Artifact Specifications differ from the frozen Plan"
            )
        if release_target == "development":
            return
        if release_target != "production":
            raise ValueError(f"unsupported release target: {release_target}")
        required = set(self.required_artifact_resource_ids(blueprint))
        planned = {item.resource_id for item in artifact_plan.specifications}
        missing = sorted(required - planned)
        if missing:
            raise ValueError(
                "production Artifact Plan omits realism-sensitive evidence "
                f"Resources: {', '.join(missing)}"
            )
        game = blueprint.materialize_game()
        if game.character_program is None:
            raise ValueError(
                "production facilitated investigations require a complete "
                "Character Program and private Dossier contract"
            )
        host_only_resources = {
            str(policy.resource).removeprefix("resource:")
            for policy in game.kernel.access_policies
            if {str(item) for item in policy.grantees} == {"viewer:host"}
        }
        if not host_only_resources:
            raise ValueError(
                "production facilitated investigations require a host-only guide Resource"
            )
        inaccessible = sorted(
            item.resource_id
            for item in artifact_plan.specifications
            if item.resource_id in required
            and item.accessibility.get("required") is not True
        )
        if inaccessible:
            raise ValueError(
                "production evidence Artifact Specifications require accessible "
                f"renditions: {', '.join(inaccessible)}"
            )

    def validate_release_instrument(
        self, instrument: FrozenInstrument, *, release_target: str
    ) -> None:
        """Require production measurement to inspect designed player output."""
        if release_target == "development":
            return
        if release_target != "production":
            raise ValueError(f"unsupported release target: {release_target}")
        dimensions = {item.dimension_id for item in instrument.dimensions}
        missing = sorted(set(self.production_dimension_floors) - dimensions)
        if missing:
            raise ValueError(
                "production Instrument omits required dimensions: "
                f"{', '.join(missing)}"
            )
        rules = {
            str(item.get("metric")): item
            for item in instrument.acceptance_rules
        }
        weak = [
            dimension
            for dimension, floor in self.production_dimension_floors.items()
            if dimension not in rules
            or rules[dimension].get("operator") != ">="
            or not isinstance(rules[dimension].get("value"), (int, float))
            or rules[dimension]["value"] < floor
        ]
        if weak:
            raise ValueError(
                "production Instrument lacks frozen per-dimension floors: "
                f"{', '.join(sorted(weak))}"
            )
        protocol = instrument.blind_protocol
        if protocol.get("inspect_print_renditions") is not True:
            raise ValueError(
                "production blind protocol must inspect exact trial/print renditions"
            )
        if protocol.get("panel_size", 0) < 3:
            raise ValueError("production blind protocol requires at least three judges")

    def build(
        self,
        draft_data: Mapping[str, Any],
        *,
        scratch_root: Path,
        instrument: FrozenInstrument,
    ) -> CompletePackage:
        del scratch_root  # The first-party rich-text path is pure and needs no scratch state.
        unknown = set(instrument.hard_gate_codes) - self.supported_hard_gates
        if unknown:
            raise ValueError(f"Instrument names unsupported profile hard gates: {sorted(unknown)}")
        blueprint = GameBlueprint.from_mapping(draft_data)
        findings = validate_blueprint(blueprint)
        if findings:
            first = findings[0]
            raise ValueError(f"Game Blueprint is invalid: {first.code} at {first.locus}")
        artifacts_by_resource = {}
        artifact_media_types = {}
        suite_attestation = None
        if self._artifact_suite is not None:
            specifications = {
                item.artifact_id: item for item in blueprint.artifact_specifications
            }
            if set(specifications) != set(self._artifact_suite.results):
                raise ValueError("bound Artifact Suite differs from Blueprint specifications")
            artifacts_by_resource = {
                specifications[artifact_id].resource_id: result
                for artifact_id, result in self._artifact_suite.results.items()
            }
            artifact_media_types = {
                specification.resource_id: specification.media_type
                for specification in specifications.values()
            }
            suite_attestation = self._artifact_suite.suite_attestation
        frozen = freeze_candidate(
            game=blueprint.materialize_game(
                artifacts_by_resource, artifact_media_types
            ),
            materials=blueprint.material_inputs(
                artifacts_by_resource,
                artifact_media_types=artifact_media_types,
                suite_attestation=suite_attestation,
            ),
            seed=blueprint.seed,
            component_lock=self.component_lock,
            compilation_options={
                "locale": "en-US",
                "presentation": "hybrid",
                "physical_provenance": "fictional-game-material",
                "displayed_claims": [
                    item.to_mapping() for item in blueprint.displayed_claims
                ],
            },
        )
        if frozen.candidate is None:
            first = frozen.findings[0]
            raise ValueError(f"Candidate freeze failed: {first.code} at {first.locus}")
        compiled = compile_candidate(frozen.candidate)
        if compiled.release is None:
            first = compiled.attempt.findings[0]
            raise ValueError(f"Game compilation failed: {first.code} at {first.locus}")
        release = compiled.release
        physical = export_physical(release)
        cover_story = str(
            instrument.blind_protocol.get("cover_story", "Anonymous facilitated investigation")
        )
        trial = prepare_blind_trial(release, physical, cover_story=cover_story)
        return CompletePackage(
            frozen.candidate.candidate_id,
            release.release_id,
            release.bundle_bytes,
            physical.export_id,
            physical.archive_bytes,
            trial,
            {code: True for code in instrument.hard_gate_codes},
        )

    def authoring_package(self, draft_data: Mapping[str, Any]) -> Mapping[str, Any]:
        blueprint = GameBlueprint.from_mapping(draft_data)
        game = blueprint.materialize_game()
        return {
            "schema_version": BLUEPRINT_SCHEMA_VERSION,
            "blueprint": blueprint.to_mapping(),
            "derived": {
                "game_definition_hash": game.content_hash,
                "total_target_minutes": sum(item.target_minutes for item in blueprint.arc),
                "phase_order": [
                    item.id for item in sorted(game.phases, key=lambda value: value.order)
                ],
                "proof_paths": [item.id for item in game.proof_paths],
            },
        }

    def proposal_contract(self) -> Mapping[str, Any]:
        return {
            "schema_version": BLUEPRINT_SCHEMA_VERSION,
            "output": {
                "schema_version": BLUEPRINT_SCHEMA_VERSION,
                "rationale": "string",
                "operations": [
                    {
                        "operation_id": "stable string",
                        "kind": (
                            "replace_direction | replace_world | replace_cast | "
                            "replace_deduction | replace_arc | replace_claims | upsert_material | "
                            "remove_material"
                        ),
                        "requirement_ids": ["every Requirement this operation addresses"],
                        "rationale": "human-readable reason",
                        "payload": "kind-specific object",
                    }
                ],
            },
            "rules": [
                "Return domain operations, never an unstructured rewrite.",
                "Address every Requirement by its exact identity.",
                "Preserve facts and content boundaries unless human direction changes them.",
                "Do not include judge-only quotes, paths, scores, or inferred answers.",
            ],
        }

    def creation_contract(self) -> Mapping[str, Any]:
        """Return the exact model-output contract for initial creation."""
        return {
            "schema_version": GENERATION_SCHEMA_VERSION,
            "output": {
                "schema_version": GENERATION_SCHEMA_VERSION,
                "rationale": "non-empty string",
                "blueprint": "complete canonical GameBlueprint mapping",
            },
            "rules": [
                "Return exactly the output envelope; unknown or omitted fields are invalid.",
                "The Blueprint must use the Creative Brief seed, title, direction, player count, and target duration.",
                "Return complete authored text for every Resource; do not return placeholders.",
                "Realism-sensitive Artifact Specifications must reference canonical Propositions and represented Events.",
                "Research is context only: cite it in authored content when relevant, but do not copy provenance into canonical truth.",
                "Invalid output is rejected and is never repaired, defaulted, or partially accepted.",
            ],
        }

    def parse_initial_creation_output(
        self,
        brief: CreativeBrief,
        parsed_output: Any,
        *,
        research: Mapping[str, Any] | None = None,
    ) -> GameBlueprint:
        """Parse one complete model result without inferring or repairing fields."""
        if not isinstance(brief, CreativeBrief):
            raise TypeError("initial creation requires a Creative Brief")
        if research is not None and not isinstance(research, Mapping):
            raise TypeError("initial creation research must be an object")
        if not isinstance(parsed_output, Mapping):
            raise ValueError("initial creation output must be an object")
        required = {"schema_version", "rationale", "blueprint"}
        if set(parsed_output) != required:
            raise ValueError(
                "initial creation output must contain exactly schema_version, rationale, and blueprint"
            )
        if parsed_output["schema_version"] != GENERATION_SCHEMA_VERSION:
            raise ValueError(
                f"initial creation output must use schema {GENERATION_SCHEMA_VERSION}"
            )
        rationale = parsed_output["rationale"]
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("initial creation output requires a non-empty rationale")
        raw_blueprint = parsed_output["blueprint"]
        if not isinstance(raw_blueprint, Mapping):
            raise ValueError("initial creation output blueprint must be an object")
        try:
            blueprint = GameBlueprint.from_mapping(raw_blueprint)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"initial creation Blueprint could not be parsed: {exc}") from exc
        # A canonical round trip detects ignored fields, implicit defaults, and
        # scalar coercions in the older Blueprint readers. Initial creation must
        # supply the exact complete mapping, not a value we can normalize.
        if canonical_json(raw_blueprint) != canonical_json(blueprint.to_mapping()):
            raise ValueError("initial creation Blueprint is not an exact canonical mapping")
        findings = validate_blueprint(blueprint)
        if findings:
            first = findings[0]
            raise ValueError(
                f"initial creation Blueprint is invalid: {first.code} at {first.locus}"
            )
        game = blueprint.materialize_game()
        canonical_game = game.to_mapping()
        canonical_game["kernel"].pop("resources")
        if canonical_json(raw_blueprint["game"]) != canonical_json(canonical_game):
            raise ValueError(
                "initial creation Game Definition is not an exact canonical mapping"
            )
        direction = game.direction
        if blueprint.seed != brief.seed:
            raise ValueError("initial creation Blueprint seed does not match the Creative Brief")
        if game.kernel.title != brief.title:
            raise ValueError("initial creation Blueprint title does not match the Creative Brief")
        if (
            direction.premise != brief.premise
            or direction.experience_targets != brief.experience_targets
            or direction.content_boundaries != brief.content_boundaries
        ):
            raise ValueError("initial creation Blueprint direction does not match the Creative Brief")
        if len(game.profile.supported_seat_ids) != brief.player_count:
            raise ValueError(
                "initial creation Blueprint player count does not match the Creative Brief"
            )
        if sum(item.target_minutes for item in blueprint.arc) != brief.target_minutes:
            raise ValueError(
                "initial creation Blueprint target duration does not match the Creative Brief"
            )
        return blueprint

    def apply_builder_output(
        self,
        draft_data: Mapping[str, Any],
        parsed_output: Any,
        *,
        requirements: tuple[Requirement, ...],
        human_direction: str | None,
        scratch_root: Path,
        instrument: FrozenInstrument,
    ) -> ProposedRevision:
        del human_direction
        if not isinstance(parsed_output, Mapping):
            raise ValueError("builder output must be a Blueprint Proposal object")
        baseline = GameBlueprint.from_mapping(draft_data)
        proposal = BlueprintProposal.from_mapping(parsed_output)
        revised = apply_blueprint_proposal(
            baseline,
            proposal,
            required_requirement_ids=(item.requirement_id for item in requirements),
        )
        preview = self.build(
            revised.to_mapping(), scratch_root=scratch_root, instrument=instrument
        )
        return ProposedRevision(revised.to_mapping(), proposal.rationale, preview)
