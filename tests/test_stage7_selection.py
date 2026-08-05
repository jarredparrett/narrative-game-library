"""Stage 7 evidence admission and deterministic Selection Decision tests."""

from __future__ import annotations

from dataclasses import replace

from narrative_game.climb import (
    Authority,
    Dimension,
    Evaluation,
    Exposure,
    FrozenInstrument,
    ModelReceipt,
    SelectionDecision,
    Task,
    decide_selection,
    validate_climb_bundle,
)


def sha(character: str) -> str:
    return "sha256:" + character * 64


def measured_pair(evidence_class: str = "live-model"):
    baseline_judge = Authority("judge-baseline", "agent", "judge", "fresh-baseline-judge")
    child_judge = Authority("judge-child", "agent", "judge", "fresh-child-judge")
    instrument = FrozenInstrument(
        "complete-player-experience",
        "1.0.0",
        "compiled-blind-trial",
        (Dimension("quality", "Complete experience quality", 1, {"0": "broken", "100": "excellent"}),),
        (
            {"metric": "overall", "operator": ">=", "value": 75},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "allowed": ["blind-trial"],
            "forbidden": ["trusted-truth", "prior-score"],
            "selection_evidence_classes": ["live-model"],
        },
        ("package.verify",),
    )
    baseline_task = Task(
        "baseline", "blind-measure", sha("a"), instrument.instrument_id,
        baseline_judge.authority_id, (), {"blind_trial": sha("1")}, "Judge the Blind Trial.",
    )
    child_task = Task(
        "child", "blind-measure", sha("b"), instrument.instrument_id,
        child_judge.authority_id, (), {"blind_trial": sha("2")}, "Judge the Blind Trial.",
    )

    def receipt(authority: Authority, character: str) -> ModelReceipt:
        return ModelReceipt(
            authority.authority_id,
            "provider",
            "judge-latest",
            f"judge-{character}-resolved",
            "judge",
            sha(character),
            sha(character),
            sha(character),
            {"blind-trial.zip": sha(character)},
            (),
            sha(character),
            sha(character),
            1997,
            evidence_class=evidence_class,
        )

    baseline_receipt = receipt(baseline_judge, "3")
    child_receipt = receipt(child_judge, "4")
    baseline = Evaluation(
        baseline_task.task_id,
        baseline_task.candidate_id,
        instrument.instrument_id,
        "blind",
        (baseline_judge.authority_id,),
        (baseline_receipt.receipt_id,),
        {"quality": 68},
        (),
        {"package.verify": True},
        "fail",
    )
    child = Evaluation(
        child_task.task_id,
        child_task.candidate_id,
        instrument.instrument_id,
        "blind",
        (child_judge.authority_id,),
        (child_receipt.receipt_id,),
        {"quality": 82},
        (),
        {"package.verify": True},
        "pass",
    )
    exposures = (
        Exposure(baseline_judge.authority_id, sha("1"), "trial-tree", "blind baseline", baseline_task.task_id),
        Exposure(child_judge.authority_id, sha("2"), "trial-tree", "blind child", child_task.task_id),
    )
    return {
        "authorities": (baseline_judge, child_judge),
        "instruments": (instrument,),
        "tasks": (baseline_task, child_task),
        "model_receipts": (baseline_receipt, child_receipt),
        "exposures": exposures,
        "evaluations": (baseline, child),
    }, instrument, baseline, child, (baseline_receipt, child_receipt)


def test_live_blind_improvement_selects_child_without_conflating_human_approval():
    """stage7.selection: admissible improvement chooses evidence for the next rung."""
    bundle, instrument, baseline, child, receipts = measured_pair()
    decision = decide_selection(instrument, baseline, child, receipts)
    assert decision.outcome == "select_child"
    assert decision.selected_candidate_id == child.candidate_id
    bundle["selections"] = (decision,)
    assert validate_climb_bundle(**bundle) == ()


def test_capability_fixture_scores_cannot_select_a_child():
    """stage7.real-measurement: fixture output cannot masquerade as quality evidence."""
    bundle, instrument, baseline, child, receipts = measured_pair("capability-fixture")
    decision = decide_selection(instrument, baseline, child, receipts)
    assert decision.outcome == "retain_baseline"
    forged = SelectionDecision(
        instrument.instrument_id,
        baseline.evaluation_id,
        child.evaluation_id,
        "select_child",
        child.candidate_id,
        "Pretend fixture scores are real.",
    )
    bundle["selections"] = (forged,)
    assert "climb.unsupported-selection" in {
        item.code for item in validate_climb_bundle(**bundle)
    }


def test_hard_gate_regression_retains_baseline_despite_higher_score():
    """stage7.selection: a higher score never waives an accepted hard gate."""
    _, instrument, baseline, child, receipts = measured_pair()
    regressed = replace(child, hard_gate_results={"package.verify": False}, outcome="fail")
    decision = decide_selection(instrument, baseline, regressed, receipts)
    assert decision.outcome == "retain_baseline"
    assert decision.selected_candidate_id == baseline.candidate_id
