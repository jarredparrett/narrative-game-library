"""Universal Kernel validation with stable Finding order."""

from __future__ import annotations

from collections import Counter

from .model import Finding, KernelDefinition, require_identifier


def _duplicate_findings(kind: str, identifiers: list[str]) -> list[Finding]:
    return [
        Finding(
            code="kernel.duplicate-id",
            severity="blocker",
            locus=f"{kind}:{identifier}",
            quote=identifier,
            message=f"{kind} identifier is duplicated",
        )
        for identifier, count in Counter(identifiers).items()
        if count > 1
    ]


def validate_kernel(game: KernelDefinition) -> tuple[Finding, ...]:
    """Validate only format-neutral identity, references, and access policy."""
    findings: list[Finding] = []
    try:
        require_identifier(game.game_id, label="game id")
    except ValueError as exc:
        findings.append(
            Finding("kernel.invalid-id", "blocker", "game", game.game_id, str(exc))
        )
    findings.extend(_duplicate_findings("resource", [item.id for item in game.resources]))
    findings.extend(_duplicate_findings("seat", [item.id for item in game.seats]))
    findings.extend(_duplicate_findings("access-policy", [item.id for item in game.access_policies]))

    for kind, items in (
        ("resource", game.resources),
        ("seat", game.seats),
        ("access-policy", game.access_policies),
    ):
        for item in items:
            try:
                require_identifier(item.id, label=f"{kind} id")
            except ValueError as exc:
                findings.append(
                    Finding("kernel.invalid-id", "blocker", f"{kind}:{item.id}", item.id, str(exc))
                )
    for resource in game.resources:
        digest = resource.content_hash.removeprefix("sha256:")
        if (
            not resource.content_hash.startswith("sha256:")
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            findings.append(
                Finding(
                    "kernel.invalid-content-ref",
                    "blocker",
                    f"resource:{resource.id}.content-hash",
                    resource.content_hash,
                    "Resource content hash must be a lowercase SHA-256 reference",
                )
            )

    resources = {resource.id for resource in game.resources}
    seats = {seat.id for seat in game.seats}
    for policy in game.access_policies:
        if policy.resource.kind != "resource" or policy.resource.id not in resources:
            findings.append(
                Finding(
                    "kernel.dangling-reference",
                    "blocker",
                    f"access-policy:{policy.id}.resource",
                    str(policy.resource),
                    "access policy refers to a missing Resource",
                )
            )
        for grantee in policy.grantees:
            if grantee.kind not in {"seat", "viewer"} or (
                grantee.kind == "seat" and grantee.id not in seats
            ):
                findings.append(
                    Finding(
                        "kernel.dangling-reference",
                        "blocker",
                        f"access-policy:{policy.id}.grantees",
                        str(grantee),
                        "access policy refers to an unknown grantee",
                    )
                )
    namespaces = [extension.namespace for extension in game.extensions]
    findings.extend(_duplicate_findings("extension", namespaces))
    return tuple(sorted(findings))
