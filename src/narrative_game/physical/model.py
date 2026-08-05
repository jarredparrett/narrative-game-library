"""Values at the Game Release to Physical Export boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from narrative_game.contracts.canonical import digest_bytes


@dataclass(frozen=True)
class PhysicalExportProfile:
    profile_id: str = "letter-simplex-safe-v1"
    version: str = "1.0.0"
    page_size: str = "US-Letter"
    orientation: str = "portrait"
    color_mode: str = "grayscale-safe"
    sides: str = "simplex"
    margin_points: int = 54
    provenance_label: str = "FICTIONAL GAME MATERIAL - NOT AN ACTUAL RECORD"

    def to_mapping(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class PhysicalFile:
    path: str
    media_type: str
    data: bytes
    audience: str

    @property
    def content_hash(self) -> str:
        return digest_bytes(self.data)

    def descriptor(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "media_type": self.media_type,
            "content_hash": self.content_hash,
            "bytes": len(self.data),
            "audience": self.audience,
        }


@dataclass(frozen=True)
class PhysicalExport:
    export_id: str
    release_id: str
    profile: PhysicalExportProfile
    plan: Mapping[str, Any]
    preflight: Mapping[str, Any]
    files: tuple[PhysicalFile, ...]
    archive_bytes: bytes
    archive_hash: str

    def file(self, path: str) -> PhysicalFile:
        try:
            return next(item for item in self.files if item.path == path)
        except StopIteration as exc:
            raise KeyError(path) from exc
