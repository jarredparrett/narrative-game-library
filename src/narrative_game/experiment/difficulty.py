"""Effectful execution of frozen difficulty-analysis assignments."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Protocol

from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json
from narrative_game.difficulty.instrument import (
    OUTPUT_REQUIRED,
    AnalysisEvidenceView,
    AnalysisInstrumentApplication,
    AnalysisInstrumentDefinition,
    AssignmentApplication,
    compose_prompt,
)
from narrative_game.workspace import Workspace


class AnalysisTransportError(RuntimeError):
    """A provider call failed before returning a model output."""


@dataclass(frozen=True)
class AnalysisModelResponse:
    raw_output: bytes
    resolved_model: str
    provider_response_id: str
    usage: Mapping[str, int]


class AnalysisModelDriver(Protocol):
    def invoke(
        self, request: bytes, *, tools: "EvidenceAccessSession"
    ) -> AnalysisModelResponse: ...


@dataclass(frozen=True)
class Exposure:
    operation: str
    object_ref: str
    span_ids: tuple[str, ...]

    def to_mapping(self) -> dict[str, Any]:
        return {"operation": self.operation, "object_ref": self.object_ref, "span_ids": list(self.span_ids)}


class EvidenceAccessSession:
    """The complete three-operation tool surface available to an analyst."""

    def __init__(
        self,
        view: AnalysisEvidenceView,
        objects: Mapping[str, Mapping[str, Any]],
    ):
        self.view = view
        self._objects = dict(objects)
        self._grants = {item.object_ref: item for item in view.grants}
        self._exposures: list[Exposure] = []
        self._submission: tuple[str, Mapping[str, Any]] | None = None

    def get(self, object_ref: str) -> Mapping[str, Any]:
        if object_ref not in self._grants or object_ref not in self._objects:
            raise PermissionError(f"object is outside the Evidence View: {object_ref}")
        self._exposures.append(Exposure("evidence.get", object_ref, ()))
        return json.loads(canonical_json(self._objects[object_ref]))

    def expand(self, span_ref: str, before: int, after: int) -> tuple[Mapping[str, Any], ...]:
        if before < 0 or after < 0 or before + after > 20:
            raise ValueError("Evidence expansion must be a non-negative bounded neighborhood")
        matched = [item for item in self.view.grants if span_ref in item.span_ids]
        if not matched:
            raise PermissionError(f"span is outside the Evidence View: {span_ref}")
        grant = matched[0]
        value = self.get(grant.object_ref)
        spans = list(value.get("spans", ()))
        indexes = [
            index for index, item in enumerate(spans)
            if item.get("source_span_id") == span_ref
        ]
        if not indexes:
            raise ValueError(f"admitted object does not materialize span: {span_ref}")
        index = indexes[0]
        selected = tuple(spans[max(0, index - before) : index + after + 1])
        selected_ids = tuple(str(item["source_span_id"]) for item in selected)
        self._exposures.append(Exposure("evidence.expand", grant.object_ref, selected_ids))
        return selected

    def submit(self, schema: str, value: Mapping[str, Any]) -> str:
        if self._submission is not None:
            raise ValueError("analysis.submit may freeze only one output per attempt")
        self._submission = (schema, json.loads(canonical_json(value)))
        value_ref = digest_json(value)
        self._exposures.append(Exposure("analysis.submit", value_ref, ()))
        return value_ref

    def ledger_value(self) -> dict[str, Any]:
        return {
            "schema_version": "exposure-ledger.1",
            "view_ref": self.view.view_ref,
            "assignment": self.view.assignment,
            "exposures": [item.to_mapping() for item in self._exposures],
        }


@dataclass(frozen=True)
class AnalysisAttemptResult:
    assignment: str
    status: str
    structured_output_ref: str | None
    attempt_receipt_refs: tuple[str, ...]
    exposure_ledger_ref: str


def _application_assignment(
    application: AnalysisInstrumentApplication, assignment: str
) -> AssignmentApplication:
    return next(item for item in application.assignments if item.assignment == assignment)


def _validate_output(
    schema: str, value: Any, *, allowed_span_ids: frozenset[str]
) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        return ("output must be a JSON object",)
    required = set(OUTPUT_REQUIRED[schema])
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - required)
    findings = [f"missing required field: {item}" for item in missing]
    findings.extend(f"unknown field: {item}" for item in unknown)
    status = value.get("status")
    if status not in {"complete", "partial", "invalid", "incomplete"}:
        findings.append("status is not recognized")
    if schema == "discovery-sweep.1":
        if status == "partial" and not value.get("continuation_cursor"):
            findings.append("partial Sweep requires a continuation cursor")
        if status == "complete" and value.get("continuation_cursor") is not None:
            findings.append("complete Sweep cannot retain a continuation cursor")
        for index, signal in enumerate(value.get("signals", ())):
            if not isinstance(signal, Mapping) or not signal.get("span_refs"):
                findings.append(f"signal {index} requires cited span refs")
    cited = set()

    def collect(item: Any, key: str | None = None) -> None:
        if isinstance(item, Mapping):
            for child_key, child in item.items():
                collect(child, str(child_key))
        elif isinstance(item, (list, tuple)):
            for child in item:
                collect(child, key)
        elif isinstance(item, str) and key in {
            "span_ref",
            "span_refs",
            "evidence_refs",
            "counterevidence_refs",
            "trace_citations",
        }:
            cited.add(item)

    collect(value)
    outside = sorted(cited - allowed_span_ids)
    if outside:
        findings.append("output cites spans outside the Evidence View: " + ", ".join(outside))
    if schema == "independent-review.1":
        if value.get("decision") not in {"accept", "reject"}:
            findings.append("review decision must be accept or reject")
        gates = value.get("gate_results")
        if value.get("decision") == "accept" and isinstance(gates, Mapping) and not all(gates.values()):
            findings.append("review acceptance cannot waive a failed gate")
    return tuple(findings)


def _store_attempt_receipt(
    workspace: Workspace,
    *,
    definition: AnalysisInstrumentDefinition,
    application: AnalysisInstrumentApplication,
    applied: AssignmentApplication,
    view: AnalysisEvidenceView,
    prompt_ref: str,
    request_ref: str,
    attempt: int,
    kind: str,
    raw_output_ref: str,
    structured_output_ref: str,
    exposure_ledger_ref: str,
    runtime_status: str,
    errors: tuple[str, ...],
    provider_response_id: str | None,
    usage: Mapping[str, int],
    upstream_receipt_refs: tuple[str, ...],
) -> str:
    receipt_id = f"analysis-receipt:{application.application_ref[7:19]}:{applied.assignment}:{attempt}"
    value = {
        "receipt_id": receipt_id,
        "authority": next(item.authority for item in definition.assignments if item.assignment == applied.assignment),
        "assignment": applied.assignment,
        "principal": applied.principal,
        "context_id": applied.context_id,
        "provider": applied.provider,
        "requested_model": applied.requested_model,
        "resolved_model": applied.resolved_model,
        "provider_response_id": provider_response_id,
        "endpoint": applied.endpoint,
        "reasoning_effort": "high",
        "sampling": {"temperature": "omitted", "top_p": "omitted", "seed": "omitted"},
        "instrument_ref": definition.definition_ref,
        "application_ref": application.application_ref,
        "prompt_ref": prompt_ref,
        "request_ref": request_ref,
        "input_refs": [application.episode_package_ref],
        "evidence_view_ref": view.view_ref,
        "exposure_ledger_ref": exposure_ledger_ref,
        "structured_output_ref": structured_output_ref,
        "raw_output_ref": raw_output_ref,
        "trace_citations": [],
        "alternatives": [],
        "confidence": "not-reported" if runtime_status != "complete" else "reported-in-output",
        "upstream_receipt_refs": list(upstream_receipt_refs),
        "runtime_status": runtime_status,
        "errors": list(errors),
        "usage": dict(sorted(usage.items())),
        "principal_conflict_result": "pending-lineage-verification",
        "attempt": attempt,
        "attempt_kind": kind,
    }
    return workspace.put_evidence_object(
        object_kind="analysis_receipt",
        object_schema="analysis-receipt.1",
        value=value,
        producer="analysis-runtime.1",
        verifier="analysis-receipt-verifier.1",
    )


def run_analysis_assignment(
    workspace: Workspace,
    *,
    definition: AnalysisInstrumentDefinition,
    application: AnalysisInstrumentApplication,
    view: AnalysisEvidenceView,
    driver: AnalysisModelDriver,
    evidence_objects: Mapping[str, Mapping[str, Any]] | None = None,
    upstream_receipt_refs: tuple[str, ...] = (),
) -> AnalysisAttemptResult:
    """Run one assignment with bounded mechanical retries and full attempt lineage."""
    applied = _application_assignment(application, view.assignment)
    spec = next(item for item in definition.assignments if item.assignment == view.assignment)
    prompt = compose_prompt(definition, view, upstream_receipt_refs=upstream_receipt_refs)
    prompt_ref = workspace.put_evidence_object(
        object_kind="prompt_contract",
        object_schema="analysis-prompt-application.1",
        value={"bytes_utf8": prompt.decode("utf-8")},
        producer="analysis-runtime.1",
        verifier="prompt-contract-verifier.1",
    )
    base_request = canonical_json(
        {
            "prompt_ref": prompt_ref,
            "prompt": prompt.decode("utf-8"),
            "model": applied.requested_model,
            "endpoint": applied.endpoint,
            "reasoning_effort": "high",
        }
    )
    base_request_ref = digest_bytes(base_request)
    session = EvidenceAccessSession(view, evidence_objects or {})
    exposure_ledger_ref = ""
    allowed_span_ids = frozenset(
        span_id for grant in view.grants for span_id in grant.span_ids
    )

    def freeze_exposure_ledger(attempt_number: int) -> str:
        ledger_ref = workspace.put_evidence_object(
            object_kind="exposure_ledger",
            object_schema="exposure-ledger.1",
            value=session.ledger_value(),
            producer="analysis-runtime.1",
            verifier="exposure-ledger-verifier.1",
        )
        workspace.access.append(
            "analysis_evidence_exposed",
            actor=applied.principal,
            payload={
                "assignment": applied.assignment,
                "view_ref": view.view_ref,
                "exposure_ledger_ref": ledger_ref,
                "attempt": attempt_number,
            },
            object_refs=(ledger_ref,),
            idempotency_key=(
                f"access:{application.application_ref}:{applied.assignment}:{attempt_number}"
            ),
        )
        return ledger_ref
    receipts = []
    transport_failures = 0
    schema_repairs = 0
    request = base_request
    kind = "initial"
    while True:
        attempt = len(receipts) + 1
        try:
            response = driver.invoke(request, tools=session)
            raw_ref = workspace.put_evidence_object(
                object_kind="analysis_raw_output",
                object_schema="analysis-raw-output.1",
                value={"bytes_utf8": response.raw_output.decode("utf-8", errors="replace")},
                producer=f"provider:{applied.provider}",
                verifier="analysis-raw-output-verifier.1",
            )
            try:
                parsed = json.loads(response.raw_output)
                errors = _validate_output(
                    spec.output_schema, parsed, allowed_span_ids=allowed_span_ids
                )
            except json.JSONDecodeError as error:
                parsed = {"invalid_raw_output_ref": raw_ref}
                errors = (f"invalid JSON: {error.msg}",)
            structured_ref = workspace.put_evidence_object(
                object_kind="analysis_structured_output" if not errors else "analysis_invalid_output",
                object_schema=spec.output_schema if not errors else "analysis-invalid-output.1",
                value=parsed,
                producer="analysis-runtime.1",
                verifier="analysis-output-schema-verifier.1",
            )
            model_mismatch = response.resolved_model != applied.resolved_model
            if model_mismatch:
                errors = errors + (
                    f"provider resolved {response.resolved_model}, Application pins {applied.resolved_model}",
                )
            exposure_ledger_ref = freeze_exposure_ledger(attempt)
            receipt_ref = _store_attempt_receipt(
                workspace,
                definition=definition,
                application=application,
                applied=applied,
                view=view,
                prompt_ref=prompt_ref,
                request_ref=digest_bytes(request),
                attempt=attempt,
                kind=kind,
                raw_output_ref=raw_ref,
                structured_output_ref=structured_ref,
                exposure_ledger_ref=exposure_ledger_ref,
                runtime_status=(
                    "application-model-mismatch"
                    if model_mismatch
                    else "complete" if not errors else "schema-invalid"
                ),
                errors=errors,
                provider_response_id=response.provider_response_id,
                usage=response.usage,
                upstream_receipt_refs=upstream_receipt_refs,
            )
            receipts.append(receipt_ref)
            if model_mismatch:
                break
            if not errors:
                workspace.analysis.append(
                    "analysis_assignment_completed",
                    actor=applied.principal,
                    payload={
                        "assignment": applied.assignment,
                        "application_ref": application.application_ref,
                        "structured_output_ref": structured_ref,
                        "attempt_receipt_refs": receipts,
                    },
                    object_refs=tuple(receipts) + (structured_ref, exposure_ledger_ref),
                    idempotency_key=f"analysis:{application.application_ref}:{applied.assignment}:complete",
                )
                return AnalysisAttemptResult(
                    applied.assignment, "complete", structured_ref, tuple(receipts), exposure_ledger_ref
                )
            if schema_repairs >= 1:
                break
            schema_repairs += 1
            kind = "schema-repair"
            request = canonical_json(
                {
                    "base_request_ref": base_request_ref,
                    "validation_diagnostics": list(errors),
                    "prior_raw_output_ref": raw_ref,
                    "prior_raw_output": response.raw_output.decode("utf-8", errors="replace"),
                }
            )
        except AnalysisTransportError as error:
            invalid_ref = workspace.put_evidence_object(
                object_kind="analysis_transport_failure",
                object_schema="analysis-transport-failure.1",
                value={"error": str(error)},
                producer="analysis-runtime.1",
                verifier="analysis-transport-verifier.1",
            )
            exposure_ledger_ref = freeze_exposure_ledger(attempt)
            receipt_ref = _store_attempt_receipt(
                workspace,
                definition=definition,
                application=application,
                applied=applied,
                view=view,
                prompt_ref=prompt_ref,
                request_ref=digest_bytes(request),
                attempt=attempt,
                kind=kind,
                raw_output_ref=invalid_ref,
                structured_output_ref=invalid_ref,
                exposure_ledger_ref=exposure_ledger_ref,
                runtime_status="transport-failed",
                errors=(str(error),),
                provider_response_id=None,
                usage={},
                upstream_receipt_refs=upstream_receipt_refs,
            )
            receipts.append(receipt_ref)
            if transport_failures >= 2:
                break
            transport_failures += 1
            kind = "transport-retry"
            # A transport retry repeats the exact bytes that failed, whether the
            # failed request was the initial application or its one schema repair.

    workspace.analysis.append(
        "analysis_assignment_incomplete",
        actor=applied.principal,
        payload={
            "assignment": applied.assignment,
            "application_ref": application.application_ref,
            "attempt_receipt_refs": receipts,
        },
        object_refs=tuple(receipts) + (exposure_ledger_ref,),
        idempotency_key=f"analysis:{application.application_ref}:{applied.assignment}:incomplete",
    )
    return AnalysisAttemptResult(
        applied.assignment, "incomplete", None, tuple(receipts), exposure_ledger_ref
    )
