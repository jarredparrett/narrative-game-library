"""Deterministic narrative game building with agentic, inspectable lineage."""

from .contracts.artifacts import ArtifactRequest, ArtifactResult
from .adapters import (
    VerismillArtifactForge,
    VerismillArtifactSuiteImporter,
    VerismillArtifactSuiteMaterializer,
)
from .authoring import parse_game_definition
from .blueprint import (
    ArcBeat,
    AuthoringOperation,
    BlueprintProposal,
    DisplayedClaim,
    GameBlueprint,
    RichTextMaterial,
    apply_blueprint_proposal,
    bind_artifact_specification,
    derive_artifact_truth_binding,
    validate_blueprint,
)
from .compiler import compile_candidate, freeze_candidate, load_release
from .experiment import (
    EfficiencyController,
    Experiment,
    ExperimentSpine,
    GameProfileAdapter,
)
from .generation import (
    ArtifactPlan,
    ArtifactSpecification,
    ArtifactSuiteImporter,
    ArtifactSuiteMaterialization,
    ArtifactSuiteMaterializer,
    CreativeBrief,
    GenerationBudget,
    GenerationCoordinator,
    GenerationDrivers,
    GenerationPlan,
    GenerationStatus,
    GenerationStopped,
    InvalidGenerationOutput,
    ModelRoleAssignment,
    StopPolicy,
    derive_generation_status,
    write_generation_status,
)
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
from .narrative import CharacterProgram, GameDefinition, validate_facilitated_investigation
from .physical import PhysicalExport, PhysicalExportProfile, export_physical, render_dossier_pdf
from .playtest import (
    EvidenceComparison,
    PlaytestProtocol,
    PlaytestRun,
)
from .playtest.ingestion import record_playtest_bundle
from .playtest.model_baseline import measure_model_baseline
from .playtest.program import PlaytestProgram
from .playtest.review import finalize_review
from .profiles import FacilitatedInvestigationAuthoringAdapter
from .release import (
    PublicReleasePolicy,
    ReleaseAttestation,
    ReleaseEvidence,
    ReleaseQualificationReport,
    qualify_public_release,
)
from .runtime import apply_command, create_session, replay, seat_snapshot
from .playtest.session_recording import record_session_plan
from .workspace import Workspace

__all__ = [
    "ArtifactRequest",
    "ArtifactResult",
    "ArtifactPlan",
    "ArtifactSpecification",
    "ArtifactSuiteImporter",
    "ArtifactSuiteMaterialization",
    "ArtifactSuiteMaterializer",
    "VerismillArtifactForge",
    "VerismillArtifactSuiteImporter",
    "VerismillArtifactSuiteMaterializer",
    "ArcBeat",
    "AuthoringOperation",
    "BlueprintProposal",
    "DisplayedClaim",
    "Experiment",
    "ExperimentSpine",
    "EfficiencyController",
    "EvidenceComparison",
    "ExperienceProjection",
    "GameDefinition",
    "CharacterProgram",
    "GameBlueprint",
    "GameProfileAdapter",
    "CreativeBrief",
    "GenerationBudget",
    "GenerationCoordinator",
    "GenerationDrivers",
    "GenerationPlan",
    "GenerationStatus",
    "GenerationStopped",
    "InvalidGenerationOutput",
    "ModelRoleAssignment",
    "PhysicalExport",
    "PhysicalExportProfile",
    "PlaytestProgram",
    "PlaytestProtocol",
    "PlaytestRun",
    "PublicReleasePolicy",
    "ReleaseAttestation",
    "ReleaseEvidence",
    "ReleaseQualificationReport",
    "TutorialProjection",
    "RichTextMaterial",
    "StopPolicy",
    "FacilitatedInvestigationAuthoringAdapter",
    "Workspace",
    "compile_candidate",
    "dispatch_session_intent",
    "derive_generation_status",
    "derive_artifact_truth_binding",
    "apply_command",
    "apply_blueprint_proposal",
    "bind_artifact_specification",
    "create_session",
    "freeze_candidate",
    "finalize_review",
    "host_projection",
    "load_release",
    "maker_projection",
    "measure_model_baseline",
    "player_projection",
    "print_projection",
    "qualify_public_release",
    "export_physical",
    "render_dossier_pdf",
    "parse_game_definition",
    "replay",
    "render_reference_html",
    "record_playtest_bundle",
    "record_session_plan",
    "seat_snapshot",
    "validate_facilitated_investigation",
    "validate_blueprint",
    "write_generation_status",
]

__version__ = "0.29.0"
