"""Capability tests for frozen Analysis Instrument execution."""

from __future__ import annotations

from copy import deepcopy
import json

import pytest

from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.adapters import OpenAIResponsesAnalysisDriver
from narrative_game.difficulty import (
    ASSIGNMENTS,
    VIEW_CONTRACTS,
    EvidenceGrant,
    analysis_instrument_v1,
    apply_instrument,
    build_analysis_view,
    evaluate_analysis_eligibility,
)
from narrative_game.experiment.difficulty import (
    AnalysisModelResponse,
    AnalysisTransportError,
    EvidenceAccessSession,
    _aggregate_material,
    run_analysis_assignment,
    run_analysis_lineage,
)
from narrative_game.workspace import Workspace


CONTRACT_REF = "sha256:" + "1" * 64
ATLAS_REF = "sha256:" + "2" * 64
EPISODE_REF = "sha256:" + "3" * 64


def _instrument():
    definition = analysis_instrument_v1(
        normative_contract_ref=CONTRACT_REF,
        published_atlas_ref=ATLAS_REF,
    )
    return definition, apply_instrument(definition, episode_package_ref=EPISODE_REF)


def _available():
    categories = {
        category
        for contract in VIEW_CONTRACTS.values()
        for category in (*contract["allow"], *contract["deny"])
    }
    objects = {
        digest_json({"schema_version": "fixture-material.1", "category": category}): {
            "schema_version": "fixture-material.1",
            "category": category,
        }
        for category in categories
    }
    grants = {
        value["category"]: EvidenceGrant(value["category"], object_ref)
        for object_ref, value in objects.items()
    }
    return grants, objects


def _base_lineage(application):
    return {
        "schema_version": "analysis-lineage-fixture.1",
        "episode_actor_principals": ["episode:host", "episode:seat:a"],
        "assignments": {
            item.assignment: {
                "principal": next(
                    applied.principal
                    for applied in application.assignments
                    if applied.assignment == item.assignment
                ),
                "view_ref": "sha256:" + "4" * 64,
                "denied_exposures": [],
                "receipt_complete": True,
                "status": "complete",
                "attempts": [
                    {"kind": "initial", "receipt_ref": "sha256:" + "5" * 64}
                ],
                "mutated_proposal": False,
            }
            for item in ASSIGNMENTS
        },
        "attribution_cross_exposure": False,
        "no_finding_claim": False,
        "corroboration_claim": True,
    }


def test_analysis_material_bundles_admit_content_not_only_opaque_references(tmp_path):
    """difficulty.d2.bundle-content: downstream agents can inspect upstream outputs."""
    workspace = Workspace.create(tmp_path / "bundle", workspace_id="bundle")
    upstream_ref = workspace.put_evidence_object(
        object_kind="analysis_structured_output",
        object_schema="discovery-sweep.1",
        value={"status": "complete", "signals": ["signal:one"]},
        producer="fixture",
        verifier="fixture",
    )
    grant, value = _aggregate_material(
        workspace,
        category="frozen_discovery_outputs",
        object_refs=(upstream_ref,),
    )
    assert grant.object_ref == workspace.store.put_json(value)
    assert value["value"]["object_refs"] == [upstream_ref]
    assert value["value"]["objects"][upstream_ref] == workspace.store.read_json(
        upstream_ref
    )


def _valid_sweep(receipt_ref: str = "analysis-receipt:pending"):
    return {
        "status": "complete",
        "lens": "outcome-progress",
        "coverage": {"start": 0, "end": 9, "complete": True},
        "signals": [],
        "counterevidence": [],
        "omissions": [],
        "continuation_cursor": None,
        "analysis_receipt_ref": receipt_ref,
    }


class ScriptedDriver:
    def __init__(self, events):
        self.events = list(events)
        self.requests = []

    def invoke(self, request: bytes, *, tools) -> AnalysisModelResponse:
        self.requests.append(request)
        event = self.events.pop(0)
        if isinstance(event, Exception):
            raise event
        return event


class FakeResponses:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        usage = type("Usage", (), {"input_tokens": 12, "output_tokens": 7, "total_tokens": 19})()
        return type(
            "Response",
            (),
            {
                "status": "completed",
                "id": "response-live-fixture",
                "model": "gpt-5.6-terra",
                "output_text": canonical_json(_valid_sweep()).decode(),
                "usage": usage,
            },
        )()


class FakeOpenAI:
    def __init__(self):
        self.responses = FakeResponses()


def _response(value, *, response_id="response-1"):
    raw = value if isinstance(value, bytes) else canonical_json(value)
    return AnalysisModelResponse(raw, "gpt-5.6-terra", response_id, {"input_tokens": 10, "output_tokens": 5})


