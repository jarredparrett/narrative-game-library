"""End-to-end worked scenario: authoring, forge, release, play, and export."""

from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

from verismill import AgentRun, Experiment, ModelConfig

from narrative_game.adapters import VerismillArtifactForge
from narrative_game.authoring import parse_game_definition
from narrative_game.compiler import (
    Candidate,
    GameRelease,
    MaterialInput,
    compile_candidate,
    freeze_candidate,
    reference_component_lock,
)
from narrative_game.contracts import ArtifactRequest, canonical_json, digest_bytes, digest_json
from narrative_game.physical import PhysicalExport, export_physical
from narrative_game.runtime import (
    Actor,
    ActorBinding,
    AuthorizationContext,
    SessionCommand,
    SessionHistory,
    ViewerGrant,
    apply_command,
    create_session,
    host_snapshot,
    replay,
    seat_snapshot,
)
from narrative_game.workspace import Workspace


UPSTREAM_COMMIT = "c2b02fdf2faa28ac869dafcd119bf65d1a32e87c"
DEFAULT_SOURCE = Path(__file__).resolve().parent / "examples" / "ashwood-ledger"


@dataclass(frozen=True)
class WorkedBuild:
    source: dict[str, Any]
    candidate: Candidate
    artifact_hash: str
    artifact_attestation: dict[str, Any]


@dataclass(frozen=True)
class WorkedResult:
    build: WorkedBuild
    release: GameRelease
    physical: PhysicalExport
    session: SessionHistory
    workspace: Workspace
    output_root: Path
    summary: dict[str, Any]


def _agent_run() -> AgentRun:
    parsed = {
        "decision": "propose",
        "summary": "emit the pinned 1997 Madison deed for The Ashwood Ledger",
    }
    return AgentRun(
        run_id="ashwood-builder-run",
        agent_id="artifact-forge-builder",
        context_id="ashwood-ledger-candidate",
        role="builder",
        model=ModelConfig(
            provider="fixture",
            model="recorded-human-direction",
            resolved_model="recorded-human-direction-v1",
        ),
        prompt_hash=digest_bytes(b"ashwood ledger artifact forge request"),
        input_hashes={"canonical_facts": digest_bytes(b"1997-10-17|425000|Madison NJ")},
        raw_response=json.dumps(parsed, sort_keys=True),
        parsed_output=parsed,
    )


