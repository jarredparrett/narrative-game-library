"""Canonical serialization and content identity for every persisted value."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    """Return the one UTF-8 JSON representation used for content identity."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_bytes(value: bytes) -> str:
    """Return a typed SHA-256 content reference."""
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    """Hash a JSON-compatible value after canonical serialization."""
    return digest_bytes(canonical_json(value))
