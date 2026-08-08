"""Failure-driven task hardening with thirteen fail-closed transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from narrative_game.contracts.canonical import digest_json


ELIGIBLE_HARDENING_LAYERS = ("agent-capability", "coordination")
REPAIR_ONLY_LAYERS = ("game", "artifact", "runtime", "provider", "evaluator")
FORBIDDEN_HARDENING_MUTATIONS = (
    "contradiction",
    "ambiguity",
    "impossibility",
    "hidden-required-action",
    "authorization-gap",
    "answer-bearing-hint",
    "runtime-degradation",
    "evaluator-change",
)
PROTECTED_HARDENING_INVARIANTS = (
    "canonical-coherence",
    "authorized-reachability",
    "two-independent-solver-solvability",
    "oracle-validity",
    "bounded-acceptable-answers",
    "no-answer-or-shortcut-leakage",
    "artifact-realism",
    "narrative-quality",
)
PREFLIGHT_GATES = (
    "canonical-compilation",
    "coherence",
    "authorization",
    "reachability",
    "solver-a-valid-solution",
    "solver-b-valid-solution",
    "oracle-validation",
    "bounded-acceptable-answers",
    "leakage-review",
    "shortcut-review",
    "matched-non-manifesting-control",
    "artifact-realism",
    "narrative-quality",
)
HARDENING_STAGES = (
    "baseline-eligibility",
    "failure-analysis",
    "failure-routing",
    "class-promotion",
    "requirement-freeze",
    "child-generation",
    "challenge-preflight",
    "matched-remeasurement",
    "target-comparison",
    "challenge-admission",
    "sealed-non-regression",
    "independent-review",
    "hardening-transition",
)
REQUIRED_HARDENING_LINEAGE = (
    "baseline-release->baseline-panel-application",
    "baseline-panel-application->baseline-episodes",
    "baseline-episodes->baseline-difficulty-profile",
    "baseline-episodes->incident",
    "incident->semantic-interpretation",
    "semantic-interpretation->attribution-a",
    "semantic-interpretation->attribution-b",
    "attribution-a->counterfactual-plan",
    "attribution-b->counterfactual-plan",
    "counterfactual-plan->contrast-a",
    "counterfactual-plan->contrast-b",
    "contrast-a->owning-layer-finding",
    "contrast-b->owning-layer-finding",
    "owning-layer-finding->promoted-failure-class",
    "promoted-failure-class->task-hardening-requirement",
    "task-hardening-requirement->generation-intent",
    "generation-intent->child-release",
    "child-release->challenge-preflight",
    "child-release->child-panel-application",
    "child-panel-application->child-episodes",
    "child-episodes->child-difficulty-profile",
    "baseline-difficulty-profile->release-comparison",
    "child-difficulty-profile->release-comparison",
    "challenge-preflight->challenge-admission",
    "release-comparison->challenge-admission",
    "challenge-admission->sealed-receipt",
    "sealed-receipt->independent-review",
    "independent-review->hardening-transition",
)


@dataclass(frozen=True)
class FailureEvidenceSummary:
    incident_ref: str
    owning_layer_finding_ref: str
    corroborated: bool
    attribution_principals: tuple[str, str]
    owning_layer_status: str
    cause_layers: tuple[str, ...]
    material_defect_layers: tuple[str, ...]
    successful_contrast_refs: tuple[str, ...]
    unresolved_branches: tuple[str, ...] = ()
    controlled_unresolved_branches: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(set(self.attribution_principals)) != 2:
            raise ValueError("Failure evidence requires two isolated Attribution principals")
        if self.owning_layer_status not in {"accepted", "partially-attributed", "unresolved"}:
            raise ValueError("owning-layer status is not recognized")

    @property
    def summary_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "incident_ref": self.incident_ref,
            "owning_layer_finding_ref": self.owning_layer_finding_ref,
            "corroborated": self.corroborated,
            "attribution_principals": list(self.attribution_principals),
            "owning_layer_status": self.owning_layer_status,
            "cause_layers": list(self.cause_layers),
            "material_defect_layers": list(self.material_defect_layers),
            "successful_contrast_refs": list(self.successful_contrast_refs),
            "unresolved_branches": list(self.unresolved_branches),
            "controlled_unresolved_branches": list(self.controlled_unresolved_branches),
        }


@dataclass(frozen=True)
class HardeningRouteDecision:
    route: str
    evidence_ref: str
    reasons: tuple[str, ...]

    @property
    def decision_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {"route": self.route, "evidence_ref": self.evidence_ref, "reasons": list(self.reasons)}


def route_failure(summary: FailureEvidenceSummary) -> HardeningRouteDecision:
    """Select harden, repair, or quarantine without a favorable default."""
    defects = tuple(sorted(set(summary.material_defect_layers) & set(REPAIR_ONLY_LAYERS)))
    if defects:
        return HardeningRouteDecision(
            "repair",
            summary.summary_ref,
            ("material defect layers cannot become difficulty: " + ", ".join(defects),),
        )
    if not summary.corroborated:
        return HardeningRouteDecision("quarantine", summary.summary_ref, ("Incident is not independently corroborated",))
    if summary.owning_layer_status not in {"accepted", "partially-attributed"}:
        return HardeningRouteDecision("quarantine", summary.summary_ref, ("causal ownership remains unresolved",))
    if len(summary.successful_contrast_refs) < 2:
        return HardeningRouteDecision("quarantine", summary.summary_ref, ("fewer than two causal Contrasts support the route",))
    uncontrolled = set(summary.unresolved_branches) - set(summary.controlled_unresolved_branches)
    if uncontrolled:
        return HardeningRouteDecision(
            "quarantine",
            summary.summary_ref,
            ("material unresolved branches are neither invariant nor controlled: " + ", ".join(sorted(uncontrolled)),),
        )
    eligible = tuple(sorted(set(summary.cause_layers) & set(ELIGIBLE_HARDENING_LAYERS)))
    if not eligible:
        return HardeningRouteDecision("repair", summary.summary_ref, ("no agent-capability or coordination factor is supported",))
    return HardeningRouteDecision(
        "harden",
        summary.summary_ref,
        ("promoted agent or coordination capability is causally supported without a material defect",),
    )


@dataclass(frozen=True)
class TaskHardeningRequirement:
    source_failure_class_ref: str
    owning_layer_finding_ref: str
    capability_demand: str
    challenge_mechanism: str
    allowed_mutation_surface: tuple[str, ...]
    selected_mutations: tuple[str, ...]
    forbidden_mutations: tuple[str, ...]
    protected_invariants: tuple[str, ...]
    expected_manifestation: str
    non_manifesting_control: str
    target_contract_ref: str
    generation_intent_ref: str
    lineage_refs: tuple[str, ...]
    schema_version: str = "task-hardening-requirement.1"

    def __post_init__(self) -> None:
        if not self.capability_demand.strip() or not self.challenge_mechanism.strip():
            raise ValueError("Task Hardening Requirement needs a capability demand and mechanism")
        if set(self.selected_mutations) & set(self.forbidden_mutations):
            raise ValueError("Task Hardening Requirement selects a forbidden mutation")
        if not set(self.selected_mutations) <= set(self.allowed_mutation_surface):
            raise ValueError("selected hardening mutation is outside the allowed surface")
        if set(self.forbidden_mutations) != set(FORBIDDEN_HARDENING_MUTATIONS):
            raise ValueError("Task Hardening Requirement must preserve every forbidden mutation")
        if not set(PROTECTED_HARDENING_INVARIANTS) <= set(self.protected_invariants):
            raise ValueError("Task Hardening Requirement omits a protected invariant")
        if not self.lineage_refs:
            raise ValueError("Task Hardening Requirement requires exact upstream lineage")

    @property
    def requirement_ref(self) -> str:
        return digest_json(self.material())

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_failure_class_ref": self.source_failure_class_ref,
            "owning_layer_finding_ref": self.owning_layer_finding_ref,
            "capability_demand": self.capability_demand,
            "challenge_mechanism": self.challenge_mechanism,
            "allowed_mutation_surface": list(self.allowed_mutation_surface),
            "selected_mutations": list(self.selected_mutations),
            "forbidden_mutations": list(self.forbidden_mutations),
            "protected_invariants": list(self.protected_invariants),
            "expected_manifestation": self.expected_manifestation,
            "non_manifesting_control": self.non_manifesting_control,
            "target_contract_ref": self.target_contract_ref,
            "generation_intent_ref": self.generation_intent_ref,
            "lineage_refs": list(self.lineage_refs),
        }

    def builder_projection(self) -> dict[str, Any]:
        """The complete allowlist exposed to the existing generation path."""
        return {
            "schema_version": self.schema_version,
            "requirement_ref": self.requirement_ref,
            "capability_demand": self.capability_demand,
            "challenge_mechanism": self.challenge_mechanism,
            "allowed_mutation_surface": list(self.allowed_mutation_surface),
            "selected_mutations": list(self.selected_mutations),
            "forbidden_mutations": list(self.forbidden_mutations),
            "protected_invariants": list(self.protected_invariants),
            "expected_manifestation": self.expected_manifestation,
            "non_manifesting_control": self.non_manifesting_control,
            "target_contract_ref": self.target_contract_ref,
            "generation_intent_ref": self.generation_intent_ref,
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "requirement_ref": self.requirement_ref,
            **self.material(),
        }


@dataclass(frozen=True)
class ArtifactPreflightAttestation:
    artifact_id: str
    attestation_ref: str
    verification_ok: bool
    measurement_status: str

    @property
    def accepted(self) -> bool:
        return self.verification_ok and self.measurement_status == "accepted"

    def to_mapping(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "attestation_ref": self.attestation_ref,
            "verification_ok": self.verification_ok,
            "measurement_status": self.measurement_status,
            "accepted": self.accepted,
        }


@dataclass(frozen=True)
class ChallengePreflight:
    child_release_ref: str
    gate_results: Mapping[str, bool]
    gate_evidence_refs: Mapping[str, tuple[str, ...]]
    expected_artifact_ids: tuple[str, ...]
    artifact_attestations: tuple[ArtifactPreflightAttestation, ...]
    designer_principal: str
    generation_builder_principal: str
    generation_reviewer_principal: str
    solver_principals: tuple[str, str]
    leakage_reviewer_principal: str
    unresolved_hard_findings: tuple[str, ...]
    schema_version: str = "challenge-preflight.1"

    def __post_init__(self) -> None:
        if set(self.gate_results) != set(PREFLIGHT_GATES):
            raise ValueError("Challenge preflight must report every frozen gate")
        if set(self.gate_evidence_refs) != set(PREFLIGHT_GATES):
            raise ValueError("Challenge preflight must preserve evidence for every gate")
        principals = {
            self.designer_principal,
            self.generation_builder_principal,
            self.generation_reviewer_principal,
            *self.solver_principals,
            self.leakage_reviewer_principal,
        }
        if len(principals) != 6:
            raise ValueError("Challenge preflight principals must be independent")
        actual = tuple(item.artifact_id for item in self.artifact_attestations)
        if len(actual) != len(set(actual)) or set(actual) != set(self.expected_artifact_ids):
            raise ValueError("Challenge preflight requires exact Artifact Attestation membership")

    @property
    def eligible(self) -> bool:
        return (
            all(self.gate_results.values())
            and not self.unresolved_hard_findings
            and all(item.accepted for item in self.artifact_attestations)
        )

    @property
    def preflight_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "child_release_ref": self.child_release_ref,
            "gate_results": dict(sorted(self.gate_results.items())),
            "gate_evidence_refs": {
                key: list(self.gate_evidence_refs[key]) for key in sorted(self.gate_evidence_refs)
            },
            "expected_artifact_ids": list(self.expected_artifact_ids),
            "artifact_attestations": [item.to_mapping() for item in self.artifact_attestations],
            "designer_principal": self.designer_principal,
            "generation_builder_principal": self.generation_builder_principal,
            "generation_reviewer_principal": self.generation_reviewer_principal,
            "solver_principals": list(self.solver_principals),
            "leakage_reviewer_principal": self.leakage_reviewer_principal,
            "unresolved_hard_findings": list(self.unresolved_hard_findings),
            "eligible": self.eligible,
        }


@dataclass(frozen=True)
class MatchedHardeningComparison:
    baseline_profile_ref: str
    child_profile_ref: str
    control_profile_ref: str
    baseline_panel_ref: str
    child_panel_ref: str
    baseline_instrument_ref: str
    child_instrument_ref: str
    target_contract_ref: str
    precommitted_assignments_complete: bool
    invalid_episodes_counted_as_failures: bool
    target_dominance_outcome: str
    child_classification: str
    targeted_delta_interval: tuple[float, float]
    control_delta_interval: tuple[float, float]
    hard_gate_results: Mapping[str, bool]
    no_gating_regression: bool
    schema_version: str = "matched-hardening-comparison.1"

    @property
    def eligible(self) -> bool:
        return (
            self.baseline_panel_ref == self.child_panel_ref
            and self.baseline_instrument_ref == self.child_instrument_ref
            and self.precommitted_assignments_complete
            and not self.invalid_episodes_counted_as_failures
            and self.target_dominance_outcome == "child-dominates"
            and self.child_classification == "supported-target-band"
            and self.targeted_delta_interval[0] > 0
            and self.control_delta_interval[0] <= 0 <= self.control_delta_interval[1]
            and all(self.hard_gate_results.values())
            and self.no_gating_regression
        )

    @property
    def comparison_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "baseline_profile_ref": self.baseline_profile_ref,
            "child_profile_ref": self.child_profile_ref,
            "control_profile_ref": self.control_profile_ref,
            "baseline_panel_ref": self.baseline_panel_ref,
            "child_panel_ref": self.child_panel_ref,
            "baseline_instrument_ref": self.baseline_instrument_ref,
            "child_instrument_ref": self.child_instrument_ref,
            "target_contract_ref": self.target_contract_ref,
            "precommitted_assignments_complete": self.precommitted_assignments_complete,
            "invalid_episodes_counted_as_failures": self.invalid_episodes_counted_as_failures,
            "target_dominance_outcome": self.target_dominance_outcome,
            "child_classification": self.child_classification,
            "targeted_delta_interval": list(self.targeted_delta_interval),
            "control_delta_interval": list(self.control_delta_interval),
            "hard_gate_results": dict(sorted(self.hard_gate_results.items())),
            "no_gating_regression": self.no_gating_regression,
            "eligible": self.eligible,
        }


@dataclass(frozen=True)
class FinalChallengeAdmission:
    preflight_ref: str
    comparison_ref: str
    generation_receipt_ref: str
    novelty_receipt_ref: str
    suite_binding_ref: str
    suite: str
    bound_child_release_ref: str

    @property
    def eligible(self) -> bool:
        return self.suite == "generated-challenge" and bool(self.suite_binding_ref)

    @property
    def admission_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "preflight_ref": self.preflight_ref,
            "comparison_ref": self.comparison_ref,
            "generation_receipt_ref": self.generation_receipt_ref,
            "novelty_receipt_ref": self.novelty_receipt_ref,
            "suite_binding_ref": self.suite_binding_ref,
            "suite": self.suite,
            "bound_child_release_ref": self.bound_child_release_ref,
            "eligible": self.eligible,
        }


@dataclass(frozen=True)
class SealedGovernanceEvidence:
    parent_framework_ref: str
    child_framework_ref: str
    existing_qualification_ref: str | None
    cohort_ref: str | None
    cohort_consumed_once: bool
    aggregate_result: str
    contents_exposed: bool

    @property
    def eligible(self) -> bool:
        if self.contents_exposed or self.aggregate_result != "pass":
            return False
        if self.parent_framework_ref == self.child_framework_ref:
            return self.existing_qualification_ref is not None and self.cohort_ref is None
        return self.cohort_ref is not None and self.cohort_consumed_once

    @property
    def evidence_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "parent_framework_ref": self.parent_framework_ref,
            "child_framework_ref": self.child_framework_ref,
            "existing_qualification_ref": self.existing_qualification_ref,
            "cohort_ref": self.cohort_ref,
            "cohort_consumed_once": self.cohort_consumed_once,
            "aggregate_result": self.aggregate_result,
            "contents_exposed": self.contents_exposed,
            "eligible": self.eligible,
        }


@dataclass(frozen=True)
class HardeningReview:
    proposal_ref: str
    reviewer_principal: str
    contributor_principals: tuple[str, ...]
    decision: str
    mutated_proposal: bool
    gate_results: Mapping[str, bool]
    receipt_ref: str

    @property
    def eligible(self) -> bool:
        return (
            self.reviewer_principal not in self.contributor_principals
            and self.decision == "accept"
            and not self.mutated_proposal
            and all(self.gate_results.values())
        )


@dataclass(frozen=True)
class HardeningContract:
    panel_ref: str
    instrument_ref: str
    atlas_ref: str
    target_contract_ref: str
    required_lineage: tuple[str, ...] = REQUIRED_HARDENING_LINEAGE
    schema_version: str = "hardening-demonstration-contract.1"

    @property
    def contract_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "panel_ref": self.panel_ref,
            "instrument_ref": self.instrument_ref,
            "atlas_ref": self.atlas_ref,
            "target_contract_ref": self.target_contract_ref,
            "required_lineage": list(self.required_lineage),
        }


@dataclass(frozen=True)
class HardeningEvidence:
    baseline_valid: bool
    baseline_complete: bool
    baseline_panel_ref: str
    baseline_instrument_ref: str
    failure: FailureEvidenceSummary
    route: HardeningRouteDecision
    failure_class_ref: str
    failure_class_stage: str
    failure_class_atlas_ref: str
    failure_class_fixtures_complete: bool
    requirement: TaskHardeningRequirement
    child_release_ref: str
    generation_receipt_ref: str
    generation_builder_principal: str
    generation_reviewer_principal: str
    preflight: ChallengePreflight
    child_measurement_complete: bool
    child_panel_ref: str
    child_instrument_ref: str
    comparison: MatchedHardeningComparison
    admission: FinalChallengeAdmission
    sealed: SealedGovernanceEvidence
    review: HardeningReview
    lineage_edges: tuple[str, ...]


@dataclass(frozen=True)
class HardeningTransitionReceipt:
    stage: str
    contract_ref: str
    input_state_ref: str
    status: str
    route: str | None
    evidence_refs: tuple[str, ...]
    lineage_edges: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def receipt_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "contract_ref": self.contract_ref,
            "input_state_ref": self.input_state_ref,
            "status": self.status,
            "route": self.route,
            "evidence_refs": list(self.evidence_refs),
            "lineage_edges": list(self.lineage_edges),
            "blockers": list(self.blockers),
        }


@dataclass(frozen=True)
class HardeningDemonstrationResult:
    status: str
    route: str | None
    receipts: tuple[HardeningTransitionReceipt, ...]
    lineage_edges: tuple[str, ...]
    blockers: tuple[str, ...]

    @property
    def result_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "route": self.route,
            "receipts": [item.to_mapping() for item in self.receipts],
            "lineage_edges": list(self.lineage_edges),
            "blockers": list(self.blockers),
        }


def _stage_receipt(
    *,
    stage: str,
    contract: HardeningContract,
    receipts: tuple[HardeningTransitionReceipt, ...],
    status: str,
    route: str | None,
    evidence_refs: tuple[str, ...],
    available_edges: tuple[str, ...],
    stage_edges: tuple[str, ...],
    blockers: tuple[str, ...] = (),
) -> HardeningTransitionReceipt:
    state_ref = digest_json(
        {
            "contract_ref": contract.contract_ref,
            "prior_receipts": [item.receipt_ref for item in receipts],
            "available_lineage_edges": list(available_edges),
        }
    )
    recorded_edges = tuple(item for item in stage_edges if item in available_edges)
    return HardeningTransitionReceipt(
        stage,
        contract.contract_ref,
        state_ref,
        status,
        route,
        evidence_refs,
        recorded_edges,
        blockers,
    )


def run_hardening_demonstration(
    contract: HardeningContract,
    evidence: HardeningEvidence,
) -> HardeningDemonstrationResult:
    """Run the thirteen transitions and retain every attributable stop."""
    receipts: tuple[HardeningTransitionReceipt, ...] = ()
    recorded_edges: tuple[str, ...] = ()
    route: str | None = None

    def pass_stage(stage: str, refs: tuple[str, ...], edges: tuple[str, ...] = ()) -> None:
        nonlocal receipts, recorded_edges
        receipt = _stage_receipt(
            stage=stage,
            contract=contract,
            receipts=receipts,
            status="passed",
            route=route,
            evidence_refs=refs,
            available_edges=evidence.lineage_edges,
            stage_edges=edges,
        )
        receipts += (receipt,)
        recorded_edges += receipt.lineage_edges

    def halt(stage: str, status: str, blockers: tuple[str, ...], refs: tuple[str, ...] = ()) -> HardeningDemonstrationResult:
        receipt = _stage_receipt(
            stage=stage,
            contract=contract,
            receipts=receipts,
            status=status,
            route=route,
            evidence_refs=refs,
            available_edges=evidence.lineage_edges,
            stage_edges=(),
            blockers=blockers,
        )
        return HardeningDemonstrationResult(status, route, receipts + (receipt,), recorded_edges, blockers)

    stage = HARDENING_STAGES[0]
    if not evidence.baseline_valid or not evidence.baseline_complete:
        return halt(stage, "rejected", ("baseline evidence is invalid or incomplete",))
    if evidence.baseline_panel_ref != contract.panel_ref or evidence.baseline_instrument_ref != contract.instrument_ref:
        return halt(stage, "rejected", ("baseline Panel or Instrument differs from frozen contract",))
    pass_stage(stage, (evidence.baseline_panel_ref, evidence.baseline_instrument_ref), REQUIRED_HARDENING_LINEAGE[:3])

    stage = HARDENING_STAGES[1]
    if not evidence.failure.corroborated:
        return halt(stage, "quarantined", ("Incident lacks independent corroboration",), (evidence.failure.summary_ref,))
    pass_stage(stage, (evidence.failure.summary_ref,), REQUIRED_HARDENING_LINEAGE[3:13])

    stage = HARDENING_STAGES[2]
    expected_route = route_failure(evidence.failure)
    if evidence.route.decision_ref != expected_route.decision_ref:
        return halt(stage, "rejected", ("frozen route does not match causal evidence",), (evidence.route.decision_ref,))
    route = evidence.route.route
    if route == "repair":
        return halt(stage, "repair-required", evidence.route.reasons, (evidence.route.decision_ref,))
    if route == "quarantine":
        return halt(stage, "quarantined", evidence.route.reasons, (evidence.route.decision_ref,))
    pass_stage(stage, (evidence.route.decision_ref,))

    stage = HARDENING_STAGES[3]
    if (
        evidence.failure_class_stage != "promoted"
        or evidence.failure_class_atlas_ref != contract.atlas_ref
        or not evidence.failure_class_fixtures_complete
    ):
        return halt(stage, "rejected", ("Failure Class is not promoted with fixtures in the pinned Atlas",), (evidence.failure_class_ref,))
    pass_stage(stage, (evidence.failure_class_ref,), (REQUIRED_HARDENING_LINEAGE[13],))

    stage = HARDENING_STAGES[4]
    if evidence.requirement.source_failure_class_ref != evidence.failure_class_ref:
        return halt(stage, "rejected", ("Task Hardening Requirement names another Failure Class",), (evidence.requirement.requirement_ref,))
    if evidence.requirement.target_contract_ref != contract.target_contract_ref:
        return halt(stage, "rejected", ("Task Hardening Requirement names a stale Target Contract",), (evidence.requirement.requirement_ref,))
    if evidence.requirement.owning_layer_finding_ref != evidence.failure.owning_layer_finding_ref:
        return halt(stage, "rejected", ("Task Hardening Requirement names another Owning-Layer Finding",), (evidence.requirement.requirement_ref,))
    pass_stage(stage, (evidence.requirement.requirement_ref,), (REQUIRED_HARDENING_LINEAGE[14],))

    stage = HARDENING_STAGES[5]
    if evidence.generation_builder_principal == evidence.generation_reviewer_principal:
        return halt(stage, "rejected", ("generation builder cannot review its own child",))
    if evidence.preflight.child_release_ref != evidence.child_release_ref:
        return halt(stage, "rejected", ("preflight names another child Release",))
    pass_stage(
        stage,
        (evidence.requirement.generation_intent_ref, evidence.child_release_ref, evidence.generation_receipt_ref),
        REQUIRED_HARDENING_LINEAGE[15:17],
    )

    stage = HARDENING_STAGES[6]
    if not evidence.preflight.eligible:
        failed = tuple(sorted(name for name, passed in evidence.preflight.gate_results.items() if not passed))
        artifact_failures = tuple(item.artifact_id for item in evidence.preflight.artifact_attestations if not item.accepted)
        blockers = ("Challenge preflight is incomplete",) + failed + artifact_failures + evidence.preflight.unresolved_hard_findings
        return halt(stage, "rejected", blockers, (evidence.preflight.preflight_ref,))
    pass_stage(stage, (evidence.preflight.preflight_ref,), (REQUIRED_HARDENING_LINEAGE[17],))

    stage = HARDENING_STAGES[7]
    if not evidence.child_measurement_complete:
        return halt(stage, "rejected", ("child measurement is incomplete",))
    if evidence.child_panel_ref != contract.panel_ref or evidence.child_instrument_ref != contract.instrument_ref:
        return halt(stage, "rejected", ("Panel or Instrument drift makes comparison ineligible",))
    pass_stage(stage, (evidence.child_panel_ref, evidence.child_instrument_ref), REQUIRED_HARDENING_LINEAGE[18:21])

    stage = HARDENING_STAGES[8]
    if not evidence.comparison.eligible:
        return halt(stage, "rejected", ("matched Target comparison is ineligible or indeterminate",), (evidence.comparison.comparison_ref,))
    if evidence.comparison.target_contract_ref != contract.target_contract_ref:
        return halt(stage, "rejected", ("matched comparison names a stale Target Contract",), (evidence.comparison.comparison_ref,))
    pass_stage(stage, (evidence.comparison.comparison_ref,), REQUIRED_HARDENING_LINEAGE[21:23])

    stage = HARDENING_STAGES[9]
    if (
        evidence.admission.preflight_ref != evidence.preflight.preflight_ref
        or evidence.admission.comparison_ref != evidence.comparison.comparison_ref
        or evidence.admission.bound_child_release_ref != evidence.child_release_ref
        or not evidence.admission.eligible
    ):
        return halt(stage, "rejected", ("Challenge Admission does not bind preflight and matched measurement",), (evidence.admission.admission_ref,))
    pass_stage(stage, (evidence.admission.admission_ref,), REQUIRED_HARDENING_LINEAGE[23:25])

    stage = HARDENING_STAGES[10]
    if not evidence.sealed.eligible:
        return halt(stage, "rejected", ("opaque sealed non-regression evidence is ineligible",), (evidence.sealed.evidence_ref,))
    pass_stage(stage, (evidence.sealed.evidence_ref,), (REQUIRED_HARDENING_LINEAGE[25],))

    stage = HARDENING_STAGES[11]
    if not evidence.review.eligible:
        return halt(stage, "rejected", ("independent review did not accept the unchanged complete proposal",), (evidence.review.receipt_ref,))
    pass_stage(stage, (evidence.review.receipt_ref,), (REQUIRED_HARDENING_LINEAGE[26],))

    stage = HARDENING_STAGES[12]
    pass_stage(stage, (evidence.review.proposal_ref,), (REQUIRED_HARDENING_LINEAGE[27],))
    missing = tuple(sorted(set(contract.required_lineage) - set(recorded_edges)))
    if missing:
        return halt(stage, "rejected", ("lineage closure is incomplete: " + ", ".join(missing),))
    return HardeningDemonstrationResult("accepted", route, receipts, recorded_edges, ())
