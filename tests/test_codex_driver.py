"""Capability tests for the isolated Codex CLI blind-judge adapter."""

from __future__ import annotations

import base64
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest

from narrative_game.playtest.codex_driver import run_codex_driver


def _archive(path: str = "trial/brief.txt") -> bytes:
    output = BytesIO()
    with ZipFile(output, "w") as archive:
        archive.writestr(path, "Anonymous complete trial")
    return output.getvalue()


def _request(data: bytes) -> dict:
    return {
        "schema_version": "0.7",
        "requested_model": "gpt-test-pinned",
        "role": "judge",
        "prompt": "Judge the attached anonymous trial.",
        "context": {
            "cover_story": "Anonymous investigation",
            "instrument": {
                "dimensions": [{"dimension_id": "quality"}],
            },
            "assigned_lens": "complete-experience",
        },
        "tool_contract": {
            "output": {
                "scores": {"quality": "integer 0..100"},
                "findings": [],
            },
        },
        "attachments": [{
            "path": "blind-trial.zip",
            "media_type": "application/zip",
            "base64": base64.b64encode(data).decode(),
        }],
        "seed": 17,
    }


def test_codex_driver_isolates_trial_and_returns_replay_receipts():
    """stage11.codex-driver: only anonymous attachments enter the judge workspace."""
    seen = {}

    def runner(argv, **kwargs):
        root = Path(argv[argv.index("--cd") + 1])
        seen["prompt"] = kwargs["input"]
        seen["trial"] = (
            root / "attachments/blind-trial-contents/trial/brief.txt"
        ).read_text()
        output = Path(argv[argv.index("--output-last-message") + 1])
        output.write_text(json.dumps({"scores": {"quality": 81}, "findings": []}))
        return SimpleNamespace(returncode=0, stdout=b'{"type":"turn.completed"}\n', stderr=b"")

    result = run_codex_driver(
        _request(_archive()), runner=runner, codex_executable="/opt/bin/codex"
    )
    assert seen["trial"] == "Anonymous complete trial"
    assert b"Do not seek repository history" in seen["prompt"]
    assert b"byte-for-byte substring" in seen["prompt"]
    assert result["resolved_model"] == "gpt-test-pinned"
    assert result["parsed_output"] == {
        "scores": {"quality": 81}, "findings": [],
    }
    assert len(result["tool_receipts_base64"]) == 2


def test_codex_driver_rejects_archive_path_escape_before_invocation():
    """stage11.codex-driver-safety: blind archives cannot escape isolation."""
    called = False

    def runner(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("runner must not be called")

    with pytest.raises(ValueError, match="unsafe"):
        run_codex_driver(
            _request(_archive("../answer-key.txt")),
            runner=runner,
            codex_executable="/opt/bin/codex",
        )
    assert not called
