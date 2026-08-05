"""Stage 7 builder repair preserves blindness and stops at human review."""

from __future__ import annotations

import pytest

from narrative_game.climb import DriverOutput, Finding
from narrative_game.contracts import canonical_json
from narrative_game.stage5_fixture import DEFAULT_SOURCE
from narrative_game.stage7_experiment import (
    prepare_baseline,
    prepare_stage7_proposal,
    review_stage7_proposal,
)


class RepairDriver:
    def invoke(self, invocation):
        assert invocation.role == "builder"
        assert "finding" not in invocation.context
        context = canonical_json(invocation.context).decode()
        assert "finding_id" not in context
        assert "Daniel Novak" not in context
        parsed = {
            "scenario_replacements": [
                {"path": "/scenario/narrative/reveals/3/phase_id", "value": "investigation"}
            ],
            "material_overrides": {
                "accusation-form": "# Joint finding\n\nWho removed the ledger?\n\nWhy?\n\nName three records that support your conclusion.\n",
                "closing-interview": "# Follow-up interview\n\n**Interviewer:** Why did you return?\n\n**Noel Voss:** I said the alarm panel called me.\n\n**Interviewer:** The log shows no call.\n",
                "host-guide": "# Host guide\n\nPlace the closing interview in the shared investigation envelope.\n",
                "host-guide": (DEFAULT_SOURCE / "content/host-guide.md").read_text().replace(
                    "Put the key register and closing interview in the shared opening folder.",
                    "Put the key register in the shared opening folder. Put the Closing interview in the investigation envelope.",
                ),
            },
            "artifact_pin_overrides": {"grantor_married": False},
            "rationale": "Clarifies artifact roles, uses player-facing resolution language, and defers admissions so evidence must be combined.",
        }
        return DriverOutput(
            "capability-driver",
            "recorded-builder-v1",
            "capability-fixture",
            canonical_json(parsed),
            parsed,
        )


class UnsynchronizedGuideDriver(RepairDriver):
    def invoke(self, invocation):
        output = super().invoke(invocation)
        parsed = dict(output.parsed_output)
        overrides = dict(parsed["material_overrides"])
        overrides.pop("host-guide")
        parsed["material_overrides"] = overrides
        return DriverOutput(
            output.provider,
            output.resolved_model,
            output.evidence_class,
            canonical_json(parsed),
            parsed,
        )


def _record_source_findings(prepared):
    records = (
        Finding("investigative_coherence", "major", "trial/materials/madison-deed-1997", "party table", "Daniel Novak", "ambiguous party roles"),
        Finding("production_realism", "minor", "trial/print/madison-deed-1997.pdf", "party table", "Daniel Novak", "printed ambiguity"),
        Finding("deduction_quality", "major", "trial/seats/avery.json", "opening evidence", "key-register", "later evidence is unframed"),
        Finding("character_agency", "major", "trial/seats/blake.json", "opening evidence", "key-register", "role evidence is unframed"),
        Finding("production_realism", "minor", "trial/materials/accusation-form", "resolution fields", "Selected hypothesis ID", "engine language leaks"),
        Finding("production_realism", "minor", "trial/print/accusation-form.pdf", "resolution fields", "Selected hypothesis ID", "printed engine language leaks"),
        Finding("deduction_quality", "major", "trial/schedule.json", "opening delivery", "closing-interview", "answer arrives early"),
        Finding("deduction_quality", "major", "trial/materials/closing-interview", "final exchange", "old transfer", "answer is pre-resolved"),
    )
    for index, finding in enumerate(records):
        prepared.ledger.register(
            finding,
            actor="agent:fixture-judge",
            idempotency_key=f"fixture-finding-{index}",
        )


