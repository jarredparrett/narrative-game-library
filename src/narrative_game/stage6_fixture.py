"""One persisted, human-governed climb over The Ashwood Ledger."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from narrative_game.authoring import parse_game_definition
from narrative_game.climb import (
    Authority,
    ClimbLedger,
    Dimension,
    Evaluation,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReview,
    Requirement,
    StandingAttestation,
    Task,
)
from narrative_game.contracts import canonical_json, digest_bytes, digest_json
from narrative_game.narrative import validate_facilitated_investigation
from narrative_game.workspace import Workspace


DEFAULT_SOURCE = Path(__file__).resolve().parent / "examples" / "ashwood-ledger"


@dataclass(frozen=True)
class ClimbResult:
    workspace: Workspace
    ledger: ClimbLedger
    baseline_candidate_id: str
    child_candidate_id: str
    baseline_evaluation: Evaluation
    child_evaluation: Evaluation
    output_root: Path
    summary: Mapping[str, Any]


def _component_lock() -> dict[str, Any]:
    return {
        "components": [
            {
                "id": "narrative-game-library",
                "version": "0.6.0",
                "implementation": digest_bytes(b"stage6-native-agentic-climb"),
            }
        ]
    }


def _materialize_game(source: Mapping[str, Any], source_root: Path):
    mapping = deepcopy(source)
    mapping.pop("authoring_schema_version", None)
    mapping.pop("displayed_claims", None)
    mapping.pop("physical_accessibility_renditions", None)
    for resource in mapping["kernel"]["resources"]:
        if "source_path" in resource:
            resource["content_hash"] = digest_bytes((source_root / resource.pop("source_path")).read_bytes())
        else:
            request = resource.pop("artifact_request")
            resource["content_hash"] = digest_json(
                {"persisted_stage5_artifact_request": request, "seed": 1997}
            )
    return parse_game_definition(canonical_json(mapping))


def _hard_gates(source: Mapping[str, Any], source_root: Path) -> dict[str, bool]:
    game = _materialize_game(source, source_root)
    replayed = parse_game_definition(canonical_json(game.to_mapping()))
    return {
        "stage5.access": validate_facilitated_investigation(game) == (),
        "stage5.rebuild": replayed.content_hash == game.content_hash,
    }


def _trial_tree(candidate_id: str, source: Mapping[str, Any]) -> dict[str, Any]:
    narrative = source["narrative"]
    labels = {
        item["id"]: item["label"] for item in source["kernel"]["resources"]
    }
    evidence_resources = {
        item["id"]: item["resource_id"] for item in narrative["evidence"]
    }
    return {
        "schema_version": "0.6",
        "candidate": candidate_id,
        "cover_story": "Evaluate this anonymous two-seat archival investigation as a complete player experience.",
        "premise": narrative["direction"]["premise"],
        "seat_labels": [item["label"] for item in source["kernel"]["seats"]],
        "phase_labels": [item["label"] for item in narrative["phases"]],
        "reveals": [
            {
                "reveal_id": item["id"],
                "phase_id": item["phase_id"],
                "material": labels[evidence_resources[item["evidence_id"]]],
                "audience_count": len(item["audience_seat_ids"]),
            }
            for item in narrative["reveals"]
        ],
        "resolution_prompt": narrative["resolution"]["prompt"],
    }


def _record_invocation(
    ledger: ClimbLedger,
    *,
    authority: Authority,
    task: Task,
    trial_ref: str,
    parsed_output: Mapping[str, Any],
    key: str,
):
    return ledger.record_model_invocation(
        authority_id=authority.authority_id,
        provider="offline-fixture",
        requested_model="recorded-blind-judge",
        resolved_model=f"recorded-blind-judge-{key}-v1",
        role=authority.role,
        prompt_hash=digest_bytes(b"stage6 frozen complete-experience blind prompt v1"),
        context_hash=digest_bytes(canonical_json({"task": task.to_mapping(), "trial_ref": trial_ref})),
        tool_contract_hash=digest_bytes(b"stage6 evaluation schema v1"),
        input_hashes={"task": digest_json(task.to_mapping()), "trial_tree": trial_ref},
        tool_receipt_hashes=(),
        raw_output=canonical_json(parsed_output),
        parsed_output=parsed_output,
        seed=1997,
        actor=f"agent:{authority.principal}",
        idempotency_key=f"model-{key}",
    )


def run(root: str | Path, *, source_root: str | Path = DEFAULT_SOURCE) -> ClimbResult:
    """Persist one complete baseline-to-child loop in a new user-owned directory."""
    root = Path(root)
    source_root = Path(source_root)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"Stage 6 output is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    source = json.loads((source_root / "scenario.json").read_bytes())
    workspace = Workspace.create(root / "workspace", workspace_id="ashwood-ledger-stage6", actor="human:fixture-maker")
    baseline_head = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={"title": "The Ashwood Ledger", "human_readable_source": source},
        reason="materialize the accepted Stage 5 source as the climb baseline",
        actor="human:fixture-maker",
        component_lock=_component_lock(),
        operation_receipt={"operation": "stage6.baseline", "source_hash": digest_json(source)},
        idempotency_key="baseline-draft",
    )
    baseline_candidate = workspace.freeze_candidate(
        branch="main",
        expected_head=baseline_head,
        actor="human:fixture-maker",
        idempotency_key="baseline-candidate",
    )
    ledger = ClimbLedger(workspace)

    builder = Authority("ashwood-builder", "agent", "builder", "ashwood-builder-model")
    baseline_judge = Authority("ashwood-baseline-judge", "agent", "judge", "ashwood-blind-judge-a")
    child_judge = Authority("ashwood-child-judge", "agent", "judge", "ashwood-blind-judge-b")
    reviewer = Authority("ashwood-human-reviewer", "human", "reviewer", "fixture-reviewer")
    instrument = FrozenInstrument(
        "complete-experience",
        "1.0.0",
        "two-seat-facilitated-investigation",
        (
            Dimension("world_realism", "The scenario behaves like a coherent lived world.", 35, {"0": "generated", "100": "expert-resistant"}),
            Dimension("deduction_quality", "Evidence supports earned, non-automatic inference.", 40, {"0": "blocked or automatic", "100": "robust inference"}),
            Dimension("playability", "Pacing, access, and recovery support complete play.", 25, {"0": "unplayable", "100": "resilient"}),
        ),
        (
            {"metric": "overall", "operator": ">=", "value": 75},
            {"metric": "hard_gates", "operator": "all", "value": True},
        ),
        {
            "allowed": ["anonymous-trial-tree", "cover-story", "frozen-instrument"],
            "forbidden": ["answer-key", "atlas", "builder-rationale", "prior-score", "trusted-truth"],
        },
        ("stage5.access", "stage5.rebuild"),
    )
    for index, authority in enumerate((builder, baseline_judge, child_judge, reviewer), 1):
        ledger.register(authority, actor="human:fixture-maker", idempotency_key=f"authority-{index}")
    ledger.register(instrument, actor="human:fixture-maker", idempotency_key="instrument")

    baseline_trial_ref = workspace.store.put_json(_trial_tree(baseline_candidate, source))
    baseline_task = Task(
        "blind-baseline",
        "blind-measure",
        baseline_candidate,
        instrument.instrument_id,
        baseline_judge.authority_id,
        (builder.authority_id,),
        {"trial_tree": baseline_trial_ref},
        "Measure only the anonymous trial tree with the frozen instrument.",
    )
    ledger.register(baseline_task, actor="human:fixture-maker", idempotency_key="task-baseline")
    ledger.register(
        Exposure(baseline_judge.authority_id, baseline_trial_ref, "trial-tree", "baseline blind measurement", baseline_task.task_id),
        actor="system:exposure-recorder",
        idempotency_key="exposure-baseline",
    )
    baseline_output = {
        "scores": {"world_realism": 72, "deduction_quality": 58, "playability": 74},
        "outcome": "fail",
        "finding": {
            "requirement_code": "world.reveal-sequencing",
            "resource_path": "trial-tree.json",
            "locus": "reveal-interview",
            "quote": "reveal-interview is available in opening",
        },
    }
    baseline_receipt = _record_invocation(
        ledger,
        authority=baseline_judge,
        task=baseline_task,
        trial_ref=baseline_trial_ref,
        parsed_output=baseline_output,
        key="baseline",
    )
    finding = Finding(
        "world.reveal-sequencing",
        "major",
        "trial-tree.json",
        "reveal-interview",
        "reveal-interview is available in opening",
        "The closing interview corroborates the insider theory before players have tested competing explanations.",
    )
    ledger.register(finding, actor="agent:ashwood-blind-judge-a", idempotency_key="finding-baseline")
    baseline_evaluation = Evaluation(
        baseline_task.task_id,
        baseline_candidate,
        instrument.instrument_id,
        "blind",
        (baseline_judge.authority_id,),
        (baseline_receipt.record_id,),
        baseline_output["scores"],
        (finding.finding_id,),
        _hard_gates(source, source_root),
        "fail",
    )
    ledger.register(baseline_evaluation, actor="agent:ashwood-blind-judge-a", idempotency_key="evaluation-baseline")

    requirement = Requirement(
        "world.reveal-sequencing",
        "A corroborating witness account arrives only after players can maintain at least two live explanations.",
        "Premature corroboration turns the central inference into confirmation.",
        "Delay one corroborating witness material until the investigation phase without changing truth, access, or proof redundancy.",
        (finding.finding_id,),
    )
    ledger.register(requirement, actor="human:fixture-maker", idempotency_key="requirement")
    build_task = Task(
        "repair-reveal-sequencing",
        "build",
        baseline_candidate,
        instrument.instrument_id,
        builder.authority_id,
        (baseline_judge.authority_id, child_judge.authority_id),
        {"requirement": ledger.get("requirement", requirement.requirement_id).record_ref},
        requirement.builder_brief,
    )
    ledger.register(build_task, actor="human:fixture-maker", idempotency_key="task-build")
    child_source = deepcopy(source)
    interview = next(item for item in child_source["narrative"]["reveals"] if item["id"] == "reveal-interview")
    interview["phase_id"] = "investigation"
    child_data = {"title": "The Ashwood Ledger", "human_readable_source": child_source}
    builder_output = {
        "decision": "propose",
        "changed_property": "one reveal phase",
        "hard_gates": _hard_gates(child_source, source_root),
    }
    builder_receipt = _record_invocation(
        ledger,
        authority=builder,
        task=build_task,
        trial_ref=ledger.get("requirement", requirement.requirement_id).record_ref,
        parsed_output=builder_output,
        key="builder",
    )
    proposal = ledger.record_proposal(
        task_id=build_task.task_id,
        baseline_draft_ref=baseline_head,
        proposed_data=child_data,
        requirement_ids=(requirement.requirement_id,),
        builder_authority_id=builder.authority_id,
        model_receipt_id=builder_receipt.record_id,
        rationale="Move one corroborating account later while preserving all canonical facts and proof paths.",
        actor="agent:ashwood-builder-model",
        idempotency_key="proposal-child",
    )
    review = HumanReview(
        proposal.record_id,
        reviewer.authority_id,
        "approved",
        "Fixture human review confirms the proposal changes only the translated reveal-sequencing requirement.",
        (requirement.requirement_id,),
    )
    ledger.register(review, actor="human:fixture-reviewer", idempotency_key="review-child")
    transition = ledger.apply_approved_transition(
        proposal_id=proposal.record_id,
        review_id=review.review_id,
        branch="main",
        component_lock=_component_lock(),
        idempotency_key="transition-child",
    )
    child_candidate = workspace.freeze_candidate(
        branch="main",
        expected_head=transition.child_draft_ref,
        actor="human:fixture-reviewer",
        idempotency_key="child-candidate",
    )

    child_trial_ref = workspace.store.put_json(_trial_tree(child_candidate, child_source))
    child_task = Task(
        "blind-child",
        "blind-measure",
        child_candidate,
        instrument.instrument_id,
        child_judge.authority_id,
        (builder.authority_id, baseline_judge.authority_id),
        {"trial_tree": child_trial_ref},
        "Measure only the anonymous child trial tree with the unchanged frozen instrument.",
    )
    ledger.register(child_task, actor="human:fixture-maker", idempotency_key="task-child")
    ledger.register(
        Exposure(child_judge.authority_id, child_trial_ref, "trial-tree", "fresh child blind measurement", child_task.task_id),
        actor="system:exposure-recorder",
        idempotency_key="exposure-child",
    )
    child_output = {
        "scores": {"world_realism": 82, "deduction_quality": 84, "playability": 82},
        "outcome": "pass",
        "findings": [],
    }
    child_receipt = _record_invocation(
        ledger,
        authority=child_judge,
        task=child_task,
        trial_ref=child_trial_ref,
        parsed_output=child_output,
        key="child",
    )
    child_evaluation = Evaluation(
        child_task.task_id,
        child_candidate,
        instrument.instrument_id,
        "blind",
        (child_judge.authority_id,),
        (child_receipt.record_id,),
        child_output["scores"],
        (),
        _hard_gates(child_source, source_root),
        "pass",
        "development_only",
    )
    ledger.register(child_evaluation, actor="agent:ashwood-blind-judge-b", idempotency_key="evaluation-child")
    standing = StandingAttestation(
        child_candidate,
        "development_only",
        (child_evaluation.evaluation_id,),
        ("offline-fixture-blind-round",),
        reviewer.authority_id,
        "The fixture proves the native loop and score movement; no fresh human-play or public realism standing is claimed.",
    )
    ledger.register(standing, actor="human:fixture-reviewer", idempotency_key="standing-child")

    baseline_score = baseline_evaluation.overall_score(instrument)
    child_score = child_evaluation.overall_score(instrument)
    if baseline_score is None or child_score is None or child_score <= baseline_score:
        raise ValueError("Stage 6 fixture did not improve under the frozen instrument")
    if not all(child_evaluation.hard_gate_results.values()):
        raise ValueError("Stage 6 fixture regressed an accepted hard gate")
    verification = ledger.verify()
    workspace_verification = workspace.verify()
    if not verification["ok"] or not workspace_verification["ok"]:
        raise ValueError({"climb": verification, "workspace": workspace_verification})

    output = root / "output"
    output.mkdir(parents=True, exist_ok=True)
    workspace.export_archive(output / "ashwood-stage6.ngw")
    summary = {
        "schema_version": "0.6",
        "game": "The Ashwood Ledger",
        "baseline_candidate_id": baseline_candidate,
        "child_candidate_id": child_candidate,
        "instrument_id": instrument.instrument_id,
        "baseline_evaluation_id": baseline_evaluation.evaluation_id,
        "child_evaluation_id": child_evaluation.evaluation_id,
        "baseline_score": round(baseline_score, 1),
        "child_score": round(child_score, 1),
        "score_delta": round(child_score - baseline_score, 1),
        "hard_gates": dict(child_evaluation.hard_gate_results),
        "standing": "development_only",
        "workspace_verified": workspace_verification["ok"],
        "climb_verified": verification["ok"],
        "climb_journal_head": workspace.climb.head(),
    }
    (output / "stage6-result.json").write_bytes(canonical_json(summary))
    (output / "climb-lineage.md").write_text(
        "\n".join(
            [
                "# The Ashwood Ledger - native hill-climb",
                "",
                f"- Frozen instrument: `{instrument.instrument_id}`",
                f"- Baseline Candidate: `{baseline_candidate}`",
                f"- Baseline blind score: `{baseline_score:.1f}`",
                f"- Translated requirement: `{requirement.requirement_id}`",
                f"- Human-approved Transition: `{transition.transition_id}`",
                f"- Child Candidate: `{child_candidate}`",
                f"- Fresh child blind score: `{child_score:.1f}`",
                f"- Improvement: `+{child_score - baseline_score:.1f}`",
                "- Accepted Stage 5 hard gates replayed without regression.",
                "- Standing remains `development_only`; this offline fixture is not fresh human-play evidence.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return ClimbResult(
        workspace,
        ledger,
        baseline_candidate,
        child_candidate,
        baseline_evaluation,
        child_evaluation,
        output,
        summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the persisted Ashwood Ledger Stage 6 climb")
    parser.add_argument("root", help="new user-owned directory for climb state and outputs")
    args = parser.parse_args()
    print(json.dumps(run(args.root).summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
