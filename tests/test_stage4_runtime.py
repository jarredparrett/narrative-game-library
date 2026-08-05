"""Stage 4 Session Authority, replay, authorization, and fork tests."""

from __future__ import annotations

import ast
import base64
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from narrative_game.runtime import (
    Actor,
    AuthorizationContext,
    AuthorizationDenied,
    SessionCommand,
    SessionHistory,
    apply_command,
    fork_session,
    host_snapshot,
    replay,
    retrieve_resource,
    seat_snapshot,
)
from narrative_game.runtime.runtime import verify_history
from narrative_game.stage3_fixture import MATERIAL_BYTES
from narrative_game.stage4_fixture import build_open_session, run_micro_session


FIXTURE = Path(__file__).parents[1] / "fixtures" / "micro-game" / "game.json"


def command(history, release, command_id, action, payload):
    return SessionCommand(
        command_id,
        history.session_id,
        release.release_id,
        history.sequence,
        action,
        payload,
    )


def test_complete_session_replays_to_the_pinned_resolution():
    """stage4.trajectory: opening through resolution is one verified chain."""
    release, history, auth = run_micro_session(FIXTURE.read_bytes())
    state = replay(release, history)
    assert state["status"] == "resolved"
    assert state["phase_id"] == "resolution"
    assert state["resolution"]["correct"] is True
    assert state["sequence"] == 9
    assert len(history.events) == 9
    assert history.content_hash == "sha256:3d0bd062ac630d14f9e6269fa4dcdcecc9c29a2fe3e74d77c3349d66e14ce11f"
    assert history.event_head == "sha256:be8c01cf4fd7ccc63d6fe9e46a77b0e489f7902e3d988e77ea0027c4ba9a7920"
    assert verify_history(history) is None
    assert host_snapshot(release, history, auth["host"])["state"] == state


def test_authorization_precedes_snapshot_and_resource_serialization():
    """stage4.authorization: trusted context, not requested Seat, grants data."""
    release, history, auth = run_micro_session(FIXTURE.read_bytes())
    avery = seat_snapshot(release, history, auth["avery"])
    blake = seat_snapshot(release, history, auth["blake"])
    assert "cash-receipt" in {item["resource_id"] for item in avery["resources"]}
    assert "cash-receipt" not in {item["resource_id"] for item in blake["resources"]}
    assert retrieve_resource(release, history, auth["avery"], "cash-receipt") == MATERIAL_BYTES[
        "cash-receipt"
    ]
    with pytest.raises(AuthorizationDenied, match="not authorized"):
        retrieve_resource(release, history, auth["blake"], "cash-receipt")
    with pytest.raises(AuthorizationDenied, match="not authorized"):
        seat_snapshot(
            release,
            history,
            AuthorizationContext("actor", "actor-avery", "binding-blake-1"),
        )
    forbidden = {"truth_model", "proof_paths", "correct_hypothesis_id"}
    assert not forbidden & set(json.dumps(blake).split('"'))
    assert blake["private_notes"] == []


def test_commands_are_atomic_revision_checked_and_exactly_idempotent():
    """stage4.command-atomicity: accept one Event batch or no Event."""
    release, history, auth = build_open_session(FIXTURE.read_bytes())
    stale = SessionCommand(
        "command-stale",
        history.session_id,
        release.release_id,
        history.sequence - 1,
        "request-hint",
        {"request": "Help"},
    )
    rejected = apply_command(release, history, stale, auth["avery"])
    assert not rejected.receipt.accepted
    assert rejected.receipt.public_reason == "command rejected"
    assert rejected.events == ()
    assert rejected.history.events == history.events

    accepted_command = command(
        rejected.history,
        release,
        "command-note",
        "add-private-note",
        {"note": "Check the register."},
    )
    accepted = apply_command(release, rejected.history, accepted_command, auth["avery"])
    retry = apply_command(release, accepted.history, accepted_command, auth["avery"])
    assert retry.receipt == accepted.receipt
    assert retry.history == accepted.history
    assert retry.events == ()

    conflicting = replace(accepted_command, payload={"note": "Different content"})
    conflict = apply_command(release, accepted.history, conflicting, auth["avery"])
    assert not conflict.receipt.accepted
    assert conflict.history.events == accepted.history.events
    assert conflict.receipt.trusted_reason == "idempotency key names another request"


