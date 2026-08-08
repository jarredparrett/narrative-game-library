"""Deterministic semantic falsifier Episodes for live Analysis qualification."""

from __future__ import annotations

from copy import deepcopy

from narrative_game.compiler import compile_candidate
from narrative_game.simulation import (
    EpisodeArchive,
    EpisodeConfig,
    MultiAgentEpisode,
    PolicyIdentity,
    PolicyLineup,
    SeatAssignment,
    ToolCall,
)
from narrative_game.stage3_fixture import build_micro_candidate, materialized_game_mapping

from .contracts import EpisodeEvidencePackage, SemanticFixtureExpectation
from .derivations import build_episode_evidence_package


SEMANTIC_FALSIFIERS = ("missing-rescue", "failed-handoff")


def _release(game_json: bytes, fixture: str):
    mapping = deepcopy(materialized_game_mapping(game_json))
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
                "description": "Operate the emergency release and record Quill's safe exit.",
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
        build_micro_candidate(game_json, game_override=mapping)
    )
    if result.release is None:
        raise ValueError("semantic falsifier release did not compile")
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


def build_semantic_falsifier_episode(
    game_json: bytes, *, fixture: str
) -> tuple[object, EpisodeArchive, EpisodeEvidencePackage, SemanticFixtureExpectation]:
    """Return one replay-valid passing Episode with one hidden missing obligation."""
    if fixture not in SEMANTIC_FALSIFIERS:
        raise ValueError(f"unknown semantic falsifier: {fixture}")
    release = _release(game_json, fixture)
    episode = MultiAgentEpisode.reset(
        release,
        episode_seed=91,
        lineup=_lineup(),
        config=EpisodeConfig(max_steps=20),
    )
    credentials = episode.credentials
    host = episode.active_actor_id
    assert host is not None
    episode.step(credentials[host], ToolCall(f"{fixture}-open", "open_session", {}))

    first = episode.active_actor_id
    assert first is not None
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-inspect-register",
            "inspect_evidence",
            {"resource_id": "key-register"},
        ),
    )
    second = episode.active_actor_id
    assert second is not None
    episode.step(
        credentials[second],
        ToolCall(
            f"{fixture}-inspect-interview",
            "inspect_evidence",
            {"resource_id": "closing-interview"},
        ),
    )
    episode.step(
        credentials[host],
        ToolCall(f"{fixture}-phase", "advance_phase", {"phase_id": "resolution"}),
    )
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-request-receipt",
            "request_evidence",
            {"resource_id": "cash-receipt"},
        ),
    )
    episode.step(
        credentials[second],
        ToolCall(
            f"{fixture}-request-camera",
            "request_evidence",
            {"resource_id": "camera-log"},
        ),
    )
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
    episode.step(
        credentials[first],
        ToolCall(
            f"{fixture}-inspect-receipt",
            "inspect_evidence",
            {"resource_id": "cash-receipt"},
        ),
    )
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
    episode.step(
        credentials[second],
        ToolCall(
            f"{fixture}-inspect-camera",
            "inspect_evidence",
            {"resource_id": "camera-log"},
        ),
    )
    episode.step(
        credentials[host],
        ToolCall(
            f"{fixture}-host-summary",
            "broadcast",
            {"text": "Submit only from records the team actually acquired."},
        ),
    )
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
    archive = episode.archive()
    package = build_episode_evidence_package(release, archive)
    expectation = (
        SemanticFixtureExpectation(
            "rescue.quill-safe-exit",
            "session-event",
            "character-state-updated",
            {"payload": {"key": "quill-safe-exit", "value": True}},
        )
        if fixture == "missing-rescue"
        else SemanticFixtureExpectation(
            "coordination.camera-log-handoff",
            "arena-event",
            "evidence-shared",
            {"payload": {"result": {"content": {"resource_id": "camera-log"}}}},
        )
    )
    return release, archive, package, expectation
