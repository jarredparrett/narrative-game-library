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
from narrative_game.experiment import CompletePackage, ProposedRevision
from narrative_game.physical import export_physical


class FacilitatedInvestigationAuthoringAdapter:
    """Build and revise complete rich-text investigation Blueprints."""

    profile_id = "narrative.facilitated-investigation-authoring"
    profile_version = "1.0.0"
    component_lock = reference_component_lock()
    supported_hard_gates = frozenset(
        {"authoring.valid", "compiler.valid", "physical.valid", "blind.valid"}
    )

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
        frozen = freeze_candidate(
            game=blueprint.materialize_game(),
            materials=blueprint.material_inputs(),
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
