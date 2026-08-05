"""Stage 2 acceptance and single-delta Defect Deck tests."""

from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from narrative_game.authoring import parse_game_definition
from narrative_game.narrative import (
    available_evidence,
    classify_claim,
    validate_facilitated_investigation,
)


FIXTURE = Path(__file__).parents[1] / "fixtures" / "micro-game" / "game.json"


def fixture_mapping() -> dict:
    return json.loads(FIXTURE.read_bytes())


def findings_for(value: dict):
    return validate_facilitated_investigation(parse_game_definition(json.dumps(value)))


def assert_finding(value: dict, *, code: str, quote: str) -> None:
    findings = findings_for(value)
    match = next(item for item in findings if item.code == code)
    assert match.quote == quote
    assert match.locus
    assert match.severity == "blocker"


def test_micro_fixture_passes_and_hashes_across_processes():
    """stage2.valid-fixture: valid input is stable, pure, and deterministic."""
    game = parse_game_definition(FIXTURE.read_bytes())
    assert validate_facilitated_investigation(game) == ()
    assert game.content_hash == "sha256:77601fae61deff0003e3928de988848e1cd3a478536eeeec3990a53aab421701"
    command = (
        "from pathlib import Path; "
        "from narrative_game.authoring import parse_game_definition; "
        "from narrative_game.narrative import validate_facilitated_investigation; "
        f"g=parse_game_definition(Path({str(FIXTURE)!r}).read_bytes()); "
        "print(g.content_hash); print(len(validate_facilitated_investigation(g)))"
    )
    first = subprocess.check_output([sys.executable, "-c", command])
    second = subprocess.check_output([sys.executable, "-c", command])
    assert first == second == f"{game.content_hash}\n0\n".encode()


def test_defect_dangling_reference_quotes_missing_evidence():
    """stage2.dangling-reference: every typed narrative edge resolves."""
    value = fixture_mapping()
    value["narrative"]["proof_paths"][0]["evidence_ids"][0] = "missing-evidence"
    assert_finding(
        value,
        code="narrative.dangling-reference",
        quote="missing-evidence",
    )


def test_defect_contradictory_truth_quotes_both_assignments():
    """stage2.contradictory-truth: one Proposition has one Truth owner."""
    value = fixture_mapping()
    value["narrative"]["truth_model"].append(
        {"proposition_id": "staff-key-used", "value": "false"}
    )
    assert_finding(
        value,
        code="narrative.contradictory-truth",
        quote="true / false",
    )


def test_defect_inaccessible_critical_evidence_names_the_evidence():
    """stage2.critical-access: all proof material can reach a supported Seat."""
    value = fixture_mapping()
    value["narrative"]["reveals"] = [
        item for item in value["narrative"]["reveals"] if item["id"] != "reveal-receipt"
    ]
    assert_finding(
        value,
        code="facilitated.inaccessible-critical-evidence",
        quote="receipt-evidence",
    )


def test_defect_single_point_proof_failure_names_the_only_path():
    """stage2.proof-redundancy: resolution has independent evidence routes."""
    value = fixture_mapping()
    value["narrative"]["resolution"]["acceptable_proof_path_ids"] = ["key-and-payment"]
    assert_finding(
        value,
        code="facilitated.single-point-proof-failure",
        quote="key-and-payment",
    )


def test_defect_shared_critical_evidence_is_not_independent():
    """stage2.proof-redundancy: nominally different routes cannot share one choke point."""
    value = fixture_mapping()
    value["narrative"]["proof_paths"][1]["evidence_ids"].append("register-evidence")
    assert_finding(
        value,
        code="facilitated.single-point-proof-failure",
        quote="register-evidence",
    )


def test_defect_premature_proof_names_early_paths():
    """stage2.reveal-timing: a complete case is not available too early."""
    value = fixture_mapping()
    value["narrative"]["resolution"]["phase_id"] = "debrief"
    assert_finding(
        value,
        code="facilitated.premature-proof",
        quote="key-and-payment, interview-and-camera",
    )


def test_defect_unauthorized_disclosure_names_forbidden_seat():
    """stage2.authorization: Reveals may only narrow Kernel access policy."""
    value = fixture_mapping()
    receipt = next(
        item for item in value["narrative"]["reveals"] if item["id"] == "reveal-receipt"
    )
    receipt["audience_seat_ids"].append("blake")
    assert_finding(
        value,
        code="facilitated.unauthorized-disclosure",
        quote="blake",
    )


def test_defect_inactive_seat_names_the_stranded_seat():
    """stage2.participation: every supported Seat can pursue an Objective."""
    value = fixture_mapping()
    value["narrative"]["characters"][0]["objective_ids"] = []
    assert_finding(value, code="facilitated.inactive-seat", quote="avery")


def test_defect_unrecoverable_progression_quotes_missing_host_power():
    """stage2.recovery: the host has an explicit route out of a dead end."""
    value = fixture_mapping()
    value["narrative"]["interventions"] = []
    assert_finding(
        value,
        code="facilitated.unrecoverable-progression",
        quote="no hint or recovery intervention",
    )


def test_derived_views_read_one_truth_and_access_owner():
    """stage2.canonical-owner: projections derive rather than copy verdicts."""
    value = fixture_mapping()
    game = parse_game_definition(json.dumps(value))
    before = classify_claim(
        game,
        character_id="avery-shaw",
        proposition_id="staff-key-used",
        stance="accepts",
    )
    assert before == {"factuality": "true", "intent": "sincere"}
    assert available_evidence(game, seat_id="avery", phase_id="opening") == (
        "interview-evidence",
        "register-evidence",
    )

    changed = deepcopy(value)
    assignment = next(
        item
        for item in changed["narrative"]["truth_model"]
        if item["proposition_id"] == "staff-key-used"
    )
    assignment["value"] = "false"
    after = classify_claim(
        parse_game_definition(json.dumps(changed)),
        character_id="avery-shaw",
        proposition_id="staff-key-used",
        stance="accepts",
    )
    assert after == {"factuality": "false", "intent": "sincere"}


def test_namespaced_extensions_compose_without_changing_kernel_semantics():
    """stage2.extension-composition: domains add manifests, not Kernel exceptions."""
    value = fixture_mapping()
    value["kernel"]["extensions"].append(
        {
            "namespace": "org.example.accounting",
            "version": "1.0.0",
            "profile": None,
        }
    )
    assert findings_for(value) == ()

    missing = deepcopy(value)
    missing["kernel"]["extensions"] = [missing["kernel"]["extensions"][1]]
    assert_finding(
        missing,
        code="facilitated.extension-contract",
        quote="org.narrativegame.narrative",
    )


def test_pure_packages_have_no_effectful_imports_or_hidden_registries():
    """stage2.purity: Kernel/profile execution needs no ambient capability."""
    roots = [
        Path(__file__).parents[1] / "src" / "narrative_game" / "kernel",
        Path(__file__).parents[1] / "src" / "narrative_game" / "narrative",
    ]
    forbidden = {
        "asyncio",
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
    for root in roots:
        for path in root.glob("*.py"):
            tree = ast.parse(path.read_text(), filename=str(path))
            imports = {
                alias.name.split(".")[0]
                for node in ast.walk(tree)
                if isinstance(node, (ast.Import, ast.ImportFrom))
                for alias in (node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")])
            }
            assert not imports & forbidden, f"{path} imports ambient capability {imports & forbidden}"
            assert "registry" not in path.read_text().lower()
