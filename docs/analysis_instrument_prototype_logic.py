"""PROTOTYPE — pure eligibility checks for the frozen Analysis Instrument."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + sha256(encoded).hexdigest()


def base_lineage(instrument: dict[str, Any]) -> dict[str, Any]:
    assignments = {
        item["assignment"]: {
            "authority": item["authority"],
            "principal": item["principal"],
            "view": item["view"],
            "visible_fields": expanded_allow(instrument, item["view"]),
            "status": "complete",
            "receipt_complete": True,
            "attempts": [{"kind": "initial", "receipt": True}],
            "mutated_proposal": False,
        }
        for item in instrument["authorities"]
    }
    return {
        "scenario": "eligible reference lineage",
        "episode_actor_principals": ["episode:host", "episode:seat:a", "episode:seat:b"],
        "assignments": assignments,
        "attribution_cross_exposure": False,
        "no_finding_claim": False,
        "corroboration_claim": True,
        "instrument_ref": canonical_hash(instrument),
    }


def expanded_allow(instrument: dict[str, Any], view_name: str) -> list[str]:
    view = instrument["evidence_views"][view_name]
    values = []
    if "extends" in view:
        values.extend(expanded_allow(instrument, view["extends"]))
    values.extend(view.get("allow", []))
    return sorted(set(values))


def expanded_deny(instrument: dict[str, Any], view_name: str) -> set[str]:
    view = instrument["evidence_views"][view_name]
    values: set[str] = set()
    if "extends" in view:
        values.update(expanded_deny(instrument, view["extends"]))
    values.update(view.get("deny", []))
    return values


def scenarios(instrument: dict[str, Any]) -> list[dict[str, Any]]:
    valid = base_lineage(instrument)
    result = [valid]

    contaminated = deepcopy(valid)
    contaminated["scenario"] = "truth leaked into discovery view"
    contaminated["assignments"]["sweep-outcome-progress"]["visible_fields"].append(
        "canonical_world_truth"
    )
    result.append(contaminated)

    collision = deepcopy(valid)
    collision["scenario"] = "reviewer reuses proposal contributor principal"
    collision["assignments"]["independent-reviewer"]["principal"] = collision[
        "assignments"
    ]["atlas-curator"]["principal"]
    result.append(collision)

    cross_exposure = deepcopy(valid)
    cross_exposure["scenario"] = "attribution B sees attribution A before freezing"
    cross_exposure["attribution_cross_exposure"] = True
    result.append(cross_exposure)

    partial = deepcopy(valid)
    partial["scenario"] = "partial discovery sweep claims no finding"
    partial["assignments"]["sweep-host-dependence"]["status"] = "partial"
    partial["no_finding_claim"] = True
    result.append(partial)

    semantic_retry = deepcopy(valid)
    semantic_retry["scenario"] = "semantic best-of retry"
    semantic_retry["assignments"]["semantic-interpreter"]["attempts"] = [
        {"kind": "initial", "receipt": True},
        {"kind": "semantic-retry", "receipt": True},
    ]
    result.append(semantic_retry)

    receipt_gap = deepcopy(valid)
    receipt_gap["scenario"] = "challenge output lacks complete receipt"
    receipt_gap["assignments"]["challenge-designer"]["receipt_complete"] = False
    result.append(receipt_gap)

    edit = deepcopy(valid)
    edit["scenario"] = "reviewer edits proposal while accepting"
    edit["assignments"]["independent-reviewer"]["mutated_proposal"] = True
    result.append(edit)

    actor_collision = deepcopy(valid)
    actor_collision["scenario"] = "episode actor analyzes own trace"
    actor_collision["assignments"]["sweep-knowledge-support"]["principal"] = (
        actor_collision["episode_actor_principals"][1]
    )
    result.append(actor_collision)
    return result


def validate(instrument: dict[str, Any], lineage: dict[str, Any]) -> dict[str, Any]:
    findings: list[str] = []
    assignments = lineage["assignments"]

    for name, state in assignments.items():
        denied = expanded_deny(instrument, state["view"])
        leaks = sorted(denied.intersection(state["visible_fields"]))
        if leaks:
            findings.append(f"view:{name}: denied fields exposed: {', '.join(leaks)}")
        if not state["receipt_complete"]:
            findings.append(f"receipt:{name}: incomplete Analysis Receipt")
        for attempt in state["attempts"]:
            if not attempt.get("receipt"):
                findings.append(f"retry:{name}: attempt has no receipt")
            if attempt["kind"] not in {"initial", "transport-retry", "schema-repair"}:
                findings.append(f"retry:{name}: forbidden {attempt['kind']}")
        transport = sum(item["kind"] == "transport-retry" for item in state["attempts"])
        repairs = sum(item["kind"] == "schema-repair" for item in state["attempts"])
        if transport > instrument["retry_policy"]["transport_attempts"]:
            findings.append(f"retry:{name}: transport attempts exceeded")
        if repairs > instrument["retry_policy"]["schema_repair_attempts"]:
            findings.append(f"retry:{name}: schema repair attempts exceeded")

    discoverers = [
        state
        for state in assignments.values()
        if state["authority"] == "incident-discoverer"
    ]
    for state in discoverers:
        if state["principal"] in lineage["episode_actor_principals"]:
            findings.append("principal: episode actor occupies Incident Discoverer")

    protected = [
        "incident-assembler",
        "semantic-interpreter",
        "attribution-a",
        "attribution-b",
        "atlas-curator",
        "challenge-designer",
        "independent-reviewer",
    ]
    principals = [assignments[name]["principal"] for name in protected]
    if len(principals) != len(set(principals)):
        findings.append("principal: conflicting authorities share a principal")

    sweep_names = [name for name in assignments if name.startswith("sweep-")]
    incomplete = [name for name in sweep_names if assignments[name]["status"] != "complete"]
    if incomplete and (lineage["no_finding_claim"] or lineage["corroboration_claim"]):
        findings.append(
            "discovery: incomplete sweep cannot support no-finding or corroboration: "
            + ", ".join(incomplete)
        )

    if lineage["attribution_cross_exposure"]:
        findings.append("independence: attribution outputs crossed before both froze")

    if assignments["independent-reviewer"]["mutated_proposal"]:
        findings.append("authority: reviewer mutated the frozen proposal")

    return {
        "scenario": lineage["scenario"],
        "instrument_ref": lineage["instrument_ref"],
        "eligible": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "assignment_count": len(assignments),
        "complete_assignments": sum(
            item["status"] == "complete" and item["receipt_complete"]
            for item in assignments.values()
        ),
    }
