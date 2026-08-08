"""Frozen Analysis Instrument identity and assignment-scoped evidence views."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_json


GLOBAL_PROMPT = (
    "You occupy exactly one named Analysis Authority. Use only the supplied "
    "Evidence View. Return only the named structured output. Every factual claim "
    "must cite supplied evidence. Preserve counterevidence, alternatives, "
    "confidence, omissions, and runtime limitations. Do not infer comparison side, "
    "desired outcome, hidden truth, or prior conclusions. Do not claim transition "
    "authority. Never provide or request private chain-of-thought; provide concise "
    "evidence-backed rationale fields only."
)


AUTHORITY_PROMPTS = {
    "sweep-outcome-progress": (
        "Traverse outcome, milestones, stalls, abandoned work, unsupported terminal "
        "claims, and counterevidence across the complete Episode. Propose expected-"
        "versus-observed gaps only. Do not assign cause or an Atlas class."
    ),
    "sweep-knowledge-support": (
        "Traverse inspection, disclosure, sharing, claim support, corroboration, and "
        "evidence lineage across the complete Episode. Propose gaps only. Do not "
        "judge hidden truth or cause."
    ),
    "sweep-coordination-allocation": (
        "Traverse communication, handoffs, duplication, disagreement, work "
        "allocation, and distinct Seat contributions. Preserve locally plausible "
        "actions and propose system-level gaps without blame."
    ),
    "sweep-host-dependence": (
        "Traverse hints, interventions, synthesis, confession, fallback, recovery "
        "timing, and counterfactual dependence on the host. State observed "
        "dependence without assigning ownership."
    ),
    "sweep-runtime-authorization-evaluator": (
        "Traverse rejected tools, timeouts, malformed output, authorization, "
        "exposure, verification gaps, and evaluator consistency. Separate runtime, "
        "evidence-quality, and reported-outcome gaps without cause claims."
    ),
    "incident-assembler": (
        "Group frozen Signals only when they share one expected milestone, required "
        "transition, terminal claim, or linked obligation and an overlapping window "
        "or factual-graph edge. Preserve exclusions and disagreement. Do not invent, "
        "suppress, classify, or attribute."
    ),
    "semantic-interpreter": (
        "Translate the frozen Incident into precise game-domain meaning: Actors, "
        "Phases, public obligations, observed transitions, missing transitions, and "
        "consequence. State what happened and what remains uncertain. Never state why."
    ),
    "attribution-a": (
        "Produce a multi-label Causal Hypothesis Set across Actor, interaction, Seat, "
        "host, game, runtime, provider, and evaluator layers. For every factor state "
        "its causal role, evidence, counterevidence, alternatives, confidence band, "
        "and one falsifiable counterfactual prediction. Do not assign blame or inspect "
        "another Attribution."
    ),
    "attribution-b": (
        "Produce a multi-label Causal Hypothesis Set across Actor, interaction, Seat, "
        "host, game, runtime, provider, and evaluator layers. For every factor state "
        "its causal role, evidence, counterevidence, alternatives, confidence band, "
        "and one falsifiable counterfactual prediction. Do not assign blame or inspect "
        "another Attribution."
    ),
    "atlas-curator": (
        "Propose an append-only Atlas revision with exact class definitions, "
        "inclusions, exclusions, adjacent distinctions, counterexamples, evidence "
        "stage, detector or rubric, fixtures, migrations, and unresolved evidence. "
        "Do not promote, edit history, or inspect sealed contents."
    ),
    "challenge-designer": (
        "Propose one answer-safe Challenge Case from the supplied promoted Failure "
        "Class and Generation Intent. State the generating mutation, protected "
        "invariants, initial state, legal actions, terminal requirements, oracle, "
        "expected manifestation, matched control, target profile, and admission plan. "
        "Do not certify it."
    ),
    "independent-reviewer": (
        "Return accept or reject for the exact frozen proposal. Evaluate every "
        "declared gate and disagreement against cited evidence and receipts. Do not "
        "edit the proposal, waive a failed gate, infer desired comparison side, or "
        "manufacture missing evidence."
    ),
}


DISCOVERY_ALLOW = (
    "episode_structure",
    "participants_anonymized",
    "phases_and_milestones",
    "verified_actions",
    "authorized_observations",
    "tool_results",
    "messages_and_visibility",
    "state_transitions",
    "timing_observations",
    "terminal_state",
    "derived_outcome_integrity_execution_facts",
    "verification_coverage",
    "assigned_factual_graphs",
    "frozen_lens_patterns",
)

VIEW_CONTRACTS = {
    "discovery": {
        "allow": DISCOVERY_ALLOW,
        "deny": (
            "canonical_world_truth",
            "proof_paths",
            "comparison_side",
            "aggregate_scores",
            "failure_atlas_labels",
            "other_analysis_outputs",
            "provider_or_model_names",
        ),
    },
    "assembly": {
        "allow": ("frozen_discovery_outputs", "sweep_coverage", "targeted_sweep_receipts"),
        "deny": (
            "canonical_episode_evidence",
            "canonical_world_truth",
            "proof_paths",
            "causal_attributions",
            "failure_atlas_labels",
            "comparison_side",
        ),
    },
    "interpretation": {
        "allow": DISCOVERY_ALLOW
        + (
            "frozen_incident",
            "public_role_phase_action_definitions",
            "evidence_authorization_definitions",
            "canonical_meanings_of_observed_transitions",
        ),
        "deny": (
            "canonical_world_truth",
            "proof_paths",
            "comparison_side",
            "failure_atlas_labels",
            "causal_attributions",
        ),
    },
    "attribution": {
        "allow": (
            "frozen_incident",
            "frozen_semantic_interpretation",
            "canonical_episode_evidence",
            "canonical_world_truth",
            "valid_proof_paths",
            "terminal_requirements",
            "role_prompts",
            "tool_contracts",
            "host_policy",
            "runtime_error_receipts",
            "anonymized_policy_occupancy",
        ),
        "deny": (
            "comparison_side",
            "aggregate_scores",
            "failure_atlas_labels",
            "provider_or_model_names",
            "other_attribution_output",
        ),
    },
    "curation": {
        "allow": (
            "reviewed_incident_packages",
            "both_frozen_attributions",
            "attribution_disagreement",
            "supporting_refuting_unresolved_evidence",
            "counterexamples",
            "published_failure_atlas",
            "approved_research_receipts",
            "opaque_sealed_non_regression_receipt",
        ),
        "deny": (
            "sealed_case_contents",
            "sealed_case_results",
            "standing_desired_outcome",
            "transition_authority",
        ),
    },
    "challenge": {
        "allow": (
            "one_promoted_failure_class",
            "deidentified_supporting_evidence",
            "target_difficulty_profile",
            "generation_intent",
            "development_coverage_cells",
            "integrity_constraints",
        ),
        "deny": (
            "sealed_case_contents",
            "sealed_case_results",
            "standing_desired_outcome",
            "self_validation_results",
            "transition_authority",
        ),
    },
    "review": {
        "allow": (
            "frozen_proposal",
            "complete_underlying_evidence",
            "deterministic_verification",
            "independent_attributions_and_disagreement",
            "controls_and_counterfactuals",
            "all_analysis_receipts",
            "principal_conflict_result",
            "opaque_sealed_receipt_when_required",
        ),
        "deny": (
            "comparison_side",
            "desired_release_outcome",
            "proposal_edit_capability",
            "gate_waiver_capability",
            "missing_evidence_fabrication",
        ),
    },
}


OUTPUT_REQUIRED = {
    "discovery-sweep.1": (
        "status",
        "lens",
        "coverage",
        "signals",
        "counterevidence",
        "omissions",
        "continuation_cursor",
        "analysis_receipt_ref",
    ),
    "incident-assembly.1": (
        "status",
        "included_signal_refs",
        "excluded_signal_refs",
        "grouping_obligation",
        "graph_connection",
        "disagreement",
        "targeted_sweep_request",
        "analysis_receipt_ref",
    ),
    "semantic-interpretation.1": (
        "status",
        "incident_ref",
        "domain_statement",
        "actors",
        "phases",
        "public_obligations",
        "observed_transitions",
        "missing_or_uncertain_transitions",
        "consequence",
        "span_refs",
        "analysis_receipt_ref",
    ),
    "causal-hypothesis-set.1": (
        "status",
        "incident_ref",
        "factors",
        "interactions",
        "alternatives",
        "overall_uncertainty",
        "analysis_receipt_ref",
    ),
    "atlas-revision-proposal.1": (
        "status",
        "parent_atlas_ref",
        "class_changes",
        "evidence_refs",
        "detector_or_rubric",
        "positive_fixtures",
        "non_manifesting_controls",
        "migration",
        "unresolved_evidence",
        "analysis_receipt_ref",
    ),
    "challenge-case-proposal.1": (
        "status",
        "failure_class_ref",
        "generation_intent_ref",
        "mutation",
        "protected_invariants",
        "initial_state",
        "legal_actions",
        "terminal_requirements",
        "oracle",
        "expected_manifestation",
        "non_manifesting_control",
        "target_profile",
        "admission_plan",
        "analysis_receipt_ref",
    ),
    "independent-review.1": (
        "status",
        "proposal_ref",
        "gate_results",
        "disagreements",
        "missing_evidence",
        "decision",
        "reasons",
        "analysis_receipt_ref",
    ),
}


@dataclass(frozen=True)
class ModelSlot:
    provider: str
    endpoint: str
    requested_model: str
    reasoning_effort: str
    max_output_tokens: int

    def to_mapping(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "endpoint": self.endpoint,
            "requested_model": self.requested_model,
            "reasoning_effort": self.reasoning_effort,
            "max_output_tokens": self.max_output_tokens,
            "sampling": {"temperature": "omitted", "top_p": "omitted", "seed": "omitted"},
        }


@dataclass(frozen=True)
class AssignmentDefinition:
    authority: str
    assignment: str
    model_slot: str
    view: str
    output_schema: str

    def to_mapping(self) -> dict[str, str]:
        return {
            "authority": self.authority,
            "assignment": self.assignment,
            "model_slot": self.model_slot,
            "view": self.view,
            "output_schema": self.output_schema,
        }


ASSIGNMENTS = (
    AssignmentDefinition("incident-discoverer", "sweep-outcome-progress", "diverse", "discovery", "discovery-sweep.1"),
    AssignmentDefinition("incident-discoverer", "sweep-knowledge-support", "diverse", "discovery", "discovery-sweep.1"),
    AssignmentDefinition("incident-discoverer", "sweep-coordination-allocation", "diverse", "discovery", "discovery-sweep.1"),
    AssignmentDefinition("incident-discoverer", "sweep-host-dependence", "diverse", "discovery", "discovery-sweep.1"),
    AssignmentDefinition("incident-discoverer", "sweep-runtime-authorization-evaluator", "diverse", "discovery", "discovery-sweep.1"),
    AssignmentDefinition("incident-discoverer", "incident-assembler", "deep", "assembly", "incident-assembly.1"),
    AssignmentDefinition("semantic-interpreter", "semantic-interpreter", "deep", "interpretation", "semantic-interpretation.1"),
    AssignmentDefinition("attribution-analyst", "attribution-a", "deep", "attribution", "causal-hypothesis-set.1"),
    AssignmentDefinition("attribution-analyst", "attribution-b", "diverse", "attribution", "causal-hypothesis-set.1"),
    AssignmentDefinition("atlas-curator", "atlas-curator", "deep", "curation", "atlas-revision-proposal.1"),
    AssignmentDefinition("challenge-designer", "challenge-designer", "deep", "challenge", "challenge-case-proposal.1"),
    AssignmentDefinition("independent-reviewer", "independent-reviewer", "deep", "review", "independent-review.1"),
)


PRINCIPAL_CONFLICTS = (
    ("episode-actor", "incident-discoverer"),
    ("incident-discoverer", "semantic-interpreter"),
    ("incident-discoverer", "attribution-a"),
    ("incident-discoverer", "attribution-b"),
    ("semantic-interpreter", "attribution-a"),
    ("semantic-interpreter", "attribution-b"),
    ("attribution-a", "attribution-b"),
    ("atlas-evidence-contributor", "atlas-curator"),
    ("challenge-designer", "challenge-validator"),
    ("proposal-contributor", "independent-reviewer"),
)


@dataclass(frozen=True)
class AnalysisInstrumentDefinition:
    published_atlas_ref: str
    normative_contract_ref: str
    version: str = "1.0.0"
    schema_version: str = "analysis-instrument.1"

    def __post_init__(self) -> None:
        for label, value in {
            "published Atlas": self.published_atlas_ref,
            "normative contract": self.normative_contract_ref,
        }.items():
            if not value.startswith("sha256:") or len(value) != 71:
                raise ValueError(f"{label} must be content-addressed")

    @property
    def assignments(self) -> tuple[AssignmentDefinition, ...]:
        return ASSIGNMENTS

    @property
    def definition_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "version": self.version,
            "normative_contract_ref": self.normative_contract_ref,
            "published_atlas_ref": self.published_atlas_ref,
            "models": {
                "deep": ModelSlot("openai", "responses", "gpt-5.6-sol", "high", 12000).to_mapping(),
                "diverse": ModelSlot("openai", "responses", "gpt-5.6-terra", "high", 10000).to_mapping(),
            },
            "global_prompt": GLOBAL_PROMPT,
            "authority_prompts": dict(sorted(AUTHORITY_PROMPTS.items())),
            "view_contracts": {
                key: {"allow": list(value["allow"]), "deny": list(value["deny"])}
                for key, value in sorted(VIEW_CONTRACTS.items())
            },
            "tool_contract": {
                "evidence.get": "read one admitted object",
                "evidence.expand": "read a bounded admitted span neighborhood",
                "analysis.submit": "freeze one structured output attempt",
            },
            "output_required": {
                key: list(value) for key, value in sorted(OUTPUT_REQUIRED.items())
            },
            "retry_policy": {
                "transport_retries": 2,
                "schema_repairs": 1,
                "semantic_retry": "forbidden",
                "best_of": "forbidden",
                "exhausted": "incomplete",
            },
            "principal_conflicts": [list(value) for value in PRINCIPAL_CONFLICTS],
            "assignments": [item.to_mapping() for item in ASSIGNMENTS],
            "eligibility_fixture_ids": [
                "reference-lineage",
                "discovery-truth-leak",
                "reviewer-contributor-collision",
                "attribution-cross-exposure",
                "partial-sweep-no-finding",
                "semantic-best-of-retry",
                "incomplete-receipt",
                "reviewer-proposal-mutation",
                "episode-actor-self-analysis",
            ],
        }


@dataclass(frozen=True)
class AssignmentApplication:
    assignment: str
    principal: str
    context_id: str
    requested_model: str
    resolved_model: str
    provider: str = "openai"
    endpoint: str = "responses"

    def to_mapping(self) -> dict[str, str]:
        return {
            "assignment": self.assignment,
            "principal": self.principal,
            "context_id": self.context_id,
            "provider": self.provider,
            "endpoint": self.endpoint,
            "requested_model": self.requested_model,
            "resolved_model": self.resolved_model,
        }


@dataclass(frozen=True)
class AnalysisInstrumentApplication:
    definition_ref: str
    episode_package_ref: str
    assignments: tuple[AssignmentApplication, ...]
    schema_version: str = "analysis-instrument-application.1"

    def __post_init__(self) -> None:
        expected = tuple(item.assignment for item in ASSIGNMENTS)
        observed = tuple(item.assignment for item in self.assignments)
        if observed != expected:
            raise ValueError("Instrument Application must occupy all twelve assignments in roster order")
        if len({item.principal for item in self.assignments}) != len(self.assignments):
            raise ValueError("Instrument Application principals must be distinct")
        if len({item.context_id for item in self.assignments}) != len(self.assignments):
            raise ValueError("Instrument Application contexts must be isolated")

    @property
    def application_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "definition_ref": self.definition_ref,
            "episode_package_ref": self.episode_package_ref,
            "assignments": [item.to_mapping() for item in self.assignments],
        }


@dataclass(frozen=True)
class EvidenceGrant:
    category: str
    object_ref: str
    span_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.object_ref.startswith("sha256:") or len(self.object_ref) != 71:
            raise ValueError("Evidence grant must name a content-addressed object")

    def to_mapping(self) -> dict[str, Any]:
        return {"category": self.category, "object_ref": self.object_ref, "span_ids": list(self.span_ids)}


@dataclass(frozen=True)
class AnalysisEvidenceView:
    definition_ref: str
    application_ref: str
    assignment: str
    view_contract: str
    grants: tuple[EvidenceGrant, ...]
    denied_categories: tuple[str, ...]
    schema_version: str = "analysis-evidence-view.1"

    def __post_init__(self) -> None:
        contract = VIEW_CONTRACTS[self.view_contract]
        allowed = set(contract["allow"])
        categories = [item.category for item in self.grants]
        leaks = sorted(set(categories) - allowed)
        if leaks:
            raise ValueError("Evidence View exposes unallowed categories: " + ", ".join(leaks))
        denied = set(contract["deny"])
        overlap = sorted(set(categories) & denied)
        if overlap:
            raise ValueError("Evidence View exposes denied categories: " + ", ".join(overlap))
        if tuple(sorted(set(categories))) != tuple(sorted(categories)):
            raise ValueError("Evidence View categories must be unique")

    @property
    def view_ref(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "definition_ref": self.definition_ref,
            "application_ref": self.application_ref,
            "assignment": self.assignment,
            "view_contract": self.view_contract,
            "grants": [item.to_mapping() for item in sorted(self.grants, key=lambda item: item.category)],
            "denied_categories": list(self.denied_categories),
        }


def analysis_instrument_v1(*, normative_contract_ref: str, published_atlas_ref: str) -> AnalysisInstrumentDefinition:
    return AnalysisInstrumentDefinition(published_atlas_ref, normative_contract_ref)


def apply_instrument(
    definition: AnalysisInstrumentDefinition,
    *,
    episode_package_ref: str,
    resolved_models: Mapping[str, str] | None = None,
    principal_prefix: str = "analysis",
) -> AnalysisInstrumentApplication:
    models = definition.to_mapping()["models"]
    resolved = dict(resolved_models or {})
    applications = []
    for index, item in enumerate(definition.assignments, 1):
        requested = str(models[item.model_slot]["requested_model"])
        applications.append(
            AssignmentApplication(
                item.assignment,
                f"{principal_prefix}:{item.assignment}",
                f"{principal_prefix}:context:{index:02d}",
                requested,
                resolved.get(item.assignment, requested),
            )
        )
    return AnalysisInstrumentApplication(
        definition.definition_ref, episode_package_ref, tuple(applications)
    )


def compose_prompt(
    definition: AnalysisInstrumentDefinition,
    view: AnalysisEvidenceView,
    *,
    upstream_receipt_refs: tuple[str, ...] = (),
) -> bytes:
    assignment = next(item for item in definition.assignments if item.assignment == view.assignment)
    material = {
        "global": GLOBAL_PROMPT,
        "authority": AUTHORITY_PROMPTS[assignment.assignment],
        "evidence_view": view.to_mapping(),
        "tools": definition.to_mapping()["tool_contract"],
        "output_schema": {
            "schema": assignment.output_schema,
            "required": list(OUTPUT_REQUIRED[assignment.output_schema]),
            "unknown_fields": "rejected",
        },
        "upstream_receipt_refs": list(upstream_receipt_refs),
    }
    return canonical_json(material)


def build_analysis_view(
    definition: AnalysisInstrumentDefinition,
    application: AnalysisInstrumentApplication,
    *,
    assignment: str,
    available: Mapping[str, EvidenceGrant],
) -> AnalysisEvidenceView:
    """Build one least-authority view from explicitly available evidence."""
    if application.definition_ref != definition.definition_ref:
        raise ValueError("Instrument Application does not match Definition")
    assignment_definition = next(
        (item for item in definition.assignments if item.assignment == assignment), None
    )
    if assignment_definition is None:
        raise ValueError(f"unknown Analysis assignment: {assignment}")
    contract = VIEW_CONTRACTS[assignment_definition.view]
    allowed = set(contract["allow"])
    grants = tuple(
        available[category]
        for category in sorted(allowed & set(available))
    )
    return AnalysisEvidenceView(
        definition.definition_ref,
        application.application_ref,
        assignment,
        assignment_definition.view,
        grants,
        tuple(contract["deny"]),
    )


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))
