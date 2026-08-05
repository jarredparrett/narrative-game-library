"""Stage 3 Candidate and deterministic Game Release acceptance tests."""

from __future__ import annotations

import ast
import base64
from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import zipfile

from narrative_game.authoring import parse_game_definition
from narrative_game.compiler import (
    CompilationFinding,
    MaterialInput,
    compile_candidate,
    freeze_candidate,
    reference_component_lock,
)
from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.stage3_fixture import (
    MATERIAL_BYTES,
    build_micro_candidate,
    materialized_game_mapping,
)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "micro-game" / "game.json"


def candidate(seed: int = 17):
    return build_micro_candidate(FIXTURE.read_bytes(), seed=seed)


def test_candidate_release_and_bundle_identities_are_pinned():
    """stage3.release-identity: one frozen Candidate has one exact Release."""
    frozen = candidate()
    result = compile_candidate(frozen)
    assert result.ok and result.release is not None
    release = result.release
    assert release.candidate_id == frozen.candidate_id
    assert release.manifest["candidate_id"] == frozen.candidate_id
    assert release.manifest["release_id"] == release.release_id
    assert result.attempt.release_id == release.release_id
    assert result.attempt.bundle_hash == release.bundle_hash
    assert result.attempt.outcome == "released"
    assert frozen.candidate_id == "sha256:db56299bcdfa36d60aac91571d9abf56d4ce9e46a30826ab38f04d4959d930b8"
    assert release.release_id == "sha256:9c79b9497609c47b6c3a7fbd5337afae08870aa0fe2cea455786bcffbe4da4a4"
    assert release.bundle_hash == "sha256:459bb11ffc63e16f5a2d2f4cc5bc092cd355eb1831c3dad729c3f840bc427700"


def test_release_bytes_are_identical_across_processes():
    """stage3.cross-process: clean compiler processes emit byte-identical archives."""
    command = (
        "from pathlib import Path; import base64; "
        "from narrative_game.stage3_fixture import build_micro_candidate; "
        "from narrative_game.compiler import compile_candidate; "
        f"c=build_micro_candidate(Path({str(FIXTURE)!r}).read_bytes()); "
        "r=compile_candidate(c).release; "
        "print(c.candidate_id); print(r.release_id); print(r.bundle_hash); "
        "print(base64.b64encode(r.bundle_bytes).decode())"
    )
    first = subprocess.check_output([sys.executable, "-c", command])
    second = subprocess.check_output([sys.executable, "-c", command])
    assert first == second
    encoded = first.splitlines()[-1]
    assert base64.b64decode(encoded).startswith(b"PK")


def test_release_is_self_contained_and_every_file_hash_verifies():
    """stage3.self-contained: Release bytes need no Draft, network, or authoring store."""
    release = compile_candidate(candidate()).release
    assert release is not None
    with zipfile.ZipFile(BytesIO(release.bundle_bytes)) as archive:
        names = sorted(archive.namelist())
        assert names == sorted(item.path for item in release.files)
        assert "release.json" in names
        assert "trusted/game.json" in names
        assert all(f"materials/{resource_id}" in names for resource_id in MATERIAL_BYTES)
        for item in release.files:
            assert digest_bytes(archive.read(item.path)) == item.content_hash


def test_tampered_candidate_blocks_without_partial_release():
    """stage3.blockers: failed material integrity produces only an Attempt."""
    frozen = candidate()
    first = frozen.materials[0]
    tampered = replace(
        frozen,
        materials=(replace(first, data=first.data + b"tampered"), *frozen.materials[1:]),
    )
    result = compile_candidate(tampered)
    assert result.release is None
    assert result.attempt.outcome == "blocked"
    assert result.attempt.release_id is None
    assert result.attempt.bundle_hash is None
    assert [item.code for item in result.attempt.findings] == [
        "compiler.candidate-material-mutation",
        "compiler.material-hash-mismatch",
    ]

    changed_seed = compile_candidate(replace(frozen, seed=18))
    assert changed_seed.release is None
    assert [item.code for item in changed_seed.attempt.findings] == [
        "compiler.candidate-semantic-mutation"
    ]


def test_warnings_remain_visible_without_claiming_stronger_standing():
    """stage3.warnings: nonfatal risk survives in report and Attempt."""
    warning = CompilationFinding(
        code="facilitated.optional-pacing-risk",
        severity="warning",
        owner="facilitated-investigation",
        owner_version="0.1.0",
        locus="phase:opening",
        quote="one opening beat",
        message="the opening may feel compressed",
        evidence={"instrument": "fixture-review-v1"},
    )
    base = candidate()
    frozen = freeze_candidate(
        game=base.game,
        materials=base.materials,
        seed=base.seed,
        component_lock=base.component_lock,
        compilation_options=base.compilation_options,
        advisories=[warning],
    ).candidate
    assert frozen is not None
    result = compile_candidate(frozen)
    assert result.release is not None
    assert result.attempt.findings == (warning,)
    assert result.release.manifest["compilation_report"]["warnings"][0]["code"] == warning.code
    assert result.release.manifest["standing"] == "development-only"


