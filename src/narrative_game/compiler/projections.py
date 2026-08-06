"""Authorized, deterministic Release projections."""

from __future__ import annotations

from typing import Any

from narrative_game.narrative import (
    GameDefinition,
    available_evidence,
    phase_character_projection,
    render_dossier_markdown,
)


def seat_projection(game: GameDefinition, seat_id: str) -> dict[str, Any]:
    seat = next(item for item in game.kernel.seats if item.id == seat_id)
    character = next(item for item in game.characters if item.seat_id == seat_id)
    objectives = {item.id: item for item in game.objectives}
    propositions = {item.id: item.expression for item in game.propositions}
    evidence = {item.id: item for item in game.evidence}
    opening = min(game.phases, key=lambda item: item.order)
    visible_evidence = available_evidence(game, seat_id=seat_id, phase_id=opening.id)
    evidence_by_phase = []
    previous: set[str] = set()
    for phase in sorted(game.phases, key=lambda item: item.order):
        available = set(available_evidence(game, seat_id=seat_id, phase_id=phase.id))
        newly_available = sorted(available - previous)
        evidence_by_phase.append(
            {
                "phase_id": phase.id,
                "phase_label": phase.label,
                "evidence": [
                    {
                        "id": item,
                        "summary": evidence[item].summary,
                        "resource_id": evidence[item].resource_id,
                    }
                    for item in newly_available
                ],
            }
        )
        previous = available
    result = {
        "schema_version": "0.4",
        "seat": {"id": seat.id, "label": seat.label},
        "character": {
            "id": character.id,
            "name": character.name,
            "beliefs": [
                {
                    "proposition_id": belief.proposition_id,
                    "expression": propositions[belief.proposition_id],
                    "stance": belief.stance,
                    "basis": belief.basis,
                }
                for belief in character.beliefs
            ],
            "objectives": [
                {
                    "id": objectives[item].id,
                    "description": objectives[item].description,
                    "activation_phase_id": objectives[item].activation_phase_id,
                }
                for item in character.objective_ids
            ],
        },
        "opening_phase": opening.id,
        "available_evidence": [
            {
                "id": item,
                "summary": evidence[item].summary,
                "resource_id": evidence[item].resource_id,
            }
            for item in visible_evidence
        ],
        "evidence_by_phase": evidence_by_phase,
        "resolution_prompt": game.resolution.prompt,
        "allowed_actions": ["share-claim", "request-evidence", "submit-resolution"],
    }
    if game.character_program is not None:
        dossier = next(
            item for item in game.character_program.dossiers if item.seat_id == seat_id
        )
        result["character_program_id"] = game.character_program.program_id
        result["dossier"] = phase_character_projection(game, dossier, opening.id)
        result["dossier_markdown"] = render_dossier_markdown(
            game, dossier
        ).decode("utf-8")
        result["allowed_actions"].append("update-character-state")
    return result


def host_projection(game: GameDefinition) -> dict[str, Any]:
    return {
        "schema_version": "0.3",
        "authority": "trusted-host",
        "game": game.to_mapping(),
    }


def simulation_projection(game: GameDefinition, seats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "0.3",
        "authority": "trusted-simulation",
        "truth_model": [item.__dict__ for item in game.truth_model],
        "resolution": {
            "correct_hypothesis_id": game.resolution.correct_hypothesis_id,
            "acceptable_proof_path_ids": list(game.resolution.acceptable_proof_path_ids),
        },
        "seat_projections": seats,
    }


def export_projection(game: GameDefinition) -> dict[str, Any]:
    return {
        "schema_version": "0.3",
        "authority": "trusted-exporter",
        "resources": [item.__dict__ for item in game.kernel.resources],
        "access_policies": [
            {
                "id": item.id,
                "resource": str(item.resource),
                "grantees": [str(grantee) for grantee in item.grantees],
            }
            for item in game.kernel.access_policies
        ],
        "reveals": [
            {
                "id": item.id,
                "evidence_id": item.evidence_id,
                "phase_id": item.phase_id,
                "audience_seat_ids": list(item.audience_seat_ids),
            }
            for item in game.reveals
        ],
        "physical_policy": {
            "provenance": "fictional-game-material",
            "delivery": "hybrid",
        },
    }