def _forge_deed(root: Path, *, artifact_pins: dict[str, Any] | None = None):
    experiment = Experiment.create(
        root,
        request="Forge the 1997 Madison deed used as resolution evidence in The Ashwood Ledger",
        experiment_id="ashwood_ledger_artifact",
        clock=lambda: 1_700_000_000,
    )
    experiment.freeze_preparation(
        research={
            "sources": [
                {
                    "id": "verismill-deed-nj-1997",
                    "kind": "seeded-document-class",
                    "provenance": {
                        "repository": "jarredparrett/verismill-lean",
                        "commit": UPSTREAM_COMMIT,
                        "document_class": "deed_nj_1997",
                    },
                }
            ],
            "coverage": {
                "execution_date": "pinned",
                "consideration": "pinned",
                "notary_identity": "pinned",
                "accessible_fields": "public artifact manifest",
                "visual_form": "existing measured emitter",
            },
        },
        rubric={
            "version": "ashwood-artifact.2",
            "scorer": "absolute-v0.3",
            "dimensions": [
                {
                    "id": "artifact_boundary",
                    "description": "Exact bytes and measurement cross only the public Artifact Result facade",
                    "anchors": {"0": "unverified bytes", "100": "verified result and attestation"},
                }
            ],
            "acceptance": {"rules": [{"metric": "overall_min", "operator": ">=", "value": 80}]},
        },
        requirements=[
            {
                "id": "artifact.exact-date",
                "property": "the displayed execution date derives from the pinned canonical fact",
                "failure": "the game and deed disagree about the represented execution date",
            },
            {
                "id": "artifact.exact-consideration",
                "property": "the displayed consideration derives from the pinned canonical fact",
                "failure": "the game and deed disagree about consideration",
            },
            {
                "id": "artifact.public-boundary",
                "property": "artifact bytes, provenance, measurement, and attestation cross the public facade",
                "failure": "the game reads private Verismill or Mattermill state",
            },
            {
                "id": "artifact.acknowledgment-number-agreement",
                "property": "acknowledgment grammar agrees with the displayed signer count",
                "failure": "a single grantor is described with plural signer language",
            },
            {
                "id": "artifact.pinned-notary-identity",
                "property": "the displayed notary identity derives from a caller pin",
                "failure": "a sampled notary collides with a narrative character",
            },
            {
                "id": "artifact.public-display-facts",
                "property": "the public manifest exposes every displayed fact required by an accessible rendition",
                "failure": "the game must duplicate or infer a deed field from private emitter state",
            },
        ],
    )
    builder_run = experiment.record_agent_run(_agent_run())
    pins = {
        "execution_date": "1997-10-17",
        "consideration": 425000,
        "grantor_married": True,
        "notary_name": "Elise North",
        "new_construction": False,
        "partial_exemption": "none",
    }
    pins.update(artifact_pins or {})
    request = ArtifactRequest(
        artifact_id="madison-deed-1997",
        document_class="deed_nj_1997",
        seed=1997,
        pins=pins,
        fact_references=("deed-date", "deed-consideration"),
        narrative_function="Resolution evidence for the concealed Quillstone transaction",
        permitted_disclosures=("host", "seat:avery", "seat:blake"),
    )
    return VerismillArtifactForge().forge(
        experiment,
        request,
        builder_run=builder_run,
        explanation={
            "observation": "the resolution requires a legally structured 1997 Madison deed",
            "requirement": "artifact.public-boundary",
            "change": "materialize the existing seeded deed class with two canonical fact pins",
            "evidence": f"verismill commit {UPSTREAM_COMMIT}",
        },
    )


def _accessible_deed_text(display_facts: Mapping[str, Any]) -> bytes:
    """Derive the in-fiction reading copy from the emitter's public fact projection."""
    required = {
        "instrument_type",
        "county",
        "municipality",
        "state",
        "street",
        "zip",
        "block",
        "lot",
        "execution_date",
        "consideration",
        "grantor_name",
        "grantor_address",
        "grantee_name",
        "grantee_address",
        "grantor_spouse_name",
        "signatory_names",
        "acknowledgment_names",
        "grantor_married",
        "new_construction",
        "partial_exemption",
        "prior_book",
        "prior_page",
        "notary_name",
    }
    missing = required - set(display_facts)
    if missing:
        raise ValueError(f"artifact display facts omit accessible fields: {sorted(missing)}")
    married = "married" if display_facts["grantor_married"] else "unmarried"
    construction = "yes" if display_facts["new_construction"] else "no"
    consideration = f"${int(display_facts['consideration']):,.2f}"
    execution_date = dt.date.fromisoformat(str(display_facts["execution_date"]))
    spouse = display_facts["grantor_spouse_name"] or "None"
    signatories = ", ".join(str(name) for name in display_facts["signatory_names"])
    acknowledgers = ", ".join(
        str(name) for name in display_facts["acknowledgment_names"]
    )
    return (
        "VALE HOUSE ARCHIVE\n"
        "READING COPY OF RECORDED INSTRUMENT\n\n"
        "Prepared for readers who cannot use the marked facsimile. Preserve this "
        "sheet with the facsimile in the Quillstone file.\n\n"
        f"Instrument type: {display_facts['instrument_type']}\n"
        f"County: {display_facts['county']} County, New Jersey\n"
        f"Municipality: Borough of {display_facts['municipality']}\n"
        f"Property address: {display_facts['street']}, {display_facts['municipality']}, "
        f"New Jersey {display_facts['zip']}\n"
        f"Tax map reference: Block {display_facts['block']}, Lot {display_facts['lot']}\n"
        f"Grantor: {display_facts['grantor_name']}\n"
        f"Grantor address: {display_facts['grantor_address']}\n"
        f"Grantee: {display_facts['grantee_name']}\n"
        f"Grantee address: {display_facts['grantee_address']}\n"
        f"Joining spouse: {spouse}\n"
        f"Execution signatories: {signatories}\n"
        f"Persons acknowledged: {acknowledgers}\n"
        f"Execution date: {execution_date:%B %d, %Y}.\n"
        f"Consideration stated: {consideration}.\n"
        "Prior transfer recital: conveyed to the Grantor by deed recorded in "
        f"Deed Book {display_facts['prior_book']}, Page {display_facts['prior_page']}.\n"
        f"Grantor marital status: {married}\n"
        f"New construction: {construction}\n"
        f"Partial exemption: {display_facts['partial_exemption']}\n"
        f"Acknowledging notary: {display_facts['notary_name']}\n\n"
        "End of reading copy.\n"
    ).encode("utf-8")


