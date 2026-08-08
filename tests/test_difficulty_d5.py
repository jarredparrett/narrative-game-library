"""Capability tests for the failure-driven task-hardening path."""

from __future__ import annotations

from dataclasses import replace

import pytest

from narrative_game.difficulty import (
    FORBIDDEN_HARDENING_MUTATIONS,
    HARDENING_STAGES,
    PREFLIGHT_GATES,
    PROTECTED_HARDENING_INVARIANTS,
    REQUIRED_HARDENING_LINEAGE,
    ArtifactPreflightAttestation,
    ChallengePreflight,
    FailureEvidenceSummary,
    FinalChallengeAdmission,
    HardeningContract,
    HardeningEvidence,
    HardeningReview,
    MatchedHardeningComparison,
    SealedGovernanceEvidence,
    TaskHardeningRequirement,
    route_failure,
    run_hardening_demonstration,
)
from narrative_game.generation import propose_hardening_child


REF = lambda value: "sha256:" + value * 64


def _failure(**overrides):
    values = {
        "incident_ref": REF("i"),
        "owning_layer_finding_ref": REF("o"),
        "corroborated": True,
        "attribution_principals": ("attribution-a", "attribution-b"),
        "owning_layer_status": "accepted",
        "cause_layers": ("coordination",),
        "material_defect_layers": (),
        "successful_contrast_refs": (REF("1"), REF("2")),
        "unresolved_branches": (),
        "controlled_unresolved_branches": (),
    }
    values.update(overrides)
    return FailureEvidenceSummary(**values)


def _requirement(**overrides):
    values = {
        "source_failure_class_ref": REF("f"),
        "owning_layer_finding_ref": REF("o"),
        "capability_demand": "The team must transfer and corroborate complementary evidence before resolution.",
        "challenge_mechanism": "Two proof-critical fragments begin with different authorized Seats.",
        "allowed_mutation_surface": ("evidence-distribution", "dependency-topology", "role-obligations"),
        "selected_mutations": ("evidence-distribution", "dependency-topology", "role-obligations"),
        "forbidden_mutations": FORBIDDEN_HARDENING_MUTATIONS,
        "protected_invariants": PROTECTED_HARDENING_INVARIANTS,
        "expected_manifestation": "proof-critical handoff omission increases under the fixed Panel",
        "non_manifesting_control": "give both fragments to one authorized Seat while preserving facts and oracle",
        "target_contract_ref": REF("t"),
        "generation_intent_ref": REF("g"),
        "lineage_refs": (REF("i"), REF("o"), REF("f")),
    }
    values.update(overrides)
    return TaskHardeningRequirement(**values)


def _preflight(**overrides):
    gates = {name: True for name in PREFLIGHT_GATES}
    values = {
        "child_release_ref": REF("c"),
        "gate_results": gates,
        "gate_evidence_refs": {name: (REF(hex(index + 1)[2:]),) for index, name in enumerate(PREFLIGHT_GATES)},
        "expected_artifact_ids": ("lease", "survey"),
        "artifact_attestations": (
            ArtifactPreflightAttestation("lease", REF("a"), True, "accepted"),
            ArtifactPreflightAttestation("survey", REF("b"), True, "accepted"),
        ),
        "designer_principal": "challenge-designer",
        "generation_builder_principal": "generation-builder",
        "generation_reviewer_principal": "generation-reviewer",
        "solver_principals": ("solver-a", "solver-b"),
        "leakage_reviewer_principal": "leakage-reviewer",
        "unresolved_hard_findings": (),
    }
    values.update(overrides)
    return ChallengePreflight(**values)


def _comparison(**overrides):
    values = {
        "baseline_profile_ref": REF("p"),
        "child_profile_ref": REF("q"),
        "control_profile_ref": REF("r"),
        "baseline_panel_ref": REF("e"),
        "child_panel_ref": REF("e"),
        "baseline_instrument_ref": REF("n"),
        "child_instrument_ref": REF("n"),
        "target_contract_ref": REF("t"),
        "precommitted_assignments_complete": True,
        "invalid_episodes_counted_as_failures": False,
        "target_dominance_outcome": "child-dominates",
        "child_classification": "supported-target-band",
        "targeted_delta_interval": (0.12, 0.28),
        "control_delta_interval": (-0.03, 0.04),
        "hard_gate_results": {
            "episode-validity": True,
            "integrity": True,
            "coherence": True,
            "authorization": True,
            "leakage-resistance": True,
            "artifact-realism": True,
            "narrative-quality": True,
        },
        "no_gating_regression": True,
    }
    values.update(overrides)
    return MatchedHardeningComparison(**values)


