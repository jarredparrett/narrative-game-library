"""Stage 6 authority, blindness, receipt, and standing capability tests."""

from __future__ import annotations

from dataclasses import replace

from narrative_game.climb import (
    Authority,
    Dimension,
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
    validate_climb_bundle,
)


def sha(character: str) -> str:
    return "sha256:" + character * 64


def valid_bundle() -> dict:
    builder = Authority("agent-builder", "agent", "builder", "fixture-builder")
    judge = Authority("agent-judge", "agent", "judge", "fixture-blind-judge")
    reviewer = Authority("human-reviewer", "human", "reviewer", "repository-owner")
    instrument = FrozenInstrument(
        name="complete-experience",
        version="1.0.0",
        scope="worked-release",
        dimensions=(
            Dimension("realism", "Artifact and world realism", 60, {"0": "obvious", "100": "survives expert review"}),
            Dimension("playability", "Playable evidence and pacing", 40, {"0": "blocked", "100": "robust"}),
        ),
        acceptance_rules=({"metric": "overall", "operator": ">=", "value": 70},),
        blind_protocol={"judge_inputs": ["trial-tree", "cover-story"], "forbidden": ["atlas", "answers"]},
        hard_gate_codes=("stage5.access", "stage5.rebuild"),
    )
    build_task = Task(
        "build-child",
        "build",
        sha("a"),
        instrument.instrument_id,
        builder.authority_id,
        (),
        {"requirements": sha("b")},
        "Propose a child that satisfies the translated requirements.",
    )
    blind_task = Task(
        "judge-child",
        "blind-measure",
        sha("c"),
        instrument.instrument_id,
        judge.authority_id,
        (builder.authority_id,),
        {"trial_tree": sha("d")},
        "Judge only the anonymous complete-experience trial tree.",
    )
    builder_receipt = ModelReceipt(
        builder.authority_id,
        "fixture",
        "builder-model",
        "builder-model-v1",
        "builder",
        sha("1"),
        sha("2"),
        sha("3"),
        {"task": sha("4")},
        (sha("5"),),
        sha("6"),
        sha("7"),
        17,
    )
    judge_receipt = ModelReceipt(
        judge.authority_id,
        "fixture",
        "judge-model",
        "judge-model-v1",
        "judge",
        sha("8"),
        sha("9"),
        sha("0"),
        {"trial": sha("d")},
        (),
        sha("e"),
        sha("f"),
        23,
    )
    finding = Finding(
        "artifact.period-language",
        "major",
        "materials/madison-deed-1997",
        "page 1, consideration clause",
        "sum and consideration of $425,000.00",
        "The clause reads as a generated recital rather than the sourced form language.",
    )
    requirement = Requirement(
        "artifact.period-language",
        "Transaction recitals use the sourced form edition's syntax.",
        "The wording exposes the artifact as generated.",
        "Render transaction recitals from the sourced edition-specific template contract.",
        (finding.finding_id,),
    )
    proposal = Proposal(
        build_task.task_id,
        sha("a"),
        sha("c"),
        (requirement.requirement_id,),
        builder.authority_id,
        builder_receipt.receipt_id,
        "Apply the edition-specific recital contract without changing canonical facts.",
    )
    review = HumanReview(
        proposal.proposal_id,
        reviewer.authority_id,
        "approved",
        "The change is bounded to the approved requirement.",
        proposal.requirement_ids,
    )
    transition = Transition(
        proposal.proposal_id,
        review.review_id,
        reviewer.authority_id,
        "main",
        proposal.baseline_draft_ref,
        proposal.proposed_data_ref,
        proposal.proposed_data_ref,
    )
    evaluation = Evaluation(
        blind_task.task_id,
        blind_task.candidate_id,
        instrument.instrument_id,
        "blind",
        (judge.authority_id,),
        (judge_receipt.receipt_id,),
        {"realism": 82, "playability": 88},
        (),
        {"stage5.access": True, "stage5.rebuild": True},
        "pass",
        "machine_qualified",
    )
    exposure = Exposure(
        judge.authority_id,
        sha("d"),
        "trial-tree",
        "blind complete-experience measurement",
        blind_task.task_id,
    )
    standing = StandingAttestation(
        blind_task.candidate_id,
        "machine_qualified",
        (evaluation.evaluation_id,),
        ("model-blind-panel",),
        reviewer.authority_id,
        "Machine-qualified by the frozen blind instrument; no human-play standing claimed.",
    )
    return {
        "authorities": (builder, judge, reviewer),
        "instruments": (instrument,),
        "tasks": (build_task, blind_task),
        "model_receipts": (builder_receipt, judge_receipt),
        "exposures": (exposure,),
        "findings": (finding,),
        "requirements": (requirement,),
        "evaluations": (evaluation,),
        "proposals": (proposal,),
        "reviews": (review,),
        "transitions": (transition,),
        "standings": (standing,),
    }


def codes(bundle: dict) -> set[str]:
    return {item.code for item in validate_climb_bundle(**bundle)}


