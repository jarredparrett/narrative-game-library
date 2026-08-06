"""Persisted execution control for bounded and formal hill-climb plans."""

from __future__ import annotations

import json
from typing import Any, Mapping

from narrative_game.climb.planning import (
    EfficiencyPlan,
    PreflightObservation,
    PreflightState,
    advance_preflight,
)
from narrative_game.contracts import canonical_json
from narrative_game.workspace.io import atomic_write


HUMAN_BOUNDARIES = (
    "target_and_instrument",
    "repair_tranche",
    "completed_exact_candidate",
    "disposition",
)


def _authorization(
    data: bytes, *, plan: EfficiencyPlan, expected_boundary: str
) -> dict[str, Any]:
    try:
        value = json.loads(data)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("human authorization must be exact JSON bytes") from exc
    if not isinstance(value, Mapping) or value.get("schema_version") != "0.13":
        raise ValueError("human authorization contract is incomplete")
    if value.get("plan_id") != plan.plan_id:
        raise ValueError("human authorization names another efficiency plan")
    if value.get("boundary") != expected_boundary or expected_boundary not in HUMAN_BOUNDARIES:
        raise ValueError("human authorization names another transition boundary")
    if value.get("decision") != "approved" or not isinstance(value.get("scope"), Mapping):
        raise ValueError("human authorization decision or scope is invalid")
    if expected_boundary == "target_and_instrument" and (
        value["scope"].get("primary_target") != plan.primary_target
        or value["scope"].get("instrument_id") != plan.instrument_id
    ):
        raise ValueError("human authorization does not freeze the selected target and instrument")
    if expected_boundary == "repair_tranche" and (
        value["scope"].get("selected_loop") != plan.selected_loop
        or sorted(value["scope"].get("representative_units", ()))
        != sorted(plan.representative_units)
    ):
        raise ValueError("human authorization does not cover the repair tranche")
    if expected_boundary == "completed_exact_candidate" and (
        not plan.exact_candidate_id
        or value["scope"].get("candidate_id") != plan.exact_candidate_id
    ):
        raise ValueError("human authorization does not cover the exact Candidate")
    return dict(value)


