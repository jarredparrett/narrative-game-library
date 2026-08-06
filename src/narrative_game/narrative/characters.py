"""Canonical deep-dossier and phase-aware Character Program contracts."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts import canonical_json, digest_json
from narrative_game.kernel import Finding


CHARACTER_PROGRAM_SCHEMA_VERSION = "0.14"
MOVE_KINDS = {"action", "bargain", "challenge", "fallback", "after_exposure"}


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _strings(value: Any) -> tuple[str, ...]:
    return tuple(str(item) for item in value or ())


def _finding(code: str, locus: str, quote: str, message: str) -> Finding:
    return Finding(code, "blocker", locus, quote, message)


@dataclass(frozen=True)
class ReferencedText:
    """Authored prose whose factual surface is licensed by canonical IDs."""

    text: str
    proposition_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    character_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReferencedText":
        return cls(
            str(value["text"]),
            _strings(value.get("proposition_ids")),
            _strings(value.get("event_ids")),
            _strings(value.get("evidence_ids")),
            _strings(value.get("character_ids")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "proposition_ids": list(self.proposition_ids),
            "event_ids": list(self.event_ids),
            "evidence_ids": list(self.evidence_ids),
            "character_ids": list(self.character_ids),
        }


@dataclass(frozen=True)
class KnowledgeGrant:
    proposition_id: str
    seat_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "KnowledgeGrant":
        return cls(str(value["proposition_id"]), _strings(value["seat_ids"]))

    def to_mapping(self) -> dict[str, Any]:
        return {"proposition_id": self.proposition_id, "seat_ids": list(self.seat_ids)}


@dataclass(frozen=True)
class EventGrant:
    event_id: str
    seat_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EventGrant":
        return cls(str(value["event_id"]), _strings(value["seat_ids"]))

    def to_mapping(self) -> dict[str, Any]:
        return {"event_id": self.event_id, "seat_ids": list(self.seat_ids)}


@dataclass(frozen=True)
class KnowledgeBoundary:
    known_fact_proposition_ids: tuple[str, ...]
    revisable_belief_proposition_ids: tuple[str, ...]
    permitted_lie_proposition_ids: tuple[str, ...]
    must_not_contradict_proposition_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "KnowledgeBoundary":
        return cls(
            _strings(value.get("known_fact_proposition_ids")),
            _strings(value.get("revisable_belief_proposition_ids")),
            _strings(value.get("permitted_lie_proposition_ids")),
            _strings(value.get("must_not_contradict_proposition_ids")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "known_fact_proposition_ids": list(self.known_fact_proposition_ids),
            "revisable_belief_proposition_ids": list(
                self.revisable_belief_proposition_ids
            ),
            "permitted_lie_proposition_ids": list(self.permitted_lie_proposition_ids),
            "must_not_contradict_proposition_ids": list(
                self.must_not_contradict_proposition_ids
            ),
        }


@dataclass(frozen=True)
class QuickStart:
    public_identity: ReferencedText
    private_truth: ReferencedText
    immediate_objective_ids: tuple[str, ...]
    opening_belief_proposition_ids: tuple[str, ...]
    first_move: ReferencedText

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "QuickStart":
        return cls(
            ReferencedText.from_mapping(value["public_identity"]),
            ReferencedText.from_mapping(value["private_truth"]),
            _strings(value["immediate_objective_ids"]),
            _strings(value["opening_belief_proposition_ids"]),
            ReferencedText.from_mapping(value["first_move"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "public_identity": self.public_identity.to_mapping(),
            "private_truth": self.private_truth.to_mapping(),
            "immediate_objective_ids": list(self.immediate_objective_ids),
            "opening_belief_proposition_ids": list(
                self.opening_belief_proposition_ids
            ),
            "first_move": self.first_move.to_mapping(),
        }


@dataclass(frozen=True)
class RelationshipProfile:
    character_id: str
    history: ReferencedText
    current_tension: ReferencedText
    leverage: ReferencedText
    likely_alliance: ReferencedText

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RelationshipProfile":
        return cls(
            str(value["character_id"]),
            ReferencedText.from_mapping(value["history"]),
            ReferencedText.from_mapping(value["current_tension"]),
            ReferencedText.from_mapping(value["leverage"]),
            ReferencedText.from_mapping(value["likely_alliance"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "character_id": self.character_id,
            "history": self.history.to_mapping(),
            "current_tension": self.current_tension.to_mapping(),
            "leverage": self.leverage.to_mapping(),
            "likely_alliance": self.likely_alliance.to_mapping(),
        }


@dataclass(frozen=True)
class PrivateChronologyEntry:
    event_id: str
    disclosure_phase_id: str
    perspective: ReferencedText

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PrivateChronologyEntry":
        return cls(
            str(value["event_id"]),
            str(value["disclosure_phase_id"]),
            ReferencedText.from_mapping(value["perspective"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "disclosure_phase_id": self.disclosure_phase_id,
            "perspective": self.perspective.to_mapping(),
        }


@dataclass(frozen=True)
class CharacterMove:
    move_id: str
    kind: str
    instruction: ReferencedText
    target_character_ids: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CharacterMove":
        return cls(
            str(value["move_id"]),
            str(value["kind"]),
            ReferencedText.from_mapping(value["instruction"]),
            _strings(value.get("target_character_ids")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "move_id": self.move_id,
            "kind": self.kind,
            "instruction": self.instruction.to_mapping(),
            "target_character_ids": list(self.target_character_ids),
        }


@dataclass(frozen=True)
class RevealPath:
    reveal_path_id: str
    secret_proposition_id: str
    phase_ids: tuple[str, ...]
    trigger: ReferencedText
    recovery_intervention_id: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RevealPath":
        return cls(
            str(value["reveal_path_id"]),
            str(value["secret_proposition_id"]),
            _strings(value["phase_ids"]),
            ReferencedText.from_mapping(value["trigger"]),
            str(value["recovery_intervention_id"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "reveal_path_id": self.reveal_path_id,
            "secret_proposition_id": self.secret_proposition_id,
            "phase_ids": list(self.phase_ids),
            "trigger": self.trigger.to_mapping(),
            "recovery_intervention_id": self.recovery_intervention_id,
        }


@dataclass(frozen=True)
class PhaseArc:
    phase_id: str
    objective_ids: tuple[str, ...]
    pressure: ReferencedText
    move_ids: tuple[str, ...]
    reveal_path_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PhaseArc":
        return cls(
            str(value["phase_id"]),
            _strings(value.get("objective_ids")),
            ReferencedText.from_mapping(value["pressure"]),
            _strings(value["move_ids"]),
            _strings(value.get("reveal_path_ids")),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "objective_ids": list(self.objective_ids),
            "pressure": self.pressure.to_mapping(),
            "move_ids": list(self.move_ids),
            "reveal_path_ids": list(self.reveal_path_ids),
        }


@dataclass(frozen=True)
class EndingChoice:
    choice_id: str
    label: str
    consequence: ReferencedText

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EndingChoice":
        return cls(
            str(value["choice_id"]),
            str(value["label"]),
            ReferencedText.from_mapping(value["consequence"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "choice_id": self.choice_id,
            "label": self.label,
            "consequence": self.consequence.to_mapping(),
        }


@dataclass(frozen=True)
class CharacterDossier:
    dossier_id: str
    seat_id: str
    character_id: str
    resource_id: str
    target_pages: int
    quick_start: QuickStart
    knowledge_boundary: KnowledgeBoundary
    personal_history: tuple[ReferencedText, ...]
    emotional_stakes: tuple[ReferencedText, ...]
    relationships: tuple[RelationshipProfile, ...]
    private_chronology: tuple[PrivateChronologyEntry, ...]
    voice_guidance: tuple[str, ...]
    evidence_connections: tuple[ReferencedText, ...]
    secondary_objective_ids: tuple[str, ...]
    moves: tuple[CharacterMove, ...]
    reveal_paths: tuple[RevealPath, ...]
    phase_arcs: tuple[PhaseArc, ...]
    ending_choices: tuple[EndingChoice, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CharacterDossier":
        return cls(
            str(value["dossier_id"]), str(value["seat_id"]),
            str(value["character_id"]), str(value["resource_id"]),
            int(value["target_pages"]),
            QuickStart.from_mapping(value["quick_start"]),
            KnowledgeBoundary.from_mapping(value["knowledge_boundary"]),
            tuple(ReferencedText.from_mapping(item) for item in value["personal_history"]),
            tuple(ReferencedText.from_mapping(item) for item in value["emotional_stakes"]),
            tuple(RelationshipProfile.from_mapping(item) for item in value["relationships"]),
            tuple(PrivateChronologyEntry.from_mapping(item) for item in value["private_chronology"]),
            _strings(value["voice_guidance"]),
            tuple(ReferencedText.from_mapping(item) for item in value["evidence_connections"]),
            _strings(value["secondary_objective_ids"]),
            tuple(CharacterMove.from_mapping(item) for item in value["moves"]),
            tuple(RevealPath.from_mapping(item) for item in value["reveal_paths"]),
            tuple(PhaseArc.from_mapping(item) for item in value["phase_arcs"]),
            tuple(EndingChoice.from_mapping(item) for item in value["ending_choices"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "seat_id": self.seat_id,
            "character_id": self.character_id,
            "resource_id": self.resource_id,
            "target_pages": self.target_pages,
            "quick_start": self.quick_start.to_mapping(),
            "knowledge_boundary": self.knowledge_boundary.to_mapping(),
            "personal_history": [item.to_mapping() for item in self.personal_history],
            "emotional_stakes": [item.to_mapping() for item in self.emotional_stakes],
            "relationships": [item.to_mapping() for item in self.relationships],
            "private_chronology": [item.to_mapping() for item in self.private_chronology],
            "voice_guidance": list(self.voice_guidance),
            "evidence_connections": [item.to_mapping() for item in self.evidence_connections],
            "secondary_objective_ids": list(self.secondary_objective_ids),
            "moves": [item.to_mapping() for item in self.moves],
            "reveal_paths": [item.to_mapping() for item in self.reveal_paths],
            "phase_arcs": [item.to_mapping() for item in self.phase_arcs],
            "ending_choices": [item.to_mapping() for item in self.ending_choices],
        }


@dataclass(frozen=True)
class CharacterProgram:
    public_proposition_ids: tuple[str, ...]
    private_knowledge_grants: tuple[KnowledgeGrant, ...]
    host_only_proposition_ids: tuple[str, ...]
    public_event_ids: tuple[str, ...]
    private_event_grants: tuple[EventGrant, ...]
    host_only_event_ids: tuple[str, ...]
    dossiers: tuple[CharacterDossier, ...]
    schema_version: str = CHARACTER_PROGRAM_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "CharacterProgram":
        return cls(
            _strings(value.get("public_proposition_ids")),
            tuple(KnowledgeGrant.from_mapping(item) for item in value.get("private_knowledge_grants", ())),
            _strings(value.get("host_only_proposition_ids")),
            _strings(value.get("public_event_ids")),
            tuple(EventGrant.from_mapping(item) for item in value.get("private_event_grants", ())),
            _strings(value.get("host_only_event_ids")),
            tuple(CharacterDossier.from_mapping(item) for item in value["dossiers"]),
            str(value.get("schema_version", "")),
        )

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "public_proposition_ids": list(self.public_proposition_ids),
            "private_knowledge_grants": [item.to_mapping() for item in self.private_knowledge_grants],
            "host_only_proposition_ids": list(self.host_only_proposition_ids),
            "public_event_ids": list(self.public_event_ids),
            "private_event_grants": [item.to_mapping() for item in self.private_event_grants],
            "host_only_event_ids": list(self.host_only_event_ids),
            "dossiers": [item.to_mapping() for item in self.dossiers],
        }

    @property
    def program_id(self) -> str:
        return f"character-program:{digest_json(self.material()).removeprefix('sha256:')}"

    def to_mapping(self) -> dict[str, Any]:
        return {"program_id": self.program_id, **self.material()}


def _texts(dossier: CharacterDossier) -> tuple[tuple[str, ReferencedText], ...]:
    result = [
        ("quick.public_identity", dossier.quick_start.public_identity),
        ("quick.private_truth", dossier.quick_start.private_truth),
        ("quick.first_move", dossier.quick_start.first_move),
    ]
    result.extend((f"personal_history.{index}", item) for index, item in enumerate(dossier.personal_history))
    result.extend((f"emotional_stakes.{index}", item) for index, item in enumerate(dossier.emotional_stakes))
    result.extend((f"evidence_connections.{index}", item) for index, item in enumerate(dossier.evidence_connections))
    for item in dossier.relationships:
        result.extend((
            (f"relationship.{item.character_id}.history", item.history),
            (f"relationship.{item.character_id}.tension", item.current_tension),
            (f"relationship.{item.character_id}.leverage", item.leverage),
            (f"relationship.{item.character_id}.alliance", item.likely_alliance),
        ))
    result.extend((f"chronology.{item.event_id}", item.perspective) for item in dossier.private_chronology)
    result.extend((f"move.{item.move_id}", item.instruction) for item in dossier.moves)
    result.extend((f"reveal.{item.reveal_path_id}", item.trigger) for item in dossier.reveal_paths)
    result.extend((f"phase.{item.phase_id}", item.pressure) for item in dossier.phase_arcs)
    result.extend((f"ending.{item.choice_id}", item.consequence) for item in dossier.ending_choices)
    return tuple(result)


def validate_character_program(game: Any, program: CharacterProgram) -> tuple[Finding, ...]:
    """Prove completeness, reachability, and seat-safe canonical references."""
    findings: list[Finding] = []
    if program.schema_version != CHARACTER_PROGRAM_SCHEMA_VERSION:
        findings.append(_finding("character.schema", "character_program", program.schema_version, "unsupported Character Program schema"))
    propositions = {item.id for item in game.propositions}
    events = {item.id for item in game.events}
    evidence = {item.id for item in game.evidence}
    resources = {item.id for item in game.kernel.resources}
    characters = {item.id: item for item in game.characters}
    seats = {item.id for item in game.kernel.seats}
    objectives = {item.id: item for item in game.objectives}
    phases = {item.id: item for item in game.phases}
    interventions = {item.id for item in game.interventions}
    truth = {item.proposition_id: item.value for item in game.truth_model}
    expected_seats = set(game.profile.supported_seat_ids)

    public_props = set(program.public_proposition_ids)
    host_props = set(program.host_only_proposition_ids)
    grants: dict[str, set[str]] = {}
    for item in program.private_knowledge_grants:
        grants.setdefault(item.proposition_id, set()).update(item.seat_ids)
    public_events = set(program.public_event_ids)
    host_events = set(program.host_only_event_ids)
    event_grants: dict[str, set[str]] = {}
    for item in program.private_event_grants:
        event_grants.setdefault(item.event_id, set()).update(item.seat_ids)
    for kind, known, universe in (
        ("public proposition", public_props, propositions),
        ("host proposition", host_props, propositions),
        ("private proposition", set(grants), propositions),
        ("public event", public_events, events),
        ("host event", host_events, events),
        ("private event", set(event_grants), events),
    ):
        for missing in sorted(known - universe):
            findings.append(_finding("character.dangling-reference", "character_program", missing, f"{kind} is not canonical"))
    if (public_props & host_props) or (public_props & set(grants)) or (host_props & set(grants)):
        findings.append(_finding("character.knowledge-overlap", "character_program.propositions", "overlap", "public, private, and host-only Proposition classes must be disjoint"))
    if (public_events & host_events) or (public_events & set(event_grants)) or (host_events & set(event_grants)):
        findings.append(_finding("character.knowledge-overlap", "character_program.events", "overlap", "public, private, and host-only Event classes must be disjoint"))
    for identifier, granted_seats in (*grants.items(), *event_grants.items()):
        for seat in sorted(granted_seats - seats):
            findings.append(_finding("character.dangling-reference", f"grant:{identifier}", seat, "knowledge Grant names a missing Seat"))

    dossier_seats = [item.seat_id for item in program.dossiers]
    dossier_ids = [item.dossier_id for item in program.dossiers]
    for duplicate in sorted(item for item, count in Counter(dossier_ids).items() if count > 1):
        findings.append(_finding("character.duplicate-id", f"dossier:{duplicate}", duplicate, "Dossier ID is duplicated"))
    if set(dossier_seats) != expected_seats or len(dossier_seats) != len(expected_seats):
        findings.append(_finding("character.incomplete-cast", "character_program.dossiers", ", ".join(sorted(dossier_seats)), "Character Program requires exactly one Dossier per supported Seat"))

    phase_order = {item.id: item.order for item in game.phases}
    reveal_phase_by_seat: dict[tuple[str, str], int] = {}
    for reveal in game.reveals:
        for seat in reveal.audience_seat_ids:
            key = (reveal.evidence_id, seat)
            reveal_phase_by_seat[key] = min(
                phase_order[reveal.phase_id], reveal_phase_by_seat.get(key, 10**9)
            )

    for dossier in program.dossiers:
        locus = f"dossier:{dossier.dossier_id}"
        character = characters.get(dossier.character_id)
        if dossier.seat_id not in seats or character is None or character.seat_id != dossier.seat_id:
            findings.append(_finding("character.dangling-reference", locus, dossier.character_id, "Dossier does not match one canonical Character and Seat"))
            continue
        if dossier.resource_id not in resources:
            findings.append(_finding("character.dangling-reference", locus, dossier.resource_id, "Dossier does not name one canonical Resource"))
        if not 3 <= dossier.target_pages <= 5:
            findings.append(_finding("character.page-target", locus, str(dossier.target_pages), "deep Dossier target must be three to five rendered pages"))
        authorized_props = public_props | {item for item, allowed in grants.items() if dossier.seat_id in allowed}
        authorized_events = public_events | {item for item, allowed in event_grants.items() if dossier.seat_id in allowed}
        boundary = dossier.knowledge_boundary
        boundary_props = set(boundary.known_fact_proposition_ids) | set(boundary.revisable_belief_proposition_ids) | set(boundary.permitted_lie_proposition_ids) | set(boundary.must_not_contradict_proposition_ids)
        for proposition_id in sorted(boundary_props - authorized_props):
            findings.append(_finding("character.unauthorized-knowledge", f"{locus}.knowledge", proposition_id, "Dossier Knowledge Boundary exceeds its canonical Grant"))
        if set(boundary.permitted_lie_proposition_ids) & set(boundary.must_not_contradict_proposition_ids):
            findings.append(_finding("character.contradictory-boundary", f"{locus}.knowledge", "lie / fixed fact", "one Proposition cannot be both lieable and non-contradictable"))
        for proposition_id in boundary.known_fact_proposition_ids:
            if truth.get(proposition_id) != "true":
                findings.append(_finding("character.contradictory-boundary", f"{locus}.known-facts", proposition_id, "known facts must be canonically true"))
        belief_ids = {item.proposition_id for item in character.beliefs}
        for proposition_id in set(boundary.revisable_belief_proposition_ids) - belief_ids:
            findings.append(_finding("character.contradictory-belief", f"{locus}.beliefs", proposition_id, "revisable belief is absent from the canonical Character"))
        owned_objectives = set(character.objective_ids)
        used_objectives = set(dossier.quick_start.immediate_objective_ids) | set(dossier.secondary_objective_ids)
        for arc in dossier.phase_arcs:
            used_objectives.update(arc.objective_ids)
        for objective_id in sorted(used_objectives - owned_objectives):
            findings.append(_finding("character.dangling-reference", f"{locus}.objectives", objective_id, "Dossier names another Character's Objective"))
        if not dossier.quick_start.public_identity.text.strip() or not dossier.quick_start.private_truth.text.strip() or not dossier.quick_start.first_move.text.strip() or not dossier.quick_start.immediate_objective_ids:
            findings.append(_finding("character.incomplete-quick-start", f"{locus}.quick_start", "incomplete", "Quick Start requires identity, private truth, immediate objectives, opening belief, and first move"))
        if set(dossier.quick_start.opening_belief_proposition_ids) - belief_ids:
            findings.append(_finding("character.contradictory-belief", f"{locus}.quick_start", "opening belief", "Quick Start opening belief is not canonical"))

        expected_relationships = set(characters) - {dossier.character_id}
        actual_relationships = [item.character_id for item in dossier.relationships]
        if set(actual_relationships) != expected_relationships or len(actual_relationships) != len(expected_relationships):
            findings.append(_finding("character.incomplete-relationships", f"{locus}.relationships", ", ".join(sorted(actual_relationships)), "Dossier requires one relationship with every other Character"))

        move_by_id = {item.move_id: item for item in dossier.moves}
        if len(move_by_id) != len(dossier.moves):
            findings.append(_finding("character.duplicate-id", f"{locus}.moves", "duplicate", "Move IDs must be unique within a Dossier"))
        reveal_by_id = {item.reveal_path_id: item for item in dossier.reveal_paths}
        if len(reveal_by_id) != len(dossier.reveal_paths):
            findings.append(_finding("character.duplicate-id", f"{locus}.reveals", "duplicate", "Reveal Path IDs must be unique within a Dossier"))
        arcs = {item.phase_id: item for item in dossier.phase_arcs}
        if set(arcs) != set(phases) or len(arcs) != len(phases):
            findings.append(_finding("character.incomplete-phase-arc", f"{locus}.phase_arcs", ", ".join(sorted(arcs)), "Dossier requires exactly one Phase Arc per canonical Phase"))
        for move in dossier.moves:
            if move.kind not in MOVE_KINDS:
                findings.append(_finding("character.invalid-move", f"{locus}.move:{move.move_id}", move.kind, "Move kind is unsupported"))
            for target in set(move.target_character_ids) | set(move.instruction.character_ids):
                if target not in characters:
                    findings.append(_finding("character.dangling-reference", f"{locus}.move:{move.move_id}", target, "Move names a missing Character"))
        for phase_id, arc in arcs.items():
            kinds = {move_by_id[item].kind for item in arc.move_ids if item in move_by_id}
            for missing in set(arc.move_ids) - set(move_by_id):
                findings.append(_finding("character.dangling-reference", f"{locus}.phase:{phase_id}", missing, "Phase Arc names a missing Move"))
            if not {"action", "fallback", "after_exposure"} <= kinds:
                findings.append(_finding("character.dead-end-state", f"{locus}.phase:{phase_id}", ", ".join(sorted(kinds)), "every Phase needs an action, fallback, and post-exposure Move"))
            for move_id in arc.move_ids:
                move = move_by_id.get(move_id)
                if move is None:
                    continue
                for evidence_id in move.instruction.evidence_ids:
                    if reveal_phase_by_seat.get((evidence_id, dossier.seat_id), 10**9) > phase_order[phase_id]:
                        findings.append(_finding("character.unavailable-evidence", f"{locus}.phase:{phase_id}", evidence_id, "Phase Move requires Evidence before this Seat can receive it"))
        if not any(item.kind == "bargain" for item in dossier.moves) or not any(item.kind == "challenge" for item in dossier.moves):
            findings.append(_finding("character.incomplete-agency", f"{locus}.moves", "bargain / challenge", "Dossier requires bargaining material and a directed challenge"))
        private_secrets = set(dossier.quick_start.private_truth.proposition_ids)
        covered_secrets = {item.secret_proposition_id for item in dossier.reveal_paths}
        for secret in sorted(private_secrets - covered_secrets):
            findings.append(_finding("character.unreachable-revelation", f"{locus}.private_truth", secret, "every private truth needs a fair Reveal Path"))
        for path in dossier.reveal_paths:
            if path.secret_proposition_id not in authorized_props or not path.phase_ids or any(item not in phases for item in path.phase_ids) or path.recovery_intervention_id not in interventions:
                findings.append(_finding("character.unreachable-revelation", f"{locus}.reveal:{path.reveal_path_id}", path.secret_proposition_id, "Reveal Path requires an authorized secret, valid window, and recovery Intervention"))
        if not dossier.ending_choices:
            findings.append(_finding("character.missing-resolution-choice", f"{locus}.ending_choices", "empty", "every Character needs a resolution choice"))

        for text_locus, text in _texts(dossier):
            if not text.text.strip():
                findings.append(_finding("character.empty-prose", f"{locus}.{text_locus}", "", "Dossier prose cannot be empty"))
            for proposition_id in text.proposition_ids:
                if proposition_id not in authorized_props:
                    findings.append(_finding("character.unauthorized-knowledge", f"{locus}.{text_locus}", proposition_id, "Dossier prose cites an unauthorized or host-only Proposition"))
            for event_id in text.event_ids:
                if event_id not in authorized_events:
                    findings.append(_finding("character.unauthorized-knowledge", f"{locus}.{text_locus}", event_id, "Dossier prose cites an unauthorized or host-only Event"))
            for evidence_id in text.evidence_ids:
                if evidence_id not in evidence or (evidence_id, dossier.seat_id) not in reveal_phase_by_seat:
                    findings.append(_finding("character.unauthorized-knowledge", f"{locus}.{text_locus}", evidence_id, "Dossier prose cites Evidence unavailable to this Seat"))
            for character_id in text.character_ids:
                if character_id not in characters:
                    findings.append(_finding("character.dangling-reference", f"{locus}.{text_locus}", character_id, "Dossier prose names a missing Character"))
    return tuple(sorted(set(findings)))


def render_dossier_markdown(game: Any, dossier: CharacterDossier) -> bytes:
    """Render a deterministic, scannable quick start followed by deep play."""
    characters = {item.id: item for item in game.characters}
    objectives = {item.id: item for item in game.objectives}
    propositions = {item.id: item.expression for item in game.propositions}
    events = {item.id: item.summary for item in game.events}
    phases = {item.id: item for item in game.phases}
    moves = {item.move_id: item for item in dossier.moves}
    reveals = {item.reveal_path_id: item for item in dossier.reveal_paths}
    lines = [
        f"# {characters[dossier.character_id].name}", "",
        "Private role dossier - read only your copy", "",
        "## Quick start - read this first", "",
        "### Who everyone sees", "", dossier.quick_start.public_identity.text, "",
        "### What only you know", "", dossier.quick_start.private_truth.text, "",
        "### What you want now", "",
        *[f"- {objectives[item].description}" for item in dossier.quick_start.immediate_objective_ids],
        "", "### Your opening belief", "",
        *[f"- {propositions[item]}" for item in dossier.quick_start.opening_belief_proposition_ids],
        "", "### Your first move", "", dossier.quick_start.first_move.text, "",
        "---", "", "## Deep play", "", "### Personal history", "",
        *[f"- {item.text}" for item in dossier.personal_history],
        "", "### Emotional stakes", "",
        *[f"- {item.text}" for item in dossier.emotional_stakes],
        "", "### Relationships", "",
    ]
    for relationship in dossier.relationships:
        lines.extend([
            f"#### {characters[relationship.character_id].name}", "",
            relationship.history.text, "", f"**Tension:** {relationship.current_tension.text}", "",
            f"**Leverage:** {relationship.leverage.text}", "",
            f"**Alliance:** {relationship.likely_alliance.text}", "",
        ])
    lines.extend(["### Private chronology", ""])
    for item in dossier.private_chronology:
        lines.append(f"- **From {phases[item.disclosure_phase_id].label}:** {events[item.event_id]} {item.perspective.text}")
    lines.extend(["", "### Knowledge boundary", "",
        "- **Facts you know:** " + "; ".join(propositions[item] for item in dossier.knowledge_boundary.known_fact_proposition_ids),
        "- **Beliefs you may revise:** " + "; ".join(propositions[item] for item in dossier.knowledge_boundary.revisable_belief_proposition_ids),
        "- **Claims you may lie about:** " + "; ".join(propositions[item] for item in dossier.knowledge_boundary.permitted_lie_proposition_ids),
        "- **Facts you may not contradict:** " + "; ".join(propositions[item] for item in dossier.knowledge_boundary.must_not_contradict_proposition_ids),
        "", "### Voice and play", "", *[f"- {item}" for item in dossier.voice_guidance],
        "", "### Evidence connections", "", *[f"- {item.text}" for item in dossier.evidence_connections],
        "", "## Phase playbook", "",
    ])
    for arc in sorted(dossier.phase_arcs, key=lambda item: phases[item.phase_id].order):
        lines.extend([f"### {phases[arc.phase_id].label}", "", arc.pressure.text, ""])
        for move_id in arc.move_ids:
            move = moves[move_id]
            lines.append(f"- **{move.kind.replace('_', ' ').title()}:** {move.instruction.text}")
        for reveal_id in arc.reveal_path_ids:
            path = reveals[reveal_id]
            lines.append(f"- **Reveal window:** {path.trigger.text} The host has a recovery path if this window is missed.")
        lines.append("")
    lines.extend(["## Your ending choices", ""])
    for choice in dossier.ending_choices:
        lines.append(f"- **{choice.label}:** {choice.consequence.text}")
    lines.extend(["", "This Dossier offers choices, not a script. Human direction may change your approach without changing canonical facts.", ""])
    return "\n".join(lines).encode("utf-8")


def phase_character_projection(
    game: Any, dossier: CharacterDossier, phase_id: str
) -> dict[str, Any]:
    """Return only the current Seat's active arc and authorized deep Dossier."""
    arc = next(item for item in dossier.phase_arcs if item.phase_id == phase_id)
    moves = {item.move_id: item for item in dossier.moves}
    return {
        "program_schema_version": CHARACTER_PROGRAM_SCHEMA_VERSION,
        "dossier_id": dossier.dossier_id,
        "target_pages": dossier.target_pages,
        "quick_start": dossier.quick_start.to_mapping(),
        "knowledge_boundary": dossier.knowledge_boundary.to_mapping(),
        "deep_play": {
            "personal_history": [item.to_mapping() for item in dossier.personal_history],
            "emotional_stakes": [item.to_mapping() for item in dossier.emotional_stakes],
            "relationships": [item.to_mapping() for item in dossier.relationships],
            "private_chronology": [item.to_mapping() for item in dossier.private_chronology],
            "voice_guidance": list(dossier.voice_guidance),
            "evidence_connections": [item.to_mapping() for item in dossier.evidence_connections],
            "secondary_objective_ids": list(dossier.secondary_objective_ids),
        },
        "active_arc": {
            **arc.to_mapping(),
            "moves": [moves[item].to_mapping() for item in arc.move_ids],
        },
        "ending_choices": [item.to_mapping() for item in dossier.ending_choices],
    }
