"""Authorized maker, host, player, print, and tutorial projections."""

from __future__ import annotations

import json
from typing import Any, Mapping

from narrative_game.blueprint import GameBlueprint
from narrative_game.compiler import GameRelease
from narrative_game.physical import PhysicalExport
from narrative_game.runtime import (
    AuthorizationContext,
    SessionCommand,
    SessionHistory,
    apply_command,
    host_snapshot,
    retrieve_resource,
    seat_snapshot,
)

from .model import (
    ActionIntent,
    ExperienceProjection,
    ExperienceSection,
    TutorialProjection,
    TutorialStep,
)


def _action(
    action_id: str,
    label: str,
    boundary: str,
    authority: str,
    command: str,
    *,
    enabled: bool = True,
    reason: str = "available",
    payload_schema: Mapping[str, Any] | None = None,
    fixed_payload: Mapping[str, Any] | None = None,
) -> ActionIntent:
    return ActionIntent(
        action_id,
        label,
        boundary,
        authority,
        command,
        enabled,
        reason,
        payload_schema or {},
        fixed_payload or {},
    )


def tutorial_projection(
    blueprint: GameBlueprint, release: GameRelease
) -> TutorialProjection:
    """Explain the real components through the exact game currently open."""
    game = blueprint.materialize_game()
    first_seat = game.kernel.seats[0]
    first_evidence = game.evidence[0]
    first_phase = sorted(game.phases, key=lambda item: item.order)[0]
    steps = (
        TutorialStep(
            "blueprint",
            "Blueprint",
            "The editable source agents may propose changing; it is not a measured game.",
            ("direction", "rich-text materials", "arc intent", "seed"),
            ("canonical Game Definition",),
            (game.kernel.game_id, blueprint.materials[0].resource_id),
        ),
        TutorialStep(
            "world",
            "World and truth",
            "One canonical world keeps every character, record, and resolution coherent.",
            ("events", "propositions", "truth assignments"),
            ("facts from which visible claims derive",),
            tuple(item.id for item in game.events[:2]),
        ),
        TutorialStep(
            "cast",
            "Characters and seats",
            "Characters belong to the story; Seats control access and action during play.",
            ("beliefs", "objectives", "authorized audience"),
            ("role-specific player experience",),
            (first_seat.id, game.characters[0].id),
        ),
        TutorialStep(
            "evidence",
            "Evidence and materials",
            "Evidence gives a document meaning; the Material is the exact thing players receive.",
            ("relations to propositions and hypotheses", "artifact bytes"),
            ("deduction paths", "displayed claim lineage"),
            (first_evidence.id, first_evidence.resource_id),
        ),
        TutorialStep(
            "arc",
            "Arc and phases",
            "Arc Beats state intended drama; Phases enforce when evidence can enter play.",
            ("dramatic questions", "timing", "reveals", "recovery"),
            ("earned progression",),
            (first_phase.id, blueprint.arc[0].dramatic_question),
        ),
        TutorialStep(
            "release",
            "Candidate and Release",
            "A Candidate freezes every play-affecting input; compilation produces one immutable Release.",
            ("component versions", "seed", "materials", "game rules"),
            ("authorized digital package",),
            (release.candidate_id, release.release_id),
        ),
        TutorialStep(
            "delivery",
            "Physical and web delivery",
            "Different delivery surfaces consume the Release without inventing new truth or access.",
            ("print plan", "role projection", "provenance"),
            ("assembled package", "character view"),
            ("projections/host.json", f"projections/seats/{first_seat.id}.json"),
        ),
        TutorialStep(
            "session",
            "Live Session",
            "A hash-chained Session records authorized disclosure, player action, host intervention, and resolution.",
            ("actor bindings", "commands", "events", "receipts"),
            ("replayable play history",),
            ("open-session", "advance-phase", "submit-resolution"),
        ),
        TutorialStep(
            "measurement",
            "Measure and hill climb",
            "Blind models and fresh human play expose tells under one frozen Instrument.",
            ("dimensions", "hard gates", "quoted findings", "comparison"),
            ("answer-safe requirements",),
            ("Frozen Instrument", "Playtest Protocol"),
        ),
        TutorialStep(
            "human-control",
            "Human direction and standing",
            "Agents propose; humans approve canonical changes and independently confer only supported standing.",
            ("Review", "Transition", "publication authority"),
            ("selected child", "Standing Attestation"),
            ("Proposal", "Human Review", "Standing"),
        ),
    )
    return TutorialProjection(
        "narrative.facilitated-investigation-authoring",
        release.release_id,
        f"How {game.kernel.title} becomes a playable game",
        steps,
    )


