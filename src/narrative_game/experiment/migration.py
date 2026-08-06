"""Migration adapters that seal historical evidence into a portable Experiment."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any, Callable, Mapping
from zipfile import ZipFile

from narrative_game.contracts import canonical_json, digest_bytes
from narrative_game.workspace import Workspace

from .standing import ExperimentSpine


_EXTERNAL_CAPSULE_MAGIC = b"NGL-EXTERNAL-EXPERIMENT/0.12\n"
_EXTERNAL_EVIDENCE_MAGIC = b"NGL-EXTERNAL-EVIDENCE/0.12\n"


def _json(data: bytes) -> dict[str, Any]:
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("migration evidence must contain one JSON object")
    return value


def seal_verismill_experiment(
    suite_item: Mapping[str, Any],
    *,
    opener: Callable[[str | Path], Any] | None = None,
) -> bytes:
    """Capture the public, verified result of one external Verismill Experiment.

    The portable capsule deliberately contains no filesystem path. The external
    bus remains authoritative; its complete public replay, terminal head, result
    manifest, and attestation are sealed under the Workspace object hash.
    """
    if opener is None:
        try:
            from verismill import Experiment as VerismillExperiment
        except ImportError as exc:  # pragma: no cover - exercised without forge extra.
            raise RuntimeError("Verismill migration requires the 'forge' extra") from exc
        opener = VerismillExperiment.open
    experiment = opener(suite_item["experiment_root"])
    verification = experiment.verify()
    if not verification.get("ok"):
        raise ValueError(
            f"Verismill Experiment {suite_item['experiment_id']} does not verify: "
            f"{verification.get('failures', [])}"
        )
    replay = experiment.replay()
    if not replay:
        raise ValueError("Verismill Experiment has no replayable bus events")
    result = experiment.artifact_result(suite_item.get("candidate_ref"))
    artifact_hash = digest_bytes(result["artifact"])
    expected = {
        "experiment_id": suite_item["experiment_id"],
        "artifact_hash": suite_item["artifact_hash"],
        "candidate": suite_item["candidate_ref"],
        "evaluation": suite_item["evaluation_ref"],
    }
    actual = {
        "experiment_id": result["attestation"]["experiment_id"],
        "artifact_hash": artifact_hash,
        "candidate": result["attestation"]["candidate"],
        "evaluation": result["attestation"]["measurement"]["evaluation"],
    }
    if actual != expected:
        raise ValueError(
            f"Verismill suite reference does not match public Experiment result: "
            f"expected {expected}, found {actual}"
        )
    return _EXTERNAL_CAPSULE_MAGIC + canonical_json(
        {
            "schema_version": "0.12",
            "provider": "verismill",
            "experiment_id": expected["experiment_id"],
            "candidate_ref": expected["candidate"],
            "evaluation_ref": expected["evaluation"],
            "artifact_hash": artifact_hash,
            "bus_head": replay[-1]["event_hash"],
            "replay": replay,
            "verification": verification,
            "result_manifest": result["manifest"],
            "artifact_attestation": result["attestation"],
        }
    )


def read_verismill_experiment_capsule(data: bytes) -> dict[str, Any]:
    """Decode one opaque external capsule after checking its format marker."""
    if not data.startswith(_EXTERNAL_CAPSULE_MAGIC):
        raise ValueError("unsupported external Experiment capsule")
    return _json(data.removeprefix(_EXTERNAL_CAPSULE_MAGIC))


def seal_external_evidence(data: bytes) -> bytes:
    """Make exact third-party bytes opaque to the Workspace's internal-ref walker."""
    if not data:
        raise ValueError("external evidence cannot be empty")
    return _EXTERNAL_EVIDENCE_MAGIC + data


def read_external_evidence(data: bytes) -> bytes:
    if not data.startswith(_EXTERNAL_EVIDENCE_MAGIC):
        raise ValueError("unsupported external evidence envelope")
    return data.removeprefix(_EXTERNAL_EVIDENCE_MAGIC)


