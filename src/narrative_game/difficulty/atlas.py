"""Append-only Atlas Workbench and independently published Failure Atlases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from narrative_game.contracts.canonical import digest_json


CLASS_STAGES = ("proposed", "experimental", "promoted")
CLASS_CHANGES = ("add", "clarify", "split", "merge", "deprecate", "retire")


@dataclass(frozen=True)
class FailureClassVersion:
    class_id: str
    version: str
    evidence_stage: str
    definition: str
    inclusions: tuple[str, ...]
    exclusions: tuple[str, ...]
    observable_signatures: tuple[str, ...]
    adjacent_class_distinctions: tuple[str, ...]
    counterexamples: tuple[str, ...]
    detector_or_rubric_ref: str | None
    positive_fixture_refs: tuple[str, ...]
    non_manifesting_control_refs: tuple[str, ...]
    lineage_refs: tuple[str, ...]
    evaluation_axes: tuple[str, ...]
    minimal_reproduction_ref: str | None = None
    lifecycle_state: str = "active"

    def __post_init__(self) -> None:
        if self.evidence_stage not in CLASS_STAGES:
            raise ValueError("Failure Class evidence stage is not recognized")
        if self.lifecycle_state not in {"active", "deprecated", "retired", "superseded"}:
            raise ValueError("Failure Class lifecycle state is not recognized")
        if not self.definition or not self.inclusions or not self.exclusions:
            raise ValueError("Failure Class requires definition, inclusions, and exclusions")

    @property
    def class_version_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "class_id": self.class_id,
            "version": self.version,
            "evidence_stage": self.evidence_stage,
            "definition": self.definition,
            "inclusions": list(self.inclusions),
            "exclusions": list(self.exclusions),
            "observable_signatures": list(self.observable_signatures),
            "adjacent_class_distinctions": list(self.adjacent_class_distinctions),
            "counterexamples": list(self.counterexamples),
            "detector_or_rubric_ref": self.detector_or_rubric_ref,
            "positive_fixture_refs": list(self.positive_fixture_refs),
            "non_manifesting_control_refs": list(self.non_manifesting_control_refs),
            "lineage_refs": list(self.lineage_refs),
            "evaluation_axes": list(self.evaluation_axes),
            "minimal_reproduction_ref": self.minimal_reproduction_ref,
            "lifecycle_state": self.lifecycle_state,
        }


@dataclass(frozen=True)
class WorkbenchEntry:
    entry_id: str
    kind: str
    object_ref: str
    principal: str
    parent_entry_refs: tuple[str, ...]
    receipt_refs: tuple[str, ...]

    @property
    def entry_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "object_ref": self.object_ref,
            "principal": self.principal,
            "parent_entry_refs": list(self.parent_entry_refs),
            "receipt_refs": list(self.receipt_refs),
        }


@dataclass(frozen=True)
class AtlasWorkbench:
    entries: tuple[WorkbenchEntry, ...] = ()
    schema_version: str = "atlas-workbench.1"

    @property
    def workbench_ref(self) -> str:
        return digest_json(self.to_mapping())

    def append(self, entry: WorkbenchEntry) -> "AtlasWorkbench":
        if entry.entry_ref in {item.entry_ref for item in self.entries}:
            raise ValueError("Atlas Workbench entry is already present")
        known = {item.entry_ref for item in self.entries}
        if not set(entry.parent_entry_refs) <= known:
            raise ValueError("Workbench entry names an unknown parent")
        return AtlasWorkbench(self.entries + (entry,))

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entries": [item.to_mapping() for item in self.entries],
        }


@dataclass(frozen=True)
class PublishedFailureAtlas:
    version: str
    parent_atlas_ref: str | None
    class_versions: tuple[FailureClassVersion, ...]
    lifecycle_links: tuple[tuple[str, str, str], ...]
    transition_receipt_ref: str
    schema_version: str = "published-failure-atlas.1"

    def __post_init__(self) -> None:
        refs = [item.class_version_ref for item in self.class_versions]
        if len(refs) != len(set(refs)):
            raise ValueError("Published Atlas class versions must be unique")
        if any(item.evidence_stage != "promoted" for item in self.class_versions):
            raise ValueError("Published Atlas may contain only promoted class versions")

    @property
    def atlas_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "parent_atlas_ref": self.parent_atlas_ref,
            "class_versions": [item.to_mapping() for item in self.class_versions],
            "lifecycle_links": [list(item) for item in self.lifecycle_links],
            "transition_receipt_ref": self.transition_receipt_ref,
        }


@dataclass(frozen=True)
class AtlasRevisionProposal:
    parent_atlas_ref: str
    proposed_version: str
    curator_principal: str
    evidence_contributor_principals: tuple[str, ...]
    change_kind: str
    proposed_class: FailureClassVersion
    supporting_incident_refs: tuple[str, ...]
    refuting_evidence_refs: tuple[str, ...]
    unresolved_evidence_refs: tuple[str, ...]
    migration_links: tuple[tuple[str, str], ...]
    sealed_non_regression_receipt_ref: str | None
    analysis_receipt_refs: tuple[str, ...]
    schema_version: str = "atlas-revision-proposal-record.1"

    def __post_init__(self) -> None:
        if self.change_kind not in CLASS_CHANGES:
            raise ValueError("Atlas class change is not recognized")

    @property
    def proposal_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "parent_atlas_ref": self.parent_atlas_ref,
            "proposed_version": self.proposed_version,
            "curator_principal": self.curator_principal,
            "evidence_contributor_principals": list(self.evidence_contributor_principals),
            "change_kind": self.change_kind,
            "proposed_class": self.proposed_class.to_mapping(),
            "supporting_incident_refs": list(self.supporting_incident_refs),
            "refuting_evidence_refs": list(self.refuting_evidence_refs),
            "unresolved_evidence_refs": list(self.unresolved_evidence_refs),
            "migration_links": [list(item) for item in self.migration_links],
            "sealed_non_regression_receipt_ref": self.sealed_non_regression_receipt_ref,
            "analysis_receipt_refs": list(self.analysis_receipt_refs),
        }


@dataclass(frozen=True)
class AtlasProposalEligibility:
    proposal_ref: str
    eligible: bool
    gate_results: tuple[tuple[str, bool], ...]
    findings: tuple[str, ...]

    @property
    def eligibility_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "proposal_ref": self.proposal_ref,
            "eligible": self.eligible,
            "gate_results": [list(item) for item in self.gate_results],
            "findings": list(self.findings),
        }


def evaluate_atlas_proposal(proposal: AtlasRevisionProposal) -> AtlasProposalEligibility:
    item = proposal.proposed_class
    reproduction = item.minimal_reproduction_ref is not None
    stage_evidence = {
        "proposed": len(proposal.supporting_incident_refs) >= 1,
        "experimental": reproduction or len(set(item.lineage_refs)) >= 2,
        "promoted": reproduction
        or (len(set(item.lineage_refs)) >= 3 and len(set(item.evaluation_axes)) >= 2),
    }[item.evidence_stage]
    gates = {
        "principal-independence": proposal.curator_principal not in proposal.evidence_contributor_principals,
        "stage-evidence": stage_evidence,
        "definition-complete": bool(
            item.definition
            and item.inclusions
            and item.exclusions
            and item.observable_signatures
        ),
        "adjacent-distinctions": bool(item.adjacent_class_distinctions),
        "counterexamples": bool(item.counterexamples),
        "rerunnable-measurement": item.detector_or_rubric_ref is not None,
        "positive-fixture": bool(item.positive_fixture_refs),
        "non-manifesting-control": bool(item.non_manifesting_control_refs),
        "support-refute-unresolved-preserved": bool(proposal.supporting_incident_refs)
        and (bool(proposal.refuting_evidence_refs) or bool(proposal.unresolved_evidence_refs)),
        "sealed-non-regression": proposal.sealed_non_regression_receipt_ref is not None,
        "complete-lineage": bool(proposal.analysis_receipt_refs),
    }
    if item.evidence_stage == "proposed":
        required = {"principal-independence", "stage-evidence", "definition-complete", "complete-lineage"}
    elif item.evidence_stage == "experimental":
        required = {
            "principal-independence",
            "stage-evidence",
            "definition-complete",
            "adjacent-distinctions",
            "counterexamples",
            "rerunnable-measurement",
            "complete-lineage",
        }
    else:
        required = set(gates)
    findings = tuple(f"failed Atlas gate: {name}" for name in sorted(required) if not gates[name])
    return AtlasProposalEligibility(
        proposal.proposal_ref,
        not findings,
        tuple(sorted(gates.items())),
        findings,
    )


@dataclass(frozen=True)
class AtlasReview:
    proposal_ref: str
    eligibility_ref: str
    reviewer_principal: str
    decision: str
    gate_results: tuple[tuple[str, bool], ...]
    disagreements: tuple[str, ...]
    review_receipt_ref: str

    def __post_init__(self) -> None:
        if self.decision not in {"accept", "reject"}:
            raise ValueError("Atlas review decision is not recognized")
        if self.decision == "accept" and not all(value for _, value in self.gate_results):
            raise ValueError("Independent Reviewer cannot waive a failed Atlas gate")

    @property
    def review_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "proposal_ref": self.proposal_ref,
            "eligibility_ref": self.eligibility_ref,
            "reviewer_principal": self.reviewer_principal,
            "decision": self.decision,
            "gate_results": [list(item) for item in self.gate_results],
            "disagreements": list(self.disagreements),
            "review_receipt_ref": self.review_receipt_ref,
        }


def review_atlas_proposal(
    proposal: AtlasRevisionProposal,
    eligibility: AtlasProposalEligibility,
    *,
    reviewer_principal: str,
    accept: bool,
    disagreements: tuple[str, ...],
    review_receipt_ref: str,
) -> AtlasReview:
    if reviewer_principal in {proposal.curator_principal, *proposal.evidence_contributor_principals}:
        raise ValueError("Atlas reviewer cannot review its own contribution")
    if eligibility.proposal_ref != proposal.proposal_ref:
        raise ValueError("Atlas eligibility belongs to another Proposal")
    decision = "accept" if accept and eligibility.eligible else "reject"
    return AtlasReview(
        proposal.proposal_ref,
        eligibility.eligibility_ref,
        reviewer_principal,
        decision,
        eligibility.gate_results,
        disagreements,
        review_receipt_ref,
    )


def publish_atlas_revision(
    parent: PublishedFailureAtlas,
    proposal: AtlasRevisionProposal,
    eligibility: AtlasProposalEligibility,
    review: AtlasReview,
    *,
    transition_receipt_ref: str,
) -> PublishedFailureAtlas:
    if proposal.parent_atlas_ref != parent.atlas_ref:
        raise ValueError("Atlas Proposal parent does not match current Published Atlas")
    if not eligibility.eligible or review.decision != "accept":
        raise ValueError("only an eligible independently accepted Proposal may publish")
    if proposal.proposed_class.evidence_stage != "promoted":
        raise ValueError("only promoted Failure Classes enter the Published Atlas")
    classes = parent.class_versions + (proposal.proposed_class,)
    links = parent.lifecycle_links
    if proposal.change_kind != "add":
        links += tuple((source, proposal.proposed_class.class_version_ref, proposal.change_kind) for source, _ in proposal.migration_links)
    return PublishedFailureAtlas(
        proposal.proposed_version,
        parent.atlas_ref,
        classes,
        links,
        transition_receipt_ref,
    )
