"""Capability evidence for the standalone Prime Hub package."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

from narrative_game.compiler import load_release


ENV_ROOT = Path(__file__).parents[1] / "environments" / "narrative_game_arena"


def _module():
    path = ENV_ROOT / "narrative_game_arena.py"
    spec = importlib.util.spec_from_file_location("narrative_game_arena", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_prime_hub_package_materializes_its_frozen_release_without_local_paths():
    """prime-rl.hub-package: hosted task materialization is self-contained."""
    module = _module()
    config = module.NarrativeGameArenaTasksetConfig(id="narrative_game_arena")
    tasks = list(module.NarrativeGameArenaTaskset(config))
    assert len(tasks) == 1
    task = tasks[0]
    release = load_release(__import__("base64").b64decode(task.data.release_base64))
    assert task.data.release_id == release.release_id
    assert task.data.episode_seed == 91
    assert task.data.episode_config["max_steps"] == 12
    assert module.__all__ == ["NarrativeGameArenaTaskset", "NarrativeGameEnv"]
