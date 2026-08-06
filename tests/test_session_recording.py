"""Capability tests for exact Release loading and physical-play transcripts."""

from pathlib import Path

import pytest

from narrative_game.compiler import compile_candidate, load_release
from narrative_game.contracts import canonical_json
from narrative_game import record_session_plan
from narrative_game.playtest.session_recording import run
from narrative_game.stage3_fixture import build_micro_candidate


GAME_JSON = Path("fixtures/micro-game/game.json").read_bytes()


def package():
    result = compile_candidate(build_micro_candidate(GAME_JSON))
    assert result.release is not None
    return result.release


def plan():
    return {
        "schema_version": "1.0",
        "session_id": "physical-table-01",
        "mode": "live",
        "bindings": [
            {
                "binding_id": "avery-binding",
                "actor_id": "avery-human",
                "label": "Avery participant",
                "seat_id": "avery",
            },
            {
                "binding_id": "blake-binding",
                "actor_id": "blake-human",
                "label": "Blake participant",
                "seat_id": "blake",
            },
        ],
        "viewers": [{"viewer_id": "host-human", "role": "host"}],
        "commands": [
            {"command_id": "open", "authority": {"kind": "host"}, "action": "open-session", "payload": {}},
            {"command_id": "phase", "authority": {"kind": "host"}, "action": "advance-phase", "payload": {"phase_id": "resolution"}},
            {
                "command_id": "receipt",
                "authority": {"kind": "host"},
                "action": "disclose-resource",
                "payload": {
                    "resource_id": "cash-receipt",
                    "audience_seat_ids": ["avery"],
                    "evidence_grade": "host-witnessed",
                },
            },
            {
                "command_id": "submit",
                "authority": {"kind": "seat", "seat_id": "avery"},
                "action": "submit-resolution",
                "payload": {
                    "hypothesis_id": "inside-job",
                    "proof_path_id": "key-and-payment",
                },
            },
            {
                "command_id": "resolve",
                "authority": {"kind": "host"},
                "action": "record-resolution",
                "payload": {"submission_sequence": "last-resolution-submission"},
            },
        ],
    }


def test_exact_release_loader_round_trips_compiled_archive_and_rejects_corruption():
    """stage11.session-release: a host transcript runs only on verified Release bytes."""
    release = package()
    loaded = load_release(release.bundle_bytes)
    assert loaded == release
    with pytest.raises(ValueError, match="Game Release archive"):
        load_release(release.bundle_bytes[:-12])


def test_host_transcript_materializes_same_resolved_live_history_twice():
    """stage11.session-transcript: physical play has a deterministic Session receipt."""
    release = package()
    first, first_summary = record_session_plan(release.bundle_bytes, plan())
    second, second_summary = record_session_plan(release.bundle_bytes, plan())
    assert first.to_bytes() == second.to_bytes()
    assert first_summary == second_summary
    assert first_summary["status"] == "resolved"
    assert first.mode == "live"
    assert first.ordered_events[-1].event_type == "resolution-recorded"


def test_session_cli_writes_only_after_every_transcript_command_passes(tmp_path):
    """stage11.session-cli: a rejected transcript does not leave partial history."""
    release = package()
    release_path = tmp_path / "game-release.zip"
    plan_path = tmp_path / "session-plan.json"
    output = tmp_path / "session-history.json"
    release_path.write_bytes(release.bundle_bytes)
    invalid = plan()
    invalid["commands"][0] = {
        **invalid["commands"][0],
        "authority": {"kind": "seat", "seat_id": "avery"},
    }
    plan_path.write_bytes(canonical_json(invalid))
    with pytest.raises(ValueError, match="command rejected"):
        run(release_path, plan_path, output)
    assert not output.exists()
    plan_path.write_bytes(canonical_json(plan()))
    summary = run(release_path, plan_path, output)
    assert output.exists()
    assert summary["session_history_ref"] == record_session_plan(
        release.bundle_bytes, plan()
    )[0].content_hash
