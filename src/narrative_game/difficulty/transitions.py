"""Deterministic eligibility transitions for Analysis Instrument v1."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json

from .instrument import AnalysisInstrumentApplication, AnalysisInstrumentDefinition


@dataclass(frozen=True)
class EligibilityFinding:
    code: str
    assignment: str | None
    message: str

    def to_mapping(self) -> dict[str, Any]:
        return {"code": self.code, "assignment": self.assignment, "message": self.message}


@dataclass(frozen=True)
class EligibilityResult:
    definition_ref: str
    application_ref: str
    lineage_ref: str
    eligible: bool
    findings: tuple[EligibilityFinding, ...]
    schema_version: str = "analysis-eligibility-result.1"

    @property
    def result_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "definition_ref": self.definition_ref,
            "application_ref": self.application_ref,
            "lineage_ref": self.lineage_ref,
            "eligible": self.eligible,
            "findings": [item.to_mapping() for item in self.findings],
        }


def analysis_lineage_ref(value: Mapping[str, Any]) -> str:
    return digest_json(value)


def evaluate_analysis_eligibility(
    definition: AnalysisInstrumentDefinition,
    application: AnalysisInstrumentApplication,
    lineage: Mapping[str, Any],
) -> EligibilityResult:
    """Check mechanical admissibility without declaring semantic conclusions true."""
    findings: list[EligibilityFinding] = []
    assignments = lineage.get("assignments", {})
    expected = {item.assignment: item for item in definition.assignments}
    if application.definition_ref != definition.definition_ref:
        findings.append(EligibilityFinding("instrument.mismatch", None, "Application names another Definition"))

    application_assignments = {item.assignment: item for item in application.assignments}
    models = definition.to_mapping()["models"]
    for name, spec in expected.items():
        applied = application_assignments[name]
        requested = models[spec.model_slot]["requested_model"]
        if applied.requested_model != requested:
            findings.append(
                EligibilityFinding(
                    "application.requested-model-drift",
                    name,
                    f"Application requests {applied.requested_model}; Definition pins {requested}",
                )
            )
        if applied.provider != models[spec.model_slot]["provider"] or applied.endpoint != models[spec.model_slot]["endpoint"]:
            findings.append(
                EligibilityFinding(
                    "application.endpoint-drift",
                    name,
                    "Application provider or endpoint differs from Definition",
                )
            )

    for name, spec in expected.items():
        state = assignments.get(name)
        if not isinstance(state, Mapping):
            findings.append(EligibilityFinding("assignment.missing", name, "required assignment is absent"))
            continue
        if state.get("view_ref") is None:
            findings.append(EligibilityFinding("view.missing", name, "Evidence View receipt is absent"))
        leaks = tuple(state.get("denied_exposures", ()))
        if leaks:
            findings.append(
                EligibilityFinding("view.denied-exposure", name, "denied evidence was exposed: " + ", ".join(sorted(leaks)))
            )
        if not state.get("receipt_complete", False):
            findings.append(EligibilityFinding("receipt.incomplete", name, "Analysis Receipt is incomplete"))
        attempts = tuple(state.get("attempts", ()))
        transport = sum(item.get("kind") == "transport-retry" for item in attempts)
        repairs = sum(item.get("kind") == "schema-repair" for item in attempts)
        if any(not item.get("receipt_ref") for item in attempts):
            findings.append(EligibilityFinding("attempt.unreceipted", name, "an attempt lacks its receipt"))
        forbidden = sorted(
            {str(item.get("kind")) for item in attempts}
            - {"initial", "transport-retry", "schema-repair"}
        )
        if forbidden:
            findings.append(EligibilityFinding("attempt.forbidden", name, "forbidden retry: " + ", ".join(forbidden)))
        if transport > 2:
            findings.append(EligibilityFinding("attempt.transport-exhausted", name, "transport retry limit exceeded"))
        if repairs > 1:
            findings.append(EligibilityFinding("attempt.schema-exhausted", name, "schema repair limit exceeded"))
        if name.startswith("sweep-") and state.get("status") == "partial" and (
            lineage.get("no_finding_claim") or lineage.get("corroboration_claim")
        ):
            findings.append(
                EligibilityFinding("discovery.partial-claim", name, "partial Sweep cannot support no-finding or corroboration")
            )

    actor_principals = set(lineage.get("episode_actor_principals", ()))
    for name, state in assignments.items():
        if not isinstance(state, Mapping):
            continue
        if state.get("principal") in actor_principals:
            findings.append(EligibilityFinding("principal.episode-actor", name, "Episode Actor analyzes its own Episode"))

    principals: dict[str, str] = {}
    for name, state in assignments.items():
        if not isinstance(state, Mapping) or not state.get("principal"):
            continue
        principal = str(state["principal"])
        if principal in principals:
            findings.append(
                EligibilityFinding("principal.conflict", name, f"principal also occupies {principals[principal]}")
            )
        else:
            principals[principal] = name

    if lineage.get("attribution_cross_exposure"):
        findings.append(
            EligibilityFinding("attribution.cross-exposure", None, "Attribution outputs crossed before both froze")
        )
    reviewer = assignments.get("independent-reviewer", {})
    if isinstance(reviewer, Mapping) and reviewer.get("mutated_proposal"):
        findings.append(
            EligibilityFinding("reviewer.proposal-mutation", "independent-reviewer", "Reviewer mutated the frozen proposal")
        )
    if isinstance(reviewer, Mapping) and reviewer.get("waived_gate"):
        findings.append(
            EligibilityFinding("reviewer.gate-waiver", "independent-reviewer", "Reviewer waived a failed gate")
        )

    ordered = tuple(sorted(findings, key=lambda item: (item.code, item.assignment or "", item.message)))
    material = json.loads(canonical_json(lineage))
    return EligibilityResult(
        definition.definition_ref,
        application.application_ref,
        analysis_lineage_ref(material),
        not ordered,
        ordered,
    )
