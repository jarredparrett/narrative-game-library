"""Content-addressed contracts for structured human play evidence."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts import canonical_json, digest_json


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _identified(kind: str, material: Mapping[str, Any]) -> str:
    return f"{kind}:{digest_json(material).removeprefix('sha256:')}"


@dataclass(frozen=True)
class PlaytestProtocol:
    """The frozen human-play contract for one exact measurement package."""

    name: str
    version: str
    binding_id: str
    instrument_id: str
    consent_version: str
    minimum_fresh_runs: int
    minimum_participants_per_run: int
    required_observation_categories: tuple[str, ...]
    require_model_comparison: bool = True
    model_human_delta_tolerance: int = 10
    required_response_stages: tuple[str, ...] = ()
    individual_response_stages: tuple[str, ...] = ()
    require_facilitator_phase_observations: bool = False
    defect_owner_taxonomy: tuple[str, ...] = ()

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.10",
            "name": self.name,
            "version": self.version,
            "binding_id": self.binding_id,
            "instrument_id": self.instrument_id,
            "consent_version": self.consent_version,
            "minimum_fresh_runs": self.minimum_fresh_runs,
            "minimum_participants_per_run": self.minimum_participants_per_run,
            "required_observation_categories": list(
                self.required_observation_categories
            ),
            "require_model_comparison": self.require_model_comparison,
            "model_human_delta_tolerance": self.model_human_delta_tolerance,
            "required_response_stages": list(self.required_response_stages),
            "individual_response_stages": list(self.individual_response_stages),
            "require_facilitator_phase_observations": self.require_facilitator_phase_observations,
            "defect_owner_taxonomy": list(self.defect_owner_taxonomy),
        }

    @property
    def protocol_id(self) -> str:
        return _identified("playtest-protocol", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"protocol_id": self.protocol_id, **self.material()}


@dataclass(frozen=True)
class ParticipantConsent:
    """One human's exact consent receipt for one Playtest Run."""

    authority_id: str
    consent_version: str
    scopes: tuple[str, ...]
    response_ref: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            "consent_version": self.consent_version,
            "scopes": list(self.scopes),
            "response_ref": self.response_ref,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ParticipantConsent":
        return cls(
            str(value["authority_id"]),
            str(value["consent_version"]),
            tuple(str(item) for item in value["scopes"]),
            str(value["response_ref"]),
        )


@dataclass(frozen=True)
class PlayObservation:
    """A phase-scoped observation quoted from an exact human response."""

    authority_id: str
    observer_role: str
    phase_id: str
    category: str
    quote: str
    note: str
    response_ref: str
    response_stage: str = "in_play"
    elapsed_seconds: int | None = None
    instrument_item_id: str = ""
    defect_owner: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PlayObservation":
        return cls(
            str(value["authority_id"]),
            str(value["observer_role"]),
            str(value["phase_id"]),
            str(value["category"]),
            str(value["quote"]),
            str(value["note"]),
            str(value["response_ref"]),
            str(value.get("response_stage", "in_play")),
            (
                int(value["elapsed_seconds"])
                if value.get("elapsed_seconds") is not None else None
            ),
            str(value.get("instrument_item_id", "")),
            (
                str(value["defect_owner"])
                if value.get("defect_owner") is not None else None
            ),
        )


@dataclass(frozen=True)
class PlaytestRun:
    """One completed live play session and its first-order observations."""

    protocol_id: str
    run_key: str
    release_id: str
    physical_export_id: str
    session_history_ref: str
    production_receipt_ref: str
    participant_authority_ids: tuple[str, ...]
    facilitator_authority_id: str
    observer_authority_ids: tuple[str, ...]
    consents: tuple[ParticipantConsent, ...]
    observations: tuple[PlayObservation, ...]
    scores: Mapping[str, int]
    finding_ids: tuple[str, ...]
    hard_gate_results: Mapping[str, bool]
    outcome: str
    evidence_class: str = "fresh-human-play"

    def __post_init__(self) -> None:
        object.__setattr__(self, "scores", _copy(self.scores))
        object.__setattr__(self, "hard_gate_results", _copy(self.hard_gate_results))

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.10",
            "protocol_id": self.protocol_id,
            "run_key": self.run_key,
            "release_id": self.release_id,
            "physical_export_id": self.physical_export_id,
            "session_history_ref": self.session_history_ref,
            "production_receipt_ref": self.production_receipt_ref,
            "participant_authority_ids": list(self.participant_authority_ids),
            "facilitator_authority_id": self.facilitator_authority_id,
            "observer_authority_ids": list(self.observer_authority_ids),
            "consents": [item.to_mapping() for item in self.consents],
            "observations": [item.to_mapping() for item in self.observations],
            "scores": dict(self.scores),
            "finding_ids": list(self.finding_ids),
            "hard_gate_results": dict(self.hard_gate_results),
            "outcome": self.outcome,
            "evidence_class": self.evidence_class,
        }

    @property
    def run_id(self) -> str:
        return _identified("playtest-run", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"run_id": self.run_id, **self.material()}

    def overall_score(self, dimensions: tuple[Any, ...]) -> float | None:
        if not self.scores:
            return None
        total_weight = sum(item.weight for item in dimensions)
        return sum(self.scores[item.dimension_id] * item.weight for item in dimensions) / total_weight


@dataclass(frozen=True)
class EvidenceComparison:
    """A deterministic comparison between blind model and human-play evidence."""

    protocol_id: str
    candidate_id: str
    instrument_id: str
    model_evaluation_id: str
    playtest_run_ids: tuple[str, ...]
    dimensions: Mapping[str, Mapping[str, int | float]]
    conclusion: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimensions", _copy(self.dimensions))

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "0.10",
            "protocol_id": self.protocol_id,
            "candidate_id": self.candidate_id,
            "instrument_id": self.instrument_id,
            "model_evaluation_id": self.model_evaluation_id,
            "playtest_run_ids": list(self.playtest_run_ids),
            "dimensions": _copy(self.dimensions),
            "conclusion": self.conclusion,
        }

    @property
    def comparison_id(self) -> str:
        return _identified("evidence-comparison", self.material())

    def to_mapping(self) -> dict[str, Any]:
        return {"comparison_id": self.comparison_id, **self.material()}
