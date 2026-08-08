"""Capability tests for the first agentic-difficulty implementation slice."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys

from narrative_game.compiler import compile_candidate
from narrative_game.contracts.canonical import canonical_json
from narrative_game.difficulty import (
    DIFFICULTY_CONTRACT_CATALOG,
    SemanticFixtureExpectation,
    build_discovery_view,
    build_episode_evidence_package,
    expectation_is_satisfied,
)
from narrative_game.simulation import (
    EpisodeConfig,
    MultiAgentEpisode,
    PolicyIdentity,
    PolicyLineup,
    SeatAssignment,
    ToolCall,
    evaluate_episode,
    verify_episode,
)
from narrative_game.stage3_fixture import build_micro_candidate, materialized_game_mapping


ROOT = Path(__file__).parents[1]
GAME = ROOT / "fixtures" / "micro-game" / "game.json"


def _release(*, fixture: str):
    mapping = materialized_game_mapping(GAME.read_bytes())
    if fixture == "missing-rescue":
        mapping["narrative"]["direction"]["premise"] += (
            " The cave emergency gate has trapped Quill, whose release and safe "
            "exit must be recorded before the investigation resolves."
        )
        mapping["narrative"]["direction"]["experience_targets"].append(
            "Record operation of the emergency release and Quill's resulting safe exit."
        )
        mapping["narrative"]["objectives"].append(
            {
                "id": "rescue-quill",
                "description": (
                    "Operate the emergency release and record Quill's safe exit."
                ),
                "activation_phase_id": "opening",
            }
        )
        blake = next(
            item
            for item in mapping["narrative"]["characters"]
            if item["seat_id"] == "blake"
        )
        blake["objective_ids"].append("rescue-quill")
    result = compile_candidate(
        build_micro_candidate(GAME.read_bytes(), game_override=mapping)
    )
    assert result.release is not None
    return result.release


def _lineup() -> PolicyLineup:
    return PolicyLineup(
        (
            SeatAssignment(
                "avery",
                PolicyIdentity(
                    "difficulty-policy-avery",
                    "fixture",
                    "model-a",
                    "difficulty-agent-a",
                    "difficulty-context-a",
                ),
            ),
            SeatAssignment(
                "blake",
                PolicyIdentity(
                    "difficulty-policy-blake",
                    "fixture",
                    "model-b",
                    "difficulty-agent-b",
                    "difficulty-context-b",
                ),
            ),
        ),
        PolicyIdentity(
            "difficulty-policy-host",
            "fixture",
            "host-model",
            "difficulty-host-agent",
            "difficulty-host-context",
        ),
    )


def _passing_semantic_episode(*, fixture: str):
    release = _release(fixture=fixture)
    episode = MultiAgentEpisode.reset(
        release,
        episode_seed=91,
        lineup=_lineup(),
        config=EpisodeConfig(max_steps=20),
    )
    credentials = episode.credentials
    host = episode.active_actor_id
    assert host is not None and host.startswith("host:")
    episode.step(credentials[host], ToolCall(f"{fixture}-open", "open_session", {}))

    first = episode.active_actor_id
    assert first is not None and first.startswith("seat:avery:")
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-inspect-register",
            "inspect_evidence",
            {"resource_id": "key-register"},
        ),
    )
    second = episode.active_actor_id
    assert second is not None and second.startswith("seat:blake:")
    episode.step(
        credentials[second],
        ToolCall(
            f"{fixture}-inspect-interview",
            "inspect_evidence",
            {"resource_id": "closing-interview"},
        ),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall(f"{fixture}-phase", "advance_phase", {"phase_id": "resolution"}),
    )

    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-request-receipt",
            "request_evidence",
            {"resource_id": "cash-receipt"},
        ),
    )
    assert episode.active_actor_id == second
    episode.step(
        credentials[second],
        ToolCall(
            f"{fixture}-request-camera",
            "request_evidence",
            {"resource_id": "camera-log"},
        ),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall(
            f"{fixture}-disclose-receipt",
            "disclose_resource",
            {
                "resource_id": "cash-receipt",
                "audience_seat_ids": ["avery"],
                "evidence_grade": "runtime-enforced",
            },
        ),
    )
    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-inspect-receipt",
            "inspect_evidence",
            {"resource_id": "cash-receipt"},
        ),
    )
    assert episode.active_actor_id == second
    if fixture == "missing-rescue":
        episode.step(
            credentials[second],
            ToolCall(
                f"{fixture}-narrate-rescue",
                "say",
                {
                    "text": (
                        "I pulled the emergency release and escorted Quill outside; "
                        "the rescue is complete."
                    )
                },
            ),
        )
    else:
        episode.step(
            credentials[second],
            ToolCall(
                f"{fixture}-share-interview",
                "share_evidence",
                {
                    "resource_id": "closing-interview",
                    "finding": "The clerk returned after the office closed.",
                },
            ),
        )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall(
            f"{fixture}-disclose-camera",
            "disclose_resource",
            {
                "resource_id": "camera-log",
                "audience_seat_ids": ["blake"],
                "evidence_grade": "runtime-enforced",
            },
        ),
    )
    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-share-receipt",
            "share_evidence",
            {
                "resource_id": "cash-receipt",
                "finding": "The payment was undeclared.",
            },
        ),
    )
    assert episode.active_actor_id == second
    episode.step(
        credentials[second],
        ToolCall(
            f"{fixture}-inspect-camera",
            "inspect_evidence",
            {"resource_id": "camera-log"},
        ),
    )
    assert episode.active_actor_id == host
    episode.step(
        credentials[host],
        ToolCall(
            f"{fixture}-host-summary",
            "broadcast",
            {"text": "Submit only from records the team actually acquired."},
        ),
    )
    assert episode.active_actor_id == first
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-resolution",
            "submit_resolution",
            {
                "hypothesis_id": "inside-job",
                "evidence_resource_ids": ["key-register", "cash-receipt"],
                "explanation": "The key and payment records independently agree.",
            },
        ),
    )
    assert episode.done
    return release, episode.archive()


def test_difficulty_contract_catalog_rejects_unknown_or_changed_normative_versions():
    """difficulty.d0.contract-lock: exact accepted contract bytes are mandatory."""
    materials = {
        item.source_path: (ROOT / item.source_path).read_bytes()
        for item in DIFFICULTY_CONTRACT_CATALOG.entries
    }
    assert DIFFICULTY_CONTRACT_CATALOG.verify_materials(materials) == ()

    changed = dict(materials)
    changed["docs/analysis-instrument-v1.md"] += b"\nchanged without a new contract\n"
    findings = DIFFICULTY_CONTRACT_CATALOG.verify_materials(changed)
    assert len(findings) == 1
    assert findings[0].startswith(
        "normative source changed: docs/analysis-instrument-v1.md"
    )

    incomplete = dict(materials)
    incomplete.pop("docs/operator-evidence-monitor.md")
    incomplete["docs/unapproved-contract.md"] = b"not accepted"
    assert DIFFICULTY_CONTRACT_CATALOG.verify_materials(incomplete) == (
        "missing normative source: docs/operator-evidence-monitor.md",
        "unexpected normative source: docs/unapproved-contract.md",
    )

    script = (
        "from narrative_game.difficulty import DIFFICULTY_CONTRACT_CATALOG as c; "
        "print(c.catalog_id)"
    )
    first = subprocess.check_output([sys.executable, "-c", script], cwd=ROOT, text=True)
    second = subprocess.check_output([sys.executable, "-c", script], cwd=ROOT, text=True)
    assert first == second == DIFFICULTY_CONTRACT_CATALOG.catalog_id + "\n"

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
    difficulty_root = ROOT / "src" / "narrative_game" / "difficulty"
    for path in difficulty_root.glob("*.py"):
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


def test_first_semantic_fixtures_replay_with_answer_safe_span_addressable_evidence():
    """difficulty.d0.semantic-fixtures: falsifiers are replay-valid and answer-safe."""
    rescue_release, rescue_archive = _passing_semantic_episode(fixture="missing-rescue")
    handoff_release, handoff_archive = _passing_semantic_episode(fixture="failed-handoff")
    assert verify_episode(rescue_release, rescue_archive) == ()
    assert verify_episode(handoff_release, handoff_archive) == ()
    assert evaluate_episode(rescue_release, rescue_archive).aggregate == 1.0
    assert evaluate_episode(handoff_release, handoff_archive).aggregate == 1.0

    rescue_package = build_episode_evidence_package(rescue_release, rescue_archive)
    handoff_package = build_episode_evidence_package(handoff_release, handoff_archive)
    assert rescue_package.verification.status == "verified"
    assert handoff_package.verification.status == "verified"
    assert rescue_package.package_id != handoff_package.package_id
    assert rescue_package.to_bytes() == build_episode_evidence_package(
        rescue_release, rescue_archive
    ).to_bytes()

    required_kinds = {
        "archive-metadata",
        "arena-event",
        "session-event",
        "session-receipt",
        "trajectory-step",
    }
    assert required_kinds <= {item.source_kind for item in rescue_package.spans}
    assert len({item.span_id for item in rescue_package.spans}) == len(
        rescue_package.spans
    )

    rescue_expectation = SemanticFixtureExpectation(
        "rescue.quill-safe-exit",
        "session-event",
        "character-state-updated",
        {"payload": {"key": "quill-safe-exit", "value": True}},
    )
    handoff_expectation = SemanticFixtureExpectation(
        "coordination.camera-log-handoff",
        "arena-event",
        "evidence-shared",
        {"payload": {"result": {"content": {"resource_id": "camera-log"}}}},
    )
    assert not expectation_is_satisfied(rescue_package, rescue_expectation)
    assert not expectation_is_satisfied(handoff_package, handoff_expectation)

    rescue_view = build_discovery_view(rescue_package)
    handoff_view = build_discovery_view(handoff_package)
    assert rescue_view.episode_package_id == rescue_package.package_id
    assert handoff_view.episode_package_id == handoff_package.package_id
    assert rescue_view.manifest_id != handoff_view.manifest_id
    projected = canonical_json(
        [item.content for item in (*rescue_view.spans, *handoff_view.spans)]
    ).decode("utf-8")
    projected_values = json.loads(projected)

    def keys(value):
        if isinstance(value, dict):
            return set(value) | {
                key
                for child in value.values()
                for key in keys(child)
            }
        if isinstance(value, list):
            return {key for child in value for key in keys(child)}
        return set()

    for denied in rescue_view.denied_fields:
        assert denied not in keys(projected_values)
    assert "model-a" not in projected
    assert "difficulty-agent-a" not in projected
    assert "seat:avery:difficulty-policy-avery" not in projected
    assert "participant:seat-001" in projected
    assert rescue_expectation.expectation_id not in rescue_view.to_bytes().decode("utf-8")
    assert handoff_expectation.expectation_id not in handoff_view.to_bytes().decode("utf-8")
    assert "I pulled the emergency release" in projected
    assert any(item.redacted_paths for item in rescue_view.spans)
