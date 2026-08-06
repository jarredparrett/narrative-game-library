"""Stage 11 acceptance for impact-scoped, bounded hill climbs."""

from __future__ import annotations

import json

import pytest

from narrative_game.climb import (
    FINDING_ROUTES,
    ContractChange,
    EfficiencyPlan,
    PlanningFinding,
    PreflightBudget,
    PreflightObservation,
    assess_impact,
    route_finding,
)
from narrative_game.contracts import canonical_json
from narrative_game.experiment import EfficiencyController
from narrative_game.stage11_efficiency_fixture import (
    winter_observatory_efficiency_proof,
)
from narrative_game.workspace import Workspace


def authorization(plan, boundary, scope):
    return canonical_json(
        {
            "schema_version": "0.13",
            "plan_id": plan.plan_id,
            "boundary": boundary,
            "decision": "approved",
            "scope": scope,
        }
    )


def target_scope(plan):
    return {
        "primary_target": plan.primary_target,
        "instrument_id": plan.instrument_id,
    }


def tranche_scope(plan):
    return {
        "selected_loop": plan.selected_loop,
        "representative_units": list(plan.representative_units),
    }


def workspace(tmp_path):
    return Workspace.create(tmp_path / "experiment", workspace_id="efficient-climb")


def test_finding_routes_choose_the_smallest_loop_and_explain_broadening():
    """stage11.efficiency-routing: every tell class has one default owner and loop."""
    for finding_class, (owner, loop) in FINDING_ROUTES.items():
        finding = PlanningFinding(
            f"finding:{finding_class}", finding_class, "structural-class", ("unit",)
        )
        route = route_finding(finding)
        assert (route.owner, route.selected_loop) == (owner, loop)
        with pytest.raises(ValueError, match="persisted reason"):
            route_finding(finding, requested_loop="complete_world_rebuild")
        broad = route_finding(
            finding,
            requested_loop="complete_world_rebuild",
            broadening_reason="The shared canonical fact has unenumerated dependents.",
        )
        assert broad.broader_than_default
        assert broad.broadening_reason


def test_impact_policy_invalidates_only_contract_dependents():
    """stage11.impact: contract deltas derive the minimum rebuild and replay set."""
    decision = assess_impact(
        (
            ContractChange(
                "same", "artifact_content", ("unchanged",),
                before_hash="sha256:same", after_hash="sha256:same",
                rationale="bytes are identical",
            ),
            ContractChange(
                "render", "renderer_only", ("print",),
                rationale="layout implementation changed",
            ),
            ContractChange(
                "access", "accessible_contract", ("accessible",),
                rationale="accessible wording changed",
            ),
            ContractChange(
                "evidence", "critical_player_evidence", ("clue",),
                rationale="player-facing proof changed",
            ),
            ContractChange(
                "host", "host_only_clarification", ("host",),
                rationale="host recovery wording changed",
            ),
            ContractChange(
                "canonical", "canonical_fact", ("truth",), ("dossier", "clue"),
                rationale="one world fact changed",
            ),
            ContractChange(
                "instrument", "instrument", ("rubric",),
                rationale="threshold changed",
            ),
            ContractChange(
                "same-id-old", "artifact_content", ("truth",),
                before_hash="sha256:old", after_hash="sha256:old",
                rationale="an earlier observation saw identical truth bytes",
            ),
        )
    )
    assert decision.carry_forward_units == ("unchanged",)
    assert set(decision.rebuild_units) == {
        "accessible", "clue", "dossier", "host", "print", "truth"
    }
    assert set(decision.measurement_loops) == {
        "accessibility_parity", "artifact_realism", "formal_measurement"
    }
    assert set(decision.replay_loops) == {
        "affected_evidence_channel", "dependent_projections", "fresh_blind_gameplay"
    }
    assert decision.new_standing_lineage
    assert not decision.comparison_allowed


def test_one_tranche_approval_allows_bounded_work_then_three_failures_escalate(
    tmp_path,
):
    """stage11.stop-rules: one approved tranche runs autonomously but cannot ruminate."""
    ws = workspace(tmp_path)
    plan, _ = winter_observatory_efficiency_proof()
    plan_values = plan.to_mapping()
    plan_values.pop("plan_id")
    plan = EfficiencyPlan.from_mapping(
        {**plan_values, "baseline_score": 80.0}
    )
    controller = EfficiencyController(ws)
    controller.record_plan(
        plan,
        target_authorization_bytes=authorization(
            plan, "target_and_instrument", target_scope(plan)
        ),
    )
    controller.authorize_boundary(
        plan.plan_id,
        boundary="repair_tranche",
        authorization_bytes=authorization(
            plan, "repair_tranche", tranche_scope(plan)
        ),
    )
    states = []
    for index, score in enumerate((80, 79, 78), 1):
        states.append(
            controller.record_observation(
                plan.plan_id,
                PreflightObservation(
                    f"observation:{index}", score, 2, 1_000, False,
                    "handwriting-register",
                ),
            )
        )
    assert states[-1].status == "escalated"
    assert states[-1].next_transition == "update_owning_capability_issue"
    assert states[-1].baseline_preserved
    assert controller.authorized_boundaries(plan.plan_id).count("repair_tranche") == 1
    assert controller.verify()["ok"]


