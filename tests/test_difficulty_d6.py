"""Capability tests for the read-only operator surface and release capsule."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import zipfile

from narrative_game.contracts.canonical import canonical_json
from narrative_game.difficulty import (
    FORBIDDEN_OPERATOR_COMMANDS,
    SEALED_HANDLE_FIELDS,
    OperatorProjectionSource,
    build_operator_projection,
    build_release_claim_capsule,
    reference_operator_projection,
    render_operator_html,
    verify_release_claim_capsule_bytes,
)
from narrative_game.workspace import Workspace
from narrative_game.workspace.evidence import capsule_members, deterministic_zip
from narrative_game.stage_d6_fixture import run as write_operator_example


REF = lambda value: "sha256:" + value * 64


def test_operator_monitor_fails_closed_across_all_freshness_and_completeness_states():
    """difficulty.d6.monitor-states: trust and completeness never blur together."""
    current = reference_operator_projection("current").to_mapping()["material"]
    assert current["trust"]["state"] == "current-complete"
    assert current["views"]["overview"]["standing_status"] == "supported"
    assert current["conclusions"]

    incomplete = reference_operator_projection("incomplete").to_mapping()["material"]
    assert incomplete["trust"]["state"] == "current-incomplete"
    assert incomplete["trust"]["freshness"] == "current"
    assert incomplete["views"]["overview"]["standing_status"] == "indeterminate"
    assert incomplete["views"]["overview"]["selection_status"] == "indeterminate"
    assert incomplete["views"]["coverage"][1]["invalid"] == 1

    stale = reference_operator_projection("stale").to_mapping()["material"]
    assert stale["trust"]["state"] == "stale"
    assert stale["identity"]["checkpoint_ref"] != stale["identity"]["current_checkpoint_ref"]
    assert stale["views"]["overview"] == current["views"]["overview"]

    corrupt = reference_operator_projection("corrupt").to_mapping()["material"]
    assert corrupt["trust"]["state"] == "invalid"
    assert corrupt["trust"]["freshness"] == "invalid"
    assert corrupt["trust"]["last_verifiable_checkpoint_ref"]
    assert corrupt["conclusions"] == []
    assert corrupt["suppressed_conclusion_ids"] == [
        "coverage-debt",
        "current-work",
        "target-band",
    ]
    assert corrupt["views"] == {"coverage": [], "incidents": [], "overview": {}}


def test_operator_monitor_is_read_only_traceable_accessible_and_sealed_safe():
    """difficulty.d6.monitor-authority: presentation cannot mutate or expose evidence."""
    projection = reference_operator_projection("current")
    material = projection.to_mapping()["material"]
    authorities = {
        *material["identity"]["claim_manifest_refs"],
        material["identity"]["scheduling_receipt_ref"],
    }
    assert all(item["authority_ref"] in authorities for item in material["conclusions"])
    assert material["trust"]["read_only"] is True
    assert material["trust"]["authority"] == "inspection-only"
    assert set(material["affordances"]) == {
        "navigate",
        "filter-projected",
        "inspect",
        "expand-trace",
        "copy-reference",
    }
    assert all(set(item) == set(SEALED_HANDLE_FIELDS) for item in material["sealed_handles"])
    encoded = json.dumps(material)
    sealed_encoded = json.dumps(material["sealed_handles"])
    for leaked in ("cohort_size", "case_count", "case_content", "seed", "oracle", "per_case"):
        assert leaked not in sealed_encoded

    html = render_operator_html(projection).decode("utf-8")
    assert '<html lang="en">' in html
    assert 'role="status"' in html
    assert 'aria-label="Monitor views"' in html
    assert ":focus-visible" in html
    assert "prefers-reduced-motion" in html
    assert "@media(max-width:760px)" in html
    assert "read only — no transition authority" in html
    assert "<button" not in html and "<form" not in html and "data-command" not in html
    for command in FORBIDDEN_OPERATOR_COMMANDS:
        assert f'"{command}":' not in encoded


def test_operator_projection_rebuild_is_offline_cross_process_and_claim_preserving(tmp_path):
    """difficulty.d6.projection-rebuild: one Checkpoint yields one disposable view."""
    first = reference_operator_projection("current")
    projection_path = tmp_path / "operator-projection.json"
    projection_path.write_bytes(first.to_bytes())
    projection_path.unlink()
    rebuilt = reference_operator_projection("current")
    assert rebuilt.to_bytes() == first.to_bytes()
    assert rebuilt.projection_ref == first.projection_ref
    assert [
        item["authority_ref"]
        for item in rebuilt.to_mapping()["material"]["conclusions"]
    ] == [
        item["authority_ref"]
        for item in first.to_mapping()["material"]["conclusions"]
    ]

    script = """
