"""Stage 7 preparation stops honestly at the real-measurement boundary."""

from __future__ import annotations

import json

from narrative_game.climb import ClimbLedger, TrialBinding
from narrative_game.stage7_experiment import prepare_baseline
from narrative_game.workspace import Workspace


def test_complete_baseline_is_persisted_without_inventing_measurement(tmp_path):
    """stage7.real-measurement: preparation emits no fixture score or Evaluation."""
    prepared = prepare_baseline(tmp_path / "stage7")
    assert prepared.summary["status"] == "awaiting-real-baseline-measurement"
    assert prepared.summary["model_receipts"] == 0
    assert prepared.summary["evaluations"] == 0
    assert prepared.summary["standing"] is None
    assert prepared.task.candidate_id == prepared.build.candidate.candidate_id
    assert prepared.binding.candidate_id == prepared.build.candidate.candidate_id
    assert prepared.binding.release_id == prepared.release.release_id
    assert prepared.binding.physical_export_id == prepared.physical.export_id
    assert prepared.binding.blind_trial_id == prepared.trial.trial_id
    assert all(prepared.binding.hard_gate_results.values())
    assert prepared.ledger.snapshot()["model_receipts"] == ()
    assert prepared.ledger.snapshot()["evaluations"] == ()
    assert prepared.ledger.snapshot()["selections"] == ()
    assert prepared.workspace.verify()["ok"]
    assert prepared.ledger.verify()["ok"]


def test_prepared_archive_relocates_complete_release_physical_and_trial_bytes(tmp_path):
    """stage7.portability: the pre-measurement archive carries every complete package."""
    prepared = prepare_baseline(tmp_path / "stage7")
    imported = Workspace.import_archive(
        prepared.output_root / "ashwood-stage7-prepared.ngw",
        tmp_path / "imported",
    )
    ledger = ClimbLedger(imported)
    binding = ledger.snapshot()["trial_bindings"][0]
    assert isinstance(binding, TrialBinding)
    assert imported.store.read_bytes(binding.release_bundle_ref) == prepared.release.bundle_bytes
    assert imported.store.read_bytes(binding.physical_archive_ref) == prepared.physical.archive_bytes
    assert imported.store.read_bytes(binding.blind_trial_ref) == prepared.trial.archive_bytes
    assert ledger.verify()["ok"]
    assert imported.verify()["ok"]
    summary = json.loads((prepared.output_root / "stage7-preparation.json").read_bytes())
    assert summary == prepared.summary
