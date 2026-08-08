"""Precommitted Standing samples and governed adaptive diagnostic scheduling."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json


PROTECTED_BUDGETS = (
    "standing",
    "invalid-replacements",
    "diagnostics",
    "counterfactuals",
    "promoted-regression",
    "sealed",
    "contingency",
)


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class StandingSamplingPlan:
    estimand: str
    assignment_ids: tuple[str, ...]
    strata: Mapping[str, tuple[str, ...]]
    replacement_chains: Mapping[str, tuple[str, ...]]
    maximum_sample_size: int
    stop_after_assignment_count: int
    schema_version: str = "standing-sampling-plan.1"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "strata",
            {key: tuple(value) for key, value in sorted(self.strata.items())},
        )
        object.__setattr__(
            self,
            "replacement_chains",
            {key: tuple(value) for key, value in sorted(self.replacement_chains.items())},
        )
        if len(set(self.assignment_ids)) != len(self.assignment_ids):
            raise ValueError("Standing Sampling Plan assignments must be unique")
        if self.maximum_sample_size < len(self.assignment_ids):
            raise ValueError("Standing maximum cannot be below frozen membership")
        if self.stop_after_assignment_count != len(self.assignment_ids):
            raise ValueError("Standing stop time must be precommitted to frozen membership")

    @property
    def plan_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "estimand": self.estimand,
            "assignment_ids": list(self.assignment_ids),
            "strata": {key: list(value) for key, value in sorted(self.strata.items())},
            "replacement_chains": {
                key: list(value) for key, value in sorted(self.replacement_chains.items())
            },
            "maximum_sample_size": self.maximum_sample_size,
            "stop_after_assignment_count": self.stop_after_assignment_count,
        }

    def standing_membership(self, outcomes: Mapping[str, str]) -> tuple[str, ...]:
        """Outcomes cannot add, remove, or reorder the precommitted sample."""
        return self.assignment_ids

    def replacement_for(self, assignment_id: str, attempt: int) -> str | None:
        chain = tuple(self.replacement_chains.get(assignment_id, ()))
        return chain[attempt] if 0 <= attempt < len(chain) else None


@dataclass(frozen=True)
class BudgetEnvelope:
    limits: Mapping[str, int]
    spent: Mapping[str, int]
    schema_version: str = "budget-envelope.1"

    def __post_init__(self) -> None:
        limits = {key: int(value) for key, value in self.limits.items()}
        spent = {key: int(value) for key, value in self.spent.items()}
        if set(limits) != set(PROTECTED_BUDGETS) or set(spent) != set(PROTECTED_BUDGETS):
            raise ValueError("Budget Envelope must preserve every protected budget")
        if any(value < 0 for value in (*limits.values(), *spent.values())):
            raise ValueError("Budget values cannot be negative")
        if any(spent[key] > limits[key] for key in limits):
            raise ValueError("Budget Envelope is overspent")
        object.__setattr__(self, "limits", limits)
        object.__setattr__(self, "spent", spent)

    @property
    def envelope_id(self) -> str:
        return digest_json(self.to_mapping())

    def remaining(self, category: str) -> int:
        return self.limits[category] - self.spent[category]

    def reserve(self, category: str, amount: int) -> "BudgetEnvelope":
        if category not in PROTECTED_BUDGETS or amount < 0:
            raise ValueError("invalid budget reservation")
        if amount > self.remaining(category):
            raise ValueError(f"{category} budget exhausted")
        updated = dict(self.spent)
        updated[category] += amount
        return replace(self, spent=updated)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "limits": dict(sorted(self.limits.items())),
            "spent": dict(sorted(self.spent.items())),
        }


@dataclass(frozen=True)
class CostForecast:
    calls: int
    input_tokens: int
    output_tokens: int
    spend_microunits: int
    latency_ms: int
    concurrency: int
    retry_burden: int
    cost_model_version: str

    def __post_init__(self) -> None:
        if min(
            self.calls,
            self.input_tokens,
            self.output_tokens,
            self.spend_microunits,
            self.latency_ms,
            self.concurrency,
            self.retry_burden,
        ) < 0:
            raise ValueError("Cost Forecast cannot contain negative values")

    def to_mapping(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class EvidenceWorkPackage:
    package_id: str
    claim_id: str
    budget_category: str
    execution: bool
    verification: bool
    sweep: bool
    corroboration: bool
    matched_control: bool
    interpretation: bool
    receipts: bool
    cascade_level: int
    required_cascade_level: int
    coverage_cell: str
    mandatory_validity_debt: int
    target_boundary_proximity: int
    causal_discrimination: int
    uncertainty_reduction: int
    regression_risk: int
    structural_novelty: int
    forecast: CostForecast
    sealed_handle_id: str | None = None

    @property
    def complete(self) -> bool:
        return all(
            (
                self.execution,
                self.verification,
                self.sweep,
                self.corroboration,
                self.matched_control,
                self.interpretation,
                self.receipts,
            )
        )

    @property
    def priority_vector(self) -> tuple[int, ...]:
        return (
            self.mandatory_validity_debt,
            self.target_boundary_proximity,
            self.causal_discrimination,
            self.uncertainty_reduction,
            self.regression_risk,
            self.structural_novelty,
            -self.forecast.spend_microunits,
            -self.forecast.latency_ms,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            **{
                key: value
                for key, value in self.__dict__.items()
                if key != "forecast"
            },
            "forecast": self.forecast.to_mapping(),
            "complete": self.complete,
            "priority_vector": list(self.priority_vector),
        }


@dataclass(frozen=True)
class SealedCohortHandle:
    handle_id: str
    cohort_size: int
    declared_cost_microunits: int
    eligibility_ref: str
    single_use: bool = True
    schema_version: str = "sealed-cohort-handle.1"

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "handle_id": self.handle_id,
            "cohort_size": self.cohort_size,
            "declared_cost_microunits": self.declared_cost_microunits,
            "eligibility_ref": self.eligibility_ref,
            "single_use": self.single_use,
        }


@dataclass(frozen=True)
class SchedulingReceipt:
    evidence_snapshot_ref: str
    scheduling_analysis_ref: str
    queue_id: str
    alternatives: tuple[Mapping[str, Any], ...]
    selected_package_id: str | None
    rejection_reasons: Mapping[str, tuple[str, ...]]
    budget_before_ref: str
    budget_after_ref: str
    stop_state: str
    next_actions: tuple[str, ...]
    reservation: Mapping[str, Any] | None = None
    schema_version: str = "scheduling-receipt.1"

    def __post_init__(self) -> None:
        object.__setattr__(self, "alternatives", tuple(_copy(item) for item in self.alternatives))
        object.__setattr__(
            self,
            "rejection_reasons",
            {key: tuple(value) for key, value in sorted(self.rejection_reasons.items())},
        )
        object.__setattr__(self, "reservation", _copy(self.reservation) if self.reservation else None)

    @property
    def receipt_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_snapshot_ref": self.evidence_snapshot_ref,
            "scheduling_analysis_ref": self.scheduling_analysis_ref,
            "queue_id": self.queue_id,
            "alternatives": [dict(item) for item in self.alternatives],
            "selected_package_id": self.selected_package_id,
            "rejection_reasons": {
                key: list(value) for key, value in sorted(self.rejection_reasons.items())
            },
            "budget_before_ref": self.budget_before_ref,
            "budget_after_ref": self.budget_after_ref,
            "stop_state": self.stop_state,
            "next_actions": list(self.next_actions),
            "reservation": dict(self.reservation) if self.reservation else None,
        }


@dataclass(frozen=True)
class SchedulingDecision:
    selected: EvidenceWorkPackage | None
    budget: BudgetEnvelope
    receipt: SchedulingReceipt


def schedule_diagnostic_work(
    *,
    evidence_snapshot_ref: str,
    scheduling_analysis_ref: str,
    queue_id: str,
    packages: tuple[EvidenceWorkPackage, ...],
    budget: BudgetEnvelope,
    sealed_handles: Mapping[str, SealedCohortHandle] | None = None,
    used_sealed_handles: tuple[str, ...] = (),
) -> SchedulingDecision:
    """Apply the lexicographic policy to complete, affordable work packages."""
    handles = dict(sealed_handles or {})
    rejections: dict[str, tuple[str, ...]] = {}
    eligible = []
    for package in packages:
        reasons = []
        if not package.complete:
            reasons.append("Evidence Work Package is incomplete")
        if package.cascade_level < package.required_cascade_level:
            reasons.append("Evidence Cascade is insufficient for the named claim")
        if package.budget_category not in PROTECTED_BUDGETS:
            reasons.append("unknown protected budget")
        if package.budget_category in {"standing", "invalid-replacements"}:
            reasons.append("diagnostic queue cannot spend protected Standing budgets")
        if package.budget_category in PROTECTED_BUDGETS and package.forecast.spend_microunits > budget.remaining(package.budget_category):
            reasons.append(f"{package.budget_category} budget is insufficient")
        if package.sealed_handle_id is not None:
            handle = handles.get(package.sealed_handle_id)
            if package.budget_category != "sealed":
                reasons.append("sealed work must use the sealed budget")
            if handle is None:
                reasons.append("sealed handle is absent")
            elif handle.handle_id in used_sealed_handles:
                reasons.append("sealed cohort handle is single-use")
            elif package.forecast.spend_microunits != handle.declared_cost_microunits:
                reasons.append("sealed cohort must be scheduled at its complete declared cost")
        if reasons:
            rejections[package.package_id] = tuple(reasons)
        else:
            eligible.append(package)

    alternatives = tuple(
        {
            "package_id": package.package_id,
            "claim_id": package.claim_id,
            "priority_vector": list(package.priority_vector),
            "forecast": package.forecast.to_mapping(),
        }
        for package in sorted(packages, key=lambda item: item.package_id)
    )
    before = budget.envelope_id
    if not eligible:
        stop = "unresolved-budget" if any("budget" in reason for values in rejections.values() for reason in values) else "saturated"
        receipt = SchedulingReceipt(
            evidence_snapshot_ref,
            scheduling_analysis_ref,
            queue_id,
            alternatives,
            None,
            rejections,
            before,
            before,
            stop,
            ("retain unresolved diagnostic claims",),
        )
        return SchedulingDecision(None, budget, receipt)
    selected = sorted(
        eligible,
        key=lambda item: (tuple(-value for value in item.priority_vector), item.package_id),
    )[0]
    updated = budget.reserve(selected.budget_category, selected.forecast.spend_microunits)
    for package in eligible:
        if package.package_id != selected.package_id:
            rejections[package.package_id] = (
                "lower lexicographic Priority Vector than selected package",
            )
    receipt = SchedulingReceipt(
        evidence_snapshot_ref,
        scheduling_analysis_ref,
        queue_id,
        alternatives,
        selected.package_id,
        rejections,
        before,
        updated.envelope_id,
        "scheduled",
        (f"execute complete package {selected.package_id}",),
        reservation={
            "category": selected.budget_category,
            "amount_microunits": selected.forecast.spend_microunits,
            "remaining_before_microunits": budget.remaining(selected.budget_category),
            "remaining_after_microunits": updated.remaining(selected.budget_category),
        },
    )
    return SchedulingDecision(selected, updated, receipt)
