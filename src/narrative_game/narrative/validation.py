"""Deterministic validation for the Facilitated Investigation profile."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from narrative_game.kernel import Finding, validate_kernel

from .model import GameDefinition
from .characters import validate_character_program


def _finding(code: str, locus: str, quote: str, message: str) -> Finding:
    return Finding(code=code, severity="blocker", locus=locus, quote=quote, message=message)


def _duplicates(kind: str, identifiers: Iterable[str]) -> list[Finding]:
    return [
        _finding(
            "narrative.duplicate-id",
            f"{kind}:{identifier}",
            identifier,
            f"{kind} identifier is duplicated",
        )
        for identifier, count in Counter(identifiers).items()
        if count > 1
    ]


def validate_facilitated_investigation(game: GameDefinition) -> tuple[Finding, ...]:
    """Return stable Findings; never mutate, repair, fetch, or infer author intent."""
    findings = list(validate_kernel(game.kernel))
    proposition_ids = {item.id for item in game.propositions}
    event_by_id = {item.id: item for item in game.events}
    seat_ids = {item.id for item in game.kernel.seats}
    resource_ids = {item.id for item in game.kernel.resources}
    phase_by_id = {item.id: item for item in game.phases}
    objective_ids = {item.id for item in game.objectives}
    hypothesis_ids = {item.id for item in game.hypotheses}
    evidence_by_id = {item.id: item for item in game.evidence}
    proof_by_id = {item.id: item for item in game.proof_paths}

    for kind, identifiers in (
        ("proposition", [item.id for item in game.propositions]),
        ("event", [item.id for item in game.events]),
        ("character", [item.id for item in game.characters]),
        ("objective", [item.id for item in game.objectives]),
        ("hypothesis", [item.id for item in game.hypotheses]),
        ("evidence", [item.id for item in game.evidence]),
        ("proof-path", [item.id for item in game.proof_paths]),
        ("phase", [item.id for item in game.phases]),
        ("reveal", [item.id for item in game.reveals]),
        ("intervention", [item.id for item in game.interventions]),
    ):
        findings.extend(_duplicates(kind, identifiers))

    truth: dict[str, str] = {}
    for assignment in game.truth_model:
        if assignment.proposition_id not in proposition_ids:
            findings.append(
                _finding(
                    "narrative.dangling-reference",
                    f"truth:{assignment.proposition_id}",
                    assignment.proposition_id,
                    "Truth Model refers to a missing Proposition",
                )
            )
        if assignment.value not in {"true", "false", "unresolved"}:
            findings.append(
                _finding(
                    "narrative.invalid-truth",
                    f"truth:{assignment.proposition_id}",
                    assignment.value,
                    "Truth value must be true, false, or unresolved",
                )
            )
        previous = truth.get(assignment.proposition_id)
        if previous is not None and previous != assignment.value:
            findings.append(
                _finding(
                    "narrative.contradictory-truth",
                    f"truth:{assignment.proposition_id}",
                    f"{previous} / {assignment.value}",
                    "one Proposition has contradictory Truth assignments",
                )
            )
        truth[assignment.proposition_id] = assignment.value
    for proposition_id in sorted(proposition_ids - set(truth)):
        findings.append(
            _finding(
                "narrative.incomplete-truth",
                f"proposition:{proposition_id}",
                proposition_id,
                "Proposition has no canonical Truth assignment",
            )
        )

    def dangling(locus: str, quote: str, exists: bool, message: str) -> None:
        if not exists:
            findings.append(_finding("narrative.dangling-reference", locus, quote, message))

    for event in game.events:
        for proposition_id in event.proposition_ids:
            dangling(
                f"event:{event.id}.propositions",
                proposition_id,
                proposition_id in proposition_ids,
                "World Event refers to a missing Proposition",
            )
        for cause_id in event.causes:
            dangling(
                f"event:{event.id}.causes",
                cause_id,
                cause_id in event_by_id,
                "World Event refers to a missing cause Event",
            )
            if cause_id in event_by_id and event_by_id[cause_id].order >= event.order:
                findings.append(
                    _finding(
                        "narrative.impossible-chronology",
                        f"event:{event.id}.causes",
                        f"{cause_id}@{event_by_id[cause_id].order} -> {event.id}@{event.order}",
                        "a cause must occur before its resulting Event",
                    )
                )
    for objective in game.objectives:
        dangling(
            f"objective:{objective.id}.activation",
            objective.activation_phase_id,
            objective.activation_phase_id in phase_by_id,
            "Objective refers to a missing activation Phase",
        )
    for character in game.characters:
        dangling(
            f"character:{character.id}.seat",
            character.seat_id,
            character.seat_id in seat_ids,
            "Character refers to a missing Seat",
        )
        for objective_id in character.objective_ids:
            dangling(
                f"character:{character.id}.objectives",
                objective_id,
                objective_id in objective_ids,
                "Character refers to a missing Objective",
            )
        for belief in character.beliefs:
            dangling(
                f"character:{character.id}.beliefs",
                belief.proposition_id,
                belief.proposition_id in proposition_ids,
                "Belief refers to a missing Proposition",
            )
    for hypothesis in game.hypotheses:
        for proposition_id in hypothesis.proposition_ids:
            dangling(
                f"hypothesis:{hypothesis.id}.propositions",
                proposition_id,
                proposition_id in proposition_ids,
                "Hypothesis refers to a missing Proposition",
            )
    for evidence in game.evidence:
        dangling(
            f"evidence:{evidence.id}.resource",
            evidence.resource_id,
            evidence.resource_id in resource_ids,
            "Evidence refers to a missing Kernel Resource",
        )
        for relation in evidence.relations:
            targets = proposition_ids if relation.target_kind == "proposition" else hypothesis_ids
            dangling(
                f"evidence:{evidence.id}.relations",
                f"{relation.target_kind}:{relation.target_id}",
                relation.target_kind in {"proposition", "hypothesis"}
                and relation.target_id in targets,
                "Evidence Relation refers to a missing narrative target",
            )
    for proof in game.proof_paths:
        dangling(
            f"proof-path:{proof.id}.hypothesis",
            proof.hypothesis_id,
            proof.hypothesis_id in hypothesis_ids,
            "Proof Path refers to a missing Hypothesis",
        )
        for evidence_id in proof.evidence_ids:
            dangling(
                f"proof-path:{proof.id}.evidence",
                evidence_id,
                evidence_id in evidence_by_id,
                "Proof Path refers to missing Evidence",
            )
    for reveal in game.reveals:
        dangling(
            f"reveal:{reveal.id}.evidence",
            reveal.evidence_id,
            reveal.evidence_id in evidence_by_id,
            "Reveal refers to missing Evidence",
        )
        dangling(
            f"reveal:{reveal.id}.phase",
            reveal.phase_id,
            reveal.phase_id in phase_by_id,
            "Reveal refers to a missing Phase",
        )
        for seat_id in reveal.audience_seat_ids:
            dangling(
                f"reveal:{reveal.id}.audience",
                seat_id,
                seat_id in seat_ids,
                "Reveal refers to a missing audience Seat",
            )
    for intervention in game.interventions:
        dangling(
            f"intervention:{intervention.id}.phase",
            intervention.phase_id,
            intervention.phase_id in phase_by_id,
            "Intervention refers to a missing Phase",
        )
        for evidence_id in intervention.evidence_ids:
            dangling(
                f"intervention:{intervention.id}.evidence",
                evidence_id,
                evidence_id in evidence_by_id,
                "Intervention refers to missing Evidence",
            )
    dangling(
        "resolution.hypothesis",
        game.resolution.correct_hypothesis_id,
        game.resolution.correct_hypothesis_id in hypothesis_ids,
        "Resolution refers to a missing correct Hypothesis",
    )
    dangling(
        "resolution.phase",
        game.resolution.phase_id,
        game.resolution.phase_id in phase_by_id,
        "Resolution refers to a missing Phase",
    )
    for proof_id in game.resolution.acceptable_proof_path_ids:
        dangling(
            "resolution.proof-paths",
            proof_id,
            proof_id in proof_by_id,
            "Resolution refers to a missing acceptable Proof Path",
        )

    for seat_id in game.profile.supported_seat_ids:
        dangling(
            "profile.supported-seats",
            seat_id,
            seat_id in seat_ids,
            "profile refers to a missing supported Seat",
        )
    findings.extend(_duplicates("cast-variant", [item.id for item in game.profile.cast_variants]))
    if not game.profile.cast_variants or any(not item.seat_ids for item in game.profile.cast_variants):
        findings.append(
            _finding(
                "facilitated.cast-contract",
                "profile.cast-variants",
                "empty cast variant",
                "the profile must declare at least one non-empty supported cast variant",
            )
        )
    narrative_extensions = [
        extension
        for extension in game.kernel.extensions
        if extension.namespace == "org.narrativegame.narrative"
    ]
    if len(narrative_extensions) != 1 or narrative_extensions[0].profile != (
        f"{game.profile.id}@{game.profile.version}"
    ):
        findings.append(
            _finding(
                "facilitated.extension-contract",
                "kernel.extensions",
                "org.narrativegame.narrative",
                "the active Narrative extension must pin the selected profile and version",
            )
        )
    if game.profile.id != "facilitated-investigation" or not game.profile.host_required:
        findings.append(
            _finding(
                "facilitated.profile-contract",
                "profile",
                f"{game.profile.id}; host_required={game.profile.host_required}",
                "version one requires the host-led Facilitated Investigation profile",
            )
        )

    has_dangling = any(item.code.endswith("dangling-reference") for item in findings)
    if not has_dangling:
        findings.extend(_validate_access_and_progression(game))
        if game.character_program is not None:
            findings.extend(validate_character_program(game, game.character_program))
    return tuple(sorted(set(findings)))


def _validate_access_and_progression(game: GameDefinition) -> list[Finding]:
    findings: list[Finding] = []
    supported_seats = set(game.profile.supported_seat_ids)
    evidence_by_id = {item.id: item for item in game.evidence}
    phase_order = {item.id: item.order for item in game.phases}
    resolution_order = phase_order[game.resolution.phase_id]
    proof_by_id = {item.id: item for item in game.proof_paths}
    allowed_by_resource: dict[str, set[str]] = defaultdict(set)
    for policy in game.kernel.access_policies:
        allowed_by_resource[policy.resource.id].update(
            grantee.id for grantee in policy.grantees if grantee.kind == "seat"
        )
    reveal_orders: dict[str, list[int]] = defaultdict(list)
    authorized_reveals: list[tuple[str, set[str], int]] = []
    for reveal in game.reveals:
        resource_id = evidence_by_id[reveal.evidence_id].resource_id
        unauthorized = set(reveal.audience_seat_ids) - allowed_by_resource[resource_id]
        if unauthorized:
            findings.append(
                _finding(
                    "facilitated.unauthorized-disclosure",
                    f"reveal:{reveal.id}.audience",
                    ", ".join(sorted(unauthorized)),
                    "Reveal grants Evidence beyond its Kernel Access Policy",
                )
            )
        authorized_audience = (
            set(reveal.audience_seat_ids) & allowed_by_resource[resource_id] & supported_seats
        )
        if authorized_audience and phase_order[reveal.phase_id] <= resolution_order:
            authorized_reveals.append(
                (reveal.evidence_id, authorized_audience, phase_order[reveal.phase_id])
            )
            reveal_orders[reveal.evidence_id].append(phase_order[reveal.phase_id])

    acceptable = [proof_by_id[item] for item in game.resolution.acceptable_proof_path_ids]
    inaccessible_by_variant = []
    for variant in game.profile.cast_variants:
        seats = set(variant.seat_ids)
        accessible_evidence = {
            evidence_id
            for evidence_id, audience, _ in authorized_reveals
            if audience & seats
        }
        inaccessible = sorted(
            {
                evidence_id
                for proof in acceptable
                for evidence_id in proof.evidence_ids
                if evidence_id not in accessible_evidence
            }
        )
        if inaccessible:
            inaccessible_by_variant.append(variant.id)
            findings.append(
                _finding(
                    "facilitated.inaccessible-critical-evidence",
                    f"cast-variant:{variant.id}",
                    ", ".join(inaccessible),
                    "critical Evidence cannot reach this supported cast by resolution",
                )
            )
    if not inaccessible_by_variant:
        if len(acceptable) < 2:
            findings.append(
                _finding(
                    "facilitated.single-point-proof-failure",
                    "resolution.proof-paths",
                    ", ".join(item.id for item in acceptable),
                    "resolution has fewer than two declared independent Proof Paths",
                )
            )
        elif common_evidence := set.intersection(
            *(set(proof.evidence_ids) for proof in acceptable)
        ):
            findings.append(
                _finding(
                    "facilitated.single-point-proof-failure",
                    "resolution.proof-paths",
                    ", ".join(sorted(common_evidence)),
                    "every acceptable Proof Path depends on the same critical Evidence",
                )
            )
        premature = [
            proof.id
            for proof in acceptable
            if max(min(reveal_orders[item]) for item in proof.evidence_ids) < resolution_order
        ]
        if premature:
            findings.append(
                _finding(
                    "facilitated.premature-proof",
                    "resolution.phase",
                    ", ".join(premature),
                    "a complete acceptable Proof Path is available before the Resolution Phase",
                )
            )

    characters_by_seat = {character.seat_id: character for character in game.characters}
    revealed_to: dict[str, set[str]] = defaultdict(set)
    for reveal in game.reveals:
        for seat_id in reveal.audience_seat_ids:
            revealed_to[seat_id].add(reveal.evidence_id)
    inactive = []
    for seat_id in sorted(supported_seats):
        character = characters_by_seat.get(seat_id)
        if character is None or not character.objective_ids or not revealed_to[seat_id]:
            inactive.append(seat_id)
    if inactive:
        findings.append(
            _finding(
                "facilitated.inactive-seat",
                "profile.supported-seats",
                ", ".join(inactive),
                "every supported Seat needs a Character, Objective, and evidence opportunity",
            )
        )

    proof_evidence = {item for proof in acceptable for item in proof.evidence_ids}
    recovery = [
        item
        for item in game.interventions
        if item.kind in {"hint", "recovery"} and set(item.evidence_ids) & proof_evidence
    ]
    if not recovery:
        findings.append(
            _finding(
                "facilitated.unrecoverable-progression",
                "interventions",
                "no hint or recovery intervention",
                "the host has no declared recovery route into a Proof Path",
            )
        )
    return findings
