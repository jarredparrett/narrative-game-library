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
from .evidence import (
    JOURNAL_IDS,
    ClaimManifest,
    WorkspaceCheckpoint,
    deterministic_zip,
    journal_prefix,
    transitive_object_closure,
    typed_evidence_object,
    verify_claim_capsule_bytes,
)


class Workspace:
    """One operator-owned game lineage persisted outside source control."""

    schema_version = "0.2"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.manifest_path = self.root / "workspace.json"
        self.lineage = Journal(
            self.root / "journals" / "lineage.jsonl", journal_id="experiment-lineage"
        )
        lineage_events = self.lineage.read()
        if not lineage_events:
            raise FileNotFoundError(f"not a narrative game Workspace: {self.root}")
        workspace_events = [
            event for event in lineage_events if event["event_type"] == "workspace_created"
        ]
        if len(workspace_events) != 1:
            raise ValueError("lineage must contain exactly one workspace_created event")
        represented_schema = str(workspace_events[0]["payload"].get("schema_version", "0.1"))
        object_root = (
            self.root / "objects"
            if represented_schema == "0.1"
            else self.root / "objects" / "sha256"
        )
        self.store = ObjectStore(object_root)
        self.operational = Journal(
            self.root / "journals" / "operational.jsonl", journal_id="operational-audit"
        )
        self.climb = Journal(
            self.root / "journals" / "climb.jsonl", journal_id="agentic-climb"
        )
        self.analysis = Journal(
            self.root / "journals" / "analysis.jsonl", journal_id="difficulty-analysis"
        )
        self.qualification = Journal(
            self.root / "journals" / "qualification.jsonl",
            journal_id="game-qualification",
        )
        self.access = Journal(
            self.root / "journals" / "access.jsonl", journal_id="evidence-access"
        )
        self.transaction_lock = self.root / "workspace.lock"
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

    @property
    def journals(self) -> dict[str, Journal]:
        return {
            "lineage": self.lineage,
            "operational": self.operational,
            "climb": self.climb,
            "analysis": self.analysis,
            "qualification": self.qualification,
            "access": self.access,
        }

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
            elif event["event_type"] == "branch_selected":
                branches[payload["branch"]] = payload["selected_revision"]
            elif event["event_type"] == "candidate_frozen":
                candidates.append(payload["candidate"])
        return {
            "schema_version": self.schema_version,
            "workspace_id": workspace_events[0]["payload"]["workspace_id"],
            "branches": dict(sorted(branches.items())),
            "candidates": candidates,
            "journal_heads": {
                "access": self.access.head(),
                "analysis": self.analysis.head(),
                "climb": self.climb.head(),
                "lineage": events[-1]["event_hash"] if events else None,
                "operational": self.operational.head(),
                "qualification": self.qualification.head(),
            },
        }

    def put_evidence_object(
        self,
        *,
        object_kind: str,
        object_schema: str,
        value: dict[str, Any],
        producer: str,
        verifier: str,
    ) -> str:
        """Persist one immutable typed Evidence Object without ambient inputs."""
        return self.store.put_json(
            typed_evidence_object(
                object_kind=object_kind,
                object_schema=object_schema,
                value=value,
                producer=producer,
                verifier=verifier,
            )
        )

    def create_checkpoint(self) -> str:
        """Pin one coherent verified head across every independent Journal."""
        with file_mutex(self.transaction_lock):
            heads = {}
            for name, journal in self.journals.items():
                ok, failures = journal.verify()
                if not ok:
                    raise ValueError(f"cannot checkpoint invalid {name} Journal: {failures}")
                events = journal.read()
                heads[name] = {
                    "journal_id": journal.journal_id,
                    "sequence": len(events),
                    "head": events[-1]["event_hash"] if events else None,
                }
            if any(
                self.journals[name].head() != value["head"]
                for name, value in heads.items()
            ):
                raise ConcurrencyConflict("a Journal advanced while creating the Checkpoint")
            checkpoint = WorkspaceCheckpoint(self.manifest["workspace_id"], heads)
            ref = self.store.put_json(checkpoint.to_mapping())
            if ref != checkpoint.checkpoint_ref:
                raise ValueError("Checkpoint content identity mismatch")
            path = self.root / "checkpoints" / f"{ref[7:]}.json"
            if path.exists() and path.read_bytes() != canonical_json(checkpoint.to_mapping()):
                raise ValueError("Checkpoint file conflicts with immutable identity")
            atomic_write(path, canonical_json(checkpoint.to_mapping()))
            return ref

    def verify_checkpoint(self, checkpoint_ref: str) -> tuple[str, ...]:
        findings = []
        if not self.store.verify(checkpoint_ref):
            return (f"missing or corrupt Checkpoint: {checkpoint_ref}",)
        try:
            checkpoint = WorkspaceCheckpoint.from_mapping(
                self.store.read_json(checkpoint_ref)
            )
        except (KeyError, TypeError, ValueError) as exc:
            return (f"Checkpoint unreadable: {exc}",)
        if checkpoint.checkpoint_ref != checkpoint_ref:
            findings.append("Checkpoint identity mismatch")
        if checkpoint.workspace_id != self.manifest["workspace_id"]:
            findings.append("Checkpoint names another Workspace")
        for name, expected in checkpoint.journal_heads.items():
            events = self.journals[name].read()
            if int(expected["sequence"]) > len(events):
                findings.append(f"{name} Checkpoint sequence exceeds Journal")
                continue
            sequence = int(expected["sequence"])
            observed = events[sequence - 1]["event_hash"] if sequence else None
            if observed != expected["head"]:
                findings.append(f"{name} Checkpoint head is not the named Journal prefix")
        path = self.root / "checkpoints" / f"{checkpoint_ref[7:]}.json"
        if path.exists() and digest_bytes(path.read_bytes()) != checkpoint_ref:
            findings.append("Checkpoint projection bytes differ from object identity")
        return tuple(findings)

    def create_claim_manifest(
        self,
        *,
        claim_id: str,
        checkpoint_ref: str,
        root_refs: tuple[str, ...],
        schema_refs: tuple[str, ...],
        verifier_refs: tuple[str, ...],
        actor: str,
        idempotency_key: str,
    ) -> str:
        """Bind one reportable claim to its complete immutable evidence closure."""
        if not claim_id.strip() or not root_refs or not schema_refs or not verifier_refs:
            raise ValueError("claim identity, roots, schemas, and verifiers are required")
        with file_mutex(self.transaction_lock):
            checkpoint_findings = self.verify_checkpoint(checkpoint_ref)
            if checkpoint_findings:
                raise ValueError(f"invalid Claim Checkpoint: {checkpoint_findings}")
            for ref, expected_kind in (
                *((ref, "schema_bundle") for ref in schema_refs),
                *((ref, "verifier_bundle") for ref in verifier_refs),
            ):
                value = self.store.read_json(ref)
                if value.get("kind") != "evidence_object" or value.get("object_kind") != expected_kind:
                    raise ValueError(f"Claim Manifest requires a typed {expected_kind}: {ref}")
            base = tuple(
                sorted({checkpoint_ref, *root_refs, *schema_refs, *verifier_refs})
            )
            closure = transitive_object_closure(self.store, base)
            manifest = ClaimManifest(
                claim_id,
                checkpoint_ref,
                tuple(sorted(set(root_refs))),
                tuple(sorted(set(schema_refs))),
                tuple(sorted(set(verifier_refs))),
                closure,
            )
            manifest_ref = self.store.put_json(manifest.to_mapping())
            event = self.qualification.append(
                "claim_manifest_created",
                actor=actor,
                payload={
                    "claim_id": claim_id,
                    "claim_manifest_ref": manifest_ref,
                    "checkpoint_ref": checkpoint_ref,
                },
                object_refs=(manifest_ref, *closure),
                idempotency_key=idempotency_key,
            )
            self._persist_projection()
            return str(event["payload"]["claim_manifest_ref"])

    def verify_claim_manifest(self, manifest_ref: str) -> tuple[str, ...]:
        findings = []
        if not self.store.verify(manifest_ref):
            return (f"missing or corrupt Claim Manifest: {manifest_ref}",)
        try:
            manifest = ClaimManifest.from_mapping(self.store.read_json(manifest_ref))
        except (KeyError, TypeError, ValueError) as exc:
            return (f"Claim Manifest unreadable: {exc}",)
        if manifest.manifest_ref != manifest_ref:
            findings.append("Claim Manifest identity mismatch")
        findings.extend(self.verify_checkpoint(manifest.checkpoint_ref))
        base = tuple(
            sorted(
                {
                    manifest.checkpoint_ref,
                    *manifest.root_refs,
                    *manifest.schema_refs,
                    *manifest.verifier_refs,
                }
            )
        )
        try:
            closure = transitive_object_closure(self.store, base)
        except ValueError as exc:
            findings.append(str(exc))
        else:
            if closure != manifest.object_refs:
                findings.append("Claim Manifest closure is incomplete or contains extras")
        return tuple(findings)

    def export_claim_capsule(
        self,
        manifest_ref: str,
        destination: str | Path,
    ) -> dict[str, Any]:
        """Export one Claim Manifest closure with exact Journal prefix proofs."""
        findings = self.verify_claim_manifest(manifest_ref)
        if findings:
            raise ValueError(f"cannot export invalid Claim Manifest: {findings}")
        manifest = ClaimManifest.from_mapping(self.store.read_json(manifest_ref))
        checkpoint = WorkspaceCheckpoint.from_mapping(
            self.store.read_json(manifest.checkpoint_ref)
        )
        object_refs = tuple(sorted({manifest_ref, *manifest.object_refs}))
        descriptor = {
            "schema_version": "claim-capsule.1",
            "claim_manifest_ref": manifest_ref,
            "checkpoint_ref": manifest.checkpoint_ref,
            "object_refs": list(object_refs),
            "journal_heads": {
                name: dict(value)
                for name, value in sorted(checkpoint.journal_heads.items())
            },
        }
        members = {"capsule.json": canonical_json(descriptor)}
        for ref in object_refs:
            members[f"objects/sha256/{ref[7:9]}/{ref[9:]}"] = self.store.read_bytes(ref)
        for name, expected in checkpoint.journal_heads.items():
            events = journal_prefix(self.journals[name].read(), expected["head"])
            members[f"journals/{name}.jsonl"] = b"".join(
                canonical_json(event) + b"\n" for event in events
            )
        data = deterministic_zip(members)
        destination = Path(destination)
        atomic_write(destination, data)
        return {
            "capsule": str(destination),
            "sha256": digest_bytes(data),
            "bytes": len(data),
            "claim_manifest_ref": manifest_ref,
        }

    @staticmethod
    def verify_claim_capsule(path: str | Path) -> dict[str, Any]:
        try:
            value = Path(path).read_bytes()
        except OSError as exc:
            return {"ok": False, "failures": [f"capsule unreadable: {exc}"]}
        return verify_claim_capsule_bytes(value)

    def migrate_legacy_evidence(
        self,
        *,
        actor: str,
        idempotency_key: str,
    ) -> str:
        """Append a receipt from Workspace 0.1 without rewriting its evidence."""
        workspace_event = next(
            event for event in self.lineage.read() if event["event_type"] == "workspace_created"
        )
        if workspace_event["payload"].get("schema_version") != "0.1":
            raise ValueError("Workspace is not a legacy 0.1 source")
        existing = self.operational.event_for_key(idempotency_key)
        if existing is not None:
            return str(existing["payload"]["migration_receipt_ref"])
        old_heads = {
            name: journal.head()
            for name, journal in self.journals.items()
            if name not in {"analysis", "access"}
        }
        old_refs = tuple(self.store.references())
        source_ref = self.put_evidence_object(
            object_kind="workspace_schema_snapshot",
            object_schema="workspace.0.1",
            value={
                "workspace_id": self.manifest["workspace_id"],
                "journal_heads": old_heads,
                "object_refs": list(old_refs),
            },
            producer="workspace-migrator.0.2",
            verifier="workspace-snapshot-verifier.1",
        )
        migrated_ref = self.put_evidence_object(
            object_kind="workspace_schema_snapshot",
            object_schema="workspace.0.2",
            value={
                "workspace_id": self.manifest["workspace_id"],
                "source_object_ref": source_ref,
                "journal_ids": dict(sorted(JOURNAL_IDS.items())),
            },
            producer="workspace-migrator.0.2",
            verifier="workspace-snapshot-verifier.1",
        )
        receipt_ref = self.put_evidence_object(
            object_kind="migration_receipt",
            object_schema="workspace-migration.1",
            value={
                "source_object_ref": source_ref,
                "migrated_object_ref": migrated_ref,
                "migrator": "workspace-migrator.0.2",
                "warnings": [],
                "information_loss": [],
            },
            producer="workspace-migrator.0.2",
            verifier="workspace-migration-verifier.1",
        )
        event = self.operational.append(
            "workspace_schema_migrated",
            actor=actor,
            payload={
                "from_schema": "0.1",
                "to_schema": "0.2",
                "migration_receipt_ref": receipt_ref,
            },
            object_refs=(source_ref, migrated_ref, receipt_ref, *old_refs),
            idempotency_key=idempotency_key,
        )
        self._persist_projection()
        return str(event["payload"]["migration_receipt_ref"])

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

    def select_revision(
        self,
        *,
        branch: str,
        expected_head: str,
        selected_revision: str,
        selection_ref: str,
        actor: str,
        idempotency_key: str,
    ) -> str:
        """Move a development branch to the immutable Draft chosen by evidence.

        No revision is deleted or rewritten. The append-only selection event is
        the auditable reason a rejected child stops being the next round's parent.
        """
        with file_mutex(self.transaction_lock):
            self._refresh()
            if not self.store.verify(selected_revision):
                raise ValueError("selected Draft Revision is unavailable")
            if not self.store.verify(selection_ref):
                raise ValueError("Selection Decision record is unavailable")
            payload = {
                "branch": branch,
                "expected_head": expected_head,
                "selected_revision": selected_revision,
                "selection_ref": selection_ref,
            }
            existing = self.lineage.event_for_key(idempotency_key)
            if existing is not None:
                event = self.lineage.append(
                    "branch_selected",
                    actor=actor,
                    payload=payload,
                    object_refs=[selected_revision, selection_ref],
                    idempotency_key=idempotency_key,
                )
                return event["payload"]["selected_revision"]
            actual = self.manifest["branches"].get(branch)
            if actual != expected_head:
                self._audit_rejection(
                    operation="branch_selected",
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
                "branch_selected",
                actor=actor,
                payload=payload,
                object_refs=[selected_revision, selection_ref],
                idempotency_key=idempotency_key,
            )
            self._persist_projection()
            return selected_revision

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
        journal_status = {}
        for name, journal in self.journals.items():
            ok, journal_failures = journal.verify()
            journal_status[name] = (ok, len(journal.read()) if ok else 0)
            failures.extend(f"{name}: {item}" for item in journal_failures)
        objects_ok, corrupt = self.store.verify_all()
        failures.extend(f"corrupt object: {ref}" for ref in corrupt)
        referenced = set()
        for journal in self.journals.values():
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
        checkpoint_root = self.root / "checkpoints"
        checkpoint_paths = (
            sorted(checkpoint_root.glob("*.json")) if checkpoint_root.exists() else ()
        )
        for path in checkpoint_paths:
            ref = "sha256:" + path.stem
            if not self.store.verify(ref) or self.store.read_bytes(ref) != path.read_bytes():
                failures.append(f"Checkpoint projection has no matching object: {path.name}")
                continue
            failures.extend(self.verify_checkpoint(ref))
        import_root = self.root / "imports"
        import_paths = sorted(import_root.glob("*.json")) if import_root.exists() else ()
        for path in import_paths:
            ref = "sha256:" + path.stem
            if not self.store.verify(ref) or self.store.read_bytes(ref) != path.read_bytes():
                failures.append(f"Import Receipt has no matching object: {path.name}")
                continue
            value = self.store.read_json(ref)
            if (
                value.get("kind") != "evidence_object"
                or value.get("object_kind") != "import_receipt"
            ):
                failures.append(f"Import Receipt has the wrong type: {path.name}")
        for event in self.qualification.read():
            if event["event_type"] == "claim_manifest_created":
                manifest_ref = event["payload"].get("claim_manifest_ref", "")
                failures.extend(self.verify_claim_manifest(manifest_ref))
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
            **{
                f"{name}_events": count if ok else 0
                for name, (ok, count) in sorted(journal_status.items())
            },
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
        archive_bytes = archive_path.read_bytes()
        archive_ref = digest_bytes(archive_bytes)
        destination = Path(destination)
        if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
            raise FileExistsError("archive destination is not empty")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.rmdir()
        quarantine = destination.with_name(
            f"{destination.name}.import-{archive_ref[7:19]}"
        )
        if quarantine.exists():
            raise FileExistsError("archive quarantine already exists")
        quarantine.mkdir()
        root = quarantine.resolve()
        with zipfile.ZipFile(archive_path, "r") as archive:
            for info in archive.infolist():
                relative = PurePosixPath(info.filename)
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"unsafe archive member: {info.filename}")
                target = quarantine.joinpath(*relative.parts)
                if not target.resolve().is_relative_to(root):
                    raise ValueError(f"unsafe archive member: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    atomic_write(target, archive.read(info))
        workspace = cls.open(quarantine)
        verification = workspace.verify()
        if not verification["ok"]:
            raise ValueError(f"imported Workspace failed verification: {verification['failures']}")
        source_heads = dict(workspace.manifest["journal_heads"])
        receipt_ref = workspace.put_evidence_object(
            object_kind="import_receipt",
            object_schema="workspace-import.1",
            value={
                "archive_ref": archive_ref,
                "source_workspace_id": workspace.manifest["workspace_id"],
                "source_journal_heads": source_heads,
                "operation": "verified-workspace-import",
            },
            producer="workspace-importer.0.2",
            verifier="workspace-archive-verifier.1",
        )
        receipt_path = workspace.root / "imports" / f"{receipt_ref[7:]}.json"
        atomic_write(receipt_path, workspace.store.read_bytes(receipt_ref))
        final = workspace.verify()
        if not final["ok"]:
            raise ValueError(f"import receipt failed verification: {final['failures']}")
        quarantine.replace(destination)
        return cls.open(destination)
