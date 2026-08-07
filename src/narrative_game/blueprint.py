"""Pure authoring contracts above the canonical Game Definition."""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
from typing import TYPE_CHECKING, Any, Iterable, Mapping

from narrative_game.compiler import MaterialInput
from narrative_game.contracts import (
    ArtifactResult,
    canonical_json,
    digest_bytes,
    digest_json,
)
from narrative_game.kernel import Finding, Resource
from narrative_game.narrative import GameDefinition, validate_facilitated_investigation

if TYPE_CHECKING:
    from narrative_game.generation.model import ArtifactSpecification


BLUEPRINT_SCHEMA_VERSION = "0.9"
_TEXT_MEDIA_TYPES = {"text/markdown", "text/plain", "text/csv"}
_OPERATION_KINDS = {
    "replace_direction",
    "replace_world",
    "replace_cast",
    "replace_deduction",
    "replace_arc",
    "replace_claims",
    "upsert_material",
    "remove_material",
}


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _finding(code: str, locus: str, quote: str, message: str) -> Finding:
    return Finding(code, "blocker", locus, quote, message)


@dataclass(frozen=True)
class RichTextMaterial:
    """One editable, deterministic source material in a Game Blueprint."""

    resource_id: str
    label: str
    media_type: str
    content: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RichTextMaterial":
        return cls(
            resource_id=str(value["resource_id"]),
            label=str(value["label"]),
            media_type=str(value["media_type"]),
            content=str(value["content"]),
        )

    @property
    def data(self) -> bytes:
        return self.content.encode("utf-8")

    @property
    def content_hash(self) -> str:
        return digest_bytes(self.data)

    def to_mapping(self) -> dict[str, str]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class ArcBeat:
    """The intended dramatic and temporal function of one authored Phase."""

    phase_id: str
    dramatic_question: str
    intended_shift: str
    target_minutes: int
    evidence_ids: tuple[str, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArcBeat":
        return cls(
            phase_id=str(value["phase_id"]),
            dramatic_question=str(value["dramatic_question"]),
            intended_shift=str(value["intended_shift"]),
            target_minutes=int(value["target_minutes"]),
            evidence_ids=tuple(str(item) for item in value.get("evidence_ids", ())),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "phase_id": self.phase_id,
            "dramatic_question": self.dramatic_question,
            "intended_shift": self.intended_shift,
            "target_minutes": self.target_minutes,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass(frozen=True)
class DisplayedClaim:
    """One visible material span traced to a canonical Proposition."""

    resource_id: str
    proposition_id: str
    quote: str
    source: str = "material-text"
    pin: str | None = None

    def __post_init__(self) -> None:
        if self.source not in {"material-text", "artifact-request"}:
            raise ValueError(f"unsupported displayed-claim source: {self.source}")
        if self.source == "material-text" and (not self.quote or self.pin is not None):
            raise ValueError("material-text claims require a quote and no request pin")
        if self.source == "artifact-request" and (
            not isinstance(self.pin, str) or not self.pin.strip()
        ):
            raise ValueError("artifact-request claims require an exact request pin")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "DisplayedClaim":
        return cls(
            resource_id=str(value["resource_id"]),
            proposition_id=str(value["proposition_id"]),
            quote=str(value.get("quote", "")),
            source=str(value.get("source", "material-text")),
            pin=(str(value["pin"]) if value.get("pin") is not None else None),
        )

    def to_mapping(self) -> dict[str, str]:
        result = {
            "resource_id": self.resource_id,
            "proposition_id": self.proposition_id,
            "source": self.source,
        }
        if self.source == "material-text":
            result["quote"] = self.quote
        else:
            assert self.pin is not None
            result["pin"] = self.pin
        return result


@dataclass(frozen=True)
class GameBlueprint:
    """An editable game source with text, artifact intent, and one canonical world."""

    game: Mapping[str, Any]
    materials: tuple[RichTextMaterial, ...]
    arc: tuple[ArcBeat, ...]
    displayed_claims: tuple[DisplayedClaim, ...]
    seed: int
    schema_version: str = BLUEPRINT_SCHEMA_VERSION
    artifact_specifications: tuple["ArtifactSpecification", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "game", _copy(self.game))
        if "resources" in self.game.get("kernel", {}):
            raise ValueError(
                "Blueprint game kernel must omit Resources; Materials derive them"
            )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "GameBlueprint":
        from narrative_game.generation.model import ArtifactSpecification

        return cls(
            game=value["game"],
            materials=tuple(
                RichTextMaterial.from_mapping(item) for item in value.get("materials", ())
            ),
            arc=tuple(ArcBeat.from_mapping(item) for item in value.get("arc", ())),
            displayed_claims=tuple(
                DisplayedClaim.from_mapping(item)
                for item in value.get("displayed_claims", ())
            ),
            seed=int(value["seed"]),
            artifact_specifications=tuple(
                ArtifactSpecification.from_mapping(item)
                for item in value.get("artifact_specifications", ())
            ),
            schema_version=str(value.get("schema_version", "")),
        )

    def to_mapping(self) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "game": _copy(self.game),
            "materials": [item.to_mapping() for item in self.materials],
            "arc": [item.to_mapping() for item in self.arc],
            "displayed_claims": [item.to_mapping() for item in self.displayed_claims],
            "seed": self.seed,
        }
        # Schema 0.9 Blueprints predate artifact planning. Keeping the key absent
        # when empty preserves their exact serialized form and content identity.
        if self.artifact_specifications:
            result["artifact_specifications"] = [
                item.to_mapping() for item in self.artifact_specifications
            ]
        return result

    def materialize_game(
        self,
        artifact_results: Mapping[str, ArtifactResult] | None = None,
        artifact_media_types: Mapping[str, str] | None = None,
    ) -> GameDefinition:
        """Derive canonical Resource hashes from the rich-text sources."""
        artifact_results = dict(artifact_results or {})
        artifact_media_types = dict(artifact_media_types or {})
        mapping = _copy(self.game)
        kernel = mapping.setdefault("kernel", {})
        kernel["resources"] = [
            Resource(
                item.resource_id,
                artifact_media_types.get(item.resource_id, item.media_type),
                (
                    artifact_results[item.resource_id].content_hash
                    if item.resource_id in artifact_results
                    else item.content_hash
                ),
                item.label,
            ).__dict__
            for item in self.materials
        ]
        return GameDefinition.from_mapping(mapping)

    def material_inputs(
        self,
        artifact_results: Mapping[str, ArtifactResult] | None = None,
        *,
        artifact_media_types: Mapping[str, str] | None = None,
        suite_attestation: Mapping[str, Any] | None = None,
    ) -> tuple[MaterialInput, ...]:
        artifact_results = dict(artifact_results or {})
        artifact_media_types = dict(artifact_media_types or {})
        return tuple(
            MaterialInput(
                item.resource_id,
                artifact_media_types.get(item.resource_id, item.media_type),
                (
                    artifact_results[item.resource_id].document
                    if item.resource_id in artifact_results
                    else item.data
                ),
                (
                    {
                        "kind": "verismill-artifact-suite-member",
                        "schema_version": BLUEPRINT_SCHEMA_VERSION,
                        "artifact_request": dict(
                            artifact_results[item.resource_id].request
                        ),
                        "artifact_manifest": dict(
                            artifact_results[item.resource_id].manifest
                        ),
                        "suite_attestation": _copy(suite_attestation or {}),
                    }
                    if item.resource_id in artifact_results
                    else {
                        "kind": "authored-rich-text",
                        "schema_version": BLUEPRINT_SCHEMA_VERSION,
                        "source_hash": item.content_hash,
                    }
                ),
                (
                    dict(artifact_results[item.resource_id].attestation)
                    if item.resource_id in artifact_results
                    else None
                ),
            )
            for item in self.materials
        )


def artifact_truth_binding_material(
    blueprint: GameBlueprint, specification: "ArtifactSpecification"
) -> dict[str, Any]:
    """Project the exact canonical facts one artifact request claims to express.

    Mattermill pins and canon are emitter-specific values, so this layer cannot
    safely infer their meaning. It can make them non-floating: the projection
    binds those exact values to the complete referenced Proposition meanings,
    truth assignments, and represented Events.
    """

    game = blueprint.materialize_game()
    propositions = {item.id: item for item in game.propositions}
    events = {item.id: item for item in game.events}
    truth_by_proposition: dict[str, list[Any]] = {}
    for assignment in game.truth_model:
        truth_by_proposition.setdefault(assignment.proposition_id, []).append(assignment)

    proposition_material = []
    for proposition_id in specification.proposition_ids:
        if proposition_id not in propositions:
            raise ValueError(f"missing canonical Proposition: {proposition_id}")
        assignments = truth_by_proposition.get(proposition_id, [])
        if len(assignments) != 1:
            raise ValueError(
                f"canonical Proposition {proposition_id} must have exactly one truth assignment"
            )
        proposition = propositions[proposition_id]
        proposition_material.append(
            {
                "proposition": {
                    "id": proposition.id,
                    "expression": proposition.expression,
                },
                "truth_assignment": {
                    "proposition_id": assignments[0].proposition_id,
                    "value": assignments[0].value,
                },
            }
        )

    event_material = []
    for event_id in specification.event_ids:
        if event_id not in events:
            raise ValueError(f"missing represented Event: {event_id}")
        event = events[event_id]
        event_material.append(
            {
                "id": event.id,
                "summary": event.summary,
                "order": event.order,
                "proposition_ids": list(event.proposition_ids),
                "causes": list(event.causes),
            }
        )

    return {
        "schema_version": "artifact-truth-binding.1",
        "artifact_id": specification.artifact_id,
        "resource_id": specification.resource_id,
        "request_truth_values": {
            "pins": _copy(specification.pins),
            "canon": _copy(specification.canon),
        },
        "propositions": proposition_material,
        "events": event_material,
    }


def derive_artifact_truth_binding(
    blueprint: GameBlueprint, specification: "ArtifactSpecification"
) -> str:
    """Derive the content identity that invalidates an artifact on world drift."""

    return digest_json(artifact_truth_binding_material(blueprint, specification))


def bind_artifact_specification(
    blueprint: GameBlueprint, specification: "ArtifactSpecification"
) -> "ArtifactSpecification":
    """Return the specification bound to this Blueprint's current canonical world."""

    return replace(
        specification,
        truth_binding=derive_artifact_truth_binding(blueprint, specification),
    )


@dataclass(frozen=True)
class AuthoringOperation:
    """One reviewable domain-sized change to a Game Blueprint."""

    operation_id: str
    kind: str
    requirement_ids: tuple[str, ...]
    rationale: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", _copy(self.payload))
        if self.kind not in _OPERATION_KINDS:
            raise ValueError(f"unsupported authoring operation: {self.kind}")
        if not self.operation_id or not self.rationale.strip():
            raise ValueError("authoring operations require identity and rationale")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AuthoringOperation":
        return cls(
            operation_id=str(value["operation_id"]),
            kind=str(value["kind"]),
            requirement_ids=tuple(str(item) for item in value.get("requirement_ids", ())),
            rationale=str(value["rationale"]),
            payload=value.get("payload", {}),
        )


@dataclass(frozen=True)
class BlueprintProposal:
    """An inert set of domain operations returned by an authoring agent."""

    operations: tuple[AuthoringOperation, ...]
    rationale: str
    schema_version: str = BLUEPRINT_SCHEMA_VERSION

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "BlueprintProposal":
        return cls(
            operations=tuple(
                AuthoringOperation.from_mapping(item) for item in value.get("operations", ())
            ),
            rationale=str(value.get("rationale", "")),
            schema_version=str(value.get("schema_version", "")),
        )


def validate_blueprint(blueprint: GameBlueprint) -> tuple[Finding, ...]:
    """Validate authoring intent and the canonical game it deterministically derives."""
    findings: list[Finding] = []
    if blueprint.schema_version != BLUEPRINT_SCHEMA_VERSION:
        findings.append(
            _finding(
                "authoring.schema-version",
                "blueprint.schema-version",
                blueprint.schema_version,
                f"Game Blueprint must use schema {BLUEPRINT_SCHEMA_VERSION}",
            )
        )
    material_ids = [item.resource_id for item in blueprint.materials]
    duplicate_materials = sorted({item for item in material_ids if material_ids.count(item) > 1})
    for resource_id in duplicate_materials:
        findings.append(
            _finding(
                "authoring.duplicate-material",
                f"material:{resource_id}",
                resource_id,
                "one Resource has more than one editable source",
            )
        )
    for item in blueprint.materials:
        if item.media_type not in _TEXT_MEDIA_TYPES:
            findings.append(
                _finding(
                    "authoring.unsupported-rich-text",
                    f"material:{item.resource_id}.media-type",
                    item.media_type,
                    "editable Blueprint materials must use a supported text media type",
                )
            )
        if not item.label.strip() or not item.content.strip():
            findings.append(
                _finding(
                    "authoring.empty-material",
                    f"material:{item.resource_id}",
                    item.label or item.resource_id,
                    "every authored material requires a label and visible content",
                )
            )
    try:
        game = blueprint.materialize_game()
    except (KeyError, TypeError, ValueError) as exc:
        findings.append(
            _finding(
                "authoring.invalid-game-definition",
                "blueprint.game",
                type(exc).__name__,
                str(exc),
            )
        )
        return tuple(sorted(set(findings)))
    findings.extend(validate_facilitated_investigation(game))
    phase_ids = [item.id for item in sorted(game.phases, key=lambda item: item.order)]
    beat_ids = [item.phase_id for item in blueprint.arc]
    if beat_ids != phase_ids:
        findings.append(
            _finding(
                "authoring.arc-coverage",
                "blueprint.arc",
                ", ".join(beat_ids),
                "Arc Beats must cover every Phase exactly once in Phase order",
            )
        )
    evidence_ids = {item.id for item in game.evidence}
    proposition_ids = {item.id for item in game.propositions}
    material_by_id = {item.resource_id: item for item in blueprint.materials}
    artifact_ids = [item.artifact_id for item in blueprint.artifact_specifications]
    artifact_resource_ids = [
        item.resource_id for item in blueprint.artifact_specifications
    ]
    for artifact_id in sorted(
        {item for item in artifact_ids if artifact_ids.count(item) > 1}
    ):
        findings.append(
            _finding(
                "authoring.duplicate-artifact-specification",
                f"artifact:{artifact_id}",
                artifact_id,
                "one artifact identity has more than one specification",
            )
        )
    for resource_id in sorted(
        {
            item
            for item in artifact_resource_ids
            if artifact_resource_ids.count(item) > 1
        }
    ):
        findings.append(
            _finding(
                "authoring.duplicate-artifact-resource",
                f"material:{resource_id}",
                resource_id,
                "one authored Resource has more than one artifact specification",
            )
        )
    event_ids = {item.id for item in game.events}
    seat_ids = {item.id for item in game.kernel.seats}
    for specification in blueprint.artifact_specifications:
        if specification.resource_id not in material_by_id:
            findings.append(
                _finding(
                    "authoring.dangling-artifact-resource",
                    f"artifact:{specification.artifact_id}.resource",
                    specification.resource_id,
                    "Artifact Specification must name an authored Resource",
                )
            )
        unknown_propositions = sorted(
            set(specification.proposition_ids) - proposition_ids
        )
        if unknown_propositions:
            findings.append(
                _finding(
                    "authoring.dangling-artifact-proposition",
                    f"artifact:{specification.artifact_id}.propositions",
                    ", ".join(unknown_propositions),
                    "Artifact Specification refers to missing canonical Propositions",
                )
            )
        unknown_events = sorted(set(specification.event_ids) - event_ids)
        if unknown_events:
            findings.append(
                _finding(
                    "authoring.dangling-artifact-event",
                    f"artifact:{specification.artifact_id}.events",
                    ", ".join(unknown_events),
                    "Artifact Specification refers to missing represented Events",
                )
            )
        if not unknown_propositions and not unknown_events:
            try:
                expected_binding = derive_artifact_truth_binding(
                    blueprint, specification
                )
            except ValueError as exc:
                findings.append(
                    _finding(
                        "authoring.invalid-artifact-truth-projection",
                        f"artifact:{specification.artifact_id}.truth-binding",
                        specification.truth_binding,
                        str(exc),
                    )
                )
            else:
                if specification.truth_binding != expected_binding:
                    findings.append(
                        _finding(
                            "authoring.stale-artifact-truth-binding",
                            f"artifact:{specification.artifact_id}.truth-binding",
                            specification.truth_binding,
                            "Artifact Specification pins/canon are not bound to the "
                            "current canonical Proposition, truth, and Event projection",
                        )
                    )
        unknown_audiences = sorted(
            set(specification.permitted_audience_ids) - seat_ids - {"host"}
        )
        if unknown_audiences:
            findings.append(
                _finding(
                    "authoring.dangling-artifact-audience",
                    f"artifact:{specification.artifact_id}.audiences",
                    ", ".join(unknown_audiences),
                    "Artifact Specification refers to an unsupported Seat or audience",
                )
            )
    claimed_resources: set[str] = set()
    artifact_by_resource = {
        item.resource_id: item for item in blueprint.artifact_specifications
    }
    for claim in blueprint.displayed_claims:
        material = material_by_id.get(claim.resource_id)
        if material is None or claim.proposition_id not in proposition_ids:
            findings.append(
                _finding(
                    "authoring.dangling-displayed-claim",
                    f"claim:{claim.resource_id}",
                    f"{claim.resource_id} -> {claim.proposition_id}",
                    "Displayed Claim must name an authored Resource and canonical Proposition",
                )
            )
        elif claim.source == "material-text" and (
            not claim.quote or claim.quote not in material.content
        ):
            findings.append(
                _finding(
                    "authoring.unquoted-displayed-claim",
                    f"claim:{claim.resource_id}",
                    claim.quote,
                    "Displayed Claim quote must be an exact visible span in its Material",
                )
            )
        elif claim.source == "artifact-request":
            specification = artifact_by_resource.get(claim.resource_id)
            if (
                specification is None
                or claim.proposition_id not in specification.proposition_ids
                or claim.pin not in specification.pins
            ):
                findings.append(
                    _finding(
                        "authoring.invalid-artifact-claim",
                        f"claim:{claim.resource_id}",
                        claim.pin or "",
                        "Artifact Claim must name a planned request pin and fact reference",
                    )
                )
            else:
                claimed_resources.add(claim.resource_id)
        else:
            claimed_resources.add(claim.resource_id)
    untraced = sorted({item.resource_id for item in game.evidence} - claimed_resources)
    if untraced:
        findings.append(
            _finding(
                "authoring.untraced-evidence-material",
                "blueprint.displayed-claims",
                ", ".join(untraced),
                "every Evidence Material needs at least one visible canonical claim trace",
            )
        )
    revealed_by_phase: dict[str, set[str]] = {item: set() for item in phase_ids}
    for reveal in game.reveals:
        revealed_by_phase.setdefault(reveal.phase_id, set()).add(reveal.evidence_id)
    for beat in blueprint.arc:
        unknown = sorted(set(beat.evidence_ids) - evidence_ids)
        if unknown:
            findings.append(
                _finding(
                    "authoring.arc-evidence",
                    f"arc:{beat.phase_id}.evidence",
                    ", ".join(unknown),
                    "Arc Beat refers to missing Evidence",
                )
            )
        if set(beat.evidence_ids) != revealed_by_phase.get(beat.phase_id, set()):
            findings.append(
                _finding(
                    "authoring.arc-reveal-drift",
                    f"arc:{beat.phase_id}.evidence",
                    ", ".join(beat.evidence_ids),
                    "Arc Beat evidence must equal the Evidence revealed in its Phase",
                )
            )
        if beat.target_minutes < 1 or not beat.dramatic_question.strip() or not beat.intended_shift.strip():
            findings.append(
                _finding(
                    "authoring.incomplete-beat",
                    f"arc:{beat.phase_id}",
                    str(beat.target_minutes),
                    "every Arc Beat needs a question, intended shift, and positive duration",
                )
            )
    return tuple(sorted(set(findings)))


_REPLACEMENTS: Mapping[str, tuple[str, ...]] = {
    "replace_direction": ("direction",),
    "replace_world": ("propositions", "truth_model", "events"),
    "replace_cast": ("objectives", "characters"),
    "replace_deduction": ("hypotheses", "evidence", "proof_paths", "resolution"),
}


def apply_blueprint_proposal(
    blueprint: GameBlueprint,
    proposal: BlueprintProposal,
    *,
    required_requirement_ids: Iterable[str] = (),
) -> GameBlueprint:
    """Apply declared operations without repairing or inferring missing intent."""
    if proposal.schema_version != BLUEPRINT_SCHEMA_VERSION or not proposal.rationale.strip():
        raise ValueError("Blueprint Proposal requires the current schema and rationale")
    if not proposal.operations:
        raise ValueError("Blueprint Proposal requires at least one operation")
    operation_ids = [item.operation_id for item in proposal.operations]
    if len(operation_ids) != len(set(operation_ids)):
        raise ValueError("Blueprint Proposal contains duplicate operation identities")
    required = set(required_requirement_ids)
    covered = {item for operation in proposal.operations for item in operation.requirement_ids}
    if covered - required:
        raise ValueError("Blueprint Proposal cites unknown Requirement identities")
    if required - covered:
        raise ValueError("Blueprint Proposal does not address every Requirement")

    result = blueprint.to_mapping()
    narrative = result["game"]["narrative"]
    materials = {item["resource_id"]: item for item in result["materials"]}
    for operation in proposal.operations:
        if operation.kind in _REPLACEMENTS:
            expected = set(_REPLACEMENTS[operation.kind])
            if set(operation.payload) != expected:
                raise ValueError(
                    f"{operation.kind} payload must contain exactly {sorted(expected)}"
                )
            for key in _REPLACEMENTS[operation.kind]:
                narrative[key] = _copy(operation.payload[key])
        elif operation.kind == "replace_arc":
            expected = {"phases", "reveals", "interventions", "arc"}
            if set(operation.payload) != expected:
                raise ValueError(f"replace_arc payload must contain exactly {sorted(expected)}")
            for key in ("phases", "reveals", "interventions"):
                narrative[key] = _copy(operation.payload[key])
            result["arc"] = _copy(operation.payload["arc"])
        elif operation.kind == "replace_claims":
            if set(operation.payload) != {"displayed_claims"}:
                raise ValueError("replace_claims payload requires only displayed_claims")
            result["displayed_claims"] = _copy(operation.payload["displayed_claims"])
        elif operation.kind == "upsert_material":
            material = RichTextMaterial.from_mapping(operation.payload)
            materials[material.resource_id] = material.to_mapping()
        elif operation.kind == "remove_material":
            if set(operation.payload) != {"resource_id"}:
                raise ValueError("remove_material payload requires only resource_id")
            resource_id = str(operation.payload["resource_id"])
            if resource_id not in materials:
                raise ValueError(f"cannot remove missing Material: {resource_id}")
            materials.pop(resource_id)
    result["materials"] = list(materials.values())
    revised = GameBlueprint.from_mapping(result)
    findings = validate_blueprint(revised)
    if findings:
        first = findings[0]
        raise ValueError(f"proposed Blueprint is invalid: {first.code} at {first.locus}")
    return revised
