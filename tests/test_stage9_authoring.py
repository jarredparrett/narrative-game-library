"""Stage 9 acceptance for typed, human-governed game authoring."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from pypdf import PdfReader

from narrative_game.blueprint import (
    AuthoringOperation,
    BlueprintProposal,
    GameBlueprint,
    apply_blueprint_proposal,
    validate_blueprint,
)
from narrative_game.climb import (
    Authority,
    Dimension,
    DriverOutput,
    FrozenInstrument,
    Requirement,
)
from narrative_game.contracts import canonical_json
from narrative_game.experiment import Experiment, ModelPanelMember
from narrative_game.examples import vanished_ledger_blueprint
from narrative_game.profiles import FacilitatedInvestigationAuthoringAdapter


def worked_blueprint() -> GameBlueprint:
    return vanished_ledger_blueprint()


def instrument() -> FrozenInstrument:
    return FrozenInstrument(
        "facilitated-authoring",
        "1.0.0",
        "complete anonymous investigation",
        (
            Dimension(
                "world_coherence",
                "The represented world and its authored materials agree.",
                1,
                {"0": "contradictory", "60": "usable", "100": "expert-resistant"},
            ),
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 60},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "cover_story": "Anonymous archival investigation",
            "panel_size": 1,
            "panel_lenses": ["world-coherence"],
            "panel_aggregation": "median-per-dimension-v1",
            "selection_evidence_classes": ["live-model"],
        },
        ("authoring.valid", "compiler.valid", "physical.valid", "blind.valid"),
    )


def test_blueprint_derives_canonical_resources_and_validates_arc_alignment():
    """stage9.blueprint: source text and arc intent derive one valid Game Definition."""
    blueprint = worked_blueprint()
    assert validate_blueprint(blueprint) == ()
    game = blueprint.materialize_game()
    assert {item.id for item in game.kernel.resources} == {
        item.resource_id for item in blueprint.materials
    }
    changed_material = replace(
        blueprint.materials[0], content=blueprint.materials[0].content + "\nA new line."
    )
    changed = replace(
        blueprint, materials=(changed_material, *blueprint.materials[1:])
    )
    assert changed.materialize_game().content_hash != game.content_hash

    drifted = replace(
        blueprint,
        arc=(replace(blueprint.arc[0], evidence_ids=()), *blueprint.arc[1:]),
    )
    assert "authoring.arc-reveal-drift" in {
        item.code for item in validate_blueprint(drifted)
    }
    duplicated_owner = blueprint.to_mapping()
    duplicated_owner["game"]["kernel"]["resources"] = []
    with pytest.raises(ValueError, match="Materials derive them"):
        GameBlueprint.from_mapping(duplicated_owner)


def test_authoring_operations_are_requirement_complete_and_domain_sized():
    """stage9.operations: agents return typed, attributable operations, not opaque rewrites."""
    baseline = worked_blueprint()
    requirement_id = "requirement:phase-voice"
    revised_text = baseline.materials[0].content.replace(
        "she admits", "she pauses, corrects the time twice, and finally admits"
    )
    proposal = BlueprintProposal(
        (
            AuthoringOperation(
                "rewrite-closing-interview",
                "upsert_material",
                (requirement_id,),
                "Make the account sound like a pressured witness rather than a summary.",
                {
                    **baseline.materials[0].to_mapping(),
                    "content": revised_text,
                },
            ),
        ),
        "Improve character voice without changing the represented facts.",
    )
    child = apply_blueprint_proposal(
        baseline, proposal, required_requirement_ids=(requirement_id,)
    )
    assert validate_blueprint(child) == ()
    assert next(
        item.content for item in child.materials if item.resource_id == "closing-interview"
    ) == revised_text
    assert child.materialize_game().truth_model == baseline.materialize_game().truth_model

    with pytest.raises(ValueError, match="requires at least one operation"):
        apply_blueprint_proposal(
            baseline, replace(proposal, operations=()), required_requirement_ids=(requirement_id,)
        )


def test_profile_adapter_builds_complete_deterministic_rich_text_package(tmp_path):
    """stage9.adapter: one reusable adapter compiles, prints, blinds, and gates a Blueprint."""
    adapter = FacilitatedInvestigationAuthoringAdapter()
    first = adapter.build(
        worked_blueprint().to_mapping(), scratch_root=tmp_path / "a", instrument=instrument()
    )
    second = adapter.build(
        worked_blueprint().to_mapping(), scratch_root=tmp_path / "b", instrument=instrument()
    )
    assert first.candidate_id == second.candidate_id
    assert first.release_bytes == second.release_bytes
    assert first.physical_archive == second.physical_archive
    assert first.blind_trial.archive_bytes == second.blind_trial.archive_bytes
    assert first.hard_gate_results == {code: True for code in instrument().hard_gate_codes}
    assert first.blind_trial.file("trial/materials/closing-interview").data.startswith(
        b"# Closing interview"
    )
    script = """
