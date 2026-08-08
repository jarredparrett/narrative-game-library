"""Capability tests for matched measurement and governed scheduling."""

from __future__ import annotations

from dataclasses import replace

from narrative_game.contracts.canonical import canonical_json
from narrative_game.difficulty import (
    DIFFICULTY_DIMENSIONS,
    PROTECTED_BUDGETS,
    BudgetEnvelope,
    CostForecast,
    DifficultyTargetContract,
    EpisodeProfileObservation,
    EvaluationPanel,
    EvaluationPolicy,
    EvidenceWorkPackage,
    MetricValue,
    PanelCell,
    SealedCohortHandle,
    StandingSamplingPlan,
    TargetBand,
    apply_evaluation_panel,
    classify_profile,
    decide_target_dominance,
    derive_difficulty_profile,
    schedule_diagnostic_work,
)


REF = lambda value: "sha256:" + value * 64


def _panel():
    return EvaluationPanel(
        (
            EvaluationPolicy(
                "player-a",
                "player",
                "openai",
                "gpt-5.6-terra",
                "gpt-5.6-terra-2026-08-01",
                REF("1"),
                REF("2"),
                {"reasoning": "high", "temperature": "omitted"},
            ),
            EvaluationPolicy(
                "host-a",
                "host",
                "openai",
                "gpt-5.6-sol",
                "gpt-5.6-sol-2026-08-01",
                REF("3"),
                REF("4"),
                {"reasoning": "high", "temperature": "omitted"},
            ),
        ),
        (
            PanelCell(
                "base",
                "ordinary",
                "facilitator-only",
                "public-messages",
                (("investigator", "player-a"), ("host", "host-a")),
            ),
            PanelCell(
                "restricted",
                "handoff-pressure",
                "facilitator-only",
                "private-then-share",
                (("investigator", "player-a"), ("host", "host-a")),
            ),
        ),
        (11, 17),
        2,
        REF("5"),
        REF("6"),
        REF("7"),
        REF("8"),
        "two identical transport retries",
        "invalid remains visible",
    )


def test_panel_application_preserves_panel_identity_and_reports_every_compatibility_grade():
    """difficulty.d3.panel-application: release bindings preserve exact Panel locks."""
    panel = _panel()
    resolutions = {
        "player-a": "gpt-5.6-terra-2026-08-01",
        "host-a": "gpt-5.6-sol-2026-08-01",
    }
    exact = apply_evaluation_panel(
        panel,
        release_id="release-a",
        release_roles=("investigator", "host"),
        release_tool_contract_ref=REF("5"),
        resolved_models=resolutions,
    )
    second = apply_evaluation_panel(
        panel,
        release_id="release-b",
        release_roles=("investigator", "host"),
        release_tool_contract_ref=REF("5"),
        resolved_models=resolutions,
    )
    assert exact.panel_id == second.panel_id == panel.panel_id
    assert exact.application_id != second.application_id
    assert exact.compatibility_grade == "exact"
    assert exact.model_match_grade == "exactly-matched"
    assert len(exact.assignments) == 8

    operational = apply_evaluation_panel(
        panel,
        release_id="release-c",
        release_roles=("investigator", "host"),
        release_tool_contract_ref=REF("5"),
        resolved_models={"player-a": None, "host-a": None},
    )
    assert operational.compatibility_grade == "operational"
    assert operational.model_match_grade == "operationally-matched"

    missing = apply_evaluation_panel(
        panel,
        release_id="release-d",
        release_roles=("host",),
        release_tool_contract_ref=REF("5"),
        resolved_models=resolutions,
    )
    assert missing.compatibility_grade == "incompatible"
    assert any("missing role" in item for item in missing.findings)
    assert len(missing.missing_assignment_ids) == len(missing.assignments)
    assert set(missing.missing_assignment_ids) <= set(missing.incompatible_assignment_ids)

    drift = apply_evaluation_panel(
        panel,
        release_id="release-e",
        release_roles=("investigator", "host"),
        release_tool_contract_ref=REF("9"),
        resolved_models={**resolutions, "player-a": "different-checkpoint"},
    )
    assert drift.compatibility_grade == "incompatible"
    assert any("model drift" in item for item in drift.findings)
    assert any("tool/action" in item for item in drift.findings)
    assert len(drift.incompatible_assignment_ids) == len(drift.assignments)


def _observations(count=10, *, statuses=None):
    statuses = statuses or ["verified"] * count
    result = []
    for index, status in enumerate(statuses):
        metrics = ()
        if status == "verified":
            metrics = (
                MetricValue("episode-validity", "verified", "binary", 1),
                MetricValue("resolution-reliability", "success", "binary", index % 3 != 0),
                MetricValue("progress-and-effort", "actions", "count", 8 + index),
                MetricValue("proof-robustness", "proof-coverage", "continuous", 0.6 + index / 100),
                MetricValue("coordination-quality", "handoff", "binary", index % 2),
                MetricValue("recovery-dependence", "host-hint", "binary", index % 4 == 0),
                MetricValue("sensitivity-and-brittleness", "slice-delta", "continuous", index / 20),
            )
        result.append(
            EpisodeProfileObservation(
                f"assignment-{index:02d}",
                REF(hex(index % 10)[2:]) if status == "verified" else None,
                status,
                "base" if index % 2 == 0 else "restricted",
                f"assignment-{index:02d}",
                metrics,
            )
        )
    return tuple(result)