def test_valid_native_climb_bundle_has_no_findings():
    """stage6.closed-bundle: complete typed lineage validates without ambient state."""
    bundle = valid_bundle()
    assert validate_climb_bundle(**bundle) == ()
    evaluation = bundle["evaluations"][0]
    assert evaluation.overall_score(bundle["instruments"][0]) == 84.4


def test_harvest_cannot_claim_a_score_or_standing():
    """stage6.harvest-honesty: an unblinded harvest moves code, never a rung."""
    bundle = valid_bundle()
    evaluation = replace(bundle["evaluations"][0], mode="harvest", scores={"realism": 90}, claimed_standing="machine_qualified")
    bundle["evaluations"] = (evaluation,)
    bundle["standings"] = ()
    assert "climb.harvest-claimed-score" in codes(bundle)


def test_builder_or_fixer_cannot_judge_its_candidate():
    """stage6.role-blindness: excluded build authorities never certify the child."""
    bundle = valid_bundle()
    builder = bundle["authorities"][0]
    evaluation = replace(bundle["evaluations"][0], judge_authority_ids=(builder.authority_id,))
    bundle["evaluations"] = (evaluation,)
    bundle["standings"] = ()
    assert "climb.self-judging" in codes(bundle)


def test_exposure_ledger_blocks_contaminated_blind_judge():
    """stage6.exposure-ledger: prior answers make a nominally blind score invalid."""
    bundle = valid_bundle()
    exposure = replace(bundle["exposures"][0], category="answer-key")
    bundle["exposures"] = (exposure,)
    assert "climb.blindness-contaminated" in codes(bundle)


def test_requirement_translation_does_not_leak_quote_or_locus():
    """stage6.requirement-translation: builders receive properties, not answers."""
    bundle = valid_bundle()
    finding = bundle["findings"][0]
    leaked = replace(bundle["requirements"][0], builder_brief=f"Fix {finding.quote} at {finding.locus}.")
    bundle["requirements"] = (leaked,)
    bundle["proposals"] = ()
    bundle["reviews"] = ()
    bundle["transitions"] = ()
    assert "climb.answer-leak" in codes(bundle)


def test_only_human_reviewer_can_approve_proposal():
    """stage6.human-authority: agent approval never authorizes canonical change."""
    bundle = valid_bundle()
    agent_review = replace(bundle["reviews"][0], reviewer_authority_id="agent-judge")
    bundle["reviews"] = (agent_review,)
    bundle["transitions"] = ()
    assert "climb.human-authority-required" in codes(bundle)


def test_rejected_review_cannot_authorize_transition():
    """stage6.transition-authority: canonical movement requires exact approval."""
    bundle = valid_bundle()
    review = replace(bundle["reviews"][0], decision="rejected")
    transition = replace(bundle["transitions"][0], review_id=review.review_id)
    bundle["reviews"] = (review,)
    bundle["transitions"] = (transition,)
    assert "climb.unauthorized-transition" in codes(bundle)


def test_model_receipt_requires_exact_provider_model_context_tools_and_outputs():
    """stage6.model-receipt: an invocation without exact hashes is unverifiable."""
    bundle = valid_bundle()
    receipt = replace(bundle["model_receipts"][0], resolved_model="", prompt_hash="unknown")
    bundle["model_receipts"] = (receipt, bundle["model_receipts"][1])
    bundle["proposals"] = ()
    bundle["reviews"] = ()
    bundle["transitions"] = ()
    assert "climb.incomplete-model-receipt" in codes(bundle)


def test_passing_evaluation_cannot_hide_hard_gate_regression():
    """stage6.no-regression: improvement never waives an accepted hard gate."""
    bundle = valid_bundle()
    evaluation = replace(bundle["evaluations"][0], hard_gate_results={"stage5.access": False, "stage5.rebuild": True})
    bundle["evaluations"] = (evaluation,)
    bundle["standings"] = ()
    assert "climb.hard-gate-regression" in codes(bundle)


def test_model_only_evidence_cannot_claim_accepted_standing():
    """stage6.standing-honesty: Accepted remains gated by fresh human evidence."""
    bundle = valid_bundle()
    standing = replace(bundle["standings"][0], level="accepted", evidence_kinds=("model-blind-panel",))
    bundle["standings"] = (standing,)
    assert "climb.unsupported-standing" in codes(bundle)


def test_blind_evaluation_requires_exact_judge_receipts_and_exposure_ledger():
    """stage6.blind-inputs: every judge invocation records both inputs and outputs."""
    bundle = valid_bundle()
    bundle["exposures"] = ()
    evaluation = replace(bundle["evaluations"][0], model_receipt_ids=(bundle["model_receipts"][0].receipt_id,))
    bundle["evaluations"] = (evaluation,)
    bundle["standings"] = ()
    assert {"climb.missing-exposure-ledger", "climb.judge-receipt-mismatch"} <= codes(bundle)