def test_budget_exhaustion_parks_debt_and_observations_are_idempotent(tmp_path):
    """stage11.budgets: budget exhaustion parks debt without silently replacing baseline."""
    ws = workspace(tmp_path)
    base, _ = winter_observatory_efficiency_proof()
    mapping = base.to_mapping()
    mapping.pop("plan_id")
    mapping["budget"] = {
        **mapping["budget"],
        "max_iterations": 1,
        "repeated_failure_threshold": 3,
    }
    mapping["baseline_score"] = 80.0
    plan = EfficiencyPlan.from_mapping(mapping)
    controller = EfficiencyController(ws)
    controller.record_plan(
        plan,
        target_authorization_bytes=authorization(
            plan, "target_and_instrument", target_scope(plan)
        ),
    )
    controller.authorize_boundary(
        plan.plan_id,
        boundary="repair_tranche",
        authorization_bytes=authorization(
            plan, "repair_tranche", tranche_scope(plan)
        ),
    )
    observation = PreflightObservation("one", 79, 1, 100, False, "same-tell")
    first = controller.record_observation(plan.plan_id, observation)
    second = controller.record_observation(plan.plan_id, observation)
    assert first == second
    assert first.status == "parked"
    assert first.next_transition == "preserve_baseline_and_park_debt"
    assert len(first.processed_observation_ids) == 1
    assert controller.verify()["ok"]


def test_active_projection_is_portable_replayable_and_detects_staleness(tmp_path):
    """stage11.active-projection: the operator view derives from portable journal state."""
    ws = workspace(tmp_path)
    plan, comparison = winter_observatory_efficiency_proof()
    controller = EfficiencyController(ws)
    controller.record_plan(
        plan,
        target_authorization_bytes=authorization(
            plan, "target_and_instrument", target_scope(plan)
        ),
    )
    projection = json.loads((ws.root / "active-experiment.json").read_bytes())
    assert projection["primary_target"] == "artifact_realism"
    assert projection["representative_units"] == ["night_observing_log"]
    assert projection["invalidation"]["rebuild_units"] == ["night_observing_log"]
    assert comparison["baseline"]["historical_candidate_7_preflight_builds"] == 76
    assert comparison["baseline"]["historical_full_artifact_judge_calls"] == 111
    assert comparison["impact_scoped"]["formal_judge_calls_after_preflight_pass"] == 3
    assert comparison["impact_scoped"]["standing_claims_during_preflight"] == 0
    archive = tmp_path / "efficient.ngw"
    ws.export_archive(archive)
    imported = Workspace.import_archive(archive, tmp_path / "relocated")
    relocated = EfficiencyController(imported)
    assert relocated.verify()["ok"]
    (imported.root / "active-experiment.json").write_text("{}")
    assert not relocated.verify()["ok"]
    relocated.write_projection()
    assert relocated.verify()["ok"]


def test_formal_measurement_freezes_child_and_excludes_its_fixer():
    """stage11.formal-boundary: standing needs an exact child and independent judges."""
    preflight, _ = winter_observatory_efficiency_proof()
    values = preflight.to_mapping()
    values.pop("plan_id")
    values.update(
        mode="formal_measurement",
        budget=None,
        representative_units=[],
        baseline_score=None,
        exact_candidate_id="winter-observatory:candidate-7",
        fixer_authority_ids=["agent:fixer"],
        judge_authority_ids=["agent:judge-a", "agent:judge-b", "agent:judge-c"],
        standing_claim_allowed=True,
    )
    formal = EfficiencyPlan.from_mapping(values)
    assert formal.exact_candidate_id == "winter-observatory:candidate-7"
    values["judge_authority_ids"] = ["agent:fixer"]
    with pytest.raises(ValueError, match="cannot certify"):
        EfficiencyPlan.from_mapping(values)


def test_formal_panel_runs_once_between_candidate_review_and_disposition(tmp_path):
    """stage11.review-boundaries: exact review and disposition bracket formal evidence."""
    ws = workspace(tmp_path)
    preflight, _ = winter_observatory_efficiency_proof()
    values = preflight.to_mapping()
    values.pop("plan_id")
    values.update(
        mode="formal_measurement",
        budget=None,
        representative_units=[],
        baseline_score=None,
        exact_candidate_id="winter-observatory:candidate-7",
        fixer_authority_ids=["agent:fixer"],
        judge_authority_ids=["agent:judge-a", "agent:judge-b", "agent:judge-c"],
        standing_claim_allowed=True,
    )
    plan = EfficiencyPlan.from_mapping(values)
    controller = EfficiencyController(ws)
    controller.record_plan(
        plan,
        target_authorization_bytes=authorization(
            plan, "target_and_instrument", target_scope(plan)
        ),
    )
    with pytest.raises(ValueError, match="Candidate review"):
        controller.record_formal_measurement(
            plan.plan_id,
            candidate_id=plan.exact_candidate_id,
            instrument_id=plan.instrument_id,
            judge_authority_ids=plan.judge_authority_ids,
            evidence_bytes=b"formal panel evidence",
        )
    controller.authorize_boundary(
        plan.plan_id,
        boundary="completed_exact_candidate",
        authorization_bytes=authorization(
            plan,
            "completed_exact_candidate",
            {"candidate_id": plan.exact_candidate_id},
        ),
    )
    controller.record_formal_measurement(
        plan.plan_id,
        candidate_id=plan.exact_candidate_id,
        instrument_id=plan.instrument_id,
        judge_authority_ids=plan.judge_authority_ids,
        evidence_bytes=b"formal panel evidence",
    )
    assert controller.derive_projection()["next_authorized_transition"] == (
        "independent_review:disposition"
    )
    controller.authorize_boundary(
        plan.plan_id,
        boundary="disposition",
        authorization_bytes=authorization(
            plan,
            "disposition",
            {"candidate_id": plan.exact_candidate_id, "outcome": "retain_baseline"},
        ),
    )
    assert controller.derive_projection()["next_authorized_transition"] == (
        "qualification_transition_complete"
    )
    assert controller.verify()["ok"]
