"""Deterministic narrative game building with human-governed lineage."""

from .contracts.artifacts import ArtifactRequest, ArtifactResult
from .authoring import parse_game_definition
from .blueprint import (
    ArcBeat,
    AuthoringOperation,
    BlueprintProposal,
    DisplayedClaim,
    GameBlueprint,
    RichTextMaterial,
    apply_blueprint_proposal,
    validate_blueprint,
)
from .compiler import compile_candidate, freeze_candidate
from .experiment import Experiment, GameProfileAdapter
from .narrative import GameDefinition, validate_facilitated_investigation
from .physical import PhysicalExport, PhysicalExportProfile, export_physical
from .playtest import EvidenceComparison, PlaytestProtocol, PlaytestRun
from .playtest.program import PlaytestProgram
from .profiles import FacilitatedInvestigationAuthoringAdapter
from .runtime import apply_command, create_session, replay, seat_snapshot
from .workspace import Workspace

__all__ = [
    "ArtifactRequest",
    "ArtifactResult",
    "ArcBeat",
    "AuthoringOperation",
    "BlueprintProposal",
    "DisplayedClaim",
    "Experiment",
    "EvidenceComparison",
    "GameDefinition",
    "GameBlueprint",
    "GameProfileAdapter",
    "PhysicalExport",
    "PhysicalExportProfile",
    "PlaytestProgram",
    "PlaytestProtocol",
    "PlaytestRun",
    "RichTextMaterial",
    "FacilitatedInvestigationAuthoringAdapter",
    "Workspace",
    "compile_candidate",
    "apply_command",
    "apply_blueprint_proposal",
    "create_session",
    "freeze_candidate",
    "export_physical",
    "parse_game_definition",
    "replay",
    "seat_snapshot",
    "validate_facilitated_investigation",
    "validate_blueprint",
]

__version__ = "0.10.0"
