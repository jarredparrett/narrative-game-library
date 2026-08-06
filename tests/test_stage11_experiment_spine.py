"""Stage 11 qualification spine, claim trace, and portability acceptance."""

from __future__ import annotations

import json

import pytest

from narrative_game.contracts import (
    canonical_json,
    claim_trace_licenses_resolution,
    digest_bytes,
    validate_accessibility_contract,
    validate_claim_trace,
)
from narrative_game.experiment import (
    ExperimentSpine,
    read_verismill_experiment_capsule,
    seal_verismill_experiment,
)
from narrative_game.workspace import Workspace


def standings(evidence: dict[str, bytes] | None = None) -> dict:
    evidence = evidence or {}
    ref = lambda key: [digest_bytes(evidence[key])] if key in evidence else []
    return {
        "coherent_build": {
            "status": "passed", "instrument": "build-audit-v1",
            "evidence_refs": ref("build"),
        },
        "gameplay": {
            "status": "passed", "instrument": "development-gameplay-v5",
            "evidence_refs": ref("gameplay"),
            "scores": {"culprit_confidence": 94},
        },
        "accessibility": {
            "status": "passed", "instrument": "critical-parity-v2",
            "evidence_refs": ref("accessibility"),
        },
        "artifact_realism": {
            "status": "not_accepted", "instrument": "absolute-v0.2",
            "evidence_refs": ref("artifact-suite"),
            "scores": {"accepted": 0, "measured": 19},
        },
        "human_play": {
            "status": "unmeasured", "instrument": "six-human-table-v1",
            "evidence_refs": [],
        },
        "public_release": {
            "status": "unclaimed", "instrument": "public-release-v1",
            "evidence_refs": [],
        },
    }


def claim_trace() -> dict:
    return {
        "schema_version": "0.12",
        "claims": [{
            "proposition_id": "mercer-entered-positive-correction",
            "evidence_id": "reduction-worksheet",
            "resource_path": "materials/reduction-worksheet.pdf",
            "locus": {"quote": "Prepared: Rook / Checked: Mercer"},
            "content_hash": "sha256:" + "5" * 64,
            "phase_id": "resolution",
            "proof_path_ids": ["sign-motive-route"],
        }],
        "proof_paths": {"sign-motive-route": ["reduction-worksheet"]},
    }


def accessibility() -> dict:
    return {
        "schema_version": "0.12",
        "artifact_id": "reduction-worksheet",
        "native_hash": "sha256:" + "6" * 64,
        "accessible_hash": "sha256:" + "7" * 64,
        "native_proposition_ids": ["mercer-entered-positive-correction"],
        "accessible_proposition_ids": ["mercer-entered-positive-correction"],
        "entries": [{
            "editorial_identification": "Reduction worksheet, correction block",
            "visible_wording": "Prepared: Rook / Checked: Mercer",
            "visual_evidence": "Mercer initials occupy the checked field",
            "interpretation": "",
            "proposition_ids": ["mercer-entered-positive-correction"],
        }],
    }


def record_candidate_6(spine: ExperimentSpine, archive_path):
    collection = {"candidate": "candidate-6", "members": 19}
    collection_bytes = canonical_json(collection)
    collection_ref = digest_bytes(collection_bytes)
    evidence = {
        "build": b"candidate-6 build receipt",
        "gameplay": b"candidate-6 gameplay manifest",
        "accessibility": b"candidate-6 accessibility gate",
        "artifact-suite": b"candidate-6 suite attestation",
    }
    return spine.record_selected_rung(
        candidate_id="candidate-6",
        parent_candidate_id=None,
        release_bytes=b"candidate-6-release",
        physical_package_bytes=b"candidate-6-physical",
        artifact_collection_bytes=collection_bytes,
        artifact_experiments={
            f"artifact-{index:02d}": f"verified experiment {index}".encode()
            for index in range(1, 20)
        },
        approvals=(canonical_json({
            "candidate_id": "candidate-6",
            "artifact_collection_hash": collection_ref,
            "decision": "approved",
            "scope": {
                "permits": ["independent artifact measurement"],
                "does_not_claim": ["artifact realism", "public release"],
            },
        }),),
        evidence_objects=evidence,
        standings=standings(evidence),
        claim_trace=claim_trace(),
        required_propositions=("mercer-entered-positive-correction",),
        accessibility_contracts=(accessibility(),),
        blockers=(
            {"code": "artifact.realism", "evidence_class": "artifact_realism",
             "reason": "0 of 19 artifacts accepted"},
            {"code": "human.play", "evidence_class": "human_play",
             "reason": "six-human table is unmeasured"},
        ),
        debt=({"code": "dossier.depth", "reason": "one-page dossiers"},),
        invalidation=("artifact byte change invalidates exact approval and realism",),
        replay_requirements=("player-visible critical change requires gameplay replay",),
        export_path=archive_path,
    )


def test_candidate_6_standing_is_separate_derived_and_portable(tmp_path):
    """stage11.portable-spine: one selected rung preserves all quality layers
    and 19 external experiment references in a relocatable journal archive."""
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="winter-observatory")
    spine = ExperimentSpine(workspace)
    result = record_candidate_6(spine, tmp_path / "candidate-6.ngw")
    projection = result["projection"]

    assert projection["selected_candidate"] == "candidate-6"
    assert len(projection["artifact_experiments"]) == 19
    assert projection["standings"]["gameplay"]["status"] == "passed"
    assert projection["standings"]["accessibility"]["status"] == "passed"
    assert projection["standings"]["artifact_realism"]["scores"] == {
        "accepted": 0, "measured": 19,
    }
    assert projection["standings"]["human_play"]["status"] == "unmeasured"
    assert projection["standings"]["public_release"]["status"] == "unclaimed"
    assert spine.verify()["ok"]

    imported = Workspace.import_archive(
        tmp_path / "candidate-6.ngw", tmp_path / "relocated" / "experiment"
    )
    imported_spine = ExperimentSpine(imported)
    assert imported_spine.derive_projection() == projection
    assert imported_spine.verify()["ok"]


