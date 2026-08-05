"""Ordered pure compiler passes from frozen Candidate to one Game Release."""

from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from typing import Any, Iterable, Mapping
import zipfile

from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json
from narrative_game.narrative import GameDefinition, validate_facilitated_investigation

from .model import (
    BundledFile,
    Candidate,
    CompilationAttempt,
    CompilationFinding,
    CompilationResult,
    FreezeResult,
    GameRelease,
    MaterialInput,
)
from .projections import export_projection, host_projection, seat_projection, simulation_projection


COMPILER_VERSION = "0.4.0"
CANONICALIZATION_VERSION = "canonical-json-sha256-v1"


def _component(component_id: str, version: str, capabilities: list[str]) -> dict[str, Any]:
    contract = {"id": component_id, "version": version, "capabilities": capabilities}
    return {**contract, "implementation": digest_json(contract)}


def reference_component_lock() -> dict[str, Any]:
    """Return the explicit first-party component resolution for v0.3."""
    return {
        "schema_version": "0.3",
        "components": [
            _component("canonicalization", "1.0.0", [CANONICALIZATION_VERSION]),
            _component("kernel", "0.3.0", ["resources", "access", "extensions"]),
            _component(
                "narrative",
                "0.4.0",
                ["fixed-truth", "authorized-projections", "phase-evidence-framing"],
            ),
            _component(
                "facilitated-investigation",
                "0.1.0",
                ["proof-resolution", "host-interventions", "cast-variants"],
            ),
            _component("compiler", COMPILER_VERSION, ["deterministic-release-zip"]),
            _component(
                "runtime",
                "0.4.0",
                ["session-authority", "event-replay", "authorized-seat-snapshots"],
            ),
        ],
    }


