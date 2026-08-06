"""Stage 11 acceptance for tutorial-led authorized product experiences."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import socket
import subprocess
import sys

import pytest

from narrative_game.experience import (
    dispatch_session_intent,
    host_projection,
    player_projection,
    render_reference_html,
)
from narrative_game.runtime import AuthorizationContext
from narrative_game.stage11_fixture import run


def read_json(path: Path):
    return json.loads(path.read_bytes())


def test_reference_renderer_depends_only_on_projection_and_canonical_contracts():
    """stage11.headless-boundary: rendering owns no game or authority rules."""
    source = Path(render_reference_html.__code__.co_filename).read_text()
    imported = {
        alias.name
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    assert imported == {
        "Any",
        "ExperienceProjection",
        "annotations",
        "canonical_json",
        "escape",
    }


def test_tutorial_explains_components_through_the_exact_worked_game(tmp_path):
    """stage11.tutorial: first-run guidance names ownership, outputs, and real examples."""
    result = run(tmp_path / "experience")
    tutorial = read_json(result.output_root / "tutorial.json")
    assert [item["component_id"] for item in tutorial["steps"]] == [
        "blueprint",
        "world",
        "cast",
        "evidence",
        "arc",
        "release",
        "delivery",
        "session",
        "measurement",
        "independent-control",
    ]
    assert all(item["owns"] and item["produces"] and item["example_refs"] for item in tutorial["steps"])
    assert tutorial["release_id"] == result.release.release_id
    assert result.summary["tutorial_id"] == tutorial["tutorial_id"]


def test_surfaces_share_exact_identity_without_sharing_one_layout_or_authority(tmp_path):
    """stage11.boundary: maker, host, player, and print are distinct exact projections."""
    result = run(tmp_path / "experience")
    views = {
        name: read_json(result.output_root / f"{name}.json")
        for name in ("maker", "host", "player-avery", "player-blake", "print")
    }
    assert {item["release_id"] for item in views.values()} == {result.release.release_id}
    assert views["host"]["session_id"] == views["player-avery"]["session_id"] == result.session.session_id
    assert views["maker"]["physical_export_id"] == views["host"]["physical_export_id"] == views["print"]["physical_export_id"] == result.physical.export_id
    assert len({item["projection_id"] for item in views.values()}) == 5
    assert {item["surface"] for item in views.values()} == {"maker", "host", "player", "print"}


def test_character_web_view_contains_only_runtime_authorized_material(tmp_path):
    """stage11.authorization: player HTML cannot carry another role or trusted truth."""
    result = run(tmp_path / "experience")
    avery = (result.output_root / "player-avery.html").read_text()
    blake = (result.output_root / "player-blake.html").read_text()
    host = (result.output_root / "host.html").read_text()
    assert "key-register" in avery and "closing-interview" in avery
    assert "camera-log" not in avery
    assert "blake-rowan" not in avery
    assert "cash-receipt" not in blake
    assert "trusted/game.json" not in avery
    assert "camera-log" in host and "cash-receipt" in host


def test_host_and_player_intents_use_session_authority_and_reject_stale_or_foreign_views(tmp_path):
    """stage11.controls: UI intent never bypasses exact Session authority and revision."""
    result = run(tmp_path / "experience")
    host_auth = AuthorizationContext("viewer", "host-viewer")
    avery_auth = AuthorizationContext("actor", "avery-actor", "avery-binding")
    blake_auth = AuthorizationContext("actor", "blake-actor", "blake-binding")
    avery = player_projection(result.release, result.session, avery_auth)
    accepted = dispatch_session_intent(
        result.release,
        result.session,
        avery_auth,
        avery,
        action_id="share-claim",
        payload={"proposition_id": "staff-key-used", "stance": "accepts"},
        command_id="stage11-share",
    )
    assert accepted.receipt.accepted
    with pytest.raises(ValueError, match="stale"):
        dispatch_session_intent(
            result.release,
            accepted.history,
            avery_auth,
            avery,
            action_id="request-hint",
            payload={"request": "What changed?"},
            command_id="stage11-stale",
        )
    with pytest.raises(ValueError, match="another authority"):
        dispatch_session_intent(
            result.release,
            result.session,
            blake_auth,
            avery,
            action_id="request-hint",
            payload={"request": "Use Avery's view"},
            command_id="stage11-foreign",
        )
    host = host_projection(result.release, result.physical, result.session, host_auth)
    assert all(item.authority == "host" for item in host.actions)


def test_reference_pages_are_accessible_intent_emitters_bound_to_exact_exports(tmp_path):
    """stage11.reference-ui: standalone pages are responsive, explicit, and mutation-free."""
    result = run(tmp_path / "experience")
    maker = (result.output_root / "maker.html").read_text()
    printed_html = (result.output_root / "print.html").read_text()
    printed = read_json(result.output_root / "print.json")
    assert '<meta name="viewport"' in maker
    assert "prefers-reduced-motion" in maker
    assert 'aria-live="polite"' in maker
    assert "narrative-game-intent" in maker
    assert "fetch(" not in maker and "http://" not in maker and "https://" not in maker
    assert "Start here" in maker and "Blueprint" in maker and "Independent review and standing" in maker
    assert "Containers and custody" in printed_html and "Packing order" in printed_html
    assert "Preflight ready" in printed_html and "Executed checks" in printed_html
    assert '"containers": [' not in printed_html
    assert printed["release_id"] == result.release.release_id
    assert printed["physical_export_id"] == result.physical.export_id
    assert render_reference_html(player_projection(result.release, result.session, AuthorizationContext("actor", "avery-actor", "avery-binding"))) == (result.output_root / "player-avery.html").read_bytes()


def test_worked_experience_is_offline_and_byte_identical_across_processes(tmp_path, monkeypatch):
    """stage11.determinism: the full tutorial and surface export is offline and reproducible."""
    def blocked(*args, **kwargs):
        raise AssertionError("network is forbidden in reference experience generation")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    local = run(tmp_path / "offline")
    assert local.summary["session_revision"] == 3

    roots = (tmp_path / "process-a", tmp_path / "process-b")
    outputs = []
    for index, root in enumerate(roots):
        environment = dict(os.environ, PYTHONHASHSEED=str(index * 999 + 1))
        subprocess.run(
            [sys.executable, "-m", "narrative_game.stage11_fixture", str(root)],
            check=True,
            capture_output=True,
            env=environment,
        )
        outputs.append(
            {
                path.relative_to(root / "output").as_posix(): path.read_bytes()
                for path in sorted((root / "output").iterdir())
                if path.is_file()
            }
        )
    assert outputs[0] == outputs[1]
