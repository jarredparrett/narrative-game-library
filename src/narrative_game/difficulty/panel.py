"""Release-independent Evaluation Panels and release-bound applications."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class EvaluationPolicy:
    policy_id: str
    role_kind: str
    provider: str
    requested_model: str
    immutable_model_revision: str | None
    system_prompt_ref: str
    scaffold_ref: str
    sampling: Mapping[str, Any]
    context_rule: str = "isolated-per-episode"
    evaluation_only: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "sampling", _copy(self.sampling))
        if not self.evaluation_only:
            raise ValueError("Evaluation Panel policies must be evaluation-only")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "role_kind": self.role_kind,
            "provider": self.provider,
            "requested_model": self.requested_model,
            "immutable_model_revision": self.immutable_model_revision,
            "system_prompt_ref": self.system_prompt_ref,
            "scaffold_ref": self.scaffold_ref,
            "sampling": _copy(self.sampling),
            "context_rule": self.context_rule,
            "evaluation_only": self.evaluation_only,
        }


@dataclass(frozen=True)
class PanelCell:
    cell_id: str
    behavioral_condition: str
    host_condition: str
    communication_mode: str
    role_rotation: tuple[tuple[str, str], ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "cell_id": self.cell_id,
            "behavioral_condition": self.behavioral_condition,
            "host_condition": self.host_condition,
            "communication_mode": self.communication_mode,
            "role_rotation": [list(item) for item in self.role_rotation],
        }


@dataclass(frozen=True)
class EvaluationPanel:
    policies: tuple[EvaluationPolicy, ...]
    cells: tuple[PanelCell, ...]
    seeds: tuple[int, ...]
    repetitions: int
    tool_contract_ref: str
    action_contract_ref: str
    scheduler_ref: str
    adapter_ref: str
    retry_rule: str
    error_rule: str
    schema_version: str = "evaluation-panel.1"

    def __post_init__(self) -> None:
        if self.repetitions < 1 or not self.seeds:
            raise ValueError("Evaluation Panel requires seeds and repetitions")
        policy_ids = [item.policy_id for item in self.policies]
        cell_ids = [item.cell_id for item in self.cells]
        if len(policy_ids) != len(set(policy_ids)) or len(cell_ids) != len(set(cell_ids)):
            raise ValueError("Evaluation Panel policy and cell IDs must be unique")
        if len(self.seeds) != len(set(self.seeds)):
            raise ValueError("Evaluation Panel seeds must be unique")

    @property
    def panel_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "policies": [item.to_mapping() for item in self.policies],
            "cells": [item.to_mapping() for item in self.cells],
            "seeds": list(self.seeds),
            "repetitions": self.repetitions,
            "tool_contract_ref": self.tool_contract_ref,
            "action_contract_ref": self.action_contract_ref,
            "scheduler_ref": self.scheduler_ref,
            "adapter_ref": self.adapter_ref,
            "context_reset": "every-episode",
            "retry_rule": self.retry_rule,
            "error_rule": self.error_rule,
            "evaluation_only": True,
        }


@dataclass(frozen=True)
class EpisodeAssignment:
    panel_id: str
    release_id: str
    cell_id: str
    seed: int
    repetition: int
    role_allocation: tuple[tuple[str, str], ...]
    schema_version: str = "episode-assignment.1"

    @property
    def assignment_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "panel_id": self.panel_id,
            "release_id": self.release_id,
            "cell_id": self.cell_id,
            "seed": self.seed,
            "repetition": self.repetition,
            "role_allocation": [list(item) for item in self.role_allocation],
        }


@dataclass(frozen=True)
class PanelApplication:
    panel_id: str
    release_id: str
    assignments: tuple[EpisodeAssignment, ...]
    compatibility_grade: str
    findings: tuple[str, ...]
    model_match_grade: str
    missing_assignment_ids: tuple[str, ...] = ()
    incompatible_assignment_ids: tuple[str, ...] = ()
    schema_version: str = "panel-application.1"

    @property
    def application_id(self) -> str:
        return digest_json(self.to_mapping())

    @property
    def compatible(self) -> bool:
        return self.compatibility_grade in {"exact", "operational"}

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "panel_id": self.panel_id,
            "release_id": self.release_id,
            "assignments": [item.to_mapping() for item in self.assignments],
            "compatibility_grade": self.compatibility_grade,
            "model_match_grade": self.model_match_grade,
            "findings": list(self.findings),
            "missing_assignment_ids": list(self.missing_assignment_ids),
            "incompatible_assignment_ids": list(self.incompatible_assignment_ids),
        }


def apply_evaluation_panel(
    panel: EvaluationPanel,
    *,
    release_id: str,
    release_roles: tuple[str, ...],
    release_tool_contract_ref: str,
    resolved_models: Mapping[str, str | None],
    cosmetic_role_mapping: Mapping[str, str] | None = None,
) -> PanelApplication:
    """Bind an immutable Panel to a Release and grade every observable lock."""
    mapping = dict(cosmetic_role_mapping or {})
    roles = set(release_roles)
    findings = []
    cells_with_missing_roles = set()
    role_allocations: dict[str, tuple[tuple[str, str], ...]] = {}
    for cell in panel.cells:
        allocation = []
        for role, policy_id in cell.role_rotation:
            release_role = mapping.get(role, role)
            if release_role not in roles:
                findings.append(f"missing role for {cell.cell_id}: {role}")
                cells_with_missing_roles.add(cell.cell_id)
            allocation.append((release_role, policy_id))
        role_allocations[cell.cell_id] = tuple(allocation)
    if release_tool_contract_ref != panel.tool_contract_ref:
        findings.append("Release tool/action semantics are incompatible with Panel")

    model_findings = []
    exact = True
    for policy in panel.policies:
        observed = resolved_models.get(policy.policy_id)
        if observed is None:
            exact = False
            continue
        if policy.immutable_model_revision is None:
            exact = False
        elif observed != policy.immutable_model_revision:
            model_findings.append(
                f"model drift for {policy.policy_id}: expected {policy.immutable_model_revision}, observed {observed}"
            )
    findings.extend(model_findings)
    compatible = not findings
    model_grade = "exactly-matched" if compatible and exact else "operationally-matched" if compatible else "incompatible"
    grade = "exact" if compatible and exact else "operational" if compatible else "incompatible"
    assignments = tuple(
        EpisodeAssignment(
            panel.panel_id,
            release_id,
            cell.cell_id,
            seed,
            repetition,
            role_allocations[cell.cell_id],
        )
        for cell in panel.cells
        for seed in panel.seeds
        for repetition in range(1, panel.repetitions + 1)
    )
    missing_assignment_ids = tuple(
        item.assignment_id for item in assignments if item.cell_id in cells_with_missing_roles
    )
    globally_incompatible = release_tool_contract_ref != panel.tool_contract_ref or bool(model_findings)
    incompatible_assignment_ids = tuple(
        item.assignment_id
        for item in assignments
        if globally_incompatible or item.assignment_id in missing_assignment_ids
    )
    return PanelApplication(
        panel.panel_id,
        release_id,
        assignments,
        grade,
        tuple(sorted(set(findings))),
        model_grade,
        missing_assignment_ids,
        incompatible_assignment_ids,
    )


@dataclass(frozen=True)
class ReleaseComparison:
    baseline_application_id: str
    candidate_application_id: str
    panel_id: str
    analysis_instrument_id: str
    expected_assignment_ids: tuple[str, ...]
    completed_assignment_ids: tuple[str, ...]
    invalid_assignment_ids: tuple[str, ...]
    missing_assignment_ids: tuple[str, ...]
    model_match_grade: str
    schema_version: str = "release-comparison.1"

    @property
    def complete(self) -> bool:
        return not self.invalid_assignment_ids and not self.missing_assignment_ids

    @property
    def comparison_id(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "baseline_application_id": self.baseline_application_id,
            "candidate_application_id": self.candidate_application_id,
            "panel_id": self.panel_id,
            "analysis_instrument_id": self.analysis_instrument_id,
            "expected_assignment_ids": list(self.expected_assignment_ids),
            "completed_assignment_ids": list(self.completed_assignment_ids),
            "invalid_assignment_ids": list(self.invalid_assignment_ids),
            "missing_assignment_ids": list(self.missing_assignment_ids),
            "model_match_grade": self.model_match_grade,
            "complete": self.complete,
        }
