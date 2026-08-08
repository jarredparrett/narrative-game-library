"""Capability tests for the durable agentic-difficulty evidence spine."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest

from narrative_game.contracts.canonical import canonical_json
from narrative_game.workspace import Journal, ObjectStore, Workspace, WorkspaceCheckpoint


def _evidence_workspace(tmp_path: Path):
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="difficulty-evidence")
    schema_ref = workspace.put_evidence_object(
        object_kind="schema_bundle",
        object_schema="schema-bundle.1",
        value={"schemas": ["episode-evidence.1", "claim-manifest.1"]},
        producer="difficulty-fixture.1",
        verifier="schema-bundle-verifier.1",
    )
    verifier_ref = workspace.put_evidence_object(
        object_kind="verifier_bundle",
        object_schema="verifier-bundle.1",
        value={"entry_point": "narrative_game.workspace:verify_claim_capsule_bytes"},
        producer="difficulty-fixture.1",
        verifier="verifier-bundle-verifier.1",
    )
    observation_ref = workspace.put_evidence_object(
        object_kind="failure_observation",
        object_schema="failure-observation.1",
        value={
            "episode_ref": "sha256:" + "1" * 64,
            "quoted_span": "I pulled the emergency release.",
            "required_transition": "character-state-updated",
        },
        producer="difficulty-fixture.1",
        verifier="failure-observation-verifier.1",
    )
    root_ref = workspace.put_evidence_object(
        object_kind="diagnostic_claim",
        object_schema="diagnostic-claim.1",
        value={
            "object_ref": observation_ref,
            "claim": "procedure narration lacks a resulting state transition",
        },
        producer="difficulty-fixture.1",
        verifier="diagnostic-claim-verifier.1",
    )
    workspace.analysis.append(
        "episode_evidence_derived",
        actor="agent:deriver",
        payload={"evidence_object_ref": root_ref},
        object_refs=(root_ref,),
        idempotency_key="analysis:episode-1",
    )
    workspace.access.append(
        "evidence_view_exposed",
        actor="workspace",
        payload={"evidence_object_ref": root_ref, "principal": "analysis:discoverer-1"},
        object_refs=(root_ref,),
        idempotency_key="access:episode-1:discoverer-1",
    )
    workspace.rebuild_indexes()
    checkpoint_ref = workspace.create_checkpoint()
    manifest_ref = workspace.create_claim_manifest(
        claim_id="diagnostic:missing-rescue",
        checkpoint_ref=checkpoint_ref,
        root_refs=(root_ref,),
        schema_refs=(schema_ref,),
        verifier_refs=(verifier_ref,),
        actor="agent:reviewer",
        idempotency_key="claim:missing-rescue",
    )
    return {
        "workspace": workspace,
        "schema_ref": schema_ref,
        "verifier_ref": verifier_ref,
        "observation_ref": observation_ref,
        "root_ref": root_ref,
        "checkpoint_ref": checkpoint_ref,
        "manifest_ref": manifest_ref,
    }


def test_difficulty_evidence_objects_are_content_addressed_and_cross_process_identical(tmp_path):
    """difficulty.d1.evidence-objects: typed evidence has one portable identity."""
    first = Workspace.create(tmp_path / "first", workspace_id="first")
    second = Workspace.create(tmp_path / "second", workspace_id="second")
    arguments = {
        "object_kind": "episode_evidence_package",
        "object_schema": "episode-evidence.1",
        "value": {"episode_id": "episode:1", "spans": ["arena:0001"]},
        "producer": "difficulty-deriver.1",
        "verifier": "episode-evidence-verifier.1",
    }
    expected = first.put_evidence_object(**arguments)
    assert second.put_evidence_object(**arguments) == expected
    assert first.store.root == first.root / "objects" / "sha256"

    script = """
