"""Deterministic narrative game building with human-governed lineage."""

from .contracts.artifacts import ArtifactRequest, ArtifactResult
from .authoring import parse_game_definition
from .compiler import compile_candidate, freeze_candidate
from .narrative import GameDefinition, validate_facilitated_investigation
from .runtime import apply_command, create_session, replay, seat_snapshot
from .workspace import Workspace

__all__ = [
    "ArtifactRequest",
    "ArtifactResult",
    "GameDefinition",
    "Workspace",
    "compile_candidate",
    "apply_command",
    "create_session",
    "freeze_candidate",
    "parse_game_definition",
    "replay",
    "seat_snapshot",
    "validate_facilitated_investigation",
]

__version__ = "0.4.0"
