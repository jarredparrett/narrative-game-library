"""Pure Candidate freeze and deterministic Game Release compilation."""

from .compiler import compile_candidate, freeze_candidate, load_release, reference_component_lock
from .model import (
    BundledFile,
    Candidate,
    CompilationFinding,
    CompilationResult,
    FreezeResult,
    GameRelease,
    MaterialInput,
)

__all__ = [
    "BundledFile",
    "Candidate",
    "CompilationFinding",
    "CompilationResult",
    "FreezeResult",
    "GameRelease",
    "MaterialInput",
    "compile_candidate",
    "freeze_candidate",
    "load_release",
    "reference_component_lock",
]
