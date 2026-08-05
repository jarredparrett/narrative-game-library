"""Committed worked examples that ship with the library."""

from importlib.resources import files
import json

from narrative_game.blueprint import GameBlueprint


def vanished_ledger_blueprint() -> GameBlueprint:
    """Load the shipped rich-text Stage 9 Game Blueprint."""
    source = files("narrative_game").joinpath(
        "examples/vanished-ledger/blueprint.json"
    )
    return GameBlueprint.from_mapping(json.loads(source.read_bytes()))


__all__ = ["vanished_ledger_blueprint"]
