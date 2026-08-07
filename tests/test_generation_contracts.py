"""Capability tests for pure initial-generation contracts."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys

import pytest

from narrative_game.blueprint import (
    GameBlueprint,
    bind_artifact_specification,
    validate_blueprint,
)
from narrative_game.contracts import canonical_json
from narrative_game.climb import Dimension, FrozenInstrument
from narrative_game.examples import vanished_ledger_blueprint
from narrative_game.generation.model import (
    GENERATION_SCHEMA_VERSION,
    ArtifactPlan,
    ArtifactSpecification,
    CreativeBrief,
    GenerationBudget,
    GenerationPlan,
    ModelRoleAssignment,
    StopPolicy,
)
from narrative_game.profiles import FacilitatedInvestigationAuthoringAdapter


def _brief() -> CreativeBrief:
    blueprint = vanished_ledger_blueprint()
    game = blueprint.materialize_game()
    return CreativeBrief(
        game.kernel.title,
        game.direction.premise,
        game.direction.experience_targets,
        game.direction.content_boundaries,
        len(game.profile.supported_seat_ids),
        sum(item.target_minutes for item in blueprint.arc),
        "hybrid",
        blueprint.seed,
    )


def _specification(
    *,
    artifact_id: str = "cash-receipt-facsimile",
    resource_id: str = "cash-receipt",
    blueprint: GameBlueprint | None = None,
) -> ArtifactSpecification:
    intent = ArtifactSpecification(
        artifact_id=artifact_id,
        resource_id=resource_id,
        document_class="1990s-cash-receipt",
        seed=6103,
        proposition_ids=("cash-payment",),
        event_ids=("payment-made",),
        pins={"currency": "USD"},
        canon={"represented_date": "1997-10-14"},
        accessibility={"required": True, "format": "text/plain"},
        permitted_audience_ids=("avery", "host"),
    )
    return bind_artifact_specification(
        blueprint or vanished_ledger_blueprint(), intent
    )


def _roles() -> tuple[ModelRoleAssignment, ...]:
    return (
        ModelRoleAssignment("builder", "builder-1", "fixture", "creator-v1", "builder-agent", "builder-context"),
        ModelRoleAssignment("reviewer", "reviewer-1", "fixture", "reviewer-v1", "reviewer-agent", "reviewer-context"),
        ModelRoleAssignment("judge", "judge-1", "fixture", "judge-v1", "judge-agent-1", "judge-context-1"),
        ModelRoleAssignment("judge", "judge-2", "fixture", "judge-v1", "judge-agent-2", "judge-context-2"),
    )


def test_generation_contracts_are_versioned_content_addressed_and_deterministic():
    """generation.contracts: canonical plans survive strict round trips across processes."""
    brief = _brief()
    artifact_plan = ArtifactPlan((_specification(),), ("cash-receipt-facsimile",))
    plan = GenerationPlan(
        "generation-example",
        "narrative.facilitated-investigation-authoring",
        "1.0.0",
        brief.seed,
        _roles(),
        GenerationBudget(12, 48_000, 4),
        StopPolicy(2),
        artifact_plan,
    )
    assert CreativeBrief.from_mapping(brief.to_mapping()) == brief
    assert GenerationPlan.from_mapping(plan.to_mapping()) == plan
    assert plan.plan_id.startswith("generation-plan:")

    tampered = brief.to_mapping()
    tampered["title"] = "Changed after identity was assigned"
    with pytest.raises(ValueError, match="identity"):
        CreativeBrief.from_mapping(tampered)
    with pytest.raises(ValueError, match="exactly once"):
        ArtifactPlan((_specification(),), ())

    script = """
