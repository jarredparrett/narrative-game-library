"""Stage 0 acceptance tests for the public Artifact Forge boundary."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import socket
import subprocess
import sys

from narrative_game.stage0_fixture import run


def test_public_artifact_forge_is_seeded_verified_and_offline(tmp_path, monkeypatch):
    """stage0.public-forge: exact verified bytes cross the public facade offline."""

    def no_network(*args, **kwargs):
        raise AssertionError("the artifact forge attempted network access")

    monkeypatch.setattr(socket, "create_connection", no_network)
    result = run(tmp_path / "experiment")
    assert result["artifact_hash"].startswith("sha256:")
    assert result["manifest_hash"].startswith("sha256:")
    assert result["experiment_verified"] is True
    assert result["measurement_status"] == "development_only"
    assert result["bytes"] > 10_000


def test_stage0_fixture_is_byte_identical_across_processes(tmp_path):
    """stage0.cross-process: the same pin, seed, and versions hash identically."""
    summaries = []
    for number in (1, 2):
        completed = subprocess.run(
            [sys.executable, "-m", "narrative_game.stage0_fixture", str(tmp_path / f"e{number}")],
            check=True,
            capture_output=True,
            text=True,
        )
        summaries.append(json.loads(completed.stdout))
    assert summaries[0] == summaries[1]


def test_verismill_adapter_has_no_private_or_mattermill_imports():
    """stage0.import-boundary: game code imports no private upstream module."""
    source_path = (
        Path(__file__).parents[1]
        / "src"
        / "narrative_game"
        / "adapters"
        / "verismill.py"
    )
    tree = ast.parse(source_path.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(name == "mattermill" or name.startswith("mattermill.") for name in imported)
    assert not any(name.startswith("verismill.") for name in imported)
    assert ".store" not in source_path.read_text()
