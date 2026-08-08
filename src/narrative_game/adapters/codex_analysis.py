"""Authenticated Codex CLI driver for one frozen Analysis Instrument assignment."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Callable, Mapping

from narrative_game.contracts.canonical import canonical_json, digest_bytes
from narrative_game.difficulty.instrument import ASSIGNMENTS, OUTPUT_REQUIRED
from narrative_game.difficulty.suites import ADMISSION_GATES
from narrative_game.experiment.difficulty import (
    AnalysisModelResponse,
    AnalysisTransportError,
    EvidenceAccessSession,
)


Runner = Callable[..., Any]


def _output_schema(schema_name: str) -> dict[str, Any]:
    required = OUTPUT_REQUIRED[schema_name]
    arrays = {
        "actors",
        "admission_plan",
        "alternatives",
        "class_changes",
        "counterevidence",
        "disagreements",
        "evidence_refs",
        "excluded_signal_refs",
        "included_signal_refs",
        "interactions",
        "legal_actions",
        "missing_evidence",
        "missing_or_uncertain_transitions",
        "non_manifesting_control",
        "observed_transitions",
        "omissions",
        "phases",
        "positive_fixtures",
        "protected_invariants",
        "public_obligations",
        "reasons",
        "span_refs",
        "terminal_requirements",
        "unresolved_evidence",
    }
    properties: dict[str, Any] = {
        name: {"type": "array", "items": {"type": "string"}}
        if name in arrays
        else {"type": "string"}
        for name in required
    }
    properties["status"] = {
        "type": "string",
        "enum": ["complete", "partial", "invalid", "incomplete"]
    }
    if "continuation_cursor" in properties:
        properties["continuation_cursor"] = {"type": ["string", "null"]}
    if "signals" in properties:
        properties["signals"] = {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["summary", "expected", "observed", "span_refs"],
                "properties": {
                    "summary": {"type": "string"},
                    "expected": {"type": "string"},
                    "observed": {"type": "string"},
                    "span_refs": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    if "factors" in properties:
        properties["factors"] = {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "factor_id",
                    "layer",
                    "causal_role",
                    "evidence_refs",
                    "counterevidence_refs",
                    "alternative",
                    "confidence_band",
                    "prediction",
                ],
                "properties": {
                    "factor_id": {"type": "string"},
                    "layer": {"type": "string"},
                    "causal_role": {"type": "string"},
                    "evidence_refs": {"type": "array", "items": {"type": "string"}},
                    "counterevidence_refs": {"type": "array", "items": {"type": "string"}},
                    "alternative": {"type": "string"},
                    "confidence_band": {"type": "string"},
                    "prediction": {"type": "string"},
                },
            },
        }
    if "gate_results" in properties:
        properties["gate_results"] = {
            "type": "object",
            "additionalProperties": False,
            "required": list(ADMISSION_GATES),
            "properties": {
                name: {"type": "boolean"} for name in ADMISSION_GATES
            },
        }
    if "decision" in properties:
        properties["decision"] = {"type": "string", "enum": ["accept", "reject"]}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": list(required),
        "properties": properties,
    }


def _usage_and_response_id(stdout: bytes) -> tuple[dict[str, int], str]:
    usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    response_id = "codex:unreported"
    for raw_line in stdout.splitlines():
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started" and event.get("thread_id"):
            response_id = f"codex:{event['thread_id']}"
        event_usage = event.get("usage")
        if isinstance(event_usage, Mapping):
            for key in ("input_tokens", "output_tokens"):
                usage[key] = max(usage[key], int(event_usage.get(key, 0)))
    usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    return usage, response_id


class CodexCLIAnalysisDriver:
    """Run an isolated Sol or Terra assignment through existing Codex auth."""

    def __init__(
        self,
        *,
        model: str,
        max_output_tokens: int,
        codex_executable: str | None = None,
        timeout_seconds: float = 900,
        runner: Runner = subprocess.run,
    ):
        if model not in {"gpt-5.6-sol", "gpt-5.6-terra"}:
            raise ValueError("Analysis Instrument v1 permits only its two frozen models")
        executable = codex_executable or shutil.which("codex")
        if not executable:
            raise RuntimeError("Codex CLI is not installed or available on PATH")
        if max_output_tokens <= 0:
            raise ValueError("Codex analysis requires a positive output budget")
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.codex_executable = executable
        self.timeout_seconds = timeout_seconds
        self.runner = runner

    def invoke(
        self, request: bytes, *, tools: EvidenceAccessSession
    ) -> AnalysisModelResponse:
        request_value = json.loads(request)
        if request_value.get("model") not in {None, self.model}:
            raise ValueError("Codex driver model differs from the frozen assignment")
        assignment = next(
            item for item in ASSIGNMENTS if item.assignment == tools.view.assignment
        )
        admitted: dict[str, dict[str, Any]] = {}
        for grant in sorted(
            tools.view.grants, key=lambda item: (item.object_ref, item.category)
        ):
            item = admitted.get(grant.object_ref)
            if item is None:
                item = {
                    "categories": [],
                    "span_ids": set(),
                    "value": tools.get(grant.object_ref),
                }
                admitted[grant.object_ref] = item
            item["categories"].append(grant.category)
            item["span_ids"].update(grant.span_ids)
        with tempfile.TemporaryDirectory(prefix="narrative-game-analysis-") as temp:
            root = Path(temp)
            evidence_root = root / "evidence"
            evidence_root.mkdir()
            index = []
            for object_ref, item in sorted(admitted.items()):
                filename = f"{object_ref[7:]}.json"
                (evidence_root / filename).write_bytes(canonical_json(item["value"]))
                index.append(
                    {
                        "object_ref": object_ref,
                        "categories": sorted(item["categories"]),
                        "span_ids": sorted(item["span_ids"]),
                        "path": f"evidence/{filename}",
                    }
                )
            prompt = canonical_json(
                {
                    "request": request_value,
                    "admitted_evidence_index": index,
                    "output_budget_tokens": self.max_output_tokens,
                    "instruction": (
                        "You occupy only the authority named in the request. Analyze only the "
                        "content-addressed JSON files listed in admitted_evidence_index. The "
                        "current workspace contains only those admitted files and the response "
                        "schema. Do not inspect parent directories, the repository, the "
                        "network, or prior sessions. Return exactly one JSON object matching "
                        "the supplied output schema. Cite only source_span_id or span_id values "
                        "listed for the corresponding admitted file. Use "
                        "'pending-runtime-receipt' when an analysis_receipt_ref is required "
                        "because the runtime creates that receipt after this response. Do not "
                        "reveal private chain-of-thought; keep only concise evidence-backed "
                        "rationale fields."
                    ),
                }
            )
            schema_path = root / "output-schema.json"
            output_path = root / "output.json"
            schema_path.write_bytes(canonical_json(_output_schema(assignment.output_schema)))
            argv = [
                self.codex_executable,
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--skip-git-repo-check",
                "--sandbox",
                "read-only",
                "--model",
                self.model,
                "--config",
                'model_reasoning_effort="high"',
                "--cd",
                str(root),
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "--json",
                "-",
            ]
            completed = self.runner(
                argv,
                input=prompt,
                capture_output=True,
                check=False,
                timeout=self.timeout_seconds,
            )
            if completed.returncode != 0:
                stderr = completed.stderr.decode("utf-8", errors="replace")[-4000:]
                stdout = completed.stdout.decode("utf-8", errors="replace")[-4000:]
                raise AnalysisTransportError(
                    f"Codex analysis exited {completed.returncode}: {stderr}\n{stdout}"
                )
            if not output_path.is_file():
                raise AnalysisTransportError("Codex analysis returned no final JSON output")
            raw_output = output_path.read_bytes()
            try:
                json.loads(raw_output)
            except json.JSONDecodeError as exc:
                raise AnalysisTransportError(
                    "Codex analysis final response is not JSON"
                ) from exc
            usage, response_id = _usage_and_response_id(completed.stdout)
            # Bind the invocation bytes without exposing full transcripts outside the
            # Evidence Object graph. The runtime freezes raw_output and provider ID.
            if response_id == "codex:unreported":
                response_id = f"codex-output:{digest_bytes(raw_output)[7:23]}"
            return AnalysisModelResponse(
                raw_output,
                self.model,
                response_id,
                usage,
            )