def test_instrument_identity_commits_models_prompts_views_tools_schemas_retries_conflicts_and_atlas():
    """difficulty.d2.instrument-identity: Definition and Application drift create new refs."""
    definition, application = _instrument()
    material = definition.to_mapping()
    assert definition.schema_version == "analysis-instrument.1"
    assert len(material["assignments"]) == 12
    assert material["models"]["deep"]["requested_model"] == "gpt-5.6-sol"
    assert material["models"]["diverse"]["requested_model"] == "gpt-5.6-terra"
    assert material["retry_policy"]["semantic_retry"] == "forbidden"
    assert material["retry_policy"]["best_of"] == "forbidden"
    assert material["published_atlas_ref"] == ATLAS_REF

    changed_definition = analysis_instrument_v1(
        normative_contract_ref=CONTRACT_REF,
        published_atlas_ref="sha256:" + "9" * 64,
    )
    assert changed_definition.definition_ref != definition.definition_ref
    changed_application = apply_instrument(
        definition,
        episode_package_ref=EPISODE_REF,
        resolved_models={"attribution-b": "gpt-5.6-terra-2026-08-09"},
    )
    assert changed_application.application_ref != application.application_ref


def test_each_analysis_authority_receives_only_its_content_addressed_evidence_view():
    """difficulty.d2.evidence-views: twelve authorities receive least-authority views."""
    definition, application = _instrument()
    available, objects = _available()
    views = {
        item.assignment: build_analysis_view(
            definition,
            application,
            assignment=item.assignment,
            available=available,
        )
        for item in ASSIGNMENTS
    }
    assert len({view.view_ref for view in views.values()}) == 12
    for item in ASSIGNMENTS:
        view = views[item.assignment]
        contract = VIEW_CONTRACTS[item.view]
        categories = {grant.category for grant in view.grants}
        assert categories <= set(contract["allow"])
        assert not categories & set(contract["deny"])

    assembler_categories = {item.category for item in views["incident-assembler"].grants}
    assert assembler_categories == set(VIEW_CONTRACTS["assembly"]["allow"])
    assert "canonical_episode_evidence" not in assembler_categories
    assert "other_attribution_output" not in {
        item.category for item in views["attribution-a"].grants
    }

    discovery = views["sweep-outcome-progress"]
    admitted = discovery.grants[0]
    session = EvidenceAccessSession(discovery, objects)
    assert session.get(admitted.object_ref)["category"] == admitted.category
    denied_ref = available["canonical_world_truth"].object_ref
    with pytest.raises(PermissionError, match="outside the Evidence View"):
        session.get(denied_ref)
    ledger = session.ledger_value()
    assert ledger["view_ref"] == discovery.view_ref
    assert ledger["exposures"] == [
        {"operation": "evidence.get", "object_ref": admitted.object_ref, "span_ids": []}
    ]


def test_instrument_v1_accepts_reference_lineage_and_rejects_all_nine_boundary_failures():
    """difficulty.d2.eligibility: all specified contamination boundaries fail closed."""
    definition, application = _instrument()
    valid = _base_lineage(application)
    assert evaluate_analysis_eligibility(definition, application, valid).eligible

    cases = []
    truth_leak = deepcopy(valid)
    truth_leak["assignments"]["sweep-outcome-progress"]["denied_exposures"] = ["canonical_world_truth"]
    cases.append((truth_leak, "view.denied-exposure"))

    collision = deepcopy(valid)
    collision["assignments"]["independent-reviewer"]["principal"] = collision["assignments"]["atlas-curator"]["principal"]
    cases.append((collision, "principal.conflict"))

    cross_exposure = deepcopy(valid)
    cross_exposure["attribution_cross_exposure"] = True
    cases.append((cross_exposure, "attribution.cross-exposure"))

    partial = deepcopy(valid)
    partial["assignments"]["sweep-host-dependence"]["status"] = "partial"
    cases.append((partial, "discovery.partial-claim"))

    retry = deepcopy(valid)
    retry["assignments"]["semantic-interpreter"]["attempts"].append(
        {"kind": "semantic-retry", "receipt_ref": "sha256:" + "6" * 64}
    )
    cases.append((retry, "attempt.forbidden"))

    receipt = deepcopy(valid)
    receipt["assignments"]["challenge-designer"]["receipt_complete"] = False
    cases.append((receipt, "receipt.incomplete"))

    mutation = deepcopy(valid)
    mutation["assignments"]["independent-reviewer"]["mutated_proposal"] = True
    cases.append((mutation, "reviewer.proposal-mutation"))

    actor = deepcopy(valid)
    actor["assignments"]["sweep-knowledge-support"]["principal"] = "episode:seat:a"
    cases.append((actor, "principal.episode-actor"))

    assert len(cases) == 8  # one eligible reference plus eight rejected cases is Instrument v1's nine fixtures
    for lineage, code in cases:
        result = evaluate_analysis_eligibility(definition, application, lineage)
        assert not result.eligible
        assert code in {item.code for item in result.findings}


