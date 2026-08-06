"""Stage 7 provider-neutral model execution and replay capability tests."""

from __future__ import annotations

from pathlib import Path
from threading import Barrier

import pytest

from narrative_game.climb import (
    Authority,
    ClimbLedger,
    ClimbRejected,
    Dimension,
    DriverOutput,
    FrozenInstrument,
    InvocationAttachment,
    ModelExecution,
    ModelInvocation,
    Task,
    execute_model_task,
    execute_model_tasks_concurrently,
    replay_envelope,
)
from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.workspace import Workspace


class RecordedDriver:
    def __init__(self, provider: str, resolved_model: str):
        self.provider = provider
        self.resolved_model = resolved_model
        self.calls: list[ModelInvocation] = []

    def invoke(self, invocation: ModelInvocation) -> DriverOutput:
        self.calls.append(invocation)
        parsed = {"decision": "measure", "scores": {"quality": 81}}
        return DriverOutput(
            self.provider,
            self.resolved_model,
            "capability-fixture",
            canonical_json(parsed),
            parsed,
            (b'{"tool":"pdf-text","status":"ok"}',),
        )


def seeded_ledger(tmp_path: Path):
    workspace = Workspace.create(tmp_path / "workspace", workspace_id="model-driver")
    head = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={"title": "Model driver fixture"},
        reason="create fixture",
        actor="human:maker",
        component_lock={"components": []},
        operation_receipt={"operation": "fixture"},
        idempotency_key="draft",
    )
    candidate = workspace.freeze_candidate(
        branch="main", expected_head=head, actor="human:maker", idempotency_key="candidate"
    )
    ledger = ClimbLedger(workspace)
    judge = Authority("judge-model-a", "agent", "judge", "configured-judge-a")
    instrument = FrozenInstrument(
        "complete-package",
        "1.0.0",
        "blind-trial",
        (Dimension("quality", "Complete experience quality", 1, {"0": "broken", "100": "excellent"}),),
        ({"metric": "overall", "operator": ">=", "value": 75},),
        {"allowed": ["blind-trial"], "forbidden": ["trusted-truth"]},
        ("package.verify",),
    )
    ledger.register(judge, actor="human:maker", idempotency_key="authority")
    ledger.register(instrument, actor="human:maker", idempotency_key="instrument")
    trial_ref = workspace.store.put_bytes(b"complete anonymous trial bytes")
    task = Task(
        "measure-complete-package",
        "blind-measure",
        candidate,
        instrument.instrument_id,
        judge.authority_id,
        (),
        {"blind_trial": trial_ref},
        "Measure only the attached Blind Trial.",
    )
    ledger.register(task, actor="human:maker", idempotency_key="task")
    return workspace, ledger, judge, task


def invocation(judge: Authority, task: Task) -> ModelInvocation:
    return ModelInvocation(
        task.task_id,
        judge.authority_id,
        "judge",
        "judge-latest",
        "Apply the frozen instrument to the attached Blind Trial.",
        {"cover_story": "Anonymous two-seat archival investigation."},
        {"output": "evaluation-v1", "tools": ["pdf-text"]},
        (InvocationAttachment("blind-trial.zip", "application/zip", b"complete anonymous trial bytes"),),
        1997,
    )


def test_replaceable_driver_persists_an_exact_replay_envelope(tmp_path):
    """stage7.model-driver: model occupancy is replaceable and fully replayable."""
    workspace, ledger, judge, task = seeded_ledger(tmp_path)
    driver = RecordedDriver("provider-a", "judge-a-2026-08-05")
    stored = execute_model_task(
        ledger, invocation(judge, task), driver, idempotency_key="invoke-judge-a"
    )
    assert len(driver.calls) == 1
    envelope = replay_envelope(ledger, stored.record_id)
    assert envelope["prompt"].startswith("Apply the frozen instrument")
    assert envelope["context"]["task_id"] == task.task_id
    assert envelope["inputs"]["task.json"] == canonical_json(task.to_mapping())
    assert envelope["inputs"]["blind-trial.zip"] == b"complete anonymous trial bytes"
    assert envelope["parsed_output"]["scores"] == {"quality": 81}
    assert envelope["tool_receipts"] == (b'{"tool":"pdf-text","status":"ok"}',)
    assert ledger.verify()["ok"]
    assert workspace.verify()["ok"]

    archive = tmp_path / "model-run.ngw"
    workspace.export_archive(archive)
    imported = Workspace.import_archive(archive, tmp_path / "imported")
    reopened = ClimbLedger(imported)
    assert replay_envelope(reopened, stored.record_id) == envelope


