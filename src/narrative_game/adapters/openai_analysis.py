"""OpenAI Responses API driver for one frozen Analysis assignment."""

from __future__ import annotations

import json
from typing import Any

from narrative_game.contracts.canonical import canonical_json
from narrative_game.experiment.difficulty import (
    AnalysisModelResponse,
    AnalysisTransportError,
    EvidenceAccessSession,
)


class OpenAIResponsesAnalysisDriver:
    """Resolve admitted evidence, then run one isolated Responses API request."""

    def __init__(
        self,
        *,
        model: str,
        max_output_tokens: int,
        client: Any | None = None,
        timeout_seconds: float = 900,
    ):
        if model not in {"gpt-5.6-sol", "gpt-5.6-terra"}:
            raise ValueError("Analysis Instrument v1 permits only its two frozen models")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - depends on optional extra
                raise RuntimeError(
                    "OpenAI analysis requires `pip install narrative-game-library[analysis]`"
                ) from exc
            client = OpenAI(timeout=timeout_seconds)
        self.client = client
        self.model = model
        self.max_output_tokens = max_output_tokens

    def invoke(
        self, request: bytes, *, tools: EvidenceAccessSession
    ) -> AnalysisModelResponse:
        request_value = json.loads(request)
        admitted = {
            grant.object_ref: tools.get(grant.object_ref)
            for grant in sorted(tools.view.grants, key=lambda item: item.object_ref)
        }
        input_value = canonical_json(
            {
                "request": request_value,
                "admitted_evidence": admitted,
                "instruction": (
                    "Return only one JSON object matching the output contract in the "
                    "request. Cite only source_span_id values present in admitted evidence."
                ),
            }
        ).decode("utf-8")
        try:
            response = self.client.responses.create(
                model=self.model,
                input=input_value,
                max_output_tokens=self.max_output_tokens,
                reasoning={"effort": "high"},
                text={"format": {"type": "json_object"}},
                store=False,
            )
        except Exception as exc:
            # The runtime preserves the error and controls retries. Provider-specific
            # exception classes need not leak into the provider-neutral interface.
            raise AnalysisTransportError(f"{type(exc).__name__}: {exc}") from exc
        if getattr(response, "status", None) != "completed":
            raise AnalysisTransportError(
                f"response {getattr(response, 'id', 'unknown')} ended as "
                f"{getattr(response, 'status', 'unknown')}"
            )
        usage = getattr(response, "usage", None)
        usage_value = {
            "input_tokens": int(getattr(usage, "input_tokens", 0)),
            "output_tokens": int(getattr(usage, "output_tokens", 0)),
            "total_tokens": int(getattr(usage, "total_tokens", 0)),
        }
        return AnalysisModelResponse(
            str(response.output_text).encode("utf-8"),
            str(response.model),
            str(response.id),
            usage_value,
        )