def _reference():
    contract = HardeningContract(REF("e"), REF("n"), REF("a"), REF("t"))
    failure = _failure()
    requirement = _requirement()
    preflight = _preflight()
    comparison = _comparison()
    admission = FinalChallengeAdmission(
        preflight.preflight_ref,
        comparison.comparison_ref,
        REF("j"),
        REF("v"),
        REF("s"),
        "generated-challenge",
        preflight.child_release_ref,
    )
    contributors = (
        preflight.designer_principal,
        preflight.generation_builder_principal,
        preflight.generation_reviewer_principal,
        *preflight.solver_principals,
        preflight.leakage_reviewer_principal,
    )
    evidence = HardeningEvidence(
        True,
        True,
        contract.panel_ref,
        contract.instrument_ref,
        failure,
        route_failure(failure),
        requirement.source_failure_class_ref,
        "promoted",
        contract.atlas_ref,
        True,
        requirement,
        preflight.child_release_ref,
        REF("j"),
        preflight.generation_builder_principal,
        preflight.generation_reviewer_principal,
        preflight,
        True,
        contract.panel_ref,
        contract.instrument_ref,
        comparison,
        admission,
        SealedGovernanceEvidence(REF("w"), REF("w"), REF("z"), None, False, "pass", False),
        HardeningReview(
            REF("h"),
            "final-reviewer",
            contributors,
            "accept",
            False,
            {"complete-lineage": True, "sealed-non-regression": True},
            REF("y"),
        ),
        REQUIRED_HARDENING_LINEAGE,
    )
    return contract, evidence


def test_failure_routing_selects_harden_repair_or_quarantine_without_favorable_default():
    """difficulty.d5.routing: only clean supported capability evidence may harden."""
    assert route_failure(_failure()).route == "harden"
    for layer in ("game", "artifact", "runtime", "provider", "evaluator"):
        decision = route_failure(
            _failure(cause_layers=(layer,), material_defect_layers=(layer,))
        )
        assert decision.route == "repair"
        assert layer in decision.reasons[0]
    assert route_failure(_failure(owning_layer_status="unresolved")).route == "quarantine"
    assert route_failure(_failure(successful_contrast_refs=(REF("1"),))).route == "quarantine"
    partial = _failure(
        owning_layer_status="partially-attributed",
        unresolved_branches=("game-affordance",),
    )
    assert route_failure(partial).route == "quarantine"
    controlled = replace(partial, controlled_unresolved_branches=("game-affordance",))
    assert route_failure(controlled).route == "harden"


def test_hardening_state_machine_accepts_reference_path_and_rejects_every_named_boundary_case():
    """difficulty.d5.state-machine: thirteen receipts compose one fail-closed path."""
    contract, evidence = _reference()
    accepted = run_hardening_demonstration(contract, evidence)
    assert accepted.status == "accepted"
    assert tuple(item.stage for item in accepted.receipts) == HARDENING_STAGES
    assert len(accepted.receipts) == 13
    assert set(accepted.lineage_edges) == set(REQUIRED_HARDENING_LINEAGE)

    game_failure = _failure(cause_layers=("game",), material_defect_layers=("game",))
    repair = run_hardening_demonstration(
        contract,
        replace(evidence, failure=game_failure, route=route_failure(game_failure)),
    )
    assert repair.status == "repair-required"
    assert repair.receipts[-1].stage == "failure-routing"

    unresolved = _failure(owning_layer_status="unresolved", successful_contrast_refs=(REF("1"),))
    quarantine = run_hardening_demonstration(
        contract,
        replace(evidence, failure=unresolved, route=route_failure(unresolved)),
    )
    assert quarantine.status == "quarantined"

    cases = (
        (replace(evidence, failure_class_stage="proposed"), "class-promotion"),
        (replace(evidence, failure_class_atlas_ref=REF("x")), "class-promotion"),
        (replace(evidence, requirement=_requirement(target_contract_ref=REF("x"))), "requirement-freeze"),
        (replace(evidence, requirement=_requirement(owning_layer_finding_ref=REF("x"))), "requirement-freeze"),
        (replace(evidence, preflight=_preflight(gate_results={**_preflight().gate_results, "solver-b-valid-solution": False})), "challenge-preflight"),
        (replace(evidence, preflight=_preflight(gate_results={**_preflight().gate_results, "leakage-review": False})), "challenge-preflight"),
        (replace(evidence, preflight=_preflight(artifact_attestations=(ArtifactPreflightAttestation("lease", REF("a"), True, "accepted"), ArtifactPreflightAttestation("survey", REF("b"), True, "rejected")))), "challenge-preflight"),
        (replace(evidence, child_panel_ref=REF("d")), "matched-remeasurement"),
        (replace(evidence, child_instrument_ref=REF("d")), "matched-remeasurement"),
        (replace(evidence, comparison=_comparison(precommitted_assignments_complete=False)), "target-comparison"),
        (replace(evidence, comparison=_comparison(invalid_episodes_counted_as_failures=True)), "target-comparison"),
        (replace(evidence, comparison=_comparison(child_classification="too-hard")), "target-comparison"),
        (replace(evidence, comparison=_comparison(targeted_delta_interval=(-0.01, 0.08))), "target-comparison"),
        (replace(evidence, comparison=_comparison(control_delta_interval=(0.05, 0.18))), "target-comparison"),
        (replace(evidence, comparison=_comparison(target_contract_ref=REF("x"))), "target-comparison"),
        (replace(evidence, admission=replace(evidence.admission, suite="development")), "challenge-admission"),
        (replace(evidence, sealed=replace(evidence.sealed, aggregate_result="fail")), "sealed-non-regression"),
        (replace(evidence, sealed=SealedGovernanceEvidence(REF("w"), REF("x"), None, REF("k"), False, "pass", False)), "sealed-non-regression"),
        (replace(evidence, review=replace(evidence.review, reviewer_principal=evidence.review.contributor_principals[0])), "independent-review"),
        (replace(evidence, lineage_edges=tuple(item for item in evidence.lineage_edges if item != "incident->semantic-interpretation")), "hardening-transition"),
    )
    for broken, expected_stage in cases:
        result = run_hardening_demonstration(contract, broken)
        assert result.status == "rejected"
        assert result.receipts[-1].stage == expected_stage

    with pytest.raises(ValueError, match="forbidden mutation"):
        _requirement(selected_mutations=("ambiguity",))


