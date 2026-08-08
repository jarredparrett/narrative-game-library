"""Pure derivations from canonical Episodes into bounded difficulty evidence."""

from __future__ import annotations

from typing import Any, Mapping

from narrative_game.compiler import GameRelease
from narrative_game.contracts.canonical import digest_bytes
from narrative_game.simulation import EpisodeArchive, verify_episode

from .contracts import (
    DIFFICULTY_CONTRACT_CATALOG,
    CanonicalEvidenceSpan,
    EpisodeEvidencePackage,
    EvidenceViewManifest,
    EvidenceViewSpan,
    SemanticFixtureExpectation,
    VerificationStatus,
)


DISCOVERY_DENIED_FIELDS = (
    "acceptable_proof_path_ids",
    "agent_id",
    "context_id",
    "correct",
    "correct_hypothesis_id",
    "model",
    "model_name",
    "policy_id",
    "proof_path_id",
    "provider",
    "response_id",
    "terminal_state_hash",
    "trusted_reason",
    "truth_model",
)


def build_episode_evidence_package(
    release: GameRelease,
    archive: EpisodeArchive,
) -> EpisodeEvidencePackage:
    """Preserve every canonical Episode surface as an addressable span."""
    spans = [
        CanonicalEvidenceSpan(
            "archive:metadata",
            "archive-metadata",
            0,
            ("verification",),
            {
                "episode_id": archive.episode_id,
                "release_id": archive.release_id,
                "episode_seed": archive.episode_seed,
                "config": archive.config.to_mapping(),
                "lineup": archive.lineup.to_mapping(),
                "version_locks": dict(sorted(archive.version_locks.items())),
                "realized_seat_order": list(archive.realized_seat_order),
                "violations": list(archive.violations),
                "termination_reason": archive.termination_reason,
                "terminal_state_hash": archive.terminal_state_hash,
                "trace_head": archive.trace_head,
            },
        )
    ]
    for event in archive.events:
        spans.append(
            CanonicalEvidenceSpan(
                f"arena:{event.sequence:04d}",
                "arena-event",
                event.sequence,
                event.visibility,
                event.to_mapping(),
            )
        )
    for event in archive.session_history.ordered_events:
        spans.append(
            CanonicalEvidenceSpan(
                f"session:{event.sequence:04d}",
                "session-event",
                event.sequence,
                ("verification",),
                event.to_mapping(),
            )
        )
    for index, receipt in enumerate(archive.session_history.receipts, 1):
        spans.append(
            CanonicalEvidenceSpan(
                f"session-receipt:{index:04d}",
                "session-receipt",
                index,
                ("verification",),
                receipt.to_mapping(),
            )
        )
    for trajectory in sorted(archive.trajectories, key=lambda item: item.actor_id):
        for step in trajectory.steps:
            spans.append(
                CanonicalEvidenceSpan(
                    f"trajectory:{trajectory.actor_id}:{step.turn:04d}",
                    "trajectory-step",
                    step.turn,
                    (trajectory.actor_id,),
                    {
                        "actor_id": trajectory.actor_id,
                        "role": trajectory.role,
                        "policy": trajectory.policy.to_mapping(),
                        "step": step.to_mapping(),
                    },
                )
            )
    findings = verify_episode(release, archive)
    span_ids = tuple(item.span_id for item in spans)
    verification = VerificationStatus(
        "complete-episode-replay",
        "verified" if not findings else "invalid",
        "narrative-episode-verifier.1",
        span_ids,
        tuple(findings),
    )
    return EpisodeEvidencePackage(
        archive.episode_id,
        archive.release_id,
        digest_bytes(archive.to_bytes()),
        DIFFICULTY_CONTRACT_CATALOG.catalog_id,
        tuple(spans),
        verification,
    )


def _redact(
    value: Any,
    *,
    path: str,
    denied: frozenset[str],
    replacements: Mapping[str, str],
) -> tuple[Any, tuple[str, ...]]:
    redacted = []
    if isinstance(value, Mapping):
        result = {}
        for key in sorted(value):
            child_path = f"{path}.{key}" if path else str(key)
            if key in denied:
                redacted.append(child_path)
                continue
            child, child_redactions = _redact(
                value[key], path=child_path, denied=denied, replacements=replacements
            )
            result[key] = child
            redacted.extend(child_redactions)
        return result, tuple(redacted)
    if isinstance(value, (list, tuple)):
        result = []
        for index, item in enumerate(value):
            child, child_redactions = _redact(
                item,
                path=f"{path}[{index}]",
                denied=denied,
                replacements=replacements,
            )
            result.append(child)
            redacted.extend(child_redactions)
        return result, tuple(redacted)
    if isinstance(value, str) and value in replacements:
        return replacements[value], (path,)
    return value, ()


def _participant_replacements(package: EpisodeEvidencePackage) -> dict[str, str]:
    metadata = next(
        span.content for span in package.spans if span.source_kind == "archive-metadata"
    )
    lineup = metadata["lineup"]
    replacements = {}
    for index, assignment in enumerate(
        sorted(lineup["seats"], key=lambda item: str(item["seat_id"])), 1
    ):
        policy = assignment["policy"]
        slot = f"participant:seat-{index:03d}"
        replacements[f"seat:{assignment['seat_id']}:{policy['policy_id']}"] = slot
        replacements[str(policy["model"])] = "redacted:model"
        for key in ("policy_id", "agent_id", "context_id"):
            replacements[str(policy[key])] = slot
    host = lineup["host"]
    replacements[f"host:{host['policy_id']}"] = "participant:host"
    replacements[str(host["model"])] = "redacted:model"
    for key in ("policy_id", "agent_id", "context_id"):
        replacements[str(host[key])] = "participant:host"
    return replacements


def build_discovery_view(package: EpisodeEvidencePackage) -> EvidenceViewManifest:
    """Project replay evidence without canonical truth or fixture answers."""
    denied = frozenset(DISCOVERY_DENIED_FIELDS)
    replacements = _participant_replacements(package)
    spans = []
    for source in package.spans:
        content, redacted = _redact(
            source.content,
            path="",
            denied=denied,
            replacements=replacements,
        )
        spans.append(EvidenceViewSpan(source.span_id, content, redacted))
    return EvidenceViewManifest(
        "difficulty-d0.discovery-preflight.1",
        package.package_id,
        tuple(spans),
        DISCOVERY_DENIED_FIELDS,
    )


def _contains(value: Any, required: Any) -> bool:
    if isinstance(required, Mapping):
        return isinstance(value, Mapping) and all(
            key in value and _contains(value[key], child)
            for key, child in required.items()
        )
    if isinstance(required, (list, tuple)):
        return isinstance(value, (list, tuple)) and all(
            any(_contains(candidate, item) for candidate in value) for item in required
        )
    return value == required


def expectation_is_satisfied(
    package: EpisodeEvidencePackage,
    expectation: SemanticFixtureExpectation,
) -> bool:
    """Evaluate a fixture oracle outside every answer-safe Evidence View."""
    return any(
        span.source_kind == expectation.source_kind
        and span.content.get("event_type") == expectation.event_type
        and _contains(span.content, expectation.required_content)
        for span in package.spans
    )
