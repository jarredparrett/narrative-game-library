"""Capability tests for the authenticated Codex Analysis Instrument driver."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from narrative_game.adapters import CodexCLIAnalysisDriver
from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.difficulty import (
    EvidenceGrant,
    analysis_instrument_v1,
    apply_instrument,
    build_analysis_view,
    build_semantic_falsifier_episode,
    expectation_is_satisfied,
)
from narrative_game.experiment.difficulty import EvidenceAccessSession
from narrative_game.simulation import evaluate_episode, verify_episode
from narrative_game.stage_difficulty_live import (
    _live_materials,
    _live_result_report,
    _record_live_hardening_route,
)
from narrative_game.workspace import Workspace


REF = lambda value: "sha256:" + value * 64


def _session():
    definition = analysis_instrument_v1(
        normative_contract_ref=REF("1"),
        published_atlas_ref=REF("2"),
    )
    episode_ref = REF("3")
    application = apply_instrument(definition, episode_package_ref=episode_ref)
    material = {
        "schema_version": "analysis-material.1",
        "category": "episode_structure",
        "spans": [{"source_span_id": "arena:0001", "content": {"event_type": "say"}}],
    }
    material_ref = digest_json(material)
    view = build_analysis_view(
        definition,
        application,
        assignment="sweep-outcome-progress",
        available={
            "episode_structure": EvidenceGrant(
                "episode_structure", material_ref, ("arena:0001",)
            ),
            "verified_actions": EvidenceGrant(
                "verified_actions", material_ref, ("arena:0001",)
            ),
        },
    )
    return view, {material_ref: material}


def test_codex_analysis_driver_preserves_frozen_model_view_and_provider_receipts():
    """difficulty.d2.codex-live-driver: local auth preserves the frozen assignment."""
    seen = {}

    def runner(argv, **kwargs):
        seen["argv"] = argv
        seen["prompt"] = json.loads(kwargs["input"])
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_bytes(
            canonical_json(
                {
                    "status": "complete",
                    "lens": "outcome-progress",
                    "coverage": {"spans": ["arena:0001"]},
                    "signals": [],
                    "counterevidence": [],
                    "omissions": [],
                    "continuation_cursor": None,
                    "analysis_receipt_ref": "pending-runtime-receipt",
                }
            )
        )
        stdout = b"\n".join(
            (
                canonical_json({"type": "thread.started", "thread_id": "live-123"}),
                canonical_json(
                    {
                        "type": "turn.completed",
                        "usage": {"input_tokens": 120, "output_tokens": 40},
                    }
                ),
            )
        )
        return SimpleNamespace(returncode=0, stdout=stdout, stderr=b"")

    view, objects = _session()
    tools = EvidenceAccessSession(view, objects)
    driver = CodexCLIAnalysisDriver(
        model="gpt-5.6-terra",
        max_output_tokens=10000,
        codex_executable="/Applications/Codex",
        runner=runner,
    )
    response = driver.invoke(
        canonical_json({"model": "gpt-5.6-terra", "prompt": "frozen"}),
        tools=tools,
    )
    assert response.resolved_model == "gpt-5.6-terra"
    assert response.provider_response_id == "codex:live-123"
    assert response.usage == {
        "input_tokens": 120,
        "output_tokens": 40,
        "total_tokens": 160,
    }
    assert seen["argv"][seen["argv"].index("--sandbox") + 1] == "read-only"
    assert "--ignore-user-config" in seen["argv"] and "--ignore-rules" in seen["argv"]
    index = seen["prompt"]["admitted_evidence_index"]
    assert len(index) == 1
    assert index[0]["object_ref"] in objects
    assert index[0]["categories"] == ["episode_structure", "verified_actions"]
    assert index[0]["path"].startswith("evidence/")
    assert "repository" in seen["prompt"]["instruction"]
    assert [item["operation"] for item in tools.ledger_value()["exposures"]] == [
        "evidence.get"
    ]


def test_codex_analysis_driver_rejects_instrument_or_invocation_model_drift():
    """difficulty.d2.codex-live-model-lock: local auth cannot change the Instrument."""
    with pytest.raises(ValueError, match="only its two frozen models"):
        CodexCLIAnalysisDriver(
            model="gpt-unfrozen",
            max_output_tokens=100,
            codex_executable="/Applications/Codex",
        )
    view, objects = _session()
    driver = CodexCLIAnalysisDriver(
        model="gpt-5.6-terra",
        max_output_tokens=10000,
        codex_executable="/Applications/Codex",
        runner=lambda *args, **kwargs: None,
    )
    with pytest.raises(ValueError, match="differs from the frozen assignment"):
        driver.invoke(
            canonical_json({"model": "gpt-5.6-sol", "prompt": "drifted"}),
            tools=EvidenceAccessSession(view, objects),
        )


def test_public_semantic_falsifiers_are_replay_valid_and_keep_hidden_oracles_outside_evidence():
    """difficulty.d2.live-fixtures: qualification uses the exact D0 semantic gaps."""
    game_json = Path("fixtures/micro-game/game.json").read_bytes()
    refs = []
    for fixture in ("missing-rescue", "failed-handoff"):
        release, archive, package, expectation = build_semantic_falsifier_episode(
            game_json, fixture=fixture
        )
        assert verify_episode(release, archive) == ()
        assert evaluate_episode(release, archive).aggregate == 1.0
        assert package.verification.status == "verified"
        assert not expectation_is_satisfied(package, expectation)
        assert expectation.expectation_id not in package.to_bytes().decode("utf-8")
        refs.append(package.package_id)
    assert len(set(refs)) == 2


def test_live_materials_include_the_content_addressed_release_for_claim_closure():
    """difficulty.d2.live-claim-closure: release graph edges remain portable."""
    game_json = Path("fixtures/micro-game/game.json").read_bytes()
    release, _, package, expectation = build_semantic_falsifier_episode(
        game_json, fixture="missing-rescue"
    )
    _, objects = _live_materials(release, package, expectation)
    assert release.release_id in objects
    assert digest_json(objects[release.release_id]) == release.release_id


def test_live_hardening_route_quarantines_uncontrasted_agent_findings(tmp_path):
    """difficulty.d5.live-terminal: live hypotheses cannot impersonate Contrasts."""
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="live-route")
    application_ref = workspace.store.put_json({"kind": "application", "id": "live"})
    lineage_ref = workspace.put_evidence_object(
        object_kind="diagnostic_claim",
        object_schema="analysis-lineage.1",
        value={"application_ref": application_ref},
        producer="fixture",
        verifier="fixture",
    )

    def output(value):
        return workspace.put_evidence_object(
            object_kind="analysis_structured_output",
            object_schema="fixture.1",
            value=value,
            producer="fixture",
            verifier="fixture",
        )

    incident_ref = output(
        {
            "status": "complete",
            "included_signal_refs": ["sweep:a#signal:1", "sweep:b#signal:2"],
        }
    )
    semantic_ref = output({"status": "complete"})
    attribution_a = output(
        {"status": "complete", "factors": [{"layer": "interaction"}]}
    )
    attribution_b = output(
        {"status": "complete", "factors": [{"layer": "actor"}]}
    )
    attempts = {}
    for name, principal in (("attribution-a", "analyst:a"), ("attribution-b", "analyst:b")):
        receipt_ref = workspace.put_evidence_object(
            object_kind="analysis_receipt",
            object_schema="analysis-receipt.1",
            value={"principal": principal},
            producer="fixture",
            verifier="fixture",
        )
        attempts[name] = [{"receipt_ref": receipt_ref}]
    report = {
        "assignment_output_refs": {
            "incident-assembler": incident_ref,
            "semantic-interpreter": semantic_ref,
            "attribution-a": attribution_a,
            "attribution-b": attribution_b,
        },
        "attempts": attempts,
        "semantic_path": {
            "incident_status": "complete",
            "independent_signal_sources": 2,
        },
    }
    terminal = _record_live_hardening_route(
        workspace,
        application_ref=application_ref,
        lineage_ref=lineage_ref,
        report=report,
        capsule_path=tmp_path / "hardening.ngc",
    )
    assert terminal["status"] == "quarantined"
    assert terminal["blockers"] == ["fewer than two causal Contrasts support the route"]
    assert Workspace.verify_claim_capsule(tmp_path / "hardening.ngc")["ok"]


def test_live_result_report_separates_model_status_attempts_and_cost(tmp_path):
    """difficulty.d2.live-report: semantic status and provider cost stay visible."""
    workspace = Workspace.create(tmp_path / "report", workspace_id="live-report")

    def output(value):
        return workspace.put_evidence_object(
            object_kind="analysis_structured_output",
            object_schema="fixture.1",
            value=value,
            producer="fixture",
            verifier="fixture",
        )

    outputs = {
        "incident-assembler": output(
            {
                "status": "complete",
                "included_signal_refs": ["sweep:a#one", "sweep:b#two"],
            }
        ),
        "semantic-interpreter": output({"status": "complete"}),
        "attribution-a": output({"status": "partial"}),
        "attribution-b": output({"status": "complete"}),
    }
    assignments = {}
    for index, (name, output_ref) in enumerate(outputs.items(), start=1):
        receipt_ref = workspace.put_evidence_object(
            object_kind="analysis_receipt",
            object_schema="analysis-receipt.1",
            value={
                "attempt": 1,
                "attempt_kind": "initial",
                "runtime_status": "complete",
                "resolved_model": "gpt-5.6-sol",
                "provider_response_id": f"response:{index}",
                "usage": {
                    "input_tokens": index,
                    "output_tokens": 1,
                    "total_tokens": index + 1,
                },
            },
            producer="fixture",
            verifier="fixture",
        )
        assignments[name] = SimpleNamespace(
            structured_output_ref=output_ref,
            attempt_receipt_refs=(receipt_ref,),
        )
    report = _live_result_report(
        workspace, SimpleNamespace(assignment_results=assignments)
    )
    assert report["assignment_output_statuses"]["attribution-a"] == "partial"
    assert report["semantic_path"]["independent_signal_sources"] == 2
    assert report["blind_attribution"]["distinct_outputs"]
    assert report["cost_report"] == {
        "provider_calls": 4,
        "schema_repairs": 0,
        "transport_retries": 0,
        "input_tokens": 10,
        "output_tokens": 4,
        "total_tokens": 14,
    }
