"""Isolated causal hypotheses, counterfactual plans, and owning-layer review."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from narrative_game.contracts.canonical import digest_json


CAUSAL_LAYERS = ("actor", "interaction", "seat", "host", "game", "runtime", "provider", "evaluator")
CAUSAL_ROLES = ("necessary", "sufficient", "contributing", "amplifying", "recovery", "confounding")
COUNTERFACTUAL_FACTORS = (
    "policy-occupancy",
    "seat-or-role-design",
    "host-policy",
    "culprit-behavior",
    "proof-path-or-evidence-availability",
    "communication-condition",
    "game-affordance-responsibility-or-reveal-policy",
    "runtime-or-provider",
    "evaluator-or-analysis-instrument",
)


@dataclass(frozen=True)
class CausalFactor:
    factor_id: str
    layer: str
    causal_role: str
    evidence_refs: tuple[str, ...]
    counterevidence_refs: tuple[str, ...]
    alternatives: tuple[str, ...]
    confidence_band: str
    prediction: str

    def __post_init__(self) -> None:
        if self.layer not in CAUSAL_LAYERS or self.causal_role not in CAUSAL_ROLES:
            raise ValueError("Causal factor has an unregistered layer or role")
        if not self.evidence_refs or not self.prediction:
            raise ValueError("Causal factor requires evidence and a falsifiable prediction")
        if self.confidence_band not in {"low", "medium", "high"}:
            raise ValueError("Causal confidence must be a band")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "factor_id": self.factor_id,
            "layer": self.layer,
            "causal_role": self.causal_role,
            "evidence_refs": list(self.evidence_refs),
            "counterevidence_refs": list(self.counterevidence_refs),
            "alternatives": list(self.alternatives),
            "confidence_band": self.confidence_band,
            "prediction": self.prediction,
        }


@dataclass(frozen=True)
class CausalHypothesisSet:
    incident_ref: str
    principal: str
    factors: tuple[CausalFactor, ...]
    interactions: tuple[tuple[str, ...], ...]
    material_alternatives: tuple[str, ...]
    overall_uncertainty: str
    analysis_receipt_ref: str
    schema_version: str = "causal-hypothesis-set-record.1"

    def __post_init__(self) -> None:
        if not self.factors:
            raise ValueError("Causal Hypothesis Set cannot be empty")
        identifiers = [item.factor_id for item in self.factors]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Causal factor identities must be unique within a set")

    @property
    def hypothesis_set_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "incident_ref": self.incident_ref,
            "principal": self.principal,
            "factors": [item.to_mapping() for item in self.factors],
            "interactions": [list(item) for item in self.interactions],
            "material_alternatives": list(self.material_alternatives),
            "overall_uncertainty": self.overall_uncertainty,
            "analysis_receipt_ref": self.analysis_receipt_ref,
        }


@dataclass(frozen=True)
class AttributionAgreement:
    left_ref: str
    right_ref: str
    prioritized_factor_ids: tuple[str, ...]
    disagreements: tuple[str, ...]
    establishes_ownership: bool = False

    def __post_init__(self) -> None:
        if self.establishes_ownership:
            raise ValueError("Attribution agreement cannot establish causal ownership")

    @property
    def agreement_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "left_ref": self.left_ref,
            "right_ref": self.right_ref,
            "prioritized_factor_ids": list(self.prioritized_factor_ids),
            "disagreements": list(self.disagreements),
            "establishes_ownership": self.establishes_ownership,
        }


def compare_hypothesis_sets(left: CausalHypothesisSet, right: CausalHypothesisSet) -> AttributionAgreement:
    if left.incident_ref != right.incident_ref:
        raise ValueError("Attribution sets must concern the same Incident")
    if left.principal == right.principal:
        raise ValueError("Attribution sets must be independently occupied")
    left_ids = {item.factor_id for item in left.factors}
    right_ids = {item.factor_id for item in right.factors}
    overlap = tuple(sorted(left_ids & right_ids))
    disagreement = tuple(sorted((left_ids | right_ids) - set(overlap)))
    return AttributionAgreement(left.hypothesis_set_ref, right.hypothesis_set_ref, overlap, disagreement)


@dataclass(frozen=True)
class PlannedContrast:
    contrast_id: str
    factor_kind: str
    factor_id: str
    baseline_condition: str
    counterfactual_condition: str
    fixed_invariants: tuple[str, ...]
    predicted_effect: str
    probe_kind: str
    cross_contract: bool = False

    def __post_init__(self) -> None:
        if self.factor_kind not in COUNTERFACTUAL_FACTORS:
            raise ValueError("Counterfactual factor is not registered in the frozen Instrument")
        if self.baseline_condition == self.counterfactual_condition:
            raise ValueError("Counterfactual Contrast must change one factor")
        if self.probe_kind not in {"direct-manipulation", "alternative-separating"}:
            raise ValueError("Contrast must declare its discriminating role")
        if self.factor_kind in {"runtime-or-provider", "evaluator-or-analysis-instrument"} and not self.cross_contract:
            raise ValueError("runtime/provider/evaluator factors require a cross-contract diagnostic lineage")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "contrast_id": self.contrast_id,
            "factor_kind": self.factor_kind,
            "factor_id": self.factor_id,
            "baseline_condition": self.baseline_condition,
            "counterfactual_condition": self.counterfactual_condition,
            "fixed_invariants": list(self.fixed_invariants),
            "predicted_effect": self.predicted_effect,
            "probe_kind": self.probe_kind,
            "cross_contract": self.cross_contract,
        }


@dataclass(frozen=True)
class CounterfactualPlan:
    incident_ref: str
    planner_principal: str
    source_hypothesis_refs: tuple[str, str]
    source_principals: tuple[str, str]
    contrasts: tuple[PlannedContrast, ...]
    controls: tuple[str, ...]
    stop_conditions: tuple[str, ...]
    analysis_receipt_ref: str
    schema_version: str = "counterfactual-plan.1"

    def __post_init__(self) -> None:
        if len(set(self.source_principals)) != 2:
            raise ValueError("Counterfactual Plan requires two isolated hypothesis authors")
        if self.planner_principal in self.source_principals:
            raise ValueError("Counterfactual planner cannot author a source hypothesis")
        if not self.contrasts or not self.stop_conditions:
            raise ValueError("Counterfactual Plan requires frozen tests and stop conditions")

    @property
    def plan_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "incident_ref": self.incident_ref,
            "planner_principal": self.planner_principal,
            "source_hypothesis_refs": list(self.source_hypothesis_refs),
            "source_principals": list(self.source_principals),
            "contrasts": [item.to_mapping() for item in self.contrasts],
            "controls": list(self.controls),
            "stop_conditions": list(self.stop_conditions),
            "analysis_receipt_ref": self.analysis_receipt_ref,
        }


@dataclass(frozen=True)
class CounterfactualContrast:
    plan_ref: str
    planned_contrast: PlannedContrast
    factual_episode_ref: str
    counterfactual_episode_ref: str
    observed_effect: str
    prediction_held: bool
    invariant_results: tuple[tuple[str, bool], ...]
    result_receipt_ref: str

    def __post_init__(self) -> None:
        if self.factual_episode_ref == self.counterfactual_episode_ref:
            raise ValueError("Counterfactual Episode must be a new Episode")
        if not all(value for _, value in self.invariant_results):
            raise ValueError("Contrast is invalid when a frozen invariant changed")

    @property
    def contrast_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "plan_ref": self.plan_ref,
            "planned_contrast": self.planned_contrast.to_mapping(),
            "factual_episode_ref": self.factual_episode_ref,
            "counterfactual_episode_ref": self.counterfactual_episode_ref,
            "observed_effect": self.observed_effect,
            "prediction_held": self.prediction_held,
            "invariant_results": [list(item) for item in self.invariant_results],
            "result_receipt_ref": self.result_receipt_ref,
        }


@dataclass(frozen=True)
class OwningLayerFinding:
    incident_ref: str
    factor_id: str
    layer: str
    status: str
    contrast_refs: tuple[str, ...]
    unresolved_alternatives: tuple[str, ...]
    reviewer_principal: str
    review_receipt_ref: str
    reasons: tuple[str, ...]

    @property
    def finding_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "incident_ref": self.incident_ref,
            "factor_id": self.factor_id,
            "layer": self.layer,
            "status": self.status,
            "contrast_refs": list(self.contrast_refs),
            "unresolved_alternatives": list(self.unresolved_alternatives),
            "reviewer_principal": self.reviewer_principal,
            "review_receipt_ref": self.review_receipt_ref,
            "reasons": list(self.reasons),
        }


def review_owning_layer(
    *,
    plan: CounterfactualPlan,
    contrasts: tuple[CounterfactualContrast, ...],
    factor: CausalFactor,
    interpretation_principals: tuple[str, str],
    reviewer_principal: str,
    review_receipt_ref: str,
    unresolved_alternatives: tuple[str, ...] = (),
    deterministic_minimal_reproduction_ref: str | None = None,
) -> OwningLayerFinding:
    """Accept factor-level ownership only under independent causal evidence."""
    occupied = {*plan.source_principals, plan.planner_principal}
    if len(set(interpretation_principals)) != 2 or occupied & set(interpretation_principals):
        raise ValueError("Counterfactual results require a fresh isolated Attribution pair")
    if reviewer_principal in occupied | set(interpretation_principals):
        raise ValueError("Independent Reviewer cannot validate its own analysis")
    applicable = tuple(
        item
        for item in contrasts
        if item.plan_ref == plan.plan_ref and item.planned_contrast.factor_id == factor.factor_id
    )
    probe_kinds = {item.planned_contrast.probe_kind for item in applicable if item.prediction_held}
    supported = bool(deterministic_minimal_reproduction_ref) or (
        len({item.planned_contrast.contrast_id for item in applicable}) >= 2
        and probe_kinds == {"direct-manipulation", "alternative-separating"}
        and all(item.prediction_held for item in applicable)
    )
    if not supported:
        return OwningLayerFinding(
            plan.incident_ref,
            factor.factor_id,
            factor.layer,
            "unresolved",
            tuple(item.contrast_ref for item in applicable),
            unresolved_alternatives,
            reviewer_principal,
            review_receipt_ref,
            ("ownership requires a deterministic reproduction or two orthogonal predicted Contrasts",),
        )
    status = "partially-attributed" if unresolved_alternatives else "accepted"
    return OwningLayerFinding(
        plan.incident_ref,
        factor.factor_id,
        factor.layer,
        status,
        tuple(item.contrast_ref for item in applicable),
        unresolved_alternatives,
        reviewer_principal,
        review_receipt_ref,
        ("factor-level ownership is independently supported; sole cause is not claimed",),
    )