def test_restart_recovery_and_tamper_detection_are_deterministic():
    """stage4.replay: portable bytes reproduce state and expose edited history."""
    release, history, auth = run_micro_session(FIXTURE.read_bytes())
    restored = SessionHistory.from_bytes(history.to_bytes())
    assert restored == history
    assert restored.content_hash == history.content_hash
    assert replay(release, restored) == replay(release, history)
    assert seat_snapshot(release, restored, auth["avery"]) == seat_snapshot(
        release, history, auth["avery"]
    )

    event = restored.events[2]
    tampered = replace(
        restored,
        events=(*restored.events[:2], replace(event, payload={"request": "rewritten"}), *restored.events[3:]),
    )
    with pytest.raises(ValueError, match="Event hash is invalid"):
        replay(release, tampered)


def test_actor_replacement_does_not_transfer_private_notes():
    """stage4.actor-replacement: control transfers explicitly; Actor notes do not."""
    release, history, auth = build_open_session(FIXTURE.read_bytes())
    note = apply_command(
        release,
        history,
        command(history, release, "command-note", "add-private-note", {"note": "Private"}),
        auth["avery"],
    )
    replacement_command = command(
        note.history,
        release,
        "command-replace",
        "replace-actor",
        {
            "seat_id": "avery",
            "binding_id": "binding-avery-2",
            "actor": {"id": "actor-new", "kind": "human", "label": "Replacement"},
        },
    )
    replaced = apply_command(release, note.history, replacement_command, auth["host"])
    new_auth = AuthorizationContext("actor", "actor-new", "binding-avery-2")
    assert seat_snapshot(release, replaced.history, new_auth)["private_notes"] == []
    with pytest.raises(AuthorizationDenied):
        seat_snapshot(release, replaced.history, auth["avery"])
    trusted = host_snapshot(release, replaced.history, auth["host"])
    assert trusted["state"]["private_notes"]["actor-avery"] == ["Private"]


def test_simulation_fork_is_isolated_and_live_model_substitution_is_blocked():
    """stage4.forks: simulation arms share a verified prefix and never merge live."""
    release, live, auth = build_open_session(FIXTURE.read_bytes())
    model_replace = command(
        live,
        release,
        "command-live-model",
        "replace-actor",
        {
            "seat_id": "blake",
            "binding_id": "binding-model",
            "actor": {"id": "model-one", "kind": "model", "label": "Simulation Model"},
        },
    )
    blocked = apply_command(release, live, model_replace, auth["host"])
    assert not blocked.receipt.accepted
    assert blocked.history.events == live.events

    fork = fork_session(live, session_id="simulation-arm-1", at_sequence=live.sequence)
    fork_command = SessionCommand(
        "command-fork-model",
        fork.session_id,
        release.release_id,
        fork.sequence,
        "replace-actor",
        model_replace.payload,
    )
    accepted = apply_command(release, fork, fork_command, auth["host"])
    assert accepted.receipt.accepted
    assert accepted.events[0].session_id == "simulation-arm-1"
    assert accepted.history.fork_source["source_session_id"] == live.session_id
    assert live.sequence == 2
    assert replay(release, live)["bindings"]["blake"]["actor"]["kind"] == "human"
    assert replay(release, accepted.history)["bindings"]["blake"]["actor"]["kind"] == "model"


