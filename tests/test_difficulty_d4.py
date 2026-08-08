"""Capability tests for discovery, causal evidence, Atlas, and suite governance."""

from __future__ import annotations

import pytest

from narrative_game.contracts.canonical import canonical_json
from narrative_game.difficulty import (
    ADMISSION_GATES,
    DISCOVERY_LENSES,
    AtlasRevisionProposal,
    AtlasWorkbench,
    CausalFactor,
    CausalHypothesisSet,
    ChallengeAdmission,
    ChallengeCaseProposal,
    CounterfactualContrast,
    CounterfactualPlan,
    DiscoverySweep,
    FailureClassVersion,
    FailureSignalProposal,
    IncidentAssembly,
    PlannedContrast,
    PublishedFailureAtlas,
    SealedCohort,
    SuiteRegistry,
    SweepCoverage,
    WorkbenchEntry,
    compare_hypothesis_sets,
    corroborate_incident,
    evaluate_atlas_proposal,
    publish_atlas_revision,
    review_atlas_proposal,
    review_owning_layer,
)


REF = lambda value: "sha256:" + value * 64


def _coverage(*, complete=True):
    required = ("structure", "milestones", "terminal", "graph")
    return SweepCoverage(
        required,
        required if complete else required[:2],
        ("knowledge-flow",),
        ("span-10", "span-11"),
        ("searched pre-handoff and post-handoff actions",),
        () if complete else ("terminal",),
    )


def _signal(principal, lens, coverage, *, gap="Avery never acknowledged the transfer"):
    return FailureSignalProposal(
        principal,
        lens,
        "Avery must acknowledge Blake's evidence handoff",
        gap,
        ("span-10", "span-11"),
        "verified",
        ("avery", "blake"),
        (10, 11),
        "handoff-not-completed",
        False,
        ("span-12",),
        ("the acknowledgment may be implicit",),
        "medium",
        coverage.coverage_ref,
        REF("a"),
        "knowledge-flow:handoff-10",
    )


def _sweep(principal, lens, *, signal=True, complete=True, gap=None):
    coverage = _coverage(complete=complete)
    signals = ()
    if signal:
        signals = (_signal(principal, lens, coverage, gap=gap or "Avery never acknowledged the transfer"),)
    return DiscoverySweep(
        REF("e"),
        principal,
        lens,
        "complete" if complete else "partial",
        coverage,
        signals,
        (),
        None if complete else "cursor:region=terminal;span=12",
        REF("b"),
    )


def _assembly(sweeps):
    refs = tuple(sweep.signals[0].signal_ref for sweep in sweeps if sweep.signals)
    return IncidentAssembly(
        REF("e"),
        "assembler",
        refs,
        (),
        "Avery must acknowledge Blake's evidence handoff",
        "knowledge-flow:handoff-10",
        (),
        None,
        REF("c"),
    )


def test_five_truth_blind_sweeps_require_coverage_and_independent_corroboration():
    """difficulty.d4.discovery: truth-blind coverage and conflict remain explicit."""
    sweeps = tuple(
        _sweep(f"discoverer-{index}", lens, signal=index < 2)
        for index, lens in enumerate(DISCOVERY_LENSES)
    )
    assert len(sweeps) == 5
    assert all(item.status == "complete" and item.coverage.complete for item in sweeps)
    corroborated = corroborate_incident(_assembly(sweeps), sweeps)
    assert corroborated.status == "eligible-for-semantic-interpretation"
    assert len(corroborated.corroborating_signal_refs) == 2

    partial = _sweep("partial-discoverer", DISCOVERY_LENSES[1], complete=False)
    first = sweeps[0]
    unresolved = corroborate_incident(_assembly((first, partial)), (first, partial))
    assert unresolved.status == "unresolved"
    assert partial.continuation_cursor == "cursor:region=terminal;span=12"

    conflict = _sweep(
        "conflicting-discoverer",
        DISCOVERY_LENSES[1],
        gap="Avery acknowledged the transfer but rejected its relevance",
    )
    conflicting = corroborate_incident(_assembly((first, conflict)), (first, conflict))
    assert conflicting.status == "unresolved"
    assert "materially different" in conflicting.disagreements[0]


def _factor():
    return CausalFactor(
        "uncompleted-handoff",
        "interaction",
        "contributing",
        (REF("1"),),
        (REF("2"),),
        ("host timing", "evidence ambiguity"),
        "medium",
        "making acknowledgment explicit should restore the downstream claim",
    )


