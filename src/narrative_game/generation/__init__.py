"""Initial-generation domain contracts."""

from .model import (
    GENERATION_SCHEMA_VERSION,
    ArtifactPlan,
    ArtifactSpecification,
    CreativeBrief,
    GenerationBudget,
    GenerationPlan,
    ModelRoleAssignment,
    StopPolicy,
)
from .artifacts import (
    ArtifactSuiteImporter,
    ArtifactSuiteMaterialization,
    ArtifactSuiteMaterializer,
)

__all__ = [
    "GENERATION_SCHEMA_VERSION",
    "ArtifactPlan",
    "ArtifactSpecification",
    "ArtifactSuiteImporter",
    "CreativeBrief",
    "GenerationBudget",
    "GenerationPlan",
    "ModelRoleAssignment",
    "StopPolicy",
    "ArtifactSuiteMaterialization",
    "ArtifactSuiteMaterializer",
    "GenerationCoordinator",
    "GenerationDrivers",
    "GenerationStopped",
    "InvalidGenerationOutput",
    "GenerationStatus",
    "derive_generation_status",
    "write_generation_status",
]


def __getattr__(name: str):
    """Load orchestration lazily so pure generation contracts remain dependency-light."""
    if name in {
        "GenerationCoordinator",
        "GenerationDrivers",
        "GenerationStopped",
        "InvalidGenerationOutput",
    }:
        from . import coordinator

        return getattr(coordinator, name)
    if name in {
        "GenerationStatus",
        "derive_generation_status",
        "write_generation_status",
    }:
        from . import status

        return getattr(status, name)
    raise AttributeError(name)
