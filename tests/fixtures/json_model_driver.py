"""Deterministic offline JSON-command model driver used only by capability tests."""

from __future__ import annotations

import base64
import json
import sys


request = json.load(sys.stdin)
scores = {
    item["dimension_id"]: 80
    for item in request["context"]["instrument"]["dimensions"]
}
parsed = {"scores": scores, "findings": []}
raw = json.dumps(parsed, sort_keys=True, separators=(",", ":")).encode()
json.dump(
    {
        "resolved_model": request["requested_model"] + "-resolved",
        "raw_output_base64": base64.b64encode(raw).decode(),
        "parsed_output": parsed,
        "tool_receipts_base64": [],
    },
    sys.stdout,
    sort_keys=True,
)
