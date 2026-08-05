"""Deterministic selection under one frozen measurement instrument."""

from __future__ import annotations

from .model import (
    Evaluation,
    FrozenInstrument,
    HumanReceipt,
    ModelReceipt,
    SelectionDecision,
)


def _compare(actual: float | bool, operator: str, expected: float | bool) -> bool:
    if operator == ">=":
        return actual >= expected
    if operator == ">":
        return actual > expected
    if operator == "<=":
        return actual <= expected
    if operator == "<":
        return actual < expected
    if operator == "==":
        return actual == expected
    if operator == "all":
        return bool(actual) is bool(expected)
    raise ValueError(f"unsupported acceptance operator: {operator!r}")


def evaluation_passes(instrument: FrozenInstrument, evaluation: Evaluation) -> bool:
    """Apply every frozen acceptance rule without trusting a claimed outcome."""
    overall = evaluation.overall_score(instrument)
    if overall is None:
        return False
    dimension_scores = dict(evaluation.scores)
    for rule in instrument.acceptance_rules:
        metric = rule.get("metric")
        operator = rule.get("operator")
        expected = rule.get("value")
        if metric in {"overall", "overall_min"}:
            actual: float | bool = overall
        elif metric == "hard_gates":
            actual = bool(evaluation.hard_gate_results) and all(
                evaluation.hard_gate_results.values()
            )
        elif metric in dimension_scores:
            actual = dimension_scores[metric]
        else:
            raise ValueError(f"unsupported acceptance metric: {metric!r}")
        if not _compare(actual, str(operator), expected):
            return False
    return True


def decide_selection(
    instrument: FrozenInstrument,
    baseline: Evaluation,
    child: Evaluation,
    receipts: tuple[ModelReceipt | HumanReceipt, ...],
) -> SelectionDecision:
    """Choose evidence for the next rung without authorizing a Draft transition."""
    if baseline.instrument_id != instrument.instrument_id or child.instrument_id != instrument.instrument_id:
        raise ValueError("Selection Evaluations must share the frozen Instrument")
    if baseline.candidate_id == child.candidate_id:
        raise ValueError("Selection requires distinct baseline and child Candidates")
    receipt_by_id = {item.receipt_id: item for item in receipts}
    receipt_ids = (
        *baseline.model_receipt_ids,
        *baseline.human_receipt_ids,
        *child.model_receipt_ids,
        *child.human_receipt_ids,
    )
    if any(item not in receipt_by_id for item in receipt_ids):
        raise ValueError("Selection requires every Evaluation evidence Receipt")
    evidence_classes = {receipt_by_id[item].evidence_class for item in receipt_ids}
    allowed = set(instrument.blind_protocol.get("selection_evidence_classes", ()))
    evidence_ok = bool(allowed) and bool(evidence_classes) and evidence_classes <= allowed
    baseline_score = baseline.overall_score(instrument)
    child_score = child.overall_score(instrument)
    child_wins = (
        baseline_score is not None
        and child_score is not None
        and child_score > baseline_score
        and evaluation_passes(instrument, child)
        and evidence_ok
    )
    if child_wins:
        outcome = "select_child"
        selected = child.candidate_id
        reason = "Child improves the frozen score, passes every hard gate, and uses admissible evidence."
    else:
        outcome = "retain_baseline"
        selected = baseline.candidate_id
        reason = "Child lacks admissible measured improvement under the frozen Instrument."
    return SelectionDecision(
        instrument.instrument_id,
        baseline.evaluation_id,
        child.evaluation_id,
        outcome,
        selected,
        reason,
    )