def _copy_json(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _key(item: CompilationFinding) -> tuple[str, ...]:
    return (item.severity, item.code, item.owner, item.locus, item.quote, item.message)


def _finding(
    code: str,
    *,
    locus: str,
    quote: str,
    message: str,
    evidence: Mapping[str, Any],
    owner: str = "compiler",
    owner_version: str = COMPILER_VERSION,
    severity: str = "blocker",
) -> CompilationFinding:
    return CompilationFinding(
        code=code,
        severity=severity,
        owner=owner,
        owner_version=owner_version,
        locus=locus,
        quote=quote,
        message=message,
        evidence=_copy_json(evidence),
    )


def _profile_findings(game: GameDefinition) -> list[CompilationFinding]:
    result = []
    for item in validate_facilitated_investigation(game):
        owner = "kernel" if item.code.startswith("kernel.") else "facilitated-investigation"
        version = "0.3.0" if owner == "kernel" else "0.1.0"
        result.append(
            _finding(
                item.code,
                locus=item.locus,
                quote=item.quote,
                message=item.message,
                evidence={"finding": item.to_mapping()},
                owner=owner,
                owner_version=version,
                severity=item.severity,
            )
        )
    return result


def _lock_findings(component_lock: Mapping[str, Any]) -> list[CompilationFinding]:
    expected = reference_component_lock()
    if component_lock == expected:
        return []
    return [
        _finding(
            "compiler.incompatible-component-lock",
            locus="candidate.component-lock",
            quote=digest_json(component_lock),
            message="Candidate component resolution is not supported by this compiler",
            evidence={"expected": digest_json(expected), "actual": digest_json(component_lock)},
        )
    ]


def _material_findings(
    game: GameDefinition, materials: tuple[MaterialInput, ...]
) -> list[CompilationFinding]:
    findings: list[CompilationFinding] = []
    resources = {item.id: item for item in game.kernel.resources}
    counts: dict[str, int] = {}
    for material in materials:
        counts[material.resource_id] = counts.get(material.resource_id, 0) + 1
        resource = resources.get(material.resource_id)
        if resource is None:
            findings.append(
                _finding(
                    "compiler.unknown-material",
                    locus=f"material:{material.resource_id}",
                    quote=material.resource_id,
                    message="material does not correspond to a Kernel Resource",
                    evidence={"content_hash": material.content_hash},
                )
            )
            continue
        if material.content_hash != resource.content_hash:
            findings.append(
                _finding(
                    "compiler.material-hash-mismatch",
                    locus=f"material:{material.resource_id}",
                    quote=material.content_hash,
                    message="material bytes do not match the frozen Resource hash",
                    evidence={"expected": resource.content_hash, "actual": material.content_hash},
                )
            )
        if material.media_type != resource.media_type:
            findings.append(
                _finding(
                    "compiler.material-media-mismatch",
                    locus=f"material:{material.resource_id}",
                    quote=material.media_type,
                    message="material media type differs from the frozen Resource",
                    evidence={"expected": resource.media_type, "actual": material.media_type},
                )
            )
        if not material.reproduction_receipt:
            findings.append(
                _finding(
                    "compiler.missing-reproduction-receipt",
                    locus=f"material:{material.resource_id}",
                    quote="{}",
                    message="every material requires a trusted reproduction receipt",
                    evidence={"resource_id": material.resource_id},
                )
            )
    for resource_id in sorted(set(resources) - set(counts)):
        findings.append(
            _finding(
                "compiler.missing-material",
                locus=f"resource:{resource_id}",
                quote=resource_id,
                message="Candidate does not contain the Resource's exact material bytes",
                evidence={"expected": resources[resource_id].content_hash},
            )
        )
    for resource_id, count in sorted(counts.items()):
        if count > 1:
            findings.append(
                _finding(
                    "compiler.duplicate-material",
                    locus=f"resource:{resource_id}",
                    quote=str(count),
                    message="one Resource has more than one authoritative material input",
                    evidence={"resource_id": resource_id, "count": count},
                )
            )
    return findings


def freeze_candidate(
    *,
    game: GameDefinition,
    materials: Iterable[MaterialInput],
    seed: int,
    component_lock: Mapping[str, Any],
    compilation_options: Mapping[str, Any] | None = None,
    advisories: Iterable[CompilationFinding] = (),
) -> FreezeResult:
    """Freeze all play-affecting inputs, or return blockers and no Candidate."""
    material_tuple = tuple(
        replace(
            item,
            reproduction_receipt=_copy_json(item.reproduction_receipt),
            artifact_attestation=(
                _copy_json(item.artifact_attestation)
                if item.artifact_attestation is not None
                else None
            ),
        )
        for item in materials
    )
    lock = _copy_json(component_lock)
    options = _copy_json(compilation_options or {})
    advisory_tuple = tuple(
        sorted(
            (replace(item, evidence=_copy_json(item.evidence)) for item in advisories),
            key=_key,
        )
    )
    if any(item.severity != "warning" for item in advisory_tuple):
        raise ValueError("Candidate advisories may contain warnings only")
    findings = [
        *_profile_findings(game),
        *_lock_findings(lock),
        *_material_findings(game, material_tuple),
    ]
    findings = sorted(findings, key=_key)
    if any(item.severity == "blocker" for item in findings):
        return FreezeResult(candidate=None, findings=tuple(findings))
    manifest = {
        "schema_version": "0.3",
        "canonicalization": CANONICALIZATION_VERSION,
        "game": game.to_mapping(),
        "game_hash": game.content_hash,
        "materials": [item.descriptor() for item in sorted(material_tuple, key=lambda x: x.resource_id)],
        "seed": seed,
        "component_lock": lock,
        "compilation_options": options,
        "advisories": [item.to_mapping() for item in advisory_tuple],
    }
    candidate_id = digest_json(manifest)
    candidate = Candidate(
        candidate_id=candidate_id,
        game=game,
        materials=tuple(sorted(material_tuple, key=lambda item: item.resource_id)),
        seed=seed,
        component_lock=lock,
        compilation_options=options,
        advisories=advisory_tuple,
        frozen_manifest=_copy_json(manifest),
    )
    return FreezeResult(candidate=candidate, findings=tuple(advisory_tuple))


def _candidate_findings(candidate: Candidate) -> list[CompilationFinding]:
    findings = [
        *_profile_findings(candidate.game),
        *_lock_findings(candidate.component_lock),
        *_material_findings(candidate.game, candidate.materials),
    ]
    if digest_json(candidate.frozen_manifest) != candidate.candidate_id:
        findings.append(
            _finding(
                "compiler.candidate-identity-mismatch",
                locus="candidate.id",
                quote=candidate.candidate_id,
                message="Candidate ID does not match its frozen canonical manifest",
                evidence={"actual": digest_json(candidate.frozen_manifest)},
            )
        )
    current_materials = [item.descriptor() for item in sorted(candidate.materials, key=lambda x: x.resource_id)]
    if current_materials != candidate.frozen_manifest.get("materials"):
        findings.append(
            _finding(
                "compiler.candidate-material-mutation",
                locus="candidate.materials",
                quote=digest_json(current_materials),
                message="Candidate material inputs differ from the frozen manifest",
                evidence={"frozen": digest_json(candidate.frozen_manifest.get("materials", []))},
            )
        )
    current_fields = {
        "game": candidate.game.to_mapping(),
        "game_hash": candidate.game.content_hash,
        "seed": candidate.seed,
        "component_lock": candidate.component_lock,
        "compilation_options": candidate.compilation_options,
        "advisories": [item.to_mapping() for item in candidate.advisories],
    }
    changed_fields = [
        key for key, value in current_fields.items() if candidate.frozen_manifest.get(key) != value
    ]
    if changed_fields:
        findings.append(
            _finding(
                "compiler.candidate-semantic-mutation",
                locus="candidate.frozen-manifest",
                quote=", ".join(changed_fields),
                message="play-affecting Candidate fields differ from the frozen manifest",
                evidence={"changed_fields": changed_fields},
            )
        )
    return sorted(findings, key=_key)


def _json_file(path: str, value: Any, audience: str) -> BundledFile:
    return BundledFile(path=path, media_type="application/json", data=canonical_json(value), audience=audience)


def _archive(files: tuple[BundledFile, ...]) -> bytes:
    target = BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
        for item in sorted(files, key=lambda value: value.path):
            info = zipfile.ZipInfo(item.path, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            info.extra = b""
            info.comment = b""
            info.internal_attr = 0
            info.external_attr = 0o600 << 16
            archive.writestr(info, item.data)
    return target.getvalue()


def _attempt(
    candidate: Candidate,
    *,
    outcome: str,
    findings: tuple[CompilationFinding, ...],
    release_id: str | None = None,
    bundle_hash: str | None = None,
) -> CompilationAttempt:
    core = {
        "candidate_id": candidate.candidate_id,
        "compiler_version": COMPILER_VERSION,
        "outcome": outcome,
        "findings": [item.to_mapping() for item in findings],
        "release_id": release_id,
        "bundle_hash": bundle_hash,
    }
    return CompilationAttempt(
        attempt_id=digest_json(core),
        candidate_id=candidate.candidate_id,
        compiler_version=COMPILER_VERSION,
        outcome=outcome,
        findings=findings,
        release_id=release_id,
        bundle_hash=bundle_hash,
    )


def compile_candidate(candidate: Candidate) -> CompilationResult:
    """Compile at most one canonical Release; blockers produce no partial bytes."""
    validation_findings = tuple(_candidate_findings(candidate))
    blockers = tuple(item for item in validation_findings if item.severity == "blocker")
    if blockers:
        return CompilationResult(
            release=None,
            attempt=_attempt(candidate, outcome="blocked", findings=validation_findings),
        )

    seat_views = {
        seat.id: seat_projection(candidate.game, seat.id)
        for seat in sorted(candidate.game.kernel.seats, key=lambda item: item.id)
    }
    content_files: list[BundledFile] = [
        _json_file("trusted/game.json", candidate.game.to_mapping(), "trusted"),
        _json_file("projections/host.json", host_projection(candidate.game), "trusted-host"),
        _json_file(
            "projections/simulation.json",
            simulation_projection(candidate.game, seat_views),
            "trusted-simulation",
        ),
        _json_file("projections/export.json", export_projection(candidate.game), "trusted-exporter"),
    ]
    for seat_id, projection in seat_views.items():
        content_files.append(_json_file(f"projections/seats/{seat_id}.json", projection, f"seat:{seat_id}"))
    material_paths: dict[str, str] = {}
    for material in candidate.materials:
        path = f"materials/{material.resource_id}"
        material_paths[material.resource_id] = path
        content_files.append(BundledFile(path, material.media_type, material.data, "access-policy"))
        content_files.append(
            _json_file(
                f"receipts/{material.resource_id}.json",
                material.reproduction_receipt,
                "trusted",
            )
        )
        if material.artifact_attestation is not None:
            content_files.append(
                _json_file(
                    f"attestations/{material.resource_id}.json",
                    material.artifact_attestation,
                    "trusted",
                )
            )
    content_tuple = tuple(sorted(content_files, key=lambda item: item.path))
    warnings = tuple(
        sorted(
            (
                *candidate.advisories,
                *(item for item in validation_findings if item.severity == "warning"),
            ),
            key=_key,
        )
    )
    release_core = {
        "schema_version": "0.3",
        "candidate_id": candidate.candidate_id,
        "seed": candidate.seed,
        "compiler_version": COMPILER_VERSION,
        "canonicalization": CANONICALIZATION_VERSION,
        "component_lock": candidate.component_lock,
        "game_profile": {
            "id": candidate.game.profile.id,
            "version": candidate.game.profile.version,
            "cast_variants": [item.__dict__ for item in candidate.game.profile.cast_variants],
        },
        "materials": [
            {**item.descriptor(), "path": material_paths[item.resource_id]}
            for item in candidate.materials
        ],
        "files": [item.descriptor() for item in content_tuple],
        "compilation_options": candidate.compilation_options,
        "compilation_report": {
            "blockers": [],
            "warnings": [item.to_mapping() for item in warnings],
        },
        "standing": "development-only",
    }
    release_id = digest_json(release_core)
    manifest = {"release_id": release_id, **release_core}
    release_file = _json_file("release.json", manifest, "public-metadata")
    files = tuple(sorted((release_file, *content_tuple), key=lambda item: item.path))
    bundle_bytes = _archive(files)
    bundle_hash = digest_bytes(bundle_bytes)
    release = GameRelease(
        release_id=release_id,
        candidate_id=candidate.candidate_id,
        manifest=_copy_json(manifest),
        files=files,
        bundle_bytes=bundle_bytes,
        bundle_hash=bundle_hash,
    )
    return CompilationResult(
        release=release,
        attempt=_attempt(
            candidate,
            outcome="released",
            findings=warnings,
            release_id=release_id,
            bundle_hash=bundle_hash,
        ),
    )
