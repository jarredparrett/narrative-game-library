"""Deterministically materialize a resolved live Session from a host transcript."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from narrative_game.compiler import load_release
from narrative_game.contracts import canonical_json
from narrative_game.runtime import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    SessionCommand,
    SessionHistory,
    ViewerGrant,
    apply_command,
    create_session,
)
from narrative_game.runtime.runtime import verify_history
from narrative_game.workspace.io import atomic_write


def record_session_plan(
    release_bytes: bytes,
    plan: Mapping[str, Any],
) -> tuple[SessionHistory, dict[str, Any]]:
    """Apply one completed host transcript in memory and return exact history."""
    if plan.get("schema_version") != "1.0" or plan.get("mode") != "live":
        raise ValueError("Session recording plan requires schema_version 1.0 and live mode")
    release = load_release(release_bytes)
    bindings = tuple(
        ActorBinding(
            str(item["binding_id"]),
            Actor(str(item["actor_id"]), "human", str(item["label"])),
            str(item["seat_id"]),
            1,
        )
        for item in plan["bindings"]
    )
    viewers = tuple(
        ViewerGrant(str(item["viewer_id"]), str(item["role"]))
        for item in plan["viewers"]
    )
    host_ids = [item.viewer_id for item in viewers if item.role == "host"]
    if len(host_ids) != 1:
        raise ValueError("Session recording plan requires exactly one host Viewer")
    binding_by_seat = {item.seat_id: item for item in bindings}
    if len(binding_by_seat) != len(bindings):
        raise ValueError("Session recording plan cannot bind a Seat twice")
    history = create_session(
        release=release,
        session_id=str(plan["session_id"]),
        mode="live",
        bindings=bindings,
        viewers=viewers,
    )
    for raw in plan["commands"]:
        authority = raw["authority"]
        kind = str(authority["kind"])
        if kind == "host":
            auth = AuthorizationContext("viewer", host_ids[0])
        elif kind == "seat":
            seat_id = str(authority["seat_id"])
            binding = binding_by_seat.get(seat_id)
            if binding is None:
                raise ValueError(f"Session command names an unbound Seat: {seat_id}")
            auth = AuthorizationContext("actor", binding.actor.id, binding.id)
        else:
            raise ValueError(f"unsupported Session transcript authority: {kind}")
        payload = dict(raw.get("payload", {}))
        if (
            str(raw["action"]) == "record-resolution"
            and payload.get("submission_sequence") == "last-resolution-submission"
        ):
            submissions = [
                item.sequence for item in history.ordered_events
                if item.event_type == "resolution-submitted"
            ]
            if not submissions:
                raise ValueError("resolution alias has no prior submission")
            payload["submission_sequence"] = submissions[-1]
        command = SessionCommand(
            str(raw["command_id"]),
            history.session_id,
            release.release_id,
            history.sequence,
            str(raw["action"]),
            payload,
        )
        result = apply_command(release, history, command, auth)
        if not result.receipt.accepted:
            raise ValueError(
                f"Session transcript command rejected: {command.command_id}: "
                f"{result.receipt.trusted_reason}"
            )
        history = result.history
    verify_history(history)
    if not any(
        item.event_type == "resolution-recorded" for item in history.ordered_events
    ):
        raise ValueError("Session recording plan must end in a recorded resolution")
    summary = {
        "schema_version": "1.0",
        "session_id": history.session_id,
        "release_id": history.release_id,
        "session_history_ref": history.content_hash,
        "event_count": len(history.ordered_events),
        "receipt_count": len(history.receipts),
        "status": "resolved",
    }
    return history, summary


def run(
    release_path: str | Path,
    plan_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    plan = json.loads(Path(plan_path).read_bytes())
    history, summary = record_session_plan(Path(release_path).read_bytes(), plan)
    atomic_write(Path(output_path), history.to_bytes())
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release")
    parser.add_argument("plan")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    print(canonical_json(run(args.release, args.plan, args.output)).decode())


if __name__ == "__main__":
    main()