from narrative_game.difficulty import reference_operator_projection
import sys
p = reference_operator_projection('current')
sys.stdout.buffer.write(p.to_bytes())
"""
    observed = subprocess.check_output([sys.executable, "-c", script])
    assert observed == first.to_bytes()
    manifest = write_operator_example(tmp_path / "monitor")
    assert manifest["entry_point"] == "index.html"
    assert (tmp_path / "monitor" / "operator-corrupt.html").is_file()


def _claim_workspace(tmp_path: Path):
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="release-capsule")
    schema_ref = workspace.put_evidence_object(
        object_kind="schema_bundle",
        object_schema="schema-bundle.1",
        value={"schemas": ["diagnostic-claim.1"]},
        producer="d6-fixture.1",
        verifier="schema-verifier.1",
    )
    verifier_ref = workspace.put_evidence_object(
        object_kind="verifier_bundle",
        object_schema="verifier-bundle.1",
        value={"entry_point": "release-capsule/verify.py"},
        producer="d6-fixture.1",
        verifier="verifier-bundle-verifier.1",
    )
    root_ref = workspace.put_evidence_object(
        object_kind="diagnostic_claim",
        object_schema="diagnostic-claim.1",
        value={"claim": "handoff failure remains corroborated", "status": "supported"},
        producer="d6-fixture.1",
        verifier="diagnostic-claim-verifier.1",
    )
    workspace.analysis.append(
        "diagnostic_claim_recorded",
        actor="analysis:reviewer",
        payload={"evidence_object_ref": root_ref},
        object_refs=(root_ref,),
        idempotency_key="d6:diagnostic-claim",
    )
    workspace.rebuild_indexes()
    checkpoint_ref = workspace.create_checkpoint()
    manifest_ref = workspace.create_claim_manifest(
        claim_id="difficulty:handoff",
        checkpoint_ref=checkpoint_ref,
        root_refs=(root_ref,),
        schema_refs=(schema_ref,),
        verifier_refs=(verifier_ref,),
        actor="analysis:independent-reviewer",
        idempotency_key="d6:claim-manifest",
    )
    capsule_path = tmp_path / "claim.ngc"
    workspace.export_claim_capsule(manifest_ref, capsule_path)
    return workspace, checkpoint_ref, manifest_ref, capsule_path.read_bytes()


def _claim_projection(workspace: Workspace, checkpoint_ref: str, manifest_ref: str):
    heads = {
        name: {
            "journal_id": journal.journal_id,
            "sequence": len(journal.read()),
            "head": journal.head(),
        }
        for name, journal in workspace.journals.items()
    }
    scheduling_ref = REF("7")
    source = OperatorProjectionSource(
        "release-capsule",
        checkpoint_ref,
        checkpoint_ref,
        REF("8"),
        heads,
        REF("9"),
        (manifest_ref,),
        scheduling_ref,
        "complete",
        {
            "supported-incident": {
                "statement": "The handoff Incident is supported.",
                "status": "supported",
                "authority_ref": manifest_ref,
            },
            "next-work": {
                "statement": "The matched counterfactual is next.",
                "status": "scheduled",
                "authority_ref": scheduling_ref,
            },
        },
        {
            "standing_status": "diagnostic-only",
            "selection_status": "indeterminate",
            "evidence_spine": [],
            "budgets": {},
        },
        (),
        (),
        (),
    )
    return build_operator_projection(source)


def test_release_capsule_contains_exact_verifier_and_rechecks_every_reportable_claim_offline(tmp_path):
    """difficulty.d6.release-capsule: a relocated result carries its own proof."""
    workspace, checkpoint_ref, manifest_ref, claim = _claim_workspace(tmp_path)
    projection = _claim_projection(workspace, checkpoint_ref, manifest_ref)
    kwargs = {
        "claim_capsule": claim,
        "projection": projection,
        "schema_bundle": {
            "schemas": [
                "claim-capsule.1",
                "operator-evidence-projection.1",
                "release-claim-capsule.1",
            ]
        },
        "component_lock": {
            "narrative-game-library": "0.31.0",
            "python": ">=3.11",
            "operator-derivation": "operator-evidence-projection.1",
        },
    }
    first = build_release_claim_capsule(**kwargs)
    assert build_release_claim_capsule(**kwargs) == first
    verified = verify_release_claim_capsule_bytes(first)
    assert verified["ok"]
    assert verified["claim_manifest_ref"] == manifest_ref
    assert verified["checkpoint_ref"] == checkpoint_ref
    assert verified["operator_projection_ref"] == projection.projection_ref
    assert all(verified[key] for key in ("component_lock_ref", "schema_bundle_ref", "verifier_ref"))

    relocated = tmp_path / "unfamiliar-operator" / "difficulty-release.ngr"
    relocated.parent.mkdir()
    relocated.write_bytes(first)
    with zipfile.ZipFile(relocated) as archive:
        verifier_path = relocated.parent / "verify.py"
        verifier_path.write_bytes(archive.read("verify.py"))
    result = json.loads(
        subprocess.check_output(
            [sys.executable, str(verifier_path), str(relocated)],
            cwd=relocated.parent,
            text=True,
        )
    )
    assert result["ok"] and result["claim_manifest_ref"] == manifest_ref

    members = capsule_members(first)
    members["component-lock.json"] = canonical_json({"tampered": "true"})
    broken = deterministic_zip(members)
    assert not verify_release_claim_capsule_bytes(broken)["ok"]
