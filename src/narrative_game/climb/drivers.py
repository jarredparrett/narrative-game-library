"""Optional command protocol for plugging configured live model providers into Tasks."""

from __future__ import annotations

import base64
from dataclasses import dataclass
import json
import subprocess

from narrative_game.contracts.canonical import canonical_json

from .execution import DriverOutput, ModelInvocation


@dataclass(frozen=True)
class JsonCommandDriver:
    """Invoke an operator-supplied executable over a canonical JSON stdin protocol."""

    command: tuple[str, ...]
    provider: str
    evidence_class: str = "live-model"
    timeout_seconds: int = 600

    def invoke(self, invocation: ModelInvocation) -> DriverOutput:
        if not self.command or not self.provider.strip():
            raise ValueError("driver command and provider are required")
        request = {
            "schema_version": "0.7",
            "requested_model": invocation.requested_model,
            "role": invocation.role,
            "prompt": invocation.prompt,
            "context": dict(invocation.context),
            "tool_contract": dict(invocation.tool_contract),
            "attachments": [
                {
                    "path": item.path,
                    "media_type": item.media_type,
                    "base64": base64.b64encode(item.data).decode("ascii"),
                }
                for item in invocation.attachments
            ],
            "seed": invocation.seed,
        }
        completed = subprocess.run(
            self.command,
            input=canonical_json(request),
            capture_output=True,
            check=False,
            timeout=self.timeout_seconds,
        )
        if completed.returncode != 0:
            stderr = completed.stderr.decode("utf-8", errors="replace")[-2000:]
            raise RuntimeError(f"Model Driver exited {completed.returncode}: {stderr}")
        try:
            response = json.loads(completed.stdout)
            raw_output = base64.b64decode(response["raw_output_base64"], validate=True)
            tool_receipts = tuple(
                base64.b64decode(item, validate=True)
                for item in response.get("tool_receipts_base64", [])
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Model Driver returned an invalid JSON protocol response") from exc
        return DriverOutput(
            self.provider,
            str(response["resolved_model"]),
            self.evidence_class,
            raw_output,
            response["parsed_output"],
            tool_receipts,
        )
