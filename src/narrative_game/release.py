"""Deterministic public-release qualification over exact persisted evidence."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from narrative_game.contracts import canonical_json, digest_bytes


_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:a[0-9]+|b[0-9]+|rc[0-9]+)?$")


@dataclass(frozen=True)
class ReleaseGate:
    code: str
    stage: int
    owner: str
    requirement: str

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)


PUBLIC_RELEASE_GATES = (
    ReleaseGate("stage8.portable-experiment", 8, "experiment", "portable Experiment verifies and binds the exact reference package"),
    ReleaseGate("stage9.reusable-authoring", 9, "authoring", "reusable Game Blueprint and profile-adapter proof is published"),
    ReleaseGate("stage10.agentic-standing", 10, "agentic-measurement", "reference Candidate has exact-version machine-qualified standing from two independent blind evaluations"),
    ReleaseGate("stage10.independent-agentic-verification", 10, "agentic-review", "standing reviewer is an agent independent of builders and blind judges"),
    ReleaseGate("stage11.creator-player-print", 11, "experience", "maker, host, player, and print projections share one Release and Session lineage"),
    ReleaseGate("stage12.tagged-upstreams", 12, "distribution", "Verismill and Mattermill use immutable release versions rather than repository pins"),
    ReleaseGate("stage12.compatibility", 12, "public-api", "stable contract epoch and compatibility promise are published"),
    ReleaseGate("stage12.support-matrix", 12, "verification", "every supported Python version has an exact passing test receipt"),
    ReleaseGate("stage12.package-artifacts", 12, "distribution", "sdist and wheel have exact content references"),
    ReleaseGate("stage12.documentation", 12, "documentation", "quickstart, tutorial, extension, release, and limitations documents are exact"),
    ReleaseGate("stage12.known-limitations", 12, "publisher", "known limitations are disclosed rather than converted into standing claims"),
    ReleaseGate("stage12.release-attestation", 12, "release-review", "an independent release agent attests this policy, version, standing, and exact package refs"),
)


@dataclass(frozen=True)
class PublicReleasePolicy:
    name: str = "narrative-game-public-release"
    version: str = "2.0.0"
    stable_contract_epoch: str = "1"
    supported_python_versions: tuple[str, ...] = ("3.11", "3.13")
    required_upstreams: tuple[str, ...] = ("verismill", "mattermill")
    required_package_artifacts: tuple[str, ...] = ("sdist", "wheel")
    required_documents: tuple[str, ...] = (
        "quickstart", "tutorial", "extension-guide", "release-policy", "known-limitations",
    )
    gates: tuple[ReleaseGate, ...] = PUBLIC_RELEASE_GATES

    @property
    def policy_id(self) -> str:
        return "release-policy:" + digest_bytes(canonical_json(self.to_mapping())).split(":", 1)[1]

    def to_mapping(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "stable_contract_epoch": self.stable_contract_epoch,
            "supported_python_versions": list(self.supported_python_versions),
            "required_upstreams": list(self.required_upstreams),
            "required_package_artifacts": list(self.required_package_artifacts),
            "required_documents": list(self.required_documents),
            "gates": [item.to_mapping() for item in self.gates],
        }


@dataclass(frozen=True)
class ReleaseAttestation:
    policy_id: str
    library_version: str
    reference_candidate_id: str
    standing_attestation_id: str
    reviewer_authority_id: str
    model_receipt_id: str
    package_artifact_refs: Mapping[str, str]
    response_ref: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "package_artifact_refs", dict(sorted(self.package_artifact_refs.items())))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReleaseAttestation":
        return cls(
            str(value["policy_id"]), str(value["library_version"]),
            str(value["reference_candidate_id"]),
            str(value["standing_attestation_id"]),
            str(value["reviewer_authority_id"]),
            str(value["model_receipt_id"]),
            {str(key): str(item) for key, item in value["package_artifact_refs"].items()},
            str(value["response_ref"]),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "policy_id": self.policy_id,
            "library_version": self.library_version,
            "reference_candidate_id": self.reference_candidate_id,
            "standing_attestation_id": self.standing_attestation_id,
            "reviewer_authority_id": self.reviewer_authority_id,
            "model_receipt_id": self.model_receipt_id,
            "package_artifact_refs": dict(self.package_artifact_refs),
            "response_ref": self.response_ref,
        }


@dataclass(frozen=True)
class ReleaseEvidence:
    library_version: str
    contract_epoch: str
    reference_candidate_id: str
    reference_release_id: str
    authoring_proof_ref: str
    experience_proof_ref: str
    upstream_versions: Mapping[str, str]
    test_receipts: Mapping[str, str]
    package_artifact_refs: Mapping[str, str]
    documentation_refs: Mapping[str, str]
    known_limitations: tuple[str, ...]
    compatibility_ref: str
    release_attestation: ReleaseAttestation | None = None

    def __post_init__(self) -> None:
        for name in (
            "upstream_versions", "test_receipts", "package_artifact_refs", "documentation_refs"
        ):
            object.__setattr__(self, name, dict(sorted(getattr(self, name).items())))
        object.__setattr__(self, "known_limitations", tuple(self.known_limitations))

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ReleaseEvidence":
        attestation = value.get("release_attestation")
        return cls(
            str(value["library_version"]), str(value["contract_epoch"]),
            str(value["reference_candidate_id"]), str(value["reference_release_id"]),
            str(value["authoring_proof_ref"]), str(value["experience_proof_ref"]),
            {str(key): str(item) for key, item in value["upstream_versions"].items()},
            {str(key): str(item) for key, item in value["test_receipts"].items()},
            {str(key): str(item) for key, item in value["package_artifact_refs"].items()},
            {str(key): str(item) for key, item in value["documentation_refs"].items()},
            tuple(str(item) for item in value["known_limitations"]),
            str(value["compatibility_ref"]),
            ReleaseAttestation.from_mapping(attestation) if attestation is not None else None,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "library_version": self.library_version,
            "contract_epoch": self.contract_epoch,
            "reference_candidate_id": self.reference_candidate_id,
            "reference_release_id": self.reference_release_id,
            "authoring_proof_ref": self.authoring_proof_ref,
            "experience_proof_ref": self.experience_proof_ref,
            "upstream_versions": dict(self.upstream_versions),
            "test_receipts": dict(self.test_receipts),
            "package_artifact_refs": dict(self.package_artifact_refs),
            "documentation_refs": dict(self.documentation_refs),
            "known_limitations": list(self.known_limitations),
            "compatibility_ref": self.compatibility_ref,
            "release_attestation": (
                self.release_attestation.to_mapping() if self.release_attestation else None
            ),
        }


@dataclass(frozen=True)
class GateResult:
    code: str
    stage: int
    owner: str
    passed: bool
    evidence_refs: tuple[str, ...]
    explanation: str
    remediation: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "code": self.code, "stage": self.stage, "owner": self.owner,
            "passed": self.passed, "evidence_refs": list(self.evidence_refs),
            "explanation": self.explanation, "remediation": self.remediation,
        }


@dataclass(frozen=True)
class ReleaseQualificationReport:
    policy_id: str
    library_version: str
    reference_candidate_id: str
    status: str
    gates: tuple[GateResult, ...]

    @property
    def report_id(self) -> str:
        return "release-qualification:" + digest_bytes(canonical_json(self.material())).split(":", 1)[1]

    def material(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "policy_id": self.policy_id,
            "library_version": self.library_version,
            "reference_candidate_id": self.reference_candidate_id,
            "status": self.status,
            "gates": [item.to_mapping() for item in self.gates],
        }

    def to_mapping(self) -> dict[str, Any]:
        return {"report_id": self.report_id, **self.material()}


def _refs_valid(
    values: Mapping[str, str],
    required: tuple[str, ...],
    available_refs: set[str],
) -> bool:
    return (
        set(values) == set(required)
        and all(_HASH.fullmatch(item) for item in values.values())
        and set(values.values()) <= available_refs
    )


def qualify_public_release(
    experiment: Any,
    evidence: ReleaseEvidence,
    *,
    policy: PublicReleasePolicy = PublicReleasePolicy(),
    evidence_objects: Mapping[str, bytes],
) -> ReleaseQualificationReport:
    """Evaluate one library version without creating or upgrading any standing."""
    available_refs = {
        ref for ref, value in evidence_objects.items()
        if _HASH.fullmatch(ref) and digest_bytes(value) == ref
    }
    verification = experiment.verify()
    snapshot = experiment.ledger.snapshot()
    bindings = [
        item for item in snapshot["trial_bindings"]
        if item.candidate_id == evidence.reference_candidate_id
        and item.release_id == evidence.reference_release_id
    ]
    standings = [
        item for item in snapshot["standings"]
        if item.candidate_id == evidence.reference_candidate_id
        and item.level == "machine_qualified"
    ]
    standing = standings[-1] if standings else None
    authorities = {item.authority_id: item for item in snapshot["authorities"]}
    evaluations = {item.evaluation_id: item for item in snapshot["evaluations"]}
    model_receipts = {item.receipt_id: item for item in snapshot["model_receipts"]}
    linked_evaluations = tuple(
        evaluations[item]
        for item in (standing.evaluation_ids if standing else ())
        if item in evaluations
    )
    judge_ids = {
        authority_id
        for evaluation in linked_evaluations
        for authority_id in evaluation.judge_authority_ids
    }
    judge_principals = {
        authorities[item].principal for item in judge_ids if item in authorities
    }
    builder_principals = {
        authorities[item.builder_authority_id].principal
        for item in snapshot.get("proposals", ())
        if item.builder_authority_id in authorities
    }
    reviewer = authorities.get(standing.reviewer_authority_id) if standing else None
    attestation = evidence.release_attestation
    release_reviewer = (
        authorities.get(attestation.reviewer_authority_id) if attestation else None
    )
    release_receipt = (
        model_receipts.get(attestation.model_receipt_id) if attestation else None
    )

    def result(code: str, passed: bool, refs: tuple[str, ...], explanation: str, remediation: str) -> GateResult:
        gate = next(item for item in policy.gates if item.code == code)
        return GateResult(code, gate.stage, gate.owner, passed, refs, explanation, remediation)

    exact_binding = bindings[-1] if bindings else None
    portable_ok = bool(verification.get("ok")) and exact_binding is not None
    authoring_ok = evidence.authoring_proof_ref in available_refs
    standing_ok = (
        standing is not None
        and len(standing.evaluation_ids) >= 2
        and len(linked_evaluations) == len(standing.evaluation_ids)
        and {"model-blind-panel", "independent-agentic-review"}
        <= set(standing.evidence_kinds)
        and all(item.mode == "blind" and item.outcome == "pass" for item in linked_evaluations)
        and len({item.instrument_id for item in linked_evaluations}) == 1
        and len(judge_principals) >= 2
    )
    independent_ok = (
        standing_ok and reviewer is not None and reviewer.kind == "agent"
        and reviewer.role == "reviewer" and reviewer.authority_id not in judge_ids
        and reviewer.principal not in judge_principals
        and reviewer.principal not in builder_principals
    )
    experience_ok = evidence.experience_proof_ref in available_refs
    upstream_ok = (
        set(evidence.upstream_versions) == set(policy.required_upstreams)
        and all(_VERSION.fullmatch(item) for item in evidence.upstream_versions.values())
    )
    compatibility_ok = (
        evidence.contract_epoch == policy.stable_contract_epoch
        and evidence.compatibility_ref in available_refs
    )
    support_ok = _refs_valid(
        evidence.test_receipts, policy.supported_python_versions, available_refs
    )
    packages_ok = _refs_valid(
        evidence.package_artifact_refs, policy.required_package_artifacts, available_refs
    )
    docs_ok = _refs_valid(
        evidence.documentation_refs, policy.required_documents, available_refs
    )
    limitations_ok = bool(evidence.known_limitations) and all(
        item.strip() for item in evidence.known_limitations
    )
    release_attestation_ok = (
        attestation is not None and release_reviewer is not None
        and release_reviewer.kind == "agent" and release_reviewer.role == "release-reviewer"
        and release_receipt is not None
        and release_receipt.authority_id == release_reviewer.authority_id
        and release_receipt.role == "release-reviewer"
        and release_receipt.parsed_output_ref == attestation.response_ref
        and release_reviewer.principal not in judge_principals
        and release_reviewer.principal not in builder_principals
        and (reviewer is None or release_reviewer.principal != reviewer.principal)
        and attestation.policy_id == policy.policy_id
        and attestation.library_version == evidence.library_version
        and attestation.reference_candidate_id == evidence.reference_candidate_id
        and standing is not None
        and attestation.standing_attestation_id == standing.attestation_id
        and dict(attestation.package_artifact_refs) == dict(evidence.package_artifact_refs)
        and attestation.response_ref in available_refs
    )
    gate_results = (
        result("stage8.portable-experiment", portable_ok, tuple(item for item in (getattr(exact_binding, "binding_id", ""),) if item), "portable lineage and exact package verify" if portable_ok else "portable lineage or exact package binding is missing", "verify the Experiment and bind the exact reference Candidate, Release, Physical Export, and Blind Trial"),
        result("stage9.reusable-authoring", authoring_ok, (evidence.authoring_proof_ref,) if authoring_ok else (), "reusable authoring proof is exact" if authoring_ok else "authoring proof is missing", "publish a content-addressed Game Blueprint and profile-adapter example"),
        result("stage10.agentic-standing", standing_ok, (standing.attestation_id,) if standing else (), "two passing blind evaluations support exact machine-qualified standing" if standing_ok else "reference Candidate lacks independently corroborated agentic standing", "run two independent blind evaluations and record machine-qualified Standing with exact model receipts"),
        result("stage10.independent-agentic-verification", independent_ok, (standing.attestation_id,) if independent_ok and standing else (), "standing was independently reviewed by an agent outside the blind panels" if independent_ok else "independent agentic standing review is missing", "have a separate review agent attest the standing without participating as builder or blind judge"),
        result("stage11.creator-player-print", experience_ok, (evidence.experience_proof_ref,) if experience_ok else (), "experience-boundary proof is exact" if experience_ok else "experience-boundary proof is missing", "publish one exact maker/host/player/print lineage proof"),
        result("stage12.tagged-upstreams", upstream_ok, tuple(evidence.upstream_versions.values()) if upstream_ok else (), "upstreams are immutable release versions" if upstream_ok else "one or more upstreams still use a repository pin or invalid version", "publish Verismill and Mattermill releases and depend on their versions"),
        result("stage12.compatibility", compatibility_ok, (evidence.compatibility_ref,) if compatibility_ok else (), "stable compatibility epoch is documented" if compatibility_ok else "stable contract epoch or compatibility evidence is missing", "declare contract epoch 1 and publish the supported public-API compatibility policy"),
        result("stage12.support-matrix", support_ok, tuple(evidence.test_receipts.values()) if support_ok else (), "supported interpreter receipts are complete" if support_ok else "supported interpreter receipts are incomplete", "record exact passing receipts for every supported Python version"),
        result("stage12.package-artifacts", packages_ok, tuple(evidence.package_artifact_refs.values()) if packages_ok else (), "sdist and wheel are content-addressed" if packages_ok else "sdist or wheel evidence is incomplete", "build and hash both required distribution artifacts"),
        result("stage12.documentation", docs_ok, tuple(evidence.documentation_refs.values()) if docs_ok else (), "required public documentation is exact" if docs_ok else "required public documentation is incomplete", "publish and hash the quickstart, tutorial, extension guide, release policy, and known limitations"),
        result("stage12.known-limitations", limitations_ok, (), "known limitations are disclosed" if limitations_ok else "known limitations are not disclosed", "publish the current limitations even when the list is short"),
        result("stage12.release-attestation", release_attestation_ok, (attestation.response_ref,) if release_attestation_ok and attestation else (), "independent release agent attested the exact version" if release_attestation_ok else "exact independent release attestation is missing", "record a distinct release-review agent receipt over this policy, version, standing, and package refs"),
    )
    status = "qualified" if all(item.passed for item in gate_results) else "not_qualified"
    return ReleaseQualificationReport(
        policy.policy_id, evidence.library_version,
        evidence.reference_candidate_id, status, gate_results,
    )
