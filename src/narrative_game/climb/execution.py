"""Effect boundary for human-triggered model occupancy of typed climb Tasks."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Protocol

from narrative_game.contracts.canonical import canonical_json
from narrative_game.workspace import IdempotencyConflict

from .ledger import ClimbLedger, ClimbRejected, StoredRecord
from .model import Authority, ModelReceipt, Task
from .validation import ClimbFinding


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


@dataclass(frozen=True)
class InvocationAttachment:
    path: str
    media_type: str
    data: bytes


@dataclass(frozen=True)
class ModelInvocation:
    task_id: str
    authority_id: str
    role: str
    requested_model: str
    prompt: str
    context: Mapping[str, Any]
    tool_contract: Mapping[str, Any]
    attachments: tuple[InvocationAttachment, ...] = ()
    seed: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "context", _copy(self.context))
        object.__setattr__(self, "tool_contract", _copy(self.tool_contract))


@dataclass(frozen=True)
class DriverOutput:
    provider: str
    resolved_model: str
    evidence_class: str
    raw_output: bytes
    parsed_output: Any
    tool_receipts: tuple[bytes, ...] = ()
    usage: Mapping[str, int] = field(default_factory=dict)
    agent_id: str | None = None
    context_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "parsed_output", _copy(self.parsed_output))
        if (self.agent_id is None) != (self.context_id is None):
            raise ValueError("Driver Output identity requires agent_id and context_id")
        if self.agent_id is not None and (
            not self.agent_id.strip() or not self.context_id or not self.context_id.strip()
        ):
            raise ValueError("Driver Output identity values must be non-empty")
        usage = dict(self.usage)
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in usage.values()
        ):
            raise ValueError("model usage values must be non-negative integers")
        object.__setattr__(self, "usage", usage)


class ModelDriver(Protocol):
    """Provider-neutral model call supplied by the operator's host application."""

    def invoke(self, invocation: ModelInvocation) -> DriverOutput: ...


@dataclass(frozen=True)
class ModelExecution:
    """One independent invocation and the key that makes it replay-idempotent."""

    invocation: ModelInvocation
    driver: ModelDriver
    idempotency_key: str


def _block(code: str, locus: str, quote: str, message: str) -> ClimbRejected:
    return ClimbRejected((ClimbFinding(code, "blocker", locus, quote, message),))


def _prepare_invocation(
    ledger: ClimbLedger,
    invocation: ModelInvocation,
    *,
    idempotency_key: str,
) -> tuple[Authority, dict[str, bytes], dict[str, Any], StoredRecord | None]:
    """Validate an invocation and return its immutable persistence envelope."""
    task_record = ledger.get("task", invocation.task_id)
    authority_record = ledger.get("authority", invocation.authority_id)
    task = task_record.value
    authority = authority_record.value
    assert isinstance(task, Task)
    assert isinstance(authority, Authority)
    if authority.authority_id not in task.occupant_authority_ids:
        raise _block(
            "climb.execution-authority-mismatch",
            task.task_id,
            authority.authority_id,
            "Model invocation Authority is not an authorized Task occupant",
        )
    if invocation.role != authority.role:
        raise _block(
            "climb.execution-role-mismatch",
            task.task_id,
            invocation.role,
            "Model invocation role differs from its Authority",
        )
    if not invocation.requested_model.strip() or not invocation.prompt.strip():
        raise ValueError("requested_model and prompt are required")
    attachment_paths = [item.path for item in invocation.attachments]
    if len(attachment_paths) != len(set(attachment_paths)) or "task.json" in attachment_paths:
        raise ValueError("attachment paths must be unique and may not use task.json")
    if any(
        not item.path.strip() or not item.media_type.strip()
        for item in invocation.attachments
    ):
        raise ValueError("attachment path and media type are required")

    inputs = {"task.json": canonical_json(task.to_mapping())}
    inputs.update({item.path: item.data for item in invocation.attachments})
    context = {
        **dict(invocation.context),
        "task_id": task.task_id,
        "authority_id": authority.authority_id,
        "attachments": [
            {"path": item.path, "media_type": item.media_type}
            for item in invocation.attachments
        ],
    }
    existing = ledger.journal.event_for_key(idempotency_key)
    if existing is not None:
        if existing.get("payload", {}).get("record_kind") != "model_receipt":
            raise IdempotencyConflict("model execution key names another climb operation")
        stored = ledger.get("model_receipt", existing["payload"]["record_id"])
        receipt = stored.value
        assert isinstance(receipt, ModelReceipt)
        envelope = replay_envelope(ledger, receipt.receipt_id)
        expected = {
            "prompt": invocation.prompt,
            "context": context,
            "tool_contract": dict(invocation.tool_contract),
            "inputs": inputs,
        }
        if (
            receipt.authority_id != authority.authority_id
            or receipt.requested_model != invocation.requested_model
            or any(envelope[key] != value for key, value in expected.items())
        ):
            raise IdempotencyConflict(
                "model execution key was reused for another invocation"
            )
        return authority, inputs, context, stored
    return authority, inputs, context, None


