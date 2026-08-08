"""PROTOTYPE — pure state machine for failure-driven task hardening."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any


STAGES = [
    "baseline-eligibility",
    "failure-analysis",
    "failure-routing",
    "class-promotion",
    "requirement-freeze",
    "child-generation",
    "challenge-admission",
    "matched-remeasurement",
    "target-comparison",
    "sealed-non-regression",
    "independent-review",
    "hardening-transition",
]


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + sha256(encoded).hexdigest()


def _reference_state(contract: dict[str, Any]) -> dict[str, Any]:
    required_gates = contract["admission_gates"]
    return {
        "scenario": "harder coordination challenge is accepted",
        "expected_terminal": "accepted",
        "contract_ref": canonical_hash(contract),
        "stage_index": 0,
        "stage": STAGES[0],
        "status": "running",
        "route": None,
        "blockers": [],
        "history": [],
        "receipts": [],
        "lineage_edges": [],
        "baseline": {
            "release_ref": "release:baseline-v1",
            "panel_application_ref": "panel-application:baseline-v1",
            "episode_set_ref": "episodes:baseline-standing-plan-v1",
            "profile_ref": "difficulty-profile:baseline-v1",
            "valid": True,
            "complete": True,
            "panel_ref": contract["panel_ref"],
            "instrument_ref": contract["instrument_ref"],
            "resolution_reliability_interval": [0.79, 0.91],
            "handoff_failure_interval": [0.05, 0.14],
            "episode_validity": 1.0,
            "integrity": 1.0,
        },
        "failure": {
            "incident_ref": "incident:uncompleted-handoff-baseline",
            "interpretation_ref": "interpretation:uncompleted-handoff-baseline",
            "attribution_a_ref": "attribution:handoff:a",
            "attribution_b_ref": "attribution:handoff:b",
            "counterfactual_plan_ref": "counterfactual-plan:handoff-ownership",
            "contrast_a_ref": "contrast:policy-rotation",
            "contrast_b_ref": "contrast:role-rotation",
            "owning_finding_ref": "owning-layer:coordination-handoff",
            "corroborated": True,
            "attributions_independent": True,
            "ownership_supported": True,
            "cause_layers": ["coordination"],
            "material_defect_layers": [],
            "contrasts": 2,
        },
        "failure_class": {
            "ref": contract["source_failure_class_ref"],
            "atlas_ref": contract["atlas_ref"],
            "stage": contract["source_failure_class_stage"],
            "positive_fixture": True,
            "non_manifesting_fixture": True,
        },
        "requirement": {
            "ref": "task-hardening-requirement:handoff-v1",
            **deepcopy(contract["task_hardening_requirement"]),
            "selected_mutations": [
                "evidence_distribution",
                "dependency_topology",
                "role_obligations",
            ],
        },
        "generation": {
            "intent_ref": "generation-intent:handoff-challenge-v1",
            "child_release_ref": "release:handoff-child-v1",
            "generation_receipt_ref": "generation-receipt:handoff-child-v1",
        },
        "admission": {
            "ref": "challenge-admission:handoff-child-v1",
            "gate_results": {gate: True for gate in required_gates},
            "solver_principals": [
                contract["principals"]["admission_solver_a"],
                contract["principals"]["admission_solver_b"],
            ],
            "leakage_reviewer": contract["principals"]["leakage_reviewer"],
            "challenge_designer": contract["principals"]["challenge_designer"],
        },
        "child": {
            "panel_application_ref": "panel-application:child-v1",
            "episode_set_ref": "episodes:child-standing-plan-v1",
            "profile_ref": "difficulty-profile:child-v1",
            "panel_ref": contract["panel_ref"],
            "instrument_ref": contract["instrument_ref"],
            "complete": True,
            "invalid_episodes_counted_as_failures": False,
            "resolution_reliability_interval": [0.60, 0.72],
            "handoff_failure_interval": [0.25, 0.38],
            "targeted_delta_interval": [0.12, 0.28],
            "episode_validity": 1.0,
            "integrity": 1.0,
            "other_gating_dimensions_regressed": False,
        },
        "comparison": {
            "ref": "release-comparison:baseline-child-v1",
            "target_contract_ref": contract["target_contract_ref"],
        },
        "sealed": {
            "receipt_ref": "sealed-decision-receipt:cohort-opaque-7",
            "result": "pass",
            "contents_exposed": False,
        },
        "review": {
            "ref": "independent-review:hardening-v1",
            "principal": contract["principals"]["independent_reviewer"],
            "contributors": [
                contract["principals"]["challenge_designer"],
                contract["principals"]["admission_solver_a"],
                contract["principals"]["admission_solver_b"],
                contract["principals"]["leakage_reviewer"],
            ],
            "decision": "accept",
            "mutated_proposal": False,
        },
        "drop_lineage_edge": None,
    }


def _set_path(value: dict[str, Any], path: str, replacement: Any) -> None:
    current = value
    parts = path.split(".")
    for part in parts[:-1]:
        current = current[part]
    current[parts[-1]] = replacement


def scenarios(contract: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = [
        ("harder coordination challenge is accepted", "accepted", {}),
        (
            "game contradiction is routed to repair",
            "repair-required",
            {
                "failure.cause_layers": ["game"],
                "failure.material_defect_layers": ["game"],
            },
        ),
        (
            "runtime timeout is routed to repair",
            "repair-required",
            {
                "failure.cause_layers": ["runtime"],
                "failure.material_defect_layers": ["runtime"],
            },
        ),
        (
            "evaluator false positive is routed to repair",
            "repair-required",
            {
                "failure.cause_layers": ["evaluator"],
                "failure.material_defect_layers": ["evaluator"],
            },
        ),
        (
            "unresolved ownership is quarantined",
            "quarantined",
            {"failure.ownership_supported": False, "failure.contrasts": 1},
        ),
        (
            "proposed class cannot drive hardening",
            "rejected",
            {"failure_class.stage": "proposed"},
        ),
        (
            "ambiguity mutation is rejected",
            "rejected",
            {"requirement.selected_mutations": ["ambiguity"]},
        ),
        (
            "unsolvable child is quarantined",
            "rejected",
            {"admission.gate_results.solver-b-valid-solution": False},
        ),
        (
            "answer-leaking child is quarantined",
            "rejected",
            {"admission.gate_results.leakage-review": False},
        ),
        (
            "changed panel invalidates comparison",
            "rejected",
            {"child.panel_ref": "evaluation-panel:changed-v2"},
        ),
        (
            "invalid episodes cannot inflate hardness",
            "rejected",
            {"child.invalid_episodes_counted_as_failures": True},
        ),
        (
            "child overshoots solvability band",
            "rejected",
            {"child.resolution_reliability_interval": [0.30, 0.45]},
        ),
        (
            "child lacks supported targeted movement",
            "rejected",
            {"child.targeted_delta_interval": [-0.01, 0.08]},
        ),
        (
            "sealed cohort regression blocks transition",
            "rejected",
            {"sealed.result": "fail"},
        ),
        (
            "proposal contributor cannot review",
            "rejected",
            {
                "review.principal": contract["principals"]["challenge_designer"]
            },
        ),
        (
            "broken evidence lineage blocks transition",
            "rejected",
            {"drop_lineage_edge": "incident->semantic-interpretation"},
        ),
    ]
    result = []
    for name, expected, replacements in definitions:
        state = _reference_state(contract)
        state["scenario"] = name
        state["expected_terminal"] = expected
        for path, replacement in replacements.items():
            _set_path(state, path, replacement)
        result.append(state)
    return result


def _record(
    state: dict[str, Any], transition: str, edges: list[str] | None = None
) -> None:
    edges = edges or []
    state["lineage_edges"].extend(edges)
    receipt = {
        "transition": transition,
        "attempt": len(state["receipts"]) + 1,
        "input_state_ref": canonical_hash(
            {
                "history": state["history"],
                "edges": state["lineage_edges"],
                "contract": state["contract_ref"],
            }
        ),
        "result": "passed",
    }
    state["receipts"].append(receipt)
    state["history"].append(transition)


def _halt(state: dict[str, Any], status: str, *blockers: str) -> dict[str, Any]:
    state["status"] = status
    state["blockers"] = list(blockers)
    state["history"].append(f"halt:{status}")
    return state


def _inside(interval: list[float], band: list[float]) -> bool:
    return interval[0] >= band[0] and interval[1] <= band[1]


def advance(contract: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    state = deepcopy(current)
    if state["status"] != "running":
        return state

    stage = STAGES[state["stage_index"]]
    baseline = state["baseline"]
    failure = state["failure"]
    child = state["child"]

    if stage == "baseline-eligibility":
        if not baseline["valid"] or not baseline["complete"]:
            return _halt(state, "rejected", "baseline evidence is invalid or incomplete")
        if baseline["panel_ref"] != contract["panel_ref"]:
            return _halt(state, "rejected", "baseline Panel differs from frozen contract")
        if baseline["instrument_ref"] != contract["instrument_ref"]:
            return _halt(state, "rejected", "baseline Instrument differs from frozen contract")
        _record(
            state,
            stage,
            [
                "baseline-release->baseline-panel-application",
                "baseline-panel-application->baseline-episodes",
                "baseline-episodes->baseline-difficulty-profile",
            ],
        )

    elif stage == "failure-analysis":
        if not failure["corroborated"] or not failure["attributions_independent"]:
            return _halt(state, "quarantined", "Incident lacks independent corroboration")
        _record(
            state,
            stage,
            [
                "baseline-episodes->incident",
                "incident->semantic-interpretation",
                "semantic-interpretation->attribution-a",
                "semantic-interpretation->attribution-b",
                "attribution-a->counterfactual-plan",
                "attribution-b->counterfactual-plan",
                "counterfactual-plan->contrast-a",
                "counterfactual-plan->contrast-b",
                "contrast-a->owning-layer-finding",
                "contrast-b->owning-layer-finding",
            ],
        )

    elif stage == "failure-routing":
        repair_layers = sorted(
            set(failure["material_defect_layers"])
            & set(contract["repair_only_layers"])
        )
        if repair_layers:
            state["route"] = "repair"
            return _halt(
                state,
                "repair-required",
                "defect layers cannot become difficulty: " + ", ".join(repair_layers),
            )
        if not failure["ownership_supported"] or failure["contrasts"] < 2:
            state["route"] = "quarantine"
            return _halt(
                state,
                "quarantined",
                "agent/coordination ownership is not causally supported",
            )
        if not set(failure["cause_layers"]).intersection(
            contract["eligible_hardening_layers"]
        ):
            state["route"] = "repair"
            return _halt(state, "repair-required", "no eligible hardening layer")
        state["route"] = "harden"
        _record(state, stage)

    elif stage == "class-promotion":
        failure_class = state["failure_class"]
        if failure_class["stage"] != "promoted":
            return _halt(state, "rejected", "Failure Class is not promoted")
        if failure_class["atlas_ref"] != contract["atlas_ref"]:
            return _halt(state, "rejected", "Failure Class is absent from pinned Atlas")
        if not failure_class["positive_fixture"] or not failure_class["non_manifesting_fixture"]:
            return _halt(state, "rejected", "Failure Class fixtures are incomplete")
        _record(state, stage, ["owning-layer-finding->promoted-failure-class"])

    elif stage == "requirement-freeze":
        requirement = state["requirement"]
        forbidden = set(requirement["selected_mutations"]) & set(
            requirement["forbidden_mutations"]
        )
        allowed = set(requirement["selected_mutations"]) <= set(
            requirement["allowed_mutation_surface"]
        )
        protected = set(contract["task_hardening_requirement"]["protected_invariants"])
        if forbidden or not allowed:
            return _halt(
                state,
                "rejected",
                "Requirement introduces forbidden or undeclared mutation",
            )
        if not protected <= set(requirement["protected_invariants"]):
            return _halt(state, "rejected", "Requirement omits a protected invariant")
        _record(
            state,
            stage,
            ["promoted-failure-class->task-hardening-requirement"],
        )

    elif stage == "child-generation":
        _record(
            state,
            stage,
            [
                "task-hardening-requirement->generation-intent",
                "generation-intent->child-release",
            ],
        )

    elif stage == "challenge-admission":
        admission = state["admission"]
        failed = sorted(
            name for name, passed in admission["gate_results"].items() if not passed
        )
        principals = admission["solver_principals"] + [
            admission["leakage_reviewer"],
            admission["challenge_designer"],
        ]
        if failed:
            return _halt(
                state,
                "rejected",
                "Challenge Admission failed: " + ", ".join(failed),
            )
        if len(principals) != len(set(principals)):
            return _halt(state, "rejected", "Challenge Admission principal conflict")
        _record(state, stage, ["child-release->challenge-admission"])

    elif stage == "matched-remeasurement":
        if not child["complete"]:
            return _halt(state, "rejected", "child measurement is incomplete")
        if child["panel_ref"] != baseline["panel_ref"]:
            return _halt(state, "rejected", "Panel drift makes comparison ineligible")
        if child["instrument_ref"] != baseline["instrument_ref"]:
            return _halt(state, "rejected", "Instrument drift makes comparison ineligible")
        _record(
            state,
            stage,
            [
                "child-release->child-panel-application",
                "child-panel-application->child-episodes",
                "child-episodes->child-difficulty-profile",
            ],
        )

    elif stage == "target-comparison":
        rule = contract["comparison_rule"]
        if child["invalid_episodes_counted_as_failures"]:
            return _halt(state, "rejected", "invalid Episodes were counted as task failures")
        if child["episode_validity"] < rule["episode_validity_floor"]:
            return _halt(state, "rejected", "Episode validity regressed")
        if child["integrity"] < rule["integrity_floor"]:
            return _halt(state, "rejected", "integrity regressed")
        if child["other_gating_dimensions_regressed"]:
            return _halt(state, "rejected", "a non-target gating dimension regressed")
        if not _inside(
            child["resolution_reliability_interval"],
            rule["resolution_reliability_target_band"],
        ):
            return _halt(state, "rejected", "child is outside the solvability band")
        if not _inside(
            child["handoff_failure_interval"],
            rule["proof_critical_handoff_failure_target_band"],
        ):
            return _halt(state, "rejected", "targeted failure is outside its target band")
        if child["targeted_delta_interval"][0] <= 0:
            return _halt(state, "rejected", "targeted difficulty movement is unsupported")
        _record(
            state,
            stage,
            [
                "baseline-difficulty-profile->release-comparison",
                "child-difficulty-profile->release-comparison",
            ],
        )

    elif stage == "sealed-non-regression":
        sealed = state["sealed"]
        if sealed["contents_exposed"]:
            return _halt(state, "rejected", "sealed cohort contents were exposed")
        if sealed["result"] != contract["comparison_rule"]["required_sealed_result"]:
            return _halt(state, "rejected", "opaque sealed non-regression check failed")
        _record(state, stage, ["release-comparison->sealed-receipt"])

    elif stage == "independent-review":
        review = state["review"]
        if review["principal"] in review["contributors"]:
            return _halt(state, "rejected", "reviewer shares a contributor principal")
        if review["decision"] != "accept" or review["mutated_proposal"]:
            return _halt(state, "rejected", "independent review did not accept unchanged proposal")
        _record(state, stage, ["sealed-receipt->independent-review"])

    elif stage == "hardening-transition":
        _record(state, stage, ["independent-review->hardening-transition"])
        dropped = state.get("drop_lineage_edge")
        if dropped in state["lineage_edges"]:
            state["lineage_edges"].remove(dropped)
        missing = sorted(set(contract["required_lineage"]) - set(state["lineage_edges"]))
        if missing:
            return _halt(
                state,
                "rejected",
                "lineage closure is incomplete: " + ", ".join(missing),
            )
        state["status"] = "accepted"

    if state["status"] == "running":
        state["stage_index"] += 1
        state["stage"] = STAGES[state["stage_index"]]
    return state


def run_to_terminal(contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(state)
    while result["status"] == "running":
        result = advance(contract, result)
    return result