def build_worked_candidate(
    experiment_root: str | Path,
    *,
    source_root: str | Path = DEFAULT_SOURCE,
    source_mapping: dict[str, Any] | None = None,
    material_overrides: Mapping[str, str | bytes] | None = None,
    artifact_pins: dict[str, Any] | None = None,
) -> WorkedBuild:
    """Materialize the human-readable scenario into one frozen Candidate."""
    source_root = Path(source_root)
    source = (
        deepcopy(source_mapping)
        if source_mapping is not None
        else json.loads((source_root / "scenario.json").read_bytes())
    )
    artifact = _forge_deed(Path(experiment_root), artifact_pins=artifact_pins)
    mapping = deepcopy(source)
    mapping.pop("authoring_schema_version", None)
    displayed_claims = mapping.pop("displayed_claims")
    accessibility = mapping.pop("physical_accessibility_renditions")
    display_facts = artifact.manifest.get("display_facts")
    if not isinstance(display_facts, Mapping):
        raise ValueError("Artifact Result omits the public deed display facts")
    material_bytes: dict[str, bytes] = {}
    relative_sources: dict[str, str] = {}
    for resource in mapping["kernel"]["resources"]:
        if resource["id"] == "deed-accessible":
            data = _accessible_deed_text(display_facts)
            relative_sources[resource["id"]] = "artifact-manifest:display_facts"
            resource.pop("source_path", None)
        elif resource["id"] in (material_overrides or {}):
            override = (material_overrides or {})[resource["id"]]
            data = override.encode("utf-8") if isinstance(override, str) else override
            relative_sources[resource["id"]] = "agent-proposed-material"
            resource.pop("source_path", None)
        elif "source_path" in resource:
            relative = resource.pop("source_path")
            data = (source_root / relative).read_bytes()
            relative_sources[resource["id"]] = relative
        elif resource.pop("artifact_request", None) == artifact.artifact_id:
            data = artifact.document
        else:  # pragma: no cover - fixture authoring error.
            raise ValueError(f"Resource has no material source: {resource['id']}")
        resource["content_hash"] = digest_bytes(data)
        material_bytes[resource["id"]] = data
    game = parse_game_definition(canonical_json(mapping))
    media_types = {item.id: item.media_type for item in game.kernel.resources}
    materials = []
    for resource_id in sorted(material_bytes):
        data = material_bytes[resource_id]
        if resource_id == artifact.artifact_id:
            receipt = {
                "schema_version": "0.5",
                "kind": "verismill-artifact-result",
                "resource_id": resource_id,
                "artifact_request": dict(artifact.request),
                "artifact_manifest": dict(artifact.manifest),
                "artifact_hash": artifact.content_hash,
                "upstream_commit": UPSTREAM_COMMIT,
            }
            attestation = dict(artifact.attestation)
        elif resource_id == "deed-accessible":
            receipt = {
                "schema_version": "0.5",
                "kind": "artifact-accessibility-rendition",
                "resource_id": resource_id,
                "source_artifact_id": artifact.artifact_id,
                "source_artifact_hash": artifact.content_hash,
                "display_facts_hash": digest_json(display_facts),
                "input_hash": digest_bytes(data),
                "operation": "derive-reading-copy-from-public-display-facts",
            }
            attestation = None
        else:
            receipt = {
                "schema_version": "0.5",
                "kind": "authored-source-material",
                "resource_id": resource_id,
                "source_path": relative_sources[resource_id],
                "input_hash": digest_bytes(data),
                "operation": "materialize-committed-worked-example-source",
            }
            attestation = None
        materials.append(
            MaterialInput(
                resource_id=resource_id,
                media_type=media_types[resource_id],
                data=data,
                reproduction_receipt=receipt,
                artifact_attestation=attestation,
            )
        )
    frozen = freeze_candidate(
        game=game,
        materials=materials,
        seed=1997,
        component_lock=reference_component_lock(),
        compilation_options={
            "locale": "en-US",
            "presentation": "hybrid",
            "physical_provenance": "fictional-game-material",
            "displayed_claims": displayed_claims,
            "physical_accessibility_renditions": accessibility,
        },
    )
    if not frozen.ok or frozen.candidate is None:
        raise ValueError([item.to_mapping() for item in frozen.findings])
    return WorkedBuild(
        source=source,
        candidate=frozen.candidate,
        artifact_hash=artifact.content_hash,
        artifact_attestation=dict(artifact.attestation),
    )


