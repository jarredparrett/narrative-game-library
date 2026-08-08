"""Pure contracts and derivations for agentic difficulty evidence."""

from .contracts import (
    DIFFICULTY_CONTRACT_CATALOG,
    CanonicalEvidenceSpan,
    EpisodeEvidencePackage,
    EvidenceViewManifest,
    EvidenceViewSpan,
    NormativeContract,
    NormativeContractCatalog,
    SemanticFixtureExpectation,
    VerificationStatus,
)
from .derivations import (
    build_discovery_view,
    build_episode_evidence_package,
    expectation_is_satisfied,
)

__all__ = [
    "DIFFICULTY_CONTRACT_CATALOG",
    "CanonicalEvidenceSpan",
    "EpisodeEvidencePackage",
    "EvidenceViewManifest",
    "EvidenceViewSpan",
    "NormativeContract",
    "NormativeContractCatalog",
    "SemanticFixtureExpectation",
    "VerificationStatus",
    "build_discovery_view",
    "build_episode_evidence_package",
    "expectation_is_satisfied",
]