class EfficiencyController:
    """One verified active experiment and its bounded execution state."""

    schema_version = "0.13"

    def __init__(self, workspace):
        self.workspace = workspace
        self.journal = workspace.operational

    @property
    def events(self) -> list[dict[str, Any]]:
        return [
            event for event in self.journal.read()
            if event["event_type"].startswith("efficiency_")
        ]

    @property
    def plan_events(self) -> list[dict[str, Any]]:
        return [
            event for event in self.events
            if event["event_type"] == "efficiency_plan_recorded"
        ]

    def _plans(self) -> dict[str, EfficiencyPlan]:
        result = {}
        for event in self.plan_events:
            plan = EfficiencyPlan.from_mapping(
                self.workspace.store.read_json(event["payload"]["plan_ref"])
            )
            result[plan.plan_id] = plan
        return result

    def get_plan(self, plan_id: str) -> EfficiencyPlan:
        try:
            return self._plans()[plan_id]
        except KeyError as exc:
            raise ValueError(f"unknown efficiency plan: {plan_id}") from exc

    def record_plan(
        self,
        plan: EfficiencyPlan,
        *,
        target_authorization_bytes: bytes,
        actor: str = "human:operator",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        approval = _authorization(
            target_authorization_bytes,
            plan=plan,
            expected_boundary="target_and_instrument",
        )
        plan_ref = self.workspace.store.put_json(plan.to_mapping())
        approval_ref = self.workspace.store.put_bytes(target_authorization_bytes)
        event = self.journal.append(
            "efficiency_plan_recorded",
            actor=actor,
            payload={
                "schema_version": self.schema_version,
                "plan_id": plan.plan_id,
                "plan_ref": plan_ref,
                "target_authorization_ref": approval_ref,
                "authorization_boundary": approval["boundary"],
            },
            object_refs=[plan_ref, approval_ref],
            idempotency_key=idempotency_key or f"efficiency-plan:{plan.plan_id}",
        )
        self.workspace.rebuild_indexes()
        self.write_projection()
        return event

    def authorize_boundary(
        self,
        plan_id: str,
        *,
        boundary: str,
        authorization_bytes: bytes,
        actor: str = "human:operator",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if boundary == "target_and_instrument":
            raise ValueError("target authorization is recorded with the plan")
        plan = self.get_plan(plan_id)
        if boundary in self.authorized_boundaries(plan_id):
            raise ValueError("efficiency boundary is already authorized")
        if boundary == "repair_tranche" and plan.mode != "bounded_preflight":
            raise ValueError("only a bounded preflight has a repair tranche")
        if boundary in {"completed_exact_candidate", "disposition"} and (
            plan.mode != "formal_measurement"
        ):
            raise ValueError("exact Candidate and disposition belong to formal measurement")
        if boundary == "disposition" and not self.formal_measurement_events(plan_id):
            raise ValueError("disposition requires completed formal measurement evidence")
        _authorization(authorization_bytes, plan=plan, expected_boundary=boundary)
        approval_ref = self.workspace.store.put_bytes(authorization_bytes)
        event = self.journal.append(
            "efficiency_human_boundary_recorded",
            actor=actor,
            payload={
                "schema_version": self.schema_version,
                "plan_id": plan_id,
                "boundary": boundary,
                "authorization_ref": approval_ref,
            },
            object_refs=[approval_ref],
            idempotency_key=idempotency_key or f"efficiency-auth:{plan_id}:{boundary}",
        )
        self.workspace.rebuild_indexes()
        self.write_projection()
        return event

    def formal_measurement_events(self, plan_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            event for event in self.events
            if event["event_type"] == "efficiency_formal_measurement_recorded"
            and event["payload"].get("plan_id") == plan_id
        )

    def record_formal_measurement(
        self,
        plan_id: str,
        *,
        candidate_id: str,
        instrument_id: str,
        judge_authority_ids: tuple[str, ...],
        evidence_bytes: bytes,
        actor: str = "system:formal-measurement",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Bind one completed formal panel to its exact frozen plan."""
        plan = self.get_plan(plan_id)
        if plan.mode != "formal_measurement":
            raise ValueError("preflight evidence cannot be recorded as formal measurement")
        if "completed_exact_candidate" not in self.authorized_boundaries(plan_id):
            raise ValueError("formal measurement requires exact Candidate human review")
        if candidate_id != plan.exact_candidate_id or instrument_id != plan.instrument_id:
            raise ValueError("formal evidence names another Candidate or Instrument")
        if tuple(sorted(judge_authority_ids)) != tuple(
            sorted(plan.judge_authority_ids)
        ):
            raise ValueError("formal evidence names another independent judge panel")
        if not evidence_bytes:
            raise ValueError("formal measurement requires exact evidence bytes")
        evidence_ref = self.workspace.store.put_bytes(evidence_bytes)
        event = self.journal.append(
            "efficiency_formal_measurement_recorded",
            actor=actor,
            payload={
                "schema_version": self.schema_version,
                "plan_id": plan_id,
                "candidate_id": candidate_id,
                "instrument_id": instrument_id,
                "judge_authority_ids": list(judge_authority_ids),
                "evidence_ref": evidence_ref,
            },
            object_refs=[evidence_ref],
            idempotency_key=idempotency_key or f"efficiency-formal:{plan_id}",
        )
        self.workspace.rebuild_indexes()
        self.write_projection()
        return event

    def authorized_boundaries(self, plan_id: str) -> tuple[str, ...]:
        boundaries = []
        for event in self.events:
            if event["payload"].get("plan_id") != plan_id:
                continue
            if event["event_type"] == "efficiency_plan_recorded":
                boundaries.append("target_and_instrument")
            elif event["event_type"] == "efficiency_human_boundary_recorded":
                boundaries.append(event["payload"]["boundary"])
        return tuple(boundaries)

    def state(self, plan_id: str) -> PreflightState:
        plan = self.get_plan(plan_id)
        state = PreflightState(best_score=plan.baseline_score)
        for event in self.events:
            if (
                event["event_type"] != "efficiency_observation_recorded"
                or event["payload"].get("plan_id") != plan_id
            ):
                continue
            observation = PreflightObservation.from_mapping(
                self.workspace.store.read_json(event["payload"]["observation_ref"])
            )
            state = advance_preflight(plan, state, observation)
        return state

    def record_observation(
        self,
        plan_id: str,
        observation: PreflightObservation,
        *,
        actor: str = "system:bounded-preflight",
        idempotency_key: str | None = None,
    ) -> PreflightState:
        plan = self.get_plan(plan_id)
        required = {"target_and_instrument", "repair_tranche"}
        if not required <= set(self.authorized_boundaries(plan_id)):
            raise ValueError("bounded execution requires one approved repair tranche")
        prior = self.state(plan_id)
        state = advance_preflight(plan, prior, observation)
        observation_ref = self.workspace.store.put_json(observation.to_mapping())
        state_ref = self.workspace.store.put_json(state.to_mapping())
        self.journal.append(
            "efficiency_observation_recorded",
            actor=actor,
            payload={
                "schema_version": self.schema_version,
                "plan_id": plan_id,
                "observation_id": observation.observation_id,
                "observation_ref": observation_ref,
                "state_ref": state_ref,
            },
            object_refs=[observation_ref, state_ref],
            idempotency_key=(
                idempotency_key
                or f"efficiency-observation:{plan_id}:{observation.observation_id}"
            ),
        )
        self.workspace.rebuild_indexes()
        self.write_projection()
        return state

    def derive_projection(self) -> dict[str, Any]:
        if not self.plan_events:
            raise ValueError("Workspace has no efficiency plan")
        event = self.plan_events[-1]
        plan = self.get_plan(event["payload"]["plan_id"])
        boundaries = self.authorized_boundaries(plan.plan_id)
        state = self.state(plan.plan_id) if plan.mode == "bounded_preflight" else None
        if plan.mode == "bounded_preflight" and "repair_tranche" not in boundaries:
            next_transition = "human_review:repair_tranche"
        elif plan.mode == "bounded_preflight":
            assert state is not None
            next_transition = (
                "human_review:create_formal_plan_for_completed_candidate"
                if state.status == "ready_for_formal_measurement"
                else state.next_transition
            )
        elif "completed_exact_candidate" not in boundaries:
            next_transition = "human_review:completed_exact_candidate"
        elif not self.formal_measurement_events(plan.plan_id):
            next_transition = "run_complete_blind_instrument_once"
        elif "disposition" not in boundaries:
            next_transition = "human_review:disposition"
        else:
            next_transition = "qualification_transition_complete"
        remaining = None
        if plan.budget is not None and state is not None:
            remaining = {
                "iterations": max(
                    0, plan.budget.max_iterations - state.iterations_used
                ),
                "model_calls": max(
                    0, plan.budget.max_model_calls - state.model_calls_used
                ),
                "tokens": (
                    max(0, plan.budget.max_tokens - state.tokens_used)
                    if plan.budget.max_tokens is not None else None
                ),
            }
        return {
            "schema_version": self.schema_version,
            "plan_id": plan.plan_id,
            "primary_target": plan.primary_target,
            "mode": plan.mode,
            "selected_loop": plan.selected_loop,
            "baseline_candidate_id": plan.baseline_candidate_id,
            "instrument_id": plan.instrument_id,
            "representative_units": list(plan.representative_units),
            "routes": [item.to_mapping() for item in plan.routes],
            "invalidation": plan.impact.to_mapping(),
            "authorized_boundaries": list(boundaries),
            "state": state.to_mapping() if state else None,
            "remaining_budget": remaining,
            "next_authorized_transition": next_transition,
            "journal_head": self.workspace.manifest["journal_heads"]["operational"],
        }

    def write_projection(self, *, sync_standing: bool = True) -> dict[str, Any]:
        projection = self.derive_projection()
        atomic_write(
            self.workspace.root / "active-experiment.json", canonical_json(projection)
        )
        if sync_standing and any(
            event["event_type"] == "selected_rung_recorded"
            for event in self.workspace.qualification.read()
        ):
            from .standing import ExperimentSpine

            ExperimentSpine(self.workspace)
        return projection

    def verify(self) -> dict[str, Any]:
        failures = []
        plans: dict[str, EfficiencyPlan] = {}
        states: dict[str, PreflightState] = {}
        boundaries: dict[str, set[str]] = {}
        formal_seen: set[str] = set()
        for event in self.events:
            payload = event.get("payload", {})
            try:
                if event["event_type"] == "efficiency_plan_recorded":
                    plan = EfficiencyPlan.from_mapping(
                        self.workspace.store.read_json(payload["plan_ref"])
                    )
                    if plan.plan_id != payload["plan_id"] or plan.plan_id in plans:
                        raise ValueError("efficiency Plan identity is duplicated or invalid")
                    _authorization(
                        self.workspace.store.read_bytes(
                            payload["target_authorization_ref"]
                        ),
                        plan=plan,
                        expected_boundary="target_and_instrument",
                    )
                    plans[plan.plan_id] = plan
                    states[plan.plan_id] = PreflightState(
                        best_score=plan.baseline_score
                    )
                    boundaries[plan.plan_id] = {"target_and_instrument"}
                elif event["event_type"] == "efficiency_human_boundary_recorded":
                    plan = plans[payload["plan_id"]]
                    boundary = payload["boundary"]
                    _authorization(
                        self.workspace.store.read_bytes(payload["authorization_ref"]),
                        plan=plan,
                        expected_boundary=boundary,
                    )
                    if boundary in boundaries[plan.plan_id]:
                        raise ValueError("efficiency boundary is authorized more than once")
                    if boundary == "repair_tranche" and plan.mode != "bounded_preflight":
                        raise ValueError("formal plan contains a repair tranche")
                    if boundary in {"completed_exact_candidate", "disposition"} and (
                        plan.mode != "formal_measurement"
                    ):
                        raise ValueError("preflight contains a formal human boundary")
                    if boundary == "disposition" and plan.plan_id not in formal_seen:
                        raise ValueError("disposition preceded formal measurement")
                    boundaries[plan.plan_id].add(boundary)
                elif event["event_type"] == "efficiency_observation_recorded":
                    plan = plans[payload["plan_id"]]
                    if not {"target_and_instrument", "repair_tranche"} <= boundaries[
                        plan.plan_id
                    ]:
                        raise ValueError("preflight ran before tranche authorization")
                    observation = PreflightObservation.from_mapping(
                        self.workspace.store.read_json(payload["observation_ref"])
                    )
                    expected = advance_preflight(
                        plan, states[plan.plan_id], observation
                    )
                    recorded = PreflightState.from_mapping(
                        self.workspace.store.read_json(payload["state_ref"])
                    )
                    if recorded != expected:
                        raise ValueError("persisted preflight state is not replayable")
                    states[plan.plan_id] = expected
                elif event["event_type"] == "efficiency_formal_measurement_recorded":
                    plan = plans[payload["plan_id"]]
                    if plan.plan_id in formal_seen:
                        raise ValueError("formal measurement was recorded more than once")
                    if plan.mode != "formal_measurement":
                        raise ValueError("preflight contains formal evidence")
                    if "completed_exact_candidate" not in boundaries[plan.plan_id]:
                        raise ValueError("formal measurement preceded Candidate review")
                    if (
                        payload["candidate_id"] != plan.exact_candidate_id
                        or payload["instrument_id"] != plan.instrument_id
                        or tuple(sorted(payload["judge_authority_ids"]))
                        != tuple(sorted(plan.judge_authority_ids))
                    ):
                        raise ValueError("formal measurement differs from its frozen plan")
                    if not self.workspace.store.verify(payload["evidence_ref"]):
                        raise ValueError("formal measurement evidence is missing or corrupt")
                    formal_seen.add(plan.plan_id)
                else:
                    raise ValueError(
                        f"unsupported efficiency event: {event['event_type']}"
                    )
                for ref in event.get("object_refs", []):
                    if not self.workspace.store.verify(ref):
                        raise ValueError(f"efficiency object is missing or corrupt: {ref}")
            except (KeyError, OSError, ValueError, json.JSONDecodeError) as exc:
                failures.append(str(exc))
        if plans:
            try:
                recorded = json.loads(
                    (self.workspace.root / "active-experiment.json").read_bytes()
                )
                if recorded != self.derive_projection():
                    failures.append("active experiment projection is stale")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                failures.append(f"active experiment projection is unreadable: {exc}")
        return {
            "ok": not failures,
            "failures": failures,
            "plans_verified": len(plans),
            "events_verified": len(self.events),
        }