def test_profile_keeps_seven_distributions_denominators_and_required_uncertainty_methods():
    """difficulty.d3.profile-uncertainty: Profiles retain denominators and honest intervals."""
    statuses = ["verified"] * 8 + ["invalid", "missing"]
    observations = _observations(statuses=statuses)
    expected = tuple(f"assignment-{index:02d}" for index in range(10))
    profile = derive_difficulty_profile(
        release_id="release-a",
        panel_application_id=REF("a"),
        analysis_instrument_id=REF("b"),
        expected_assignment_ids=expected,
        observations=observations,
    )
    assert tuple(profile.dimensions) == DIFFICULTY_DIMENSIONS
    assert profile.status_counts == {
        "verified": 8,
        "invalid": 1,
        "partial": 0,
        "missing": 1,
    }
    success = profile.dimensions["resolution-reliability"][0]
    assert success.denominator == 8
    assert success.numerator == 5
    assert success.interval_method == "wilson-95"
    assert success.interval is not None
    actions = profile.dimensions["progress-and-effort"][0]
    assert actions.interval_method == "stratified-bootstrap-median-95"
    assert actions.interval is not None
    assert actions.interquartile_range == (9.75, 13.25)
    assert len(actions.assignment_ids) == len(actions.observations) == 8
    assert canonical_json(profile.to_mapping()) == canonical_json(
        derive_difficulty_profile(
            release_id="release-a",
            panel_application_id=REF("a"),
            analysis_instrument_id=REF("b"),
            expected_assignment_ids=expected,
            observations=observations,
        ).to_mapping()
    )

    too_small = derive_difficulty_profile(
        release_id="release-small",
        panel_application_id=REF("c"),
        analysis_instrument_id=REF("b"),
        expected_assignment_ids=expected[:7],
        observations=_observations(7),
    )
    assert too_small.dimensions["progress-and-effort"][0].interval is None
    assert too_small.dimensions["progress-and-effort"][0].interval_method == "insufficient-n<8"
    target = DifficultyTargetContract(
        "facilitated-investigation",
        "1",
        _panel().panel_id,
        REF("b"),
        8,
        (TargetBand("resolution-reliability", "success", 0.4, 0.8),),
        calibration_receipt_ref=REF("d"),
    )
    assert classify_profile(profile, target).classification == "indeterminate"
    assert classify_profile(too_small, target).classification == "indeterminate"

    complete = derive_difficulty_profile(
        release_id="release-complete",
        panel_application_id=REF("a"),
        analysis_instrument_id=REF("b"),
        expected_assignment_ids=expected,
        observations=_observations(10),
    )
    metric = complete.dimensions["resolution-reliability"][0]
    baseline_metric = replace(metric, point_estimate=0.2, interval=(0.1, 0.3))
    unresolved_metric = replace(metric, point_estimate=0.3, interval=(0.25, 0.35))
    supported_metric = replace(metric, point_estimate=0.65, interval=(0.6, 0.7))

    def with_metric(value):
        dimensions = dict(complete.dimensions)
        dimensions["resolution-reliability"] = (value,)
        return replace(complete, dimensions=dimensions)

    dominance_target = DifficultyTargetContract(
        "facilitated-investigation",
        "1",
        _panel().panel_id,
        REF("b"),
        10,
        (TargetBand("resolution-reliability", "success", 0.8, 1.0),),
        calibration_receipt_ref=REF("d"),
    )
    unresolved = decide_target_dominance(
        with_metric(baseline_metric),
        with_metric(unresolved_metric),
        dominance_target,
        repair_targets=("resolution-reliability.success",),
    )
    assert unresolved.outcome == "indeterminate"
    assert "paired uncertainty" in unresolved.reasons[0]
    supported = decide_target_dominance(
        with_metric(baseline_metric),
        with_metric(supported_metric),
        dominance_target,
        repair_targets=("resolution-reliability.success",),
    )
    assert supported.outcome == "child-dominates"


def test_diagnostic_outcomes_cannot_change_current_standing_membership_or_stop_time():
    """difficulty.d3.sampling-separation: diagnostics never alter the Standing estimand."""
    plan = StandingSamplingPlan(
        "success under frozen panel",
        ("a", "b", "c"),
        {"base": ("a", "b"), "restricted": ("c",)},
        {"b": ("b-replacement-1", "b-replacement-2")},
        3,
        3,
    )
    before = plan.standing_membership({})
    after_failures = plan.standing_membership({"a": "failed", "b": "invalid"})
    after_diagnostics = plan.standing_membership({"diagnostic-x": "success"})
    assert before == after_failures == after_diagnostics == ("a", "b", "c")
    assert plan.stop_after_assignment_count == 3
    assert plan.replacement_for("b", 0) == "b-replacement-1"
    assert plan.replacement_for("b", 2) is None