def _run_session(release: GameRelease) -> SessionHistory:
    bindings = (
        ActorBinding("binding-avery-1", Actor("actor-avery", "human", "Avery Player"), "avery", 1),
        ActorBinding("binding-blake-1", Actor("actor-blake", "human", "Blake Player"), "blake", 1),
    )
    viewers = (ViewerGrant("viewer-host", "host"),)
    history = create_session(
        release=release,
        session_id="ashwood-session",
        mode="live",
        bindings=bindings,
        viewers=viewers,
    )
    auth = {
        "host": AuthorizationContext("viewer", "viewer-host"),
        "avery": AuthorizationContext("actor", "actor-avery", "binding-avery-1"),
        "blake": AuthorizationContext("actor", "actor-blake", "binding-blake-1"),
    }

    def accept(command_id: str, action: str, payload: dict[str, Any], authority: str):
        nonlocal history
        result = apply_command(
            release,
            history,
            SessionCommand(
                command_id,
                history.session_id,
                release.release_id,
                history.sequence,
                action,
                payload,
            ),
            auth[authority],
        )
        if not result.receipt.accepted:  # pragma: no cover - fixture contract regression.
            raise ValueError(result.receipt.trusted_reason)
        history = result.history
        return result

    accept("command-open", "open-session", {}, "host")
    accept(
        "command-avery-claim",
        "share-claim",
        {"proposition_id": "staff-key-used", "stance": "accepts"},
        "avery",
    )
    accept(
        "command-blake-claim",
        "share-claim",
        {"proposition_id": "window-forced", "stance": "rejects"},
        "blake",
    )
    accept("command-investigation", "advance-phase", {"phase_id": "investigation"}, "host")
    accept(
        "command-payment",
        "disclose-resource",
        {"resource_id": "payment-note", "audience_seat_ids": ["avery"], "evidence_grade": "host-witnessed"},
        "host",
    )
    accept(
        "command-camera",
        "disclose-resource",
        {"resource_id": "camera-log", "audience_seat_ids": ["blake"], "evidence_grade": "host-witnessed"},
        "host",
    )
    accept("command-resolution-phase", "advance-phase", {"phase_id": "resolution"}, "host")
    for resource_id in ("madison-deed-1997", "deed-accessible", "accusation-form"):
        accept(
            f"command-disclose-{resource_id}",
            "disclose-resource",
            {
                "resource_id": resource_id,
                "audience_seat_ids": ["avery", "blake"],
                "evidence_grade": "host-witnessed",
            },
            "host",
        )
    submission = accept(
        "command-submit",
        "submit-resolution",
        {"hypothesis_id": "paid-insider", "proof_path_id": "access-payment-deed"},
        "avery",
    )
    accept(
        "command-resolve",
        "record-resolution",
        {"submission_sequence": submission.events[0].sequence},
        "host",
    )
    return history