def _release_evidence_contracts(
    release_bytes: bytes, suite_items: list[Mapping[str, Any]]
) -> tuple[dict[str, Any], tuple[str, ...], tuple[dict[str, Any], ...]]:
    """Reconstruct proof and accessibility contracts from exact released bytes."""
    with ZipFile(BytesIO(release_bytes)) as archive:
        release = _json(archive.read("release.json"))
        game = _json(archive.read("trusted/game.json"))
        material_by_resource = {
            item["resource_id"]: item for item in release["materials"]
        }
        evidence_by_id = {
            item["id"]: item for item in game["narrative"]["evidence"]
        }
        reveal_phase = {
            item["evidence_id"]: item["phase_id"]
            for item in game["narrative"]["reveals"]
        }
        proof_paths = {
            item["id"]: tuple(item["evidence_ids"])
            for item in game["narrative"]["proof_paths"]
            if item["id"] in game["narrative"]["resolution"][
                "acceptable_proof_path_ids"
            ]
        }
        paths_for_evidence: dict[str, list[str]] = {}
        for path_id, evidence_ids in proof_paths.items():
            for evidence_id in evidence_ids:
                paths_for_evidence.setdefault(evidence_id, []).append(path_id)

        contracts = []
        for suite_item in sorted(suite_items, key=lambda item: item["artifact_id"]):
            artifact_id = str(suite_item["artifact_id"])
            resource_id = artifact_id.replace("_", "-")
            accessible_id = f"{resource_id}-reading-copy"
            evidence = evidence_by_id[artifact_id]
            propositions = sorted(
                {
                    relation["target_id"]
                    for relation in evidence["relations"]
                    if relation["target_kind"] == "proposition"
                }
            )
            receipt = _json(archive.read(f"receipts/{resource_id}.json"))
            accessibility = receipt["artifact_manifest"]["display_facts"][
                "accessibility"
            ]
            native = material_by_resource[resource_id]
            accessible = material_by_resource[accessible_id]
            if native["content_hash"] != suite_item["artifact_hash"]:
                raise ValueError(
                    f"released {resource_id} differs from measured Verismill artifact"
                )
            contracts.append(
                {
                    "schema_version": "0.12",
                    "artifact_id": artifact_id,
                    "native_hash": native["content_hash"],
                    "accessible_hash": accessible["content_hash"],
                    "native_proposition_ids": propositions,
                    "accessible_proposition_ids": propositions,
                    "entries": [
                        {
                            "editorial_identification": accessibility[
                                "editorial_identification"
                            ],
                            "visible_wording": accessibility["visible_content"],
                            "visual_evidence": accessibility["visual_description"],
                            "interpretation": accessibility["interpretation"],
                            "proposition_ids": propositions,
                        }
                    ],
                }
            )

        claims = []
        required_propositions: set[str] = set()
        for evidence_id, path_ids in sorted(paths_for_evidence.items()):
            evidence = evidence_by_id[evidence_id]
            resource_id = evidence["resource_id"]
            if resource_id not in material_by_resource:
                raise ValueError(f"proof path names unreleased Resource: {resource_id}")
            propositions = sorted(
                {
                    relation["target_id"]
                    for relation in evidence["relations"]
                    if relation["target_kind"] == "proposition"
                }
            )
            if not propositions:
                raise ValueError(f"proof-path Evidence has no Proposition: {evidence_id}")
            required_propositions.update(propositions)
            for proposition in propositions:
                claims.append(
                    {
                        "proposition_id": proposition,
                        "evidence_id": evidence_id,
                        "resource_path": material_by_resource[resource_id]["path"],
                        "locus": {"page": 1, "bbox_norm": [0, 0, 1, 1]},
                        "content_hash": material_by_resource[resource_id][
                            "content_hash"
                        ],
                        "phase_id": reveal_phase[evidence_id],
                        "proof_path_ids": sorted(path_ids),
                    }
                )
        trace = {
            "schema_version": "0.12",
            "proof_paths": {
                path: list(evidence_ids)
                for path, evidence_ids in sorted(proof_paths.items())
            },
            "claims": claims,
        }
        return trace, tuple(sorted(required_propositions)), tuple(contracts)


