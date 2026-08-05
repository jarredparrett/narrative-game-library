"""Stage 6 acceptance: one complete native hill climb is executable offline."""

from __future__ import annotations

import json
from pathlib import Path
import socket
import subprocess
import sys

from narrative_game.climb import ClimbLedger, HumanReview, Proposal, Transition
from narrative_game.stage6_fixture import run
from narrative_game.workspace import Workspace


def test_ashwood_climb_moves_only_after_review_and_improves_frozen_score(tmp_path):
    """stage6.vertical-loop: baseline, repair, and fresh measurement share one lineage."""
    result = run(tmp_path / "run")
    assert result.summary["baseline_score"] == 66.9
    assert result.summary["child_score"] == 82.8
    assert result.summary["score_delta"] == 15.9
    assert result.summary["hard_gates"] == {"stage5.access": True, "stage5.rebuild": True}
    assert result.summary["standing"] == "development_only"
    assert result.baseline_candidate_id != result.child_candidate_id
    records = result.ledger.records()
    proposals = [item.value for item in records if isinstance(item.value, Proposal)]
    reviews = [item.value for item in records if isinstance(item.value, HumanReview)]
    transitions = [item.value for item in records if isinstance(item.value, Transition)]
    assert len(proposals) == len(reviews) == len(transitions) == 1
    assert reviews[0].decision == "approved"
    assert transitions[0].proposal_id == proposals[0].proposal_id
    assert transitions[0].review_id == reviews[0].review_id
    assert result.workspace.lineage.read()[-2]["actor"] == "human:fixture-reviewer"
    assert result.ledger.verify()["ok"]
    assert result.workspace.verify()["ok"]


def test_stage6_archive_reopens_with_complete_climb_receipts(tmp_path):
    """stage6.complete-receipts: the portable archive carries the full climb graph."""
    result = run(tmp_path / "run")
    archive = Workspace.import_archive(
        result.output_root / "ashwood-stage6.ngw",
        tmp_path / "reopened",
    )
    verification = ClimbLedger(archive).verify()
    assert verification["ok"]
    assert verification["records"] == 21
    assert archive.verify()["climb_events"] == 21


def test_stage6_build_path_is_offline_and_cross_process_deterministic(tmp_path, monkeypatch):
    """stage6.offline-replay: the full loop has no network or process-local identity."""
    def blocked(*args, **kwargs):
        raise AssertionError("network access is forbidden in the Stage 6 build path")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)
    first = run(tmp_path / "offline")
    assert first.summary["climb_verified"]

    roots = (tmp_path / "process-a", tmp_path / "process-b")
    summaries = []
    archives = []
    for root in roots:
        completed = subprocess.run(
            [sys.executable, "-m", "narrative_game.stage6_fixture", str(root)],
            check=True,
            capture_output=True,
            text=True,
        )
        summaries.append(json.loads(completed.stdout))
        archives.append((root / "output" / "ashwood-stage6.ngw").read_bytes())
    assert summaries[0] == summaries[1]
    assert archives[0] == archives[1]