def test_concurrent_sessions_over_one_release_remain_isolated():
    """stage4.session-isolation: no Session state is ambient or shared."""
    release, first, auth = build_open_session(FIXTURE.read_bytes(), session_id="session-one")
    _, second, _ = build_open_session(FIXTURE.read_bytes(), session_id="session-two")
    changed = apply_command(
        release,
        first,
        command(first, release, "command-note", "add-private-note", {"note": "Only first"}),
        auth["avery"],
    ).history
    assert replay(release, changed)["private_notes"] == {"actor-avery": ["Only first"]}
    assert replay(release, second)["private_notes"] == {}
    assert changed.session_id != second.session_id
    assert changed.event_head != second.event_head


def test_physical_disclosure_preserves_method_and_evidence_grade():
    """stage4.physical-evidence: possession changes only through a Disclosure Event."""
    release, history, _ = run_micro_session(FIXTURE.read_bytes())
    disclosure = next(
        item
        for item in history.events
        if item.command_id == "command-receipt" and item.event_type == "resource-disclosed"
    )
    assert disclosure.payload["disclosures"] == [
        {
            "seat_id": "avery",
            "resource_id": "cash-receipt",
            "evidence_grade": "host-witnessed",
        }
    ]


def test_exceptional_intervention_is_exact_recorded_and_access_bounded():
    """stage4.exceptional-intervention: unforeseen host action remains explicit and bounded."""
    release, history, auth = build_open_session(FIXTURE.read_bytes())
    exceptional = apply_command(
        release,
        history,
        command(
            history,
            release,
            "command-exceptional",
            "record-exceptional-intervention",
            {
                "reason": "A printed register became unreadable.",
                "materialized_content": "The host read the existing register entry aloud.",
                "audience_seat_ids": ["avery", "blake"],
                "affected_object_ids": ["register-evidence"],
                "resource_ids": ["key-register"],
            },
        ),
        auth["host"],
    )
    assert exceptional.receipt.accepted
    event = exceptional.events[0]
    assert event.event_type == "exceptional-intervention-recorded"
    assert event.payload["reason"] == "A printed register became unreadable."
    assert event.payload["materialized_content"] == (
        "The host read the existing register entry aloud."
    )
    assert replay(release, exceptional.history)["interventions"][-1]["kind"] == "exceptional"

    forbidden = command(
        exceptional.history,
        release,
        "command-exceptional-leak",
        "record-exceptional-intervention",
        {
            "reason": "Attempt an early disclosure.",
            "materialized_content": "Receipt contents",
            "audience_seat_ids": ["blake"],
            "resource_ids": ["cash-receipt"],
        },
    )
    blocked = apply_command(release, exceptional.history, forbidden, auth["host"])
    assert not blocked.receipt.accepted
    assert blocked.events == ()


def test_session_bytes_and_snapshots_match_across_processes():
    """stage4.cross-process: portable Session replay has one canonical result."""
    command_text = (
        "from pathlib import Path; import base64, json; "
        "from narrative_game.stage4_fixture import run_micro_session; "
        "from narrative_game.runtime import replay, seat_snapshot; "
        f"r,h,a=run_micro_session(Path({str(FIXTURE)!r}).read_bytes()); "
        "print(h.content_hash); print(base64.b64encode(h.to_bytes()).decode()); "
        "print(json.dumps(seat_snapshot(r,h,a['avery']),sort_keys=True,separators=(',',':')))"
    )
    first = subprocess.check_output([sys.executable, "-c", command_text])
    second = subprocess.check_output([sys.executable, "-c", command_text])
    assert first == second
    assert base64.b64decode(first.splitlines()[1]).startswith(b'{"events"')


def test_runtime_core_has_no_ambient_effect_imports():
    """stage4.purity: reducers and projectors need no IO, clock, model, or randomness."""
    root = Path(__file__).parents[1] / "src" / "narrative_game" / "runtime"
    forbidden = {
        "datetime",
        "http",
        "os",
        "pathlib",
        "random",
        "requests",
        "socket",
        "subprocess",
        "time",
        "urllib",
        "uuid",
    }
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        assert not imports & forbidden
