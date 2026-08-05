"""Stage 7 fresh-panel measurement and frozen aggregation tests."""

from __future__ import annotations

from narrative_game.climb import DriverOutput
from narrative_game.contracts import canonical_json
from narrative_game.stage7_experiment import (
    PanelMember,
    complete_experience_panel_instrument,
    measure_stage7_blind_panel,
    prepare_baseline,
)


class PanelDriver:
    def __init__(self, scores, findings=()):
        self.scores = scores
        self.findings = list(findings)
        self.calls = 0

    def invoke(self, invocation):
        self.calls += 1
        parsed = {"scores": self.scores, "findings": self.findings}
        return DriverOutput(
            "fixture-provider",
            f"fixture-{invocation.authority_id}",
            "capability-fixture",
            canonical_json(parsed),
            parsed,
        )


def scores(value):
    return {
        "investigative_coherence": value,
        "deduction_quality": value,
        "character_agency": value,
        "facilitation_resilience": value,
        "production_realism": value,
    }


def test_fresh_panel_uses_three_identities_and_frozen_dimension_medians(tmp_path):
    """stage7.blind-panel: k=3 independent receipts produce the frozen median score."""
    prepared = prepare_baseline(tmp_path / "stage7")
    drivers = (PanelDriver(scores(76)), PanelDriver(scores(91)), PanelDriver(scores(82)))
    lenses = complete_experience_panel_instrument().blind_protocol["panel_lenses"]
    members = tuple(
        PanelMember(
            f"fresh-panel-{index}",
            f"fixture-principal-{index}",
            f"fixture-model-{index}",
            lens,
            driver,
        )
        for index, (lens, driver) in enumerate(zip(lenses, drivers), start=1)
    )
    measured = measure_stage7_blind_panel(
        tmp_path / "stage7",
        binding_id=prepared.binding.binding_id,
        task_key="fresh-baseline-panel",
        members=members,
    )
    assert measured.evaluation.scores == scores(82)
    assert measured.evaluation.outcome == "pass"
    assert len(measured.evaluation.judge_authority_ids) == 3
    assert len(measured.evaluation.model_receipt_ids) == 3
    assert all(driver.calls == 1 for driver in drivers)
    assert measured.ledger.verify()["ok"]
    assert measured.workspace.verify()["ok"]

    replayed = measure_stage7_blind_panel(
        tmp_path / "stage7",
        binding_id=prepared.binding.binding_id,
        task_key="fresh-baseline-panel",
        members=members,
    )
    assert replayed.evaluation == measured.evaluation
    assert all(driver.calls == 1 for driver in drivers)


def test_followup_translation_uses_only_finding_backed_requirement_categories(tmp_path):
    """stage7.answer-safe-followup: sparse panels do not invent unsupported repair categories."""
    from narrative_game.stage7_experiment import record_stage7_followup_requirements

    prepared = prepare_baseline(tmp_path / "stage7")
    findings = (
        {
            "requirement_code": "investigative_coherence",
            "severity": "major",
            "resource_path": "trial/materials/deed-accessible",
            "locus": "date row",
            "quote": "Execution date: October 17, 1997.",
            "message": "The represented chronology is not possible.",
        },
        {
            "requirement_code": "stage5.access",
            "severity": "major",
            "resource_path": "trial/materials/deed-accessible",
            "locus": "field omission",
            "quote": "READING COPY OF RECORDED INSTRUMENT",
            "message": "The accessible rendition omits a required comparison.",
        },
        {
            "requirement_code": "production_realism",
            "severity": "minor",
            "resource_path": "trial/materials/deed-accessible",
            "locus": "audience boundary",
            "quote": "Prepared for readers who cannot use the marked facsimile.",
            "message": "Pipeline language breaks the in-fiction boundary.",
        },
    )
    drivers = tuple(PanelDriver(scores(70), findings) for _ in range(3))
    lenses = complete_experience_panel_instrument().blind_protocol["panel_lenses"]
    members = tuple(
        PanelMember(
            f"sparse-panel-{index}",
            f"fixture-principal-{index}",
            f"fixture-model-{index}",
            lens,
            driver,
        )
        for index, (lens, driver) in enumerate(zip(lenses, drivers), start=1)
    )
    measured = measure_stage7_blind_panel(
        tmp_path / "stage7",
        binding_id=prepared.binding.binding_id,
        task_key="sparse-failed-panel",
        members=members,
    )
    requirements = record_stage7_followup_requirements(
        tmp_path / "stage7", evaluation_id=measured.evaluation.evaluation_id
    )
    assert {item.requirement_code for item in requirements} == {
        "artifact.in-fiction-boundary",
        "world.closed-verifiable-claims",
        "accessibility.equivalent-evidence",
    }
    assert all(item.source_finding_ids for item in requirements)
    assert measured.ledger.verify()["ok"]


