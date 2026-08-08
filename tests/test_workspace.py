"""Stage 1 acceptance tests for Workspace persistence and lineage."""

from __future__ import annotations

import json
from pathlib import Path
import threading

import pytest

from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.workspace import ConcurrencyConflict, IdempotencyConflict, Workspace


def component_lock() -> dict:
    return {
        "components": [
            {
                "id": "narrative-game-library",
                "version": "0.1.0",
                "implementation": "sha256:" + "1" * 64,
            }
        ]
    }


def receipt(operation: str) -> dict:
    return {
        "operation": operation,
        "inputs": {"fixture": "sha256:" + "2" * 64},
        "outputs": {},
        "seed": 17,
    }


def initial_workspace(tmp_path: Path) -> tuple[Workspace, str]:
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="micro-case")
    head = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={"title": "The Vanished Ledger", "facts": []},
        reason="create the minimum human-readable Draft",
        actor="human:maker",
        component_lock=component_lock(),
        operation_receipt=receipt("draft.create"),
        idempotency_key="draft-main-1",
    )
    return workspace, head


def test_content_addressed_store_detects_tampering_and_deduplicates(tmp_path):
    """stage1.object-integrity: immutable values are addressed only by bytes."""
    workspace = Workspace.create(tmp_path / "w", workspace_id="integrity")
    value = {"b": 2, "a": 1}
    first = workspace.store.put_json(value)
    second = workspace.store.put_bytes(canonical_json(value))
    assert first == second == digest_bytes(b'{"a":1,"b":2}')
    workspace.store.path_for(first).write_bytes(b"tampered")
    assert not workspace.store.verify(first)
    assert workspace.verify()["ok"] is False


def test_external_attestation_hashes_are_not_local_workspace_edges(tmp_path):
    """workspace.external-evidence: foreign content hashes remain opaque while
    their enclosing imported record stays content-addressed and verified."""
    workspace = Workspace.create(tmp_path / "external", workspace_id="external")
    external = workspace.store.put_json({
        "schema_version": "0.1",
        "kind": "external_artifact_attestation",
        "external_payload": {
            "candidate": "sha256:" + "1" * 64,
            "attestation": "sha256:" + "2" * 64,
            "verification": {"ok": True},
        },
    })
    workspace.operational.append(
        "external_artifact_imported",
        actor="test",
        payload={"attestation_ref": external},
        object_refs=(external,),
        idempotency_key="external-artifact-imported",
    )
    assert Workspace.open(workspace.root).verify()["ok"]


def test_draft_transitions_are_idempotent_branchable_and_human_readable(tmp_path):
    """stage1.lineage: immutable Draft transitions retain why and authority."""
    workspace, first = initial_workspace(tmp_path)
    retry = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={"title": "The Vanished Ledger", "facts": []},
        reason="create the minimum human-readable Draft",
        actor="human:maker",
        component_lock=component_lock(),
        operation_receipt=receipt("draft.create"),
        idempotency_key="draft-main-1",
    )
    assert retry == first
    assert len(workspace.lineage.read()) == 2
    workspace.create_branch(
        branch="alternate",
        from_revision=first,
        actor="human:maker",
        reason="test a different reveal order",
        idempotency_key="branch-alternate-1",
    )
    alternate = workspace.commit_draft(
        branch="alternate",
        expected_head=first,
        data={"title": "The Vanished Ledger", "facts": [], "reveal": "late"},
        reason="delay the ledger reveal",
        actor="human:maker",
        component_lock=component_lock(),
        operation_receipt=receipt("draft.revise"),
        idempotency_key="draft-alternate-2",
    )
    merged = workspace.commit_draft(
        branch="main",
        expected_head=first,
        additional_parents=(alternate,),
        data={"title": "The Vanished Ledger", "facts": [], "reveal": "reviewed"},
        reason="human-reviewed merge of the alternate reveal",
        actor="human:reviewer",
        component_lock=component_lock(),
        operation_receipt=receipt("draft.merge"),
        idempotency_key="draft-main-merge",
    )
    candidate = workspace.freeze_candidate(
        branch="main",
        expected_head=merged,
        actor="human:publisher",
        idempotency_key="candidate-main-1",
    )
    assert workspace.branches == {"alternate": alternate, "main": merged}
    assert workspace.candidates == [candidate]
    report = workspace.lineage_report()
    assert "human-reviewed merge" in report
    assert "human:reviewer" in report
    assert candidate in report
    assert workspace.verify()["ok"]


def test_stale_writes_are_rejected_and_audited(tmp_path):
    """stage1.optimistic-concurrency: stale writers never win silently."""
    workspace, first = initial_workspace(tmp_path)
    second = workspace.commit_draft(
        branch="main",
        expected_head=first,
        data={"title": "The Vanished Ledger", "facts": ["p1"]},
        reason="add the first Proposition",
        actor="human:maker",
        component_lock=component_lock(),
        operation_receipt=receipt("draft.revise"),
        idempotency_key="draft-main-2",
    )
    with pytest.raises(ConcurrencyConflict, match="Draft Head changed"):
        workspace.commit_draft(
            branch="main",
            expected_head=first,
            data={"title": "stale"},
            reason="stale edit",
            actor="agent:builder",
            component_lock=component_lock(),
            operation_receipt=receipt("draft.revise"),
            idempotency_key="draft-main-stale",
        )
    assert workspace.branches["main"] == second
    assert workspace.operational.read()[-1]["payload"]["reason"] == "stale_head"
    assert workspace.verify()["ok"]