def test_builder_receives_answer_safe_requirements_and_stops_at_proposal(tmp_path):
    """stage7.human-gate: a rebuildable agent Proposal cannot advance canonical state."""
    prepared = prepare_baseline(tmp_path / "stage7")
    _record_source_findings(prepared)
    result = prepare_stage7_proposal(
        tmp_path / "stage7", RepairDriver(), requested_model="configured-builder"
    )
    snapshot = result.ledger.snapshot()
    assert len(snapshot["requirements"]) == 4
    assert len(snapshot["proposals"]) == 1
    assert snapshot["reviews"] == ()
    assert snapshot["transitions"] == ()
    assert result.workspace.branches["main"] == result.proposal.baseline_draft_ref
    assert result.summary["status"] == "awaiting-human-review"
    proposed_data = result.workspace.store.read_json(result.proposal.proposed_data_ref)
    assert "proposal_summary" not in proposed_data
    assert result.summary["hard_gates"] == {
        "compiler.release": True,
        "physical.preflight": True,
        "blind-trial.verify": True,
        "stage5.access": True,
    }
    seat = result.proposed_build.candidate.game
    assert next(item for item in seat.reveals if item.id == "reveal-interview").phase_id == "investigation"
    assert result.ledger.verify()["ok"]
    assert result.workspace.verify()["ok"]


def test_seat_projection_frames_new_evidence_by_phase(tmp_path):
    """stage7.seat-framing: every delivered artifact has phase-aware Seat context."""
    prepared = prepare_baseline(tmp_path / "stage7")
    release = prepared.release
    avery = release.file("projections/seats/avery.json").data.decode()
    blake = release.file("projections/seats/blake.json").data.decode()
    assert '"evidence_by_phase"' in avery
    assert '"resource_id":"payment-note"' in avery
    assert '"resource_id":"madison-deed-1997"' in avery
    assert '"resource_id":"camera-log"' in blake
    assert '"resource_id":"madison-deed-1997"' in blake


def test_human_rejection_is_preserved_before_a_fresh_revised_proposal(tmp_path):
    """stage7.human-feedback: rejected work remains lineage, not overwritten history."""
    prepared = prepare_baseline(tmp_path / "stage7")
    _record_source_findings(prepared)
    first = prepare_stage7_proposal(
        tmp_path / "stage7", RepairDriver(), requested_model="configured-builder"
    )
    review = review_stage7_proposal(
        tmp_path / "stage7",
        proposal_id=first.proposal.proposal_id,
        decision="rejected",
        reason="Explanatory text cannot substitute for a repair to the rendered artifact.",
    )
    second = prepare_stage7_proposal(
        tmp_path / "stage7",
        RepairDriver(),
        requested_model="configured-builder",
        task_key="repair-complete-baseline-b",
        authority_id="stage7-child-builder-b",
        human_direction=review.reason,
        require_artifact_pin_change=True,
        require_host_guide_sync=True,
    )
    snapshot = second.ledger.snapshot()
    assert review.decision == "rejected"
    assert len(snapshot["proposals"]) == 2
    assert len(snapshot["reviews"]) == 1
    assert snapshot["transitions"] == ()
    assert second.summary["artifact_pin_overrides"] == {"grantor_married": False}


class UnsynchronizedRepairDriver(RepairDriver):
    def invoke(self, invocation):
        output = super().invoke(invocation)
        parsed = dict(output.parsed_output)
        parsed["material_overrides"] = dict(parsed["material_overrides"])
        parsed["material_overrides"].pop("host-guide")
        return DriverOutput(
            output.provider,
            output.resolved_model,
            output.evidence_class,
            canonical_json(parsed),
            parsed,
        )


def test_reveal_timing_change_requires_synchronized_host_instructions(tmp_path):
    """stage7.host-guide-sync: reveal changes cannot contradict assembly instructions."""
    prepared = prepare_baseline(tmp_path / "stage7")
    _record_source_findings(prepared)
    with pytest.raises(ValueError, match="host guide to match"):
        prepare_stage7_proposal(
            tmp_path / "stage7",
            UnsynchronizedRepairDriver(),
            requested_model="configured-builder",
            task_key="repair-with-host-sync",
            authority_id="stage7-sync-builder",
            human_direction="Synchronize authored host instructions with the reveal schedule.",
            require_artifact_pin_change=True,
            require_host_guide_sync=True,
        )


def test_reveal_change_without_synchronized_host_instructions_is_rejected(tmp_path):
    """stage7.schedule-coherence: authored instructions move with structured reveals."""
    prepared = prepare_baseline(tmp_path / "stage7")
    _record_source_findings(prepared)
    with pytest.raises(ValueError, match="synchronized host-guide"):
        prepare_stage7_proposal(
            tmp_path / "stage7",
            UnsynchronizedGuideDriver(),
            requested_model="configured-builder",
        )
    assert prepared.ledger.snapshot()["proposals"] == ()
