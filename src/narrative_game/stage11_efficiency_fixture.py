"""Worked impact-scoped plan for the Winter Observatory handwriting tell."""

from __future__ import annotations

from typing import Any

from narrative_game.climb import (
    ContractChange,
    EfficiencyPlan,
    PlanningFinding,
    PreflightBudget,
    assess_impact,
    route_finding,
)


def winter_observatory_efficiency_proof() -> tuple[EfficiencyPlan, dict[str, Any]]:
    """Return the smallest falsifying experiment and its honest cost comparison.

    The finding is local to the night observing log's handwriting. Unchanged
    artifact bytes retain prior evidence; this plan neither rebuilds nor judges
    the other eighteen documents.
    """
    finding = PlanningFinding(
        "winter-observatory:handwriting-register",
        "shared_renderer_defect",
        "handwriting-register",
        ("night_observing_log",),
    )
    route = route_finding(finding)
    impact = assess_impact(
        (
            ContractChange(
                "winter-observatory:night-log-content",
                "artifact_content",
                ("night_observing_log",),
                rationale=(
                    "Only the night observing log's visible handwriting contract "
                    "changes; the other eighteen artifact hashes are unchanged."
                ),
            ),
        )
    )
    plan = EfficiencyPlan(
        "artifact_realism",
        "bounded_preflight",
        "winter-observatory:candidate-6",
        "verismill:absolute-v0.3+handwriting-register-v1",
        route.selected_loop,
        (route,),
        impact,
        ("night_observing_log",),
        PreflightBudget(
            max_iterations=3,
            max_model_calls=6,
            max_tokens=18_000,
            minimum_improvement=1,
            repeated_failure_threshold=3,
            escalation_condition=(
                "three non-improving handwriting-register observations update "
                "the owning emitter capability issue"
            ),
            park_condition=(
                "any iteration, call, or token budget exhaustion preserves "
                "Candidate 6 and parks the finding"
            ),
        ),
        baseline_score=0,
    )
    comparison = {
        "schema_version": "0.13",
        "baseline": {
            "historical_candidate_7_preflight_builds": 76,
            "historical_full_artifact_judge_calls": 111,
            "one_full_suite_builds": 19,
            "one_full_suite_judge_calls": 57,
            "basis": (
                "four nineteen-artifact preflights plus the persisted Candidate "
                "3 and Candidate 6 formal-panel history"
            ),
        },
        "impact_scoped": {
            "maximum_preflight_builds": 3,
            "maximum_preflight_model_calls": 6,
            "formal_judge_calls_after_preflight_pass": 3,
            "standing_claims_during_preflight": 0,
            "carry_forward_basis": "content-identical hashes for eighteen artifacts",
        },
        "authority_preserved": {
            "target_and_instrument": "human approval required",
            "repair_tranche": "human approval required once",
            "completed_exact_candidate": "human review required before blind panel",
            "disposition": "human approval required after formal evidence",
        },
        "quality_claim": (
            "The comparison proves reduced work and preserved authority only; "
            "quality remains unclaimed until formal measurement."
        ),
    }
    return plan, comparison
