"""Immutable authoring model for the first-party Narrative extension."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from narrative_game.contracts.canonical import digest_json
from narrative_game.kernel import KernelDefinition


def _strings(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in value)


@dataclass(frozen=True)
class Direction:
    premise: str
    experience_targets: tuple[str, ...]
    content_boundaries: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Direction":
        return cls(
            premise=str(value["premise"]),
            experience_targets=_strings(value.get("experience_targets", [])),
            content_boundaries=_strings(value.get("content_boundaries", [])),
        )


@dataclass(frozen=True)
class Proposition:
    id: str
    expression: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Proposition":
        return cls(id=str(value["id"]), expression=str(value["expression"]))


@dataclass(frozen=True)
class TruthAssignment:
    proposition_id: str
    value: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TruthAssignment":
        return cls(proposition_id=str(value["proposition_id"]), value=str(value["value"]))


@dataclass(frozen=True)
class WorldEvent:
    id: str
    summary: str
    order: int
    proposition_ids: tuple[str, ...]
    causes: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "WorldEvent":
        return cls(
            id=str(value["id"]),
            summary=str(value["summary"]),
            order=int(value["order"]),
            proposition_ids=_strings(value.get("proposition_ids", [])),
            causes=_strings(value.get("causes", [])),
        )


@dataclass(frozen=True)
class Belief:
    proposition_id: str
    stance: str
    basis: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Belief":
        return cls(
            proposition_id=str(value["proposition_id"]),
            stance=str(value["stance"]),
            basis=str(value.get("basis", "")),
        )


@dataclass(frozen=True)
class Objective:
    id: str
    description: str
    activation_phase_id: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Objective":
        return cls(
            id=str(value["id"]),
            description=str(value["description"]),
            activation_phase_id=str(value["activation_phase_id"]),
        )


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    seat_id: str
    beliefs: tuple[Belief, ...]
    objective_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Character":
        return cls(
            id=str(value["id"]),
            name=str(value["name"]),
            seat_id=str(value["seat_id"]),
            beliefs=tuple(Belief.from_mapping(item) for item in value.get("beliefs", [])),
            objective_ids=_strings(value.get("objective_ids", [])),
        )


@dataclass(frozen=True)
class Hypothesis:
    id: str
    label: str
    proposition_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Hypothesis":
        return cls(
            id=str(value["id"]),
            label=str(value["label"]),
            proposition_ids=_strings(value["proposition_ids"]),
        )


@dataclass(frozen=True)
class EvidenceRelation:
    target_kind: str
    target_id: str
    relation: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvidenceRelation":
        return cls(
            target_kind=str(value["target_kind"]),
            target_id=str(value["target_id"]),
            relation=str(value["relation"]),
        )


@dataclass(frozen=True)
class Evidence:
    id: str
    resource_id: str
    summary: str
    relations: tuple[EvidenceRelation, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Evidence":
        return cls(
            id=str(value["id"]),
            resource_id=str(value["resource_id"]),
            summary=str(value["summary"]),
            relations=tuple(EvidenceRelation.from_mapping(item) for item in value["relations"]),
        )


@dataclass(frozen=True)
class ProofPath:
    id: str
    hypothesis_id: str
    evidence_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProofPath":
        return cls(
            id=str(value["id"]),
            hypothesis_id=str(value["hypothesis_id"]),
            evidence_ids=_strings(value["evidence_ids"]),
        )


@dataclass(frozen=True)
class Phase:
    id: str
    label: str
    order: int

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Phase":
        return cls(id=str(value["id"]), label=str(value["label"]), order=int(value["order"]))


@dataclass(frozen=True)
class Reveal:
    id: str
    evidence_id: str
    phase_id: str
    audience_seat_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Reveal":
        return cls(
            id=str(value["id"]),
            evidence_id=str(value["evidence_id"]),
            phase_id=str(value["phase_id"]),
            audience_seat_ids=_strings(value["audience_seat_ids"]),
        )


@dataclass(frozen=True)
class Intervention:
    id: str
    kind: str
    phase_id: str
    evidence_ids: tuple[str, ...]
    instruction: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Intervention":
        return cls(
            id=str(value["id"]),
            kind=str(value["kind"]),
            phase_id=str(value["phase_id"]),
            evidence_ids=_strings(value.get("evidence_ids", [])),
            instruction=str(value["instruction"]),
        )


@dataclass(frozen=True)
class Resolution:
    prompt: str
    correct_hypothesis_id: str
    acceptable_proof_path_ids: tuple[str, ...]
    phase_id: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Resolution":
        return cls(
            prompt=str(value["prompt"]),
            correct_hypothesis_id=str(value["correct_hypothesis_id"]),
            acceptable_proof_path_ids=_strings(value["acceptable_proof_path_ids"]),
            phase_id=str(value["phase_id"]),
        )


@dataclass(frozen=True)
class CastVariant:
    id: str
    seat_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CastVariant":
        return cls(id=str(value["id"]), seat_ids=_strings(value["seat_ids"]))


@dataclass(frozen=True)
class FacilitatedInvestigation:
    id: str
    version: str
    cast_variants: tuple[CastVariant, ...]
    host_required: bool

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "FacilitatedInvestigation":
        return cls(
            id=str(value["id"]),
            version=str(value["version"]),
            cast_variants=tuple(
                CastVariant.from_mapping(item) for item in value["cast_variants"]
            ),
            host_required=bool(value["host_required"]),
        )

    @property
    def supported_seat_ids(self) -> tuple[str, ...]:
        return tuple(sorted({seat for variant in self.cast_variants for seat in variant.seat_ids}))


@dataclass(frozen=True)
class GameDefinition:
    """One fixed-truth, format-neutral authored investigation."""

    kernel: KernelDefinition
    direction: Direction
    profile: FacilitatedInvestigation
    propositions: tuple[Proposition, ...]
    truth_model: tuple[TruthAssignment, ...]
    events: tuple[WorldEvent, ...]
    characters: tuple[Character, ...]
    objectives: tuple[Objective, ...]
    hypotheses: tuple[Hypothesis, ...]
    evidence: tuple[Evidence, ...]
    proof_paths: tuple[ProofPath, ...]
    phases: tuple[Phase, ...]
    reveals: tuple[Reveal, ...]
    interventions: tuple[Intervention, ...]
    resolution: Resolution

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GameDefinition":
        narrative = value["narrative"]
        return cls(
            kernel=KernelDefinition.from_mapping(value["kernel"]),
            direction=Direction.from_mapping(narrative["direction"]),
            profile=FacilitatedInvestigation.from_mapping(narrative["profile"]),
            propositions=tuple(Proposition.from_mapping(item) for item in narrative["propositions"]),
            truth_model=tuple(
                TruthAssignment.from_mapping(item) for item in narrative["truth_model"]
            ),
            events=tuple(WorldEvent.from_mapping(item) for item in narrative["events"]),
            characters=tuple(Character.from_mapping(item) for item in narrative["characters"]),
            objectives=tuple(Objective.from_mapping(item) for item in narrative["objectives"]),
            hypotheses=tuple(Hypothesis.from_mapping(item) for item in narrative["hypotheses"]),
            evidence=tuple(Evidence.from_mapping(item) for item in narrative["evidence"]),
            proof_paths=tuple(ProofPath.from_mapping(item) for item in narrative["proof_paths"]),
            phases=tuple(Phase.from_mapping(item) for item in narrative["phases"]),
            reveals=tuple(Reveal.from_mapping(item) for item in narrative["reveals"]),
            interventions=tuple(
                Intervention.from_mapping(item) for item in narrative["interventions"]
            ),
            resolution=Resolution.from_mapping(narrative["resolution"]),
        )

    @property
    def content_hash(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        def records(items: tuple[Any, ...]) -> list[dict[str, Any]]:
            result = []
            for item in items:
                record = dict(item.__dict__)
                for key, value in tuple(record.items()):
                    if isinstance(value, tuple):
                        record[key] = [
                            dict(child.__dict__) if hasattr(child, "__dict__") else child
                            for child in value
                        ]
                result.append(record)
            return result

        return {
            "kernel": self.kernel.to_mapping(),
            "narrative": {
                "direction": {
                    "premise": self.direction.premise,
                    "experience_targets": list(self.direction.experience_targets),
                    "content_boundaries": list(self.direction.content_boundaries),
                },
                "profile": {
                    "id": self.profile.id,
                    "version": self.profile.version,
                    "cast_variants": [
                        {"id": variant.id, "seat_ids": list(variant.seat_ids)}
                        for variant in self.profile.cast_variants
                    ],
                    "host_required": self.profile.host_required,
                },
                "propositions": records(self.propositions),
                "truth_model": records(self.truth_model),
                "events": records(self.events),
                "characters": records(self.characters),
                "objectives": records(self.objectives),
                "hypotheses": records(self.hypotheses),
                "evidence": records(self.evidence),
                "proof_paths": records(self.proof_paths),
                "phases": records(self.phases),
                "reveals": records(self.reveals),
                "interventions": records(self.interventions),
                "resolution": {
                    "prompt": self.resolution.prompt,
                    "correct_hypothesis_id": self.resolution.correct_hypothesis_id,
                    "acceptable_proof_path_ids": list(
                        self.resolution.acceptable_proof_path_ids
                    ),
                    "phase_id": self.resolution.phase_id,
                },
            },
        }
