"""Proof-path and accessible-evidence contracts for qualification."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .canonical import canonical_json


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def validate_claim_trace(
    trace: Mapping[str, Any], *, required_propositions: tuple[str, ...]
) -> dict[str, Any]:
    """Require every conclusion to be licensed by released, authorized evidence."""
    if trace.get("schema_version") != "0.12":
        raise ValueError("claim trace requires schema_version 0.12")
    claims = trace.get("claims")
    if not isinstance(claims, list):
        raise ValueError("claim trace claims must be a list")
    expected_paths = trace.get("proof_paths", {})
    if not isinstance(expected_paths, Mapping) or not expected_paths:
        raise ValueError("claim trace proof_paths must be a non-empty mapping")
    normalized_paths = {
        str(path): sorted({str(item) for item in evidence_ids})
        for path, evidence_ids in sorted(expected_paths.items())
    }
    if any(not path or not evidence_ids for path, evidence_ids in normalized_paths.items()):
        raise ValueError("claim trace proof paths require IDs and Evidence members")
    seen: set[str] = set()
    evidence_by_path: dict[str, set[str]] = {}
    normalized = []
    for index, claim in enumerate(claims):
        required = {
            "proposition_id", "evidence_id", "resource_path", "locus",
            "content_hash", "phase_id", "proof_path_ids",
        }
        if not isinstance(claim, Mapping) or required - set(claim):
            raise ValueError(f"claim trace item {index} is incomplete")
        proposition = str(claim["proposition_id"])
        evidence_id = str(claim["evidence_id"])
        resource = str(claim["resource_path"])
        content_hash = str(claim["content_hash"])
        proof_paths = tuple(str(item) for item in claim["proof_path_ids"])
        if not proposition or not evidence_id or not resource or not proof_paths:
            raise ValueError(f"claim trace item {index} lacks an evidence path")
        if not content_hash.startswith("sha256:") or len(content_hash) != 71:
            raise ValueError(f"claim trace item {index} has an invalid content hash")
        locus = claim["locus"]
        if not isinstance(locus, Mapping) or set(locus) not in (
            {"quote"}, {"page", "bbox_norm"}
        ):
            raise ValueError(f"claim trace item {index} needs a quote or visible region")
        if "quote" in locus and not isinstance(locus["quote"], str):
            raise ValueError(f"claim trace item {index} quote must be text")
        if "bbox_norm" in locus:
            bbox = locus["bbox_norm"]
            if (
                not isinstance(locus["page"], int)
                or locus["page"] < 1
                or not isinstance(bbox, (list, tuple))
                or len(bbox) != 4
                or any(not isinstance(item, (int, float)) for item in bbox)
                or not (0 <= bbox[0] < bbox[2] <= 1)
                or not (0 <= bbox[1] < bbox[3] <= 1)
            ):
                raise ValueError(f"claim trace item {index} visible region is invalid")
        seen.add(proposition)
        for proof_path in proof_paths:
            evidence_by_path.setdefault(proof_path, set()).add(evidence_id)
        normalized.append({
            "proposition_id": proposition,
            "evidence_id": evidence_id,
            "resource_path": resource,
            "locus": dict(locus),
            "content_hash": content_hash,
            "phase_id": str(claim["phase_id"]),
            "proof_path_ids": list(proof_paths),
        })
    normalized_required = sorted({str(item) for item in required_propositions})
    missing = sorted(set(normalized_required) - seen)
    if missing:
        raise ValueError(f"claim trace omits required propositions: {missing}")
    undeclared_paths = sorted(set(evidence_by_path) - set(normalized_paths))
    if undeclared_paths:
        raise ValueError(f"claim trace names undeclared proof paths: {undeclared_paths}")
    for path, evidence_ids in normalized_paths.items():
        missing_evidence = sorted(set(evidence_ids) - evidence_by_path.get(path, set()))
        if missing_evidence:
            raise ValueError(
                f"claim trace does not license {path}: missing {missing_evidence}"
            )
    return {
        "schema_version": "0.12",
        "required_propositions": normalized_required,
        "proof_paths": normalized_paths,
        "claims": sorted(
            normalized,
            key=lambda item: (
                item["proposition_id"], item["evidence_id"], item["resource_path"]
            ),
        ),
    }


def claim_trace_licenses_resolution(
    trace: Mapping[str, Any], *, proof_path_id: str
) -> bool:
    """Return whether released evidence licenses every member of one proof path."""
    normalized = validate_claim_trace(
        trace,
        required_propositions=tuple(str(item) for item in trace.get(
            "required_propositions", ()
        )),
    )
    expected = set(normalized["proof_paths"].get(proof_path_id, ()))
    if not expected:
        return False
    licensed = {
        item["evidence_id"]
        for item in normalized["claims"]
        if proof_path_id in item["proof_path_ids"]
    }
    return licensed == expected


def validate_accessibility_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Prove native and accessible channels expose equal facts without answers."""
    required = {
        "schema_version", "artifact_id", "native_hash", "accessible_hash",
        "native_proposition_ids", "accessible_proposition_ids", "entries",
    }
    if required - set(contract) or contract.get("schema_version") != "0.12":
        raise ValueError("accessibility contract is incomplete")
    native = tuple(sorted({str(item) for item in contract["native_proposition_ids"]}))
    accessible = tuple(sorted({
        str(item) for item in contract["accessible_proposition_ids"]
    }))
    if native != accessible:
        raise ValueError("native and accessible channels have unequal proof power")
    entries = contract["entries"]
    if not isinstance(entries, list):
        raise ValueError("accessibility entries must be a list")
    normalized = []
    covered: set[str] = set()
    for index, entry in enumerate(entries):
        fields = {
            "editorial_identification", "visible_wording", "visual_evidence",
            "interpretation", "proposition_ids",
        }
        if not isinstance(entry, Mapping) or fields - set(entry):
            raise ValueError(f"accessibility entry {index} is incomplete")
        if entry["interpretation"] not in ("", None, [], ()):
            raise ValueError("artifact-layer accessibility cannot supply interpretation")
        propositions = tuple(str(item) for item in entry["proposition_ids"])
        covered.update(propositions)
        normalized.append({
            "editorial_identification": _copy(entry["editorial_identification"]),
            "visible_wording": _copy(entry["visible_wording"]),
            "visual_evidence": _copy(entry["visual_evidence"]),
            "interpretation": [],
            "proposition_ids": list(propositions),
        })
    if covered != set(native):
        raise ValueError("accessibility entries do not cover every load-bearing fact")
    for key in ("native_hash", "accessible_hash"):
        value = str(contract[key])
        if not value.startswith("sha256:") or len(value) != 71:
            raise ValueError(f"accessibility {key} is invalid")
    return {
        "schema_version": "0.12",
        "artifact_id": str(contract["artifact_id"]),
        "native_hash": str(contract["native_hash"]),
        "accessible_hash": str(contract["accessible_hash"]),
        "native_proposition_ids": list(native),
        "accessible_proposition_ids": list(accessible),
        "entries": normalized,
    }
