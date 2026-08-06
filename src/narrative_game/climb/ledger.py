"""Persistent, operator-owned recording for native agentic hill climbs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping

from narrative_game.contracts import canonical_json
from narrative_game.workspace import Workspace
from narrative_game.playtest.model import (
    EvidenceComparison,
    ParticipantConsent,
    PlayObservation,
    PlaytestProtocol,
    PlaytestRun,
)

from .model import (
    AgentReview,
    Authority,
    Dimension,
    Evaluation,
    ExperimentPlan,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReceipt,
    HumanReview,
    ModelReceipt,
    Proposal,
    Requirement,
    SelectionDecision,
    StandingAttestation,
    Task,
    TrialBinding,
    Transition,
)
from .validation import ClimbFinding, validate_climb_bundle


Record = (
    ExperimentPlan
    | Authority
    | FrozenInstrument
    | Task
    | ModelReceipt
    | HumanReceipt
    | Exposure
    | Finding
    | Requirement
    | Evaluation
    | Proposal
    | HumanReview
    | AgentReview
    | Transition
    | StandingAttestation
    | TrialBinding
    | SelectionDecision
    | PlaytestProtocol
    | PlaytestRun
    | EvidenceComparison
)


class ClimbRejected(RuntimeError):
    """The requested record or transition violates a climb invariant."""

    def __init__(self, findings: tuple[ClimbFinding, ...]):
        self.findings = findings
        summary = "; ".join(f"{item.code}: {item.message}" for item in findings)
        super().__init__(summary or "climb operation rejected")


@dataclass(frozen=True)
class StoredRecord:
    kind: str
    record_id: str
    record_ref: str
    value: Record


_KIND_TO_COLLECTION = {
    "experiment_plan": "experiment_plans",
    "authority": "authorities",
    "instrument": "instruments",
    "task": "tasks",
    "model_receipt": "model_receipts",
    "human_receipt": "human_receipts",
    "exposure": "exposures",
    "finding": "findings",
    "requirement": "requirements",
    "evaluation": "evaluations",
    "proposal": "proposals",
    "human_review": "reviews",
    "agent_review": "reviews",
    "transition": "transitions",
    "standing": "standings",
    "trial_binding": "trial_bindings",
    "selection": "selections",
    "playtest_protocol": "playtest_protocols",
    "playtest_run": "playtest_runs",
    "evidence_comparison": "evidence_comparisons",
}


def _kind_and_id(value: Record) -> tuple[str, str]:
    if isinstance(value, ExperimentPlan):
        return "experiment_plan", value.plan_id
    if isinstance(value, Authority):
        return "authority", value.authority_id
    if isinstance(value, FrozenInstrument):
        return "instrument", value.instrument_id
    if isinstance(value, Task):
        return "task", value.task_id
    if isinstance(value, ModelReceipt):
        return "model_receipt", value.receipt_id
    if isinstance(value, HumanReceipt):
        return "human_receipt", value.receipt_id
    if isinstance(value, Exposure):
        return "exposure", value.exposure_id
    if isinstance(value, Finding):
        return "finding", value.finding_id
    if isinstance(value, Requirement):
        return "requirement", value.requirement_id
    if isinstance(value, Evaluation):
        return "evaluation", value.evaluation_id
    if isinstance(value, Proposal):
        return "proposal", value.proposal_id
    if isinstance(value, HumanReview):
        return "human_review", value.review_id
    if isinstance(value, AgentReview):
        return "agent_review", value.review_id
    if isinstance(value, Transition):
        return "transition", value.transition_id
    if isinstance(value, StandingAttestation):
        return "standing", value.attestation_id
    if isinstance(value, TrialBinding):
        return "trial_binding", value.binding_id
    if isinstance(value, SelectionDecision):
        return "selection", value.decision_id
    if isinstance(value, PlaytestProtocol):
        return "playtest_protocol", value.protocol_id
    if isinstance(value, PlaytestRun):
        return "playtest_run", value.run_id
    if isinstance(value, EvidenceComparison):
        return "evidence_comparison", value.comparison_id
    raise TypeError(f"unsupported climb record: {type(value)!r}")


def _parse(kind: str, value: Mapping[str, Any]) -> Record:
    if kind == "experiment_plan":
        result: Record = ExperimentPlan(
            value["experiment_id"], value["profile_id"], value["profile_version"],
            value["instrument_id"], value["branch"],
        )
    elif kind == "authority":
        result: Record = Authority(value["authority_id"], value["kind"], value["role"], value["principal"])
    elif kind == "instrument":
        result = FrozenInstrument(
            value["name"],
            value["version"],
            value["scope"],
            tuple(
                Dimension(item["dimension_id"], item["description"], item["weight"], item["anchors"])
                for item in value["dimensions"]
            ),
            tuple(value["acceptance_rules"]),
            value["blind_protocol"],
            tuple(value["hard_gate_codes"]),
        )
    elif kind == "task":
        result = Task(
            value["task_key"], value["kind"], value["candidate_id"], value["instrument_id"],
            value["assigned_authority_id"], tuple(value["excluded_authority_ids"]),
            value["input_refs"], value["instructions"],
            tuple(value.get("participant_authority_ids", ())),
        )
    elif kind == "model_receipt":
        replay = value.get("replay", {})
        result = ModelReceipt(
            value["authority_id"], value["provider"], value["requested_model"],
            value["resolved_model"], value["role"], value["prompt_hash"],
            value["context_hash"], value["tool_contract_hash"], value["input_hashes"],
            tuple(value["tool_receipt_hashes"]), value["raw_output_ref"],
            value["parsed_output_ref"], value.get("seed"),
            replay.get("prompt_ref"), replay.get("context_ref"),
            replay.get("tool_contract_ref"), replay.get("input_refs", {}),
            value.get("evidence_class"),
        )
    elif kind == "human_receipt":
        result = HumanReceipt(
            value["authority_id"], value["task_id"], value["input_refs"],
            value["response_ref"], value["evidence_class"],
        )
    elif kind == "exposure":
        result = Exposure(
            value["authority_id"], value["object_ref"], value["category"],
            value["purpose"], value["before_task_id"],
        )
    elif kind == "finding":
        result = Finding(
            value["requirement_code"], value["severity"], value["resource_path"],
            value["locus"], value["quote"], value["message"],
        )
    elif kind == "requirement":
        result = Requirement(
            value["requirement_code"], value["property"], value["failure"],
            value["builder_brief"], tuple(value["source_finding_ids"]),
        )
    elif kind == "evaluation":
        result = Evaluation(
            value["task_id"], value["candidate_id"], value["instrument_id"], value["mode"],
            tuple(value["judge_authority_ids"]), tuple(value["model_receipt_ids"]),
            value["scores"], tuple(value["finding_ids"]), value["hard_gate_results"],
            value["outcome"], value.get("claimed_standing"),
            tuple(value.get("human_receipt_ids", ())),
        )
    elif kind == "proposal":
        result = Proposal(
            value["task_id"], value["baseline_draft_ref"], value["proposed_data_ref"],
            tuple(value["requirement_ids"]), value["builder_authority_id"],
            value["model_receipt_id"], value["rationale"],
        )
    elif kind == "human_review":
        result = HumanReview(
            value["proposal_id"], value["reviewer_authority_id"], value["decision"],
            value["reason"], tuple(value["approved_requirement_ids"]),
        )
    elif kind == "agent_review":
        result = AgentReview(
            value["proposal_id"], value["reviewer_authority_id"],
            value["model_receipt_id"], value["decision"], value["reason"],
            tuple(value["approved_requirement_ids"]),
        )
    elif kind == "transition":
        result = Transition(
            value["proposal_id"], value["review_id"], value["reviewer_authority_id"],
            value["branch"], value["parent_draft_ref"], value["proposed_data_ref"],
            value["child_draft_ref"],
        )
    elif kind == "standing":
        result = StandingAttestation(
            value["candidate_id"], value["level"], tuple(value["evaluation_ids"]),
            tuple(value["evidence_kinds"]), value["reviewer_authority_id"], value["statement"],
            tuple(value.get("playtest_run_ids", ())), value.get("comparison_id"),
        )
    elif kind == "trial_binding":
        result = TrialBinding(
            value["candidate_id"], value["release_id"], value["release_bundle_ref"],
            value["physical_export_id"], value["physical_archive_ref"],
            value["blind_trial_id"], value["blind_trial_ref"], value["hard_gate_results"],
        )
    elif kind == "selection":
        result = SelectionDecision(
            value["instrument_id"], value["baseline_evaluation_id"],
            value["child_evaluation_id"], value["outcome"],
            value["selected_candidate_id"], value["reason"],
        )
    elif kind == "playtest_protocol":
        result = PlaytestProtocol(
            value["name"], value["version"], value["binding_id"],
            value["instrument_id"], value["consent_version"],
            int(value["minimum_fresh_runs"]), int(value["minimum_participants_per_run"]),
            tuple(value["required_observation_categories"]),
            bool(value.get("require_model_comparison", True)),
            int(value.get("model_human_delta_tolerance", 10)),
            tuple(value.get("required_response_stages", ())),
            tuple(value.get("individual_response_stages", ())),
            bool(value.get("require_facilitator_phase_observations", False)),
            tuple(value.get("defect_owner_taxonomy", ())),
        )
    elif kind == "playtest_run":
        result = PlaytestRun(
            value["protocol_id"], value["run_key"], value["release_id"],
            value["physical_export_id"], value["session_history_ref"],
            value["production_receipt_ref"], tuple(value["participant_authority_ids"]),
            value["facilitator_authority_id"], tuple(value["observer_authority_ids"]),
            tuple(ParticipantConsent.from_mapping(item) for item in value["consents"]),
            tuple(PlayObservation.from_mapping(item) for item in value["observations"]),
            value["scores"], tuple(value["finding_ids"]), value["hard_gate_results"],
            value["outcome"], value.get("evidence_class", "fresh-human-play"),
        )
    elif kind == "evidence_comparison":
        result = EvidenceComparison(
            value["protocol_id"], value["candidate_id"], value["instrument_id"],
            value["model_evaluation_id"], tuple(value["playtest_run_ids"]),
            value["dimensions"], value["conclusion"],
        )
    else:
        raise ValueError(f"unsupported climb record kind: {kind!r}")
    expected_kind, expected_id = _kind_and_id(result)
    if expected_kind != kind or value.get("record_id") != expected_id:
        raise ValueError(f"{kind} record identity is invalid")
    return result


class ClimbLedger:
    """Append-only climb evidence sharing an operator-owned Workspace store."""

    def __init__(self, workspace: Workspace):
        self.workspace = workspace
        self.store = workspace.store
        self.journal = workspace.climb

    def _records(self) -> tuple[StoredRecord, ...]:
        records: list[StoredRecord] = []
        for event in self.journal.read():
            payload = event.get("payload", {})
            if event.get("event_type") != "climb_recorded":
                raise ValueError(f"unsupported climb event: {event.get('event_type')!r}")
            kind = payload["record_kind"]
            record_id = payload["record_id"]
            record_ref = payload["record_ref"]
            raw = self.store.read_json(record_ref)
            if raw.get("record_kind") != kind or raw.get("record_id") != record_id:
                raise ValueError(f"climb event does not match stored record: {record_id}")
            records.append(StoredRecord(kind, record_id, record_ref, _parse(kind, raw)))
        return tuple(records)

    def records(self) -> tuple[StoredRecord, ...]:
        """Return all reconstructed records in journal order."""
        return self._records()

    def snapshot(self) -> dict[str, tuple[Record, ...]]:
        result: dict[str, list[Record]] = {value: [] for value in _KIND_TO_COLLECTION.values()}
        for record in self._records():
            result[_KIND_TO_COLLECTION[record.kind]].append(record.value)
        return {key: tuple(value) for key, value in result.items()}

    def get(self, kind: str, record_id: str) -> StoredRecord:
        matches = [item for item in self._records() if item.kind == kind and item.record_id == record_id]
        if len(matches) != 1:
            raise KeyError(f"expected one {kind} record {record_id!r}, found {len(matches)}")
        return matches[0]

    def preflight(self, values: Iterable[Record]) -> None:
        """Validate a closed set of records without mutating journals or objects."""
        current = self.snapshot()
        for value in values:
            kind, record_id = _kind_and_id(value)
            collection = _KIND_TO_COLLECTION[kind]
            matches = [
                item for item in current[collection]
                if _kind_and_id(item)[1] == record_id
            ]
            if matches:
                if len(matches) != 1 or matches[0].to_mapping() != value.to_mapping():
                    raise ValueError(
                        f"{kind} identity already names different content: {record_id}"
                    )
                continue
            current[collection] = (*current[collection], value)
        findings = validate_climb_bundle(**current)
        if findings:
            raise ClimbRejected(findings)

    def _record(
        self,
        value: Record,
        *,
        actor: str,
        idempotency_key: str,
        extra_object_refs: tuple[str, ...] = (),
    ) -> StoredRecord:
        kind, record_id = _kind_and_id(value)
        mapping = {
            "schema_version": "0.6",
            "record_kind": kind,
            "record_id": record_id,
            **value.to_mapping(),
        }
        record_ref = self.store.put_json(mapping)
        object_refs = (record_ref, *extra_object_refs)
        existing = self.journal.event_for_key(idempotency_key)
        if existing is None:
            current = self.snapshot()
            current[_KIND_TO_COLLECTION[kind]] = (*current[_KIND_TO_COLLECTION[kind]], value)
            findings = validate_climb_bundle(**current)
            if findings:
                raise ClimbRejected(findings)
        event = self.journal.append(
            "climb_recorded",
            actor=actor,
            payload={"record_kind": kind, "record_id": record_id, "record_ref": record_ref},
            object_refs=object_refs,
            idempotency_key=idempotency_key,
        )
        self.workspace.rebuild_indexes()
        persisted_ref = event["payload"]["record_ref"]
        return StoredRecord(kind, record_id, persisted_ref, value)

    def register(self, value: Record, *, actor: str, idempotency_key: str) -> StoredRecord:
        """Record a fully materialized contract after validating the closed ledger."""
        return self._record(value, actor=actor, idempotency_key=idempotency_key)

    def record_model_invocation(
        self,
        *,
        authority_id: str,
        provider: str,
        requested_model: str,
        resolved_model: str,
        role: str,
        prompt_hash: str,
        context_hash: str,
        tool_contract_hash: str,
        input_hashes: Mapping[str, str],
        tool_receipt_hashes: tuple[str, ...],
        raw_output: bytes,
        parsed_output: Any,
        seed: int | None,
        actor: str,
        idempotency_key: str,
        evidence_class: str | None = None,
    ) -> StoredRecord:
        raw_ref = self.store.put_bytes(raw_output)
        parsed_ref = self.store.put_json(parsed_output)
        receipt = ModelReceipt(
            authority_id, provider, requested_model, resolved_model, role, prompt_hash,
            context_hash, tool_contract_hash, input_hashes, tool_receipt_hashes,
            raw_ref, parsed_ref, seed, evidence_class=evidence_class,
        )
        return self._record(
            receipt,
            actor=actor,
            idempotency_key=idempotency_key,
            extra_object_refs=(raw_ref, parsed_ref),
        )

    def record_replayable_model_invocation(
        self,
        *,
        authority_id: str,
        provider: str,
        requested_model: str,
        resolved_model: str,
        role: str,
        prompt: str,
        context: Any,
        tool_contract: Any,
        inputs: Mapping[str, bytes],
        tool_receipts: tuple[bytes, ...],
        raw_output: bytes,
        parsed_output: Any,
        seed: int | None,
        evidence_class: str,
        actor: str,
        idempotency_key: str,
    ) -> StoredRecord:
        """Persist a model result together with every byte needed to replay it."""
        prompt_ref = self.store.put_bytes(prompt.encode("utf-8"))
        context_ref = self.store.put_json(context)
        tool_contract_ref = self.store.put_json(tool_contract)
        input_refs = {key: self.store.put_bytes(value) for key, value in sorted(inputs.items())}
        tool_receipt_refs = tuple(self.store.put_bytes(value) for value in tool_receipts)
        raw_ref = self.store.put_bytes(raw_output)
        parsed_ref = self.store.put_json(parsed_output)
        receipt = ModelReceipt(
            authority_id=authority_id,
            provider=provider,
            requested_model=requested_model,
            resolved_model=resolved_model,
            role=role,
            prompt_hash=prompt_ref,
            context_hash=context_ref,
            tool_contract_hash=tool_contract_ref,
            input_hashes=dict(input_refs),
            tool_receipt_hashes=tool_receipt_refs,
            raw_output_ref=raw_ref,
            parsed_output_ref=parsed_ref,
            seed=seed,
            prompt_ref=prompt_ref,
            context_ref=context_ref,
            tool_contract_ref=tool_contract_ref,
            input_refs=input_refs,
            evidence_class=evidence_class,
        )
        return self._record(
            receipt,
            actor=actor,
            idempotency_key=idempotency_key,
            extra_object_refs=(
                prompt_ref,
                context_ref,
                tool_contract_ref,
                *input_refs.values(),
                *tool_receipt_refs,
                raw_ref,
                parsed_ref,
            ),
        )

    def record_proposal(
        self,
        *,
        task_id: str,
        baseline_draft_ref: str,
        proposed_data: Mapping[str, Any],
        requirement_ids: tuple[str, ...],
        builder_authority_id: str,
        model_receipt_id: str,
        rationale: str,
        actor: str,
        idempotency_key: str,
    ) -> StoredRecord:
        proposed_data_ref = self.store.put_json(proposed_data)
        proposal = Proposal(
            task_id, baseline_draft_ref, proposed_data_ref, requirement_ids,
            builder_authority_id, model_receipt_id, rationale,
        )
        return self._record(
            proposal,
            actor=actor,
            idempotency_key=idempotency_key,
            extra_object_refs=(baseline_draft_ref, proposed_data_ref),
        )

    def record_human_observation(
        self,
        *,
        authority_id: str,
        task_id: str,
        input_refs: Mapping[str, str],
        response: Mapping[str, Any],
        evidence_class: str,
        actor: str,
        idempotency_key: str,
    ) -> StoredRecord:
        """Persist an exact human observation without representing it as a model call."""
        response_ref = self.store.put_json(response)
        receipt = HumanReceipt(
            authority_id,
            task_id,
            input_refs,
            response_ref,
            evidence_class,
        )
        return self._record(
            receipt,
            actor=actor,
            idempotency_key=idempotency_key,
            extra_object_refs=(*input_refs.values(), response_ref),
        )

    def apply_approved_transition(
        self,
        *,
        proposal_id: str,
        review_id: str,
        branch: str,
        component_lock: Mapping[str, Any],
        idempotency_key: str,
    ) -> Transition:
        proposal_record = self.get("proposal", proposal_id)
        matches = [
            item for item in self._records()
            if item.kind in {"human_review", "agent_review"}
            and item.record_id == review_id
        ]
        if len(matches) != 1:
            raise KeyError(f"expected one review record {review_id!r}, found {len(matches)}")
        review_record = matches[0]
        proposal = proposal_record.value
        review = review_record.value
        assert isinstance(proposal, Proposal)
        assert isinstance(review, (HumanReview, AgentReview))
        reviewer_record = self.get("authority", review.reviewer_authority_id)
        reviewer = reviewer_record.value
        assert isinstance(reviewer, Authority)
        blockers: list[ClimbFinding] = []
        if review.proposal_id != proposal.proposal_id or review.decision != "approved":
            blockers.append(ClimbFinding("climb.unauthorized-transition", "blocker", review.review_id, review.decision, "Only an approved Review of this Proposal may advance canonical state"))
        expected_kind = "human" if isinstance(review, HumanReview) else "agent"
        if reviewer.kind != expected_kind or reviewer.role != "reviewer":
            blockers.append(ClimbFinding("climb.review-authority-required", "blocker", reviewer.authority_id, reviewer.kind, "Canonical movement requires a typed reviewer matching the Review evidence"))
        if set(review.approved_requirement_ids) != set(proposal.requirement_ids):
            blockers.append(ClimbFinding("climb.partial-approval", "blocker", review.review_id, str(review.approved_requirement_ids), "Approval must cover every Proposal Requirement"))
        if blockers:
            raise ClimbRejected(tuple(blockers))
        proposed_data = self.store.read_json(proposal.proposed_data_ref)
        child = self.workspace.commit_draft(
            branch=branch,
            expected_head=proposal.baseline_draft_ref,
            data=proposed_data,
            reason=review.reason,
            actor=f"{reviewer.kind}:{reviewer.principal}",
            component_lock=dict(component_lock),
            operation_receipt={
                "operation": "agentic-transition",
                "task": self.get("task", proposal.task_id).record_ref,
                "proposal": proposal_record.record_ref,
                "review": review_record.record_ref,
                "model_receipt": self.get("model_receipt", proposal.model_receipt_id).record_ref,
                "requirements": [self.get("requirement", item).record_ref for item in proposal.requirement_ids],
            },
            idempotency_key=f"climb-transition-workspace:{idempotency_key}",
        )
        transition = Transition(
            proposal.proposal_id,
            review.review_id,
            reviewer.authority_id,
            branch,
            proposal.baseline_draft_ref,
            proposal.proposed_data_ref,
            child,
        )
        self._record(
            transition,
            actor=f"{reviewer.kind}:{reviewer.principal}",
            idempotency_key=idempotency_key,
            extra_object_refs=(proposal_record.record_ref, review_record.record_ref, child),
        )
        return transition

    def verify(self) -> dict[str, Any]:
        failures: list[str] = []
        journal_ok, journal_failures = self.journal.verify()
        failures.extend(f"journal: {item}" for item in journal_failures)
        records: tuple[StoredRecord, ...] = ()
        if journal_ok:
            try:
                records = self._records()
                findings = validate_climb_bundle(**self.snapshot())
                failures.extend(f"{item.code}: {item.message}" for item in findings)
                authorities = {
                    item.value.authority_id: item.value
                    for item in records
                    if isinstance(item.value, Authority)
                }
                for record in records:
                    if not self.store.verify(record.record_ref):
                        failures.append(f"missing record object: {record.record_ref}")
                    if isinstance(record.value, ModelReceipt):
                        receipt = record.value
                        replay_refs = tuple(
                            item
                            for item in (
                                receipt.prompt_ref,
                                receipt.context_ref,
                                receipt.tool_contract_ref,
                                *receipt.input_refs.values(),
                            )
                            if item is not None
                        )
                        for output_ref in (
                            receipt.raw_output_ref,
                            receipt.parsed_output_ref,
                            *receipt.tool_receipt_hashes,
                            *replay_refs,
                        ):
                            if not self.store.verify(output_ref):
                                failures.append(f"missing model replay object: {output_ref}")
                        for claimed, replay_ref in (
                            (receipt.prompt_hash, receipt.prompt_ref),
                            (receipt.context_hash, receipt.context_ref),
                            (receipt.tool_contract_hash, receipt.tool_contract_ref),
                        ):
                            if replay_ref is not None and claimed != replay_ref:
                                failures.append(f"model replay hash differs: {claimed} != {replay_ref}")
                        for key, replay_ref in receipt.input_refs.items():
                            if receipt.input_hashes.get(key) != replay_ref:
                                failures.append(f"model input replay hash differs: {key}")
                    if isinstance(record.value, HumanReceipt):
                        for input_ref in record.value.input_refs.values():
                            if not self.store.verify(input_ref):
                                failures.append(f"missing human observation input: {input_ref}")
                        if not self.store.verify(record.value.response_ref):
                            failures.append(
                                f"missing human observation response: {record.value.response_ref}"
                            )
                    if isinstance(record.value, PlaytestRun):
                        playtest_refs = (
                            record.value.session_history_ref,
                            record.value.production_receipt_ref,
                            *(item.response_ref for item in record.value.consents),
                            *(item.response_ref for item in record.value.observations),
                        )
                        for playtest_ref in playtest_refs:
                            if not self.store.verify(playtest_ref):
                                failures.append(
                                    f"missing human play evidence object: {playtest_ref}"
                                )
                        try:
                            from narrative_game.runtime import SessionHistory
                            from narrative_game.runtime.runtime import verify_history

                            history = SessionHistory.from_bytes(
                                self.store.read_bytes(record.value.session_history_ref)
                            )
                            verify_history(history)
                            if history.mode != "live" or history.release_id != record.value.release_id:
                                failures.append(
                                    f"playtest Session is not fresh live evidence: {record.value.run_id}"
                                )
                            if not any(
                                item.event_type == "resolution-recorded"
                                for item in history.ordered_events
                            ):
                                failures.append(
                                    f"playtest Session is incomplete: {record.value.run_id}"
                                )
                            genesis = history.ordered_events[0]
                            session_actor_ids = {
                                item["actor"]["id"]
                                for item in genesis.payload["bindings"]
                            }
                            participant_principals = {
                                authorities[item].principal
                                for item in record.value.participant_authority_ids
                                if item in authorities
                            }
                            if participant_principals != session_actor_ids:
                                failures.append(
                                    f"playtest participants differ from Session Actors: {record.value.run_id}"
                                )
                            production = self.store.read_json(
                                record.value.production_receipt_ref
                            )
                            if (
                                production.get("release_id") != record.value.release_id
                                or production.get("physical_export_id")
                                != record.value.physical_export_id
                            ):
                                failures.append(
                                    f"playtest production receipt differs: {record.value.run_id}"
                                )
                            for observation in record.value.observations:
                                response = self.store.read_json(observation.response_ref)
                                if observation.quote not in canonical_json(response).decode("utf-8"):
                                    failures.append(
                                        f"playtest quote is absent from response: {record.value.run_id}"
                                    )
                        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                            failures.append(
                                f"human play evidence verification failed: {exc}"
                            )
            except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                failures.append(f"record reconstruction failed: {exc}")
        return {
            "ok": not failures,
            "failures": failures,
            "journal_events": len(self.journal.read()) if journal_ok else 0,
            "records": len(records),
        }
