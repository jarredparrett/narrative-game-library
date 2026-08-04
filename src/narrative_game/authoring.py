"""Pure parsing boundary for human-readable Game Definitions."""

from __future__ import annotations

import json

from .narrative import GameDefinition


def parse_game_definition(value: str | bytes) -> GameDefinition:
    """Parse canonical JSON without filesystem access or implicit repair."""
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Game Definition must be a JSON object")
    return GameDefinition.from_mapping(parsed)
