"""Deterministic Micro Fixture assembly for compiler capability tests."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping

from narrative_game.authoring import parse_game_definition
from narrative_game.compiler import MaterialInput, freeze_candidate, reference_component_lock
from narrative_game.contracts.canonical import digest_bytes, digest_json


MATERIAL_BYTES = {
    "closing-interview": (
        b"# Closing interview\n\nThe clerk confirms returning after an evening call.\n"
    ),
    "key-register": b'{"entries":[{"holder":"clerk","key":"records","status":"out"}]}',
    "camera-log": b"time,zone,motion\n21:00,outside-window,false\n",
    "cash-receipt": b"%PDF-1.4\n% deterministic micro-fixture receipt\n%%EOF\n",
}


def materialized_game_mapping(game_json: str | bytes) -> dict[str, Any]:
    value = deepcopy(json.loads(game_json))
    for resource in value["kernel"]["resources"]:
        resource["content_hash"] = digest_bytes(MATERIAL_BYTES[resource["id"]])
    return value


def build_micro_candidate(
    game_json: str | bytes,
    *,
    seed: int = 17,
    game_override: Mapping[str, Any] | None = None,
):
    mapping = deepcopy(game_override) if game_override is not None else materialized_game_mapping(game_json)
    game = parse_game_definition(json.dumps(mapping))
    media_types = {item.id: item.media_type for item in game.kernel.resources}
    materials = []
    for resource_id, data in MATERIAL_BYTES.items():
        receipt = {
            "schema_version": "0.3",
            "kind": "fixture-material",
            "resource_id": resource_id,
            "input_hash": digest_bytes(data),
            "operation": "materialize-existing-fixture",
        }
        attestation = None
        if resource_id == "cash-receipt":
            attestation = {
                "schema_version": "0.1",
                "artifact_hash": digest_bytes(data),
                "standing": "fixture-only",
                "verified": True,
            }
        materials.append(
            MaterialInput(
                resource_id=resource_id,
                media_type=media_types[resource_id],
                data=data,
                reproduction_receipt=receipt,
                artifact_attestation=attestation,
            )
        )
    result = freeze_candidate(
        game=game,
        materials=materials,
        seed=seed,
        component_lock=reference_component_lock(),
        compilation_options={
            "locale": "en-US",
            "presentation": "hybrid",
            "physical_provenance": "fictional-game-material",
        },
    )
    if not result.ok or result.candidate is None:
        raise ValueError([item.to_mapping() for item in result.findings])
    return result.candidate
