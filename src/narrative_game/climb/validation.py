"""Pure validation of authority, blindness, evidence, and standing rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Iterable

from .model import (
    Authority,
    Evaluation,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReview,
    ModelReceipt,
    Proposal,
    Requirement,
    StandingAttestation,
    Task,
    Transition,
)


_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_BLIND_EXPOSURES = {
    "answer-key",
    "atlas",
    "builder-rationale",
    "finding-detail",
    "prior-score",
    "trusted-truth",
}


@dataclass(frozen=True, order=True)
class ClimbFinding:
    code: str
    severity: str
    locus: str
    quote: str
    message: str

    def to_mapping(self) -> dict[str, str]:
        return dict(self.__dict__)


def _finding(code: str, locus: str, quote: str, message: str) -> ClimbFinding:
    return ClimbFinding(code, "blocker", locus, quote, message)


def _duplicates(kind: str, values: Iterable[str]) -> list[ClimbFinding]:
    return [
        _finding("climb.duplicate-id", f"{kind}:{value}", value, f"{kind} identifier is duplicated")
        for value, count in Counter(values).items()
        if count > 1
    ]


def validate_climb_bundle(
    *,
    authorities: Iterable[Authority] = (),
    instruments: Iterable[FrozenInstrument] = (),
    tasks: Iterable[Task] = (),
    model_receipts: Iterable[ModelReceipt] = (),
    exposures: Iterable[Exposure] = (),
    findings: Iterable[Finding] = (),
    requirements: Iterable[Requirement] = (),
    evaluations: Iterable[Evaluation] = (),
    proposals: Iterable[Proposal] = (),
    reviews: Iterable[HumanReview] = (),
    transitions: Iterable[Transition] = (),
    standings: Iterable[StandingAttestation] = (),
) -> tuple[ClimbFinding, ...]:
    """Validate one closed bundle without fetching, repairing, or mutating it."""
    authorities = tuple(authorities)
    instruments = tuple(instruments)
    tasks = tuple(tasks)
    model_receipts = tuple(model_receipts)
    exposures = tuple(exposures)
    findings = tuple(findings)
    requirements = tuple(requirements)
    evaluations = tuple(evaluations)
    proposals = tuple(proposals)
    reviews = tuple(reviews)
    transitions = tuple(transitions)
    standings = tuple(standings)
    result: list[ClimbFinding] = []

    ids = {
        "authority": [item.authority_id for item in authorities],
        "instrument": [item.instrument_id for item in instruments],
        "task": [item.task_id for item in tasks],
        "model-receipt": [item.receipt_id for item in model_receipts],
        "exposure": [item.exposure_id for item in exposures],
        "finding": [item.finding_id for item in findings],
        "requirement": [item.requirement_id for item in requirements],
        "evaluation": [item.evaluation_id for item in evaluations],
        "proposal": [item.proposal_id for item in proposals],
        "review": [item.review_id for item in reviews],
        "transition": [item.transition_id for item in transitions],
        "standing": [item.attestation_id for item in standings],
    }
    for kind, values in ids.items():
        result.extend(_duplicates(kind, values))

    authority_by_id = {item.authority_id: item for item in authorities}
    instrument_by_id = {item.instrument_id: item for item in instruments}
    task_by_id = {item.task_id: item for item in tasks}
    receipt_by_id = {item.receipt_id: item for item in model_receipts}
    finding_by_id = {item.finding_id: item for item in findings}
    requirement_by_id = {item.requirement_id: item for item in requirements}
    evaluation_by_id = {item.evaluation_id: item for item in evaluations}
    proposal_by_id = {item.proposal_id: item for item in proposals}
    review_by_id = {item.review_id: item for item in reviews}

    for authority in authorities:
        if authority.kind not in {"agent", "human", "system"}:
            result.append(_finding("climb.invalid-authority", authority.authority_id, authority.kind, "authority kind is unsupported"))
        if authority.role not in {"builder", "fixer", "judge", "reviewer", "publisher", "validator"}:
            result.append(_finding("climb.invalid-authority", authority.authority_id, authority.role, "authority role is unsupported"))
        if authority.role in {"reviewer", "publisher"} and authority.kind != "human":
            result.append(_finding("climb.human-authority-required", authority.authority_id, authority.kind, "review and publication authority must be human"))

    for instrument in instruments:
        dimensions = [item.dimension_id for item in instrument.dimensions]
        result.extend(_duplicates("dimension", dimensions))
        if not dimensions or any(item.weight <= 0 for item in instrument.dimensions):
            result.append(_finding("climb.invalid-instrument", instrument.instrument_id, str(dimensions), "instrument requires unique positive-weight dimensions"))
        if not instrument.acceptance_rules or not instrument.blind_protocol:
            result.append(_finding("climb.invalid-instrument", instrument.instrument_id, "missing rules or blind protocol", "instrument must freeze acceptance and blindness rules"))

    for task in tasks:
        authority = authority_by_id.get(task.assigned_authority_id)
        instrument = instrument_by_id.get(task.instrument_id)
        if authority is None:
            result.append(_finding("climb.dangling-reference", task.task_id, task.assigned_authority_id, "Task names a missing Authority"))
        if instrument is None:
            result.append(_finding("climb.dangling-reference", task.task_id, task.instrument_id, "Task names a missing Instrument"))
        if task.kind not in {"build", "fix", "harvest", "blind-measure", "deterministic-validate"}:
            result.append(_finding("climb.invalid-task", task.task_id, task.kind, "Task kind is unsupported"))
        expected_roles = {
            "build": {"builder"},
            "fix": {"builder", "fixer"},
            "harvest": {"judge"},
            "blind-measure": {"judge"},
            "deterministic-validate": {"validator"},
        }.get(task.kind, set())
        if authority is not None and authority.role not in expected_roles:
            result.append(_finding("climb.role-mismatch", task.task_id, authority.role, "Task is assigned to an incompatible role"))
        if task.assigned_authority_id in task.excluded_authority_ids:
            result.append(_finding("climb.excluded-authority", task.task_id, task.assigned_authority_id, "Task is assigned to an explicitly excluded authority"))
        for label, value in {"candidate_id": task.candidate_id, **task.input_refs}.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.invalid-object-reference", task.task_id, f"{label}={value}", "Task Candidate and input references require exact SHA-256 identities"))

    for receipt in model_receipts:
        authority = authority_by_id.get(receipt.authority_id)
        if authority is None:
            result.append(_finding("climb.dangling-reference", receipt.receipt_id, receipt.authority_id, "Model Receipt names a missing Authority"))
        elif authority.kind != "agent" or receipt.role != authority.role:
            result.append(_finding("climb.receipt-authority-mismatch", receipt.receipt_id, f"{authority.kind}:{authority.role}/{receipt.role}", "Model Receipt does not match its agent Authority"))
        for label, value in {
            "prompt_hash": receipt.prompt_hash,
            "context_hash": receipt.context_hash,
            "tool_contract_hash": receipt.tool_contract_hash,
            "raw_output_ref": receipt.raw_output_ref,
            "parsed_output_ref": receipt.parsed_output_ref,
        }.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.incomplete-model-receipt", receipt.receipt_id, f"{label}={value}", "Model Receipt requires exact typed hashes"))
        if not receipt.provider or not receipt.requested_model or not receipt.resolved_model:
            result.append(_finding("climb.incomplete-model-receipt", receipt.receipt_id, "missing provider or model", "Model Receipt requires provider and requested/resolved model"))
        for label, value in {
            **receipt.input_hashes,
            **{f"tool_receipt_{index}": item for index, item in enumerate(receipt.tool_receipt_hashes)},
        }.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.incomplete-model-receipt", receipt.receipt_id, f"{label}={value}", "Model Receipt input and tool receipts require exact SHA-256 identities"))

    for requirement in requirements:
        source_findings = [finding_by_id.get(item) for item in requirement.source_finding_ids]
        missing = [item for item, value in zip(requirement.source_finding_ids, source_findings) if value is None]
        if missing:
            result.append(_finding("climb.dangling-reference", requirement.requirement_id, ", ".join(missing), "Requirement names missing source Findings"))
        normalized_brief = " ".join(requirement.builder_brief.lower().split())
        for source in (item for item in source_findings if item is not None):
            normalized_quote = " ".join(source.quote.lower().split())
            if normalized_quote and normalized_quote in normalized_brief:
                result.append(_finding("climb.answer-leak", requirement.requirement_id, source.quote, "Builder brief repeats a judge-only answer span"))
            if source.locus and source.locus.lower() in requirement.builder_brief.lower():
                result.append(_finding("climb.answer-leak", requirement.requirement_id, source.locus, "Builder brief repeats a judge-only locus"))

    exposures_by_authority: dict[str, list[Exposure]] = {}
    for exposure in exposures:
        exposures_by_authority.setdefault(exposure.authority_id, []).append(exposure)
        if exposure.authority_id not in authority_by_id:
            result.append(_finding("climb.dangling-reference", exposure.exposure_id, exposure.authority_id, "Exposure names a missing Authority"))
        if exposure.before_task_id not in task_by_id:
            result.append(_finding("climb.dangling-reference", exposure.exposure_id, exposure.before_task_id, "Exposure names a missing Task"))

    for evaluation in evaluations:
        task = task_by_id.get(evaluation.task_id)
        instrument = instrument_by_id.get(evaluation.instrument_id)
        if task is None or instrument is None:
            result.append(_finding("climb.dangling-reference", evaluation.evaluation_id, f"{evaluation.task_id}; {evaluation.instrument_id}", "Evaluation names a missing Task or Instrument"))
            continue
        if evaluation.candidate_id != task.candidate_id or evaluation.instrument_id != task.instrument_id:
            result.append(_finding("climb.evaluation-input-mismatch", evaluation.evaluation_id, evaluation.candidate_id, "Evaluation differs from its frozen Task inputs"))
        if evaluation.mode not in {"harvest", "blind"}:
            result.append(_finding("climb.invalid-evaluation", evaluation.evaluation_id, evaluation.mode, "Evaluation mode is unsupported"))
        if evaluation.mode == "harvest" and (evaluation.scores or evaluation.claimed_standing is not None):
            result.append(_finding("climb.harvest-claimed-score", evaluation.evaluation_id, str(dict(evaluation.scores)), "Harvests may record Findings but never a score or standing"))
        if evaluation.mode == "blind":
            if task.kind != "blind-measure":
                result.append(_finding("climb.invalid-blind-task", evaluation.evaluation_id, task.kind, "Blind Evaluation requires a blind-measure Task"))
            dimension_ids = {item.dimension_id for item in instrument.dimensions}
            if set(evaluation.scores) != dimension_ids or any(not 0 <= value <= 100 for value in evaluation.scores.values()):
                result.append(_finding("climb.invalid-score", evaluation.evaluation_id, str(dict(evaluation.scores)), "Blind scores must cover every frozen dimension from 0 to 100"))
            for judge_id in evaluation.judge_authority_ids:
                authority = authority_by_id.get(judge_id)
                if authority is None or authority.role != "judge":
                    result.append(_finding("climb.invalid-judge", evaluation.evaluation_id, judge_id, "Blind Evaluation names a missing or non-judge Authority"))
                if judge_id in task.excluded_authority_ids:
                    result.append(_finding("climb.self-judging", evaluation.evaluation_id, judge_id, "Excluded builder or fixer cannot judge the Candidate"))
                task_exposures = [
                    item
                    for item in exposures_by_authority.get(judge_id, [])
                    if item.before_task_id == evaluation.task_id
                ]
                forbidden = sorted({item.category for item in task_exposures} & _FORBIDDEN_BLIND_EXPOSURES)
                if forbidden:
                    result.append(_finding("climb.blindness-contaminated", evaluation.evaluation_id, f"{judge_id}: {', '.join(forbidden)}", "Judge Exposure Ledger contains blind-forbidden material"))
                if not task_exposures:
                    result.append(_finding("climb.missing-exposure-ledger", evaluation.evaluation_id, judge_id, "Every blind judge requires an explicit input Exposure for this Task"))
        missing_receipts = [item for item in evaluation.model_receipt_ids if item not in receipt_by_id]
        if missing_receipts:
            result.append(_finding("climb.dangling-reference", evaluation.evaluation_id, ", ".join(missing_receipts), "Evaluation names missing Model Receipts"))
        if evaluation.mode == "blind" and not missing_receipts:
            receipt_authorities = {
                receipt_by_id[item].authority_id for item in evaluation.model_receipt_ids
            }
            if receipt_authorities != set(evaluation.judge_authority_ids):
                result.append(_finding("climb.judge-receipt-mismatch", evaluation.evaluation_id, str(sorted(receipt_authorities)), "Blind Evaluation receipts must exactly cover its named judges"))
        if set(evaluation.hard_gate_results) != set(instrument.hard_gate_codes):
            result.append(_finding("climb.incomplete-hard-gates", evaluation.evaluation_id, str(dict(evaluation.hard_gate_results)), "Evaluation must replay every frozen hard gate"))
        if evaluation.outcome == "pass" and not all(evaluation.hard_gate_results.values()):
            result.append(_finding("climb.hard-gate-regression", evaluation.evaluation_id, str(dict(evaluation.hard_gate_results)), "Evaluation cannot pass while a hard gate regresses"))

    for proposal in proposals:
        task = task_by_id.get(proposal.task_id)
        authority = authority_by_id.get(proposal.builder_authority_id)
        receipt = receipt_by_id.get(proposal.model_receipt_id)
        if task is None or authority is None or receipt is None:
            result.append(_finding("climb.dangling-reference", proposal.proposal_id, f"{proposal.task_id}; {proposal.builder_authority_id}; {proposal.model_receipt_id}", "Proposal names a missing Task, Authority, or Model Receipt"))
        else:
            if task.kind not in {"build", "fix"} or task.assigned_authority_id != proposal.builder_authority_id:
                result.append(_finding("climb.proposal-authority-mismatch", proposal.proposal_id, proposal.builder_authority_id, "Proposal does not come from its assigned build/fix Task"))
            if receipt.authority_id != proposal.builder_authority_id:
                result.append(_finding("climb.proposal-receipt-mismatch", proposal.proposal_id, receipt.authority_id, "Proposal Model Receipt belongs to another Authority"))
        missing_requirements = [item for item in proposal.requirement_ids if item not in requirement_by_id]
        if missing_requirements:
            result.append(_finding("climb.dangling-reference", proposal.proposal_id, ", ".join(missing_requirements), "Proposal names missing Requirements"))
        for label, value in {
            "baseline_draft_ref": proposal.baseline_draft_ref,
            "proposed_data_ref": proposal.proposed_data_ref,
        }.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.invalid-object-reference", proposal.proposal_id, f"{label}={value}", "Proposal content requires exact Workspace object references"))

    for review in reviews:
        proposal = proposal_by_id.get(review.proposal_id)
        reviewer = authority_by_id.get(review.reviewer_authority_id)
        if proposal is None:
            result.append(_finding("climb.dangling-reference", review.review_id, review.proposal_id, "Human Review names a missing Proposal"))
        if reviewer is None or reviewer.kind != "human" or reviewer.role != "reviewer":
            result.append(_finding("climb.human-authority-required", review.review_id, review.reviewer_authority_id, "Proposal review requires a human reviewer Authority"))
        if review.decision not in {"approved", "rejected"}:
            result.append(_finding("climb.invalid-review", review.review_id, review.decision, "Human Review decision is unsupported"))
        if review.decision == "approved" and proposal is not None and set(review.approved_requirement_ids) != set(proposal.requirement_ids):
            result.append(_finding("climb.partial-approval", review.review_id, str(review.approved_requirement_ids), "Approved transition must explicitly cover every Proposal Requirement"))

    for transition in transitions:
        proposal = proposal_by_id.get(transition.proposal_id)
        review = review_by_id.get(transition.review_id)
        if proposal is None or review is None:
            result.append(_finding("climb.dangling-reference", transition.transition_id, f"{transition.proposal_id}; {transition.review_id}", "Transition names a missing Proposal or Review"))
            continue
        if review.proposal_id != proposal.proposal_id or review.decision != "approved":
            result.append(_finding("climb.unauthorized-transition", transition.transition_id, review.decision, "Only an approved Review of this Proposal may advance canonical state"))
        if transition.reviewer_authority_id != review.reviewer_authority_id:
            result.append(_finding("climb.unauthorized-transition", transition.transition_id, transition.reviewer_authority_id, "Transition authority differs from the approving human"))
        if transition.parent_draft_ref != proposal.baseline_draft_ref or transition.proposed_data_ref != proposal.proposed_data_ref:
            result.append(_finding("climb.transition-content-mismatch", transition.transition_id, f"{transition.parent_draft_ref} -> {transition.proposed_data_ref}", "Transition differs from the reviewed Proposal"))
        for label, value in {
            "parent_draft_ref": transition.parent_draft_ref,
            "proposed_data_ref": transition.proposed_data_ref,
            "child_draft_ref": transition.child_draft_ref,
        }.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.invalid-object-reference", transition.transition_id, f"{label}={value}", "Transition content requires exact Workspace object references"))

    for standing in standings:
        reviewer = authority_by_id.get(standing.reviewer_authority_id)
        linked = [evaluation_by_id.get(item) for item in standing.evaluation_ids]
        if reviewer is None or reviewer.kind != "human" or reviewer.role not in {"reviewer", "publisher"}:
            result.append(_finding("climb.human-authority-required", standing.attestation_id, standing.reviewer_authority_id, "Standing requires human review or publication authority"))
        if any(item is None for item in linked):
            result.append(_finding("climb.dangling-reference", standing.attestation_id, str(standing.evaluation_ids), "Standing names missing Evaluations"))
            continue
        linked_evaluations = [item for item in linked if item is not None]
        if any(item.candidate_id != standing.candidate_id for item in linked_evaluations):
            result.append(_finding("climb.standing-candidate-mismatch", standing.attestation_id, standing.candidate_id, "Standing evidence evaluates another Candidate"))
        if standing.level not in {"development_only", "machine_qualified", "accepted"}:
            result.append(_finding("climb.invalid-standing", standing.attestation_id, standing.level, "Standing level is unsupported"))
        if standing.level == "machine_qualified":
            if "model-blind-panel" not in standing.evidence_kinds or not linked_evaluations or any(item.mode != "blind" or item.outcome != "pass" for item in linked_evaluations):
                result.append(_finding("climb.unsupported-standing", standing.attestation_id, str(standing.evidence_kinds), "Machine-qualified standing requires passing blind model evidence"))
        if standing.level == "accepted":
            required = {"two-fresh-human-runs", "independent-standing-review"}
            if not required <= set(standing.evidence_kinds):
                result.append(_finding("climb.unsupported-standing", standing.attestation_id, str(standing.evidence_kinds), "Accepted standing requires two fresh human runs and independent review"))

    return tuple(sorted(set(result)))