def test_followup_translation_preserves_structural_tell_classes(tmp_path):
    """stage7.structural-followup: specific blind tells become answer-safe structural contracts."""
    from narrative_game.stage7_experiment import record_stage7_followup_requirements

    prepared = prepare_baseline(tmp_path / "stage7")
    findings = (
        {
            "requirement_code": "deduction_quality.single_suspect_convergence",
            "severity": "major",
            "resource_path": "trial/seats/blake.json",
            "locus": "opening hypothesis",
            "quote": "An outsider forced the records-room window.",
            "message": "Opening eliminates the only alternate explanation.",
        },
        {
            "requirement_code": "deduction_quality.payment_attribution",
            "severity": "major",
            "resource_path": "trial/materials/payment-note",
            "locus": "payment fragment",
            "quote": "N.V. - $2,000 after the Quillstone entry is out of the trustees' packet.",
            "message": "The payer is not independently attributable.",
        },
        {
            "requirement_code": "character_agency.mirrored_instruction_template",
            "severity": "minor",
            "resource_path": "trial/materials/blake-dossier",
            "locus": "opening instructions",
            "quote": "Test the outsider-entry theory against physical and camera evidence.",
            "message": "Both roles receive the same procedure.",
        },
        {
            "requirement_code": "facilitation_resilience.phase_recovery",
            "severity": "major",
            "resource_path": "trial/materials/avery-dossier",
            "locus": "phase transition",
            "quote": "Share documentary facts, but do not treat another character's hunch as established truth.",
            "message": "The host has no objective validation path.",
        },
        {
            "requirement_code": "production_realism.document_provenance",
            "severity": "minor",
            "resource_path": "trial/print/camera-log.pdf",
            "locus": "record identity",
            "quote": "Exterior camera log",
            "message": "The artifact combines unlike producing systems.",
        },
        {
            "requirement_code": "physical.preflight",
            "severity": "minor",
            "resource_path": "trial/schedule.json",
            "locus": "preflight scope",
            "quote": "\"preflight\":{\"files\"",
            "message": "The check omits visual usability properties.",
        },
    )
    drivers = tuple(PanelDriver(scores(70), findings) for _ in range(3))
    lenses = complete_experience_panel_instrument().blind_protocol["panel_lenses"]
    members = tuple(
        PanelMember(
            f"structural-panel-{index}",
            f"fixture-principal-{index}",
            f"fixture-model-{index}",
            lens,
            driver,
        )
        for index, (lens, driver) in enumerate(zip(lenses, drivers), start=1)
    )
    measured = measure_stage7_blind_panel(
        tmp_path / "stage7",
        binding_id=prepared.binding.binding_id,
        task_key="structural-failed-panel",
        members=members,
    )
    requirements = record_stage7_followup_requirements(
        tmp_path / "stage7", evaluation_id=measured.evaluation.evaluation_id
    )
    codes = {item.requirement_code for item in requirements}
    assert {
        "evidence.competing-hypotheses",
        "evidence.independent-attribution",
        "seat.role-distinct-decisions",
        "facilitation.operational-checkpoints",
        "artifact.single-system-provenance",
        "physical.preflight-coverage",
    } <= codes
    assert all(item.source_finding_ids for item in requirements)
    assert measured.ledger.verify()["ok"]
