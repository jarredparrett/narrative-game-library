"""Derived current standing over one portable game Experiment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from narrative_game.contracts import canonical_json
from narrative_game.contracts.evidence import (
    validate_accessibility_contract,
    validate_claim_trace,
)
from narrative_game.workspace.io import atomic_write


_EVIDENCE_CLASSES = (
    "coherent_build",
    "gameplay",
    "accessibility",
    "artifact_realism",
    "human_play",
    "public_release",
)
_STATUSES = {
    "coherent_build": {"passed", "not_accepted", "unmeasured"},
    "gameplay": {"passed", "not_accepted", "unmeasured"},
    "accessibility": {"passed", "not_accepted", "unmeasured"},
    "artifact_realism": {
        "accepted", "not_accepted", "measurement_required", "unmeasured"
    },
    "human_play": {"passed", "not_accepted", "unmeasured"},
    "public_release": {"qualified", "not_qualified", "unclaimed"},
}


def _validate_standings(
    value: Mapping[str, Mapping[str, Any]], *, available_refs: set[str]
) -> dict[str, Any]:
    if set(value) != set(_EVIDENCE_CLASSES):
        raise ValueError(f"standing must separate every evidence class: {_EVIDENCE_CLASSES}")
    result = {}
    for evidence_class in _EVIDENCE_CLASSES:
        item = value[evidence_class]
        required = {"status", "instrument", "evidence_refs"}
        if not isinstance(item, Mapping) or required - set(item):
            raise ValueError(f"{evidence_class} standing is incomplete")
        if item["status"] not in _STATUSES[evidence_class]:
            raise ValueError(f"unsupported {evidence_class} status: {item['status']!r}")
        evidence_refs = [str(item) for item in item["evidence_refs"]]
        unavailable = sorted(set(evidence_refs) - available_refs)
        if unavailable:
            raise ValueError(
                f"{evidence_class} standing names evidence outside this Experiment: "
                f"{unavailable}"
            )
        result[evidence_class] = {
            "evidence_class": evidence_class,
            "status": item["status"],
            "instrument": item["instrument"],
            "evidence_refs": evidence_refs,
            "scores": dict(item.get("scores", {})),
            "summary": str(item.get("summary", "")),
        }
    return result


def _approval_scope(value: Mapping[str, Any]) -> tuple[str, str, str, Mapping[str, Any]]:
    """Read the current approval contract or the historical Candidate 6 receipt."""
    candidate_id = value.get("candidate_id", value.get("game_candidate_id"))
    collection_hash = value.get("artifact_collection_hash")
    if collection_hash is None and isinstance(value.get("collection_manifest"), Mapping):
        collection_hash = value["collection_manifest"].get("sha256")
    decision = value.get("decision")
    scope = value.get("scope")
    if not all(isinstance(item, str) and item for item in (
        candidate_id, collection_hash, decision
    )) or not isinstance(scope, Mapping):
        raise ValueError("human approval scope is incomplete")
    return candidate_id, collection_hash, decision, scope


def _validate_approval(
    value: Mapping[str, Any], *, candidate_id: str, collection_ref: str
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("human approval scope is incomplete")
    approved_candidate, approved_collection, decision, _ = _approval_scope(value)
    if approved_candidate != candidate_id:
        raise ValueError("human approval names a different candidate")
    if approved_collection != collection_ref:
        raise ValueError("human approval names a different artifact collection")
    if decision not in {"approved", "approved-for-independent-measurement"}:
        raise ValueError("human approval decision or scope is invalid")
    return dict(value)


class ExperimentSpine:
    """Qualification journal and replaceable projections for a Workspace."""

    schema_version = "0.12"

    def __init__(self, workspace):
        self.workspace = workspace
        self.journal = workspace.qualification
        if any(
            event["event_type"] == "selected_rung_recorded"
            for event in self.journal.read()
        ):
            self.write_projection()

    def register_lineage_anchor(
        self,
        *,
        candidate_id: str,
        source_bytes: bytes,
        label: str = "",
        actor: str = "system:migration",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Register a historical parent without inventing a selected-rung claim."""
        if not candidate_id.strip() or not source_bytes:
            raise ValueError("lineage anchor requires a Candidate and source evidence")
        source_ref = self.workspace.store.put_bytes(source_bytes)
        event = self.journal.append(
            "lineage_anchor_recorded",
            actor=actor,
            payload={
                "schema_version": self.schema_version,
                "candidate_id": candidate_id,
                "label": label,
                "source_ref": source_ref,
            },
            object_refs=[source_ref],
            idempotency_key=idempotency_key or f"lineage-anchor:{candidate_id}",
        )
        self.workspace.rebuild_indexes()
        return event

    def record_selected_rung(
        self,
        *,
        candidate_id: str,
        parent_candidate_id: str | None,
        release_bytes: bytes,
        physical_package_bytes: bytes,
        artifact_collection_bytes: bytes,
        artifact_experiments: Mapping[str, bytes],
        approvals: tuple[bytes, ...],
        evidence_objects: Mapping[str, bytes],
        standings: Mapping[str, Mapping[str, Any]],
        claim_trace: Mapping[str, Any],
        required_propositions: tuple[str, ...],
        accessibility_contracts: tuple[Mapping[str, Any], ...],
        blockers: tuple[Mapping[str, Any], ...] = (),
        debt: tuple[Mapping[str, Any], ...] = (),
        invalidation: tuple[str, ...] = (),
        replay_requirements: tuple[str, ...] = (),
        actor: str = "human:operator",
        idempotency_key: str | None = None,
        export_path: str | Path | None = None,
    ) -> dict[str, Any]:
        if not candidate_id.strip():
            raise ValueError("selected rung requires candidate_id")
        prior = [event["payload"] for event in self.journal.read()
                 if event["event_type"] in {
                     "lineage_anchor_recorded", "selected_rung_recorded"
                 }]
        known = {item["candidate_id"] for item in prior}
        if parent_candidate_id is not None and parent_candidate_id not in known:
            raise ValueError("selected rung parent is not in this Experiment")
        release_ref = self.workspace.store.put_bytes(release_bytes)
        physical_ref = self.workspace.store.put_bytes(physical_package_bytes)
        if not artifact_collection_bytes:
            raise ValueError("selected rung requires exact artifact collection bytes")
        collection_ref = self.workspace.store.put_bytes(artifact_collection_bytes)
        experiment_refs = {
            name: self.workspace.store.put_bytes(data)
            for name, data in sorted(artifact_experiments.items())
        }
        approval_refs = []
        for data in approvals:
            try:
                item = json.loads(data)
            except (TypeError, json.JSONDecodeError) as exc:
                raise ValueError("human approval must be exact JSON bytes") from exc
            _validate_approval(
                item, candidate_id=candidate_id, collection_ref=collection_ref
            )
            approval_refs.append(self.workspace.store.put_bytes(data))
        evidence_refs = {
            name: self.workspace.store.put_bytes(data)
            for name, data in sorted(evidence_objects.items())
        }
        normalized_trace = validate_claim_trace(
            claim_trace, required_propositions=required_propositions
        )
        claim_trace_ref = self.workspace.store.put_json(normalized_trace)
        accessibility_refs = [
            self.workspace.store.put_json(validate_accessibility_contract(item))
            for item in accessibility_contracts
        ]
        available_refs = {
            release_ref, physical_ref, collection_ref, claim_trace_ref,
            *experiment_refs.values(), *approval_refs, *accessibility_refs,
            *evidence_refs.values(),
        }
        normalized_standings = _validate_standings(
            standings, available_refs=available_refs
        )
        payload = {
            "schema_version": self.schema_version,
            "candidate_id": candidate_id,
            "parent_candidate_id": parent_candidate_id,
            "release_ref": release_ref,
            "physical_package_ref": physical_ref,
            "artifact_collection_ref": collection_ref,
            "artifact_experiment_refs": experiment_refs,
            "evidence_refs": evidence_refs,
            "approval_refs": approval_refs,
            "standings": normalized_standings,
            "claim_trace_ref": claim_trace_ref,
            "accessibility_contract_refs": accessibility_refs,
            "blockers": [dict(item) for item in blockers],
            "debt": [dict(item) for item in debt],
            "invalidation": list(invalidation),
            "replay_requirements": list(replay_requirements),
        }
        record_ref = self.workspace.store.put_json(
            {"kind": "selected_rung", **payload}
        )
        object_refs = [
            record_ref, release_ref, physical_ref, collection_ref,
            claim_trace_ref, *experiment_refs.values(), *approval_refs,
            *accessibility_refs, *evidence_refs.values(),
        ]
        event = self.journal.append(
            "selected_rung_recorded",
            actor=actor,
            payload={**payload, "selected_rung_ref": record_ref},
            object_refs=object_refs,
            idempotency_key=idempotency_key or f"selected-rung:{candidate_id}",
        )
        self.workspace.rebuild_indexes()
        projection = self.write_projection()
        target = Path(export_path) if export_path else self.workspace.root.with_name(
            f"{self.workspace.root.name}-{candidate_id.replace(':', '-')}.ngw"
        )
        archive = self.workspace.export_archive(target)
        return {"event": event, "projection": projection, "archive": archive}

    def derive_projection(self) -> dict[str, Any]:
        events = [event for event in self.journal.read()
                  if event["event_type"] == "selected_rung_recorded"]
        if not events:
            raise ValueError("Experiment has no selected rung")
        current = events[-1]["payload"]
        verification = self.verify(include_projection=False)
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.workspace.manifest["workspace_id"],
            "selected_candidate": current["candidate_id"],
            "parent_candidate": current["parent_candidate_id"],
            "release_hash": current["release_ref"],
            "physical_package_hash": current["physical_package_ref"],
            "artifact_collection_hash": current["artifact_collection_ref"],
            "artifact_experiments": current["artifact_experiment_refs"],
            "evidence": current["evidence_refs"],
            "human_approvals": current["approval_refs"],
            "standings": current["standings"],
            "claim_trace": current["claim_trace_ref"],
            "accessibility_contracts": current["accessibility_contract_refs"],
            "blockers": current["blockers"],
            "non_blocking_debt": current["debt"],
            "invalidation": current["invalidation"],
            "replay_requirements": current["replay_requirements"],
            "journal_heads": dict(self.workspace.manifest["journal_heads"]),
            "verification": verification,
        }

    def write_projection(self) -> dict[str, Any]:
        projection = self.derive_projection()
        atomic_write(self.workspace.root / "current-standing.json", canonical_json(projection))
        lines = [
            f"# Current standing: {projection['selected_candidate']}", "",
            f"Parent: `{projection['parent_candidate']}`", "",
            "## Qualification", "",
        ]
        for name in _EVIDENCE_CLASSES:
            item = projection["standings"][name]
            lines.append(f"- **{name.replace('_', ' ')}:** `{item['status']}` "
                         f"(`{item['instrument']}`)")
        lines += ["", "## Blockers", ""]
        lines.extend(
            f"- **{item['code']}** ({item['evidence_class']}): {item['reason']}"
            for item in projection["blockers"]
        )
        if not projection["blockers"]:
            lines.append("- None recorded.")
        atomic_write(
            self.workspace.root / "current-standing.md",
            ("\n".join(lines) + "\n").encode(),
        )
        return projection

    def verify(self, *, include_projection: bool = True) -> dict[str, Any]:
        ok, failures = self.journal.verify()
        known: set[str] = set()
        for event in self.journal.read():
            if event.get("event_type") == "lineage_anchor_recorded":
                candidate = event.get("payload", {}).get("candidate_id")
                if not candidate or candidate in known:
                    failures.append("lineage anchor Candidate is missing or duplicated")
                known.add(candidate)
                for ref in event.get("object_refs", []):
                    if not self.workspace.store.verify(ref):
                        failures.append(
                            f"qualification object is missing or corrupt: {ref}"
                        )
                continue
            if event.get("event_type") != "selected_rung_recorded":
                failures.append(f"unsupported qualification event: {event.get('event_type')}")
                continue
            payload = event["payload"]
            parent = payload.get("parent_candidate_id")
            if parent is not None and parent not in known:
                failures.append(f"candidate {payload.get('candidate_id')} has broken parentage")
            known.add(payload.get("candidate_id"))
            for approval_ref in payload.get("approval_refs", []):
                try:
                    _validate_approval(
                        self.workspace.store.read_json(approval_ref),
                        candidate_id=payload["candidate_id"],
                        collection_ref=payload["artifact_collection_ref"],
                    )
                except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                    failures.append(f"human approval scope is invalid: {exc}")
            try:
                trace = self.workspace.store.read_json(payload["claim_trace_ref"])
                validate_claim_trace(
                    trace,
                    required_propositions=tuple(trace["required_propositions"]),
                )
                for ref in payload.get("accessibility_contract_refs", []):
                    validate_accessibility_contract(self.workspace.store.read_json(ref))
                available_refs = set(event.get("object_refs", []))
                _validate_standings(
                    payload["standings"], available_refs=available_refs
                )
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                failures.append(f"qualification evidence contract is invalid: {exc}")
            for ref in event.get("object_refs", []):
                if not self.workspace.store.verify(ref):
                    failures.append(f"qualification object is missing or corrupt: {ref}")
        if include_projection and any(
            event["event_type"] == "selected_rung_recorded"
            for event in self.journal.read()
        ):
            try:
                recorded = json.loads(
                    (self.workspace.root / "current-standing.json").read_bytes()
                )
                if recorded != self.derive_projection():
                    failures.append("current standing projection is stale")
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                failures.append(f"current standing projection is unreadable: {exc}")
        return {"ok": ok and not failures, "failures": failures,
                "events_verified": len(self.journal.read()) if ok else 0}