def _budget(**overrides):
    limits = {key: 1000 for key in PROTECTED_BUDGETS}
    limits.update(overrides)
    return BudgetEnvelope(limits, {key: 0 for key in PROTECTED_BUDGETS})


def _package(identifier, vector, *, cost=100, category="diagnostics", complete=True, sealed=None, cascade=3, required=3):
    return EvidenceWorkPackage(
        identifier,
        f"claim-{identifier}",
        category,
        complete,
        complete,
        complete,
        complete,
        complete,
        complete,
        complete,
        cascade,
        required,
        f"coverage-{identifier}",
        *vector,
        CostForecast(3, 100, 50, cost, 500, 2, 1, "cost-v1"),
        sealed,
    )


def test_scheduler_applies_evidence_cascade_priority_vector_and_stop_states_deterministically():
    """difficulty.d3.scheduling: complete packages follow one deterministic lexicographic policy."""
    coverage_debt = _package("coverage", (1, 0, 0, 0, 0, 0), cost=500)
    attractive_lower_tier = _package("uncertainty", (0, 9, 9, 9, 9, 9), cost=10)
    incomplete = _package("incomplete", (9, 9, 9, 9, 9, 9), complete=False)
    insufficient_cascade = _package("thin", (8, 8, 8, 8, 8, 8), cascade=1, required=4)
    kwargs = {
        "evidence_snapshot_ref": REF("e"),
        "scheduling_analysis_ref": REF("f"),
        "queue_id": "queue-1",
        "packages": (attractive_lower_tier, incomplete, coverage_debt, insufficient_cascade),
        "budget": _budget(),
    }
    first = schedule_diagnostic_work(**kwargs)
    second = schedule_diagnostic_work(**kwargs)
    assert first.selected == coverage_debt
    assert canonical_json(first.receipt.to_mapping()) == canonical_json(second.receipt.to_mapping())
    assert first.receipt.rejection_reasons["incomplete"] == (
        "Evidence Work Package is incomplete",
    )
    assert "Evidence Cascade is insufficient" in first.receipt.rejection_reasons["thin"][0]
    assert first.budget.spent["diagnostics"] == 500
    assert first.receipt.reservation == {
        "category": "diagnostics",
        "amount_microunits": 500,
        "remaining_before_microunits": 1000,
        "remaining_after_microunits": 500,
    }

    stopped = schedule_diagnostic_work(
        evidence_snapshot_ref=REF("e"),
        scheduling_analysis_ref=REF("f"),
        queue_id="queue-2",
        packages=(_package("expensive", (1, 1, 1, 1, 1, 1), cost=100),),
        budget=_budget(diagnostics=0),
    )
    assert stopped.selected is None
    assert stopped.receipt.stop_state == "unresolved-budget"


def test_standing_and_sealed_budgets_are_protected_and_sealed_cases_remain_opaque():
    """difficulty.d3.budget-sealed: protected reservations and sealed handles cannot leak or split."""
    standing = _package("standing-theft", (9, 9, 9, 9, 9, 9), category="standing")
    handle = SealedCohortHandle("sealed-1", 12, 300, REF("1"))
    partial_cost = _package(
        "sealed-partial", (8, 8, 8, 8, 8, 8), cost=100, category="sealed", sealed="sealed-1"
    )
    full = _package(
        "sealed-full", (1, 1, 1, 1, 1, 1), cost=300, category="sealed", sealed="sealed-1"
    )
    decision = schedule_diagnostic_work(
        evidence_snapshot_ref=REF("2"),
        scheduling_analysis_ref=REF("3"),
        queue_id="sealed-queue",
        packages=(standing, partial_cost, full),
        budget=_budget(),
        sealed_handles={handle.handle_id: handle},
    )
    assert decision.selected == full
    assert decision.budget.spent["standing"] == 0
    assert decision.budget.spent["sealed"] == 300
    assert "protected Standing" in decision.receipt.rejection_reasons["standing-theft"][0]
    assert "complete declared cost" in decision.receipt.rejection_reasons["sealed-partial"][0]
    serialized = canonical_json(handle.to_mapping()).decode()
    assert "case" not in serialized and "result" not in serialized

    reused = schedule_diagnostic_work(
        evidence_snapshot_ref=REF("2"),
        scheduling_analysis_ref=REF("3"),
        queue_id="sealed-queue-2",
        packages=(full,),
        budget=_budget(),
        sealed_handles={handle.handle_id: handle},
        used_sealed_handles=(handle.handle_id,),
    )
    assert reused.selected is None
    assert "single-use" in reused.receipt.rejection_reasons["sealed-full"][0]