def _hypothesis(principal, *, extra=()):
    return CausalHypothesisSet(
        REF("i"),
        principal,
        (_factor(), *extra),
        (("uncompleted-handoff", "host-timing"),),
        ("host timing", "evidence ambiguity"),
        "material alternatives remain",
        REF("r"),
    )


def test_isolated_attributions_preserve_alternatives_and_require_causal_corroboration():
    """difficulty.d4.attribution: agreement ranks tests but cannot certify ownership."""
    left = _hypothesis("attribution-a")
    right = _hypothesis("attribution-b")
    agreement = compare_hypothesis_sets(left, right)
    assert agreement.prioritized_factor_ids == ("uncompleted-handoff",)
    assert agreement.establishes_ownership is False

    direct = PlannedContrast(
        "direct",
        "communication-condition",
        "uncompleted-handoff",
        "implicit acknowledgment",
        "explicit acknowledgment",
        ("release", "panel", "proof path"),
        "downstream claim becomes supported",
        "direct-manipulation",
    )
    alternative = PlannedContrast(
        "alternative",
        "host-policy",
        "uncompleted-handoff",
        "passive host",
        "active host",
        ("release", "panel", "communication condition"),
        "host activity alone does not restore the unsupported claim",
        "alternative-separating",
    )
    plan = CounterfactualPlan(
        REF("i"),
        "planner",
        (left.hypothesis_set_ref, right.hypothesis_set_ref),
        (left.principal, right.principal),
        (direct, alternative),
        ("non-manifesting baseline",),
        ("two orthogonal predictions resolved", "budget exhausted"),
        REF("p"),
    )
    direct_result = CounterfactualContrast(
        plan.plan_ref,
        direct,
        REF("3"),
        REF("4"),
        "downstream claim became supported",
        True,
        (("release", True), ("panel", True), ("proof path", True)),
        REF("5"),
    )
    one_only = review_owning_layer(
        plan=plan,
        contrasts=(direct_result,),
        factor=_factor(),
        interpretation_principals=("interpreter-a", "interpreter-b"),
        reviewer_principal="reviewer",
        review_receipt_ref=REF("6"),
        unresolved_alternatives=("host timing",),
    )
    assert one_only.status == "unresolved"
    alternative_result = CounterfactualContrast(
        plan.plan_ref,
        alternative,
        REF("3"),
        REF("7"),
        "host activity alone did not restore the claim",
        True,
        (("release", True), ("panel", True), ("communication condition", True)),
        REF("8"),
    )
    supported = review_owning_layer(
        plan=plan,
        contrasts=(direct_result, alternative_result),
        factor=_factor(),
        interpretation_principals=("interpreter-a", "interpreter-b"),
        reviewer_principal="reviewer",
        review_receipt_ref=REF("6"),
        unresolved_alternatives=("evidence ambiguity",),
    )
    assert supported.status == "partially-attributed"
    assert supported.unresolved_alternatives == ("evidence ambiguity",)


def _promoted_class(*, complete=True):
    return FailureClassVersion(
        "coordination.uncompleted-handoff",
        "1.0.0",
        "promoted",
        "An evidence transfer is initiated but its required uptake never completes.",
        ("sender transfers evidence; receiver must use or acknowledge it",),
        ("receiver explicitly rejects a non-required suggestion",),
        ("transfer recorded without a downstream acknowledgment",),
        ("distinguish missing disclosure from missing uptake",) if complete else (),
        ("receiver acknowledges and deliberately rejects relevance",) if complete else (),
        REF("d") if complete else None,
        (REF("f"),) if complete else (),
        (REF("n"),) if complete else (),
        (REF("1"), REF("2"), REF("3")),
        ("seed", "host-policy"),
    )


def _proposal(parent, *, complete=True):
    return AtlasRevisionProposal(
        parent.atlas_ref,
        "1.1.0",
        "curator",
        ("discoverer", "attribution-a"),
        "add",
        _promoted_class(complete=complete),
        (REF("i"), REF("j"), REF("k")),
        (REF("x"),) if complete else (),
        (REF("u"),),
        (),
        REF("s") if complete else None,
        (REF("r"),),
    )


