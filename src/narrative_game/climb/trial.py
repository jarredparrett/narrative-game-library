"""Complete, deterministic player-facing packages for blind measurement."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import json
from typing import Any, Mapping
import zipfile

from pypdf import PdfReader

from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import canonical_json, digest_bytes, digest_json
from narrative_game.physical import PhysicalExport, verify_physical_export


@dataclass(frozen=True)
class TrialFile:
    path: str
    media_type: str
    data: bytes

    @property
    def content_hash(self) -> str:
        return digest_bytes(self.data)

    def descriptor(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "media_type": self.media_type,
            "content_hash": self.content_hash,
            "bytes": len(self.data),
        }


@dataclass(frozen=True)
class BlindTrial:
    trial_id: str
    manifest: Mapping[str, Any]
    files: tuple[TrialFile, ...]
    archive_bytes: bytes
    archive_hash: str

    def file(self, path: str) -> TrialFile:
        try:
            return next(item for item in self.files if item.path == path)
        except StopIteration as exc:
            raise KeyError(path) from exc


_FORBIDDEN_JSON_KEYS = {
    "acceptable_proof_path_ids",
    "artifact_attestation",
    "candidate_id",
    "correct_hypothesis_id",
    "export_id",
    "release_id",
    "reproduction_receipt",
    "truth_model",
}


def _archive(files: tuple[TrialFile, ...]) -> bytes:
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


def _forbidden_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return {
            *(str(key) for key in value if key in _FORBIDDEN_JSON_KEYS),
            *(item for child in value.values() for item in _forbidden_keys(child)),
        }
    if isinstance(value, (list, tuple)):
        return {item for child in value for item in _forbidden_keys(child)}
    return set()


def _manifest(files: tuple[TrialFile, ...]) -> dict[str, Any]:
    core = {
        "schema_version": "0.7",
        "kind": "blind-trial",
        "blind_protocol": {
            "contains": [
                "all-seat-projections",
                "all-seat-accessible-source-materials",
                "all-seat-accessible-print-renditions",
                "delivery-schedule",
                "included-file-preflight",
            ],
            "excludes": [
                "trusted-truth",
                "host-only-materials",
                "answer-keys",
                "candidate-release-export-identities",
                "provenance-and-reproduction-receipts",
                "prior-scores-and-builder-rationale",
            ],
        },
        "files": [item.descriptor() for item in files],
    }
    return {"trial_id": digest_json(core), **core}


def prepare_blind_trial(
    release: GameRelease,
    physical: PhysicalExport,
    *,
    cover_story: str,
) -> BlindTrial:
    """Project one complete Release into a source-identity-free judge package."""
    if not cover_story.strip():
        raise ValueError("cover_story is required")
    verify_physical_export(physical, release)
    seat_files = tuple(
        item
        for item in release.files
        if item.path.startswith("projections/seats/") and item.audience.startswith("seat:")
    )
    seat_copies = tuple(
        item for item in physical.plan["copies"] if item["audience"].startswith("seat:")
    )
    seat_resources = {item["resource_id"] for item in seat_copies}
    if not seat_files or not seat_resources:
        raise ValueError("Blind Trial requires Seat projections and Seat-accessible materials")

    files: list[TrialFile] = [
        TrialFile("trial/cover-story.txt", "text/plain", cover_story.encode("utf-8"))
    ]
    material_paths: dict[str, str] = {}
    print_paths: dict[str, str] = {}
    for item in sorted(seat_files, key=lambda value: value.path):
        seat_name = item.path.removeprefix("projections/seats/")
        files.append(TrialFile(f"trial/seats/{seat_name}", item.media_type, item.data))
    for resource_id in sorted(seat_resources):
        source = release.file(f"materials/{resource_id}")
        rendered = physical.file(f"print/resources/{resource_id}.pdf")
        print_path = f"trial/print/{resource_id}.pdf"
        print_paths[resource_id] = print_path
        files.append(TrialFile(print_path, rendered.media_type, rendered.data))
        if source.media_type == "application/pdf":
            material_paths[resource_id] = print_path
        else:
            material_path = f"trial/materials/{resource_id}"
            material_paths[resource_id] = material_path
            files.append(TrialFile(material_path, source.media_type, source.data))

    included_print_paths = {f"print/resources/{item}.pdf" for item in seat_resources}
    preflight_checks = [
        {
            **item,
            "path": f"trial/print/{item['path'].removeprefix('print/resources/')}",
        }
        for item in physical.preflight["files"]
        if item["path"] in included_print_paths
    ]
    schedule = {
        "schema_version": "0.7",
        "containers": [
            {
                "audience": item["audience"],
                "delivery_condition": item["delivery_condition"],
                "label": item["label"],
            }
            for item in physical.plan["containers"]
            if item["audience"].startswith("seat:")
        ],
        "copies": [
            {
                "audience": item["audience"],
                "delivery_condition": item["delivery_condition"],
                "resource_id": item["resource_id"],
                "material_path": material_paths[item["resource_id"]],
                "print_path": print_paths[item["resource_id"]],
            }
            for item in seat_copies
        ],
        "production": physical.plan["production"],
        "preflight": {"ok": len(preflight_checks) == len(seat_resources), "files": preflight_checks},
    }
    files.append(TrialFile("trial/schedule.json", "application/json", canonical_json(schedule)))
    content = tuple(sorted(files, key=lambda item: item.path))
    manifest = _manifest(content)
    all_files = tuple(
        sorted(
            (*content, TrialFile("blind-trial.json", "application/json", canonical_json(manifest))),
            key=lambda item: item.path,
        )
    )
    archive_bytes = _archive(all_files)
    result = BlindTrial(
        manifest["trial_id"],
        manifest,
        all_files,
        archive_bytes,
        digest_bytes(archive_bytes),
    )
    verify_blind_trial(result)
    return result


def verify_blind_trial(value: BlindTrial) -> None:
    """Verify identity, completeness, archive bytes, and forbidden disclosures."""
    failures: list[str] = []
    content = tuple(item for item in value.files if item.path != "blind-trial.json")
    expected_manifest = _manifest(content)
    if value.manifest != expected_manifest or value.trial_id != expected_manifest["trial_id"]:
        failures.append("Blind Trial manifest or identity differs")
    try:
        manifest_file = value.file("blind-trial.json")
    except KeyError:
        failures.append("Blind Trial manifest file is missing")
    else:
        if manifest_file.data != canonical_json(value.manifest):
            failures.append("Blind Trial manifest bytes differ")
    if digest_bytes(value.archive_bytes) != value.archive_hash or _archive(value.files) != value.archive_bytes:
        failures.append("Blind Trial archive identity differs")
    paths = {item.path for item in value.files}
    if any(
        path.startswith(("trusted/", "receipts/", "attestations/", "source/"))
        or "host" in path.lower()
        for path in paths
    ):
        failures.append("Blind Trial contains a trusted or host-only path")
    schedule_path = "trial/schedule.json"
    if schedule_path not in paths:
        failures.append("Blind Trial schedule is missing")
    else:
        schedule = json.loads(value.file(schedule_path).data)
        resources = {item["resource_id"] for item in schedule["copies"]}
        for copy in schedule["copies"]:
            if copy["material_path"] not in paths or copy["print_path"] not in paths:
                failures.append(
                    f"Blind Trial omits a Seat-accessible resource: {copy['resource_id']}"
                )
        if not schedule["preflight"]["ok"]:
            failures.append("Blind Trial included-file preflight failed")
    for item in value.files:
        if item.media_type == "application/json":
            try:
                forbidden = _forbidden_keys(json.loads(item.data))
            except json.JSONDecodeError:
                failures.append(f"Blind Trial JSON is invalid: {item.path}")
            else:
                if forbidden:
                    failures.append(f"Blind Trial leaks {sorted(forbidden)} in {item.path}")
    if failures:
        raise ValueError("; ".join(failures))


def load_blind_trial(archive_bytes: bytes) -> BlindTrial:
    """Reconstruct and verify a Blind Trial from its portable archive bytes."""
    with zipfile.ZipFile(BytesIO(archive_bytes), "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "blind-trial.json" not in names:
            raise ValueError("Blind Trial archive has duplicate paths or no manifest")
        manifest = json.loads(archive.read("blind-trial.json"))
        media_types = {
            item["path"]: item["media_type"] for item in manifest["files"]
        }
        media_types["blind-trial.json"] = "application/json"
        if set(names) != set(media_types):
            raise ValueError("Blind Trial archive file graph differs from its manifest")
        files = tuple(
            sorted(
                (
                    TrialFile(path, media_types[path], archive.read(path))
                    for path in names
                ),
                key=lambda item: item.path,
            )
        )
    result = BlindTrial(
        manifest["trial_id"], manifest, files, archive_bytes, digest_bytes(archive_bytes)
    )
    verify_blind_trial(result)
    return result


def verify_trial_quote(value: BlindTrial, resource_path: str, quote: str) -> None:
    """Require a Finding quote to exist in the exact judge-visible file."""
    if not quote.strip():
        raise ValueError("Finding quote is required")
    item = value.file(resource_path)
    if item.media_type == "application/pdf":
        reader = PdfReader(BytesIO(item.data))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    elif item.media_type.startswith("text/") or item.media_type == "application/json":
        text = item.data.decode("utf-8")
    else:
        raise ValueError(f"Finding quotes are unsupported for {item.media_type}")
    normalized_text = " ".join(text.split()).casefold()
    normalized_quote = " ".join(quote.split()).casefold()
    if normalized_quote not in normalized_text:
        raise ValueError(f"Finding quote is absent from {resource_path}: {quote!r}")
