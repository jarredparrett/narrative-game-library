"""Stage 6 persistence and human-authority tests for the climb ledger."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from narrative_game.climb import (
    Authority,
    ClimbLedger,
    ClimbRejected,
    Dimension,
    Finding,
    FrozenInstrument,
    HumanReview,
    Requirement,
    Task,
)
from narrative_game.contracts import digest_bytes
from narrative_game.workspace import IdempotencyConflict, Workspace


def component_lock() -> dict:
    return {
        "components": [
            {
                "id": "narrative-game-library",
                "version": "0.6.0",
                "implementation": digest_bytes(b"stage-6-fixture"),
            }
        ]
    }


def make_workspace(tmp_path: Path) -> tuple[Workspace, str]:
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="ashwood-climb")
    head = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={"title": "The Ashwood Ledger", "reveal_order": ["will", "ledger"]},
        reason="create Stage 6 baseline",
        actor="human:maker",
        component_lock=component_lock(),
        operation_receipt={"operation": "fixture.create", "seed": 17},
        idempotency_key="fixture-baseline",
    )
    return workspace, head


def seed_proposal(ledger: ClimbLedger, baseline: str):
    builder = Authority("builder-1", "agent", "builder", "fixture-builder")
    judge = Authority("judge-1", "agent", "judge", "fixture-judge")
    reviewer = Authority("reviewer-1", "human", "reviewer", "jarredparrett")
    instrument = FrozenInstrument(
        "complete-experience",
        "1.0.0",
        "worked-release",
        (
            Dimension("realism", "World and artifact realism", 60, {"0": "obvious", "100": "expert"}),
            Dimension("playability", "Playable evidence and pacing", 40, {"0": "blocked", "100": "robust"}),
        ),
        ({"metric": "overall", "operator": ">=", "value": 70},),
        {"judge_inputs": ["trial-tree"], "forbidden": ["answers", "atlas"]},
        ("stage5.access", "stage5.rebuild"),
    )
    finding = Finding(
        "world.reveal-order",
        "major",
        "game/ashwood-ledger",
        "act 2 transition",
        "the ledger appears before its meaning can be inferred",
        "The current reveal order makes the deduction automatic rather than earned.",
    )
    requirement = Requirement(
        "world.reveal-order",
        "Evidence sequencing preserves an inferential gap before the ledger resolves it.",
        "An early reveal collapses the central deduction.",
        "Sequence the corroborating artifact after players can form at least two live hypotheses.",
        (finding.finding_id,),
    )
    for index, authority in enumerate((builder, judge, reviewer), 1):
        ledger.register(authority, actor="human:maker", idempotency_key=f"authority-{index}")
    ledger.register(instrument, actor="human:maker", idempotency_key="instrument-1")
    ledger.register(finding, actor="agent:judge", idempotency_key="finding-1")
    ledger.register(requirement, actor="human:maker", idempotency_key="requirement-1")
    task = Task(
        "repair-reveal-order",
        "build",
        baseline,
        instrument.instrument_id,
        builder.authority_id,
        (),
        {"requirement": ledger.get("requirement", requirement.requirement_id).record_ref},
        requirement.builder_brief,
    )
    ledger.register(task, actor="human:maker", idempotency_key="task-1")
    receipt = ledger.record_model_invocation(
        authority_id=builder.authority_id,
        provider="fixture-provider",
        requested_model="builder-model",
        resolved_model="builder-model-2026-08-01",
        role="builder",
        prompt_hash=digest_bytes(b"builder prompt"),
        context_hash=digest_bytes(b"requirements only"),
        tool_contract_hash=digest_bytes(b"proposal schema"),
        input_hashes={"task": digest_bytes(task.to_mapping().__repr__().encode())},
        tool_receipt_hashes=(),
        raw_output=b'{"proposal":"delay ledger"}',
        parsed_output={"reveal_order": ["will", "witness", "ledger"]},
        seed=17,
        actor="agent:builder",
        idempotency_key="model-1",
    )
    proposal = ledger.record_proposal(
        task_id=task.task_id,
        baseline_draft_ref=baseline,
        proposed_data={"title": "The Ashwood Ledger", "reveal_order": ["will", "witness", "ledger"]},
        requirement_ids=(requirement.requirement_id,),
        builder_authority_id=builder.authority_id,
        model_receipt_id=receipt.record_id,
        rationale="Preserve two live hypotheses before the resolving artifact appears.",
        actor="agent:builder",
        idempotency_key="proposal-1",
    )
    return builder, judge, reviewer, instrument, task, requirement, receipt, proposal


def test_proposal_is_inert_until_exact_human_approval_advances_workspace(tmp_path):
    """stage6.human-transition: an agent Proposal cannot move canonical state."""
    workspace, baseline = make_workspace(tmp_path)
    ledger = ClimbLedger(workspace)
    builder, judge, reviewer, _, _, requirement, receipt, proposal = seed_proposal(ledger, baseline)
    assert workspace.branches["main"] == baseline

    with pytest.raises(ClimbRejected, match="human-authority-required"):
        ledger.register(
            HumanReview(proposal.record_id, judge.authority_id, "approved", "agent says yes", (requirement.requirement_id,)),
            actor="agent:judge",
            idempotency_key="invalid-agent-review",
        )
    assert workspace.branches["main"] == baseline

    rejected = HumanReview(
        proposal.record_id,
        reviewer.authority_id,
        "rejected",
        "The proposed order needs another human pass.",
        (),
    )
    ledger.register(rejected, actor="human:jarredparrett", idempotency_key="review-rejected")
    with pytest.raises(ClimbRejected, match="unauthorized-transition"):
        ledger.apply_approved_transition(
            proposal_id=proposal.record_id,
            review_id=rejected.review_id,
            branch="main",
            component_lock=component_lock(),
            idempotency_key="transition-rejected",
        )
    assert workspace.branches["main"] == baseline

    approved = HumanReview(
        proposal.record_id,
        reviewer.authority_id,
        "approved",
        "Human review confirms this is the bounded reveal-order repair.",
        (requirement.requirement_id,),
    )
    ledger.register(approved, actor="human:jarredparrett", idempotency_key="review-approved")
    transition = ledger.apply_approved_transition(
        proposal_id=proposal.record_id,
        review_id=approved.review_id,
        branch="main",
        component_lock=component_lock(),
        idempotency_key="transition-approved",
    )
    assert transition.child_draft_ref == workspace.branches["main"]
    assert transition.child_draft_ref != baseline
    revision = workspace.store.read_json(transition.child_draft_ref)
    operation = workspace.store.read_json(revision["operation_receipt"])
    assert operation["operation"] == "agentic-transition"
    assert operation["proposal"] == proposal.record_ref
    assert operation["model_receipt"] == receipt.record_ref
    assert workspace.lineage.read()[-1]["actor"] == "human:jarredparrett"
    assert ledger.verify()["ok"]
    assert workspace.verify()["ok"]


def test_climb_reopens_archives_and_preserves_exact_model_outputs(tmp_path):
    """stage6.portable-replay: climb evidence and raw receipts survive relocation."""
    workspace, baseline = make_workspace(tmp_path)
    ledger = ClimbLedger(workspace)
    *_, receipt, _ = seed_proposal(ledger, baseline)
    model = receipt.value
    assert workspace.store.read_bytes(model.raw_output_ref) == b'{"proposal":"delay ledger"}'
    assert workspace.store.read_json(model.parsed_output_ref) == {"reveal_order": ["will", "witness", "ledger"]}
    assert ClimbLedger(Workspace.open(workspace.root)).verify()["ok"]

    archive = tmp_path / "ashwood.ngw"
    workspace.export_archive(archive)
    imported = Workspace.import_archive(archive, tmp_path / "imported")
    imported_ledger = ClimbLedger(imported)
    assert imported.verify()["ok"]
    assert imported_ledger.verify() == ledger.verify()
    imported_receipt = imported_ledger.get("model_receipt", receipt.record_id).value
    assert imported.store.read_bytes(imported_receipt.raw_output_ref) == b'{"proposal":"delay ledger"}'


def test_climb_records_are_idempotent_and_conflicting_retries_fail(tmp_path):
    """stage6.climb-idempotency: retry keys cannot alias different evidence."""
    workspace, baseline = make_workspace(tmp_path)
    ledger = ClimbLedger(workspace)
    builder = Authority("builder-1", "agent", "builder", "fixture-builder")
    first = ledger.register(builder, actor="human:maker", idempotency_key="authority-1")
    retry = ledger.register(builder, actor="human:maker", idempotency_key="authority-1")
    assert retry.record_ref == first.record_ref
    assert len(ledger.journal.read()) == 1
    with pytest.raises(IdempotencyConflict):
        ledger.register(
            Authority("builder-2", "agent", "builder", "another-builder"),
            actor="human:maker",
            idempotency_key="authority-1",
        )
    assert workspace.branches["main"] == baseline


def test_climb_journal_tampering_is_detected_by_ledger_and_workspace(tmp_path):
    """stage6.climb-integrity: evidence history is hash chained and archive-load-bearing."""
    workspace, _ = make_workspace(tmp_path)
    ledger = ClimbLedger(workspace)
    ledger.register(
        Authority("builder-1", "agent", "builder", "fixture-builder"),
        actor="human:maker",
        idempotency_key="authority-1",
    )
    event = json.loads(workspace.climb.path.read_text().splitlines()[0])
    event["actor"] = "agent:forged"
    workspace.climb.path.write_text(json.dumps(event) + "\n")
    assert not ledger.verify()["ok"]
    assert not workspace.verify()["ok"]