from narrative_game.generation.model import *
from narrative_game.contracts import canonical_json
brief = CreativeBrief('A', 'B', ('C',), (), 2, 60, 'hybrid', 73)
roles = (
    ModelRoleAssignment('builder', 'b', 'fixture', 'v1', 'ba', 'bc'),
    ModelRoleAssignment('reviewer', 'r', 'fixture', 'v1', 'ra', 'rc'),
    ModelRoleAssignment('judge', 'j2', 'fixture', 'v1', 'j2a', 'j2c'),
    ModelRoleAssignment('judge', 'j1', 'fixture', 'v1', 'j1a', 'j1c'),
)
plan = GenerationPlan('e', 'p', '1', 73, roles, GenerationBudget(4, 1000, 2), StopPolicy(2), ArtifactPlan((), ()))
print(canonical_json({'brief': brief.to_mapping(), 'plan': plan.to_mapping()}).decode())
"""
    outputs = []
    for hash_seed in ("1", "987654"):
        outputs.append(
            subprocess.check_output(
                [sys.executable, "-c", script],
                cwd=Path.cwd(),
                env=dict(os.environ, PYTHONHASHSEED=hash_seed),
            )
        )
    assert outputs[0] == outputs[1]


def test_production_target_requires_complete_evidence_artifact_coverage():
    """generation.production-artifacts: production cannot opt out of realism
    by omitting Artifact Specifications for player-visible evidence records."""
    blueprint = vanished_ledger_blueprint()
    adapter = FacilitatedInvestigationAuthoringAdapter()

    adapter.validate_release_target(
        blueprint, ArtifactPlan((), ()), release_target="development"
    )
    with pytest.raises(ValueError, match="camera-log.*closing-interview.*key-register"):
        adapter.validate_release_target(
            blueprint, ArtifactPlan((), ()), release_target="production"
        )

    one = _specification()
    partial = replace(blueprint, artifact_specifications=(one,))
    with pytest.raises(ValueError, match="camera-log.*closing-interview.*key-register"):
        adapter.validate_release_target(
            partial,
            ArtifactPlan((one,), (one.artifact_id,)),
            release_target="production",
        )


def test_release_target_is_frozen_without_changing_legacy_plan_identity():
    """generation.release-target: production intent is content-addressed while
    legacy development Plans preserve their serialized identity."""
    brief = _brief()
    legacy = GenerationPlan(
        "generation-example", "narrative.facilitated-investigation-authoring",
        "1.0.0", brief.seed, _roles(), GenerationBudget(12, 48_000, 4),
        StopPolicy(2), ArtifactPlan((), ()),
    )
    assert "release_target" not in legacy.to_mapping()
    assert GenerationPlan.from_mapping(legacy.to_mapping()) == legacy

    production = replace(legacy, release_target="production")
    assert production.to_mapping()["release_target"] == "production"
    assert production.plan_id != legacy.plan_id
    assert GenerationPlan.from_mapping(production.to_mapping()) == production


def test_production_instrument_requires_visual_and_host_quality_floors():
    """generation.production-measurement: a narrative-only rubric cannot
    qualify a player-visible production package."""
    adapter = FacilitatedInvestigationAuthoringAdapter()
    weak = FrozenInstrument(
        "weak", "1", "game", (
            Dimension("world_coherence", "Coherent.", 1, {"0": "no", "100": "yes"}),
        ),
        ({"metric": "overall", "operator": ">=", "value": 70},),
        {"panel_size": 3},
        ("authoring.valid",),
    )
    with pytest.raises(ValueError, match="required dimensions"):
        adapter.validate_release_instrument(weak, release_target="production")

    dimensions = weak.dimensions + tuple(
        Dimension(code, code, 1, {"0": "unusable", "100": "excellent"})
        for code in adapter.production_dimension_floors
    )
    missing_inspection = replace(
        weak,
        dimensions=dimensions,
        acceptance_rules=tuple(
            {"metric": code, "operator": ">=", "value": floor}
            for code, floor in adapter.production_dimension_floors.items()
        ),
    )
    with pytest.raises(ValueError, match="inspect exact trial/print"):
        adapter.validate_release_instrument(
            missing_inspection, release_target="production"
        )

    production = replace(
        missing_inspection,
        blind_protocol={"panel_size": 3, "inspect_print_renditions": True},
    )
    adapter.validate_release_instrument(production, release_target="production")


def test_blueprint_preserves_legacy_serialization_and_validates_artifact_references():
    """generation.blueprint: old text sources retain identity while artifact intent coexists."""
    legacy = vanished_ledger_blueprint().to_mapping()
    assert "artifact_specifications" not in legacy
    assert GameBlueprint.from_mapping(legacy).to_mapping() == legacy

    blueprint = replace(
        vanished_ledger_blueprint(), artifact_specifications=(_specification(),)
    )
    assert validate_blueprint(blueprint) == ()
    assert blueprint.to_mapping()["artifact_specifications"] == [
        _specification().to_mapping()
    ]
    assert blueprint.material_inputs() == vanished_ledger_blueprint().material_inputs()

    invalid = replace(
        blueprint,
        artifact_specifications=(
            _specification(),
            replace(
                _specification(artifact_id="second"),
                proposition_ids=("missing-proposition",),
                event_ids=("missing-event",),
            ),
        ),
    )
    assert {
        "authoring.duplicate-artifact-resource",
        "authoring.dangling-artifact-proposition",
        "authoring.dangling-artifact-event",
    } <= {item.code for item in validate_blueprint(invalid)}


def test_artifact_truth_binding_invalidates_every_canonical_world_drift():
    """generation.artifact-truth: pins/canon cannot float free of referenced world facts."""
    source = vanished_ledger_blueprint()
    specification = _specification(blueprint=source)
    blueprint = replace(source, artifact_specifications=(specification,))
    assert validate_blueprint(blueprint) == ()

    for section, identity, field, changed in (
        ("propositions", "cash-payment", "expression", "A different payment occurred."),
        ("truth_model", "cash-payment", "value", "false"),
        ("events", "payment-made", "summary", "A different represented event."),
    ):
        mapping = blueprint.to_mapping()
        records = mapping["game"]["narrative"][section]
        id_field = "proposition_id" if section == "truth_model" else "id"
        next(item for item in records if item[id_field] == identity)[field] = changed
        stale = GameBlueprint.from_mapping(mapping)
        assert "authoring.stale-artifact-truth-binding" in {
            item.code for item in validate_blueprint(stale)
        }

    changed_request = replace(
        specification,
        pins={**dict(specification.pins), "currency": "CAD"},
    )
    stale_request = replace(blueprint, artifact_specifications=(changed_request,))
    assert "authoring.stale-artifact-truth-binding" in {
        item.code for item in validate_blueprint(stale_request)
    }
    rebound = bind_artifact_specification(blueprint, changed_request)
    assert validate_blueprint(
        replace(blueprint, artifact_specifications=(rebound,))
    ) == ()

    with pytest.raises(ValueError, match="without canonical truth bindings"):
        ArtifactPlan(
            (replace(specification, truth_binding=""),),
            (specification.artifact_id,),
        )
    with pytest.raises(ValueError, match="typed SHA-256"):
        replace(specification, truth_binding="sha256:" + "not-hex" * 9 + "x")


def test_profile_parses_only_complete_exact_valid_initial_creation_output():
    """generation.creation-parse: model output is accepted whole or rejected without repair."""
    adapter = FacilitatedInvestigationAuthoringAdapter()
    blueprint = replace(
        vanished_ledger_blueprint(), artifact_specifications=(_specification(),)
    )
    envelope = {
        "schema_version": GENERATION_SCHEMA_VERSION,
        "rationale": "Create one coherent investigation and identify its realism-sensitive receipt.",
        "blueprint": blueprint.to_mapping(),
    }
    parsed = adapter.parse_initial_creation_output(
        _brief(), envelope, research={"receipt_source": "registered research object"}
    )
    assert parsed == blueprint
    assert adapter.creation_contract()["output"]["schema_version"] == "0.1"

    extra = {**envelope, "notes": "silently ignoring this would repair the output"}
    with pytest.raises(ValueError, match="exactly"):
        adapter.parse_initial_creation_output(_brief(), extra)

    normalized = {**envelope, "blueprint": {**blueprint.to_mapping(), "unknown": True}}
    with pytest.raises(ValueError, match="exact canonical"):
        adapter.parse_initial_creation_output(_brief(), normalized)

    nested_game = blueprint.to_mapping()
    nested_game["game"]["narrative"]["direction"]["ignored"] = "not canonical"
    with pytest.raises(ValueError, match="Game Definition is not an exact canonical"):
        adapter.parse_initial_creation_output(
            _brief(), {**envelope, "blueprint": nested_game}
        )

    changed_seed = {
        **envelope,
        "blueprint": {**blueprint.to_mapping(), "seed": blueprint.seed + 1},
    }
    with pytest.raises(ValueError, match="seed does not match"):
        adapter.parse_initial_creation_output(_brief(), changed_seed)

    invalid = replace(
        blueprint,
        artifact_specifications=(
            replace(_specification(), proposition_ids=("missing-proposition",)),
        ),
    )
    with pytest.raises(ValueError, match="dangling-artifact-proposition"):
        adapter.parse_initial_creation_output(
            _brief(), {**envelope, "blueprint": invalid.to_mapping()}
        )


def test_generation_plan_requires_independent_role_occupancy():
    """generation.roles: one builder, one reviewer, and a blind judge panel are explicit."""
    with pytest.raises(ValueError, match="exactly one reviewer"):
        GenerationPlan(
            "e",
            "p",
            "1",
            1,
            tuple(item for item in _roles() if item.role != "reviewer"),
            GenerationBudget(3, 1000, 1),
            StopPolicy(1),
            ArtifactPlan((), ()),
        )
    duplicated_authority = (
        ModelRoleAssignment("builder", "same", "fixture", "v1", "builder-agent", "builder-context"),
        ModelRoleAssignment("reviewer", "same", "fixture", "v1", "reviewer-agent", "reviewer-context"),
        ModelRoleAssignment("judge", "judge", "fixture", "v1", "judge-agent", "judge-context"),
    )
    with pytest.raises(ValueError, match="reuses a model authority"):
        GenerationPlan(
            "e",
            "p",
            "1",
            1,
            duplicated_authority,
            GenerationBudget(3, 1000, 1),
            StopPolicy(1),
            ArtifactPlan((), ()),
        )
    for field_name, message in (
        ("agent_id", "reuses a model agent identity"),
        ("context_id", "reuses a model context identity"),
    ):
        roles = list(_roles())
        roles[1] = replace(
            roles[1], **{field_name: getattr(roles[0], field_name)}
        )
        with pytest.raises(ValueError, match=message):
            GenerationPlan(
                "e",
                "p",
                "1",
                1,
                tuple(roles),
                GenerationBudget(4, 1000, 1),
                StopPolicy(1),
                ArtifactPlan((), ()),
            )
