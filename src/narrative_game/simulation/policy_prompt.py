"""Shared model-facing arena protocol without provider dependencies."""

from __future__ import annotations

import base64
from io import BytesIO
import json
from typing import Any, Mapping

from pypdf import PdfReader

from narrative_game.contracts.canonical import canonical_json


TOOL_ARGUMENT_CONTRACTS: dict[str, dict[str, str]] = {
    "open_session": {},
    "broadcast": {"text": "string"},
    "advance_phase": {"phase_id": "exact next phase id"},
    "disclose_resource": {
        "resource_id": "exact resource id",
        "audience_seat_ids": "array of exact seat ids",
        "evidence_grade": "runtime-enforced | host-witnessed | actor-reported",
    },
    "deliver_intervention": {
        "intervention_id": "exact intervention id",
        "audience_seat_ids": "array of exact seat ids",
        "reason": "string",
    },
    "end_session": {"reason": "string"},
    "inspect_evidence": {"resource_id": "exact role-visible resource id"},
    "say": {"text": "string"},
    "message": {"seat_id": "exact other seat id", "text": "string"},
    "request_evidence": {"resource_id": "exact resource id"},
    "request_hint": {"request": "string"},
    "share_claim": {
        "proposition_id": "exact role-visible proposition id",
        "stance": "accepts | rejects",
    },
    "submit_resolution": {
        "hypothesis_id": "exact role-visible hypothesis id",
        "proof_path_id": "exact role-visible proof path id",
        "explanation": "concise evidence-grounded explanation",
    },
    "update_character_state": {
        "move_id": "current-phase move id or null",
        "objective_id": "owned active objective id or null",
        "objective_status": "active | advanced | satisfied | abandoned | null",
        "belief_proposition_id": "revisable belief id or null",
        "belief_stance": "accepts | rejects | uncertain | null",
        "human_direction": "string or null",
    },
}


def _extract_resource_text(raw: bytes) -> str:
    if raw.startswith(b"%PDF"):
        reader = PdfReader(BytesIO(raw))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    return raw.decode("utf-8", errors="replace")


def model_observation(
    observation: Mapping[str, Any],
    *,
    include_static: bool,
    dialogue_after: int,
    actions_after: int,
) -> dict[str, Any]:
    """Return the first authorized snapshot or only the next stateful delta."""
    value = json.loads(canonical_json(observation))
    for action in value.get("own_prior_actions", []):
        content = action.get("result", {}).get("content", {})
        encoded = content.pop("content_base64", None)
        if encoded is None:
            continue
        raw = base64.b64decode(encoded)
        text = _extract_resource_text(raw)
        content["content_text"] = text[:60000]
        content["content_truncated"] = len(text) > 60000
    if include_static:
        return value
    value["dialogue"] = [
        item
        for item in value.get("dialogue", [])
        if int(item.get("sequence", -1)) > dialogue_after
    ]
    value["own_prior_actions"] = value.get("own_prior_actions", [])[actions_after:]
    snapshot = value.get("game", {})
    if value.get("role") == "host":
        state = snapshot.get("state", {})
        value["game"] = {
            "authority": snapshot.get("authority"),
            "state": {
                key: state.get(key)
                for key in (
                    "status",
                    "phase_id",
                    "sequence",
                    "evidence_requests",
                    "disclosures",
                    "interventions",
                    "resolution",
                )
            },
        }
    else:
        dossier = snapshot.get("dossier") or {}
        value["game"] = {
            key: snapshot.get(key)
            for key in (
                "status",
                "phase_id",
                "resources",
                "private_notes",
                "visible_events",
                "character_state",
                "resolution_prompt",
                "resolution_options",
            )
            if key in snapshot
        }
        if dossier:
            value["game"]["active_arc"] = dossier.get("active_arc")
    return value


def policy_guidance(role: str, observation: Mapping[str, Any]) -> list[str]:
    """Make protocol-critical choices salient without scripting a solution."""
    remaining = int(observation["remaining_steps"])
    if role == "host":
        return [
            "The host acts once per complete seat cycle; treat remaining_steps as a hard budget.",
            "Open a created session immediately.",
            "Advance phases promptly so a seat reaches resolution with a turn left.",
            "Disclose an exact authorized resource when requested and budget permits.",
            f"There are {remaining} total arena actions left.",
        ]
    return [
        "inspect_evidence accepts only an ID currently listed in game.resources.",
        "request_evidence accepts only an exact ID from requestable_resources.",
        "At resolution, prioritize submit_resolution with exact visible option IDs.",
        "Use say for bounded facts and update_character_state for genuine progress.",
        f"There are {remaining} total arena actions left.",
    ]

