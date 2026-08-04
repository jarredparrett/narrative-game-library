"""Pure views derived from one canonical Narrative owner."""

from __future__ import annotations

from typing import Literal, cast

from .model import GameDefinition


TruthValue = Literal["true", "false", "unresolved"]


def _truth_index(game: GameDefinition) -> dict[str, TruthValue]:
    result: dict[str, TruthValue] = {}
    for assignment in game.truth_model:
        value = assignment.value
        if value not in {"true", "false", "unresolved"}:
            raise ValueError(f"invalid truth value for {assignment.proposition_id!r}: {value!r}")
        previous = result.get(assignment.proposition_id)
        if previous is not None and previous != value:
            raise ValueError(f"contradictory truth for {assignment.proposition_id!r}")
        result[assignment.proposition_id] = cast(TruthValue, value)
    return result


def proposition_truth(game: GameDefinition, proposition_id: str) -> TruthValue:
    """Read truth from the sole Truth Model owner."""
    try:
        return _truth_index(game)[proposition_id]
    except KeyError as exc:
        raise KeyError(f"Proposition has no Truth assignment: {proposition_id}") from exc


def classify_claim(
    game: GameDefinition,
    *,
    character_id: str,
    proposition_id: str,
    stance: Literal["accepts", "rejects"],
) -> dict[str, str]:
    """Derive factuality and intent without copying either into a Claim."""
    truth = proposition_truth(game, proposition_id)
    if truth == "unresolved":
        factuality = "unresolved"
    else:
        factuality = "true" if (truth == "true") == (stance == "accepts") else "false"
    character = next(item for item in game.characters if item.id == character_id)
    belief = next(
        (item.stance for item in character.beliefs if item.proposition_id == proposition_id),
        "uncertain",
    )
    if belief == "uncertain":
        intent = "indeterminate"
    elif belief == stance:
        intent = "sincere"
    else:
        intent = "deliberate-lie"
    return {"factuality": factuality, "intent": intent}


def available_evidence(
    game: GameDefinition, *, seat_id: str, phase_id: str
) -> tuple[str, ...]:
    """Resolve one authorized evidence view from Reveals plus Kernel policy."""
    phase_order = {phase.id: phase.order for phase in game.phases}
    current_order = phase_order[phase_id]
    evidence = {item.id: item for item in game.evidence}
    allowed = {
        policy.resource.id
        for policy in game.kernel.access_policies
        if any(grantee.kind == "seat" and grantee.id == seat_id for grantee in policy.grantees)
    }
    result = {
        reveal.evidence_id
        for reveal in game.reveals
        if seat_id in reveal.audience_seat_ids
        and phase_order[reveal.phase_id] <= current_order
        and evidence[reveal.evidence_id].resource_id in allowed
    }
    return tuple(sorted(result))
