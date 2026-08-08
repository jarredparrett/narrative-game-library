"""Run the two real-agent semantic falsifiers through Analysis Instrument v1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from narrative_game.adapters import CodexCLIAnalysisDriver
from narrative_game.contracts.canonical import canonical_json, digest_json
from narrative_game.difficulty import (
    ASSIGNMENTS,
    DIFFICULTY_CONTRACT_CATALOG,
    SEMANTIC_FALSIFIERS,
    VIEW_CONTRACTS,
    EvidenceGrant,
    FailureEvidenceSummary,
    analysis_instrument_v1,
    apply_instrument,
    build_semantic_falsifier_episode,
    derive_discovery_materials,
    expectation_is_satisfied,
    route_failure,
)
from narrative_game.experiment import run_analysis_lineage
from narrative_game.simulation import evaluate_episode, verify_episode
from narrative_game.workspace import Workspace


_COORDINATOR_CATEGORIES = {
    "all_analysis_receipts",
    "attribution_disagreement",
    "both_frozen_attributions",
    "frozen_discovery_outputs",
    "frozen_incident",
    "frozen_proposal",
    "frozen_semantic_interpretation",
    "reviewed_incident_packages",
    "sweep_coverage",
}


def _analysis_contract_ref() -> str:
    return next(
        item.content_ref
        for item in DIFFICULTY_CONTRACT_CATALOG.entries
        if item.contract_id == "difficulty.analysis-instrument"
    )


def _live_materials(release, package, expectation):
    grants, objects = derive_discovery_materials(package)
    grants = dict(grants)
    objects = dict(objects)
    trusted_game = json.loads(release.file("trusted/game.json").data)
    release_core = dict(release.manifest)
    release_core.pop("release_id")
    if digest_json(release_core) != release.release_id:
        raise ValueError("Game Release identity is unstable")
    objects[release.release_id] = release_core
    package_span_ids = tuple(item.span_id for item in package.spans)

    canonical_ref = package.package_id
    objects[canonical_ref] = package.to_mapping()
    grants["canonical_episode_evidence"] = EvidenceGrant(
        "canonical_episode_evidence", canonical_ref, package_span_ids
    )

    categories = {
        category
        for contract in VIEW_CONTRACTS.values()
        for category in contract["allow"]
    } - _COORDINATOR_CATEGORIES
    truth_categories = {
        "canonical_world_truth",
        "valid_proof_paths",
        "terminal_requirements",
        "role_prompts",
        "tool_contracts",
        "host_policy",
        "public_role_phase_action_definitions",
        "evidence_authorization_definitions",
        "canonical_meanings_of_observed_transitions",
        "complete_underlying_evidence",
    }
    promoted_id = (
        "semantic.required-state-transition"
        if expectation.expectation_id.startswith("rescue.")
        else "coordination.uncompleted-handoff"
    )
    for category in sorted(categories - set(grants)):
        content: Any
        if category in truth_categories:
            content = {
                "trusted_game": trusted_game,
                "semantic_requirement": expectation.to_mapping(),
            }
        elif category in {"one_promoted_failure_class", "published_failure_atlas"}:
            content = {
                "atlas_version": "qualification-seed.1",
                "failure_class_id": promoted_id,
                "stage": "promoted",
                "definition": (
                    "A required observable transition or evidence handoff is absent even "
                    "though the terminal outcome and integrity gates pass."
                ),
            }
        elif category == "generation_intent":
            content = {
                "profile": "facilitated-investigation",
                "intent": "Create a matched challenge that requires observable completion.",
            }
        else:
            content = {
                "episode_package_ref": package.package_id,
                "category": category,
                "status": "qualification-input",
                "note": "No additional evidence beyond the named verified Episode is asserted.",
            }
        value = {
            "schema_version": "live-analysis-material.1",
            "category": category,
            "content": content,
        }
        object_ref = digest_json(value)
        objects[object_ref] = value
        grants[category] = EvidenceGrant(category, object_ref)
    return grants, objects


def _live_result_report(workspace: Workspace, result) -> Mapping[str, Any]:
    assignment_outputs: dict[str, str] = {}
    assignment_output_statuses: dict[str, str] = {}
    attempts: dict[str, list[Mapping[str, Any]]] = {}
    usage = {
        "provider_calls": 0,
        "schema_repairs": 0,
        "transport_retries": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }
    for name, assignment in sorted(result.assignment_results.items()):
        if assignment.structured_output_ref is not None:
            assignment_outputs[name] = assignment.structured_output_ref
            structured = workspace.store.read_json(assignment.structured_output_ref)[
                "value"
            ]
            assignment_output_statuses[name] = str(structured.get("status"))
        rows = []
        for receipt_ref in assignment.attempt_receipt_refs:
            receipt = workspace.store.read_json(receipt_ref)["value"]
            attempt_usage = dict(receipt.get("usage", {}))
            row = {
                "attempt": receipt["attempt"],
                "attempt_kind": receipt["attempt_kind"],
                "runtime_status": receipt["runtime_status"],
                "model": receipt["resolved_model"],
                "provider_response_id": receipt["provider_response_id"],
                "usage": attempt_usage,
                "receipt_ref": receipt_ref,
            }
            rows.append(row)
            usage["provider_calls"] += 1
            usage["schema_repairs"] += receipt["attempt_kind"] == "schema-repair"
            usage["transport_retries"] += (
                receipt["attempt_kind"] == "transport-retry"
            )
            for key in ("input_tokens", "output_tokens", "total_tokens"):
                usage[key] += int(attempt_usage.get(key, 0))
        attempts[name] = rows

    incident = {}
    incident_ref = assignment_outputs.get("incident-assembler")
    if incident_ref is not None:
        incident = workspace.store.read_json(incident_ref)["value"]
    included = tuple(incident.get("included_signal_refs", ()))
    attribution_refs = tuple(
        assignment_outputs[name]
        for name in ("attribution-a", "attribution-b")
        if name in assignment_outputs
    )
    return {
        "assignment_output_refs": assignment_outputs,
        "assignment_output_statuses": assignment_output_statuses,
        "attempts": attempts,
        "cost_report": usage,
        "semantic_path": {
            "incident_status": incident.get("status", "missing"),
            "included_signal_count": len(included),
            "independent_signal_sources": len(
                {item.split("#", 1)[0] for item in included}
            ),
            "semantic_interpretation_ref": assignment_outputs.get(
                "semantic-interpreter"
            ),
        },
        "blind_attribution": {
            "output_refs": list(attribution_refs),
            "distinct_outputs": len(set(attribution_refs)) == 2,
            "cross_exposure": False,
            "curator_output_ref": assignment_outputs.get("atlas-curator"),
        },
    }


def _record_live_hardening_route(
    workspace: Workspace,
    *,
    application_ref: str,
    lineage_ref: str,
    report: Mapping[str, Any],
    capsule_path: str | Path,
) -> Mapping[str, Any]:
    """Freeze the first honest D5 terminal from live D2 evidence."""
    output_refs = report["assignment_output_refs"]
    incident_ref = str(output_refs["incident-assembler"])
    semantic_ref = str(output_refs["semantic-interpreter"])
    attribution_refs = tuple(
        str(output_refs[name]) for name in ("attribution-a", "attribution-b")
    )
    principals = []
    cause_layers = set()
    for name, attribution_ref in zip(
        ("attribution-a", "attribution-b"), attribution_refs, strict=True
    ):
        attempts = report["attempts"][name]
        receipt = workspace.store.read_json(attempts[-1]["receipt_ref"])["value"]
        principals.append(str(receipt["principal"]))
        attribution = workspace.store.read_json(attribution_ref)["value"]
        for factor in attribution.get("factors", ()):
            layer = str(factor.get("layer", "")).strip().lower()
            if layer in {"interaction", "seat", "host"}:
                cause_layers.add("coordination")
            elif layer == "actor":
                cause_layers.add("agent-capability")

    owning_value = {
        "schema_version": "live-owning-layer-finding.1",
        "status": "partially-attributed",
        "incident_ref": incident_ref,
        "semantic_interpretation_ref": semantic_ref,
        "attribution_refs": list(attribution_refs),
        "cause_layers": sorted(cause_layers),
        "successful_contrast_refs": [],
        "unresolved_branches": ["causal-contrast-not-run"],
        "finding": (
            "The live attributions supply testable causal hypotheses but no two "
            "independent successful Counterfactual Contrasts."
        ),
    }
    owning_ref = workspace.put_evidence_object(
        object_kind="owning_layer_finding",
        object_schema="live-owning-layer-finding.1",
        value=owning_value,
        producer="live-hardening-route.1",
        verifier="hardening-route-verifier.1",
    )
    semantic_path = report["semantic_path"]
    failure = FailureEvidenceSummary(
        incident_ref=incident_ref,
        owning_layer_finding_ref=owning_ref,
        corroborated=(
            semantic_path["incident_status"] == "complete"
            and int(semantic_path["independent_signal_sources"]) >= 2
        ),
        attribution_principals=tuple(principals),
        owning_layer_status="partially-attributed",
        cause_layers=tuple(sorted(cause_layers)),
        material_defect_layers=(),
        successful_contrast_refs=(),
        unresolved_branches=("causal-contrast-not-run",),
    )
    if workspace.store.put_json(failure.to_mapping()) != failure.summary_ref:
        raise ValueError("live Failure Evidence Summary identity is unstable")
    failure_ref = workspace.put_evidence_object(
        object_kind="failure_evidence_summary",
        object_schema="failure-evidence-summary.1",
        value=failure.to_mapping(),
        producer="live-hardening-route.1",
        verifier="hardening-route-verifier.1",
    )
    route = route_failure(failure)
    if workspace.store.put_json(route.to_mapping()) != route.decision_ref:
        raise ValueError("live Hardening Route identity is unstable")
    route_ref = workspace.put_evidence_object(
        object_kind="hardening_route_decision",
        object_schema="hardening-route-decision.1",
        value=route.to_mapping(),
        producer="live-hardening-route.1",
        verifier="hardening-route-verifier.1",
    )
    status = {
        "harden": "eligible-for-class-promotion",
        "repair": "repair-required",
        "quarantine": "quarantined",
    }[route.route]
    evidence_refs = (
        lineage_ref,
        incident_ref,
        semantic_ref,
        *attribution_refs,
        owning_ref,
        failure.summary_ref,
        failure_ref,
        route.decision_ref,
        route_ref,
    )
    terminal_value = {
        "schema_version": "live-hardening-terminal.1",
        "application_ref": application_ref,
        "stage": "failure-routing",
        "status": status,
        "route": route.route,
        "blockers": list(route.reasons if route.route != "harden" else ()),
        "evidence_refs": list(evidence_refs),
        "next_required_evidence": (
            ["two independent successful Counterfactual Contrast receipts"]
            if route.route == "quarantine"
            else []
        ),
    }
    terminal_ref = workspace.put_evidence_object(
        object_kind="hardening_terminal_result",
        object_schema="live-hardening-terminal.1",
        value=terminal_value,
        producer="live-hardening-route.1",
        verifier="hardening-route-verifier.1",
    )
    workspace.climb.append(
        "live_hardening_terminal_recorded",
        actor="hardening:coordinator",
        payload={
            "application_ref": application_ref,
            "terminal_ref": terminal_ref,
            "status": status,
            "route": route.route,
        },
        object_refs=(terminal_ref, *evidence_refs),
        idempotency_key=f"live-hardening:{application_ref}",
    )
    schema_ref = workspace.put_evidence_object(
        object_kind="schema_bundle",
        object_schema="schema-bundle.1",
        value={
            "schemas": [
                "live-owning-layer-finding.1",
                "failure-evidence-summary.1",
                "hardening-route-decision.1",
                "live-hardening-terminal.1",
            ]
        },
        producer="live-hardening-route.1",
        verifier="schema-bundle-verifier.1",
    )
    verifier_ref = workspace.put_evidence_object(
        object_kind="verifier_bundle",
        object_schema="verifier-bundle.1",
        value={
            "entry_point": "narrative_game.workspace:verify_claim_capsule_bytes",
            "route_verifier": "narrative_game.difficulty:route_failure",
        },
        producer="live-hardening-route.1",
        verifier="verifier-bundle-verifier.1",
    )
    checkpoint_ref = workspace.create_checkpoint()
    manifest_ref = workspace.create_claim_manifest(
        claim_id=f"live-hardening:{application_ref}",
        checkpoint_ref=checkpoint_ref,
        root_refs=(terminal_ref,),
        schema_refs=(schema_ref,),
        verifier_refs=(verifier_ref,),
        actor="hardening:coordinator",
        idempotency_key=f"live-hardening-claim:{application_ref}",
    )
    capsule = workspace.export_claim_capsule(manifest_ref, capsule_path)["capsule"]
    return {
        **terminal_value,
        "terminal_ref": terminal_ref,
        "claim_manifest_ref": manifest_ref,
        "claim_capsule": capsule,
    }


def run_live_falsifier(
    *,
    fixture: str,
    game_json: bytes,
    output_root: str | Path,
    codex_executable: str | None = None,
) -> Mapping[str, Any]:
    """Run and persist one complete real-agent analysis lineage."""
    output = Path(output_root)
    output.mkdir(parents=True, exist_ok=False)
    release, archive, package, expectation = build_semantic_falsifier_episode(
        game_json, fixture=fixture
    )
    replay_findings = verify_episode(release, archive)
    reward = evaluate_episode(release, archive)
    if replay_findings or reward.aggregate != 1.0:
        raise ValueError("semantic falsifier no longer passes its frozen Episode gates")
    if expectation_is_satisfied(package, expectation):
        raise ValueError("semantic falsifier no longer falsifies the named obligation")

    atlas_seed = {
        "schema_version": "published-failure-atlas.1",
        "stage": "qualification-seed",
        "classes": [],
    }
    definition = analysis_instrument_v1(
        normative_contract_ref=_analysis_contract_ref(),
        published_atlas_ref=digest_json(atlas_seed),
    )
    application = apply_instrument(
        definition,
        episode_package_ref=package.package_id,
        principal_prefix=f"live:{fixture}",
    )
    grants, objects = _live_materials(release, package, expectation)
    models = definition.to_mapping()["models"]
    specs = {item.assignment: item for item in ASSIGNMENTS}

    def factory(applied, view):
        slot = specs[applied.assignment].model_slot
        return CodexCLIAnalysisDriver(
            model=applied.requested_model,
            max_output_tokens=int(models[slot]["max_output_tokens"]),
            codex_executable=codex_executable,
        )

    workspace = Workspace.create(
        output / "workspace",
        workspace_id=f"difficulty-live:{fixture}:codex-v1",
        actor="human-triggered:codex",
    )
    result = run_analysis_lineage(
        workspace,
        definition=definition,
        application=application,
        available_grants=grants,
        evidence_objects=objects,
        driver_factory=factory,
        episode_actor_principals=tuple(
            sorted({trajectory.actor_id for trajectory in archive.trajectories})
        ),
        capsule_path=output / "diagnostic-claim.ngc",
    )
    report = _live_result_report(workspace, result)
    hardening = _record_live_hardening_route(
        workspace,
        application_ref=application.application_ref,
        lineage_ref=result.lineage_object_ref,
        report=report,
        capsule_path=output / "hardening-terminal.ngc",
    )
    archive_path = output / "episode.json"
    archive_path.write_bytes(archive.to_bytes())
    summary = {
        "schema_version": "live-analysis-demonstration.1",
        "fixture": fixture,
        "release_id": release.release_id,
        "episode_id": archive.episode_id,
        "episode_ref": package.archive_ref,
        "episode_reward": reward.aggregate,
        "episode_verification": "verified",
        "hidden_expectation_id": expectation.expectation_id,
        "hidden_expectation_satisfied": False,
        "instrument_definition_ref": definition.definition_ref,
        "instrument_application_ref": application.application_ref,
        "lineage_status": result.status,
        "lineage_object_ref": result.lineage_object_ref,
        "claim_manifest_ref": result.claim_manifest_ref,
        "claim_capsule": result.claim_capsule,
        "assignment_statuses": {
            name: value.status
            for name, value in sorted(result.assignment_results.items())
        },
        **report,
        "hardening": hardening,
        "eligibility": result.eligibility.to_mapping(),
        "workspace_verification": workspace.verify(),
    }
    (output / "summary.json").write_bytes(canonical_json(summary))
    return summary


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--fixture", choices=(*SEMANTIC_FALSIFIERS, "both"), default="both"
    )
    parser.add_argument("--codex-executable")
    arguments = parser.parse_args(argv)
    fixtures = SEMANTIC_FALSIFIERS if arguments.fixture == "both" else (arguments.fixture,)
    game_json = Path(arguments.game).read_bytes()
    summaries = []
    for fixture in fixtures:
        summaries.append(
            run_live_falsifier(
                fixture=fixture,
                game_json=game_json,
                output_root=Path(arguments.output) / fixture,
                codex_executable=arguments.codex_executable,
            )
        )
    manifest = {
        "schema_version": "live-analysis-suite.1",
        "fixtures": summaries,
    }
    output = Path(arguments.output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_bytes(canonical_json(manifest))
    print(canonical_json(manifest).decode("utf-8"))


if __name__ == "__main__":
    main()