def _persist_workspace(root: Path, build: WorkedBuild) -> Workspace:
    workspace = Workspace.create(root, workspace_id="ashwood-ledger", actor="human:owner")
    candidate_manifest_ref = workspace.store.put_json(build.candidate.frozen_manifest)
    deed = next(
        item for item in build.candidate.materials if item.resource_id == "madison-deed-1997"
    )
    artifact_ref = workspace.store.put_bytes(deed.data)
    if artifact_ref != build.artifact_hash:  # pragma: no cover
        raise ValueError("Workspace artifact identity differs from the forged result")
    draft = workspace.commit_draft(
        branch="main",
        expected_head=None,
        data={
            "title": "The Ashwood Ledger",
            "human_readable_source": build.source,
            "canonical_game_hash": build.candidate.game.content_hash,
            "compiler_candidate_id": build.candidate.candidate_id,
            "compiler_candidate_manifest": candidate_manifest_ref,
            "artifact_hash": build.artifact_hash,
            "human_authorization": "Stage 5 implementation authorized by repository owner",
        },
        reason="authorize the worked scenario and its forged artifact as the Stage 5 Candidate",
        actor="human:owner",
        component_lock=reference_component_lock(),
        operation_receipt={
            "operation": "worked-example.freeze",
            "inputs": {"scenario": digest_json(build.source)},
            "outputs": {
                "candidate": build.candidate.candidate_id,
                "artifact": build.artifact_hash,
            },
            "seed": 1997,
        },
        idempotency_key="ashwood-draft-1",
    )
    workspace.freeze_candidate(
        branch="main",
        expected_head=draft,
        actor="human:owner",
        idempotency_key="ashwood-candidate-1",
    )
    if not workspace.verify()["ok"]:  # pragma: no cover
        raise ValueError("worked example Workspace did not verify")
    return workspace


def _hill_climb_report(
    *,
    build: WorkedBuild,
    release: GameRelease,
    physical: PhysicalExport,
    history: SessionHistory,
    workspace: Workspace,
) -> str:
    return "\n".join(
        [
            "# The Ashwood Ledger - hill-climb lineage",
            "",
            "This report is a human-readable index over the immutable machine receipts in this output.",
            "",
            "## 1. Human direction and canonical source",
            "",
            "- Direction: build a rich, playable mystery using hill climbing and human oversight.",
            f"- Authoring source hash: `{digest_json(build.source)}`",
            "- Canonical truth owner: the frozen Game Definition; neither the artifact emitter nor Physical Export may invent narrative truth.",
            "",
            "## 2. Artifact Forge proposal",
            "",
            f"- Verismill commit: `{UPSTREAM_COMMIT}`",
            "- Document class: `deed_nj_1997`",
            "- Pinned claims: execution date `1997-10-17`; consideration `425000`.",
            f"- Exact artifact: `{build.artifact_hash}`",
            f"- Measurement status: `{build.artifact_attestation['measurement']['status']}`",
            f"- Artifact attestation: `{digest_json(build.artifact_attestation)}`",
            "- Full append-only forge state remains in `../forge-experiment/`; the Release carries the request, reproduction receipt, manifest, and attestation.",
            "",
            "## 3. Human-authorized Candidate",
            "",
            f"- Candidate: `{build.candidate.candidate_id}`",
            f"- Canonical game: `{build.candidate.game.content_hash}`",
            f"- Workspace lineage head: `{workspace.manifest['journal_heads']['lineage']}`",
            "- Human authority: `human:owner` authorized the worked Candidate.",
            "",
            "## 4. Deterministic Game Release",
            "",
            f"- Release: `{release.release_id}`",
            f"- Bundle: `{release.bundle_hash}`",
            "- The bundle contains trusted truth, authorized host and Seat projections, exact materials, receipts, and Artifact Attestation.",
            "",
            "## 5. Physical production projection",
            "",
            f"- Physical Export: `{physical.export_id}`",
            f"- Physical archive: `{physical.archive_hash}`",
            f"- Package plan: `{digest_json(physical.plan)}`",
            f"- Preflight: `{digest_json(physical.preflight)}` (`ok={str(physical.preflight['ok']).lower()}`)",
            "- The print deed is visibly marked; its unmodified source bytes remain in the embedded Release.",
            "",
            "## 6. Replay evidence",
            "",
            f"- Session History: `{history.content_hash}`",
            f"- Event head: `{history.event_head}`",
            f"- Event count: `{history.sequence}`",
            "- The final Session records a correct proof-based resolution without exposing private Seat state across boundaries.",
            "",
            "## Honest standing",
            "",
            "The physical layout and assembly plan passed deterministic preflight and human visual review. The deed's Verismill measurement remains `development_only`; this example does not claim independent legal-realism validation.",
            "",
        ]
    )