from narrative_game.workspace import Workspace
import sys
w = Workspace.create(sys.argv[1], workspace_id='subprocess')
print(w.put_evidence_object(
    object_kind='episode_evidence_package',
    object_schema='episode-evidence.1',
    value={'episode_id': 'episode:1', 'spans': ['arena:0001']},
    producer='difficulty-deriver.1',
    verifier='episode-evidence-verifier.1',
))
"""
    observed = subprocess.check_output(
        [sys.executable, "-c", script, str(tmp_path / "subprocess")],
        text=True,
    ).strip()
    assert observed == expected


def test_checkpoint_pins_verified_heads_without_cross_journal_partial_state(tmp_path):
    """difficulty.d1.checkpoint: one Checkpoint pins every verified Journal head."""
    result = _evidence_workspace(tmp_path)
    workspace = result["workspace"]
    checkpoint = WorkspaceCheckpoint.from_mapping(
        workspace.store.read_json(result["checkpoint_ref"])
    )
    assert set(checkpoint.journal_heads) == set(workspace.journals)
    assert checkpoint.journal_heads["analysis"]["sequence"] == 1
    assert checkpoint.journal_heads["access"]["sequence"] == 1
    assert workspace.verify_checkpoint(result["checkpoint_ref"]) == ()

    mapping = checkpoint.to_mapping()
    mapping["journal_heads"]["analysis"] = {
        **mapping["journal_heads"]["analysis"],
        "head": mapping["journal_heads"]["lineage"]["head"],
    }
    invalid_ref = workspace.store.put_json(mapping)
    assert workspace.verify_checkpoint(invalid_ref) == (
        "analysis Checkpoint head is not the named Journal prefix",
    )
    mapping["journal_heads"].pop("access")
    with pytest.raises(ValueError, match="every Workspace Journal"):
        WorkspaceCheckpoint.from_mapping(mapping)


def test_claim_manifest_requires_complete_transitive_objects_schemas_and_verifiers(tmp_path):
    """difficulty.d1.claim-manifest: a reportable claim binds its full closure."""
    result = _evidence_workspace(tmp_path)
    workspace = result["workspace"]
    manifest = workspace.store.read_json(result["manifest_ref"])
    assert workspace.verify_claim_manifest(result["manifest_ref"]) == ()
    assert {
        result["root_ref"],
        result["observation_ref"],
        result["schema_ref"],
        result["verifier_ref"],
        result["checkpoint_ref"],
    } <= set(manifest["object_refs"])

    workspace.store.path_for(result["observation_ref"]).write_bytes(b"tampered")
    findings = workspace.verify_claim_manifest(result["manifest_ref"])
    assert any("missing or corrupt evidence object" in item for item in findings)
    assert not workspace.verify()["ok"]


def test_difficulty_archive_and_capsule_verify_offline_after_relocation(tmp_path):
    """difficulty.d1.portability: Archives and Claim Capsules relocate offline."""
    result = _evidence_workspace(tmp_path)
    workspace = result["workspace"]
    first = workspace.export_claim_capsule(result["manifest_ref"], tmp_path / "one.ngc")
    second = workspace.export_claim_capsule(result["manifest_ref"], tmp_path / "two.ngc")
    assert Path(first["capsule"]).read_bytes() == Path(second["capsule"]).read_bytes()

    relocated = tmp_path / "relocated" / "claim.ngc"
    relocated.parent.mkdir(parents=True)
    relocated.write_bytes(Path(first["capsule"]).read_bytes())
    verified = Workspace.verify_claim_capsule(relocated)
    assert verified["ok"]
    assert verified["claim_manifest_ref"] == result["manifest_ref"]

    archive = workspace.export_archive(tmp_path / "workspace.ngw")
    imported = Workspace.import_archive(archive["archive"], tmp_path / "imported")
    assert imported.verify()["ok"]
    receipt_paths = list((imported.root / "imports").glob("*.json"))
    assert len(receipt_paths) == 1
    receipt_ref = "sha256:" + receipt_paths[0].stem
    receipt = imported.store.read_json(receipt_ref)
    assert receipt["object_kind"] == "import_receipt"
    assert receipt["value"]["archive_ref"] == archive["sha256"]

    broken_archive = tmp_path / "broken.ngw"
    broken_archive.write_bytes(Path(archive["archive"]).read_bytes()[:-17])
    with pytest.raises((ValueError, zipfile.BadZipFile)):
        Workspace.import_archive(broken_archive, tmp_path / "must-not-appear")
    assert not (tmp_path / "must-not-appear").exists()

    truncated = relocated.read_bytes()[:-17]
    (tmp_path / "broken.ngc").write_bytes(truncated)
    assert not Workspace.verify_claim_capsule(tmp_path / "broken.ngc")["ok"]


def test_workspace_migration_is_append_only_receipted_and_preserves_old_identity(tmp_path):
    """difficulty.d1.migration: Workspace 0.1 evidence is never rewritten in place."""
    root = tmp_path / "legacy"
    lineage = Journal(root / "journals" / "lineage.jsonl", journal_id="experiment-lineage")
    lineage.append(
        "workspace_created",
        actor="human",
        payload={"workspace_id": "legacy", "schema_version": "0.1"},
        idempotency_key="workspace.create:legacy",
        expected_head=None,
    )
    store = ObjectStore(root / "objects")
    old_ref = store.put_json(
        {"schema_version": "0.1", "kind": "legacy_evidence", "value": "preserve me"}
    )
    lineage.append(
        "legacy_evidence_recorded",
        actor="human",
        payload={"object_ref": old_ref},
        object_refs=(old_ref,),
        idempotency_key="legacy:evidence:1",
    )
    old_lineage = lineage.path.read_bytes()
    old_object = store.read_bytes(old_ref)

    workspace = Workspace.open(root)
    assert workspace.store.root == root / "objects"
    receipt_ref = workspace.migrate_legacy_evidence(
        actor="agent:migrator",
        idempotency_key="migration:0.1-to-0.2",
    )
    assert lineage.path.read_bytes() == old_lineage
    assert store.read_bytes(old_ref) == old_object
    receipt = workspace.store.read_json(receipt_ref)
    assert receipt["object_kind"] == "migration_receipt"
    assert receipt["value"]["warnings"] == []
    assert receipt["value"]["information_loss"] == []
    assert workspace.migrate_legacy_evidence(
        actor="agent:migrator",
        idempotency_key="migration:0.1-to-0.2",
    ) == receipt_ref
    assert workspace.verify()["ok"]
