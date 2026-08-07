"""Derived, replaceable progress projection for one generation lineage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from narrative_game.contracts import canonical_json
from narrative_game.workspace.io import atomic_write


@dataclass(frozen=True)
class GenerationStatus:
    """Human-readable progress derived from durable experiment records."""

    phase: str
    development_draft_ref: str
    selected_candidate_id: str | None
    active_target: str | None
    model_calls_used: int
    model_calls_remaining: int
    tokens_used: int
    tokens_remaining: int
    rounds_used: int
    rounds_remaining: int
    artifact_members_required: int
    artifact_members_completed: int
    stop_reason: str | None
    next_actions: tuple[str, ...]
    journal_heads: Mapping[str, str | None]
    schema_version: str = "0.19"

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "phase": self.phase,
            "development_draft_ref": self.development_draft_ref,
            "selected_candidate_id": self.selected_candidate_id,
            "active_target": self.active_target,
            "budget": {
                "model_calls_used": self.model_calls_used,
                "model_calls_remaining": self.model_calls_remaining,
                "tokens_used": self.tokens_used,
                "tokens_remaining": self.tokens_remaining,
                "rounds_used": self.rounds_used,
                "rounds_remaining": self.rounds_remaining,
            },
            "artifact_suite": {
                "members_required": self.artifact_members_required,
                "members_completed": self.artifact_members_completed,
            },
            "stop_reason": self.stop_reason,
            "next_actions": list(self.next_actions),
            "journal_heads": dict(self.journal_heads),
        }


def _generation_events(experiment: Any) -> tuple[dict[str, Any], ...]:
    return tuple(
        event
        for event in experiment.workspace.operational.read()
        if event["event_type"].startswith("generation_")
    )


def _phase_and_actions(
    experiment: Any,
    *,
    stopped: bool,
    plan: Any,
    events: tuple[dict[str, Any], ...],
) -> tuple[str, tuple[str, ...]]:
    snapshot = experiment.ledger.snapshot()
    draft = experiment.current_draft_data
    proposals = snapshot["proposals"]
    transitions = snapshot["transitions"]
    if stopped:
        return "stopped", ("inspect_stop_reason", "resume_with_new_plan",)
    if any(event["event_type"] == "generation_completed" for event in events):
        return "passed", ("inspect_evidence", "qualify_release",)
    if isinstance(draft, Mapping) and draft.get("kind") == "generation_brief":
        return "awaiting_initial_blueprint", ("create_initial_blueprint",)
    artifact_events = [
        event
        for event in events
        if event["event_type"] == "generation_artifact_suite_materialized"
        and event["payload"]["draft_ref"] == experiment.current_draft_ref
    ]
    if plan.artifact_plan.specifications and not artifact_events:
        return "awaiting_artifact_suite", ("materialize_independent_artifacts",)
    bound_events = [
        event
        for event in events
        if event["event_type"] == "generation_candidate_bound"
        and event["payload"]["draft_ref"] == experiment.current_draft_ref
    ]
    if not bound_events:
        return "awaiting_baseline_build", ("build_baseline",)
    candidate_id = bound_events[-1]["payload"]["candidate_id"]
    candidate_evaluations = [
        item for item in snapshot["evaluations"] if item.candidate_id == candidate_id
    ]
    if not candidate_evaluations:
        return "awaiting_measurement", ("measure_bound_candidate",)
    if len(proposals) > len(transitions):
        return "awaiting_review", ("review_proposal",)
    if candidate_evaluations[-1].outcome == "pass":
        return "passing_candidate", ("record_completion", "qualify_release",)
    return "ready_to_climb", ("translate_findings", "propose_child",)


def derive_generation_status(experiment: Any, plan: Any) -> GenerationStatus:
    """Rebuild progress from journals; projections are never authoritative state."""
    snapshot = experiment.ledger.snapshot()
    events = _generation_events(experiment)
    stop_events = [event for event in events if event["event_type"] == "generation_stopped"]
    stop_reason = (
        str(stop_events[-1]["payload"]["reason"])
        if stop_events
        else None
    )
    active_events = [
        event for event in events if event["event_type"] == "generation_target_changed"
    ]
    active_target = (
        str(active_events[-1]["payload"]["target"])
        if active_events
        else None
    )
    phase, actions = _phase_and_actions(
        experiment, stopped=bool(stop_events), plan=plan, events=events
    )
    selections = snapshot["selections"]
    completed = [event for event in events if event["event_type"] == "generation_completed"]
    selected = (
        str(completed[-1]["payload"]["candidate_id"])
        if completed
        else selections[-1].selected_candidate_id if selections else None
    )
    calls_used = len(snapshot["model_receipts"])
    tokens_used = sum(
        item.usage.get(
            "total_tokens",
            item.usage.get("input_tokens", 0) + item.usage.get("output_tokens", 0),
        )
        for item in snapshot["model_receipts"]
    )
    rounds_used = len(selections)
    artifact_events = [
        event
        for event in events
        if event["event_type"] == "generation_artifact_suite_materialized"
        and event["payload"]["draft_ref"] == experiment.current_draft_ref
    ]
    artifact_completed = (
        len(artifact_events[-1]["payload"]["members"])
        if artifact_events
        else 0
    )
    return GenerationStatus(
        phase=phase,
        development_draft_ref=experiment.current_draft_ref,
        selected_candidate_id=selected,
        active_target=active_target,
        model_calls_used=calls_used,
        model_calls_remaining=max(0, plan.budget.max_model_calls - calls_used),
        tokens_used=tokens_used,
        tokens_remaining=max(0, plan.budget.max_tokens - tokens_used),
        rounds_used=rounds_used,
        rounds_remaining=max(0, plan.budget.max_rounds - rounds_used),
        artifact_members_required=len(plan.artifact_plan.specifications),
        artifact_members_completed=artifact_completed,
        stop_reason=stop_reason,
        next_actions=actions,
        journal_heads=experiment.workspace.manifest["journal_heads"],
    )


def write_generation_status(experiment: Any, plan: Any) -> GenerationStatus:
    status = derive_generation_status(experiment, plan)
    atomic_write(
        experiment.workspace.root / "generation-status.json",
        canonical_json(status.to_mapping()),
    )
    lines = [
        "# Generation status",
        "",
        f"- Phase: `{status.phase}`",
        f"- Development Draft: `{status.development_draft_ref}`",
        f"- Selected Candidate: `{status.selected_candidate_id or 'none'}`",
        f"- Active target: `{status.active_target or 'none'}`",
        f"- Model calls: `{status.model_calls_used}` used, "
        f"`{status.model_calls_remaining}` remaining",
        f"- Tokens: `{status.tokens_used}` used, "
        f"`{status.tokens_remaining}` remaining",
        f"- Climb rounds: `{status.rounds_used}` used, "
        f"`{status.rounds_remaining}` remaining",
        f"- Artifact members: `{status.artifact_members_completed}` completed of "
        f"`{status.artifact_members_required}` required",
        f"- Stop reason: `{status.stop_reason or 'none'}`",
        "",
        "## Next actions",
        "",
        *(f"- `{item}`" for item in status.next_actions),
        "",
    ]
    atomic_write(
        experiment.workspace.root / "generation-status.md",
        "\n".join(lines).encode("utf-8"),
    )
    return status


__all__ = ["GenerationStatus", "derive_generation_status", "write_generation_status"]