def _persist_output(
    ledger: ClimbLedger,
    invocation: ModelInvocation,
    authority: Authority,
    inputs: Mapping[str, bytes],
    context: Mapping[str, Any],
    output: DriverOutput,
    *,
    idempotency_key: str,
) -> StoredRecord:
    if not output.provider.strip() or not output.resolved_model.strip():
        raise ValueError("Model Driver must report provider and resolved model")
    return ledger.record_replayable_model_invocation(
        authority_id=authority.authority_id,
        provider=output.provider,
        requested_model=invocation.requested_model,
        resolved_model=output.resolved_model,
        role=invocation.role,
        prompt=invocation.prompt,
        context=context,
        tool_contract=invocation.tool_contract,
        inputs=inputs,
        tool_receipts=output.tool_receipts,
        raw_output=output.raw_output,
        parsed_output=output.parsed_output,
        seed=invocation.seed,
        evidence_class=output.evidence_class,
        usage=output.usage,
        agent_id=output.agent_id,
        context_id=output.context_id,
        actor=f"agent:{authority.principal}",
        idempotency_key=idempotency_key,
    )


def execute_model_task(
    ledger: ClimbLedger,
    invocation: ModelInvocation,
    driver: ModelDriver,
    *,
    idempotency_key: str,
) -> StoredRecord:
    """Invoke one configured model and atomically preserve its replay envelope."""
    authority, inputs, context, existing = _prepare_invocation(
        ledger, invocation, idempotency_key=idempotency_key
    )
    if existing is not None:
        return existing
    output = driver.invoke(invocation)
    return _persist_output(
        ledger, invocation, authority, inputs, context, output,
        idempotency_key=idempotency_key,
    )


def execute_model_tasks_concurrently(
    ledger: ClimbLedger,
    executions: tuple[ModelExecution, ...],
    *,
    max_workers: int | None = None,
) -> tuple[StoredRecord, ...]:
    """Invoke independent tasks concurrently; persist receipts in input order.

    Provider latency is parallel. Store and journal mutations remain serial, so
    the same ordered executions produce the same receipt and aggregation order.
    """
    if not executions:
        raise ValueError("concurrent model execution requires at least one task")
    keys = tuple(item.idempotency_key for item in executions)
    if len(keys) != len(set(keys)):
        raise ValueError("concurrent model execution keys must be distinct")
    prepared = [
        _prepare_invocation(
            ledger, item.invocation, idempotency_key=item.idempotency_key
        )
        for item in executions
    ]
    pending = [
        index for index, (_, _, _, existing) in enumerate(prepared)
        if existing is None
    ]
    outputs: dict[int, DriverOutput] = {}
    errors: dict[int, Exception] = {}
    if pending:
        workers = max_workers or len(pending)
        if workers < 1:
            raise ValueError("max_workers must be positive")
        with ThreadPoolExecutor(max_workers=min(workers, len(pending))) as pool:
            futures = {
                index: pool.submit(
                    executions[index].driver.invoke,
                    executions[index].invocation,
                )
                for index in pending
            }
            for index in pending:
                try:
                    outputs[index] = futures[index].result()
                except Exception as exc:  # preserve completed sibling evidence
                    errors[index] = exc
    result = []
    for index, execution in enumerate(executions):
        authority, inputs, context, existing = prepared[index]
        if existing is not None:
            result.append(existing)
        elif index in outputs:
            result.append(
                _persist_output(
                    ledger,
                    execution.invocation,
                    authority,
                    inputs,
                    context,
                    outputs[index],
                    idempotency_key=execution.idempotency_key,
                )
            )
    if errors:
        raise errors[min(errors)]
    return tuple(result)


def replay_envelope(ledger: ClimbLedger, receipt_id: str) -> dict[str, Any]:
    """Load the exact prompt, context, tools, inputs, and outputs for one run."""
    receipt = ledger.get("model_receipt", receipt_id).value
    assert isinstance(receipt, ModelReceipt)
    if not receipt.prompt_ref or not receipt.context_ref or not receipt.tool_contract_ref:
        raise ValueError("Model Receipt predates the replayable invocation envelope")
    return {
        "prompt": ledger.store.read_bytes(receipt.prompt_ref).decode("utf-8"),
        "context": ledger.store.read_json(receipt.context_ref),
        "tool_contract": ledger.store.read_json(receipt.tool_contract_ref),
        "inputs": {
            key: ledger.store.read_bytes(ref)
            for key, ref in sorted(receipt.input_refs.items())
        },
        "tool_receipts": tuple(
            ledger.store.read_bytes(ref) for ref in receipt.tool_receipt_hashes
        ),
        "raw_output": ledger.store.read_bytes(receipt.raw_output_ref),
        "parsed_output": ledger.store.read_json(receipt.parsed_output_ref),
    }
