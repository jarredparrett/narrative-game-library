"""Deterministic narrative game building with human-governed lineage."""

from .contracts.artifacts import ArtifactRequest, ArtifactResult
from .authoring import parse_game_definition
from .narrative import GameDefinition, validate_facilitated_investigation
from .workspace import Workspace

__all__ = [
    "ArtifactRequest",
    "ArtifactResult",
    "GameDefinition",
    "Workspace",
    "parse_game_definition",
    "validate_facilitated_investigation",
]

__version__ = "0.2.0"
