"""Challenge Admission, immutable Suite Bindings, and sealed-cohort use."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from narrative_game.contracts.canonical import digest_json


SUITES = ("development", "generated-challenge", "sealed-standing")
ADMISSION_GATES = (
    "canonical-compilation-and-coherence",
    "authorization-and-reachability",
    "solver-lineage-a",
    "solver-lineage-b",
    "oracle-validation",
    "leakage-shortcut-ambiguity-review",
    "matched-non-manifesting-control",
    "target-difficulty",
    "structural-novelty",
)


@dataclass(frozen=True)
class ChallengeCaseProposal:
    failure_class_ref: str
    generation_intent_ref: str
    designer_principal: str
    mutation: str
    protected_invariants: tuple[str, ...]
    initial_state_ref: str
    legal_action_contract_ref: str
    terminal_requirements: tuple[str, ...]
    oracle_ref: str
    expected_manifestation: str
    non_manifesting_control_ref: str
    target_profile_ref: str
    admission_plan_ref: str
    analysis_receipt_ref: str
    schema_version: str = "challenge-case-proposal-record.1"

    def __post_init__(self) -> None:
        if not self.protected_invariants or not self.terminal_requirements:
            raise ValueError("Challenge Case Proposal requires invariants and terminal requirements")

    @property
    def proposal_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "failure_class_ref": self.failure_class_ref,
            "generation_intent_ref": self.generation_intent_ref,
            "designer_principal": self.designer_principal,
            "mutation": self.mutation,
            "protected_invariants": list(self.protected_invariants),
            "initial_state_ref": self.initial_state_ref,
            "legal_action_contract_ref": self.legal_action_contract_ref,
            "terminal_requirements": list(self.terminal_requirements),
            "oracle_ref": self.oracle_ref,
            "expected_manifestation": self.expected_manifestation,
            "non_manifesting_control_ref": self.non_manifesting_control_ref,
            "target_profile_ref": self.target_profile_ref,
            "admission_plan_ref": self.admission_plan_ref,
            "analysis_receipt_ref": self.analysis_receipt_ref,
        }


@dataclass(frozen=True)
class ChallengeAdmission:
    case_ref: str
    proposal_ref: str
    designer_principal: str
    solver_principals: tuple[str, str]
    adversarial_reviewer_principal: str
    gate_results: Mapping[str, bool]
    evidence_refs: Mapping[str, tuple[str, ...]]
    unresolved_hard_findings: tuple[str, ...]
    admission_receipt_ref: str

    def __post_init__(self) -> None:
        if set(self.gate_results) != set(ADMISSION_GATES):
            raise ValueError("Challenge Admission must report every frozen gate")
        if set(self.evidence_refs) != set(ADMISSION_GATES):
            raise ValueError("Challenge Admission must preserve gate evidence")
        principals = {
            self.designer_principal,
            *self.solver_principals,
            self.adversarial_reviewer_principal,
        }
        if len(principals) != 4:
            raise ValueError("designer, two solvers, and adversarial reviewer must be independent")

    @property
    def admitted(self) -> bool:
        return all(self.gate_results.values()) and not self.unresolved_hard_findings

    @property
    def admission_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "case_ref": self.case_ref,
            "proposal_ref": self.proposal_ref,
            "designer_principal": self.designer_principal,
            "solver_principals": list(self.solver_principals),
            "adversarial_reviewer_principal": self.adversarial_reviewer_principal,
            "gate_results": dict(sorted(self.gate_results.items())),
            "evidence_refs": {
                key: list(self.evidence_refs[key]) for key in sorted(self.evidence_refs)
            },
            "unresolved_hard_findings": list(self.unresolved_hard_findings),
            "admission_receipt_ref": self.admission_receipt_ref,
            "admitted": self.admitted,
        }


@dataclass(frozen=True)
class SuiteBinding:
    case_ref: str
    suite: str
    admission_ref: str | None
    curator_principal: str
    independently_instantiated: bool
    source_binding_ref: str | None = None
    exposure_receipt_ref: str | None = None
    schema_version: str = "suite-binding.1"

    def __post_init__(self) -> None:
        if self.suite not in SUITES:
            raise ValueError("Suite Binding target is not recognized")
        if self.suite == "sealed-standing" and not self.independently_instantiated:
            raise ValueError("sealed cases must be independently instantiated")

    @property
    def binding_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_ref": self.case_ref,
            "suite": self.suite,
            "admission_ref": self.admission_ref,
            "curator_principal": self.curator_principal,
            "independently_instantiated": self.independently_instantiated,
            "source_binding_ref": self.source_binding_ref,
            "exposure_receipt_ref": self.exposure_receipt_ref,
        }


@dataclass(frozen=True)
class SuiteRegistry:
    bindings: tuple[SuiteBinding, ...] = ()
    schema_version: str = "suite-registry.1"

    @property
    def registry_ref(self) -> str:
        return digest_json(self.to_mapping())

    def current_binding(self, case_ref: str) -> SuiteBinding | None:
        matches = [item for item in self.bindings if item.case_ref == case_ref]
        return matches[-1] if matches else None

    def bind(
        self,
        *,
        case_ref: str,
        suite: str,
        curator_principal: str,
        admission: ChallengeAdmission | None = None,
        independently_instantiated: bool = False,
    ) -> "SuiteRegistry":
        current = self.current_binding(case_ref)
        if current is not None:
            raise ValueError("Suite Binding is immutable; use an explicit exposure retirement")
        if suite in {"generated-challenge", "sealed-standing"}:
            if admission is None or admission.case_ref != case_ref or not admission.admitted:
                raise ValueError("evaluation suites require a complete Challenge Admission")
        binding = SuiteBinding(
            case_ref,
            suite,
            admission.admission_ref if admission else None,
            curator_principal,
            independently_instantiated,
        )
        return SuiteRegistry(self.bindings + (binding,))

    def retire_exposed_sealed(
        self,
        *,
        case_ref: str,
        curator_principal: str,
        exposure_receipt_ref: str,
    ) -> "SuiteRegistry":
        current = self.current_binding(case_ref)
        if current is None or current.suite != "sealed-standing":
            raise ValueError("only an exposed sealed case can retire to development")
        retired = SuiteBinding(
            case_ref,
            "development",
            current.admission_ref,
            curator_principal,
            False,
            source_binding_ref=current.binding_ref,
            exposure_receipt_ref=exposure_receipt_ref,
        )
        return SuiteRegistry(self.bindings + (retired,))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "bindings": [item.to_mapping() for item in self.bindings],
        }


@dataclass(frozen=True)
class SealedCohort:
    cohort_id: str
    suite_registry_ref: str
    opaque_case_count: int
    aggregate_gate: str
    consumed_by_attempt_ref: str | None = None
    aggregate_receipt_ref: str | None = None
    schema_version: str = "sealed-cohort.1"

    def __post_init__(self) -> None:
        if self.opaque_case_count < 1:
            raise ValueError("Sealed Cohort cannot be empty")
        if (self.consumed_by_attempt_ref is None) != (self.aggregate_receipt_ref is None):
            raise ValueError("Sealed consumption and aggregate receipt must appear together")

    @property
    def cohort_ref(self) -> str:
        return digest_json(self.to_mapping())

    @property
    def consumed(self) -> bool:
        return self.consumed_by_attempt_ref is not None

    def consume(self, *, attempt_ref: str, aggregate_receipt_ref: str) -> "SealedCohort":
        if self.consumed:
            raise ValueError("Sealed Cohort is single-use")
        return replace(
            self,
            consumed_by_attempt_ref=attempt_ref,
            aggregate_receipt_ref=aggregate_receipt_ref,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "cohort_id": self.cohort_id,
            "suite_registry_ref": self.suite_registry_ref,
            "opaque_case_count": self.opaque_case_count,
            "aggregate_gate": self.aggregate_gate,
            "consumed_by_attempt_ref": self.consumed_by_attempt_ref,
            "aggregate_receipt_ref": self.aggregate_receipt_ref,
        }
