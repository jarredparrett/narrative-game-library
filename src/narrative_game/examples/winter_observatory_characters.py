"""Six canonical, phase-aware dossiers for the Winter Observatory example."""

from dataclasses import replace
from importlib.resources import files

from narrative_game.authoring import parse_game_definition
from narrative_game.contracts import digest_bytes
from narrative_game.narrative import (
    CharacterDossier, CharacterMove, CharacterProgram, EndingChoice, EventGrant,
    KnowledgeBoundary, KnowledgeGrant, PhaseArc, PrivateChronologyEntry,
    QuickStart, ReferencedText, RelationshipProfile, RevealPath,
    render_dossier_markdown,
)


_PRIVATE = {
    "eleanor-vale": ("eleanor-removed-order", "vale-planned-confession"),
    "felix-mercer": (
        "mercer-diverted-funds", "mercer-met-vale", "vale-killed-in-vault",
        "body-in-drive-chase", "mercer-altered-correction",
    ),
    "ruth-bell": ("ruth-removed-plate", "vale-planned-confession"),
    "samuel-wren": ("wren-relabeled-jacket", "plate-fixes-sequence"),
    "thomas-rook": ("rook-clock-drift",),
    "lillian-hart": ("lillian-inflated-brightness", "mercer-diverted-funds"),
}

_EVENTS = {
    "eleanor-vale": ("vale-prepares-confession", "guests-alter-records"),
    "felix-mercer": (
        "vale-prepares-confession", "guests-alter-records", "vault-meeting",
        "vale-killed", "vale-concealed", "correction-reversed",
    ),
    "ruth-bell": ("vale-prepares-confession", "guests-alter-records"),
    "samuel-wren": ("guests-alter-records", "records-disagree"),
    "thomas-rook": ("guests-alter-records",),
    "lillian-hart": ("vale-prepares-confession", "guests-alter-records"),
}

_ROLE = {
    "eleanor-vale": (
        "Vale's physician and estranged daughter, trained to protect patients and distrust spectacle.",
        "You removed his final observing order because his tremor threatened the institution, then learned he meant to correct an older wrong.",
        "Your professional instinct says preserve dignity; your private fear is that preservation has become concealment.",
    ),
    "felix-mercer": (
        "The observatory's composed treasurer, fluent in trustees, budgets, and institutional survival.",
        "You diverted restricted funds, killed Vale when he confronted you, concealed him, and reversed the clock correction to build an alibi.",
        "You must remain playable after exposure: bargain with what you know, challenge weak inferences, and choose what kind of confession follows defeat.",
    ),
    "ruth-bell": (
        "A retired observer whose 1911 discovery was credited to Vale and whose patience has become exacting.",
        "You removed the original plate envelope to recover proof of your authorship; Vale had promised to restore your credit tonight.",
        "You want the truth restored without letting a just grievance be mistaken for murder.",
    ),
    "samuel-wren": (
        "A celebrated astronomer who converts difficult observations into decisive public claims.",
        "You relabeled a plate jacket to strengthen a priority claim and recognize that the independent records fix the disputed sequence.",
        "Admitting your alteration may cost status, but withholding your technical reading may cost the group the truth.",
    ),
    "thomas-rook": (
        "The observatory engineer, responsible for clocks, drives, keys, and every mechanism others notice only when it fails.",
        "Your unauthorized repair introduced a real sub-second drift, but not the fatal event you fear.",
        "Quantify the fault honestly before someone turns a small error into a complete explanation.",
    ),
    "lillian-hart": (
        "The observatory's public secretary, charged with converting uncertain science into support, attendance, and money.",
        "You inflated the comet brightness forecast and found signs that Mercer moved restricted funds.",
        "You must distinguish institutional advocacy from falsifying the record, including your own part in both.",
    ),
}

_PUBLIC = ("vale-staged-disappearance", "rook-caused-fatal-accident", "ruth-killed-vale")
_BELIEF_GRANTS = {"felix-mercer": ("rook-clock-drift",)}


def _text(text: str, *, props=(), events=(), evidence=(), characters=()) -> ReferencedText:
    return ReferencedText(text, tuple(props), tuple(events), tuple(evidence), tuple(characters))


