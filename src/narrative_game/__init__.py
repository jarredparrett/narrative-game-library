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
from .experience import (
    ExperienceProjection,
    TutorialProjection,
    dispatch_session_intent,
    host_projection,
    maker_projection,
    player_projection,
    print_projection,
    render_reference_html,
)
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
    "ExperienceProjection",
    "GameDefinition",
    "GameBlueprint",
    "GameProfileAdapter",
    "PhysicalExport",
    "PhysicalExportProfile",
    "PlaytestProgram",
    "PlaytestProtocol",
    "PlaytestRun",
    "TutorialProjection",
    "RichTextMaterial",
    "FacilitatedInvestigationAuthoringAdapter",
    "Workspace",
    "compile_candidate",
    "dispatch_session_intent",
    "apply_command",
    "apply_blueprint_proposal",
    "create_session",
    "freeze_candidate",
    "host_projection",
    "maker_projection",
    "player_projection",
    "print_projection",
    "export_physical",
    "parse_game_definition",
    "replay",
    "render_reference_html",
    "seat_snapshot",
    "validate_facilitated_investigation",
    "validate_blueprint",
]

__version__ = "0.11.0"
