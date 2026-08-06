"""Committed worked examples that ship with the library."""

from importlib.resources import files
import json

from narrative_game.blueprint import GameBlueprint
from .winter_observatory_characters import (
    winter_observatory_game,
    winter_observatory_parent_game,
)


def vanished_ledger_blueprint() -> GameBlueprint:
    """Load the shipped rich-text Stage 9 Game Blueprint."""
    source = files("narrative_game").joinpath(
        "examples/vanished-ledger/blueprint.json"
    )
    return GameBlueprint.from_mapping(json.loads(source.read_bytes()))


__all__ = [
    "vanished_ledger_blueprint",
    "winter_observatory_game",
    "winter_observatory_parent_game",
]