def _dossier(game, character) -> CharacterDossier:
    seat = character.seat_id
    identity, private_truth, stakes = _ROLE[seat]
    secrets = _PRIVATE[seat]
    belief = character.beliefs[0].proposition_id
    others = [item for item in game.characters if item.id != character.id]
    relationships = tuple(
        RelationshipProfile(
            other.id,
            _text(f"You and {other.name} have worked around the same institution long enough to know which courtesies conceal pressure.", characters=(other.id,)),
            _text(f"Tonight, {other.name} may read your alteration as motive unless you separate what you changed from what happened to Vale.", characters=(other.id,)),
            _text(f"You can offer {other.name} a precise account, a corroborating question, or restraint in exchange for the same.", characters=(other.id,)),
            _text(f"An alliance with {other.name} is credible when it follows shared evidence rather than shared suspicion.", characters=(other.id,)),
        ) for other in others
    )
    moves = []
    arcs = []
    phases = sorted(game.phases, key=lambda item: item.order)
    for phase in phases:
        move_ids = []
        for kind, instruction in (
            ("action", f"State one thing you personally observed, ask one named person a precise question, and keep your current objective visible during {phase.label}."),
            ("fallback", "If the conversation passes you by, compare two accounts aloud and ask what fact would distinguish them."),
            ("after_exposure", "If your alteration is exposed, acknowledge exactly that act, explain its motive, and refuse any unsupported leap from alteration to murder."),
        ):
            move_id = f"{seat}:{phase.id}:{kind}"
            move_ids.append(move_id)
            moves.append(CharacterMove(move_id, kind, _text(instruction)))
        if phase.id == "alterations":
            move_id = f"{seat}:{phase.id}:bargain"
            move_ids.append(move_id)
            moves.append(CharacterMove(move_id, "bargain", _text("Offer the timing of your own alteration in return for another player's equally specific account.")))
        if phase.id == "accusation":
            target = others[0].id
            move_id = f"{seat}:{phase.id}:challenge"
            move_ids.append(move_id)
            moves.append(CharacterMove(move_id, "challenge", _text("Challenge one causal step in the leading theory and require evidence, not character judgment.", characters=(target,)), (target,)))
        reveal_ids = tuple(f"{seat}:reveal:{secret}" for secret in secrets if phase.id in {"alterations", "accusation"})
        active = tuple(
            item.id for item in game.objectives
            if item.id in character.objective_ids and next(p.order for p in phases if p.id == item.activation_phase_id) <= phase.order
        )
        arcs.append(PhaseArc(phase.id, active, _text(f"During {phase.label}, protect agency under pressure: pursue evidence, revise beliefs when warranted, and do not invent facts."), tuple(move_ids), reveal_ids))
    reveal_paths = tuple(
        RevealPath(
            f"{seat}:reveal:{secret}", secret, ("alterations", "accusation"),
            _text("Disclose this truth when its physical record appears, when another player asks a direct fair question, or before the final accusation.", props=(secret,)),
            "second-route-recovery",
        ) for secret in secrets
    )
    first_event = _EVENTS[seat][0]
    return CharacterDossier(
        dossier_id=f"winter-observatory:{seat}:dossier",
        seat_id=seat,
        character_id=character.id,
        resource_id=f"dossier-{seat}",
        target_pages=4,
        quick_start=QuickStart(
            _text(identity), _text(private_truth, props=secrets),
            (character.objective_ids[0],), (belief,),
            _text("Begin by placing your professional role in the room, then ask who last saw Vale and which record they touched.")
        ),
        knowledge_boundary=KnowledgeBoundary(
            tuple(secret for secret in secrets if secret not in _PUBLIC),
            (belief,), tuple(secrets), (),
        ),
        personal_history=(
            _text(identity),
            _text("Years at the observatory taught you that records have authors, custodians, incentives, and scars; neutrality must be demonstrated, not asserted."),
            _text(private_truth, props=secrets),
        ),
        emotional_stakes=(
            _text(stakes),
            _text("A truthful ending may damage the institution and your reputation; an evasive ending leaves someone else's lie in the permanent record."),
        ),
        relationships=relationships,
        private_chronology=(
            PrivateChronologyEntry(first_event, "alterations", _text(f"Your account of {first_event} is partial but firsthand; distinguish what you saw from what you inferred.", events=(first_event,))),
        ),
        voice_guidance=(
            "Speak in concrete observations before interpretations.",
            "Ask direct questions without narrating another character's answer.",
            "Concede proved facts; keep unproved causal claims contestable.",
            "Let human direction change tone, alliances, and risk tolerance - not canonical truth.",
        ),
        evidence_connections=(
            _text(
                "Your private briefing licenses your opening knowledge; later records must be interpreted only after the host reveals them.",
                evidence=(f"briefing-{seat}",),
            ),
        ),
        secondary_objective_ids=tuple(character.objective_ids[1:]),
        moves=tuple(moves), reveal_paths=reveal_paths, phase_arcs=tuple(arcs),
        ending_choices=(
            EndingChoice(f"{seat}:public-record", "Correct the public record", _text("Tell the complete truth you are authorized to know and accept the consequence of your own alteration.", props=secrets)),
            EndingChoice(f"{seat}:private-reckoning", "Choose a private reckoning", _text("Support the proved accusation while reserving your personal confession for those directly harmed.", props=secrets)),
        ),
    )


def winter_observatory_parent_game():
    """Return the exact selected Candidate 6 canonical game."""
    source = files("narrative_game").joinpath("examples/winter-observatory/game.json")
    return parse_game_definition(source.read_bytes())


def winter_observatory_game():
    """Return a Candidate 6 child with one canonical deep Dossier per Seat."""
    game = winter_observatory_parent_game()
    private_grants = tuple(
        KnowledgeGrant(prop, (seat,))
        for seat, props in _PRIVATE.items() for prop in props if prop not in _PUBLIC
    ) + tuple(
        KnowledgeGrant(prop, (seat,))
        for seat, props in _BELIEF_GRANTS.items() for prop in props
    )
    event_grants = tuple(
        EventGrant(event, (seat,)) for seat, events in _EVENTS.items() for event in events
    )
    classified_props = set(_PUBLIC) | {item.proposition_id for item in private_grants}
    classified_events = {item.event_id for item in event_grants}
    program = CharacterProgram(
        public_proposition_ids=_PUBLIC,
        private_knowledge_grants=private_grants,
        host_only_proposition_ids=tuple(sorted({item.id for item in game.propositions} - classified_props)),
        public_event_ids=(), private_event_grants=event_grants,
        host_only_event_ids=tuple(sorted({item.id for item in game.events} - classified_events)),
        dossiers=tuple(_dossier(game, character) for character in game.characters),
    )
    game = replace(game, character_program=program)
    dossier_by_resource = {item.resource_id: item for item in program.dossiers}
    resources = tuple(
        replace(
            resource,
            content_hash=digest_bytes(
                render_dossier_markdown(game, dossier_by_resource[resource.id])
            ),
        )
        if resource.id in dossier_by_resource else resource
        for resource in game.kernel.resources
    )
    return replace(game, kernel=replace(game.kernel, resources=resources))


__all__ = ["winter_observatory_game", "winter_observatory_parent_game"]
