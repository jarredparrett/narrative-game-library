"""High-level authoring Workspace with immutable lineage and derived heads."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any
import zipfile

from narrative_game.contracts.canonical import canonical_json, digest_bytes

from .io import atomic_write, file_mutex
from .journal import ConcurrencyConflict, Journal
from .store import ObjectStore, refs_in


class Workspace:
    """One operator-owned game lineage persisted outside source control."""

    schema_version = "0.1"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest_path = self.root / "workspace.json"
        self.store = ObjectStore(self.root / "objects")
        self.lineage = Journal(
            self.root / "journals" / "lineage.jsonl", journal_id="experiment-lineage"
        )
        self.operational = Journal(
            self.root / "journals" / "operational.jsonl", journal_id="operational-audit"
        )
        self.climb = Journal(
            self.root / "journals" / "climb.jsonl", journal_id="agentic-climb"
        )
        self.transaction_lock = self.root / "workspace.lock"
        if not self.lineage.read():
            raise FileNotFoundError(f"not a narrative game Workspace: {self.root}")
        derived = self._derive_manifest()
        if self.manifest_path.exists():
            try:
                current = json.loads(self.manifest_path.read_bytes())
            except json.JSONDecodeError:
                current = None
        else:
            current = None
        if current != derived:
            self._write_manifest(derived)
        self.manifest = derived

    @classmethod
    def create(cls, root: str | Path, *, workspace_id: str, actor: str = "human") -> "Workspace":
        root = Path(root)
        if root.exists() and (not root.is_dir() or any(root.iterdir())):
            raise FileExistsError(f"Workspace directory is not empty: {root}")
        if not workspace_id.strip():
            raise ValueError("workspace_id is required")
        root.mkdir(parents=True, exist_ok=True)
        lineage = Journal(root / "journals" / "lineage.jsonl", journal_id="experiment-lineage")
        lineage.append(
            "workspace_created",
            actor=actor,
            payload={"workspace_id": workspace_id, "schema_version": cls.schema_version},
            idempotency_key=f"workspace.create:{workspace_id}",
            expected_head=None,
        )
        return cls(root)

    @classmethod
    def open(cls, root: str | Path) -> "Workspace":
        return cls(root)

    @property
    def branches(self) -> dict[str, str]:
        return dict(self.manifest["branches"])

    @property
    def candidates(self) -> list[str]:
        return list(self.manifest["candidates"])

    def _derive_manifest(self) -> dict[str, Any]:
        events = self.lineage.read()
        workspace_events = [event for event in events if event["event_type"] == "workspace_created"]
        if len(workspace_events) != 1:
            raise ValueError("lineage must contain exactly one workspace_created event")
        branches: dict[str, str] = {}
        candidates = []
        for event in events:
            payload = event["payload"]
            if event["event_type"] in {"draft_committed", "draft_merged"}:
                branches[payload["branch"]] = payload["child"]
            elif event["event_type"] == "branch_created":
                branches[payload["branch"]] = payload["from_revision"]
            elif event["event_type"] == "candidate_frozen":
                candidates.append(payload["candidate"])
        return {
            "schema_version": self.schema_version,
            "workspace_id": workspace_events[0]["payload"]["workspace_id"],
            "branches": dict(sorted(branches.items())),
            "candidates": candidates,
            "journal_heads": {
                "climb": self.climb.head(),
                "lineage": events[-1]["event_hash"] if events else None,
                "operational": self.operational.head(),
            },
        }

    def _write_manifest(self, manifest: dict[str, Any]) -> None:
        atomic_write(self.manifest_path, canonical_json(manifest))

    def _refresh(self) -> None:
        self.manifest = self._derive_manifest()

    def _persist_projection(self) -> None:
        self._refresh()
        self._write_manifest(self.manifest)

    def _audit_rejection(
        self,
        *,
        operation: str,
        branch: str,
        expected: str | None,
        actual: str | None,
        idempotency_key: str,
    ) -> None:
        self.operational.append(
            "operation_rejected",
            actor="workspace",
            payload={
                "operation": operation,
                "branch": branch,
                "expected_head": expected,
                "actual_head": actual,
                "reason": "stale_head",
            },
            idempotency_key=f"rejected:{idempotency_key}:{expected}:{actual}",
        )

    def commit_draft(
        self,
        *,
        branch: str,
        expected_head: str | None,
        data: dict[str, Any],
        reason: str,
        actor: str,
        component_lock: dict[str, Any],
        operation_receipt: dict[str, Any],
        idempotency_key: str,
        additional_parents: tuple[str, ...] = (),
    ) -> str:
        """Create one immutable Draft Revision and advance exactly one branch."""
        if not branch.strip() or not reason.strip():
            raise ValueError("branch and reason are required")
        with file_mutex(self.transaction_lock):
            self._refresh()
            lock_ref = self.store.put_json(
                {"schema_version": "0.1", "kind": "component_lock", **component_lock}
            )
            receipt_ref = self.store.put_json(
                {"schema_version": "0.1", "kind": "operation_receipt", **operation_receipt}
            )
            parents = tuple(item for item in (expected_head, *additional_parents) if item)
            for parent in parents:
                if not self.store.verify(parent):
                    raise ValueError(f"draft parent is unavailable: {parent}")
            revision = {
                "schema_version": "0.1",
                "kind": "draft_revision",
                "parents": list(parents),
                "data": data,
                "reason": reason,
                "component_lock": lock_ref,
                "operation_receipt": receipt_ref,
            }
            child = self.store.put_json(revision)
            event_type = "draft_merged" if additional_parents else "draft_committed"
            event_payload = {
                "branch": branch,
                "expected_head": expected_head,
                "parents": list(parents),
                "child": child,
                "reason": reason,
            }
            existing = self.lineage.event_for_key(idempotency_key)
            if existing is not None:
                event = self.lineage.append(
                    event_type,
                    actor=actor,
                    payload=event_payload,
                    object_refs=[child, lock_ref, receipt_ref, *parents],
                    idempotency_key=idempotency_key,
                )
                return event["payload"]["child"]
            actual = self.manifest["branches"].get(branch)
            if actual != expected_head:
                self._audit_rejection(
                    operation=event_type,
                    branch=branch,
                    expected=expected_head,
                    actual=actual,
                    idempotency_key=idempotency_key,
                )
                self._persist_projection()
                raise ConcurrencyConflict(
                    f"Draft Head changed for {branch!r}: expected {expected_head!r}, found {actual!r}"
                )
            self.lineage.append(
                event_type,
                actor=actor,
                payload=event_payload,
                object_refs=[child, lock_ref, receipt_ref, *parents],
                idempotency_key=idempotency_key,
            )
            self._persist_projection()
            return child

    def create_branch(
        self,
        *,
        branch: str,
        from_revision: str,
        actor: str,
        reason: str,
        idempotency_key: str,
    ) -> str:
        with file_mutex(self.transaction_lock):
            self._refresh()
            if not self.store.verify(from_revision):
                raise ValueError("branch source revision is unavailable")
            existing = self.lineage.event_for_key(idempotency_key)
            payload = {"branch": branch, "from_revision": from_revision, "reason": reason}
            if existing is not None:
                return self.lineage.append(
                    "branch_created",
                    actor=actor,
                    payload=payload,
                    object_refs=[from_revision],
                    idempotency_key=idempotency_key,
                )["payload"]["from_revision"]
            if branch in self.manifest["branches"]:
                raise ConcurrencyConflict(f"branch already exists: {branch}")
            self.lineage.append(
                "branch_created",
                actor=actor,
                payload=payload,
                object_refs=[from_revision],
                idempotency_key=idempotency_key,
            )
            self._persist_projection()
            return from_revision

    def freeze_candidate(
        self,
        *,
        branch: str,
        expected_head: str,
        actor: str,
        idempotency_key: str,
    ) -> str:
        with file_mutex(self.transaction_lock):
            self._refresh()
            revision = self.store.read_json(expected_head)
            candidate = self.store.put_json(
                {
                    "schema_version": "0.1",
                    "kind": "candidate",
                    "draft_revision": expected_head,
                    "component_lock": revision["component_lock"],
                    "operation_receipt": revision["operation_receipt"],
                }
            )
            payload = {"branch": branch, "draft_revision": expected_head, "candidate": candidate}
            existing = self.lineage.event_for_key(idempotency_key)
            if existing is not None:
                event = self.lineage.append(
                    "candidate_frozen",
                    actor=actor,
                    payload=payload,
                    object_refs=[expected_head, candidate],
                    idempotency_key=idempotency_key,
                )
                return event["payload"]["candidate"]
            actual = self.manifest["branches"].get(branch)
            if actual != expected_head:
                self._audit_rejection(
                    operation="candidate_frozen",
                    branch=branch,
                    expected=expected_head,
                    actual=actual,
                    idempotency_key=idempotency_key,
                )
                self._persist_projection()
                raise ConcurrencyConflict("candidate freeze targeted a stale Draft Head")
            event = self.lineage.append(
                "candidate_frozen",
                actor=actor,
                payload=payload,
                object_refs=[expected_head, candidate],
                idempotency_key=idempotency_key,
            )
            self._persist_projection()
            return event["payload"]["candidate"]

    def rebuild_indexes(self) -> dict[str, Any]:
        with file_mutex(self.transaction_lock):
            manifest = self._derive_manifest()
            self._write_manifest(manifest)
            self.manifest = manifest
            return manifest

    def lineage_report(self) -> str:
        lines = [
            f"# Workspace lineage: {self.manifest['workspace_id']}",
            "",
            f"Lineage head: `{self.manifest['journal_heads']['lineage']}`",
            "",
        ]
        for event in self.lineage.read():
            payload = event["payload"]
            summary = payload.get("reason") or event["event_type"].replace("_", " ")
            lines.extend(
                [
                    f"## {event['sequence']}. {event['event_type']}",
                    "",
                    f"- Actor: `{event['actor']}`",
                    f"- Why: {summary}",
                    f"- Event: `{event['event_hash']}`",
                ]
            )
            if "branch" in payload:
                lines.append(f"- Branch: `{payload['branch']}`")
            if "child" in payload:
                lines.append(f"- Result: `{payload['child']}`")
            if "candidate" in payload:
                lines.append(f"- Candidate: `{payload['candidate']}`")
            lines.append("")
        return "\n".join(lines)

    def verify(self) -> dict[str, Any]:
        failures = []
        lineage_ok, lineage_failures = self.lineage.verify()
        operational_ok, operational_failures = self.operational.verify()
        climb_ok, climb_failures = self.climb.verify()
        failures.extend(f"lineage: {item}" for item in lineage_failures)
        failures.extend(f"operational: {item}" for item in operational_failures)
        failures.extend(f"climb: {item}" for item in climb_failures)
        objects_ok, corrupt = self.store.verify_all()
        failures.extend(f"corrupt object: {ref}" for ref in corrupt)
        referenced = set()
        for journal in (self.lineage, self.operational, self.climb):
            for event in journal.read():
                referenced.update(event.get("object_refs", []))
        pending = list(referenced)
        checked = set()
        while pending:
            ref = pending.pop()
            if ref in checked:
                continue
            if not self.store.verify(ref):
                failures.append(f"missing referenced object: {ref}")
                continue
            checked.add(ref)
            try:
                pending.extend(refs_in(self.store.read_json(ref)))
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
        derived = self._derive_manifest()
        try:
            recorded = json.loads(self.manifest_path.read_bytes())
        except (OSError, json.JSONDecodeError) as exc:
            recorded = None
            failures.append(f"manifest unreadable: {exc}")
        if recorded != derived:
            failures.append("manifest projection does not match journals")
        return {
            "ok": not failures,
            "failures": failures,
            "objects_verified": len(checked),
            "lineage_events": len(self.lineage.read()) if lineage_ok else 0,
            "operational_events": len(self.operational.read()) if operational_ok else 0,
            "climb_events": len(self.climb.read()) if climb_ok else 0,
            "all_objects_intact": objects_ok,
        }

    def export_archive(self, destination: str | Path) -> dict[str, Any]:
        verification = self.verify()
        if not verification["ok"]:
            raise ValueError(f"cannot archive an invalid Workspace: {verification['failures']}")
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        files = [
            path
            for path in self.root.rglob("*")
            if path.is_file()
            and not path.name.endswith((".lock", ".tmp"))
            and path != destination
        ]
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as archive:
            for path in sorted(files, key=lambda item: item.relative_to(self.root).as_posix()):
                relative = path.relative_to(self.root).as_posix()
                info = zipfile.ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED
                info.external_attr = 0o600 << 16
                archive.writestr(info, path.read_bytes())
        data = destination.read_bytes()
        return {"archive": str(destination), "sha256": digest_bytes(data), "bytes": len(data)}

    @classmethod
    def import_archive(cls, archive_path: str | Path, destination: str | Path) -> "Workspace":
        archive_path = Path(archive_path)
        destination = Path(destination)
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            raise FileExistsError("archive destination is not empty")
        destination.mkdir(parents=True, exist_ok=True)
        root = destination.resolve()
        with zipfile.ZipFile(archive_path, "r") as archive:
            for info in archive.infolist():
                relative = PurePosixPath(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"unsafe archive member: {info.filename}")
                target = destination.joinpath(*relative.parts)
                if not target.resolve().is_relative_to(root):
                    raise ValueError(f"unsafe archive member: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    atomic_write(target, archive.read(info))
        workspace = cls.open(destination)
        verification = workspace.verify()
        if not verification["ok"]:
            raise ValueError(f"imported Workspace failed verification: {verification['failures']}")
        return workspace