def test_driver_and_resolved_model_are_evidence_not_workflow_identity(tmp_path):
    """stage7.model-driver: another provider can occupy the same typed Task."""
    _, ledger, judge, task = seeded_ledger(tmp_path)
    first = execute_model_task(
        ledger,
        invocation(judge, task),
        RecordedDriver("provider-a", "judge-a-v1"),
        idempotency_key="invoke-a",
    )
    second = execute_model_task(
        ledger,
        invocation(judge, task),
        RecordedDriver("provider-b", "judge-b-v3"),
        idempotency_key="invoke-b",
    )
    assert first.record_id != second.record_id
    assert first.value.provider == "provider-a"
    assert second.value.provider == "provider-b"
    assert first.value.resolved_model == "judge-a-v1"
    assert second.value.resolved_model == "judge-b-v3"


def test_independent_model_calls_are_concurrent_but_receipts_are_ordered(tmp_path):
    """stage11.concurrent-panel: latency is parallel and evidence order is deterministic."""
    workspace, ledger, first, original = seeded_ledger(tmp_path)
    authorities = (first,) + tuple(
        Authority(f"judge-model-{name}", "agent", "judge", f"judge-{name}")
        for name in ("b", "c")
    )
    for authority in authorities[1:]:
        ledger.register(
            authority,
            actor="human:maker",
            idempotency_key=f"authority-{authority.authority_id}",
        )
    task = Task(
        "measure-concurrently",
        "blind-measure",
        original.candidate_id,
        original.instrument_id,
        authorities[0].authority_id,
        (),
        original.input_refs,
        "Measure in parallel and persist in Authority order.",
        tuple(item.authority_id for item in authorities[1:]),
    )
    ledger.register(task, actor="human:maker", idempotency_key="parallel-task")
    barrier = Barrier(3)

    class BarrierDriver(RecordedDriver):
        def invoke(self, model_invocation):
            barrier.wait(timeout=2)
            return super().invoke(model_invocation)

    drivers = tuple(
        BarrierDriver("provider", f"resolved-{index}") for index in range(3)
    )
    executions = tuple(
        ModelExecution(
            ModelInvocation(
                task.task_id,
                authority.authority_id,
                "judge",
                "judge-latest",
                "Apply the frozen instrument.",
                {},
                {"output": "evaluation-v1"},
                (),
                1997,
            ),
            driver,
            f"parallel-{index}",
        )
        for index, (authority, driver) in enumerate(zip(authorities, drivers))
    )
    records = execute_model_tasks_concurrently(ledger, executions)
    assert tuple(item.value.authority_id for item in records) == tuple(
        item.authority_id for item in authorities
    )
    assert [len(item.calls) for item in drivers] == [1, 1, 1]
    replayed = execute_model_tasks_concurrently(ledger, executions)
    assert tuple(item.record_id for item in replayed) == tuple(
        item.record_id for item in records
    )
    assert [len(item.calls) for item in drivers] == [1, 1, 1]
    assert ledger.verify()["ok"]
    assert workspace.verify()["ok"]


def test_execution_rejects_an_authority_that_does_not_occupy_the_task(tmp_path):
    """stage7.model-driver: provider calls cannot bypass Task authority."""
    _, ledger, judge, task = seeded_ledger(tmp_path)
    intruder = Authority("builder-model", "agent", "builder", "configured-builder")
    ledger.register(intruder, actor="human:maker", idempotency_key="intruder")
    bad = ModelInvocation(
        task.task_id,
        intruder.authority_id,
        "builder",
        "builder-latest",
        "Attempt to judge.",
        {},
        {},
    )
    driver = RecordedDriver("provider", "builder-v1")
    with pytest.raises(ClimbRejected, match="execution-authority-mismatch"):
        execute_model_task(ledger, bad, driver, idempotency_key="invalid")
    assert driver.calls == []


def test_frozen_panel_task_accepts_each_named_judge_and_rejects_others(tmp_path):
    """stage7.blind-panel: one frozen Task may be occupied by exactly its named panel."""
    workspace, ledger, first, task = seeded_ledger(tmp_path)
    second = Authority("judge-model-b", "agent", "judge", "configured-judge-b")
    ledger.register(second, actor="human:maker", idempotency_key="authority-b")
    panel = Task(
        task.task_key,
        task.kind,
        task.candidate_id,
        task.instrument_id,
        first.authority_id,
        task.excluded_authority_ids,
        task.input_refs,
        task.instructions,
        (second.authority_id,),
    )
    ledger.register(panel, actor="human:maker", idempotency_key="panel-task")
    second_invocation = ModelInvocation(
        panel.task_id,
        second.authority_id,
        "judge",
        "judge-latest",
        "Apply the frozen instrument to the attached Blind Trial.",
        {"cover_story": "Anonymous two-seat archival investigation."},
        {"output": "evaluation-v1", "tools": ["pdf-text"]},
        (InvocationAttachment("blind-trial.zip", "application/zip", b"complete anonymous trial bytes"),),
        1997,
    )
    stored = execute_model_task(
        ledger,
        second_invocation,
        RecordedDriver("provider-b", "judge-b-v1"),
        idempotency_key="invoke-panel-b",
    )
    assert stored.value.authority_id == second.authority_id
    assert panel.occupant_authority_ids == (first.authority_id, second.authority_id)
    assert workspace.verify()["ok"]