def test_idempotency_key_cannot_name_different_content(tmp_path):
    """stage1.idempotency: retries are exact, never aliases for new work."""
    workspace, _ = initial_workspace(tmp_path)
    with pytest.raises(IdempotencyConflict):
        workspace.commit_draft(
            branch="main",
            expected_head=None,
            data={"title": "different"},
            reason="different operation",
            actor="human:maker",
            component_lock=component_lock(),
            operation_receipt=receipt("draft.create"),
            idempotency_key="draft-main-1",
        )


def test_candidate_retry_survives_later_branch_advancement(tmp_path):
    """stage1.idempotency: a completed freeze remains exactly retryable."""
    workspace, first = initial_workspace(tmp_path)
    candidate = workspace.freeze_candidate(
        branch="main",
        expected_head=first,
        actor="human:publisher",
        idempotency_key="candidate-main-1",
    )
    workspace.commit_draft(
        branch="main",
        expected_head=first,
        data={"title": "The Vanished Ledger", "facts": ["p1"]},
        reason="advance after freezing the first Candidate",
        actor="human:maker",
        component_lock=component_lock(),
        operation_receipt=receipt("draft.revise"),
        idempotency_key="draft-main-2",
    )
    retry = workspace.freeze_candidate(
        branch="main",
        expected_head=first,
        actor="human:publisher",
        idempotency_key="candidate-main-1",
    )
    assert retry == candidate
    assert workspace.candidates == [candidate]
    assert workspace.verify()["ok"]


def test_crash_after_journal_commit_leaves_reconstructable_state(tmp_path, monkeypatch):
    """stage1.atomic-transition: journal commit survives a projection crash."""
    workspace, first = initial_workspace(tmp_path)

    def fail_projection(manifest):
        raise OSError("simulated projection write failure")

    monkeypatch.setattr(workspace, "_write_manifest", fail_projection)
    with pytest.raises(OSError, match="simulated"):
        workspace.commit_draft(
            branch="main",
            expected_head=first,
            data={"title": "The Vanished Ledger", "facts": ["p1"]},
            reason="commit before simulated crash",
            actor="human:maker",
            component_lock=component_lock(),
            operation_receipt=receipt("draft.revise"),
            idempotency_key="draft-main-crash",
        )
    reopened = Workspace.open(workspace.root)
    assert reopened.branches["main"] != first
    assert reopened.verify()["ok"]


def test_index_rebuild_and_archive_import_are_path_independent(tmp_path):
    """stage1.portability: indexes rebuild and archives verify elsewhere."""
    workspace, first = initial_workspace(tmp_path)
    candidate = workspace.freeze_candidate(
        branch="main",
        expected_head=first,
        actor="human:publisher",
        idempotency_key="candidate-main-1",
    )
    first_archive = workspace.export_archive(tmp_path / "one.ngw")
    second_archive = workspace.export_archive(tmp_path / "two.ngw")
    assert Path(first_archive["archive"]).read_bytes() == Path(second_archive["archive"]).read_bytes()
    workspace.manifest_path.unlink()
    rebuilt = Workspace.open(workspace.root)
    assert rebuilt.candidates == [candidate]
    imported = Workspace.import_archive(tmp_path / "one.ngw", tmp_path / "elsewhere" / "game")
    assert imported.root != workspace.root
    assert imported.manifest == rebuilt.manifest
    assert len(list((imported.root / "imports").glob("*.json"))) == 1
    assert imported.verify()["ok"]


def test_competing_writers_produce_one_winner(tmp_path):
    """stage1.concurrent-writers: one expected Draft Head has one successor."""
    workspace, first = initial_workspace(tmp_path)
    barrier = threading.Barrier(2)
    results: list[tuple[str, str]] = []

    def writer(number: int) -> None:
        local = Workspace.open(workspace.root)
        barrier.wait()
        try:
            head = local.commit_draft(
                branch="main",
                expected_head=first,
                data={"title": "The Vanished Ledger", "writer": number},
                reason=f"writer {number}",
                actor=f"agent:{number}",
                component_lock=component_lock(),
                operation_receipt=receipt("draft.revise"),
                idempotency_key=f"concurrent-{number}",
            )
            results.append(("accepted", head))
        except ConcurrencyConflict:
            results.append(("rejected", str(number)))

    threads = [threading.Thread(target=writer, args=(number,)) for number in (1, 2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(result[0] for result in results) == ["accepted", "rejected"]
    reopened = Workspace.open(workspace.root)
    assert reopened.verify()["ok"]
    assert len(reopened.operational.read()) == 1


def test_journal_tampering_is_detected(tmp_path):
    """stage1.journal-integrity: edited history is never trusted."""
    workspace, _ = initial_workspace(tmp_path)
    text = workspace.lineage.path.read_text().replace(
        "create the minimum human-readable Draft", "rewrite history"
    )
    workspace.lineage.path.write_text(text)
    assert workspace.lineage.verify()[0] is False
    assert workspace.verify()["ok"] is False
