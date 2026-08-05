"""Stage 5 acceptance: one rich scenario crosses every public boundary."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys

from pypdf import PdfReader
import pytest

from narrative_game.compiler import compile_candidate, freeze_candidate, reference_component_lock
from narrative_game.contracts import digest_json
from narrative_game.physical import export_physical, verify_physical_export
from narrative_game.runtime import (
    AuthorizationContext,
    SessionHistory,
    replay,
    retrieve_resource,
    seat_snapshot,
)
from narrative_game.stage5_fixture import build_worked_candidate, run
from narrative_game.workspace import Workspace


@pytest.fixture(scope="module")
def worked(tmp_path_factory):
    root = tmp_path_factory.mktemp("ashwood") / "worked"
    return run(root)


def test_worked_scenario_freezes_forges_compiles_runs_and_persists(worked):
    """stage5.complete-example: every required layer yields verified evidence."""
    assert worked.summary["game"] == "The Ashwood Ledger"
    for name in (
        "artifact_hash",
        "candidate_id",
        "release_id",
        "release_bundle_hash",
        "physical_export_id",
        "physical_archive_hash",
        "session_history_hash",
    ):
        assert worked.summary[name].startswith("sha256:")
    assert worked.summary["artifact_measurement_status"] == "development_only"
    assert worked.summary["physical_preflight_ok"] is True
    assert worked.summary["session_resolved_correctly"] is True
    assert worked.summary["workspace_verified"] is True
    assert "persisted Candidate" in worked.summary["determinism_scope"]
    assert worked.session.sequence == 13
    assert worked.output_root.joinpath("hill-climb-lineage.md").is_file()
    assert "Human-authorized Candidate" in worked.output_root.joinpath(
        "hill-climb-lineage.md"
    ).read_text()


def test_artifact_boundary_preserves_bytes_attestation_and_only_pinned_facts(worked):
    """stage5.artifact-boundary: the emitter supplies bytes, not narrative truth."""
    release = worked.release
    artifact = release.file("materials/madison-deed-1997")
    receipt = json.loads(release.file("receipts/madison-deed-1997.json").data)
    attestation = json.loads(release.file("attestations/madison-deed-1997.json").data)
    request = receipt["artifact_request"]
    propositions = {item.id for item in worked.build.candidate.game.propositions}
    assert artifact.content_hash == worked.build.artifact_hash
    assert attestation["artifact_hash"] == artifact.content_hash
    assert attestation["verification"]["ok"] is True
    assert set(request["fact_references"]) == {"deed-date", "deed-consideration"}
    assert set(request["fact_references"]) <= propositions
    assert request["pins"]["execution_date"] == "1997-10-17"
    assert request["pins"]["consideration"] == 425000
    assert "deed-index-hidden" not in request["fact_references"]


def test_artifact_acknowledgment_agrees_with_pinned_signer_count(worked):
    """artifact.acknowledgment-number-agreement: deed grammar follows signer count."""
    receipt = json.loads(worked.release.file("receipts/madison-deed-1997.json").data)
    deed = worked.release.file("materials/madison-deed-1997").data
    text = " ".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(deed)).pages
    )
    if receipt["artifact_request"]["pins"]["grantor_married"]:
        assert "they are the persons named" in text
    else:
        assert "the Grantor is the person named" in text
        assert "they are the persons named" not in text


def test_artifact_notary_identity_is_pinned_away_from_game_characters(worked):
    """artifact.pinned-notary-identity: the request controls a non-colliding notary."""
    receipt = json.loads(worked.release.file("receipts/madison-deed-1997.json").data)
    deed = worked.release.file("materials/madison-deed-1997").data
    text = " ".join(
        page.extract_text() or "" for page in PdfReader(BytesIO(deed)).pages
    )
    assert receipt["artifact_request"]["pins"]["notary_name"] == "Elise North"
    assert "Elise North, Notary Public" in text
    assert "Avery North" not in text


def test_accessible_deed_derives_every_required_field_from_public_manifest(worked):
    """artifact.public-display-facts: reading-copy fields derive from the public result."""
    receipt = json.loads(worked.release.file("receipts/madison-deed-1997.json").data)
    accessible_receipt = json.loads(
        worked.release.file("receipts/deed-accessible.json").data
    )
    text = worked.release.file("materials/deed-accessible").data.decode()
    facts = receipt["artifact_manifest"]["display_facts"]
    for field in (
        "grantor_name",
        "grantor_address",
        "grantee_name",
        "grantee_address",
        "grantor_spouse_name",
    ):
        assert str(facts[field]) in text
    for name in facts["signatory_names"]:
        assert name in text
    for name in facts["acknowledgment_names"]:
        assert name in text
    assert accessible_receipt["kind"] == "artifact-accessibility-rendition"
    assert f"Deed Book {facts['prior_book']}, Page {facts['prior_page']}" in text
    assert "Execution date: October 17, 1997" in text
    assert f"${facts['consideration']:,.2f}" in text
    assert facts["notary_name"] in text


def test_every_displayed_claim_has_reexecuted_proposition_lineage(worked):
    """stage5.claim-trace: displayed facts quote material or an exact forge pin."""
    trace = json.loads(worked.physical.file("trusted/claim-trace.json").data)
    propositions = {item.id for item in worked.build.candidate.game.propositions}
    assert len(trace["claims"]) == 8
    for claim in trace["claims"]:
        assert claim["proposition_id"] in propositions
        assert claim["verified_evidence"]
        if claim["source"] == "material-text":
            assert claim["quote"]
            assert claim["verified_evidence"]["content_hash"].startswith("sha256:")
        else:
            assert claim["verified_evidence"]["pin"] in {"execution_date", "consideration"}


def test_physical_plan_is_access_equivalent_explicit_and_spoiler_safe(worked):
    """stage5.physical-equivalence: one access policy drives digital and print copies."""
    game = worked.build.candidate.game
    plan = worked.physical.plan
    copies = plan["copies"]
    expected = {
        (policy.resource.id, str(grantee))
        for policy in game.kernel.access_policies
        for grantee in policy.grantees
    }
    actual = {(item["resource_id"], item["audience"]) for item in copies}
    assert actual == expected
    assert len({item["copy_id"] for item in copies}) == len(copies)
    assert all(item["copy_count"] == 1 for item in copies)
    assert all(item["custodian"] == "host" for item in copies)
    assert all(item["container_id"] for item in copies)
    assert all(item["delivery_condition"] for item in copies)
    for resource_id in {item["resource_id"] for item in copies}:
        same = [item for item in copies if item["resource_id"] == resource_id]
        assert same[0]["duplicate_of"] is None
        assert all(item["duplicate_of"] == same[0]["copy_id"] for item in same[1:])
    assert worked.physical.file("print/container-labels.pdf").data.startswith(b"%PDF")


def test_every_print_page_is_letter_sized_marked_and_preflighted(worked):
    """stage5.print-safety: all detached pages are visually marked and counted."""
    label = worked.physical.profile.provenance_label
    pdfs = [item for item in worked.physical.files if item.media_type == "application/pdf"]
    assert len(pdfs) == 12
    for item in pdfs:
        reader = PdfReader(BytesIO(item.data))
        assert reader.pages
        for page in reader.pages:
            assert float(page.mediabox.width) == pytest.approx(612, abs=1)
            assert float(page.mediabox.height) == pytest.approx(792, abs=1)
            assert label in (page.extract_text() or "")
    marked_deed = worked.physical.file("print/resources/madison-deed-1997.pdf")
    exact_deed = worked.release.file("materials/madison-deed-1997")
    assert marked_deed.content_hash != exact_deed.content_hash
    assert worked.physical.file("source/game-release.zip").data == worked.release.bundle_bytes


def test_physical_preflight_reports_executed_and_unexecuted_usability_checks(worked):
    """stage7.physical-preflight-coverage: readiness names measured scope and remaining print debt."""
    preflight = worked.physical.preflight
    assert set(preflight["executed_checks"]) == {
        "file_integrity",
        "pdf_geometry",
        "text_usability",
        "authored_reading_order",
        "layout_completion",
        "renderer_palette_contrast",
    }
    assert set(preflight["unexecuted_checks"]) == {
        "physical_printer_test",
        "imported_artifact_palette_contrast",
    }
    pdf_records = [item for item in preflight["files"] if "pdf_checks" in item]
    assert pdf_records
    assert all(item["pdf_checks"]["extractable_text"] for item in pdf_records)
    assert all(item["pdf_checks"]["minimum_font_size"]["passed"] for item in pdf_records)
    authored = [
        item["pdf_checks"]["authored_content_font_size"]
        for item in pdf_records
        if item["pdf_checks"]["authored_content_font_size"]["executed"]
    ]
    assert authored
    assert all(item["passed"] for item in authored)
    assert all(item["measured_points"] >= 8.5 for item in authored)
    assert all(item["pdf_checks"]["authored_reading_order"]["executed"] for item in pdf_records)
    assert all(item["pdf_checks"]["authored_reading_order"]["passed"] for item in pdf_records)
    rendered = [
        item for item in pdf_records
        if item["pdf_checks"]["layout_engine_completed"]["executed"]
    ]
    assert rendered
    assert all(item["pdf_checks"]["layout_engine_completed"]["passed"] for item in rendered)
    assert len(rendered) == len(pdf_records)
    assert all(item["pdf_checks"]["renderer_palette_contrast"]["passed"] for item in rendered)


def test_authorized_seat_experiences_remain_distinct_and_replay_portably(worked):
    """stage5.authorized-play: rich physical and digital play share one Session policy."""
    restored = SessionHistory.from_bytes(worked.session.to_bytes())
    assert replay(worked.release, restored) == replay(worked.release, worked.session)
    avery_auth = AuthorizationContext("actor", "actor-avery", "binding-avery-1")
    blake_auth = AuthorizationContext("actor", "actor-blake", "binding-blake-1")
    avery = seat_snapshot(worked.release, restored, avery_auth)
    blake = seat_snapshot(worked.release, restored, blake_auth)
    avery_resources = {item["resource_id"] for item in avery["resources"]}
    blake_resources = {item["resource_id"] for item in blake["resources"]}
    assert "payment-note" in avery_resources and "payment-note" not in blake_resources
    assert "camera-log" in blake_resources and "camera-log" not in avery_resources
    assert "madison-deed-1997" in avery_resources & blake_resources
    assert retrieve_resource(worked.release, restored, avery_auth, "madison-deed-1997").startswith(
        b"%PDF"
    )
    assert "truth_model" not in json.dumps(avery)
    assert "truth_model" not in json.dumps(blake)


def test_physical_export_detects_a_broken_displayed_claim(tmp_path):
    """stage5.claim-gate: a material claim cannot drift silently from its source."""
    build = build_worked_candidate(tmp_path / "forge")
    options = dict(build.candidate.compilation_options)
    claims = [dict(item) for item in options["displayed_claims"]]
    claims[0]["quote"] = "The deed was executed on October 18, 1997."
    options["displayed_claims"] = claims
    frozen = freeze_candidate(
        game=build.candidate.game,
        materials=build.candidate.materials,
        seed=build.candidate.seed,
        component_lock=reference_component_lock(),
        compilation_options=options,
    )
    assert frozen.candidate is not None
    release = compile_candidate(frozen.candidate).release
    assert release is not None
    with pytest.raises(ValueError, match="displayed claim quote is absent"):
        export_physical(release)


def test_complete_rebuild_is_path_independent_and_offline(tmp_path, monkeypatch):
    """stage5.rebuild: all durable outputs are exact without network access."""
    def no_network(*args, **kwargs):
        raise AssertionError("network access is forbidden in the Stage 5 build path")

    monkeypatch.setattr("socket.socket.connect", no_network)
    first = run(tmp_path / "one")
    second = run(tmp_path / "two")
    assert first.summary == second.summary
    for name in (
        "candidate.json",
        "game-release.zip",
        "physical-package.zip",
        "session-history.json",
        "workspace.ngw",
    ):
        assert first.output_root.joinpath(name).read_bytes() == second.output_root.joinpath(
            name
        ).read_bytes()
    verify_physical_export(first.physical, first.release)
    imported = Workspace.import_archive(
        first.output_root / "workspace.ngw", tmp_path / "imported-workspace"
    )
    assert imported.verify()["ok"] is True
    assert digest_json(first.physical.plan) == digest_json(second.physical.plan)


def test_stage5_cli_outputs_are_identical_across_processes(tmp_path):
    """stage5.cross-process: the public worked-example command is reproducible."""
    roots = [tmp_path / "process-one", tmp_path / "process-two"]
    summaries = []
    for root in roots:
        output = subprocess.check_output(
            [sys.executable, "-m", "narrative_game.stage5_fixture", str(root)]
        )
        summaries.append(json.loads(output))
    assert summaries[0] == summaries[1]
    for name in (
        "candidate.json",
        "game-release.zip",
        "physical-package.zip",
        "session-history.json",
        "workspace.ngw",
    ):
        assert roots[0].joinpath("output", name).read_bytes() == roots[1].joinpath(
            "output", name
        ).read_bytes()


def test_an_unfamiliar_operator_has_complete_assembly_and_run_instructions(worked):
    """stage5.independent-operation: the package explains setup, control, and verification."""
    guide = worked.physical.file("guides/assembly-guide.md").data.decode()
    for phrase in (
        "Print every PDF",
        "Confirm each file's page count and hash",
        "Give opening containers before play",
        "Keep the host binder private",
        "record physical disclosure in the Session ledger",
        "verify this package offline",
    ):
        assert phrase in guide
    assert worked.physical.preflight["ok"] is True
    assert worked.workspace.verify()["ok"] is True
