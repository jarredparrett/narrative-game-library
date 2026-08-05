"""Persistent, operator-owned recording for native agentic hill climbs."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from narrative_game.workspace import Workspace

from .model import (
    Authority,
    Dimension,
    Evaluation,
    Exposure,
    Finding,
    FrozenInstrument,
    HumanReview,
    ModelReceipt,
    Proposal,
    Requirement,
    StandingAttestation,
    Task,
    Transition,
)
from .validation import ClimbFinding, validate_climb_bundle


Record = (
    Authority
    | FrozenInstrument
    | Task
    | ModelReceipt
    | Exposure
    | Finding
    | Requirement
    | Evaluation
    | Proposal
    | HumanReview
    | Transition
    | StandingAttestation
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
    "authority": "authorities",
    "instrument": "instruments",
    "task": "tasks",
    "model_receipt": "model_receipts",
    "exposure": "exposures",
    "finding": "findings",
    "requirement": "requirements",
    "evaluation": "evaluations",
    "proposal": "proposals",
    "human_review": "reviews",
    "transition": "transitions",
    "standing": "standings",
}


def _kind_and_id(value: Record) -> tuple[str, str]:
    if isinstance(value, Authority):
        return "authority", value.authority_id
    if isinstance(value, FrozenInstrument):
        return "instrument", value.instrument_id
    if isinstance(value, Task):
        return "task", value.task_id
    if isinstance(value, ModelReceipt):
        return "model_receipt", value.receipt_id
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
    if isinstance(value, Transition):
        return "transition", value.transition_id
    if isinstance(value, StandingAttestation):
        return "standing", value.attestation_id
    raise TypeError(f"unsupported climb record: {type(value)!r}")


def _parse(kind: str, value: Mapping[str, Any]) -> Record:
    if kind == "authority":
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
        )
    elif kind == "model_receipt":
        result = ModelReceipt(
            value["authority_id"], value["provider"], value["requested_model"],
            value["resolved_model"], value["role"], value["prompt_hash"],
            value["context_hash"], value["tool_contract_hash"], value["input_hashes"],
            tuple(value["tool_receipt_hashes"]), value["raw_output_ref"],
            value["parsed_output_ref"], value.get("seed"),
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
    ) -> StoredRecord:
        raw_ref = self.store.put_bytes(raw_output)
        parsed_ref = self.store.put_json(parsed_output)
        receipt = ModelReceipt(
            authority_id, provider, requested_model, resolved_model, role, prompt_hash,
            context_hash, tool_contract_hash, input_hashes, tool_receipt_hashes,
            raw_ref, parsed_ref, seed,
        )
        return self._record(
            receipt,
            actor=actor,
            idempotency_key=idempotency_key,
            extra_object_refs=(raw_ref, parsed_ref),
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
        review_record = self.get("human_review", review_id)
        proposal = proposal_record.value
        review = review_record.value
        assert isinstance(proposal, Proposal)
        assert isinstance(review, HumanReview)
        reviewer_record = self.get("authority", review.reviewer_authority_id)
        reviewer = reviewer_record.value
        assert isinstance(reviewer, Authority)
        blockers: list[ClimbFinding] = []
        if review.proposal_id != proposal.proposal_id or review.decision != "approved":
            blockers.append(ClimbFinding("climb.unauthorized-transition", "blocker", review.review_id, review.decision, "Only an approved Review of this Proposal may advance canonical state"))
        if reviewer.kind != "human" or reviewer.role != "reviewer":
            blockers.append(ClimbFinding("climb.human-authority-required", "blocker", reviewer.authority_id, reviewer.kind, "Canonical movement requires a human reviewer"))
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
            actor=f"human:{reviewer.principal}",
            component_lock=dict(component_lock),
            operation_receipt={
                "operation": "agentic-transition",
                "task": self.get("task", proposal.task_id).record_ref,
                "proposal": proposal_record.record_ref,
                "human_review": review_record.record_ref,
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
            actor=f"human:{reviewer.principal}",
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
                for record in records:
                    if not self.store.verify(record.record_ref):
                        failures.append(f"missing record object: {record.record_ref}")
                    if isinstance(record.value, ModelReceipt):
                        for output_ref in (record.value.raw_output_ref, record.value.parsed_output_ref):
                            if not self.store.verify(output_ref):
                                failures.append(f"missing model output: {output_ref}")
            except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
                failures.append(f"record reconstruction failed: {exc}")
        return {
            "ok": not failures,
            "failures": failures,
            "journal_events": len(self.journal.read()) if journal_ok else 0,
            "records": len(records),
        }
