"""Stage 7 complete player-facing Blind Trial capability tests."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json

import pytest

from narrative_game.climb import prepare_blind_trial, verify_blind_trial
from narrative_game.climb.trial import _project_preflight_checks
from narrative_game.compiler import compile_candidate
from narrative_game.physical import export_physical
from narrative_game.stage5_fixture import DEFAULT_SOURCE, build_worked_candidate


@pytest.fixture(scope="module")
def trials(tmp_path_factory):
    root = tmp_path_factory.mktemp("stage7-trials")
    source = json.loads((DEFAULT_SOURCE / "scenario.json").read_bytes())
    baseline_build = build_worked_candidate(root / "baseline-forge", source_mapping=source)
    baseline_release = compile_candidate(baseline_build.candidate).release
    assert baseline_release is not None
    baseline_physical = export_physical(baseline_release)

    child_source = deepcopy(source)
    next(
        item
        for item in child_source["narrative"]["reveals"]
        if item["id"] == "reveal-interview"
    )["phase_id"] = "investigation"
    child_build = build_worked_candidate(root / "child-forge", source_mapping=child_source)
    child_release = compile_candidate(child_build.candidate).release
    assert child_release is not None
    child_physical = export_physical(child_release)
    cover_story = "Evaluate this anonymous two-seat archival investigation as a complete player experience."
    return (
        prepare_blind_trial(baseline_release, baseline_physical, cover_story=cover_story),
        prepare_blind_trial(child_release, child_physical, cover_story=cover_story),
        baseline_release,
        child_release,
        baseline_physical,
        child_physical,
    )


def test_blind_trial_contains_complete_seat_experience_without_trusted_truth(trials):
    """stage7.complete-trial: every Seat-facing source and print asset reaches judges."""
    baseline, _, release, _, physical, _ = trials
    schedule = json.loads(baseline.file("trial/schedule.json").data)
    resources = {item["resource_id"] for item in schedule["copies"]}
    expected = {
        item["resource_id"]
        for item in physical.plan["copies"]
        if item["audience"].startswith("seat:")
    }
    assert resources == expected
    assert "host-guide" not in resources
    for resource_id in resources:
        source = release.file(f"materials/{resource_id}")
        rendered = physical.file(
            f"print/resources/{resource_id}.pdf"
        )
        assert baseline.file(f"trial/print/{resource_id}.pdf").data == rendered.data
        if source.media_type == "application/pdf":
            copy = next(
                item for item in schedule["copies"] if item["resource_id"] == resource_id
            )
            assert copy["material_path"] == copy["print_path"]
        else:
            assert baseline.file(f"trial/materials/{resource_id}").data == source.data
    assert {item.path for item in baseline.files if item.path.startswith("trial/seats/")} == {
        "trial/seats/avery.json",
        "trial/seats/blake.json",
    }
    verify_blind_trial(baseline)


def test_preflight_paths_name_exact_shipped_print_files(trials):
    """stage7.archive-fidelity: preflight paths are re-executable in the Blind Trial."""
    baseline, *_ = trials
    schedule = json.loads(baseline.file("trial/schedule.json").data)
    shipped = {item.path for item in baseline.files}
    assert all(item["path"] in shipped for item in schedule["preflight"]["files"])


def test_preflight_projection_handles_dossier_rendition_namespace():
    """stage7.archive-fidelity: dossier checks resolve to emitted Trial filenames."""
    projected = _project_preflight_checks(
        [{"path": "print/dossiers/eleanor.pdf", "ok": True}],
        {"dossier-eleanor": "print/dossiers/eleanor.pdf"},
        {"dossier-eleanor": "trial/print/dossier-eleanor.pdf"},
    )

    assert projected == [
        {"path": "trial/print/dossier-eleanor.pdf", "ok": True}
    ]


def test_verifier_rejects_preflight_path_that_is_not_shipped(trials):
    """stage7.archive-fidelity: verification independently checks named paths."""
    baseline, *_ = trials
    schedule = json.loads(baseline.file("trial/schedule.json").data)
    schedule["preflight"]["files"][0]["path"] = "trial/print/not-shipped.pdf"
    corrupted = replace(
        baseline,
        files=tuple(
            replace(item, data=json.dumps(schedule).encode())
            if item.path == "trial/schedule.json"
            else item
            for item in baseline.files
        ),
    )

    with pytest.raises(ValueError, match="preflight names an unshipped path"):
        verify_blind_trial(corrupted)


def test_trial_conceals_source_identity_answers_and_provenance(trials):
    """stage7.blindness: judge bytes contain no trusted identities or answer objects."""
    baseline, _, release, _, physical, _ = trials
    paths = {item.path for item in baseline.files}
    assert not any(
        path.startswith(("trusted/", "receipts/", "attestations/", "source/"))
        for path in paths
    )
    assert "host-guide" not in "\n".join(paths)
    for identity in (
        release.candidate_id,
        release.release_id,
        physical.export_id,
        physical.archive_hash,
    ):
        assert identity.encode() not in baseline.archive_bytes
    json_bytes = b"\n".join(
        item.data for item in baseline.files if item.media_type == "application/json"
    )
    for key in (
        b'"truth_model"',
        b'"correct_hypothesis_id"',
        b'"acceptable_proof_path_ids"',
    ):
        assert key not in json_bytes


def test_complete_child_package_changes_trial_without_revealing_lineage(trials):
    """stage7.full-child: an approved play-affecting change reaches the measured package."""
    baseline, child, *_ = trials
    assert baseline.trial_id != child.trial_id
    assert baseline.archive_hash != child.archive_hash
    baseline_schedule = json.loads(baseline.file("trial/schedule.json").data)
    child_schedule = json.loads(child.file("trial/schedule.json").data)
    baseline_interview = {
        item["delivery_condition"]
        for item in baseline_schedule["copies"]
        if item["resource_id"] == "closing-interview"
    }
    child_interview = {
        item["delivery_condition"]
        for item in child_schedule["copies"]
        if item["resource_id"] == "closing-interview"
    }
    assert baseline_interview == {"opening"}
    assert child_interview == {"investigation"}
    assert "baseline" not in baseline.archive_bytes.decode("latin-1").lower()
    assert "child" not in child.archive_bytes.decode("latin-1").lower()
