"""Shared model-facing arena protocol without provider dependencies."""

from __future__ import annotations

import base64
from io import BytesIO
import json
from typing import Any, Mapping

from pypdf import PdfReader
from pypdf.errors import PdfReadError

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
    "share_evidence": {
        "resource_id": "exact resource id previously inspected by this role",
        "finding": "concise bounded finding supported by that resource",
    },
    "say": {"text": "string"},
    "message": {"seat_id": "exact other seat id", "text": "string"},
    "request_evidence": {"resource_id": "exact resource id"},
    "request_hint": {"request": "string"},
    "share_claim": {
        "proposition_id": "exact role-visible proposition id",
        "stance": "accepts | rejects",
    },
    "submit_resolution": {
        "hypothesis_id": "exact candidate-theory id",
        "evidence_resource_ids": "array of exact acquired or publicly shared resource ids",
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
        try:
            reader = PdfReader(BytesIO(raw))
            return "\n\n".join(page.extract_text() or "" for page in reader.pages)
        except PdfReadError:
            # Some test and third-party resources advertise PDF media while
            # carrying a textual diagnostic stub. Preserve the exact content
            # for the policy rather than failing the whole episode.
            pass
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
                "candidate_theories",
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
            "Prioritize a pending evidence request that is authorized in the current phase; the trusted reveal graph tells you when it is legal.",
            "Advance after current-phase requests are handled, leaving several full seat cycles in the resolution phase.",
            "Do not end the session merely because an early resolution attempt was rejected.",
            f"There are {remaining} total arena actions left.",
        ]
    return [
        "inspect_evidence accepts only an ID currently listed in game.resources.",
        "request_evidence accepts only an exact ID from requestable_resources.",
        "Prioritize inspecting an uninspected visible record, then share its bounded finding so other roles can cite it.",
        "Use epistemic_state to avoid repeating inspections and to distinguish acquired records from mere filenames.",
        "At resolution, submit a candidate theory only with enough acquired records to establish a complete proof path.",
        "A rejected resolution means the cited acquired records are incomplete; continue investigating.",
        "Use say for bounded facts and update_character_state for genuine progress.",
        f"There are {remaining} total arena actions left.",
    ]