import json
from pathlib import Path
import runpy
from narrative_game.contracts import digest_bytes
from narrative_game.profiles import FacilitatedInvestigationAuthoringAdapter
fixture = runpy.run_path('tests/test_stage9_authoring.py')
package = FacilitatedInvestigationAuthoringAdapter().build(
    fixture['worked_blueprint']().to_mapping(),
    scratch_root=Path('.'),
    instrument=fixture['instrument'](),
)
print(json.dumps({
    'candidate': package.candidate_id,
    'release': digest_bytes(package.release_bytes),
    'physical': digest_bytes(package.physical_archive),
    'trial': digest_bytes(package.blind_trial.archive_bytes),
}, sort_keys=True))
"""
    process_results = []
    for hash_seed in ("1", "987654"):
        environment = dict(os.environ, PYTHONHASHSEED=hash_seed)
        process_results.append(
            subprocess.check_output(
                [sys.executable, "-c", script],
                cwd=Path.cwd(),
                env=environment,
            )
        )
    assert process_results[0] == process_results[1]


class JudgeDriver:
    def invoke(self, invocation):
        parsed = {
            "scores": {"world_coherence": 55},
            "findings": [
                {
                    "requirement_code": "character.witness-voice",
                    "severity": "major",
                    "resource_path": "trial/materials/closing-interview",
                    "locus": "opening paragraph",
                    "quote": "Mara Vale says she returned after a late call",
                    "message": "The witness account reads as a neutral plot summary.",
                }
            ],
        }
        return DriverOutput("fixture", "stage9-judge-v1", "live-model", canonical_json(parsed), parsed)


class BuilderDriver:
    def invoke(self, invocation):
        requirement = invocation.context["requirements"]["requirements"][0]
        baseline = json.loads(invocation.attachments[0].data)["blueprint"]
        material = next(
            item for item in baseline["materials"] if item["resource_id"] == "closing-interview"
        )
        material["content"] = material["content"].replace(
            "Mara Vale says she returned",
            "Mara Vale first insists she never returned, then corrects herself and says she returned",
        )
        parsed = {
            "schema_version": "0.9",
            "rationale": "Give the witness a self-protective voice while preserving every fact.",
            "operations": [
                {
                    "operation_id": "revise-witness-voice",
                    "kind": "upsert_material",
                    "requirement_ids": [requirement["requirement_id"]],
                    "rationale": "Replace neutral summary language with an observable correction.",
                    "payload": material,
                }
            ],
        }
        return DriverOutput("fixture", "stage9-builder-v1", "capability-fixture", canonical_json(parsed), parsed)


class PassingJudgeDriver:
    def invoke(self, invocation):
        parsed = {"scores": {"world_coherence": 80}, "findings": []}
        return DriverOutput(
            "fixture", "stage9-fresh-judge-v1", "live-model", canonical_json(parsed), parsed
        )


class VisualJudgeDriver:
    def __init__(self, *, include_inspection: bool) -> None:
        self.include_inspection = include_inspection

    def invoke(self, invocation):
        parsed = {"scores": {"world_coherence": 80}, "findings": []}
        if self.include_inspection:
            with zipfile.ZipFile(BytesIO(invocation.attachments[0].data)) as archive:
                parsed["print_inspection"] = [
                    {
                        "resource_path": path,
                        "page_count": len(PdfReader(BytesIO(archive.read(path))).pages),
                        "visual_observation": (
                            "The rendered page uses a legible hierarchy and stable margins."
                        ),
                    }
                    for path in sorted(
                        name
                        for name in archive.namelist()
                        if name.startswith("trial/print/") and name.endswith(".pdf")
                    )
                ]
        return DriverOutput(
            "fixture", "stage9-visual-judge-v1", "live-model",
            canonical_json(parsed), parsed,
        )


def test_visual_panel_requires_a_verified_receipt_for_every_print_pdf(tmp_path):
    """generation.production-visual-inspection: a production panel cannot
    submit text-only scores without accounting for every exact print PDF."""
    production_instrument = replace(
        instrument(),
        blind_protocol={
            **instrument().blind_protocol,
            "inspect_print_renditions": True,
        },
    )
    adapter = FacilitatedInvestigationAuthoringAdapter()
    experiment = Experiment.create(
        tmp_path / "experiment",
        experiment_id="visual-inspection-contract",
        profile_id=adapter.profile_id,
        profile_version=adapter.profile_version,
        instrument=production_instrument,
        initial_data=worked_blueprint().to_mapping(),
        component_lock=adapter.component_lock,
        reviewer=Authority("maker", "human", "reviewer", "game-maker"),
    )
    _, binding = experiment.build_and_bind(
        adapter, scratch_root=tmp_path / "build", idempotency_key="bind"
    )
    with pytest.raises(ValueError, match="panel contract"):
        experiment.measure_model_panel(
            binding_id=binding.binding_id,
            task_key="text-only-panel",
            members=(
                ModelPanelMember(
                    "text-only-judge", "text-only-principal", "judge-v1",
                    "world-coherence", VisualJudgeDriver(include_inspection=False),
                ),
            ),
        )
    measured = experiment.measure_model_panel(
        binding_id=binding.binding_id,
        task_key="visual-panel",
        members=(
            ModelPanelMember(
                "visual-judge", "visual-principal", "judge-v1",
                "world-coherence", VisualJudgeDriver(include_inspection=True),
            ),
        ),
    )
    assert measured.evaluation.outcome == "pass"


def translate(evaluation, findings):
    return (
        Requirement(
            "character.distinct-witness-voice",
            "Witness-authored accounts express situated knowledge and self-interest.",
            "A neutral plot summary erases character agency and weakens realism.",
            "Revise the witness account's voice without changing world truth.",
            tuple(item.finding_id for item in findings),
        ),
    )


def test_agentic_authoring_stops_at_human_review_before_child_transition(tmp_path):
    """stage9.human-control: model operations preview a child; only human Review advances it."""
    adapter = FacilitatedInvestigationAuthoringAdapter()
    experiment = Experiment.create(
        tmp_path / "experiment",
        experiment_id="stage9-worked-authoring",
        profile_id=adapter.profile_id,
        profile_version=adapter.profile_version,
        instrument=instrument(),
        initial_data=worked_blueprint().to_mapping(),
        component_lock=adapter.component_lock,
        reviewer=Authority("maker", "human", "reviewer", "game-maker"),
    )
    baseline_package, baseline_binding = experiment.build_and_bind(
        adapter, scratch_root=tmp_path / "baseline", idempotency_key="bind-baseline"
    )
    measured = experiment.measure_model_panel(
        binding_id=baseline_binding.binding_id,
        task_key="measure-baseline",
        members=(
            ModelPanelMember(
                "blind-judge",
                "independent-judge",
                "judge-v1",
                "world-coherence",
                JudgeDriver(),
            ),
        ),
    )
    baseline_draft = experiment.current_draft_ref
    prepared = experiment.propose_revision(
        adapter,
        evaluation_id=measured.evaluation.evaluation_id,
        translator=translate,
        task_key="improve-witness-voice",
        authority_id="authoring-agent",
        principal="game-builder",
        requested_model="builder-v1",
        driver=BuilderDriver(),
        scratch_root=tmp_path / "preview",
        human_direction="Preserve the answer and make the witness more self-protective.",
    )
    assert experiment.current_draft_ref == baseline_draft
    assert prepared.preview.candidate_id != baseline_package.candidate_id
    review = experiment.review_proposal(
        proposal_id=prepared.proposal.proposal_id,
        reviewer_authority_id="maker",
        decision="approved",
        reason="The exact voice revision preserves truth and improves the intended characterization.",
    )
    experiment.apply_review(
        adapter,
        proposal_id=prepared.proposal.proposal_id,
        review_id=review.review_id,
        idempotency_key="approve-witness-voice",
    )
    child, child_binding = experiment.build_and_bind(
        adapter, scratch_root=tmp_path / "child", idempotency_key="bind-child"
    )
    assert child.candidate_id == prepared.preview.candidate_id
    child_measurement = experiment.measure_model_panel(
        binding_id=child_binding.binding_id,
        task_key="measure-child",
        members=(
            ModelPanelMember(
                "fresh-child-judge",
                "independent-child-judge",
                "judge-v1",
                "world-coherence",
                PassingJudgeDriver(),
            ),
        ),
    )
    decision = experiment.select(
        baseline_evaluation_id=measured.evaluation.evaluation_id,
        child_evaluation_id=child_measurement.evaluation.evaluation_id,
    )
    assert decision.outcome == "select_child"
    assert decision.selected_candidate_id == child.candidate_id
    assert experiment.verify()["ok"]
