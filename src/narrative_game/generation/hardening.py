"""Answer-safe bridge from Task Hardening Requirements to the existing generator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from narrative_game.climb.model import Finding, Requirement
from narrative_game.difficulty.hardening import TaskHardeningRequirement


class HardeningGenerationPort(Protocol):
    ledger: Any

    def propose_revision_from_requirements(
        self,
        adapter: Any,
        *,
        binding_id: str,
        requirement_ids: tuple[str, ...],
        task_key: str,
        authority_id: str,
        principal: str,
        requested_model: str,
        driver: Any,
        scratch_root: str | Path,
        human_direction: str | None = None,
        seed: int | None = None,
    ) -> Any: ...


def register_answer_safe_hardening_requirements(
    experiment: HardeningGenerationPort,
    requirement: TaskHardeningRequirement,
) -> tuple[Requirement, ...]:
    """Translate one governed demand into the generator's existing Requirement type."""
    source = Finding(
        "difficulty.task-hardening-source",
        "blocker",
        requirement.requirement_ref,
        "",
        "answer-safe hardening evidence",
        "A promoted capability demand has been accepted for bounded generation.",
    )
    experiment.ledger.register(
        source,
        actor="system:hardening-bridge",
        idempotency_key=f"hardening-source-{source.finding_id}",
    )
    translated = (
        Requirement(
            "difficulty.capability-demand",
            requirement.capability_demand,
            "The child does not exercise the declared capability demand.",
            requirement.capability_demand,
            (source.finding_id,),
        ),
        Requirement(
            "difficulty.challenge-mechanism",
            requirement.challenge_mechanism,
            "The child does not instantiate the declared interaction or information dependency.",
            (
                f"Implement this challenge mechanism using only {', '.join(requirement.selected_mutations)}: "
                f"{requirement.challenge_mechanism}"
            ),
            (source.finding_id,),
        ),
        Requirement(
            "difficulty.protected-invariants",
            "Every protected integrity and quality invariant remains true.",
            "A harder child that violates a protected invariant is a defect, not a valid challenge.",
            (
                "Preserve all invariants: "
                + ", ".join(requirement.protected_invariants)
                + ". Do not introduce: "
                + ", ".join(requirement.forbidden_mutations)
                + "."
            ),
            (source.finding_id,),
        ),
        Requirement(
            "difficulty.non-manifesting-control",
            requirement.non_manifesting_control,
            "The challenge lacks a matched control that isolates its mechanism.",
            "Also produce the matched non-manifesting control: " + requirement.non_manifesting_control,
            (source.finding_id,),
        ),
    )
    for item in translated:
        experiment.ledger.register(
            item,
            actor="system:hardening-bridge",
            idempotency_key=f"hardening-requirement-{item.requirement_id}",
        )
    return translated


def propose_hardening_child(
    experiment: HardeningGenerationPort,
    adapter: Any,
    *,
    requirement: TaskHardeningRequirement,
    baseline_binding_id: str,
    task_key: str,
    authority_id: str,
    principal: str,
    requested_model: str,
    driver: Any,
    scratch_root: str | Path,
    seed: int | None = None,
) -> Any:
    """Produce one child through Experiment.propose_revision_from_requirements."""
    translated = register_answer_safe_hardening_requirements(experiment, requirement)
    return experiment.propose_revision_from_requirements(
        adapter,
        binding_id=baseline_binding_id,
        requirement_ids=tuple(item.requirement_id for item in translated),
        task_key=task_key,
        authority_id=authority_id,
        principal=principal,
        requested_model=requested_model,
        driver=driver,
        scratch_root=scratch_root,
        human_direction=None,
        seed=seed,
    )


__all__ = [
    "HardeningGenerationPort",
    "propose_hardening_child",
    "register_answer_safe_hardening_requirements",
]
