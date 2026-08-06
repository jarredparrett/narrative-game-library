"""Pure validation of authority, blindness, evidence, and standing rules."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from statistics import median
from typing import Iterable

from narrative_game.playtest.model import (
    EvidenceComparison,
    PlaytestProtocol,
    PlaytestRun,
)

from .model import (
    Authority,
    Evaluation,
    ExperimentPlan,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReceipt,
    HumanReview,
    ModelReceipt,
    Proposal,
    Requirement,
    SelectionDecision,
    StandingAttestation,
    Task,
    TrialBinding,
    Transition,
)
from .selection import evaluation_passes


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
    experiment_plans: Iterable[ExperimentPlan] = (),
    authorities: Iterable[Authority] = (),
    instruments: Iterable[FrozenInstrument] = (),
    tasks: Iterable[Task] = (),
    model_receipts: Iterable[ModelReceipt] = (),
    human_receipts: Iterable[HumanReceipt] = (),
    exposures: Iterable[Exposure] = (),
    findings: Iterable[Finding] = (),
    requirements: Iterable[Requirement] = (),
    evaluations: Iterable[Evaluation] = (),
    proposals: Iterable[Proposal] = (),
    reviews: Iterable[HumanReview] = (),
    transitions: Iterable[Transition] = (),
    standings: Iterable[StandingAttestation] = (),
    trial_bindings: Iterable[TrialBinding] = (),
    selections: Iterable[SelectionDecision] = (),
    playtest_protocols: Iterable[PlaytestProtocol] = (),
    playtest_runs: Iterable[PlaytestRun] = (),
    evidence_comparisons: Iterable[EvidenceComparison] = (),
) -> tuple[ClimbFinding, ...]:
    """Validate one closed bundle without fetching, repairing, or mutating it."""
    experiment_plans = tuple(experiment_plans)
    authorities = tuple(authorities)
    instruments = tuple(instruments)
    tasks = tuple(tasks)
    model_receipts = tuple(model_receipts)
    human_receipts = tuple(human_receipts)
    exposures = tuple(exposures)
    findings = tuple(findings)
    requirements = tuple(requirements)
    evaluations = tuple(evaluations)
    proposals = tuple(proposals)
    reviews = tuple(reviews)
    transitions = tuple(transitions)
    standings = tuple(standings)
    trial_bindings = tuple(trial_bindings)
    selections = tuple(selections)
    playtest_protocols = tuple(playtest_protocols)
    playtest_runs = tuple(playtest_runs)
    evidence_comparisons = tuple(evidence_comparisons)
    result: list[ClimbFinding] = []

    ids = {
        "experiment-plan": [item.plan_id for item in experiment_plans],
        "authority": [item.authority_id for item in authorities],
        "instrument": [item.instrument_id for item in instruments],
        "task": [item.task_id for item in tasks],
        "model-receipt": [item.receipt_id for item in model_receipts],
        "human-receipt": [item.receipt_id for item in human_receipts],
        "exposure": [item.exposure_id for item in exposures],
        "finding": [item.finding_id for item in findings],
        "requirement": [item.requirement_id for item in requirements],
        "evaluation": [item.evaluation_id for item in evaluations],
        "proposal": [item.proposal_id for item in proposals],
        "review": [item.review_id for item in reviews],
        "transition": [item.transition_id for item in transitions],
        "standing": [item.attestation_id for item in standings],
        "trial-binding": [item.binding_id for item in trial_bindings],
        "selection": [item.decision_id for item in selections],
        "playtest-protocol": [item.protocol_id for item in playtest_protocols],
        "playtest-run": [item.run_id for item in playtest_runs],
        "evidence-comparison": [item.comparison_id for item in evidence_comparisons],
    }
    for kind, values in ids.items():
        result.extend(_duplicates(kind, values))

    authority_by_id = {item.authority_id: item for item in authorities}
    instrument_by_id = {item.instrument_id: item for item in instruments}
    task_by_id = {item.task_id: item for item in tasks}
    receipt_by_id = {item.receipt_id: item for item in model_receipts}
    human_receipt_by_id = {item.receipt_id: item for item in human_receipts}
    finding_by_id = {item.finding_id: item for item in findings}
    requirement_by_id = {item.requirement_id: item for item in requirements}
    evaluation_by_id = {item.evaluation_id: item for item in evaluations}
    proposal_by_id = {item.proposal_id: item for item in proposals}
    review_by_id = {item.review_id: item for item in reviews}
    binding_by_id = {item.binding_id: item for item in trial_bindings}
    protocol_by_id = {item.protocol_id: item for item in playtest_protocols}
    playtest_run_by_id = {item.run_id: item for item in playtest_runs}
    comparison_by_id = {item.comparison_id: item for item in evidence_comparisons}

    if len(experiment_plans) > 1:
        result.append(
            _finding(
                "climb.multiple-experiment-plans",
                "experiment",
                str([item.plan_id for item in experiment_plans]),
                "One Workspace carries exactly one Experiment Plan",
            )
        )
    for plan in experiment_plans:
        if not all(
            value.strip()
            for value in (
                plan.experiment_id,
                plan.profile_id,
                plan.profile_version,
                plan.branch,
            )
        ):
            result.append(
                _finding(
                    "climb.invalid-experiment-plan",
                    plan.plan_id,
                    str(plan.to_mapping()),
                    "Experiment Plan identity, profile, version, and branch are required",
                )
            )
        if plan.instrument_id not in instrument_by_id:
            result.append(
                _finding(
                    "climb.dangling-reference",
                    plan.plan_id,
                    plan.instrument_id,
                    "Experiment Plan names a missing Frozen Instrument",
                )
            )

    for authority in authorities:
        if authority.kind not in {"agent", "human", "system"}:
            result.append(_finding("climb.invalid-authority", authority.authority_id, authority.kind, "authority kind is unsupported"))
        if authority.role not in {"builder", "fixer", "judge", "reviewer", "publisher", "validator", "participant", "facilitator", "observer"}:
            result.append(_finding("climb.invalid-authority", authority.authority_id, authority.role, "authority role is unsupported"))
        if authority.role in {"reviewer", "publisher", "participant", "facilitator", "observer"} and authority.kind != "human":
            result.append(_finding("climb.human-authority-required", authority.authority_id, authority.kind, "review, publication, and human-play authority must be human"))

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
        occupants = task.occupant_authority_ids
        if len(occupants) != len(set(occupants)):
            result.append(_finding("climb.duplicate-task-occupant", task.task_id, str(occupants), "Task occupants must be distinct"))
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
        for occupant_id in occupants:
            occupant = authority_by_id.get(occupant_id)
            if occupant is None:
                result.append(_finding("climb.dangling-reference", task.task_id, occupant_id, "Task names a missing participant Authority"))
            elif occupant.role not in expected_roles:
                result.append(_finding("climb.role-mismatch", task.task_id, occupant.role, "Task participant has an incompatible role"))
            if occupant_id in task.excluded_authority_ids:
                result.append(_finding("climb.excluded-authority", task.task_id, occupant_id, "Task occupant is explicitly excluded"))
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
        if receipt.evidence_class is not None and receipt.evidence_class not in {
            "live-model",
            "recorded-model",
            "capability-fixture",
        }:
            result.append(_finding("climb.invalid-evidence-class", receipt.receipt_id, receipt.evidence_class, "Model Receipt evidence class is unsupported"))
        for label, value in {
            **receipt.input_hashes,
            **{f"tool_receipt_{index}": item for index, item in enumerate(receipt.tool_receipt_hashes)},
        }.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.incomplete-model-receipt", receipt.receipt_id, f"{label}={value}", "Model Receipt input and tool receipts require exact SHA-256 identities"))
        replay_core = (receipt.prompt_ref, receipt.context_ref, receipt.tool_contract_ref)
        if any(item is not None for item in replay_core) or receipt.input_refs:
            if any(item is None for item in replay_core):
                result.append(_finding("climb.incomplete-replay-envelope", receipt.receipt_id, str(replay_core), "Replayable Model Receipt requires prompt, context, and tool contract objects"))
            for label, claimed, replay_ref in (
                ("prompt", receipt.prompt_hash, receipt.prompt_ref),
                ("context", receipt.context_hash, receipt.context_ref),
                ("tool_contract", receipt.tool_contract_hash, receipt.tool_contract_ref),
            ):
                if replay_ref is not None and (not _HASH.fullmatch(replay_ref) or replay_ref != claimed):
                    result.append(_finding("climb.replay-hash-mismatch", receipt.receipt_id, f"{label}={replay_ref}", "Replay object must exactly match the Model Receipt hash"))
            for key, replay_ref in receipt.input_refs.items():
                if not _HASH.fullmatch(replay_ref) or receipt.input_hashes.get(key) != replay_ref:
                    result.append(_finding("climb.replay-hash-mismatch", receipt.receipt_id, f"{key}={replay_ref}", "Replay input object must exactly match its Model Receipt hash"))

    for receipt in human_receipts:
        authority = authority_by_id.get(receipt.authority_id)
        task = task_by_id.get(receipt.task_id)
        if authority is None or authority.kind != "human" or authority.role != "judge":
            result.append(
                _finding(
                    "climb.human-observation-authority-mismatch",
                    receipt.receipt_id,
                    receipt.authority_id,
                    "Human Receipt requires a human judge Authority",
                )
            )
        if task is None or receipt.authority_id not in task.occupant_authority_ids:
            result.append(
                _finding(
                    "climb.human-observation-task-mismatch",
                    receipt.receipt_id,
                    receipt.task_id,
                    "Human Receipt must occupy its named Task",
                )
            )
        if receipt.evidence_class not in {"fresh-human", "recorded-human"}:
            result.append(
                _finding(
                    "climb.invalid-evidence-class",
                    receipt.receipt_id,
                    receipt.evidence_class,
                    "Human Receipt evidence class is unsupported",
                )
            )
        for label, value in {**receipt.input_refs, "response": receipt.response_ref}.items():
            if not _HASH.fullmatch(value):
                result.append(
                    _finding(
                        "climb.incomplete-human-receipt",
                        receipt.receipt_id,
                        f"{label}={value}",
                        "Human Receipt requires exact input and response object references",
                    )
                )

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
            if set(evaluation.judge_authority_ids) != set(task.occupant_authority_ids):
                result.append(_finding("climb.incomplete-blind-panel", evaluation.evaluation_id, str(evaluation.judge_authority_ids), "Blind Evaluation judges must exactly match the frozen Task occupants"))
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
        missing_human_receipts = [
            item for item in evaluation.human_receipt_ids if item not in human_receipt_by_id
        ]
        if missing_human_receipts:
            result.append(
                _finding(
                    "climb.dangling-reference",
                    evaluation.evaluation_id,
                    ", ".join(missing_human_receipts),
                    "Evaluation names missing Human Receipts",
                )
            )
        if evaluation.mode == "blind" and not missing_receipts and not missing_human_receipts:
            receipt_authorities = {
                receipt_by_id[item].authority_id for item in evaluation.model_receipt_ids
            }
            receipt_authorities.update(
                human_receipt_by_id[item].authority_id
                for item in evaluation.human_receipt_ids
            )
            if receipt_authorities != set(evaluation.judge_authority_ids):
                result.append(_finding("climb.judge-receipt-mismatch", evaluation.evaluation_id, str(sorted(receipt_authorities)), "Blind Evaluation model and human receipts must exactly cover its named judges"))
        if set(evaluation.hard_gate_results) != set(instrument.hard_gate_codes):
            result.append(_finding("climb.incomplete-hard-gates", evaluation.evaluation_id, str(dict(evaluation.hard_gate_results)), "Evaluation must replay every frozen hard gate"))
        if evaluation.outcome == "pass" and not all(evaluation.hard_gate_results.values()):
            result.append(_finding("climb.hard-gate-regression", evaluation.evaluation_id, str(dict(evaluation.hard_gate_results)), "Evaluation cannot pass while a hard gate regresses"))
        if evaluation.mode == "blind":
            try:
                expected_outcome = "pass" if evaluation_passes(instrument, evaluation) else "fail"
            except ValueError as exc:
                result.append(_finding("climb.invalid-instrument", instrument.instrument_id, str(instrument.acceptance_rules), str(exc)))
            else:
                if evaluation.outcome != expected_outcome:
                    result.append(_finding("climb.invalid-evaluation-outcome", evaluation.evaluation_id, evaluation.outcome, "Evaluation outcome differs from the frozen acceptance rules"))

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

    for protocol in playtest_protocols:
        binding = binding_by_id.get(protocol.binding_id)
        if binding is None:
            result.append(_finding("climb.dangling-reference", protocol.protocol_id, protocol.binding_id, "Playtest Protocol names a missing Trial Binding"))
        if protocol.instrument_id not in instrument_by_id:
            result.append(_finding("climb.dangling-reference", protocol.protocol_id, protocol.instrument_id, "Playtest Protocol names a missing Frozen Instrument"))
        if (
            not protocol.name.strip()
            or not protocol.version.strip()
            or not protocol.consent_version.strip()
            or protocol.minimum_fresh_runs < 2
            or protocol.minimum_participants_per_run < 1
            or protocol.model_human_delta_tolerance < 0
        ):
            result.append(_finding("climb.invalid-playtest-protocol", protocol.protocol_id, str(protocol.to_mapping()), "Playtest Protocol requires identity, versioned consent, at least two fresh runs, participants, and a nonnegative comparison tolerance"))
        categories = protocol.required_observation_categories
        if not categories or len(categories) != len(set(categories)) or any(not item.strip() for item in categories):
            result.append(_finding("climb.invalid-playtest-protocol", protocol.protocol_id, str(categories), "Playtest Protocol requires unique observation categories"))
        for label, values in (
            ("response stages", protocol.required_response_stages),
            ("individual response stages", protocol.individual_response_stages),
            ("defect owners", protocol.defect_owner_taxonomy),
        ):
            if len(values) != len(set(values)) or any(not item.strip() for item in values):
                result.append(_finding("climb.invalid-playtest-protocol", protocol.protocol_id, str(values), f"Playtest Protocol requires unique {label}"))
        if not set(protocol.individual_response_stages) <= set(protocol.required_response_stages):
            result.append(_finding("climb.invalid-playtest-protocol", protocol.protocol_id, str(protocol.individual_response_stages), "individual response stages must be frozen response stages"))

    for protocol in playtest_protocols:
        protocol_runs = [item for item in playtest_runs if item.protocol_id == protocol.protocol_id]
        run_keys = [item.run_key for item in protocol_runs]
        if len(run_keys) != len(set(run_keys)):
            result.append(_finding("climb.duplicate-playtest-run", protocol.protocol_id, str(run_keys), "one Playtest Protocol cannot reuse a run key"))
        session_refs = [item.session_history_ref for item in protocol_runs]
        if len(session_refs) != len(set(session_refs)):
            result.append(_finding("climb.reused-play-session", protocol.protocol_id, str(session_refs), "fresh Playtest Runs require distinct live Session histories"))
        cohorts = [
            tuple(
                sorted(
                    authority_by_id[item].principal
                    for item in run.participant_authority_ids
                    if item in authority_by_id
                )
            )
            for run in protocol_runs
        ]
        if len(cohorts) != len(set(cohorts)):
            result.append(_finding("climb.reused-playtest-cohort", protocol.protocol_id, str(cohorts), "fresh Playtest Runs require distinct participant cohorts"))

    for run in playtest_runs:
        protocol = protocol_by_id.get(run.protocol_id)
        if protocol is None:
            result.append(_finding("climb.dangling-reference", run.run_id, run.protocol_id, "Playtest Run names a missing Protocol"))
            continue
        binding = binding_by_id.get(protocol.binding_id)
        instrument = instrument_by_id.get(protocol.instrument_id)
        if binding is None or instrument is None:
            continue
        if run.release_id != binding.release_id or run.physical_export_id != binding.physical_export_id:
            result.append(_finding("climb.playtest-package-mismatch", run.run_id, f"{run.release_id}; {run.physical_export_id}", "Playtest Run differs from the Protocol's exact Release or Physical Export"))
        for label, ref in {
            "session_history_ref": run.session_history_ref,
            "production_receipt_ref": run.production_receipt_ref,
        }.items():
            if not _HASH.fullmatch(ref):
                result.append(_finding("climb.invalid-object-reference", run.run_id, f"{label}={ref}", "Playtest Run requires exact Session and production objects"))
        roster = (
            *run.participant_authority_ids,
            run.facilitator_authority_id,
            *run.observer_authority_ids,
        )
        if len(roster) != len(set(roster)):
            result.append(_finding("climb.duplicate-playtest-role", run.run_id, str(roster), "one human cannot occupy multiple roles in one Playtest Run"))
        if len(run.participant_authority_ids) < protocol.minimum_participants_per_run:
            result.append(_finding("climb.incomplete-playtest-cast", run.run_id, str(run.participant_authority_ids), "Playtest Run does not meet the frozen participant minimum"))
        expected_roles = {
            **{item: "participant" for item in run.participant_authority_ids},
            run.facilitator_authority_id: "facilitator",
            **{item: "observer" for item in run.observer_authority_ids},
        }
        for authority_id, expected_role in expected_roles.items():
            authority = authority_by_id.get(authority_id)
            if authority is None or authority.kind != "human" or authority.role != expected_role:
                result.append(_finding("climb.playtest-role-mismatch", run.run_id, f"{authority_id}:{expected_role}", "Playtest roster requires exact human participant, facilitator, and observer Authorities"))
        consent_by_authority = {item.authority_id: item for item in run.consents}
        if set(consent_by_authority) != set(roster):
            result.append(_finding("climb.incomplete-playtest-consent", run.run_id, str(sorted(consent_by_authority)), "every human in a Playtest Run requires one exact consent receipt"))
        for authority_id, consent in consent_by_authority.items():
            required_scopes = {"record-observations", "retain-anonymized-quotes"}
            if expected_roles.get(authority_id) == "participant":
                required_scopes.add("participate")
            if consent.consent_version != protocol.consent_version or not required_scopes <= set(consent.scopes) or not _HASH.fullmatch(consent.response_ref):
                result.append(_finding("climb.incomplete-playtest-consent", run.run_id, authority_id, "consent must match the frozen version, required scopes, and exact response object"))
        observed_categories = {item.category for item in run.observations}
        if not set(protocol.required_observation_categories) <= observed_categories:
            result.append(_finding("climb.incomplete-playtest-observation", run.run_id, str(sorted(observed_categories)), "Playtest Run must cover every frozen observation category"))
        observed_stages = {item.response_stage for item in run.observations}
        if not set(protocol.required_response_stages) <= observed_stages:
            result.append(_finding("climb.incomplete-playtest-observation", run.run_id, str(sorted(observed_stages)), "Playtest Run must cover every frozen response stage"))
        for participant_id in run.participant_authority_ids:
            participant_stages = {item.response_stage for item in run.observations if item.authority_id == participant_id}
            if not set(protocol.individual_response_stages) <= participant_stages:
                result.append(_finding("climb.incomplete-playtest-observation", run.run_id, participant_id, "participant lacks a frozen individual response stage"))
        for observation in run.observations:
            authority = authority_by_id.get(observation.authority_id)
            if observation.authority_id not in roster or authority is None or observation.observer_role != authority.role:
                result.append(_finding("climb.playtest-observer-mismatch", run.run_id, observation.authority_id, "Play Observation must come from a human occupying its declared Run role"))
            if observation.category not in protocol.required_observation_categories or not observation.phase_id.strip() or not observation.quote.strip() or not observation.note.strip() or not _HASH.fullmatch(observation.response_ref):
                result.append(_finding("climb.invalid-playtest-observation", run.run_id, observation.quote, "Play Observation requires a frozen category, Phase, exact quote, note, and response object"))
            if observation.response_stage not in (protocol.required_response_stages or ("in_play",)) or (observation.elapsed_seconds is not None and observation.elapsed_seconds < 0) or (protocol.required_response_stages and not observation.instrument_item_id.strip()):
                result.append(_finding("climb.invalid-playtest-observation", run.run_id, observation.quote, "Play Observation requires a frozen response stage, nonnegative optional timestamp, and rubric item"))
            if observation.defect_owner is not None and observation.defect_owner not in protocol.defect_owner_taxonomy:
                result.append(_finding("climb.invalid-playtest-observation", run.run_id, observation.defect_owner, "Play Observation defect owner is outside the frozen taxonomy"))
        if set(run.scores) != {item.dimension_id for item in instrument.dimensions} or any(not 0 <= item <= 100 for item in run.scores.values()):
            result.append(_finding("climb.invalid-score", run.run_id, str(dict(run.scores)), "Playtest scores must cover every frozen dimension from 0 to 100"))
        if set(run.hard_gate_results) != set(instrument.hard_gate_codes):
            result.append(_finding("climb.incomplete-hard-gates", run.run_id, str(dict(run.hard_gate_results)), "Playtest Run must replay every frozen hard gate"))
        if run.evidence_class != "fresh-human-play":
            result.append(_finding("climb.invalid-evidence-class", run.run_id, run.evidence_class, "Playtest Run must be first-order fresh-human-play evidence"))
        missing_findings = [item for item in run.finding_ids if item not in finding_by_id]
        if missing_findings:
            result.append(_finding("climb.dangling-reference", run.run_id, str(missing_findings), "Playtest Run names missing Findings"))
        if set(run.scores) == {item.dimension_id for item in instrument.dimensions} and set(run.hard_gate_results) == set(instrument.hard_gate_codes):
            candidate_id = binding.candidate_id
            synthetic = Evaluation("playtest", candidate_id, instrument.instrument_id, "blind", (), (), run.scores, (), run.hard_gate_results, run.outcome)
            try:
                expected = "pass" if evaluation_passes(instrument, synthetic) else "fail"
            except ValueError as exc:
                result.append(_finding("climb.invalid-instrument", instrument.instrument_id, str(instrument.acceptance_rules), str(exc)))
            else:
                if run.outcome != expected:
                    result.append(_finding("climb.invalid-playtest-outcome", run.run_id, run.outcome, "Playtest outcome differs from the frozen Instrument"))

    for comparison in evidence_comparisons:
        protocol = protocol_by_id.get(comparison.protocol_id)
        evaluation = evaluation_by_id.get(comparison.model_evaluation_id)
        runs = [playtest_run_by_id.get(item) for item in comparison.playtest_run_ids]
        if protocol is None or evaluation is None or not runs or any(item is None for item in runs):
            result.append(_finding("climb.dangling-reference", comparison.comparison_id, f"{comparison.protocol_id}; {comparison.model_evaluation_id}; {comparison.playtest_run_ids}", "Evidence Comparison names missing Protocol, model Evaluation, or Playtest Run"))
            continue
        binding = binding_by_id.get(protocol.binding_id)
        task = task_by_id.get(evaluation.task_id)
        complete_runs = [item for item in runs if item is not None]
        if binding is None or task is None or task.input_refs.get("blind_trial") != binding.blind_trial_ref or evaluation.candidate_id != binding.candidate_id or comparison.candidate_id != binding.candidate_id or comparison.instrument_id != protocol.instrument_id or evaluation.instrument_id != protocol.instrument_id or evaluation.mode != "blind" or not evaluation.model_receipt_ids:
            result.append(_finding("climb.comparison-input-mismatch", comparison.comparison_id, comparison.candidate_id, "Evidence Comparison requires blind model evidence and human Runs for the same Candidate and Instrument"))
        if any(item.protocol_id != protocol.protocol_id for item in complete_runs):
            result.append(_finding("climb.comparison-input-mismatch", comparison.comparison_id, str(comparison.playtest_run_ids), "Evidence Comparison mixes Playtest Protocols"))
        expected_dimensions = {}
        for dimension in instrument_by_id[protocol.instrument_id].dimensions:
            human_median = median(item.scores[dimension.dimension_id] for item in complete_runs)
            model_score = evaluation.scores[dimension.dimension_id]
            expected_dimensions[dimension.dimension_id] = {
                "model": model_score,
                "human_median": human_median,
                "delta": human_median - model_score,
            }
        expected_conclusion = "divergent" if any(abs(item["delta"]) > protocol.model_human_delta_tolerance for item in expected_dimensions.values()) else "aligned"
        if comparison.dimensions != expected_dimensions or comparison.conclusion != expected_conclusion:
            result.append(_finding("climb.invalid-evidence-comparison", comparison.comparison_id, str(dict(comparison.dimensions)), "Evidence Comparison differs from deterministic model-versus-human aggregation"))

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
            required = {"fresh-human-play", "independent-standing-review", "model-human-comparison"}
            if not required <= set(standing.evidence_kinds):
                result.append(_finding("climb.unsupported-standing", standing.attestation_id, str(standing.evidence_kinds), "Accepted standing requires fresh human play, model comparison, and independent review"))
            linked_runs = [playtest_run_by_id.get(item) for item in standing.playtest_run_ids]
            comparison = comparison_by_id.get(standing.comparison_id or "")
            if not standing.playtest_run_ids or any(item is None for item in linked_runs):
                result.append(_finding("climb.unsupported-standing", standing.attestation_id, str(standing.playtest_run_ids), "Accepted standing must link exact Playtest Runs"))
            else:
                complete_runs = [item for item in linked_runs if item is not None]
                protocols = {item.protocol_id for item in complete_runs}
                protocol = protocol_by_id.get(next(iter(protocols))) if len(protocols) == 1 else None
                if protocol is None or len(complete_runs) < protocol.minimum_fresh_runs or any(item.outcome != "pass" for item in complete_runs):
                    result.append(_finding("climb.unsupported-standing", standing.attestation_id, str(standing.playtest_run_ids), "Accepted standing requires the frozen number of passing fresh Runs under one Protocol"))
                roster = {authority_id for item in complete_runs for authority_id in (*item.participant_authority_ids, item.facilitator_authority_id, *item.observer_authority_ids)}
                if standing.reviewer_authority_id in roster:
                    result.append(_finding("climb.nonindependent-standing-review", standing.attestation_id, standing.reviewer_authority_id, "Standing reviewer cannot participate in, facilitate, or observe a supporting Run"))
                if protocol is not None and protocol.require_model_comparison:
                    if comparison is None or set(comparison.playtest_run_ids) != set(standing.playtest_run_ids) or comparison.protocol_id != protocol.protocol_id or comparison.model_evaluation_id not in standing.evaluation_ids:
                        result.append(_finding("climb.unsupported-standing", standing.attestation_id, str(standing.comparison_id), "Accepted standing requires the exact persisted model-versus-human comparison"))

    for binding in trial_bindings:
        for label, value in {
            "candidate_id": binding.candidate_id,
            "release_id": binding.release_id,
            "release_bundle_ref": binding.release_bundle_ref,
            "physical_export_id": binding.physical_export_id,
            "physical_archive_ref": binding.physical_archive_ref,
            "blind_trial_id": binding.blind_trial_id,
            "blind_trial_ref": binding.blind_trial_ref,
        }.items():
            if not _HASH.fullmatch(value):
                result.append(_finding("climb.invalid-object-reference", binding.binding_id, f"{label}={value}", "Trial Binding requires exact content identities"))
        if not binding.hard_gate_results or not all(binding.hard_gate_results.values()):
            result.append(_finding("climb.incomplete-trial-package", binding.binding_id, str(dict(binding.hard_gate_results)), "Trial Binding requires a verified Release, Physical Export, Blind Trial, and frozen hard gates"))

    for selection in selections:
        instrument = instrument_by_id.get(selection.instrument_id)
        baseline = evaluation_by_id.get(selection.baseline_evaluation_id)
        child = evaluation_by_id.get(selection.child_evaluation_id)
        if instrument is None or baseline is None or child is None:
            result.append(_finding("climb.dangling-reference", selection.decision_id, f"{selection.instrument_id}; {selection.baseline_evaluation_id}; {selection.child_evaluation_id}", "Selection Decision names missing evidence"))
            continue
        if baseline.instrument_id != instrument.instrument_id or child.instrument_id != instrument.instrument_id:
            result.append(_finding("climb.selection-instrument-mismatch", selection.decision_id, instrument.instrument_id, "Selection Evaluations do not share the frozen Instrument"))
            continue
        baseline_score = baseline.overall_score(instrument)
        child_score = child.overall_score(instrument)
        child_receipts = [receipt_by_id.get(item) for item in child.model_receipt_ids]
        child_receipts.extend(human_receipt_by_id.get(item) for item in child.human_receipt_ids)
        baseline_receipts = [receipt_by_id.get(item) for item in baseline.model_receipt_ids]
        baseline_receipts.extend(
            human_receipt_by_id.get(item) for item in baseline.human_receipt_ids
        )
        allowed_classes = set(instrument.blind_protocol.get("selection_evidence_classes", ()))
        receipt_classes = {
            item.evidence_class
            for item in (*baseline_receipts, *child_receipts)
            if item is not None
        }
        evidence_ok = bool(allowed_classes) and bool(receipt_classes) and receipt_classes <= allowed_classes
        child_wins = (
            baseline_score is not None
            and child_score is not None
            and child_score > baseline_score
            and evaluation_passes(instrument, child)
            and evidence_ok
        )
        expected_outcome = "select_child" if child_wins else "retain_baseline"
        expected_candidate = child.candidate_id if child_wins else baseline.candidate_id
        if selection.outcome != expected_outcome or selection.selected_candidate_id != expected_candidate:
            result.append(_finding("climb.unsupported-selection", selection.decision_id, f"{selection.outcome}:{selection.selected_candidate_id}", "Selection differs from frozen scores, hard gates, or admissible evidence classes"))

    return tuple(sorted(set(result)))
