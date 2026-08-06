"""UI-neutral, content-addressed experience projection contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts import canonical_json, digest_json


EXPERIENCE_SCHEMA_VERSION = "0.11"


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class ActionIntent:
    """An authorized application boundary action; rendering never executes it."""

    action_id: str
    label: str
    boundary: str
    authority: str
    command: str
    enabled: bool
    reason: str
    payload_schema: Mapping[str, Any]
    fixed_payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload_schema", _copy(self.payload_schema))
        object.__setattr__(self, "fixed_payload", _copy(self.fixed_payload))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "label": self.label,
            "boundary": self.boundary,
            "authority": self.authority,
            "command": self.command,
            "enabled": self.enabled,
            "reason": self.reason,
            "payload_schema": _copy(self.payload_schema),
            "fixed_payload": _copy(self.fixed_payload),
        }


@dataclass(frozen=True)
class TutorialStep:
    """One component in the maker's executable game-anatomy walkthrough."""

    component_id: str
    title: str
    summary: str
    owns: tuple[str, ...]
    produces: tuple[str, ...]
    example_refs: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "title": self.title,
            "summary": self.summary,
            "owns": list(self.owns),
            "produces": list(self.produces),
            "example_refs": list(self.example_refs),
        }


@dataclass(frozen=True)
class TutorialProjection:
    """A deterministic walkthrough of the components behind one exact game."""

    profile_id: str
    release_id: str
    title: str
    steps: tuple[TutorialStep, ...]

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": EXPERIENCE_SCHEMA_VERSION,
            "profile_id": self.profile_id,
            "release_id": self.release_id,
            "title": self.title,
            "steps": [item.to_mapping() for item in self.steps],
        }

    @property
    def tutorial_id(self) -> str:
        return f"tutorial:{digest_json(self.material()).removeprefix('sha256:')}"

    def to_mapping(self) -> dict[str, Any]:
        return {"tutorial_id": self.tutorial_id, **self.material()}


@dataclass(frozen=True)
class ExperienceSection:
    """One renderer-independent region of an authorized surface."""

    section_id: str
    label: str
    kind: str
    data: Any

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _copy(self.data))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "label": self.label,
            "kind": self.kind,
            "data": _copy(self.data),
        }


@dataclass(frozen=True)
class ExperienceProjection:
    """One role-scoped view over exact immutable and live game state."""

    surface: str
    authority_scope: str
    title: str
    subtitle: str
    release_id: str
    session_id: str | None
    revision: int | None
    physical_export_id: str | None
    sections: tuple[ExperienceSection, ...]
    actions: tuple[ActionIntent, ...]
    tutorial_id: str | None = None

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": EXPERIENCE_SCHEMA_VERSION,
            "surface": self.surface,
            "authority_scope": self.authority_scope,
            "title": self.title,
            "subtitle": self.subtitle,
            "release_id": self.release_id,
            "session_id": self.session_id,
            "revision": self.revision,
            "physical_export_id": self.physical_export_id,
            "sections": [item.to_mapping() for item in self.sections],
            "actions": [item.to_mapping() for item in self.actions],
            "tutorial_id": self.tutorial_id,
        }

    @property
    def projection_id(self) -> str:
        return f"experience:{digest_json(self.material()).removeprefix('sha256:')}"

    def to_mapping(self) -> dict[str, Any]:
        return {"projection_id": self.projection_id, **self.material()}
