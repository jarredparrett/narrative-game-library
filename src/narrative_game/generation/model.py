"""Pure contracts for planning a deterministic initial game generation."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Mapping

from narrative_game.contracts import canonical_json, digest_json


GENERATION_SCHEMA_VERSION = "0.1"


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _require_mapping(value: Any, *, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be an object")
    return value


def _require_keys(
    value: Mapping[str, Any], *, required: set[str], optional: set[str] = frozenset()
) -> None:
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        raise ValueError(f"mapping is missing required fields: {sorted(missing)}")
    if unknown:
        raise ValueError(f"mapping contains unknown fields: {sorted(unknown)}")


def _require_string(value: Any, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _require_int(value: Any, *, label: str, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{label} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{label} must be at least {minimum}")
    return value


def _require_strings(value: Any, *, label: str, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError(f"{label} must be an array")
    result = tuple(_require_string(item, label=label) for item in value)
    if not allow_empty and not result:
        raise ValueError(f"{label} must not be empty")
    if len(result) != len(set(result)):
        raise ValueError(f"{label} must not contain duplicates")
    return result


def _require_schema(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != GENERATION_SCHEMA_VERSION:
        raise ValueError(
            f"generation contract must use schema {GENERATION_SCHEMA_VERSION}"
        )


@dataclass(frozen=True)
class CreativeBrief:
    """Canonical human intent supplied to the initial game creator."""

    title: str
    premise: str
    experience_targets: tuple[str, ...]
    content_boundaries: tuple[str, ...]
    player_count: int
    target_minutes: int
    delivery_format: str
    seed: int
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        _require_string(self.title, label="brief title")
        _require_string(self.premise, label="brief premise")
        object.__setattr__(
            self,
            "experience_targets",
            _require_strings(
                self.experience_targets, label="experience targets", allow_empty=False
            ),
        )
        object.__setattr__(
            self,
            "content_boundaries",
            _require_strings(self.content_boundaries, label="content boundaries"),
        )
        _require_int(self.player_count, label="player count", minimum=1)
        _require_int(self.target_minutes, label="target minutes", minimum=1)
        _require_string(self.delivery_format, label="delivery format")
        _require_int(self.seed, label="brief seed")

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "premise": self.premise,
            "experience_targets": list(self.experience_targets),
            "content_boundaries": list(self.content_boundaries),
            "player_count": self.player_count,
            "target_minutes": self.target_minutes,
            "delivery_format": self.delivery_format,
            "seed": self.seed,
        }

    @property
    def brief_id(self) -> str:
        return f"creative-brief:{digest_json(self.material()).removeprefix('sha256:')}"

    def to_mapping(self) -> dict[str, Any]:
        return {"brief_id": self.brief_id, **self.material()}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CreativeBrief":
        value = _require_mapping(value, label="Creative Brief")
        _require_keys(
            value,
            required={
                "brief_id",
                "schema_version",
                "title",
                "premise",
                "experience_targets",
                "content_boundaries",
                "player_count",
                "target_minutes",
                "delivery_format",
                "seed",
            },
        )
        _require_schema(value)
        result = cls(
            title=_require_string(value["title"], label="brief title"),
            premise=_require_string(value["premise"], label="brief premise"),
            experience_targets=_require_strings(
                value["experience_targets"],
                label="experience targets",
                allow_empty=False,
            ),
            content_boundaries=_require_strings(
                value["content_boundaries"], label="content boundaries"
            ),
            player_count=_require_int(value["player_count"], label="player count", minimum=1),
            target_minutes=_require_int(
                value["target_minutes"], label="target minutes", minimum=1
            ),
            delivery_format=_require_string(
                value["delivery_format"], label="delivery format"
            ),
            seed=_require_int(value["seed"], label="brief seed"),
            schema_version=str(value["schema_version"]),
        )
        if value["brief_id"] != result.brief_id:
            raise ValueError("Creative Brief identity is invalid")
        return result


@dataclass(frozen=True)
class ArtifactSpecification:
    """Authoring-time contract for one realism-sensitive game artifact."""

    artifact_id: str
    resource_id: str
    document_class: str
    seed: int
    proposition_ids: tuple[str, ...]
    event_ids: tuple[str, ...]
    truth_binding: str = ""
    media_type: str = "application/pdf"
    pins: Mapping[str, Any] = field(default_factory=dict)
    canon: Mapping[str, Any] = field(default_factory=dict)
    accessibility: Mapping[str, Any] = field(default_factory=dict)
    permitted_audience_ids: tuple[str, ...] = ()
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        _require_string(self.artifact_id, label="artifact id")
        _require_string(self.resource_id, label="artifact resource id")
        _require_string(self.document_class, label="document class")
        _require_int(self.seed, label="artifact seed")
        _require_string(self.media_type, label="artifact media type")
        object.__setattr__(
            self,
            "proposition_ids",
            _require_strings(self.proposition_ids, label="artifact proposition ids"),
        )
        object.__setattr__(
            self,
            "event_ids",
            _require_strings(self.event_ids, label="artifact event ids"),
        )
        if self.truth_binding and re.fullmatch(
            r"sha256:[0-9a-f]{64}", self.truth_binding
        ) is None:
            raise ValueError("artifact truth binding must be a typed SHA-256 digest")
        object.__setattr__(
            self,
            "permitted_audience_ids",
            _require_strings(
                self.permitted_audience_ids,
                label="permitted audience ids",
                allow_empty=False,
            ),
        )
        if not self.proposition_ids and not self.event_ids:
            raise ValueError(
                "Artifact Specification requires a canonical Proposition or Event reference"
            )
        object.__setattr__(self, "pins", _copy(_require_mapping(self.pins, label="pins")))
        object.__setattr__(self, "canon", _copy(_require_mapping(self.canon, label="canon")))
        object.__setattr__(
            self,
            "accessibility",
            _copy(_require_mapping(self.accessibility, label="accessibility")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "artifact_id": self.artifact_id,
            "resource_id": self.resource_id,
            "document_class": self.document_class,
            "seed": self.seed,
            "proposition_ids": list(self.proposition_ids),
            "event_ids": list(self.event_ids),
            "truth_binding": self.truth_binding,
            "media_type": self.media_type,
            "pins": _copy(self.pins),
            "canon": _copy(self.canon),
            "accessibility": _copy(self.accessibility),
            "permitted_audience_ids": list(self.permitted_audience_ids),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactSpecification":
        value = _require_mapping(value, label="Artifact Specification")
        _require_keys(
            value,
            required={
                "schema_version",
                "artifact_id",
                "resource_id",
                "document_class",
                "seed",
                "proposition_ids",
                "event_ids",
                "truth_binding",
                "media_type",
                "pins",
                "canon",
                "accessibility",
                "permitted_audience_ids",
            },
        )
        _require_schema(value)
        return cls(
            artifact_id=_require_string(value["artifact_id"], label="artifact id"),
            resource_id=_require_string(value["resource_id"], label="artifact resource id"),
            document_class=_require_string(value["document_class"], label="document class"),
            seed=_require_int(value["seed"], label="artifact seed"),
            proposition_ids=_require_strings(
                value["proposition_ids"], label="artifact proposition ids"
            ),
            event_ids=_require_strings(value["event_ids"], label="artifact event ids"),
            truth_binding=str(value["truth_binding"]),
            media_type=_require_string(value["media_type"], label="artifact media type"),
            pins=_require_mapping(value["pins"], label="pins"),
            canon=_require_mapping(value["canon"], label="canon"),
            accessibility=_require_mapping(
                value["accessibility"], label="accessibility"
            ),
            permitted_audience_ids=_require_strings(
                value["permitted_audience_ids"], label="permitted audience ids"
            ),
            schema_version=str(value["schema_version"]),
        )


@dataclass(frozen=True)
class ArtifactPlan:
    """An exact set of artifact specifications and its deterministic order."""

    specifications: tuple[ArtifactSpecification, ...]
    generation_order: tuple[str, ...]
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        if not isinstance(self.specifications, (list, tuple)) or any(
            not isinstance(item, ArtifactSpecification) for item in self.specifications
        ):
            raise TypeError("artifact specifications must contain ArtifactSpecification values")
        object.__setattr__(self, "specifications", tuple(self.specifications))
        object.__setattr__(
            self,
            "generation_order",
            _require_strings(self.generation_order, label="artifact generation order"),
        )
        ids = tuple(item.artifact_id for item in self.specifications)
        if len(ids) != len(set(ids)):
            raise ValueError("Artifact Plan contains duplicate artifact ids")
        resource_ids = tuple(item.resource_id for item in self.specifications)
        if len(resource_ids) != len(set(resource_ids)):
            raise ValueError("Artifact Plan contains duplicate artifact resource ids")
        if len(self.generation_order) != len(ids) or set(self.generation_order) != set(ids):
            raise ValueError(
                "artifact generation order must cover every specification exactly once"
            )
        unbound = [item.artifact_id for item in self.specifications if not item.truth_binding]
        if unbound:
            raise ValueError(
                "Artifact Plan contains specifications without canonical truth bindings: "
                f"{sorted(unbound)}"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "specifications": [item.to_mapping() for item in self.specifications],
            "generation_order": list(self.generation_order),
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactPlan":
        value = _require_mapping(value, label="Artifact Plan")
        _require_keys(
            value,
            required={"schema_version", "specifications", "generation_order"},
        )
        _require_schema(value)
        if not isinstance(value["specifications"], list):
            raise TypeError("artifact specifications must be an array")
        return cls(
            tuple(ArtifactSpecification.from_mapping(item) for item in value["specifications"]),
            _require_strings(value["generation_order"], label="artifact generation order"),
            str(value["schema_version"]),
        )


@dataclass(frozen=True)
class ModelRoleAssignment:
    """One provider/model selected to occupy one generation role."""

    role: str
    authority_id: str
    provider: str
    requested_model: str
    agent_id: str
    context_id: str
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        _require_string(self.role, label="model role")
        _require_string(self.authority_id, label="model authority id")
        _require_string(self.provider, label="model provider")
        _require_string(self.requested_model, label="requested model")
        _require_string(self.agent_id, label="model agent id")
        _require_string(self.context_id, label="model context id")

    def to_mapping(self) -> dict[str, str]:
        return dict(self.__dict__)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ModelRoleAssignment":
        value = _require_mapping(value, label="Model Role Assignment")
        _require_keys(
            value,
            required={
                "schema_version",
                "role",
                "authority_id",
                "provider",
                "requested_model",
                "agent_id",
                "context_id",
            },
        )
        _require_schema(value)
        return cls(
            _require_string(value["role"], label="model role"),
            _require_string(value["authority_id"], label="model authority id"),
            _require_string(value["provider"], label="model provider"),
            _require_string(value["requested_model"], label="requested model"),
            _require_string(value["agent_id"], label="model agent id"),
            _require_string(value["context_id"], label="model context id"),
            str(value["schema_version"]),
        )


@dataclass(frozen=True)
class GenerationBudget:
    """Hard resource limits for one initial-generation process."""

    max_model_calls: int
    max_tokens: int
    max_rounds: int
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        _require_int(self.max_model_calls, label="maximum model calls", minimum=1)
        _require_int(self.max_tokens, label="maximum tokens", minimum=1)
        _require_int(self.max_rounds, label="maximum rounds", minimum=1)

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GenerationBudget":
        value = _require_mapping(value, label="Generation Budget")
        _require_keys(
            value,
            required={"schema_version", "max_model_calls", "max_tokens", "max_rounds"},
        )
        _require_schema(value)
        return cls(
            _require_int(value["max_model_calls"], label="maximum model calls", minimum=1),
            _require_int(value["max_tokens"], label="maximum tokens", minimum=1),
            _require_int(value["max_rounds"], label="maximum rounds", minimum=1),
            str(value["schema_version"]),
        )


@dataclass(frozen=True)
class StopPolicy:
    """Explicit terminal rule for repeated invalid creator output.

    Passing-candidate completion and hard budget exhaustion are invariant
    coordinator behavior, so they are not exposed as misleading switches.
    """

    max_consecutive_invalid_outputs: int
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        _require_int(
            self.max_consecutive_invalid_outputs,
            label="maximum consecutive invalid outputs",
            minimum=1,
        )

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "StopPolicy":
        value = _require_mapping(value, label="Stop Policy")
        _require_keys(
            value,
            required={"schema_version", "max_consecutive_invalid_outputs"},
        )
        _require_schema(value)
        return cls(
            _require_int(
                value["max_consecutive_invalid_outputs"],
                label="maximum consecutive invalid outputs",
                minimum=1,
            ),
            str(value["schema_version"]),
        )


@dataclass(frozen=True)
class GenerationPlan:
    """Frozen initial-generation inputs, assignments, limits, and artifact work."""

    experiment_id: str
    profile_id: str
    profile_version: str
    seed: int
    role_assignments: tuple[ModelRoleAssignment, ...]
    budget: GenerationBudget
    stop_policy: StopPolicy
    artifact_plan: ArtifactPlan
    schema_version: str = GENERATION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _require_schema({"schema_version": self.schema_version})
        _require_string(self.experiment_id, label="experiment id")
        _require_string(self.profile_id, label="profile id")
        _require_string(self.profile_version, label="profile version")
        _require_int(self.seed, label="generation seed")
        if not isinstance(self.role_assignments, (list, tuple)) or any(
            not isinstance(item, ModelRoleAssignment) for item in self.role_assignments
        ):
            raise TypeError("role assignments must contain ModelRoleAssignment values")
        object.__setattr__(self, "role_assignments", tuple(self.role_assignments))
        if not self.role_assignments:
            raise ValueError("Generation Plan requires at least one model role assignment")
        roles = tuple(item.role for item in self.role_assignments)
        authorities = tuple(item.authority_id for item in self.role_assignments)
        agents = tuple(item.agent_id for item in self.role_assignments)
        contexts = tuple(item.context_id for item in self.role_assignments)
        if len(authorities) != len(set(authorities)):
            raise ValueError("Generation Plan reuses a model authority")
        if len(agents) != len(set(agents)):
            raise ValueError("Generation Plan reuses a model agent identity")
        if len(contexts) != len(set(contexts)):
            raise ValueError("Generation Plan reuses a model context identity")
        if roles.count("builder") != 1 or roles.count("reviewer") != 1:
            raise ValueError(
                "Generation Plan requires exactly one builder and exactly one reviewer"
            )
        if roles.count("judge") < 1:
            raise ValueError("Generation Plan requires at least one judge")

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "seed": self.seed,
            "role_assignments": [item.to_mapping() for item in self.role_assignments],
            "budget": self.budget.to_mapping(),
            "stop_policy": self.stop_policy.to_mapping(),
            "artifact_plan": self.artifact_plan.to_mapping(),
        }

    @property
    def plan_id(self) -> str:
        return f"generation-plan:{digest_json(self.material()).removeprefix('sha256:')}"

    def to_mapping(self) -> dict[str, Any]:
        return {"plan_id": self.plan_id, **self.material()}

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GenerationPlan":
        value = _require_mapping(value, label="Generation Plan")
        _require_keys(
            value,
            required={
                "plan_id",
                "schema_version",
                "experiment_id",
                "profile_id",
                "profile_version",
                "seed",
                "role_assignments",
                "budget",
                "stop_policy",
                "artifact_plan",
            },
        )
        _require_schema(value)
        if not isinstance(value["role_assignments"], list):
            raise TypeError("model role assignments must be an array")
        result = cls(
            _require_string(value["experiment_id"], label="experiment id"),
            _require_string(value["profile_id"], label="profile id"),
            _require_string(value["profile_version"], label="profile version"),
            _require_int(value["seed"], label="generation seed"),
            tuple(
                ModelRoleAssignment.from_mapping(item)
                for item in value["role_assignments"]
            ),
            GenerationBudget.from_mapping(value["budget"]),
            StopPolicy.from_mapping(value["stop_policy"]),
            ArtifactPlan.from_mapping(value["artifact_plan"]),
            str(value["schema_version"]),
        )
        if value["plan_id"] != result.plan_id:
            raise ValueError("Generation Plan identity is invalid")
        return result
