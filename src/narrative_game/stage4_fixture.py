"""Deterministic complete Micro Session used by runtime capability tests."""

from __future__ import annotations

from narrative_game.compiler import compile_candidate
from narrative_game.runtime import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    SessionCommand,
    ViewerGrant,
    apply_command,
    create_session,
)
from narrative_game.stage3_fixture import build_micro_candidate


def build_open_session(game_json: str | bytes, *, session_id: str = "micro-session"):
    release = compile_candidate(build_micro_candidate(game_json)).release
    if release is None:  # pragma: no cover - a broken lower-stage fixture.
        raise ValueError("Micro Candidate did not compile")
    bindings = (
        ActorBinding("binding-avery-1", Actor("actor-avery", "human", "Avery Player"), "avery", 1),
        ActorBinding("binding-blake-1", Actor("actor-blake", "human", "Blake Player"), "blake", 1),
    )
    history = create_session(
        release=release,
        session_id=session_id,
        mode="live",
        bindings=bindings,
        viewers=(ViewerGrant("viewer-host", "host"),),
    )
    auth = {
        "host": AuthorizationContext("viewer", "viewer-host"),
        "avery": AuthorizationContext("actor", "actor-avery", "binding-avery-1"),
        "blake": AuthorizationContext("actor", "actor-blake", "binding-blake-1"),
    }
    opened = apply_command(
        release,
        history,
        SessionCommand(
            "command-open",
            session_id,
            release.release_id,
            history.sequence,
            "open-session",
            {},
        ),
        auth["host"],
    )
    if not opened.receipt.accepted:  # pragma: no cover
        raise ValueError(opened.receipt.trusted_reason)
    return release, opened.history, auth


def run_micro_session(game_json: str | bytes, *, session_id: str = "micro-session"):
    release, history, auth = build_open_session(game_json, session_id=session_id)

    def accept(command_id: str, action: str, payload: dict, authority: str):
        nonlocal history
        result = apply_command(
            release,
            history,
            SessionCommand(
                command_id,
                session_id,
                release.release_id,
                history.sequence,
                action,
                payload,
            ),
            auth[authority],
        )
        if not result.receipt.accepted:  # pragma: no cover
            raise ValueError(result.receipt.trusted_reason)
        history = result.history
        return result

    accept("command-note", "add-private-note", {"note": "Compare the key signature."}, "avery")
    accept("command-hint-request", "request-hint", {"request": "What should we compare?"}, "avery")
    accept("command-phase", "advance-phase", {"phase_id": "resolution"}, "host")
    accept(
        "command-receipt",
        "disclose-resource",
        {
            "resource_id": "cash-receipt",
            "audience_seat_ids": ["avery"],
            "evidence_grade": "host-witnessed",
        },
        "host",
    )
    accept(
        "command-intervention",
        "deliver-intervention",
        {
            "intervention_id": "host-recovery",
            "audience_seat_ids": ["blake"],
            "reason": "The group requested recovery support.",
        },
        "host",
    )
    submission = accept(
        "command-submit",
        "submit-resolution",
        {"hypothesis_id": "inside-job", "proof_path_id": "key-and-payment"},
        "avery",
    )
    accept(
        "command-resolve",
        "record-resolution",
        {"submission_sequence": submission.events[0].sequence},
        "host",
    )
    return release, history, auth
