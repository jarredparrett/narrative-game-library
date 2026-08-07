"""End-to-end capabilities for resumable agentic game generation."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from narrative_game.adapters import VerismillArtifactSuiteImporter
from narrative_game.climb import Dimension, DriverOutput, FrozenInstrument, Requirement
from narrative_game.contracts import ArtifactResult, digest_bytes
from narrative_game.blueprint import (
    DisplayedClaim,
    GameBlueprint,
    bind_artifact_specification,
)
from narrative_game.examples import vanished_ledger_blueprint
from narrative_game.generation import (
    ArtifactPlan,
    ArtifactSpecification,
    CreativeBrief,
    GenerationBudget,
    GenerationCoordinator,
    GenerationDrivers,
    GenerationPlan,
    ModelRoleAssignment,
    StopPolicy,
)
from narrative_game.profiles import FacilitatedInvestigationAuthoringAdapter


def _instrument() -> FrozenInstrument:
    return FrozenInstrument(
        "generated-game-quality",
        "1.0.0",
        "complete anonymous generated game",
        (
            Dimension(
                "world_coherence",
                "The represented world, play flow, and materials agree.",
                1,
                {"0": "contradictory", "60": "usable", "100": "expert-resistant"},
            ),
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 70},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "cover_story": "Anonymous facilitated investigation",
            "panel_size": 1,
            "panel_lenses": ["world-coherence"],
            "panel_aggregation": "median-per-dimension-v1",
            "selection_evidence_classes": ["live-model"],
        },
        ("authoring.valid", "compiler.valid", "physical.valid", "blind.valid"),
    )


def _brief() -> CreativeBrief:
    blueprint = vanished_ledger_blueprint()
    game = blueprint.materialize_game()
    return CreativeBrief(
        game.kernel.title,
        game.direction.premise,
        game.direction.experience_targets,
        game.direction.content_boundaries,
        len(game.profile.supported_seat_ids),
        sum(item.target_minutes for item in blueprint.arc),
        "hybrid",
        blueprint.seed,
    )


def _roles() -> tuple[ModelRoleAssignment, ...]:
    return (
        ModelRoleAssignment("builder", "creator", "fixture", "creator-v1", "creator-agent", "creator-context"),
        ModelRoleAssignment("reviewer", "reviewer", "fixture", "reviewer-v1", "reviewer-agent", "reviewer-context"),
        ModelRoleAssignment("judge", "judge", "fixture", "judge-v1", "judge-agent", "judge-context"),
    )


class CreatorDriver:
    def __init__(self, blueprint):
        self.blueprint = blueprint
        self.calls = 0

    def invoke(self, invocation):
        self.calls += 1
        if invocation.tool_contract["schema_version"] == "0.1":
            parsed = {
                "schema_version": "0.1",
                "rationale": "A complete coherent first candidate from the frozen brief.",
                "blueprint": self.blueprint.to_mapping(),
            }
        else:
            requirement_id = invocation.context["requirements"]["requirements"][0][
                "requirement_id"
            ]
            authoring = json.loads(
                next(
                    item.data
                    for item in invocation.attachments
                    if item.path == "authoring-package.json"
                )
            )
            material = GameBlueprint.from_mapping(authoring["blueprint"]).materials[0]
            revision_index = self.calls - 1
            parsed = {
                "schema_version": "0.9",
                "rationale": "Clarify the observed record while preserving canonical facts.",
                "operations": [
                    {
                        "operation_id": f"clarify-first-material-{revision_index}",
                        "kind": "upsert_material",
                        "requirement_ids": [requirement_id],
                        "rationale": "Make the material's evidentiary purpose explicit.",
                        "payload": {
                            **material.to_mapping(),
                            "content": material.content
                            + f"\n\nClerk's verification {revision_index}: sequence checked.",
                        },
                    }
                ],
            }
        return DriverOutput(
            "fixture",
            "creator-resolved",
            "live-model",
            json.dumps(parsed).encode(),
            parsed,
            usage={"input_tokens": 80, "output_tokens": 120},
            agent_id="creator-agent",
            context_id="creator-context",
        )


class ReviewerDriver:
    def __init__(self):
        self.calls = 0

    def invoke(self, invocation):
        self.calls += 1
        parsed = {
            "decision": "approved",
            "reason": "The complete Blueprint satisfies the brief and is internally coherent.",
        }
        return DriverOutput(
            "fixture",
            "reviewer-resolved",
            "live-model",
            json.dumps(parsed).encode(),
            parsed,
            usage={"total_tokens": 90},
            agent_id="reviewer-agent",
            context_id="reviewer-context",
        )


class JudgeDriver:
    def __init__(self, *, interrupt_child_once: bool = False):
        self.calls = 0
        self.interrupt_child_once = interrupt_child_once

    def invoke(self, invocation):
        self.calls += 1
        if self.calls == 1:
            with ZipFile(BytesIO(invocation.attachments[0].data)) as archive:
                path = "trial/materials/closing-interview"
                visible = archive.read(path).decode("utf-8")
            quote = next(
                line.strip() for line in visible.splitlines() if len(line.strip()) > 20
            )
            parsed = {
                "scores": {"world_coherence": 55},
                "findings": [
                    {
                        "requirement_code": "world.coherence",
                        "severity": "major",
                        "resource_path": path,
                        "locus": "opening account",
                        "quote": quote,
                        "message": "The account needs a clearer verification cue.",
                    }
                ],
            }
        elif self.interrupt_child_once and self.calls == 2:
            self.interrupt_child_once = False
            raise RuntimeError("simulated child-panel interruption")
        else:
            parsed = {"scores": {"world_coherence": 88}, "findings": []}
        return DriverOutput(
            "fixture",
            "judge-resolved",
            "live-model",
            json.dumps(parsed).encode(),
            parsed,
            usage={"total_tokens": 110},
            agent_id="judge-agent",
            context_id="judge-context",
        )


class SequenceJudgeDriver:
    def __init__(self, scores):
        self.scores = tuple(scores)
        self.calls = 0

    def invoke(self, invocation):
        score = self.scores[self.calls]
        self.calls += 1
        findings = []
        if score < 70:
            with ZipFile(BytesIO(invocation.attachments[0].data)) as archive:
                path = "trial/materials/closing-interview"
                visible = archive.read(path).decode("utf-8")
            quote = next(
                line.strip() for line in visible.splitlines() if len(line.strip()) > 20
            )
            findings = [
                {
                    "requirement_code": "world.coherence",
                    "severity": "major",
                    "resource_path": path,
                    "locus": "opening account",
                    "quote": quote,
                    "message": "The account needs a clearer verification cue.",
                }
            ]
        parsed = {"scores": {"world_coherence": score}, "findings": findings}
        return DriverOutput(
            "fixture",
            "judge-resolved",
            "live-model",
            json.dumps(parsed).encode(),
            parsed,
            usage={"total_tokens": 110},
            agent_id="judge-agent",
            context_id="judge-context",
        )


def test_brief_to_passing_candidate_is_resumable_and_fully_receipted(tmp_path):
    """generation.coordinator: a brief reaches a passing Candidate without a human gate."""
    brief = _brief()
    plan = GenerationPlan(
        "brief-to-game",
        FacilitatedInvestigationAuthoringAdapter.profile_id,
        FacilitatedInvestigationAuthoringAdapter.profile_version,
        brief.seed,
        _roles(),
        GenerationBudget(6, 2_000, 2),
        StopPolicy(2),
        ArtifactPlan((), ()),
    )
    coordinator = GenerationCoordinator.create(
        tmp_path / "experiment",
        plan=plan,
        brief=brief,
        instrument=_instrument(),
        component_lock=FacilitatedInvestigationAuthoringAdapter.component_lock,
    )
    creator = CreatorDriver(vanished_ledger_blueprint())
    reviewer = ReviewerDriver()
    judge = JudgeDriver(interrupt_child_once=True)
    drivers = GenerationDrivers(
        {"creator": creator, "reviewer": reviewer, "judge": judge}
    )
    translate = lambda evaluation, findings: (
        Requirement(
            "world.coherence",
            "visible records carry an intelligible verification cue",
            "a record reads as an unsupported narrative convenience",
            "Make the record's verification cue explicit without changing facts.",
            (findings[0].finding_id,),
        ),
    )
    with pytest.raises(RuntimeError, match="child-panel interruption"):
        coordinator.run(
            FacilitatedInvestigationAuthoringAdapter(),
            drivers=drivers,
            translator=translate,
            scratch_root=tmp_path / "scratch",
        )

    resumed = GenerationCoordinator.open(tmp_path / "experiment")
    evaluation = resumed.run(
        FacilitatedInvestigationAuthoringAdapter(),
        drivers=drivers,
        translator=translate,
        scratch_root=tmp_path / "scratch-resumed",
    )
    assert evaluation.outcome == "pass"
    assert creator.calls == reviewer.calls == 2
    assert judge.calls == 3
    selection = coordinator.experiment.ledger.snapshot()["selections"][-1]
    assert selection.outcome == "select_child"
    assert coordinator.experiment.verify()["ok"]

    reopened = GenerationCoordinator.open(tmp_path / "experiment")
    repeated = reopened.run(
        FacilitatedInvestigationAuthoringAdapter(),
        drivers=drivers,
        translator=lambda evaluation, findings: (),
        scratch_root=tmp_path / "scratch-replay",
    )
    assert repeated.evaluation_id == evaluation.evaluation_id
    assert creator.calls == reviewer.calls == 2
    assert judge.calls == 3
    status = json.loads((tmp_path / "experiment/generation-status.json").read_text())
    assert status["phase"] == "passed"
    assert status["release_qualification"] == {
        "target": "development",
        "status": "development_only",
        "production_candidate_ready": False,
    }
    assert status["budget"] == {
        "model_calls_used": 6,
        "model_calls_remaining": 0,
        "rounds_used": 1,
        "rounds_remaining": 1,
        "tokens_used": 800,
        "tokens_remaining": 1_200,
    }
    assert status["selected_candidate_id"] == evaluation.candidate_id


def test_rejected_child_never_becomes_the_next_round_parent(tmp_path):
    """generation.selection-lineage: every new rung branches from the selected Draft."""
    brief = _brief()
    plan = GenerationPlan(
        "selection-controls-lineage",
        FacilitatedInvestigationAuthoringAdapter.profile_id,
        FacilitatedInvestigationAuthoringAdapter.profile_version,
        brief.seed,
        _roles(),
        GenerationBudget(9, 3_000, 3),
        StopPolicy(2),
        ArtifactPlan((), ()),
    )
    coordinator = GenerationCoordinator.create(
        tmp_path / "experiment",
        plan=plan,
        brief=brief,
        instrument=_instrument(),
        component_lock=FacilitatedInvestigationAuthoringAdapter.component_lock,
    )
    creator = CreatorDriver(vanished_ledger_blueprint())
    drivers = GenerationDrivers(
        {
            "creator": creator,
            "reviewer": ReviewerDriver(),
            "judge": SequenceJudgeDriver((55, 40, 88)),
        }
    )
    evaluation = coordinator.run(
        FacilitatedInvestigationAuthoringAdapter(),
        drivers=drivers,
        translator=lambda evaluation, findings: (
            Requirement(
                "world.coherence",
                "visible records carry an intelligible verification cue",
                "a record reads as an unsupported narrative convenience",
                "Make the record's verification cue explicit without changing facts.",
                (findings[0].finding_id,),
            ),
        ),
        scratch_root=tmp_path / "scratch",
    )
    snapshot = coordinator.experiment.ledger.snapshot()
    assert [item.outcome for item in snapshot["selections"]] == [
        "retain_baseline",
        "select_child",
    ]
    revision_proposals = [
        item
        for item in snapshot["proposals"]
        if coordinator.experiment.ledger.get("task", item.task_id).value.kind == "fix"
    ]
    assert len(revision_proposals) == 2
    assert revision_proposals[1].baseline_draft_ref == (
        revision_proposals[0].baseline_draft_ref
    )
    current = GameBlueprint.from_mapping(coordinator.experiment.current_draft_data)
    assert current.materials[0].content.count("Clerk's verification") == 1
    assert evaluation.candidate_id == snapshot["selections"][-1].selected_candidate_id
    assert any(
        event["event_type"] == "branch_selected"
        for event in coordinator.experiment.workspace.lineage.read()
    )
    assert coordinator.experiment.verify()["ok"]


def _pdf() -> bytes:
    return (
        Path(__file__).parents[1]
        / "examples/winter-observatory-candidate-6/documents/01-night-observing-log.pdf"
    ).read_bytes()


def test_accepted_artifact_suite_replaces_source_text_at_compilation(tmp_path):
    """generation.artifacts: accepted PDFs replace authoring text without blending standing."""
    source_blueprint = vanished_ledger_blueprint()
    specification = bind_artifact_specification(
        source_blueprint,
        ArtifactSpecification(
            artifact_id="cash-receipt-facsimile",
            resource_id="cash-receipt",
            document_class="1990s-cash-receipt",
            seed=6103,
            proposition_ids=("cash-payment",),
            event_ids=("payment-made",),
            pins={},
            canon={
                "represented_date": "1997-10-14",
                "amount": "$4,000 cash",
            },
            accessibility={"required": True},
            permitted_audience_ids=("avery", "host"),
        ),
    )
    blueprint = replace(
        source_blueprint,
        displayed_claims=tuple(
            DisplayedClaim(
                item.resource_id,
                item.proposition_id,
                "",
                "artifact-request",
                "canon.amount",
            )
            if item.resource_id == specification.resource_id
            else item
            for item in source_blueprint.displayed_claims
        ),
        artifact_specifications=(specification,),
    )
    document = _pdf()
    content_hash = digest_bytes(document)
    request = {
        "artifact_id": specification.artifact_id,
        "document_class": specification.document_class,
        "seed": specification.seed,
        "pins": dict(specification.pins),
        "canon": dict(specification.canon),
        "metadata": {
            "narrative_truth_binding": specification.truth_binding,
        },
        "fact_references": [
            *specification.proposition_ids,
            *specification.event_ids,
        ],
    }
    result = ArtifactResult(
        specification.artifact_id,
        document,
        {"sha256": content_hash},
        {
            "artifact_hash": content_hash,
            "measurement": {"status": "accepted"},
            "verification": {"ok": True},
        },
        request,
    )
    suite_attestation = {
        "suite_id": "fixture-suite",
        "qualification": {"release_ready": True, "status": "accepted"},
    }

    class Suite:
        def verify(self):
            return {"ok": True}

        def attestation(self):
            return suite_attestation

        def artifact_results(self):
            return {
                "cash_receipt": {
                    "artifact": result.document,
                    "manifest": {
                        **dict(result.manifest),
                        "class": specification.document_class,
                        "seed": specification.seed,
                        "pins": dict(specification.pins),
                        "canon": dict(specification.canon),
                    },
                    "attestation": dict(result.attestation),
                }
            }

    artifact_plan = ArtifactPlan((specification,), (specification.artifact_id,))
    importer = VerismillArtifactSuiteImporter(
        Suite(), {specification.artifact_id: "cash_receipt"}
    )
    stale_mapping = blueprint.to_mapping()
    next(
        item
        for item in stale_mapping["game"]["narrative"]["events"]
        if item["id"] == "payment-made"
    )["summary"] = "A changed event that the imported suite never expressed."
    with pytest.raises(ValueError, match="stale canonical truth binding"):
        importer.import_suite(artifact_plan, GameBlueprint.from_mapping(stale_mapping))

    materialization = importer.import_suite(artifact_plan, blueprint)
    with pytest.raises(ValueError, match="embedded text or OCR"):
        materialization.validate_production_for(artifact_plan)
    package = FacilitatedInvestigationAuthoringAdapter(
        materialization
    ).build(blueprint.to_mapping(), scratch_root=tmp_path, instrument=_instrument())
    assert package.hard_gate_results == {
        code: True for code in _instrument().hard_gate_codes
    }
    assert content_hash.encode() in package.release_bytes
    with ZipFile(BytesIO(package.physical_archive)) as archive:
        player_visible = archive.read("print/resources/cash-receipt.pdf")
        preflight = json.loads(archive.read("trusted/preflight.json"))
        claim_trace = json.loads(archive.read("trusted/claim-trace.json"))
    assert player_visible == document
    exact = next(
        item for item in preflight["files"]
        if item["path"] == "print/resources/cash-receipt.pdf"
    )["pdf_checks"]["exact_attested_bytes"]
    assert exact == {
        "executed": True,
        "source_content_hash": content_hash,
        "player_visible_content_hash": content_hash,
        "passed": True,
    }
    claim = next(
        item for item in claim_trace["claims"]
        if item["resource_id"] == specification.resource_id
    )
    assert claim["verified_evidence"]["pin"] == "canon.amount"
    assert claim["verified_evidence"]["value"] == "$4,000 cash"