def test_projection_is_replaced_from_journal_and_mutation_is_detected(tmp_path):
    """stage11.derived-standing: stale status cannot outrank journal evidence,
    and missing external evidence invalidates the portable Experiment."""
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="winter-observatory")
    spine = ExperimentSpine(workspace)
    record_candidate_6(spine, tmp_path / "candidate-6.ngw")
    expected = spine.derive_projection()
    (workspace.root / "current-standing.json").write_text('{"stale":true}')
    reopened = ExperimentSpine(Workspace.open(workspace.root))
    assert json.loads((workspace.root / "current-standing.json").read_bytes()) == expected

    external_ref = next(iter(expected["artifact_experiments"].values()))
    reopened.workspace.store.path_for(external_ref).unlink()
    assert reopened.verify()["ok"] is False
    assert any("missing or corrupt" in item for item in reopened.verify()["failures"])


def test_parentage_and_exact_approval_scope_cannot_be_forged(tmp_path):
    """stage11.rung-integrity: a child needs a known parent and approval must
    name the exact Candidate and artifact collection hash."""
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="winter-observatory")
    spine = ExperimentSpine(workspace)
    kwargs = dict(
        candidate_id="candidate-7",
        parent_candidate_id="missing-candidate",
        release_bytes=b"release", physical_package_bytes=b"physical",
        artifact_collection_bytes=canonical_json({"candidate": "candidate-7"}),
        artifact_experiments={}, approvals=(), evidence_objects={},
        standings=standings(),
        claim_trace=claim_trace(),
        required_propositions=("mercer-entered-positive-correction",),
        accessibility_contracts=(accessibility(),),
        export_path=tmp_path / "child.ngw",
    )
    with pytest.raises(ValueError, match="parent"):
        spine.record_selected_rung(**kwargs)

    kwargs["parent_candidate_id"] = None
    kwargs["approvals"] = (canonical_json({
        "candidate_id": "another-candidate",
        "artifact_collection_hash": "sha256:" + "0" * 64,
        "decision": "approved", "scope": {},
    }),)
    with pytest.raises(ValueError, match="different candidate"):
        spine.record_selected_rung(**kwargs)


def test_claim_and_accessibility_contracts_reject_missing_or_interpreted_evidence():
    """stage11.evidence-invariants: proof paths cover every conclusion and
    accessibility carries visible facts without supplying interpretation."""
    with pytest.raises(ValueError, match="omits required"):
        validate_claim_trace(claim_trace(), required_propositions=("cause-of-death",))
    interpreted = accessibility()
    interpreted["entries"][0]["interpretation"] = "Mercer is the murderer"
    with pytest.raises(ValueError, match="cannot supply interpretation"):
        validate_accessibility_contract(interpreted)
    unequal = accessibility()
    unequal["accessible_proposition_ids"] = []
    with pytest.raises(ValueError, match="unequal proof power"):
        validate_accessibility_contract(unequal)
    assert claim_trace_licenses_resolution(
        claim_trace(), proof_path_id="sign-motive-route"
    )
    assert not claim_trace_licenses_resolution(
        claim_trace(), proof_path_id="unreleased-route"
    )


def test_external_verismill_reference_uses_only_the_verified_public_facade():
    """stage11.cross-system-reference: a path-free capsule seals the verified
    public replay and rejects a suite row that names a different exact result."""
    artifact = b"measured artifact"
    artifact_hash = digest_bytes(artifact)
    candidate_ref = "sha256:" + "8" * 64
    evaluation_ref = "sha256:" + "9" * 64

    class PublicExperiment:
        def verify(self):
            return {"ok": True, "failures": [], "events_verified": 2,
                    "objects_verified": 3}

        def replay(self):
            return [
                {"event_type": "candidate", "event_hash": "sha256:" + "a" * 64},
                {"event_type": "evaluation", "event_hash": "sha256:" + "b" * 64},
            ]

        def artifact_result(self, candidate):
            assert candidate == candidate_ref
            return {
                "artifact": artifact,
                "manifest": {"sha256": artifact_hash},
                "attestation": {
                    "experiment_id": "external-1",
                    "candidate": candidate_ref,
                    "measurement": {"evaluation": evaluation_ref},
                },
            }

    item = {
        "experiment_root": "/convenience/path/never-persisted",
        "experiment_id": "external-1",
        "artifact_hash": artifact_hash,
        "candidate_ref": candidate_ref,
        "evaluation_ref": evaluation_ref,
    }
    capsule = seal_verismill_experiment(item, opener=lambda _: PublicExperiment())
    decoded = read_verismill_experiment_capsule(capsule)
    assert decoded["bus_head"] == "sha256:" + "b" * 64
    assert decoded["artifact_hash"] == artifact_hash
    assert b"convenience/path" not in capsule

    wrong = dict(item, evaluation_ref="sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="does not match"):
        seal_verismill_experiment(wrong, opener=lambda _: PublicExperiment())
