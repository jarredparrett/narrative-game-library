"""Immutable values for one native agentic hill-climb lineage."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _identified(kind: str, material: Mapping[str, Any]) -> str:
    return f"{kind}:{digest_json(material).removeprefix('sha256:')}"


@dataclass(frozen=True)
class ExperimentPlan:
    experiment_id: str
    profile_id: str
    profile_version: str
    instrument_id: str
    branch: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.8",
            "experiment_id": self.experiment_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "instrument_id": self.instrument_id,
            "branch": self.branch,
        }

    @property
    def plan_id(self) -> str:
        return _identified("experiment-plan", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, **self.material()}


@dataclass(frozen=True)
class Authority:
    authority_id: str
    kind: str
    role: str
    principal: str

    def to_mapping(self) -> dict[str, str]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class Dimension:
    dimension_id: str
    description: str
    weight: int
    anchors: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "anchors", _copy(self.anchors))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "description": self.description,
            "weight": self.weight,
            "anchors": dict(self.anchors),
        }


@dataclass(frozen=True)
class FrozenInstrument:
    name: str
    version: str
    scope: str
    dimensions: tuple[Dimension, ...]
    acceptance_rules: tuple[Mapping[str, Any], ...]
    blind_protocol: Mapping[str, Any]
    hard_gate_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "acceptance_rules",
            tuple(_copy(item) for item in self.acceptance_rules),
        )
        object.__setattr__(self, "blind_protocol", _copy(self.blind_protocol))

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "name": self.name,
            "version": self.version,
            "scope": self.scope,
            "dimensions": [item.to_mapping() for item in self.dimensions],
            "acceptance_rules": [dict(item) for item in self.acceptance_rules],
            "blind_protocol": dict(self.blind_protocol),
            "hard_gate_codes": list(self.hard_gate_codes),
        }

    @property
    def instrument_id(self) -> str:
        return _identified("instrument", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"instrument_id": self.instrument_id, **self.material()}


@dataclass(frozen=True)
class Task:
    task_key: str
    kind: str
    candidate_id: str
    instrument_id: str
    assigned_authority_id: str
    excluded_authority_ids: tuple[str, ...]
    input_refs: Mapping[str, str]
    instructions: str
    participant_authority_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_refs", _copy(self.input_refs))

    def material(self) -> dict[str, Any]:
        result = {
            "schema_version": "0.6",
            "task_key": self.task_key,
            "kind": self.kind,
            "candidate_id": self.candidate_id,
            "instrument_id": self.instrument_id,
            "assigned_authority_id": self.assigned_authority_id,
            "excluded_authority_ids": list(self.excluded_authority_ids),
            "input_refs": dict(self.input_refs),
            "instructions": self.instructions,
        }
        if self.participant_authority_ids:
            result["participant_authority_ids"] = list(self.participant_authority_ids)
        return result

    @property
    def occupant_authority_ids(self) -> tuple[str, ...]:
        """Return every agent explicitly authorized to occupy this Task."""
        return (self.assigned_authority_id, *self.participant_authority_ids)

    @property
    def task_id(self) -> str:
        return _identified("task", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"task_id": self.task_id, **self.material()}


@dataclass(frozen=True)
class ModelReceipt:
    authority_id: str
    provider: str
    requested_model: str
    resolved_model: str
    role: str
    prompt_hash: str
    context_hash: str
    tool_contract_hash: str
    input_hashes: Mapping[str, str]
    tool_receipt_hashes: tuple[str, ...]
    raw_output_ref: str
    parsed_output_ref: str
    seed: int | None
    prompt_ref: str | None = None
    context_ref: str | None = None
    tool_contract_ref: str | None = None
    input_refs: Mapping[str, str] | None = None
    evidence_class: str | None = None
    usage: Mapping[str, int] | None = None
    agent_id: str | None = None
    context_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_hashes", _copy(self.input_hashes))
        object.__setattr__(self, "input_refs", _copy(self.input_refs or {}))
        object.__setattr__(self, "usage", _copy(self.usage or {}))
        if (self.agent_id is None) != (self.context_id is None):
            raise ValueError("model execution identity requires agent_id and context_id")
        if self.agent_id is not None and (
            not self.agent_id.strip() or not self.context_id or not self.context_id.strip()
        ):
            raise ValueError("model execution identity values must be non-empty")

    def material(self) -> dict[str, Any]:
        result = {
            "schema_version": "0.6",
            "authority_id": self.authority_id,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "resolved_model": self.resolved_model,
            "role": self.role,
            "prompt_hash": self.prompt_hash,
            "context_hash": self.context_hash,
            "tool_contract_hash": self.tool_contract_hash,
            "input_hashes": dict(self.input_hashes),
            "tool_receipt_hashes": list(self.tool_receipt_hashes),
            "raw_output_ref": self.raw_output_ref,
            "parsed_output_ref": self.parsed_output_ref,
            "seed": self.seed,
        }
        if any(
            item is not None
            for item in (self.prompt_ref, self.context_ref, self.tool_contract_ref)
        ) or self.input_refs:
            result["replay"] = {
                "prompt_ref": self.prompt_ref,
                "context_ref": self.context_ref,
                "tool_contract_ref": self.tool_contract_ref,
                "input_refs": dict(self.input_refs or {}),
            }
        if self.evidence_class is not None:
            result["evidence_class"] = self.evidence_class
        if self.usage:
            result["usage"] = dict(self.usage)
        if self.agent_id is not None or self.context_id is not None:
            result["execution_identity"] = {
                "agent_id": self.agent_id,
                "context_id": self.context_id,
            }
        return result

    @property
    def receipt_id(self) -> str:
        return _identified("model-receipt", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.material()}


@dataclass(frozen=True)
class HumanReceipt:
    authority_id: str
    task_id: str
    input_refs: Mapping[str, str]
    response_ref: str
    evidence_class: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_refs", _copy(self.input_refs))

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.8",
            "authority_id": self.authority_id,
            "task_id": self.task_id,
            "input_refs": dict(self.input_refs),
            "response_ref": self.response_ref,
            "evidence_class": self.evidence_class,
        }

    @property
    def receipt_id(self) -> str:
        return _identified("human-receipt", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"receipt_id": self.receipt_id, **self.material()}


@dataclass(frozen=True)
class Exposure:
    authority_id: str
    object_ref: str
    category: str
    purpose: str
    before_task_id: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "authority_id": self.authority_id,
            "object_ref": self.object_ref,
            "category": self.category,
            "purpose": self.purpose,
            "before_task_id": self.before_task_id,
        }

    @property
    def exposure_id(self) -> str:
        return _identified("exposure", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"exposure_id": self.exposure_id, **self.material()}


@dataclass(frozen=True)
class Finding:
    requirement_code: str
    severity: str
    resource_path: str
    locus: str
    quote: str
    message: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "requirement_code": self.requirement_code,
            "severity": self.severity,
            "resource_path": self.resource_path,
            "locus": self.locus,
            "quote": self.quote,
            "message": self.message,
        }

    @property
    def finding_id(self) -> str:
        return _identified("finding", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"finding_id": self.finding_id, **self.material()}


@dataclass(frozen=True)
class Requirement:
    requirement_code: str
    property: str
    failure: str
    builder_brief: str
    source_finding_ids: tuple[str, ...]

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "requirement_code": self.requirement_code,
            "property": self.property,
            "failure": self.failure,
            "builder_brief": self.builder_brief,
            "source_finding_ids": list(self.source_finding_ids),
        }

    @property
    def requirement_id(self) -> str:
        return _identified("requirement", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"requirement_id": self.requirement_id, **self.material()}


@dataclass(frozen=True)
class Evaluation:
    task_id: str
    candidate_id: str
    instrument_id: str
    mode: str
    judge_authority_ids: tuple[str, ...]
    model_receipt_ids: tuple[str, ...]
    scores: Mapping[str, int]
    finding_ids: tuple[str, ...]
    hard_gate_results: Mapping[str, bool]
    outcome: str
    claimed_standing: str | None = None
    human_receipt_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "scores", _copy(self.scores))
        object.__setattr__(self, "hard_gate_results", _copy(self.hard_gate_results))

    def material(self) -> dict[str, Any]:
        result = {
            "schema_version": "0.8" if self.human_receipt_ids else "0.6",
            "task_id": self.task_id,
            "candidate_id": self.candidate_id,
            "instrument_id": self.instrument_id,
            "mode": self.mode,
            "judge_authority_ids": list(self.judge_authority_ids),
            "model_receipt_ids": list(self.model_receipt_ids),
            "scores": dict(self.scores),
            "finding_ids": list(self.finding_ids),
            "hard_gate_results": dict(self.hard_gate_results),
            "outcome": self.outcome,
            "claimed_standing": self.claimed_standing,
        }
        if self.human_receipt_ids:
            result["human_receipt_ids"] = list(self.human_receipt_ids)
        return result

    @property
    def evaluation_id(self) -> str:
        return _identified("evaluation", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"evaluation_id": self.evaluation_id, **self.material()}

    def overall_score(self, instrument: FrozenInstrument) -> float | None:
        if not self.scores:
            return None
        total_weight = sum(item.weight for item in instrument.dimensions)
        weighted = sum(self.scores[item.dimension_id] * item.weight for item in instrument.dimensions)
        return weighted / total_weight


@dataclass(frozen=True)
class Proposal:
    task_id: str
    baseline_draft_ref: str
    proposed_data_ref: str
    requirement_ids: tuple[str, ...]
    builder_authority_id: str
    model_receipt_id: str
    rationale: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "task_id": self.task_id,
            "baseline_draft_ref": self.baseline_draft_ref,
            "proposed_data_ref": self.proposed_data_ref,
            "requirement_ids": list(self.requirement_ids),
            "builder_authority_id": self.builder_authority_id,
            "model_receipt_id": self.model_receipt_id,
            "rationale": self.rationale,
        }

    @property
    def proposal_id(self) -> str:
        return _identified("proposal", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"proposal_id": self.proposal_id, **self.material()}


@dataclass(frozen=True)
class HumanReview:
    proposal_id: str
    reviewer_authority_id: str
    decision: str
    reason: str
    approved_requirement_ids: tuple[str, ...]

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "proposal_id": self.proposal_id,
            "reviewer_authority_id": self.reviewer_authority_id,
            "decision": self.decision,
            "reason": self.reason,
            "approved_requirement_ids": list(self.approved_requirement_ids),
        }

    @property
    def review_id(self) -> str:
        return _identified("human-review", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"review_id": self.review_id, **self.material()}


@dataclass(frozen=True)
class AgentReview:
    proposal_id: str
    reviewer_authority_id: str
    model_receipt_id: str
    decision: str
    reason: str
    approved_requirement_ids: tuple[str, ...]

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.18",
            "proposal_id": self.proposal_id,
            "reviewer_authority_id": self.reviewer_authority_id,
            "model_receipt_id": self.model_receipt_id,
            "decision": self.decision,
            "reason": self.reason,
            "approved_requirement_ids": list(self.approved_requirement_ids),
        }

    @property
    def review_id(self) -> str:
        return _identified("agent-review", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"review_id": self.review_id, **self.material()}


@dataclass(frozen=True)
class Transition:
    proposal_id: str
    review_id: str
    reviewer_authority_id: str
    branch: str
    parent_draft_ref: str
    proposed_data_ref: str
    child_draft_ref: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.6",
            "proposal_id": self.proposal_id,
            "review_id": self.review_id,
            "reviewer_authority_id": self.reviewer_authority_id,
            "branch": self.branch,
            "parent_draft_ref": self.parent_draft_ref,
            "proposed_data_ref": self.proposed_data_ref,
            "child_draft_ref": self.child_draft_ref,
        }

    @property
    def transition_id(self) -> str:
        return _identified("transition", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"transition_id": self.transition_id, **self.material()}


@dataclass(frozen=True)
class StandingAttestation:
    candidate_id: str
    level: str
    evaluation_ids: tuple[str, ...]
    evidence_kinds: tuple[str, ...]
    reviewer_authority_id: str
    statement: str
    playtest_run_ids: tuple[str, ...] = ()
    comparison_id: str | None = None

    def material(self) -> dict[str, Any]:
        result = {
            "schema_version": "0.10" if self.playtest_run_ids else "0.6",
            "candidate_id": self.candidate_id,
            "level": self.level,
            "evaluation_ids": list(self.evaluation_ids),
            "evidence_kinds": list(self.evidence_kinds),
            "reviewer_authority_id": self.reviewer_authority_id,
            "statement": self.statement,
        }
        if self.playtest_run_ids:
            result["playtest_run_ids"] = list(self.playtest_run_ids)
            result["comparison_id"] = self.comparison_id
        return result

    @property
    def attestation_id(self) -> str:
        return _identified("standing", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"attestation_id": self.attestation_id, **self.material()}


@dataclass(frozen=True)
class TrialBinding:
    candidate_id: str
    release_id: str
    release_bundle_ref: str
    physical_export_id: str
    physical_archive_ref: str
    blind_trial_id: str
    blind_trial_ref: str
    hard_gate_results: Mapping[str, bool]

    def __post_init__(self) -> None:
        object.__setattr__(self, "hard_gate_results", _copy(self.hard_gate_results))

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.7",
            "candidate_id": self.candidate_id,
            "release_id": self.release_id,
            "release_bundle_ref": self.release_bundle_ref,
            "physical_export_id": self.physical_export_id,
            "physical_archive_ref": self.physical_archive_ref,
            "blind_trial_id": self.blind_trial_id,
            "blind_trial_ref": self.blind_trial_ref,
            "hard_gate_results": dict(self.hard_gate_results),
        }

    @property
    def binding_id(self) -> str:
        return _identified("trial-binding", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.material()}


@dataclass(frozen=True)
class SelectionDecision:
    instrument_id: str
    baseline_evaluation_id: str
    child_evaluation_id: str
    outcome: str
    selected_candidate_id: str
    reason: str

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.7",
            "instrument_id": self.instrument_id,
            "baseline_evaluation_id": self.baseline_evaluation_id,
            "child_evaluation_id": self.child_evaluation_id,
            "outcome": self.outcome,
            "selected_candidate_id": self.selected_candidate_id,
            "reason": self.reason,
        }

    @property
    def decision_id(self) -> str:
        return _identified("selection", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"decision_id": self.decision_id, **self.material()}