def test_play_affecting_inputs_change_candidate_and_release_identity():
    """stage3.input-commitment: seed, access, and components are identity-bearing."""
    baseline_candidate = candidate()
    baseline = compile_candidate(baseline_candidate).release
    changed_seed_candidate = candidate(seed=18)
    changed_seed = compile_candidate(changed_seed_candidate).release
    assert baseline is not None and changed_seed is not None
    assert baseline_candidate.candidate_id != changed_seed_candidate.candidate_id
    assert baseline.release_id != changed_seed.release_id

    mapping = materialized_game_mapping(FIXTURE.read_bytes())
    mapping["kernel"]["access_policies"][0]["grantees"].remove("seat:blake")
    opening_interview = next(
        item for item in mapping["narrative"]["reveals"] if item["id"] == "reveal-interview"
    )
    opening_interview["audience_seat_ids"].remove("blake")
    changed_access_candidate = build_micro_candidate(
        FIXTURE.read_bytes(), game_override=mapping
    )
    changed_access = compile_candidate(changed_access_candidate).release
    assert changed_access is not None
    assert changed_access_candidate.candidate_id != baseline_candidate.candidate_id
    assert changed_access.release_id != baseline.release_id


def test_seat_projections_contain_no_truth_proof_or_material_bytes():
    """stage3.secrecy: authorization happens before Seat serialization."""
    release = compile_candidate(candidate()).release
    assert release is not None
    forbidden_keys = {
        "truth_model",
        "correct_hypothesis_id",
        "acceptable_proof_path_ids",
        "proof_paths",
    }

    def keys(value):
        if isinstance(value, dict):
            for key, child in value.items():
                yield key
                yield from keys(child)
        elif isinstance(value, list):
            for child in value:
                yield from keys(child)

    for seat_id in ("avery", "blake"):
        data = release.file(f"projections/seats/{seat_id}.json").data
        projection = json.loads(data)
        assert not forbidden_keys & set(keys(projection))
        assert all(material not in data for material in MATERIAL_BYTES.values())


def test_invalid_draft_or_component_lock_cannot_freeze_candidate():
    """stage3.freeze-gate: hard gates cannot be waived at Candidate freeze."""
    mapping = materialized_game_mapping(FIXTURE.read_bytes())
    mapping["narrative"]["proof_paths"][0]["evidence_ids"][0] = "missing-evidence"
    game = parse_game_definition(json.dumps(mapping))
    materials = [
        MaterialInput(
            resource_id=resource_id,
            media_type=next(item.media_type for item in game.kernel.resources if item.id == resource_id),
            data=data,
            reproduction_receipt={"kind": "fixture"},
        )
        for resource_id, data in MATERIAL_BYTES.items()
    ]
    invalid = freeze_candidate(
        game=game,
        materials=materials,
        seed=17,
        component_lock=reference_component_lock(),
    )
    assert invalid.candidate is None
    assert any(item.code == "narrative.dangling-reference" for item in invalid.findings)

    valid_game = candidate().game
    lock = reference_component_lock()
    lock["components"][-1]["version"] = "0.3.1"
    incompatible = freeze_candidate(
        game=valid_game,
        materials=candidate().materials,
        seed=17,
        component_lock=lock,
    )
    assert incompatible.candidate is None
    assert [item.code for item in incompatible.findings] == [
        "compiler.incompatible-component-lock"
    ]


def test_compiler_package_has_no_ambient_effect_imports():
    """stage3.purity: compiler reads no filesystem, network, clock, model, or randomness."""
    root = Path(__file__).parents[1] / "src" / "narrative_game" / "compiler"
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


def test_release_manifest_is_canonical_and_commits_component_graph():
    """stage3.traceability: Release links Candidate, components, content, and report."""
    frozen = candidate()
    release = compile_candidate(frozen).release
    assert release is not None
    assert release.file("release.json").data == canonical_json(release.manifest)
    assert release.manifest["component_lock"] == reference_component_lock()
    assert {item["resource_id"] for item in release.manifest["materials"]} == set(MATERIAL_BYTES)
    assert all(item["content_hash"].startswith("sha256:") for item in release.manifest["files"])