def maker_projection(
    blueprint: GameBlueprint,
    release: GameRelease,
    physical: PhysicalExport,
    *,
    lineage: Mapping[str, Any],
) -> tuple[ExperienceProjection, TutorialProjection]:
    """Project editable intent and release evidence without granting mutation."""
    game = blueprint.materialize_game()
    tutorial = tutorial_projection(blueprint, release)
    projection = ExperienceProjection(
        "maker",
        "trusted-maker",
        game.kernel.title,
        game.direction.premise,
        release.release_id,
        None,
        None,
        physical.export_id,
        (
            ExperienceSection("tutorial", "Start here", "tutorial", tutorial.to_mapping()),
            ExperienceSection(
                "blueprint",
                "Game anatomy",
                "component-summary",
                {
                    "game_id": game.kernel.game_id,
                    "seats": [item.id for item in game.kernel.seats],
                    "characters": [item.id for item in game.characters],
                    "evidence": [item.id for item in game.evidence],
                    "proof_paths": [item.id for item in game.proof_paths],
                    "materials": [item.to_mapping() for item in blueprint.materials],
                },
            ),
            ExperienceSection(
                "arc",
                "Evidence custody",
                "phase-rail",
                [item.to_mapping() for item in blueprint.arc],
            ),
            ExperienceSection(
                "lineage",
                "Hill-climb lineage",
                "lineage",
                dict(lineage),
            ),
            ExperienceSection(
                "package",
                "Current package",
                "identity",
                {
                    "candidate_id": release.candidate_id,
                    "release_id": release.release_id,
                    "physical_export_id": physical.export_id,
                },
            ),
        ),
        (
            _action("propose-revision", "Propose a revision", "experiment", "agent-builder", "propose_revision"),
            _action("review-proposal", "Review proposal", "experiment", "human-reviewer", "review_proposal"),
            _action("prepare-playtest", "Prepare playtest", "experiment", "human-operator", "freeze_protocol"),
        ),
        tutorial.tutorial_id,
    )
    return projection, tutorial


def host_projection(
    release: GameRelease,
    physical: PhysicalExport,
    history: SessionHistory,
    auth: AuthorizationContext,
) -> ExperienceProjection:
    snapshot = host_snapshot(release, history, auth)
    state = snapshot["state"]
    game = snapshot["game"]["game"]
    phases = sorted(game["narrative"]["phases"], key=lambda item: item["order"])
    phase_index = next(index for index, item in enumerate(phases) if item["id"] == state["phase_id"])
    actions = []
    if state["status"] == "created":
        actions.append(_action("open-session", "Open session", "session", "host", "open-session"))
    elif state["status"] == "active":
        if phase_index + 1 < len(phases):
            next_phase = phases[phase_index + 1]["id"]
            actions.append(_action("advance-phase", f"Advance to {next_phase}", "session", "host", "advance-phase", fixed_payload={"phase_id": next_phase}))
        actions.extend(
            (
                _action("disclose-resource", "Disclose evidence", "session", "host", "disclose-resource", payload_schema={"resource_id": "string", "audience_seat_ids": ["seat-id"], "evidence_grade": "runtime-enforced | host-witnessed | actor-reported"}),
                _action("deliver-intervention", "Deliver planned intervention", "session", "host", "deliver-intervention", payload_schema={"intervention_id": "string", "audience_seat_ids": ["seat-id"], "reason": "string"}),
            )
        )
    sections = [
        ExperienceSection("phase", "Live phase", "phase-rail", {"current": state["phase_id"], "phases": phases}),
    ]
    if game["narrative"].get("character_program") is not None:
        sections.append(
            ExperienceSection(
                "character-arcs",
                "Character arc oversight",
                "character-state-grid",
                {
                    "states": state.get("character_states", {}),
                    "recovery_interventions": [
                        item for item in game["narrative"]["interventions"]
                        if item["phase_id"] == state["phase_id"]
                    ],
                },
            )
        )
    sections.extend((
        ExperienceSection("requests", "Player requests", "queue", {"hints": state["hint_requests"], "evidence": state["evidence_requests"]}),
        ExperienceSection("events", "Session event record", "event-stream", [item.to_mapping() for item in history.ordered_events]),
        ExperienceSection("materials", "Authorized materials", "material-index", release.manifest["materials"]),
        ExperienceSection("assembly", "Physical handoff", "physical-plan", physical.plan),
    ))
    return ExperienceProjection(
        "host",
        f"viewer:{auth.principal_id}",
        game["kernel"]["title"],
        f"{state['phase_id']} · {state['status']}",
        release.release_id,
        history.session_id,
        state["sequence"],
        physical.export_id,
        tuple(sections),
        tuple(actions),
    )