def run(
    root: str | Path,
    *,
    source_root: str | Path = DEFAULT_SOURCE,
) -> WorkedResult:
    """Build the complete example into a new operator-owned output directory."""
    root = Path(root)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise FileExistsError(f"worked example output is not empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    build = build_worked_candidate(root / "forge-experiment", source_root=source_root)
    compiled = compile_candidate(build.candidate)
    if not compiled.ok or compiled.release is None:  # pragma: no cover
        raise ValueError([item.to_mapping() for item in compiled.attempt.findings])
    release = compiled.release
    physical = export_physical(release)
    history = _run_session(release)
    state = replay(release, history)
    if state["status"] != "resolved" or not state["resolution"]["correct"]:  # pragma: no cover
        raise ValueError("worked Session did not reach the canonical resolution")
    workspace = _persist_workspace(root / "workspace", build)
    output_root = root / "output"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "game-release.zip").write_bytes(release.bundle_bytes)
    (output_root / "physical-package.zip").write_bytes(physical.archive_bytes)
    (output_root / "session-history.json").write_bytes(history.to_bytes())
    (output_root / "candidate.json").write_bytes(canonical_json(build.candidate.frozen_manifest))
    (output_root / "workspace-lineage.md").write_text(workspace.lineage_report(), encoding="utf-8")
    (output_root / "hill-climb-lineage.md").write_text(
        _hill_climb_report(
            build=build,
            release=release,
            physical=physical,
            history=history,
            workspace=workspace,
        ),
        encoding="utf-8",
    )
    workspace.export_archive(output_root / "workspace.ngw")
    package_root = output_root / "physical-package"
    for item in physical.files:
        target = package_root / item.path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(item.data)
    host_auth = AuthorizationContext("viewer", "viewer-host")
    avery_auth = AuthorizationContext("actor", "actor-avery", "binding-avery-1")
    blake_auth = AuthorizationContext("actor", "actor-blake", "binding-blake-1")
    summary = {
        "schema_version": "0.5",
        "game": "The Ashwood Ledger",
        "candidate_id": build.candidate.candidate_id,
        "release_id": release.release_id,
        "release_bundle_hash": release.bundle_hash,
        "artifact_hash": build.artifact_hash,
        "artifact_measurement_status": build.artifact_attestation["measurement"]["status"],
        "physical_export_id": physical.export_id,
        "physical_archive_hash": physical.archive_hash,
        "physical_preflight_ok": physical.preflight["ok"],
        "session_history_hash": history.content_hash,
        "session_event_head": history.event_head,
        "session_events": history.sequence,
        "session_resolved_correctly": state["resolution"]["correct"],
        "host_snapshot_hash": digest_json(host_snapshot(release, history, host_auth)),
        "seat_snapshot_hashes": {
            "avery": digest_json(seat_snapshot(release, history, avery_auth)),
            "blake": digest_json(seat_snapshot(release, history, blake_auth)),
        },
        "workspace_verified": workspace.verify()["ok"],
        "workspace_lineage_head": workspace.manifest["journal_heads"]["lineage"],
        "upstream_verismill_commit": UPSTREAM_COMMIT,
        "determinism_scope": (
            "byte-identical for the same persisted Candidate and resolved toolchain; "
            "forged artifact bytes are persisted for cross-environment replay"
        ),
    }
    (output_root / "stage5-result.json").write_bytes(canonical_json(summary))
    return WorkedResult(
        build=build,
        release=release,
        physical=physical,
        session=history,
        workspace=workspace,
        output_root=output_root,
        summary=summary,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the complete deterministic Ashwood Ledger worked example"
    )
    parser.add_argument("root", help="new user-owned directory for experiment and outputs")
    args = parser.parse_args()
    print(json.dumps(run(args.root).summary, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
