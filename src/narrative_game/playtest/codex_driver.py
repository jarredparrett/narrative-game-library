"""Codex CLI adapter for the provider-neutral JSON-command blind-judge protocol."""

from __future__ import annotations

import argparse
import base64
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Callable, Mapping
from zipfile import BadZipFile, ZipFile

from narrative_game.contracts import canonical_json, digest_bytes


Runner = Callable[..., Any]


def _safe_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError(f"blind attachment path is unsafe: {value}")
    return path


def _materialize_attachment(root: Path, item: Mapping[str, Any]) -> None:
    relative = _safe_path(str(item["path"]))
    try:
        data = base64.b64decode(str(item["base64"]), validate=True)
    except ValueError as exc:
        raise ValueError(f"blind attachment is not valid base64: {relative}") from exc
    target = root / "attachments" / Path(*relative.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    if str(item.get("media_type")) != "application/zip":
        return
    extracted = root / "attachments" / (relative.stem + "-contents")
    extracted.mkdir(parents=True, exist_ok=True)
    try:
        with ZipFile(BytesIO(data)) as archive:
            names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
            if len(names) != len(set(names)):
                raise ValueError("blind attachment archive contains duplicate paths")
            for name in names:
                member = _safe_path(name)
                output = extracted / Path(*member.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(archive.read(name))
    except BadZipFile as exc:
        raise ValueError(f"blind attachment is not a valid ZIP: {relative}") from exc


def _judge_schema(request: Mapping[str, Any]) -> dict[str, Any]:
    dimensions = request["context"]["instrument"]["dimensions"]
    dimension_ids = [str(item["dimension_id"]) for item in dimensions]
    if not dimension_ids or len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("blind judge Instrument dimensions are invalid")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["scores", "findings"],
        "properties": {
            "scores": {
                "type": "object",
                "additionalProperties": False,
                "required": dimension_ids,
                "properties": {
                    item: {"type": "integer", "minimum": 0, "maximum": 100}
                    for item in dimension_ids
                },
            },
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "requirement_code", "severity", "resource_path",
                        "locus", "quote", "message",
                    ],
                    "properties": {
                        "requirement_code": {"type": "string", "minLength": 1},
                        "severity": {"enum": ["major", "minor"]},
                        "resource_path": {"type": "string", "minLength": 1},
                        "locus": {"type": "string", "minLength": 1},
                        "quote": {"type": "string", "minLength": 1},
                        "message": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }


def _prompt(request: Mapping[str, Any]) -> bytes:
    context = canonical_json(request["context"]).decode()
    contract = canonical_json(request["tool_contract"]).decode()
    return (
        "You are an independent blind judge. Inspect only the anonymous material "
        "under attachments/. Do not seek repository history, provenance, answer "
        "keys, prior scores, or builder context. Evaluate every frozen dimension "
        "absolutely. Every finding must quote an exact visible span and name its "
        "exact path under the extracted blind trial. Markdown markers, repeated "
        "asterisks, punctuation, and whitespace inside that span are part of the "
        "quote and must not be normalized away. Before returning, use a local "
        "read-only check to prove that every quote is a byte-for-byte substring "
        "of the named file. Return only the JSON object required by the supplied "
        "output schema.\n\n"
        f"Task prompt:\n{request['prompt']}\n\n"
        f"Frozen context:\n{context}\n\n"
        f"Output contract:\n{contract}\n"
    ).encode()


def run_codex_driver(
    request: Mapping[str, Any],
    *,
    runner: Runner = subprocess.run,
    codex_executable: str | None = None,
) -> dict[str, Any]:
    """Run one isolated Codex judge and return the JSON-command response envelope."""
    if request.get("schema_version") != "0.7" or request.get("role") != "judge":
        raise ValueError("Codex judge driver requires a schema 0.7 judge invocation")
    requested_model = str(request.get("requested_model", "")).strip()
    if not requested_model:
        raise ValueError("Codex judge driver requires an explicit model")
    attachments = request.get("attachments")
    if not isinstance(attachments, list) or not attachments:
        raise ValueError("Codex judge driver requires anonymous attachments")
    executable = codex_executable or shutil.which("codex")
    if not executable:
        raise RuntimeError("Codex CLI is not installed or available on PATH")
    timeout_seconds = int(request.get("timeout_seconds", 900))
    with tempfile.TemporaryDirectory(prefix="narrative-game-blind-judge-") as temp:
        root = Path(temp)
        for item in attachments:
            if not isinstance(item, Mapping):
                raise ValueError("blind attachment descriptor is invalid")
            _materialize_attachment(root, item)
        schema_path = root / "judge-output-schema.json"
        result_path = root / "judge-output.json"
        schema_path.write_bytes(canonical_json(_judge_schema(request)))
        argv = [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--model",
            requested_model,
            "--cd",
            str(root),
            "--output-schema",
            str(schema_path),
            "--output-last-message",
            str(result_path),
            "--json",
            "-",
        ]
        completed = runner(
            argv,
            input=_prompt(request),
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
            raise RuntimeError(
                f"Codex blind judge exited {completed.returncode}: {stderr}"
            )
        if not result_path.is_file():
            raise RuntimeError("Codex blind judge returned no final JSON message")
        raw_output = result_path.read_bytes()
        try:
            parsed_output = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise ValueError("Codex blind judge final message is not JSON") from exc
        metadata = canonical_json({
            "schema_version": "1.0",
            "adapter": "narrative-game-codex-judge-driver",
            "requested_model": requested_model,
            "resolved_model": requested_model,
            "resolution_basis": "explicit codex exec --model argument",
            "codex_executable": Path(executable).name,
            "stdout_ref": digest_bytes(completed.stdout),
            "stderr_ref": digest_bytes(completed.stderr),
            "output_ref": digest_bytes(raw_output),
        })
        return {
            "resolved_model": requested_model,
            "raw_output_base64": base64.b64encode(raw_output).decode(),
            "parsed_output": parsed_output,
            "tool_receipts_base64": [
                base64.b64encode(metadata).decode(),
                base64.b64encode(completed.stdout).decode(),
            ],
        }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-executable")
    args = parser.parse_args(argv)
    request = json.load(sys.stdin)
    print(
        canonical_json(
            run_codex_driver(request, codex_executable=args.codex_executable)
        ).decode()
    )


if __name__ == "__main__":
    main()