def test_atlas_promotion_requires_fixtures_rerunnable_measurement_and_independent_review():
    """difficulty.d4.atlas-promotion: Workbench research cannot self-publish."""
    parent = PublishedFailureAtlas("1.0.0", None, (), (), REF("0"))
    proposal = _proposal(parent)
    eligibility = evaluate_atlas_proposal(proposal)
    assert eligibility.eligible
    review = review_atlas_proposal(
        proposal,
        eligibility,
        reviewer_principal="independent-reviewer",
        accept=True,
        disagreements=(),
        review_receipt_ref=REF("v"),
    )
    published = publish_atlas_revision(
        parent,
        proposal,
        eligibility,
        review,
        transition_receipt_ref=REF("t"),
    )
    assert published.parent_atlas_ref == parent.atlas_ref
    assert published.class_versions == (proposal.proposed_class,)

    incomplete = _proposal(parent, complete=False)
    rejected_eligibility = evaluate_atlas_proposal(incomplete)
    assert not rejected_eligibility.eligible
    assert any("rerunnable-measurement" in item for item in rejected_eligibility.findings)
    rejected_review = review_atlas_proposal(
        incomplete,
        rejected_eligibility,
        reviewer_principal="independent-reviewer",
        accept=True,
        disagreements=("promotion package is incomplete",),
        review_receipt_ref=REF("w"),
    )
    assert rejected_review.decision == "reject"
    with pytest.raises(ValueError, match="eligible independently accepted"):
        publish_atlas_revision(
            parent,
            incomplete,
            rejected_eligibility,
            rejected_review,
            transition_receipt_ref=REF("z"),
        )

    workbench = AtlasWorkbench().append(
        WorkbenchEntry("failed-promotion", "failed-proposal", incomplete.proposal_ref, "curator", (), (REF("w"),))
    )
    assert len(workbench.entries) == 1
    assert parent.class_versions == ()


def _admission(case_ref):
    proposal = ChallengeCaseProposal(
        REF("f"),
        REF("g"),
        "designer",
        "require an explicit evidence-uptake acknowledgment",
        ("solvability", "authorization", "no answer leakage"),
        REF("h"),
        REF("i"),
        ("authorized investigators can establish the final claim",),
        REF("o"),
        "an incomplete handoff blocks one otherwise available proof path",
        REF("c"),
        REF("t"),
        REF("p"),
        REF("r"),
    )
    return ChallengeAdmission(
        case_ref,
        proposal.proposal_ref,
        proposal.designer_principal,
        ("solver-a", "solver-b"),
        "adversarial-reviewer",
        {gate: True for gate in ADMISSION_GATES},
        {gate: (REF(hex(index + 1)[2:]),) for index, gate in enumerate(ADMISSION_GATES)},
        (),
        REF("a"),
    )


def test_suite_bindings_are_immutable_one_way_and_sealed_cohorts_are_single_use():
    """difficulty.d4.suite-binding: exposure and reuse cannot manufacture Standing."""
    development_case = REF("1")
    development = SuiteRegistry().bind(
        case_ref=development_case,
        suite="development",
        curator_principal="developer",
    )
    with pytest.raises(ValueError, match="immutable"):
        development.bind(
            case_ref=development_case,
            suite="sealed-standing",
            curator_principal="sealed-curator",
            admission=_admission(development_case),
            independently_instantiated=True,
        )

    generated_case = REF("2")
    generated = development.bind(
        case_ref=generated_case,
        suite="generated-challenge",
        curator_principal="challenge-curator",
        admission=_admission(generated_case),
    )
    sealed_case = REF("3")
    sealed = generated.bind(
        case_ref=sealed_case,
        suite="sealed-standing",
        curator_principal="sealed-curator",
        admission=_admission(sealed_case),
        independently_instantiated=True,
    )
    exposed = sealed.retire_exposed_sealed(
        case_ref=sealed_case,
        curator_principal="sealed-curator",
        exposure_receipt_ref=REF("e"),
    )
    assert exposed.current_binding(sealed_case).suite == "development"
    assert exposed.current_binding(sealed_case).source_binding_ref == sealed.current_binding(sealed_case).binding_ref

    cohort = SealedCohort("cohort-1", sealed.registry_ref, 12, "framework-promotion-v1")
    consumed = cohort.consume(attempt_ref=REF("p"), aggregate_receipt_ref=REF("q"))
    assert consumed.consumed
    with pytest.raises(ValueError, match="single-use"):
        consumed.consume(attempt_ref=REF("r"), aggregate_receipt_ref=REF("s"))
    serialized = canonical_json(consumed.to_mapping()).decode()
    assert sealed_case not in serialized and "oracle" not in serialized