def player_projection(
    release: GameRelease,
    history: SessionHistory,
    auth: AuthorizationContext,
) -> ExperienceProjection:
    snapshot = seat_snapshot(release, history, auth)
    resources = []
    for item in snapshot["resources"]:
        data = retrieve_resource(release, history, auth, item["resource_id"])
        value = dict(item)
        value["content"] = data.decode("utf-8") if item["media_type"].startswith("text/") else None
        resources.append(value)
    action_labels = {
        "request-evidence": "Request evidence",
        "request-hint": "Request a hint",
        "share-claim": "Share a claim",
        "submit-resolution": "Submit resolution",
        "update-character-state": "Record character direction",
    }
    schemas = {
        "request-evidence": {"resource_id": "string"},
        "request-hint": {"request": "string"},
        "share-claim": {"proposition_id": "string", "stance": "accepts | rejects"},
        "submit-resolution": {"hypothesis_id": "string", "proof_path_id": "string"},
        "update-character-state": {
            "move_id": "current-phase move-id | null",
            "objective_id": "owned active objective-id | null",
            "objective_status": "active | advanced | satisfied | abandoned | null",
            "belief_proposition_id": "revisable belief-id | null",
            "belief_stance": "accepts | rejects | uncertain | null",
            "human_direction": "string | null",
        },
    }
    actions = tuple(
        _action(item, action_labels[item], "session", "active-player", item, payload_schema=schemas[item])
        for item in snapshot["allowed_actions"]
    )
    return ExperienceProjection(
        "player",
        f"actor:{auth.principal_id}:{auth.binding_id}",
        snapshot["character"]["name"],
        snapshot["character"]["objectives"][0]["description"],
        release.release_id,
        history.session_id,
        snapshot["revision"],
        None,
        tuple(
            item for item in (
            ExperienceSection("brief", "Your character", "character", {"seat": snapshot["seat"], "character": snapshot["character"], "resolution_prompt": snapshot["resolution_prompt"]}),
            (
                ExperienceSection(
                    "quick-start", "Read this first", "character-quick-start",
                    snapshot["dossier"]["quick_start"],
                ) if snapshot["dossier"] is not None else None
            ),
            (
                ExperienceSection(
                    "deep-play", "Your deeper dossier", "character-dossier",
                    snapshot["dossier"]["deep_play"],
                ) if snapshot["dossier"] is not None else None
            ),
            (
                ExperienceSection(
                    "phase-arc", "What is changing now", "character-phase-arc",
                    snapshot["dossier"]["active_arc"],
                ) if snapshot["dossier"] is not None else None
            ),
            (
                ExperienceSection(
                    "character-state", "Your choices so far", "character-state",
                    snapshot["character_state"],
                ) if snapshot["dossier"] is not None else None
            ),
            ExperienceSection("evidence", "Evidence in hand", "authorized-materials", resources),
            ExperienceSection("notes", "Private notes", "private-notes", snapshot["private_notes"]),
            ExperienceSection("events", "What you have seen", "visible-events", snapshot["visible_events"]),
            ) if item is not None
        ),
        actions,
    )


def print_projection(
    release: GameRelease, physical: PhysicalExport
) -> ExperienceProjection:
    return ExperienceProjection(
        "print",
        "trusted-operator",
        str(json.loads(release.file("trusted/game.json").data)["kernel"]["title"]),
        "Assemble the exact authorized physical package.",
        release.release_id,
        None,
        None,
        physical.export_id,
        (
            ExperienceSection("plan", "Assembly plan", "physical-plan", physical.plan),
            ExperienceSection("preflight", "Print preflight", "preflight", physical.preflight),
            ExperienceSection("files", "Package files", "file-index", [item.descriptor() for item in physical.files]),
        ),
        (_action("download-package", "Download package", "export", "operator", "download_physical_export"),),
    )


def dispatch_session_intent(
    release: GameRelease,
    history: SessionHistory,
    auth: AuthorizationContext,
    projection: ExperienceProjection,
    *,
    action_id: str,
    payload: Mapping[str, Any],
    command_id: str,
):
    """Route one surface intent through the unchanged Session Authority."""
    if projection.release_id != release.release_id or projection.session_id != history.session_id or projection.revision != history.sequence:
        raise ValueError("Experience Projection is stale or bound to another Release or Session")
    expected_scope = (
        f"actor:{auth.principal_id}:{auth.binding_id}"
        if auth.kind == "actor"
        else f"viewer:{auth.principal_id}"
    )
    if projection.authority_scope != expected_scope:
        raise ValueError("Experience Projection belongs to another authority")
    matches = [item for item in projection.actions if item.action_id == action_id]
    if len(matches) != 1 or matches[0].boundary != "session" or not matches[0].enabled:
        raise ValueError("Experience action is unavailable")
    action = matches[0]
    command = SessionCommand(
        command_id,
        history.session_id,
        release.release_id,
        history.sequence,
        action.command,
        {**action.fixed_payload, **dict(payload)},
    )
    return apply_command(release, history, command, auth)