def test_analysis_attempts_preserve_failures_and_forbid_semantic_or_best_of_retry(tmp_path):
    """difficulty.d2.attempts: only bounded transport/schema retries retain every attempt."""
    definition, application = _instrument()
    available, _ = _available()
    view = build_analysis_view(
        definition,
        application,
        assignment="sweep-outcome-progress",
        available=available,
    )

    transport_workspace = Workspace.create(tmp_path / "transport", workspace_id="transport")
    transport_driver = ScriptedDriver(
        [AnalysisTransportError("timeout"), _response(_valid_sweep())]
    )
    transport = run_analysis_assignment(
        transport_workspace,
        definition=definition,
        application=application,
        view=view,
        driver=transport_driver,
    )
    assert transport.status == "complete"
    assert len(transport.attempt_receipt_refs) == 2
    first, second = [
        transport_workspace.store.read_json(ref)["value"]
        for ref in transport.attempt_receipt_refs
    ]
    assert first["runtime_status"] == "transport-failed"
    assert first["request_ref"] == second["request_ref"]
    assert [first["attempt_kind"], second["attempt_kind"]] == ["initial", "transport-retry"]

    repair_workspace = Workspace.create(tmp_path / "repair", workspace_id="repair")
    repair_driver = ScriptedDriver(
        [_response({"status": "complete"}), _response(_valid_sweep(), response_id="response-2")]
    )
    repair = run_analysis_assignment(
        repair_workspace,
        definition=definition,
        application=application,
        view=view,
        driver=repair_driver,
    )
    assert repair.status == "complete"
    assert len(repair.attempt_receipt_refs) == 2
    repair_receipts = [repair_workspace.store.read_json(ref)["value"] for ref in repair.attempt_receipt_refs]
    assert repair_receipts[0]["runtime_status"] == "schema-invalid"
    assert repair_receipts[1]["attempt_kind"] == "schema-repair"
    assert repair_receipts[0]["request_ref"] != repair_receipts[1]["request_ref"]

    exhausted_workspace = Workspace.create(tmp_path / "exhausted", workspace_id="exhausted")
    exhausted = run_analysis_assignment(
        exhausted_workspace,
        definition=definition,
        application=application,
        view=view,
        driver=ScriptedDriver([AnalysisTransportError("one"), AnalysisTransportError("two"), AnalysisTransportError("three")]),
    )
    assert exhausted.status == "incomplete"
    assert len(exhausted.attempt_receipt_refs) == 3
    kinds = [
        exhausted_workspace.store.read_json(ref)["value"]["attempt_kind"]
        for ref in exhausted.attempt_receipt_refs
    ]
    assert kinds == ["initial", "transport-retry", "transport-retry"]
    assert "semantic-retry" not in kinds and "best-of" not in kinds


def test_openai_analysis_driver_uses_exact_model_settings_and_records_admitted_exposure():
    """difficulty.d2.live-driver: Responses calls omit unfrozen sampling knobs."""
    definition, application = _instrument()
    available, objects = _available()
    view = build_analysis_view(
        definition,
        application,
        assignment="sweep-outcome-progress",
        available=available,
    )
    session = EvidenceAccessSession(view, objects)
    client = FakeOpenAI()
    driver = OpenAIResponsesAnalysisDriver(
        model="gpt-5.6-terra", max_output_tokens=10000, client=client
    )
    response = driver.invoke(canonical_json({"prompt": "fixture"}), tools=session)
    assert response.resolved_model == "gpt-5.6-terra"
    call = client.responses.calls[0]
    assert call["model"] == "gpt-5.6-terra"
    assert call["reasoning"] == {"effort": "high"}
    assert call["max_output_tokens"] == 10000
    assert call["store"] is False
    assert not {"temperature", "top_p", "seed"} & set(call)
    assert len(session.ledger_value()["exposures"]) == len(view.grants)


