"""Pure policy for impact-scoped, budgeted hill-climb experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from typing import Any, Mapping

from narrative_game.contracts import canonical_json, digest_json


QUALIFICATION_TARGETS = (
    "coherent_build",
    "gameplay",
    "accessibility",
    "artifact_realism",
    "human_play",
    "public_release",
)

FINDING_ROUTES: Mapping[str, tuple[str, str]] = {
    "canonical_contradiction": ("canonical_model", "canonical_capability_tests"),
    "incomplete_proof": ("gameplay", "affected_blind_gameplay"),
    "accessibility_mismatch": ("accessibility", "parity_and_channel_replay"),
    "shared_renderer_defect": (
        "artifact_renderer", "representative_renderer_benchmark"
    ),
    "artifact_form_defect": ("artifact_emitter", "emitter_source_contract"),
    "character_social_defect": ("game_profile", "dossier_human_playtest"),
    "release_standing_ambiguity": (
        "experiment_spine", "trace_qualification_verification"
    ),
}

CHANGE_KINDS = {
    "renderer_only",
    "accessible_contract",
    "critical_player_evidence",
    "host_only_clarification",
    "artifact_content",
    "canonical_fact",
    "instrument",
}


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _id(kind: str, material: Mapping[str, Any]) -> str:
    return f"{kind}:{digest_json(material).removeprefix('sha256:')}"


@dataclass(frozen=True)
class PlanningFinding:
    finding_id: str
    finding_class: str
    structural_class: str
    affected_units: tuple[str, ...]
    blocking: bool = True

    def __post_init__(self) -> None:
        if self.finding_class not in FINDING_ROUTES:
            raise ValueError(f"unsupported finding class: {self.finding_class}")
        if not self.finding_id or not self.structural_class or not self.affected_units:
            raise ValueError("planning Finding requires identity, class, and affected units")


@dataclass(frozen=True)
class FindingRoute:
    finding_id: str
    finding_class: str
    owner: str
    selected_loop: str
    affected_units: tuple[str, ...]
    primary: bool
    broader_than_default: bool
    broadening_reason: str | None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FindingRoute":
        return cls(
            str(value["finding_id"]), str(value["finding_class"]),
            str(value["owner"]), str(value["selected_loop"]),
            tuple(str(item) for item in value["affected_units"]),
            bool(value["primary"]), bool(value["broader_than_default"]),
            value.get("broadening_reason"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_class": self.finding_class,
            "owner": self.owner,
            "selected_loop": self.selected_loop,
            "affected_units": list(self.affected_units),
            "primary": self.primary,
            "broader_than_default": self.broader_than_default,
            "broadening_reason": self.broadening_reason,
        }


def route_finding(
    finding: PlanningFinding,
    *,
    primary: bool = True,
    requested_loop: str | None = None,
    broadening_reason: str | None = None,
) -> FindingRoute:
    """Choose the cheapest valid loop; broader work requires a recorded reason."""
    owner, default_loop = FINDING_ROUTES[finding.finding_class]
    selected = requested_loop or default_loop
    broader = selected != default_loop
    if broader and not (broadening_reason and broadening_reason.strip()):
        raise ValueError("broader finding route requires a persisted reason")
    return FindingRoute(
        finding.finding_id,
        finding.finding_class,
        owner,
        selected,
        tuple(sorted(set(finding.affected_units))),
        primary,
        broader,
        broadening_reason.strip() if broadening_reason else None,
    )


@dataclass(frozen=True)
class ContractChange:
    change_id: str
    kind: str
    affected_units: tuple[str, ...]
    dependent_units: tuple[str, ...] = ()
    before_hash: str | None = None
    after_hash: str | None = None
    visible_evidence_changed: bool = False
    rationale: str = ""

    def __post_init__(self) -> None:
        if self.kind not in CHANGE_KINDS:
            raise ValueError(f"unsupported contract change: {self.kind}")
        if not self.change_id or not self.affected_units or not self.rationale.strip():
            raise ValueError("contract change requires identity, units, and rationale")
        if (self.before_hash is None) != (self.after_hash is None):
            raise ValueError("change hashes must be supplied together")


@dataclass(frozen=True)
class ImpactDecision:
    rebuild_units: tuple[str, ...]
    carry_forward_units: tuple[str, ...]
    measurement_loops: tuple[str, ...]
    replay_loops: tuple[str, ...]
    new_standing_lineage: bool
    comparison_allowed: bool
    rationales: tuple[Mapping[str, Any], ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "rationales", tuple(_copy(item) for item in self.rationales)
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ImpactDecision":
        return cls(
            tuple(str(item) for item in value["rebuild_units"]),
            tuple(str(item) for item in value["carry_forward_units"]),
            tuple(str(item) for item in value["measurement_loops"]),
            tuple(str(item) for item in value["replay_loops"]),
            bool(value["new_standing_lineage"]),
            bool(value["comparison_allowed"]),
            tuple(value["rationales"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "rebuild_units": list(self.rebuild_units),
            "carry_forward_units": list(self.carry_forward_units),
            "measurement_loops": list(self.measurement_loops),
            "replay_loops": list(self.replay_loops),
            "new_standing_lineage": self.new_standing_lineage,
            "comparison_allowed": self.comparison_allowed,
            "rationales": [dict(item) for item in self.rationales],
        }


def assess_impact(changes: tuple[ContractChange, ...]) -> ImpactDecision:
    """Compute the minimum rebuild and remeasurement set before execution."""
    if not changes:
        raise ValueError("impact assessment requires at least one change")
    rebuild: set[str] = set()
    carry: set[str] = set()
    measure: set[str] = set()
    replay: set[str] = set()
    new_lineage = False
    comparison_allowed = True
    reasons = []
    for change in sorted(changes, key=lambda item: item.change_id):
        units = set(change.affected_units)
        identical = (
            change.before_hash is not None
            and change.before_hash == change.after_hash
        )
        if identical:
            carry.update(units)
            action = "carry_forward_identical_bytes"
        elif change.kind == "renderer_only" and not change.visible_evidence_changed:
            rebuild.update(units)
            measure.add("artifact_realism")
            action = "artifact_measurement_only"
        elif change.kind == "accessible_contract":
            rebuild.update(units)
            measure.add("accessibility_parity")
            replay.add("affected_evidence_channel")
            action = "parity_and_channel_replay"
        elif change.kind == "critical_player_evidence":
            rebuild.update(units)
            replay.add("fresh_blind_gameplay")
            action = "fresh_blind_gameplay"
        elif change.kind == "host_only_clarification":
            rebuild.update(units)
            action = "host_projection_only"
        elif change.kind == "artifact_content":
            rebuild.update(units)
            measure.add("artifact_realism")
            action = "affected_artifact_measurement"
        elif change.kind == "canonical_fact":
            rebuild.update(units | set(change.dependent_units))
            replay.update(("dependent_projections", "fresh_blind_gameplay"))
            action = "rebuild_every_dependent_projection"
        elif change.kind == "instrument":
            new_lineage = True
            comparison_allowed = False
            measure.add("formal_measurement")
            action = "new_standing_lineage"
        else:  # pragma: no cover - guarded by ContractChange.
            raise AssertionError(change.kind)
        reasons.append(
            {
                "change_id": change.change_id,
                "kind": change.kind,
                "action": action,
                "rationale": change.rationale,
            }
        )
    carry.difference_update(rebuild)
    return ImpactDecision(
        tuple(sorted(rebuild)),
        tuple(sorted(carry)),
        tuple(sorted(measure)),
        tuple(sorted(replay)),
        new_lineage,
        comparison_allowed,
        tuple(reasons),
    )


@dataclass(frozen=True)
class PreflightBudget:
    max_iterations: int
    max_model_calls: int
    max_tokens: int | None
    minimum_improvement: float
    repeated_failure_threshold: int
    escalation_condition: str
    park_condition: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "minimum_improvement", float(self.minimum_improvement))
        if self.max_iterations < 1 or self.max_model_calls < 0:
            raise ValueError("preflight budget requires positive iterations and calls")
        if self.max_tokens is not None and self.max_tokens < 1:
            raise ValueError("configured token budget must be positive")
        if self.minimum_improvement <= 0 or self.repeated_failure_threshold < 1:
            raise ValueError("preflight improvement and failure thresholds must be positive")
        if not self.escalation_condition.strip() or not self.park_condition.strip():
            raise ValueError("preflight stop conditions are required")

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PreflightBudget":
        return cls(
            int(value["max_iterations"]), int(value["max_model_calls"]),
            int(value["max_tokens"]) if value.get("max_tokens") is not None else None,
            float(value["minimum_improvement"]),
            int(value["repeated_failure_threshold"]),
            str(value["escalation_condition"]), str(value["park_condition"]),
        )


@dataclass(frozen=True)
class EfficiencyPlan:
    primary_target: str
    mode: str
    baseline_candidate_id: str
    instrument_id: str
    selected_loop: str
    routes: tuple[FindingRoute, ...]
    impact: ImpactDecision
    representative_units: tuple[str, ...]
    budget: PreflightBudget | None
    baseline_score: float | None = None
    exact_candidate_id: str | None = None
    fixer_authority_ids: tuple[str, ...] = ()
    judge_authority_ids: tuple[str, ...] = ()
    standing_claim_allowed: bool = False

    def __post_init__(self) -> None:
        if self.baseline_score is not None:
            object.__setattr__(self, "baseline_score", float(self.baseline_score))
            if not math.isfinite(self.baseline_score):
                raise ValueError("baseline score must be finite")
        if self.primary_target not in QUALIFICATION_TARGETS:
            raise ValueError("efficiency plan requires exactly one qualification target")
        if self.mode not in {"bounded_preflight", "formal_measurement"}:
            raise ValueError("execution mode must be bounded_preflight or formal_measurement")
        if not self.baseline_candidate_id or not self.instrument_id or not self.selected_loop:
            raise ValueError("plan requires baseline, instrument, and selected loop")
        primary = tuple(item for item in self.routes if item.primary)
        if not primary or any(item.selected_loop != self.selected_loop for item in primary):
            raise ValueError("primary findings must route to the selected loop")
        routed_units = {
            unit for item in primary for unit in item.affected_units
        }
        if not set(self.representative_units) <= routed_units:
            raise ValueError("representative units must belong to primary findings")
        if self.mode == "bounded_preflight":
            if self.budget is None or not 1 <= len(self.representative_units) <= 2:
                raise ValueError("bounded preflight requires a budget and one or two units")
            if self.standing_claim_allowed or self.exact_candidate_id is not None:
                raise ValueError("bounded preflight cannot claim standing or freeze a child")
        else:
            if (
                self.budget is not None
                or self.representative_units
                or not self.exact_candidate_id
            ):
                raise ValueError("formal measurement requires one exact Candidate")
            if len(self.judge_authority_ids) != len(set(self.judge_authority_ids)):
                raise ValueError("formal measurement judges must be distinct")
            if set(self.fixer_authority_ids) & set(self.judge_authority_ids):
                raise ValueError("a fixer cannot certify its own child")
            if not self.judge_authority_ids or not self.standing_claim_allowed:
                raise ValueError("formal measurement requires independent judges")

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.13",
            "primary_target": self.primary_target,
            "mode": self.mode,
            "baseline_candidate_id": self.baseline_candidate_id,
            "instrument_id": self.instrument_id,
            "selected_loop": self.selected_loop,
            "routes": [item.to_mapping() for item in self.routes],
            "impact": self.impact.to_mapping(),
            "representative_units": list(self.representative_units),
            "budget": self.budget.to_mapping() if self.budget else None,
            "baseline_score": self.baseline_score,
            "exact_candidate_id": self.exact_candidate_id,
            "fixer_authority_ids": list(self.fixer_authority_ids),
            "judge_authority_ids": list(self.judge_authority_ids),
            "standing_claim_allowed": self.standing_claim_allowed,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EfficiencyPlan":
        if value.get("schema_version") != "0.13":
            raise ValueError("unsupported efficiency plan schema")
        result = cls(
            str(value["primary_target"]), str(value["mode"]),
            str(value["baseline_candidate_id"]), str(value["instrument_id"]),
            str(value["selected_loop"]),
            tuple(FindingRoute.from_mapping(item) for item in value["routes"]),
            ImpactDecision.from_mapping(value["impact"]),
            tuple(str(item) for item in value["representative_units"]),
            PreflightBudget.from_mapping(value["budget"])
            if value.get("budget") is not None else None,
            float(value["baseline_score"])
            if value.get("baseline_score") is not None else None,
            value.get("exact_candidate_id"),
            tuple(str(item) for item in value.get("fixer_authority_ids", ())),
            tuple(str(item) for item in value.get("judge_authority_ids", ())),
            bool(value.get("standing_claim_allowed", False)),
        )
        if value.get("plan_id", result.plan_id) != result.plan_id:
            raise ValueError("efficiency plan identity is invalid")
        return result

    @property
    def plan_id(self) -> str:
        return _id("efficiency-plan", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, **self.material()}


@dataclass(frozen=True)
class PreflightObservation:
    observation_id: str
    score: float
    model_calls: int
    tokens: int
    passed: bool
    structural_class: str

    def __post_init__(self) -> None:
        if not self.observation_id or not self.structural_class:
            raise ValueError("preflight observation requires identity and tell class")
        if not math.isfinite(float(self.score)):
            raise ValueError("preflight score must be finite")
        if self.model_calls < 0 or self.tokens < 0:
            raise ValueError("preflight usage cannot be negative")

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PreflightObservation":
        return cls(
            str(value["observation_id"]), float(value["score"]),
            int(value["model_calls"]), int(value["tokens"]),
            bool(value["passed"]), str(value["structural_class"]),
        )


@dataclass(frozen=True)
class PreflightState:
    processed_observation_ids: tuple[str, ...] = ()
    iterations_used: int = 0
    model_calls_used: int = 0
    tokens_used: int = 0
    best_score: float | None = None
    failure_counts: Mapping[str, int] = field(default_factory=dict)
    status: str = "active"
    next_transition: str = "continue_bounded_preflight"
    baseline_preserved: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "failure_counts", _copy(self.failure_counts or {}))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "processed_observation_ids": list(self.processed_observation_ids),
            "iterations_used": self.iterations_used,
            "model_calls_used": self.model_calls_used,
            "tokens_used": self.tokens_used,
            "best_score": self.best_score,
            "failure_counts": dict(self.failure_counts),
            "status": self.status,
            "next_transition": self.next_transition,
            "baseline_preserved": self.baseline_preserved,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PreflightState":
        return cls(
            tuple(str(item) for item in value.get("processed_observation_ids", ())),
            int(value.get("iterations_used", 0)),
            int(value.get("model_calls_used", 0)),
            int(value.get("tokens_used", 0)),
            float(value["best_score"]) if value.get("best_score") is not None else None,
            value.get("failure_counts", {}), str(value.get("status", "active")),
            str(value.get("next_transition", "continue_bounded_preflight")),
            bool(value.get("baseline_preserved", True)),
        )


def advance_preflight(
    plan: EfficiencyPlan,
    state: PreflightState,
    observation: PreflightObservation,
) -> PreflightState:
    """Advance once, or return the identical state for an idempotent replay."""
    if plan.mode != "bounded_preflight" or plan.budget is None:
        raise ValueError("only a bounded preflight accepts preflight observations")
    if observation.observation_id in state.processed_observation_ids:
        return state
    if state.status != "active":
        raise ValueError("preflight has already reached a terminal stop rule")
    prior_best = state.best_score
    improvement = observation.score if prior_best is None else observation.score - prior_best
    useful = prior_best is None or improvement >= plan.budget.minimum_improvement
    best = observation.score if prior_best is None else max(prior_best, observation.score)
    failures = dict(state.failure_counts)
    if observation.passed or useful:
        failures[observation.structural_class] = 0
    else:
        failures[observation.structural_class] = (
            failures.get(observation.structural_class, 0) + 1
        )
    iterations = state.iterations_used + 1
    calls = state.model_calls_used + observation.model_calls
    tokens = state.tokens_used + observation.tokens
    status = "active"
    next_transition = "continue_bounded_preflight"
    if observation.passed:
        status = "ready_for_formal_measurement"
        next_transition = "independent_review:completed_exact_candidate"
    elif failures.get(observation.structural_class, 0) >= (
        plan.budget.repeated_failure_threshold
    ):
        status = "escalated"
        next_transition = "update_owning_capability_issue"
    elif (
        iterations >= plan.budget.max_iterations
        or calls >= plan.budget.max_model_calls
        or (plan.budget.max_tokens is not None and tokens >= plan.budget.max_tokens)
    ):
        status = "parked"
        next_transition = "preserve_baseline_and_park_debt"
    return PreflightState(
        (*state.processed_observation_ids, observation.observation_id),
        iterations,
        calls,
        tokens,
        best,
        failures,
        status,
        next_transition,
        True,
    )
