"""Pure, immutable contracts shared by every game domain."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from narrative_game.contracts.canonical import digest_json


_IDENTIFIER = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
_NAMESPACE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9_-]*)+$")


def require_identifier(value: str, *, label: str = "identifier") -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"invalid {label}: {value!r}")
    return value


@dataclass(frozen=True, order=True)
class TypedRef:
    """A reference whose expected target kind is explicit."""

    kind: str
    id: str

    def __post_init__(self) -> None:
        require_identifier(self.kind, label="reference kind")
        require_identifier(self.id, label="reference id")

    @classmethod
    def parse(cls, value: str) -> "TypedRef":
        kind, separator, identifier = value.partition(":")
        if not separator:
            raise ValueError(f"typed reference must contain ':': {value!r}")
        return cls(kind=kind, id=identifier)

    def __str__(self) -> str:
        return f"{self.kind}:{self.id}"


@dataclass(frozen=True)
class Resource:
    id: str
    media_type: str
    content_hash: str
    label: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Resource":
        return cls(
            id=str(value["id"]),
            media_type=str(value["media_type"]),
            content_hash=str(value["content_hash"]),
            label=str(value["label"]),
        )


@dataclass(frozen=True)
class Seat:
    id: str
    label: str
    required: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Seat":
        return cls(
            id=str(value["id"]),
            label=str(value["label"]),
            required=bool(value.get("required", True)),
        )


@dataclass(frozen=True)
class AccessPolicy:
    id: str
    resource: TypedRef
    grantees: tuple[TypedRef, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AccessPolicy":
        return cls(
            id=str(value["id"]),
            resource=TypedRef.parse(str(value["resource"])),
            grantees=tuple(TypedRef.parse(str(item)) for item in value["grantees"]),
        )


@dataclass(frozen=True)
class ExtensionManifest:
    namespace: str
    version: str
    profile: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ExtensionManifest":
        return cls(
            namespace=str(value["namespace"]),
            version=str(value["version"]),
            profile=str(value["profile"]) if value.get("profile") is not None else None,
        )

    def __post_init__(self) -> None:
        if not _NAMESPACE.fullmatch(self.namespace):
            raise ValueError(f"invalid extension namespace: {self.namespace!r}")


@dataclass(frozen=True, order=True)
class Finding:
    """One stable, attributable validation observation."""

    code: str
    severity: str
    locus: str
    quote: str
    message: str

    def __post_init__(self) -> None:
        if self.severity not in {"blocker", "warning"}:
            raise ValueError(f"invalid Finding severity: {self.severity!r}")

    def to_mapping(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "locus": self.locus,
            "quote": self.quote,
            "message": self.message,
        }


@dataclass(frozen=True)
class KernelDefinition:
    schema_version: str
    game_id: str
    title: str
    resources: tuple[Resource, ...]
    seats: tuple[Seat, ...]
    access_policies: tuple[AccessPolicy, ...]
    extensions: tuple[ExtensionManifest, ...]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "KernelDefinition":
        return cls(
            schema_version=str(value["schema_version"]),
            game_id=str(value["game_id"]),
            title=str(value["title"]),
            resources=tuple(Resource.from_mapping(item) for item in value["resources"]),
            seats=tuple(Seat.from_mapping(item) for item in value["seats"]),
            access_policies=tuple(
                AccessPolicy.from_mapping(item) for item in value["access_policies"]
            ),
            extensions=tuple(ExtensionManifest.from_mapping(item) for item in value["extensions"]),
        )

    @property
    def content_hash(self) -> str:
        return digest_json(self.to_mapping())

    def to_mapping(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "game_id": self.game_id,
            "title": self.title,
            "resources": [resource.__dict__ for resource in self.resources],
            "seats": [seat.__dict__ for seat in self.seats],
            "access_policies": [
                {
                    "id": policy.id,
                    "resource": str(policy.resource),
                    "grantees": [str(item) for item in policy.grantees],
                }
                for policy in self.access_policies
            ],
            "extensions": [extension.__dict__ for extension in self.extensions],
        }