class _Ledger:
    def __init__(self):
        self.records = []

    def register(self, value, *, actor, idempotency_key):
        self.records.append((value, actor, idempotency_key))


class _ExistingExperiment:
    def __init__(self):
        self.ledger = _Ledger()
        self.call = None

    def propose_revision_from_requirements(self, adapter, **kwargs):
        self.call = (adapter, kwargs)
        return {"child_candidate_id": "candidate:one-child", "requirement_ids": kwargs["requirement_ids"]}


def test_builder_receives_answer_safe_requirement_and_existing_generator_produces_one_child(tmp_path):
    """difficulty.d5.builder-boundary: hardening reuses the existing proposal path."""
    experiment = _ExistingExperiment()
    requirement = _requirement()
    result = propose_hardening_child(
        experiment,
        object(),
        requirement=requirement,
        baseline_binding_id="binding:baseline",
        task_key="hardening-child-1",
        authority_id="builder-authority",
        principal="builder-principal",
        requested_model="gpt-5.6-sol",
        driver=object(),
        scratch_root=tmp_path,
        seed=31,
    )
    assert result["child_candidate_id"] == "candidate:one-child"
    assert len(result["requirement_ids"]) == 4
    _, kwargs = experiment.call
    assert kwargs["binding_id"] == "binding:baseline"
    assert kwargs["human_direction"] is None
    serialized = str([item.to_mapping() for item, _, _ in experiment.ledger.records])
    assert requirement.owning_layer_finding_ref not in serialized
    assert requirement.lineage_refs[0] not in serialized
    assert "canonical world truth" not in serialized.casefold()


def test_challenge_preflight_requires_two_solvers_oracle_leakage_review_and_all_artifact_attestations():
    """difficulty.d5.preflight: an unmeasured or failed artifact quarantines the child."""
    assert _preflight().eligible
    failed_solver = _preflight(gate_results={**_preflight().gate_results, "solver-a-valid-solution": False})
    assert not failed_solver.eligible
    failed_artifact = _preflight(
        artifact_attestations=(
            ArtifactPreflightAttestation("lease", REF("a"), True, "accepted"),
            ArtifactPreflightAttestation("survey", REF("b"), True, "rejected"),
        )
    )
    assert not failed_artifact.eligible
    missing_oracle = _preflight(gate_results={**_preflight().gate_results, "oracle-validation": False})
    assert not missing_oracle.eligible
    leakage = _preflight(gate_results={**_preflight().gate_results, "leakage-review": False})
    assert not leakage.eligible
    with pytest.raises(ValueError, match="exact Artifact Attestation membership"):
        _preflight(artifact_attestations=_preflight().artifact_attestations[:1])


def test_target_dominance_requires_matched_uncertainty_movement_control_discrimination_and_no_regression():
    """difficulty.d5.matched-comparison: no scalar or invalid-run shortcut selects a child."""
    assert _comparison().eligible
    assert not _comparison(targeted_delta_interval=(-0.02, 0.09)).eligible
    assert not _comparison(control_delta_interval=(0.04, 0.16)).eligible
    assert not _comparison(child_panel_ref=REF("x")).eligible
    assert not _comparison(child_instrument_ref=REF("x")).eligible
    assert not _comparison(precommitted_assignments_complete=False).eligible
    assert not _comparison(invalid_episodes_counted_as_failures=True).eligible
    assert not _comparison(no_gating_regression=False).eligible
    assert not _comparison(hard_gate_results={**_comparison().hard_gate_results, "artifact-realism": False}).eligible