def migrate_winter_observatory_candidate_6(
    game_root: str | Path,
    *,
    workspace_root: str | Path,
    archive_path: str | Path,
    verismill_opener: Callable[[str | Path], Any] | None = None,
) -> dict[str, Any]:
    """Seal the historical Candidate 6 rung without creating new standing."""
    game_root = Path(game_root)
    workspace_root = Path(workspace_root)
    archive_path = Path(archive_path)
    release_bytes = (
        game_root / "playable-candidate-6-development/output/game-release.zip"
    ).read_bytes()
    physical_bytes = (
        game_root / "playable-candidate-6-development/output/physical-package.zip"
    ).read_bytes()
    build_bytes = (
        game_root / "playable-candidate-6-development/output/build-result.json"
    ).read_bytes()
    build = _json(build_bytes)
    collection_bytes = (
        game_root / "artifacts/candidate-6/native-artifact-manifest.json"
    ).read_bytes()
    approval_bytes = (
        game_root / "artifacts/candidate-6/human-approval.json"
    ).read_bytes()
    approval = _json(approval_bytes)
    gameplay_bytes = (
        game_root / "playtests/development-blind-005-candidate-6/manifest.json"
    ).read_bytes()
    gameplay = _json(gameplay_bytes)
    playtest_root = game_root / "playtests/development-blind-005-candidate-6"
    transcript_bytes = {
        str(player["transcript"]): (playtest_root / player["transcript"]).read_bytes()
        for player in gameplay["players"]
    }
    for player in gameplay["players"]:
        actual = digest_bytes(transcript_bytes[player["transcript"]]).removeprefix(
            "sha256:"
        )
        if actual != player["transcript_sha256"]:
            raise ValueError(
                f"Candidate 6 transcript differs from manifest: {player['transcript']}"
            )
    suite_bytes = (game_root / "measurements/candidate-6/suite.json").read_bytes()
    suite = _json(suite_bytes)
    attestation_bytes = (
        game_root / "measurements/candidate-6/suite-attestation.json"
    ).read_bytes()
    attestation = _json(attestation_bytes)
    lineage_bytes = (game_root / "artifacts/candidate-6/lineage.json").read_bytes()

    expected_hashes = {
        "release": (digest_bytes(release_bytes), build["release_hash"]),
        "physical": (digest_bytes(physical_bytes), build["physical_hash"]),
        "collection": (
            digest_bytes(collection_bytes), approval["collection_manifest"]["sha256"]
        ),
        "approval": (digest_bytes(approval_bytes), suite["approval_hash"]),
    }
    mismatches = {
        name: values for name, values in expected_hashes.items()
        if values[0] != values[1]
    }
    if mismatches:
        raise ValueError(f"Candidate 6 exact-hash evidence mismatch: {mismatches}")
    if len(suite["artifacts"]) != 19 or attestation["artifact_count"] != 19:
        raise ValueError("Candidate 6 migration requires all 19 artifact Experiments")
    if attestation["accepted_artifacts"] != 0:
        raise ValueError("historical Candidate 6 realism standing changed")

    capsules = {
        item["artifact_id"]: seal_verismill_experiment(
            item, opener=verismill_opener
        )
        for item in suite["artifacts"]
    }
    claim_trace, required, accessibility = _release_evidence_contracts(
        release_bytes, suite["artifacts"]
    )

    workspace = Workspace.create(
        workspace_root, workspace_id="winter-observatory", actor="system:migration"
    )
    spine = ExperimentSpine(workspace)
    parent_build_bytes = (
        game_root / "playable-candidate-5-development/output/build-result.json"
    ).read_bytes()
    parent = _json(parent_build_bytes)["candidate_id"]
    spine.register_lineage_anchor(
        candidate_id=parent,
        source_bytes=parent_build_bytes,
        label="Candidate 5 historical parent",
    )
    evidence_objects = {
        "candidate-6-build": seal_external_evidence(build_bytes),
        "candidate-6-gameplay": seal_external_evidence(gameplay_bytes),
        "candidate-6-lineage": seal_external_evidence(lineage_bytes),
        "candidate-6-suite": seal_external_evidence(suite_bytes),
        "candidate-6-suite-attestation": seal_external_evidence(attestation_bytes),
        **{
            f"candidate-6-transcript:{name}": seal_external_evidence(data)
            for name, data in transcript_bytes.items()
        },
    }
    evidence_hash = {
        name: digest_bytes(data) for name, data in evidence_objects.items()
    }
    standings = {
        "coherent_build": {
            "status": "passed",
            "instrument": "candidate-build-preflight-v0.1",
            "evidence_refs": [evidence_hash["candidate-6-build"]],
        },
        "gameplay": {
            "status": "passed",
            "instrument": "fresh-phase-gated-blind-playtest-v1",
            "evidence_refs": [
                evidence_hash["candidate-6-gameplay"],
                *[
                    evidence_hash[f"candidate-6-transcript:{name}"]
                    for name in sorted(transcript_bytes)
                ],
            ],
            "scores": {"model_players": 2, "hints": 0},
        },
        "accessibility": {
            "status": "passed",
            "instrument": "critical-typed-pdf-parity-v1",
            "evidence_refs": [evidence_hash["candidate-6-gameplay"]],
            "scores": {"paired_artifacts": 19},
        },
        "artifact_realism": {
            "status": "not_accepted",
            "instrument": "verismill:absolute-v0.2",
            "evidence_refs": [evidence_hash["candidate-6-suite-attestation"]],
            "scores": {"accepted": 0, "measured": 19},
        },
        "human_play": {
            "status": "unmeasured",
            "instrument": "six-human-table-v1",
            "evidence_refs": [],
        },
        "public_release": {
            "status": "unclaimed",
            "instrument": "public-release-v1",
            "evidence_refs": [],
        },
    }
    result = spine.record_selected_rung(
        candidate_id=build["candidate_id"],
        parent_candidate_id=parent,
        release_bytes=release_bytes,
        physical_package_bytes=physical_bytes,
        artifact_collection_bytes=collection_bytes,
        artifact_experiments=capsules,
        approvals=(approval_bytes,),
        evidence_objects=evidence_objects,
        standings=standings,
        claim_trace=claim_trace,
        required_propositions=required,
        accessibility_contracts=accessibility,
        blockers=(
            {
                "code": "artifact.realism",
                "evidence_class": "artifact_realism",
                "reason": "0 of 19 exact artifacts met the frozen realism gate",
            },
            {
                "code": "human.play",
                "evidence_class": "human_play",
                "reason": "an exact-version six-human table has not been measured",
            },
        ),
        debt=(
            {
                "code": "dossier.depth",
                "reason": "six role dossiers remain shallow and mechanically static",
            },
        ),
        invalidation=(
            "release byte change invalidates gameplay and accessibility evidence",
            "artifact byte change invalidates exact approval and realism evidence",
            "proof-path or authorization change invalidates the claim trace",
        ),
        replay_requirements=(
            "player-visible or proof-affecting change requires fresh blind gameplay",
            "artifact change requires scoped human approval and fresh realism measurement",
        ),
        actor="system:migration",
        export_path=archive_path,
    )
    return {
        "schema_version": "0.12",
        "migration": "winter-observatory-candidate-6",
        "created_candidate": False,
        "created_standing": False,
        "projection": result["projection"],
        "archive": result["archive"],
    }