def _valid_output(schema: str):
    receipt = "analysis-receipt:pending"
    values = {
        "discovery-sweep.1": _valid_sweep(receipt),
        "incident-assembly.1": {
            "status": "complete",
            "included_signal_refs": [],
            "excluded_signal_refs": [],
            "grouping_obligation": "No frozen Signals required grouping.",
            "graph_connection": [],
            "disagreement": [],
            "targeted_sweep_request": None,
            "analysis_receipt_ref": receipt,
        },
        "semantic-interpretation.1": {
            "status": "complete",
            "incident_ref": "incident:none",
            "domain_statement": "No Incident was assembled.",
            "actors": [],
            "phases": [],
            "public_obligations": [],
            "observed_transitions": [],
            "missing_or_uncertain_transitions": [],
            "consequence": "No semantic conclusion.",
            "span_refs": [],
            "analysis_receipt_ref": receipt,
        },
        "causal-hypothesis-set.1": {
            "status": "complete",
            "incident_ref": "incident:none",
            "factors": [],
            "interactions": [],
            "alternatives": [],
            "overall_uncertainty": "insufficient incident evidence",
            "analysis_receipt_ref": receipt,
        },
        "atlas-revision-proposal.1": {
            "status": "complete",
            "parent_atlas_ref": ATLAS_REF,
            "class_changes": [],
            "evidence_refs": [],
            "detector_or_rubric": None,
            "positive_fixtures": [],
            "non_manifesting_controls": [],
            "migration": None,
            "unresolved_evidence": ["No Incident was assembled."],
            "analysis_receipt_ref": receipt,
        },
        "challenge-case-proposal.1": {
            "status": "complete",
            "failure_class_ref": "failure-class:fixture",
            "generation_intent_ref": "generation-intent:fixture",
            "mutation": "fixture-only",
            "protected_invariants": [],
            "initial_state": {},
            "legal_actions": [],
            "terminal_requirements": [],
            "oracle": {},
            "expected_manifestation": {},
            "non_manifesting_control": {},
            "target_profile": {},
            "admission_plan": {},
            "analysis_receipt_ref": receipt,
        },
        "independent-review.1": {
            "status": "complete",
            "proposal_ref": "proposal:fixture",
            "gate_results": {"receipts": True},
            "disagreements": [],
            "missing_evidence": [],
            "decision": "accept",
            "reasons": ["Fixture lineage is mechanically complete."],
            "analysis_receipt_ref": receipt,
        },
    }
    return values[schema]


class LineageDriver:
    def __init__(self, output, resolved_model, response_id):
        self.output = output
        self.resolved_model = resolved_model
        self.response_id = response_id

    def invoke(self, request: bytes, *, tools) -> AnalysisModelResponse:
        if tools.view.grants:
            tools.get(tools.view.grants[0].object_ref)
        return AnalysisModelResponse(
            canonical_json(self.output),
            self.resolved_model,
            self.response_id,
            {"input_tokens": 20, "output_tokens": 10, "total_tokens": 30},
        )


def test_complete_twelve_assignment_lineage_exports_a_portable_diagnostic_capsule(tmp_path):
    """difficulty.d2.lineage: one complete run freezes receipts, eligibility, and claim closure."""
    episode = {"schema_version": "episode-evidence.1", "episode_id": "episode:fixture"}
    episode_ref = digest_json(episode)
    definition = analysis_instrument_v1(
        normative_contract_ref=CONTRACT_REF,
        published_atlas_ref=ATLAS_REF,
    )
    application = apply_instrument(definition, episode_package_ref=episode_ref)
    categories = {
        category
        for contract in VIEW_CONTRACTS.values()
        for category in contract["allow"]
    }
    objects = {episode_ref: episode}
    grants = {}
    for category in sorted(categories):
        value = {"schema_version": "lineage-material.1", "category": category, "spans": []}
        ref = digest_json(value)
        objects[ref] = value
        grants[category] = EvidenceGrant(category, ref)

    specs = {item.assignment: item for item in ASSIGNMENTS}
    applied = {item.assignment: item for item in application.assignments}

    def factory(assignment, view):
        spec = specs[assignment.assignment]
        return LineageDriver(
            _valid_output(spec.output_schema),
            applied[assignment.assignment].resolved_model,
            f"response-{assignment.assignment}",
        )

    workspace = Workspace.create(tmp_path / "lineage", workspace_id="lineage")
    result = run_analysis_lineage(
        workspace,
        definition=definition,
        application=application,
        available_grants=grants,
        evidence_objects=objects,
        driver_factory=factory,
        episode_actor_principals=("episode:host", "episode:seat:a"),
        capsule_path=tmp_path / "diagnostic.ngc",
    )
    assert result.status == "complete"
    assert result.eligibility.eligible
    assert len(result.assignment_results) == 12
    attribution_a_receipt = result.assignment_results["attribution-a"].attempt_receipt_refs[-1]
    attribution_b_receipt = workspace.store.read_json(
        result.assignment_results["attribution-b"].attempt_receipt_refs[-1]
    )["value"]
    assert attribution_a_receipt not in attribution_b_receipt["upstream_receipt_refs"]
    assert result.claim_capsule is not None
    assert Workspace.verify_claim_capsule(result.claim_capsule)["ok"]
    assert workspace.verify_claim_manifest(result.claim_manifest_ref) == ()
